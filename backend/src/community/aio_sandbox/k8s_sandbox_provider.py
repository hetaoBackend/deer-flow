import atexit
import logging
import os
import signal
import threading
import time
import uuid
from pathlib import Path

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from src.config import get_app_config
from src.sandbox.sandbox import Sandbox
from src.sandbox.sandbox_provider import SandboxProvider

from .aio_sandbox import AioSandbox
from .exceptions import K8sSandboxError

logger = logging.getLogger(__name__)

# Reuse constants from AioSandboxProvider
THREAD_DATA_BASE_DIR = ".deer-flow/threads"
CONTAINER_USER_DATA_DIR = "/mnt/user-data"

# Default configuration
DEFAULT_IMAGE = "enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest"
DEFAULT_NAMESPACE = "deer-flow"
DEFAULT_POD_PREFIX = "deer-flow-sandbox"
DEFAULT_TTL_SECONDS = 3600  # 1 hour - K8s will auto-terminate Pods after this
DEFAULT_SERVICE_NAME = "deer-flow-sandbox"


class KubernetesSandboxProvider(SandboxProvider):
    """Sandbox provider that manages Kubernetes Pods running the AIO sandbox.

    This provider dynamically creates and destroys Kubernetes Pods for sandbox
    execution, enabling true concurrent multi-instance support without port conflicts.

    Configuration options in config.yaml under sandbox:
        use: src.community.aio_sandbox:KubernetesSandboxProvider
        image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
        k8s_namespace: deer-flow  # Kubernetes namespace
        k8s_context: docker-desktop  # Optional: kubeconfig context
        ttl_seconds: 3600  # Pod cleanup TTL after release
        cpu_request: 100m  # Optional: CPU request
        cpu_limit: 1000m   # Optional: CPU limit
        memory_request: 256Mi  # Optional: Memory request
        memory_limit: 1Gi      # Optional: Memory limit
        environment:  # Environment variables ($ prefix resolves from host)
          NODE_ENV: production
          API_KEY: $MY_API_KEY
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._sandboxes: dict[str, AioSandbox] = {}
        self._pods: dict[str, str] = {}  # sandbox_id -> pod_name
        self._thread_sandboxes: dict[str, str] = {}  # thread_id -> sandbox_id
        self._config = self._load_config()
        self._shutdown_called = False

        # Initialize Kubernetes client
        self._init_k8s_client()

        # Register shutdown handlers
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
                signal.signal(signum, signal.SIG_DFL)
                signal.raise_signal(signum)

        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except ValueError:
            logger.debug("Could not register signal handlers (not main thread)")

    def _load_config(self) -> dict:
        """Load sandbox configuration from app config."""
        config = get_app_config()
        sandbox_config = config.sandbox

        return {
            "image": sandbox_config.image or DEFAULT_IMAGE,
            "namespace": getattr(sandbox_config, "k8s_namespace", DEFAULT_NAMESPACE),
            "context": getattr(sandbox_config, "k8s_context", None),
            "ttl_seconds": getattr(sandbox_config, "ttl_seconds", DEFAULT_TTL_SECONDS),
            "service_name": DEFAULT_SERVICE_NAME,
            "pod_prefix": DEFAULT_POD_PREFIX,
            "cpu_request": getattr(sandbox_config, "cpu_request", None),
            "cpu_limit": getattr(sandbox_config, "cpu_limit", None),
            "memory_request": getattr(sandbox_config, "memory_request", None),
            "memory_limit": getattr(sandbox_config, "memory_limit", None),
            "environment": self._resolve_env_vars(getattr(sandbox_config, "environment", {}) or {}),
        }

    def _resolve_env_vars(self, env_config: dict[str, str]) -> dict[str, str]:
        """Resolve environment variable references in configuration."""
        resolved = {}
        for key, value in env_config.items():
            if isinstance(value, str) and value.startswith("$"):
                env_name = value[1:]
                resolved[key] = os.environ.get(env_name, "")
            else:
                resolved[key] = str(value)
        return resolved

    def _init_k8s_client(self) -> None:
        """Initialize Kubernetes API client."""
        try:
            # Load kubeconfig with optional context
            if self._config.get("context"):
                config.load_kube_config(context=self._config["context"])
            else:
                config.load_kube_config()

            self._core_v1 = client.CoreV1Api()
            logger.info(f"Initialized K8s client for namespace {self._config['namespace']}")
        except Exception as e:
            raise K8sSandboxError(f"Failed to initialize Kubernetes client: {e}", reason="ClientInitError")

    def _get_project_root(self) -> str:
        """Get project root directory from current working directory."""
        return os.getcwd()

    def _get_thread_volumes(self, thread_id: str) -> tuple[list[client.V1Volume], list[client.V1VolumeMount]]:
        """Create volume and volume mount specs for thread data directories.

        Args:
            thread_id: The thread ID.

        Returns:
            Tuple of (volumes, volume_mounts) for Pod spec.
        """
        project_root = self._get_project_root()
        thread_dir = Path(project_root) / THREAD_DATA_BASE_DIR / thread_id / "user-data"

        # Ensure directories exist before creating Pod
        for subdir in ["workspace", "uploads", "outputs"]:
            os.makedirs(thread_dir / subdir, exist_ok=True)

        volumes = []
        volume_mounts = []

        for subdir in ["workspace", "uploads", "outputs"]:
            host_path = str(thread_dir / subdir)
            container_path = f"{CONTAINER_USER_DATA_DIR}/{subdir}"

            volumes.append(client.V1Volume(name=f"thread-{subdir}", host_path=client.V1HostPathVolumeSource(path=host_path, type="Directory")))
            volume_mounts.append(client.V1VolumeMount(name=f"thread-{subdir}", mount_path=container_path, read_only=False))

        return volumes, volume_mounts

    def _get_skills_volume(self) -> tuple[client.V1Volume | None, client.V1VolumeMount | None]:
        """Create volume and volume mount specs for skills directory.

        Returns:
            Tuple of (volume, volume_mount) or (None, None) if skills not available.
        """
        try:
            app_config = get_app_config()
            container_path = app_config.skills.container_path

            # Use shared PVC for skills
            volume = client.V1Volume(name="skills", persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name="deer-flow-skills-pvc"))
            volume_mount = client.V1VolumeMount(name="skills", mount_path=container_path, read_only=True)

            return volume, volume_mount
        except Exception as e:
            logger.warning(f"Could not setup skills volume: {e}")
            return None, None

    def _build_resource_requirements(self) -> client.V1ResourceRequirements | None:
        """Build resource requirements for Pod."""
        requests = {}
        limits = {}

        if self._config.get("cpu_request"):
            requests["cpu"] = self._config["cpu_request"]
        if self._config.get("memory_request"):
            requests["memory"] = self._config["memory_request"]
        if self._config.get("cpu_limit"):
            limits["cpu"] = self._config["cpu_limit"]
        if self._config.get("memory_limit"):
            limits["memory"] = self._config["memory_limit"]

        if not requests and not limits:
            return None

        return client.V1ResourceRequirements(requests=requests if requests else None, limits=limits if limits else None)

    def _create_pod(self, sandbox_id: str, thread_id: str | None = None) -> str:
        """Create a Kubernetes Pod for the sandbox.

        Args:
            sandbox_id: Unique identifier for the sandbox.
            thread_id: Optional thread ID for thread-specific mounts.

        Returns:
            The Pod name.

        Raises:
            K8sSandboxError: If Pod creation fails.
        """
        pod_name = f"{self._config['pod_prefix']}-{sandbox_id}"
        namespace = self._config["namespace"]

        # Build volumes and volume mounts
        volumes = []
        volume_mounts = []

        # Add thread-specific volumes
        if thread_id:
            thread_volumes, thread_mounts = self._get_thread_volumes(thread_id)
            volumes.extend(thread_volumes)
            volume_mounts.extend(thread_mounts)

        # Add skills volume
        skills_volume, skills_mount = self._get_skills_volume()
        if skills_volume and skills_mount:
            volumes.append(skills_volume)
            volume_mounts.append(skills_mount)

        # Build environment variables
        env_vars = [client.V1EnvVar(name=key, value=value) for key, value in self._config["environment"].items()]

        # Build container spec
        container = client.V1Container(
            name="sandbox",
            image=self._config["image"],
            ports=[client.V1ContainerPort(container_port=8080)],
            env=env_vars if env_vars else None,
            volume_mounts=volume_mounts if volume_mounts else None,
            resources=self._build_resource_requirements(),
            readiness_probe=client.V1Probe(http_get=client.V1HTTPGetAction(path="/v1/sandbox", port=8080), initial_delay_seconds=2, period_seconds=2, timeout_seconds=5, failure_threshold=3),
            security_context=client.V1SecurityContext(
                # Maintain same security profile as Docker version
                privileged=False,
                allow_privilege_escalation=True,  # Required for seccomp=unconfined equivalent
            ),
        )

        # Build Pod spec
        # Use activeDeadlineSeconds to let K8s auto-cleanup Pods after TTL
        ttl_seconds = self._config["ttl_seconds"]
        pod_spec = client.V1PodSpec(
            containers=[container],
            volumes=volumes if volumes else None,
            restart_policy="Never",
            active_deadline_seconds=ttl_seconds,
            # Single-node deployment assumption: no nodeSelector needed
        )

        # Build Pod metadata
        pod_metadata = client.V1ObjectMeta(
            name=pod_name,
            namespace=namespace,
            labels={
                "app": "deer-flow-sandbox",
                "app.kubernetes.io/name": "deer-flow",
                "app.kubernetes.io/component": "sandbox",
                "sandbox-id": sandbox_id,
            },
        )

        # Create Pod object
        pod = client.V1Pod(api_version="v1", kind="Pod", metadata=pod_metadata, spec=pod_spec)

        # Create Pod via K8s API
        try:
            self._core_v1.create_namespaced_pod(namespace=namespace, body=pod)
            logger.info(f"Created Pod {pod_name} in namespace {namespace}")
            return pod_name
        except ApiException as e:
            raise K8sSandboxError(f"Failed to create Pod {pod_name}: {e.reason}", reason=e.reason, status_code=e.status)

    def _wait_for_pod_ready(self, pod_name: str, timeout: int = 60) -> bool:
        """Wait for Pod to be ready.

        Args:
            pod_name: The Pod name.
            timeout: Maximum time to wait in seconds.

        Returns:
            True if Pod is ready, False otherwise.
        """
        namespace = self._config["namespace"]
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                pod = self._core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)

                # Check if Pod is running
                if pod.status.phase != "Running":
                    time.sleep(2)
                    continue

                # Check if all containers are ready
                if pod.status.conditions:
                    for condition in pod.status.conditions:
                        if condition.type == "Ready" and condition.status == "True":
                            logger.info(f"Pod {pod_name} is ready")
                            return True

                time.sleep(2)
            except ApiException as e:
                logger.warning(f"Error checking Pod status: {e.reason}")
                time.sleep(2)

        return False

    def _get_pod_url(self, pod_name: str) -> str:
        """Get URL for accessing Pod.

        Uses Pod IP directly for compatibility with local development environments.
        The Kubernetes internal DNS (*.svc.cluster.local) only works from within
        the cluster, so we use the Pod IP which is accessible from the host machine
        in typical local K8s setups (Docker Desktop, OrbStack, Minikube, etc.).

        Args:
            pod_name: The Pod name.

        Returns:
            HTTP URL for accessing the Pod.
        """
        namespace = self._config["namespace"]

        try:
            pod = self._core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            pod_ip = pod.status.pod_ip
            if pod_ip:
                return f"http://{pod_ip}:8080"
        except ApiException as e:
            logger.warning(f"Failed to get Pod IP for {pod_name}: {e.reason}")

        # Fallback to DNS (works when running inside the cluster)
        service_name = self._config["service_name"]
        return f"http://{pod_name}.{service_name}.{namespace}.svc.cluster.local:8080"

    def _delete_pod(self, pod_name: str) -> None:
        """Delete a Kubernetes Pod.

        Args:
            pod_name: The Pod name to delete.
        """
        namespace = self._config["namespace"]

        try:
            self._core_v1.delete_namespaced_pod(name=pod_name, namespace=namespace, body=client.V1DeleteOptions(propagation_policy="Background"))
            logger.info(f"Deleted Pod {pod_name}")
        except ApiException as e:
            if e.status == 404:
                logger.debug(f"Pod {pod_name} already deleted")
            else:
                logger.warning(f"Failed to delete Pod {pod_name}: {e.reason}")

    def acquire(self, thread_id: str | None = None) -> str:
        """Acquire a sandbox environment and return its ID.

        Creates a new Kubernetes Pod for the sandbox with thread-specific
        volume mounts and shared skills access.

        For the same thread_id, reuses the existing sandbox to maintain
        state across conversation turns.

        This method is thread-safe.

        Args:
            thread_id: Optional thread ID for thread-specific configurations.

        Returns:
            The ID of the acquired sandbox environment.

        Raises:
            K8sSandboxError: If Pod creation or startup fails.
        """
        # Check if we already have a sandbox for this thread
        if thread_id:
            with self._lock:
                if thread_id in self._thread_sandboxes:
                    existing_sandbox_id = self._thread_sandboxes[thread_id]
                    if existing_sandbox_id in self._sandboxes:
                        logger.info(f"Reusing existing sandbox {existing_sandbox_id} for thread {thread_id}")
                        return existing_sandbox_id
                    else:
                        del self._thread_sandboxes[thread_id]

        sandbox_id = str(uuid.uuid4())[:8]

        try:
            # Create Pod
            pod_name = self._create_pod(sandbox_id, thread_id)

            # Wait for Pod to be ready
            if not self._wait_for_pod_ready(pod_name, timeout=60):
                self._delete_pod(pod_name)
                raise K8sSandboxError(f"Pod {pod_name} failed to become ready within timeout", reason="PodStartupTimeout")

            # Get Pod URL (uses Pod IP for local dev compatibility)
            base_url = self._get_pod_url(pod_name)

            # Create sandbox instance
            sandbox = AioSandbox(id=sandbox_id, base_url=base_url)

            with self._lock:
                self._sandboxes[sandbox_id] = sandbox
                self._pods[sandbox_id] = pod_name
                if thread_id:
                    self._thread_sandboxes[thread_id] = sandbox_id

            logger.info(f"Acquired sandbox {sandbox_id} for thread {thread_id} at {base_url}")
            return sandbox_id

        except Exception as e:
            logger.error(f"Failed to acquire sandbox: {e}")
            raise

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

        Deletes the associated Kubernetes Pod. The Pod will be terminated
        and cleaned up by Kubernetes.

        This method is thread-safe.

        Args:
            sandbox_id: The ID of the sandbox environment to release.
        """
        pod_name = None

        with self._lock:
            if sandbox_id in self._sandboxes:
                del self._sandboxes[sandbox_id]
                logger.info(f"Released sandbox {sandbox_id}")

            # Remove thread_id -> sandbox_id mapping
            thread_ids_to_remove = [tid for tid, sid in self._thread_sandboxes.items() if sid == sandbox_id]
            for tid in thread_ids_to_remove:
                del self._thread_sandboxes[tid]

            # Get Pod name for deletion
            if sandbox_id in self._pods:
                pod_name = self._pods.pop(sandbox_id)

        # Delete Pod outside the lock (K8s will handle cleanup)
        if pod_name:
            self._delete_pod(pod_name)

    def shutdown(self) -> None:
        """Shutdown all sandbox Pods managed by this provider.

        Releases all active sandboxes and deletes their Pods.

        This method is thread-safe and idempotent.
        """
        with self._lock:
            if self._shutdown_called:
                return
            self._shutdown_called = True
            sandbox_ids = list(self._sandboxes.keys())

        logger.info(f"Shutting down {len(sandbox_ids)} sandbox Pod(s)")

        # Release all active sandboxes (this will delete Pods)
        for sandbox_id in sandbox_ids:
            try:
                self.release(sandbox_id)
            except Exception as e:
                logger.error(f"Failed to release sandbox {sandbox_id} during shutdown: {e}")
