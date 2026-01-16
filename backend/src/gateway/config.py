import os

from pydantic import BaseModel, Field


class GatewayConfig(BaseModel):
    """Configuration for the API Gateway."""

    host: str = Field(default="0.0.0.0", description="Host to bind the gateway server")
    port: int = Field(default=8000, description="Port to bind the gateway server")
    langgraph_url: str = Field(default="http://localhost:2024", description="URL of the LangGraph server to proxy requests to")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"], description="Allowed CORS origins")
    proxy_timeout: float = Field(default=300.0, description="Timeout for proxy requests in seconds")
    stream_timeout: float = Field(default=600.0, description="Timeout for streaming requests in seconds")


_gateway_config: GatewayConfig | None = None


def get_gateway_config() -> GatewayConfig:
    """Get gateway config, loading from environment if available."""
    global _gateway_config
    if _gateway_config is None:
        cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        _gateway_config = GatewayConfig(
            host=os.getenv("GATEWAY_HOST", "0.0.0.0"),
            port=int(os.getenv("GATEWAY_PORT", "8000")),
            langgraph_url=os.getenv("LANGGRAPH_URL", "http://localhost:2024"),
            cors_origins=cors_origins_str.split(","),
            proxy_timeout=float(os.getenv("PROXY_TIMEOUT", "300")),
            stream_timeout=float(os.getenv("STREAM_TIMEOUT", "600")),
        )
    return _gateway_config
