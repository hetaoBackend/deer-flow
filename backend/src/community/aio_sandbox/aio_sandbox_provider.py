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


class AioSandboxProvider(SandboxProvider):
    """Sandbox provider that manages Docker containers running the AIO sandbox.

    Configuration options in config.yaml under sandbox:
        use: src.community.aio_sandbox:AioSandboxProvider
        image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest  # Docker image to use
        port: 8080  # Base port for sandbox containers
        base_url: http://localhost:8080  # If set, uses existing sandbox instead of starting new container
        auto_start: true  # Whether to automatically start Docker container
        container_prefix: deer-flow-sandbox  # Prefix for container names
        mounts:  # List of volume mounts
          - host_path: /path/on/host
            container_path: /path/in/container
            read_only: false
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._sandboxes: dict[str, AioSandbox] = {}
        self._containers: dict[str, str] = {}  # sandbox_id -> container_id
        self._ports: dict[str, int] = {}  # sandbox_id -> port
        self._config = self._load_config()
        self._shutdown_called = False

        # Register shutdown handler to clean up containers on exit
        atexit.register(self.shutdown)
        self._register_signal_handlers()

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

    def _load_config(self) -> dict:
        """Load sandbox configuration from app config."""
        config = get_app_config()
        sandbox_config = config.sandbox

        # Set defaults
        return {
            "image": sandbox_config.image or DEFAULT_IMAGE,
            "port": sandbox_config.port or DEFAULT_PORT,
            "base_url": sandbox_config.base_url,
            "auto_start": sandbox_config.auto_start if sandbox_config.auto_start is not None else True,
            "container_prefix": sandbox_config.container_prefix or DEFAULT_CONTAINER_PREFIX,
            "mounts": sandbox_config.mounts or [],
        }

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

    def _get_thread_mounts(self, thread_id: str) -> list[tuple[str, str, bool]]:
        """Get the volume mounts for a thread's data directories.

        Args:
            thread_id: The thread ID.

        Returns:
            List of (host_path, container_path, read_only) tuples.
        """
        base_dir = os.getcwd()
        thread_dir = Path(base_dir) / THREAD_DATA_BASE_DIR / thread_id / "user-data"

        return [
            (str(thread_dir / "workspace"), f"{CONTAINER_USER_DATA_DIR}/workspace", False),
            (str(thread_dir / "uploads"), f"{CONTAINER_USER_DATA_DIR}/uploads", False),
            (str(thread_dir / "outputs"), f"{CONTAINER_USER_DATA_DIR}/outputs", False),
        ]

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
        """Start a new Docker container for the sandbox.

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
            "docker",
            "run",
            "--security-opt",
            "seccomp=unconfined",
            "--rm",
            "-d",
            "-p",
            f"{port}:8080",
            "--name",
            container_name,
        ]

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

        logger.info(f"Starting sandbox container: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            container_id = result.stdout.strip()
            logger.info(f"Started sandbox container {container_name} with ID {container_id}")
            return container_id
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start sandbox container: {e.stderr}")
            raise RuntimeError(f"Failed to start sandbox container: {e.stderr}")

    def _stop_container(self, container_id: str) -> None:
        """Stop and remove a Docker container.

        Args:
            container_id: The container ID to stop.
        """
        try:
            subprocess.run(["docker", "stop", container_id], capture_output=True, text=True, check=True)
            logger.info(f"Stopped sandbox container {container_id}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to stop sandbox container {container_id}: {e.stderr}")

    def acquire(self, thread_id: str | None = None) -> str:
        """Acquire a sandbox environment and return its ID.

        If base_url is configured, uses the existing sandbox.
        Otherwise, starts a new Docker container.

        This method is thread-safe.

        Args:
            thread_id: Optional thread ID for thread-specific configurations.
                If provided, the sandbox will be configured with thread-specific
                mounts for workspace, uploads, and outputs directories.

        Returns:
            The ID of the acquired sandbox environment.
        """
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
            base_url = self._config["base_url"]
            logger.info(f"Using existing sandbox at {base_url}")

            if not self._is_sandbox_ready(base_url, timeout=60):
                raise RuntimeError(f"Sandbox at {base_url} is not ready")

            sandbox = AioSandbox(id=sandbox_id, base_url=base_url)
            with self._lock:
                self._sandboxes[sandbox_id] = sandbox
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
        logger.info(f"Acquired sandbox {sandbox_id} at {base_url}")
        return sandbox_id

    def get(self, sandbox_id: str) -> Sandbox | None:
        """Get a sandbox environment by ID.

        This method is thread-safe.

        Args:
            sandbox_id: The ID of the sandbox environment.

        Returns:
            The sandbox instance if found, None otherwise.
        """
        with self._lock:
            return self._sandboxes.get(sandbox_id)

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

        logger.info(f"Shutting down {len(sandbox_ids)} sandbox container(s)")

        for sandbox_id in sandbox_ids:
            try:
                self.release(sandbox_id)
            except Exception as e:
                logger.error(f"Failed to release sandbox {sandbox_id} during shutdown: {e}")
