import atexit
import logging
import os
import signal
import subprocess
import threading
import time
import uuid
from pathlib import Path

import requests

from src.config import get_app_config
from src.sandbox.sandbox import Sandbox
from src.sandbox.sandbox_provider import SandboxProvider
from src.utils.network import get_free_port, release_port

from .aio_sandbox import AioSandbox

logger = logging.getLogger(__name__)

# Thread data directory structure
THREAD_DATA_BASE_DIR = ".deer-flow/threads"
CONTAINER_USER_DATA_DIR = "/mnt/user-data"

# Default configuration
DEFAULT_IMAGE = "enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest"
DEFAULT_PORT = 8080
DEFAULT_CONTAINER_PREFIX = "deer-flow-sandbox"
DEFAULT_IDLE_TIMEOUT = 600  # 10 minutes in seconds
IDLE_CHECK_INTERVAL = 60  # Check every 60 seconds


class AioSandboxProvider(SandboxProvider):
    """Sandbox provider that manages containers running the AIO sandbox.

    On macOS, automatically prefers Apple Container if available, otherwise falls back to Docker.
    On other platforms, uses Docker.

    Configuration options in config.yaml under sandbox:
        use: src.community.aio_sandbox:AioSandboxProvider
        image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest  # Container image to use (works with both runtimes)
        port: 8080  # Base port for sandbox containers
        base_url: http://localhost:8080  # If set, uses existing sandbox instead of starting new container
        auto_start: true  # Whether to automatically start container
        container_prefix: deer-flow-sandbox  # Prefix for container names
        idle_timeout: 600  # Idle timeout in seconds (default: 600 = 10 minutes). Set to 0 to disable.
        mounts:  # List of volume mounts
          - host_path: /path/on/host
            container_path: /path/in/container
            read_only: false
        environment:  # Environment variables to inject (values starting with $ are resolved from host env)
          NODE_ENV: production
          API_KEY: $MY_API_KEY
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._sandboxes: dict[str, AioSandbox] = {}
        self._containers: dict[str, str] = {}  # sandbox_id -> container_id
        self._ports: dict[str, int] = {}  # sandbox_id -> port
        self._thread_sandboxes: dict[str, str] = {}  # thread_id -> sandbox_id (for reusing sandbox across turns)
        self._thread_locks: dict[str, threading.Lock] = {}  # thread_id -> lock (for thread-specific acquisition)
        self._last_activity: dict[str, float] = {}  # sandbox_id -> last activity timestamp
        # Pod pool allocation for StatefulSet mode (exclusive 1:1 thread-to-pod mapping)
        self._allocated_pods: dict[int, str] = {}  # pod_index -> thread_id (or sandbox_id if no thread_id)
        self._sandbox_pod_index: dict[str, int] = {}  # sandbox_id -> pod_index (for release)
        self._config = self._load_config()
        self._shutdown_called = False
        self._idle_checker_stop = threading.Event()
        self._idle_checker_thread: threading.Thread | None = None
        self._container_runtime = self._detect_container_runtime()

        # Register shutdown handler to clean up containers on exit
        atexit.register(self.shutdown)
        self._register_signal_handlers()

        # Start idle checker thread if idle_timeout is enabled
        if self._config.get("idle_timeout", DEFAULT_IDLE_TIMEOUT) > 0:
            self._start_idle_checker()

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        self._original_sigterm = signal.getsignal(signal.SIGTERM)
        self._original_sigint = signal.getsignal(signal.SIGINT)

        def signal_handler(signum, frame):
            self.shutdown()
            # Call original handler
            original = self._original_sigterm if signum == signal.SIGTERM else self._original_sigint
            if callable(original):
                original(signum, frame)
            elif original == signal.SIG_DFL:
                # Re-raise the signal with default handler
                signal.signal(signum, signal.SIG_DFL)
                signal.raise_signal(signum)

        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except ValueError:
            # Signal handling can only be set from the main thread
            logger.debug("Could not register signal handlers (not main thread)")

    def _start_idle_checker(self) -> None:
        """Start the background thread that checks for idle sandboxes."""
        self._idle_checker_thread = threading.Thread(
            target=self._idle_checker_loop,
            name="sandbox-idle-checker",
            daemon=True,
        )
        self._idle_checker_thread.start()
        logger.info(f"Started idle checker thread (timeout: {self._config.get('idle_timeout', DEFAULT_IDLE_TIMEOUT)}s)")

    def _idle_checker_loop(self) -> None:
        """Background loop that periodically checks and releases idle sandboxes."""
        idle_timeout = self._config.get("idle_timeout", DEFAULT_IDLE_TIMEOUT)

        while not self._idle_checker_stop.wait(timeout=IDLE_CHECK_INTERVAL):
            try:
                self._cleanup_idle_sandboxes(idle_timeout)
            except Exception as e:
                logger.error(f"Error in idle checker loop: {e}")

    def _cleanup_idle_sandboxes(self, idle_timeout: float) -> None:
        """Check and release sandboxes that have been idle for too long.

        Args:
            idle_timeout: Maximum idle time in seconds before releasing a sandbox.
        """
        current_time = time.time()
        sandboxes_to_release = []

        with self._lock:
            for sandbox_id, last_activity in self._last_activity.items():
                idle_duration = current_time - last_activity
                if idle_duration > idle_timeout:
                    sandboxes_to_release.append(sandbox_id)
                    logger.info(f"Sandbox {sandbox_id} has been idle for {idle_duration:.1f}s, marking for release")

        # Release sandboxes outside the lock
        for sandbox_id in sandboxes_to_release:
            try:
                logger.info(f"Releasing idle sandbox {sandbox_id}")
                self.release(sandbox_id)
            except Exception as e:
                logger.error(f"Failed to release idle sandbox {sandbox_id}: {e}")

    def _update_activity(self, sandbox_id: str) -> None:
        """Update the last activity timestamp for a sandbox.

        Args:
            sandbox_id: The ID of the sandbox.
        """
        with self._lock:
            self._last_activity[sandbox_id] = time.time()

    def _load_config(self) -> dict:
        """Load sandbox configuration from app config."""
        config = get_app_config()
        sandbox_config = config.sandbox

        # Set defaults
        return {
            "image": sandbox_config.image or DEFAULT_IMAGE,
            "port": sandbox_config.port or DEFAULT_PORT,
            "base_url": sandbox_config.base_url,
            "replicas": sandbox_config.replicas,
            "auto_start": sandbox_config.auto_start if sandbox_config.auto_start is not None else True,
            "container_prefix": sandbox_config.container_prefix or DEFAULT_CONTAINER_PREFIX,
            "idle_timeout": getattr(sandbox_config, "idle_timeout", None) or DEFAULT_IDLE_TIMEOUT,
            "mounts": sandbox_config.mounts or [],
            "environment": self._resolve_env_vars(sandbox_config.environment or {}),
        }

    def _resolve_env_vars(self, env_config: dict[str, str]) -> dict[str, str]:
        """Resolve environment variable references in configuration.

        Values starting with $ are resolved from host environment variables.

        Args:
            env_config: Dictionary of environment variable names to values.

        Returns:
            Dictionary with resolved environment variable values.
        """
        resolved = {}
        for key, value in env_config.items():
            if isinstance(value, str) and value.startswith("$"):
                env_name = value[1:]  # Remove $ prefix
                resolved[key] = os.environ.get(env_name, "")
            else:
                resolved[key] = str(value)
        return resolved

    def _detect_container_runtime(self) -> str:
        """Detect which container runtime to use.

        On macOS, prefer Apple Container if available, otherwise fall back to Docker.
        On other platforms, use Docker.

        Returns:
            "container" for Apple Container, "docker" for Docker.
        """
        import platform

        # Only try Apple Container on macOS
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(
                    ["container", "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5,
                )
                logger.info(f"Detected Apple Container: {result.stdout.strip()}")
                return "container"
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                logger.info("Apple Container not available, falling back to Docker")

        # Default to Docker
        return "docker"

    def _is_sandbox_ready(self, base_url: str, timeout: int = 30) -> bool:
        """Check if sandbox is ready to accept connections.

        Args:
            base_url: Base URL of the sandbox.
            timeout: Maximum time to wait in seconds.

        Returns:
            True if sandbox is ready, False otherwise.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{base_url}/v1/sandbox", timeout=5)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        return False

    def _resolve_pod_url(self, base_url_template: str, thread_id: str | None, sandbox_id: str) -> str:
        """Allocate an exclusive pod for this thread/sandbox from the StatefulSet pod pool.

        Each thread gets exclusive access to one pod to ensure filesystem isolation.
        When the sandbox is released, the pod is returned to the pool.

        Args:
            base_url_template: URL template containing {pod_index} placeholder.
            thread_id: Thread ID for exclusive allocation tracking.
            sandbox_id: Sandbox ID for tracking pod release.

        Returns:
            Resolved base_url pointing to the exclusively allocated pod.

        Raises:
            RuntimeError: If no free and healthy pod is available.
        """
        replicas = self._config.get("replicas")
        if not replicas or replicas < 1:
            logger.warning("base_url contains {pod_index} but replicas is not set, defaulting to 1")
            replicas = 1

        # Determine the allocation key (prefer thread_id, fall back to sandbox_id)
        alloc_key = thread_id or sandbox_id

        # Build the list of free pod indices
        with self._lock:
            free_pods = [i for i in range(replicas) if i not in self._allocated_pods]

        if not free_pods:
            raise RuntimeError(f"All {replicas} sandbox pods are exclusively allocated, no free pod available for thread {thread_id}")

        # Probe free pods to find a healthy one (outside lock to avoid blocking)
        for pod_index in free_pods:
            candidate_url = base_url_template.replace("{pod_index}", str(pod_index))
            try:
                response = requests.get(f"{candidate_url}/v1/sandbox", timeout=3)
                if response.status_code == 200:
                    with self._lock:
                        # Double-check: another thread may have taken this pod
                        if pod_index in self._allocated_pods:
                            continue
                        self._allocated_pods[pod_index] = alloc_key
                        self._sandbox_pod_index[sandbox_id] = pod_index
                    logger.info(f"Exclusively allocated pod {pod_index} to thread={thread_id} sandbox={sandbox_id}")
                    return candidate_url
            except requests.exceptions.RequestException:
                logger.debug(f"Pod {pod_index} is not reachable at {candidate_url}")

        raise RuntimeError(f"No healthy sandbox pod available ({len(free_pods)} free but all unhealthy, replicas={replicas})")

    def _get_thread_mounts(self, thread_id: str) -> list[tuple[str, str, bool]]:
        """Get the volume mounts for a thread's data directories.

        Creates the directories if they don't exist (lazy initialization).

        Args:
            thread_id: The thread ID.

        Returns:
            List of (host_path, container_path, read_only) tuples.
        """
        base_dir = os.getcwd()
        thread_dir = Path(base_dir) / THREAD_DATA_BASE_DIR / thread_id / "user-data"

        # Create directories for Docker volume mounts (required before container starts)
        mounts = [
            (str(thread_dir / "workspace"), f"{CONTAINER_USER_DATA_DIR}/workspace", False),
            (str(thread_dir / "uploads"), f"{CONTAINER_USER_DATA_DIR}/uploads", False),
            (str(thread_dir / "outputs"), f"{CONTAINER_USER_DATA_DIR}/outputs", False),
        ]

        # Ensure directories exist before mounting
        for host_path, _, _ in mounts:
            os.makedirs(host_path, exist_ok=True)

        return mounts

    def _get_skills_mount(self) -> tuple[str, str, bool] | None:
        """Get the skills directory mount configuration.

        Returns:
            Tuple of (host_path, container_path, read_only) if skills directory exists,
            None otherwise.
        """
        try:
            config = get_app_config()
            skills_path = config.skills.get_skills_path()
            container_path = config.skills.container_path

            # Only mount if skills directory exists
            if skills_path.exists():
                return (str(skills_path), container_path, True)  # Read-only mount for security
        except Exception as e:
            logger.warning(f"Could not setup skills mount: {e}")

        return None

    def _start_container(self, sandbox_id: str, port: int, extra_mounts: list[tuple[str, str, bool]] | None = None) -> str:
        """Start a new container for the sandbox.

        On macOS, prefers Apple Container if available, otherwise uses Docker.
        On other platforms, uses Docker.

        Args:
            sandbox_id: Unique identifier for the sandbox.
            port: Port to expose the sandbox API on.
            extra_mounts: Additional volume mounts as (host_path, container_path, read_only) tuples.

        Returns:
            The container ID.
        """
        image = self._config["image"]
        container_name = f"{self._config['container_prefix']}-{sandbox_id}"

        cmd = [
            self._container_runtime,
            "run",
        ]

        # Add Docker-specific security options
        if self._container_runtime == "docker":
            cmd.extend(["--security-opt", "seccomp=unconfined"])

        cmd.extend(
            [
                "--rm",
                "-d",
                "-p",
                f"{port}:8080",
                "--name",
                container_name,
            ]
        )

        # Add configured environment variables
        for key, value in self._config["environment"].items():
            cmd.extend(["-e", f"{key}={value}"])

        # Add configured volume mounts
        for mount in self._config["mounts"]:
            host_path = mount.host_path
            container_path = mount.container_path
            read_only = mount.read_only
            mount_spec = f"{host_path}:{container_path}"
            if read_only:
                mount_spec += ":ro"
            cmd.extend(["-v", mount_spec])

        # Add extra mounts (e.g., thread-specific directories)
        if extra_mounts:
            for host_path, container_path, read_only in extra_mounts:
                mount_spec = f"{host_path}:{container_path}"
                if read_only:
                    mount_spec += ":ro"
                cmd.extend(["-v", mount_spec])

        cmd.append(image)

        logger.info(f"Starting sandbox container using {self._container_runtime}: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            container_id = result.stdout.strip()
            logger.info(f"Started sandbox container {container_name} with ID {container_id} using {self._container_runtime}")
            return container_id
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start sandbox container using {self._container_runtime}: {e.stderr}")
            raise RuntimeError(f"Failed to start sandbox container: {e.stderr}")

    def _stop_container(self, container_id: str) -> None:
        """Stop and remove a container.

        Since we use --rm flag, the container is automatically removed after stopping.

        Args:
            container_id: The container ID to stop.
        """
        try:
            subprocess.run([self._container_runtime, "stop", container_id], capture_output=True, text=True, check=True)
            logger.info(f"Stopped sandbox container {container_id} using {self._container_runtime} (--rm will auto-remove)")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to stop sandbox container {container_id}: {e.stderr}")

    def _get_thread_lock(self, thread_id: str) -> threading.Lock:
        """Get or create a lock for a specific thread_id.

        This ensures that concurrent sandbox acquisition for the same thread_id
        is serialized, preventing duplicate sandbox creation.

        Args:
            thread_id: The thread ID.

        Returns:
            A lock specific to this thread_id.
        """
        with self._lock:
            if thread_id not in self._thread_locks:
                self._thread_locks[thread_id] = threading.Lock()
            return self._thread_locks[thread_id]

    def acquire(self, thread_id: str | None = None) -> str:
        """Acquire a sandbox environment and return its ID.

        If base_url is configured, uses the existing sandbox.
        Otherwise, starts a new Docker container.

        For the same thread_id, this method will return the same sandbox_id,
        allowing sandbox reuse across multiple turns in a conversation.

        This method is thread-safe and prevents race conditions when multiple
        concurrent requests try to acquire a sandbox for the same thread_id.

        Args:
            thread_id: Optional thread ID for thread-specific configurations.
                If provided, the sandbox will be configured with thread-specific
                mounts for workspace, uploads, and outputs directories.
                The same thread_id will reuse the same sandbox.

        Returns:
            The ID of the acquired sandbox environment.
        """
        # For thread-specific acquisition, use a per-thread lock to prevent
        # concurrent creation of multiple sandboxes for the same thread
        if thread_id:
            thread_lock = self._get_thread_lock(thread_id)
            with thread_lock:
                return self._acquire_internal(thread_id)
        else:
            return self._acquire_internal(thread_id)

    def _acquire_internal(self, thread_id: str | None) -> str:
        """Internal implementation of sandbox acquisition.

        This method should only be called from acquire() which handles locking.

        Args:
            thread_id: Optional thread ID for thread-specific configurations.

        Returns:
            The ID of the acquired sandbox environment.
        """
        # Check if we already have a sandbox for this thread
        if thread_id:
            with self._lock:
                if thread_id in self._thread_sandboxes:
                    existing_sandbox_id = self._thread_sandboxes[thread_id]
                    # Verify the sandbox still exists
                    if existing_sandbox_id in self._sandboxes:
                        logger.info(f"Reusing existing sandbox {existing_sandbox_id} for thread {thread_id}")
                        self._last_activity[existing_sandbox_id] = time.time()
                        return existing_sandbox_id
                    else:
                        # Sandbox was released, remove stale mapping
                        del self._thread_sandboxes[thread_id]

        sandbox_id = str(uuid.uuid4())[:8]

        # Get thread-specific mounts if thread_id is provided
        extra_mounts = []
        if thread_id:
            extra_mounts.extend(self._get_thread_mounts(thread_id))
            logger.info(f"Adding thread mounts for thread {thread_id}: {extra_mounts}")

        # Add skills mount if available
        skills_mount = self._get_skills_mount()
        if skills_mount:
            extra_mounts.append(skills_mount)
            logger.info(f"Adding skills mount: {skills_mount}")

        # If base_url is configured, use existing sandbox
        if self._config.get("base_url"):
            base_url_template = self._config["base_url"]

            # StatefulSet exclusive pod allocation: resolve {pod_index} in base_url
            # _resolve_pod_url already probes health, so skip _is_sandbox_ready
            if "{pod_index}" in base_url_template:
                base_url = self._resolve_pod_url(base_url_template, thread_id, sandbox_id)
                skip_ready_check = True
            else:
                base_url = base_url_template
                skip_ready_check = False

            logger.info(f"Using existing sandbox at {base_url}")

            if not skip_ready_check and not self._is_sandbox_ready(base_url, timeout=60):
                raise RuntimeError(f"Sandbox at {base_url} is not ready")

            sandbox = AioSandbox(id=sandbox_id, base_url=base_url)
            with self._lock:
                self._sandboxes[sandbox_id] = sandbox
                self._last_activity[sandbox_id] = time.time()
                if thread_id:
                    self._thread_sandboxes[thread_id] = sandbox_id
            return sandbox_id

        # Otherwise, start a new container
        if not self._config.get("auto_start", True):
            raise RuntimeError("auto_start is disabled and no base_url is configured")

        # Allocate port using thread-safe utility
        port = get_free_port(start_port=self._config["port"])
        try:
            container_id = self._start_container(sandbox_id, port, extra_mounts=extra_mounts if extra_mounts else None)
        except Exception:
            # Release port if container failed to start
            release_port(port)
            raise

        base_url = f"http://localhost:{port}"

        # Wait for sandbox to be ready
        if not self._is_sandbox_ready(base_url, timeout=60):
            # Clean up container and release port if it didn't start properly
            self._stop_container(container_id)
            release_port(port)
            raise RuntimeError("Sandbox container failed to start within timeout")

        sandbox = AioSandbox(id=sandbox_id, base_url=base_url)
        with self._lock:
            self._sandboxes[sandbox_id] = sandbox
            self._containers[sandbox_id] = container_id
            self._ports[sandbox_id] = port
            self._last_activity[sandbox_id] = time.time()
            if thread_id:
                self._thread_sandboxes[thread_id] = sandbox_id
        logger.info(f"Acquired sandbox {sandbox_id} for thread {thread_id} at {base_url}")
        return sandbox_id

    def get(self, sandbox_id: str) -> Sandbox | None:
        """Get a sandbox environment by ID.

        This method is thread-safe. Also updates the last activity timestamp
        to prevent idle timeout while the sandbox is being used.

        Args:
            sandbox_id: The ID of the sandbox environment.

        Returns:
            The sandbox instance if found, None otherwise.
        """
        with self._lock:
            sandbox = self._sandboxes.get(sandbox_id)
            if sandbox is not None:
                self._last_activity[sandbox_id] = time.time()
            return sandbox

    def release(self, sandbox_id: str) -> None:
        """Release a sandbox environment.

        If the sandbox was started by this provider, stops the container
        and releases the allocated port.

        This method is thread-safe.

        Args:
            sandbox_id: The ID of the sandbox environment to release.
        """
        container_id = None
        port = None

        with self._lock:
            if sandbox_id in self._sandboxes:
                del self._sandboxes[sandbox_id]
                logger.info(f"Released sandbox {sandbox_id}")

            # Remove thread_id -> sandbox_id mapping
            thread_ids_to_remove = [tid for tid, sid in self._thread_sandboxes.items() if sid == sandbox_id]
            for tid in thread_ids_to_remove:
                del self._thread_sandboxes[tid]

            # Release exclusive pod allocation back to the pool
            if sandbox_id in self._sandbox_pod_index:
                pod_index = self._sandbox_pod_index.pop(sandbox_id)
                self._allocated_pods.pop(pod_index, None)
                logger.info(f"Released pod {pod_index} back to pool (sandbox={sandbox_id})")

            # Remove last activity tracking
            if sandbox_id in self._last_activity:
                del self._last_activity[sandbox_id]

            # Get container and port info while holding the lock
            if sandbox_id in self._containers:
                container_id = self._containers.pop(sandbox_id)

            if sandbox_id in self._ports:
                port = self._ports.pop(sandbox_id)

        # Stop container and release port outside the lock to avoid blocking
        if container_id:
            self._stop_container(container_id)

        if port:
            release_port(port)

    def shutdown(self) -> None:
        """Shutdown all sandbox containers managed by this provider.

        This method should be called when the application is shutting down
        to ensure all containers are properly stopped and ports are released.

        This method is thread-safe and idempotent (safe to call multiple times).
        """
        # Prevent multiple shutdown calls
        with self._lock:
            if self._shutdown_called:
                return
            self._shutdown_called = True
            sandbox_ids = list(self._sandboxes.keys())

        # Stop the idle checker thread
        self._idle_checker_stop.set()
        if self._idle_checker_thread is not None and self._idle_checker_thread.is_alive():
            self._idle_checker_thread.join(timeout=5)
            logger.info("Stopped idle checker thread")

        logger.info(f"Shutting down {len(sandbox_ids)} sandbox container(s)")

        for sandbox_id in sandbox_ids:
            try:
                self.release(sandbox_id)
            except Exception as e:
                logger.error(f"Failed to release sandbox {sandbox_id} during shutdown: {e}")
