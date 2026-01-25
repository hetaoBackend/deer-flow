from pydantic import BaseModel, ConfigDict, Field


class VolumeMountConfig(BaseModel):
    """Configuration for a volume mount."""

    host_path: str = Field(..., description="Path on the host machine")
    container_path: str = Field(..., description="Path inside the container")
    read_only: bool = Field(default=False, description="Whether the mount is read-only")


class SandboxConfig(BaseModel):
    """Config section for a sandbox.

    Common options:
        use: Class path of the sandbox provider (required)

    AioSandboxProvider specific options:
        image: Docker image to use (default: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest)
        port: Base port for sandbox containers (default: 8080)
        base_url: If set, uses existing sandbox instead of starting new container
        auto_start: Whether to automatically start Docker container (default: true)
        container_prefix: Prefix for container names (default: deer-flow-sandbox)
        idle_timeout: Idle timeout in seconds before sandbox is released (default: 600 = 10 minutes). Set to 0 to disable.
        mounts: List of volume mounts to share directories with the container
        environment: Environment variables to inject into the container (values starting with $ are resolved from host env)

    KubernetesSandboxProvider specific options:
        k8s_namespace: Kubernetes namespace (default: deer-flow)
        k8s_context: Optional kubeconfig context to use
        ttl_seconds: Pod cleanup TTL after release (default: 3600)
        cpu_request: CPU request (e.g., "100m")
        cpu_limit: CPU limit (e.g., "1000m")
        memory_request: Memory request (e.g., "256Mi")
        memory_limit: Memory limit (e.g., "1Gi")
    """

    use: str = Field(
        ...,
        description="Class path of the sandbox provider (e.g. src.sandbox.local:LocalSandboxProvider)",
    )
    image: str | None = Field(
        default=None,
        description="Docker image to use for the sandbox container",
    )
    port: int | None = Field(
        default=None,
        description="Base port for sandbox containers",
    )
    base_url: str | None = Field(
        default=None,
        description="If set, uses existing sandbox at this URL instead of starting new container",
    )
    auto_start: bool | None = Field(
        default=None,
        description="Whether to automatically start Docker container",
    )
    container_prefix: str | None = Field(
        default=None,
        description="Prefix for container names",
    )
    idle_timeout: int | None = Field(
        default=None,
        description="Idle timeout in seconds before sandbox is released (default: 600 = 10 minutes). Set to 0 to disable.",
    )
    mounts: list[VolumeMountConfig] = Field(
        default_factory=list,
        description="List of volume mounts to share directories between host and container",
    )
    environment: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to inject into the sandbox container. Values starting with $ will be resolved from host environment variables.",
    )

    # Kubernetes-specific configuration
    k8s_namespace: str | None = Field(
        default=None,
        description="Kubernetes namespace for sandbox Pods (KubernetesSandboxProvider only)",
    )
    k8s_context: str | None = Field(
        default=None,
        description="Kubeconfig context to use (KubernetesSandboxProvider only)",
    )
    ttl_seconds: int | None = Field(
        default=None,
        description="Pod cleanup TTL in seconds after release (KubernetesSandboxProvider only)",
    )
    cpu_request: str | None = Field(
        default=None,
        description="CPU request for Pod (e.g., '100m') (KubernetesSandboxProvider only)",
    )
    cpu_limit: str | None = Field(
        default=None,
        description="CPU limit for Pod (e.g., '1000m') (KubernetesSandboxProvider only)",
    )
    memory_request: str | None = Field(
        default=None,
        description="Memory request for Pod (e.g., '256Mi') (KubernetesSandboxProvider only)",
    )
    memory_limit: str | None = Field(
        default=None,
        description="Memory limit for Pod (e.g., '1Gi') (KubernetesSandboxProvider only)",
    )

    model_config = ConfigDict(extra="allow")
