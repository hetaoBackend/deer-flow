import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from deerflow.config.extensions_config import ExtensionsConfig, get_extensions_config, reload_extensions_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["mcp"])

_REDACTED_VALUE = "********"
_MCP_CONFIG_ADMIN_TOKEN_ENV = "DEER_FLOW_MCP_CONFIG_ADMIN_TOKEN"
_MCP_CONFIG_ALLOW_UNAUTH_ENV = "DEER_FLOW_MCP_CONFIG_ALLOW_UNAUTH"
_MCP_STDIO_ALLOWLIST_ENV = "DEER_FLOW_MCP_STDIO_COMMAND_ALLOWLIST"
_DEFAULT_STDIO_COMMAND_ALLOWLIST = {"npx", "uvx"}
_SENSITIVE_OAUTH_FIELDS = {"client_secret", "refresh_token"}


class McpOAuthConfigResponse(BaseModel):
    """OAuth configuration for an MCP server."""

    enabled: bool = Field(default=True, description="Whether OAuth token injection is enabled")
    token_url: str = Field(default="", description="OAuth token endpoint URL")
    grant_type: Literal["client_credentials", "refresh_token"] = Field(default="client_credentials", description="OAuth grant type")
    client_id: str | None = Field(default=None, description="OAuth client ID")
    client_secret: str | None = Field(default=None, description="OAuth client secret")
    refresh_token: str | None = Field(default=None, description="OAuth refresh token")
    scope: str | None = Field(default=None, description="OAuth scope")
    audience: str | None = Field(default=None, description="OAuth audience")
    token_field: str = Field(default="access_token", description="Token response field containing access token")
    token_type_field: str = Field(default="token_type", description="Token response field containing token type")
    expires_in_field: str = Field(default="expires_in", description="Token response field containing expires-in seconds")
    default_token_type: str = Field(default="Bearer", description="Default token type when response omits token_type")
    refresh_skew_seconds: int = Field(default=60, description="Refresh this many seconds before expiry")
    extra_token_params: dict[str, str] = Field(default_factory=dict, description="Additional form params sent to token endpoint")


class McpServerConfigResponse(BaseModel):
    """Response model for MCP server configuration."""

    enabled: bool = Field(default=True, description="Whether this MCP server is enabled")
    type: str = Field(default="stdio", description="Transport type: 'stdio', 'sse', or 'http'")
    command: str | None = Field(default=None, description="Command to execute to start the MCP server (for stdio type)")
    args: list[str] = Field(default_factory=list, description="Arguments to pass to the command (for stdio type)")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables for the MCP server")
    url: str | None = Field(default=None, description="URL of the MCP server (for sse or http type)")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers to send (for sse or http type)")
    oauth: McpOAuthConfigResponse | None = Field(default=None, description="OAuth configuration for MCP HTTP/SSE servers")
    description: str = Field(default="", description="Human-readable description of what this MCP server provides")


class McpConfigResponse(BaseModel):
    """Response model for MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        default_factory=dict,
        description="Map of MCP server name to configuration",
    )


class McpConfigUpdateRequest(BaseModel):
    """Request model for updating MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        ...,
        description="Map of MCP server name to configuration",
    )


def _require_mcp_config_admin(authorization: str | None = Header(default=None)) -> None:
    """Require a static bearer token unless unauthenticated config admin is explicitly enabled."""
    expected_token = os.getenv(_MCP_CONFIG_ADMIN_TOKEN_ENV)
    if expected_token and authorization == f"Bearer {expected_token}":
        return
    if not expected_token and os.getenv(_MCP_CONFIG_ALLOW_UNAUTH_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        return
    raise HTTPException(status_code=403, detail="MCP configuration admin token is required")


def _redact_mapping_values(values: dict[str, str]) -> dict[str, str]:
    return {key: _REDACTED_VALUE for key in values}


def _redact_oauth_config(oauth: dict | None) -> dict | None:
    if oauth is None:
        return None
    redacted = dict(oauth)
    for key in _SENSITIVE_OAUTH_FIELDS:
        if key in redacted and redacted[key] is not None:
            redacted[key] = _REDACTED_VALUE
    if isinstance(redacted.get("extra_token_params"), dict):
        redacted["extra_token_params"] = _redact_mapping_values(redacted["extra_token_params"])
    return redacted


def _server_response_payload(server) -> dict:
    payload = server.model_dump()
    if payload.get("env"):
        payload["env"] = _redact_mapping_values(payload["env"])
    if payload.get("headers"):
        payload["headers"] = _redact_mapping_values(payload["headers"])
    payload["oauth"] = _redact_oauth_config(payload.get("oauth"))
    return payload


def _build_mcp_config_response(config) -> McpConfigResponse:
    return McpConfigResponse(
        mcp_servers={
            name: McpServerConfigResponse(**_server_response_payload(server))
            for name, server in config.mcp_servers.items()
        },
    )


def _load_raw_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        try:
            loaded = json.load(f)
        except json.JSONDecodeError:
            return {}
    return loaded if isinstance(loaded, dict) else {}


def _has_redacted_mapping_values(values: dict | None) -> bool:
    return isinstance(values, dict) and any(value == _REDACTED_VALUE for value in values.values())


def _has_redacted_oauth_values(oauth: dict | None) -> bool:
    if not isinstance(oauth, dict):
        return False
    if any(oauth.get(key) == _REDACTED_VALUE for key in _SENSITIVE_OAUTH_FIELDS):
        return True
    return _has_redacted_mapping_values(oauth.get("extra_token_params"))


def _require_redacted_boundary_unchanged(name: str, server_data: dict, existing_server: dict, *, secret_type: str) -> None:
    if not isinstance(existing_server, dict) or not existing_server:
        raise HTTPException(
            status_code=400,
            detail=f"Redacted MCP {secret_type} values for '{name}' require an existing server configuration",
        )

    new_type = server_data.get("type") or "stdio"
    existing_type = existing_server.get("type") or "stdio"
    if new_type != existing_type:
        raise HTTPException(
            status_code=400,
            detail=f"Redacted MCP {secret_type} values for '{name}' cannot be reused after changing server type",
        )

    if new_type == "stdio":
        command_changed = server_data.get("command") != existing_server.get("command")
        args_changed = (server_data.get("args") or []) != (existing_server.get("args") or [])
        if command_changed or args_changed:
            raise HTTPException(
                status_code=400,
                detail=f"Redacted MCP {secret_type} values for '{name}' cannot be reused after changing command or args",
            )
        return

    if server_data.get("url") != existing_server.get("url"):
        raise HTTPException(
            status_code=400,
            detail=f"Redacted MCP {secret_type} values for '{name}' cannot be reused after changing url",
        )


def _require_oauth_redacted_boundary_unchanged(name: str, server_data: dict, existing_server: dict) -> None:
    _require_redacted_boundary_unchanged(name, server_data, existing_server, secret_type="OAuth")
    new_oauth = server_data.get("oauth") if isinstance(server_data.get("oauth"), dict) else {}
    existing_oauth = existing_server.get("oauth") if isinstance(existing_server.get("oauth"), dict) else {}
    for key in ("token_url", "grant_type", "client_id"):
        new_value = new_oauth.get(key)
        existing_value = existing_oauth.get(key)
        if key == "grant_type":
            new_value = new_value or "client_credentials"
            existing_value = existing_value or "client_credentials"
        if new_value != existing_value:
            raise HTTPException(
                status_code=400,
                detail=f"Redacted MCP OAuth values for '{name}' cannot be reused after changing oauth.{key}",
            )


def _restore_redacted_mapping(
    new_values: dict[str, str],
    existing_values: dict | None,
    *,
    name: str,
    secret_type: str,
) -> dict[str, str]:
    if not isinstance(existing_values, dict):
        existing_values = {}
    restored = dict(new_values)
    for key, value in list(restored.items()):
        if value != _REDACTED_VALUE:
            continue
        if key not in existing_values:
            raise HTTPException(
                status_code=400,
                detail=f"Redacted MCP {secret_type} value for '{name}' has no existing value for key '{key}'",
            )
        restored[key] = existing_values[key]
    return restored


def _restore_redacted_oauth(new_oauth: dict | None, existing_oauth: dict | None, *, name: str) -> dict | None:
    if new_oauth is None:
        return None
    if not isinstance(existing_oauth, dict):
        existing_oauth = {}
    restored = dict(new_oauth)
    for key in _SENSITIVE_OAUTH_FIELDS:
        if restored.get(key) != _REDACTED_VALUE:
            continue
        if key not in existing_oauth:
            raise HTTPException(
                status_code=400,
                detail=f"Redacted MCP OAuth value for '{name}' has no existing value for key '{key}'",
            )
        restored[key] = existing_oauth[key]
    if isinstance(restored.get("extra_token_params"), dict):
        existing_params = existing_oauth.get("extra_token_params") if isinstance(existing_oauth, dict) else {}
        restored["extra_token_params"] = _restore_redacted_mapping(
            restored["extra_token_params"],
            existing_params,
            name=name,
            secret_type="OAuth extra token parameter",
        )
    return restored


def _restore_redacted_mcp_values(config_data: dict, existing_raw_config: dict) -> None:
    existing_servers = existing_raw_config.get("mcpServers")
    if not isinstance(existing_servers, dict):
        existing_servers = {}

    for name, server_data in config_data.get("mcpServers", {}).items():
        existing_server = existing_servers.get(name)
        if not isinstance(existing_server, dict):
            existing_server = {}
        if _has_redacted_mapping_values(server_data.get("env")):
            _require_redacted_boundary_unchanged(name, server_data, existing_server, secret_type="environment")
        if _has_redacted_mapping_values(server_data.get("headers")):
            _require_redacted_boundary_unchanged(name, server_data, existing_server, secret_type="header")
        if _has_redacted_oauth_values(server_data.get("oauth")):
            _require_oauth_redacted_boundary_unchanged(name, server_data, existing_server)
        if isinstance(server_data.get("env"), dict):
            server_data["env"] = _restore_redacted_mapping(
                server_data["env"],
                existing_server.get("env"),
                name=name,
                secret_type="environment",
            )
        if isinstance(server_data.get("headers"), dict):
            server_data["headers"] = _restore_redacted_mapping(
                server_data["headers"],
                existing_server.get("headers"),
                name=name,
                secret_type="header",
            )
        if isinstance(server_data.get("oauth"), dict):
            server_data["oauth"] = _restore_redacted_oauth(
                server_data["oauth"],
                existing_server.get("oauth"),
                name=name,
            )


def _stdio_command_allowlist() -> set[str]:
    raw = os.getenv(_MCP_STDIO_ALLOWLIST_ENV)
    if raw is None:
        return set(_DEFAULT_STDIO_COMMAND_ALLOWLIST)
    return {item.strip() for item in raw.split(",") if item.strip() and "/" not in item and "\\" not in item}


def _validate_mcp_server_config(name: str, server: McpServerConfigResponse) -> None:
    if server.type not in {"stdio", "sse", "http"}:
        raise HTTPException(status_code=400, detail=f"Unsupported MCP server type for '{name}': {server.type}")

    if server.type == "stdio":
        if not server.command:
            raise HTTPException(status_code=400, detail=f"MCP stdio server '{name}' requires a command")
        command_name = server.command
        if "/" in command_name or "\\" in command_name or command_name in {".", ".."}:
            raise HTTPException(
                status_code=400,
                detail=f"MCP stdio command for '{name}' must be a bare executable name",
            )
        allowed = _stdio_command_allowlist()
        if command_name not in allowed:
            allowed_text = ", ".join(sorted(allowed)) or "(none)"
            raise HTTPException(
                status_code=400,
                detail=f"MCP stdio command for '{name}' is not allowed: {command_name}. Allowed commands: {allowed_text}",
            )
        return

    if not server.url:
        raise HTTPException(status_code=400, detail=f"MCP {server.type} server '{name}' requires a url")
    if not (server.url.startswith("http://") or server.url.startswith("https://")):
        raise HTTPException(status_code=400, detail=f"MCP server '{name}' url must use http:// or https://")


def _write_json_atomic(config_path: Path, config_data: dict) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=config_path.parent, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        os.chmod(tmp_path, 0o600)
        json.dump(config_data, tmp, indent=2)
        tmp.write("\n")
        tmp.flush()
        os.fsync(tmp.fileno())
    os.replace(tmp_path, config_path)
    os.chmod(config_path, 0o600)


@router.get(
    "/mcp/config",
    response_model=McpConfigResponse,
    summary="Get MCP Configuration",
    description="Retrieve the current Model Context Protocol (MCP) server configurations.",
    dependencies=[Depends(_require_mcp_config_admin)],
)
async def get_mcp_configuration() -> McpConfigResponse:
    """Get the current MCP configuration.

    Returns:
        The current MCP configuration with all servers.

    Example:
        ```json
        {
            "mcp_servers": {
                "github": {
                    "enabled": true,
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": "ghp_xxx"},
                    "description": "GitHub MCP server for repository operations"
                }
            }
        }
        ```
    """
    config = get_extensions_config()

    return _build_mcp_config_response(config)


@router.put(
    "/mcp/config",
    response_model=McpConfigResponse,
    summary="Update MCP Configuration",
    description="Update Model Context Protocol (MCP) server configurations and save to file.",
    dependencies=[Depends(_require_mcp_config_admin)],
)
async def update_mcp_configuration(request: McpConfigUpdateRequest) -> McpConfigResponse:
    """Update the MCP configuration.

    This will:
    1. Save the new configuration to the mcp_config.json file
    2. Reload the configuration cache
    3. Reset MCP tools cache to trigger reinitialization

    Args:
        request: The new MCP configuration to save.

    Returns:
        The updated MCP configuration.

    Raises:
        HTTPException: 500 if the configuration file cannot be written.

    Example Request:
        ```json
        {
            "mcp_servers": {
                "github": {
                    "enabled": true,
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"},
                    "description": "GitHub MCP server for repository operations"
                }
            }
        }
        ```
    """
    try:
        # Get the current config path (or determine where to save it)
        config_path = ExtensionsConfig.resolve_config_path()

        # If no config file exists, create one in the parent directory (project root)
        if config_path is None:
            config_path = Path.cwd().parent / "extensions_config.json"
            logger.info(f"No existing extensions config found. Creating new config at: {config_path}")

        # Load current config to preserve skills configuration
        current_config = get_extensions_config()
        existing_raw_config = _load_raw_config(config_path)

        for name, server in request.mcp_servers.items():
            _validate_mcp_server_config(name, server)

        # Convert request to dict format for JSON serialization
        config_data = {
            "mcpServers": {name: server.model_dump() for name, server in request.mcp_servers.items()},
            "skills": {name: {"enabled": skill.enabled} for name, skill in current_config.skills.items()},
        }
        _restore_redacted_mcp_values(config_data, existing_raw_config)

        # Write the configuration to file
        _write_json_atomic(config_path, config_data)

        logger.info(f"MCP configuration updated and saved to: {config_path}")

        # NOTE: No need to reload/reset cache here - LangGraph Server (separate process)
        # will detect config file changes via mtime and reinitialize MCP tools automatically

        # Reload the configuration and update the global cache
        reloaded_config = reload_extensions_config()
        return _build_mcp_config_response(reloaded_config)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update MCP configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update MCP configuration: {str(e)}")
