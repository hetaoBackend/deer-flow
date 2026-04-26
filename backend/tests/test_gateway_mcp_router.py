import asyncio
import json
import stat
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.gateway.routers import mcp
from deerflow.config.extensions_config import ExtensionsConfig, McpOAuthConfig, McpServerConfig


def test_get_mcp_configuration_redacts_sensitive_values(monkeypatch) -> None:
    config = ExtensionsConfig(
        mcp_servers={
            "secure": McpServerConfig(
                enabled=True,
                type="http",
                url="https://mcp.example.test",
                env={"TOKEN": "raw-token"},
                headers={"Authorization": "Bearer raw-token"},
                oauth=McpOAuthConfig(
                    token_url="https://auth.example.test/token",
                    client_id="client-id",
                    client_secret="client-secret",
                    refresh_token="refresh-token",
                    extra_token_params={"audience_secret": "secret"},
                ),
            )
        },
        skills={},
    )
    monkeypatch.setattr(mcp, "get_extensions_config", lambda: config)

    response = asyncio.run(mcp.get_mcp_configuration())
    server = response.mcp_servers["secure"]

    assert server.env == {"TOKEN": mcp._REDACTED_VALUE}
    assert server.headers == {"Authorization": mcp._REDACTED_VALUE}
    assert server.oauth is not None
    assert server.oauth.client_id == "client-id"
    assert server.oauth.client_secret == mcp._REDACTED_VALUE
    assert server.oauth.refresh_token == mcp._REDACTED_VALUE
    assert server.oauth.extra_token_params == {"audience_secret": mcp._REDACTED_VALUE}


def test_get_mcp_configuration_redacts_empty_oauth_secrets(monkeypatch) -> None:
    config = ExtensionsConfig(
        mcp_servers={
            "secure": McpServerConfig(
                enabled=True,
                type="http",
                url="https://mcp.example.test",
                oauth=McpOAuthConfig(
                    token_url="https://auth.example.test/token",
                    client_secret="",
                    refresh_token="",
                ),
            )
        },
        skills={},
    )
    monkeypatch.setattr(mcp, "get_extensions_config", lambda: config)

    response = asyncio.run(mcp.get_mcp_configuration())
    oauth = response.mcp_servers["secure"].oauth

    assert oauth is not None
    assert oauth.client_secret == mcp._REDACTED_VALUE
    assert oauth.refresh_token == mcp._REDACTED_VALUE


def test_update_mcp_configuration_preserves_redacted_existing_values(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "extensions_config.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "secure": {
                        "enabled": True,
                        "type": "http",
                        "url": "https://mcp.example.test",
                        "env": {"TOKEN": "$MCP_TOKEN"},
                        "headers": {"Authorization": "$MCP_AUTH_HEADER"},
                        "oauth": {
                            "token_url": "https://auth.example.test/token",
                            "client_id": "client-id",
                            "client_secret": "$MCP_CLIENT_SECRET",
                            "refresh_token": "$MCP_REFRESH_TOKEN",
                            "extra_token_params": {"audience": "$MCP_AUDIENCE"},
                        },
                    }
                },
                "skills": {},
            }
        ),
        encoding="utf-8",
    )
    current_config = ExtensionsConfig(mcp_servers={}, skills={})
    reloaded_config = ExtensionsConfig(
        mcp_servers={
            "secure": McpServerConfig(
                enabled=True,
                type="http",
                url="https://mcp.example.test",
                env={"TOKEN": "resolved-token"},
                headers={"Authorization": "resolved-header"},
                oauth=McpOAuthConfig(
                    token_url="https://auth.example.test/token",
                    client_id="client-id",
                    client_secret="resolved-secret",
                    refresh_token="resolved-refresh",
                    extra_token_params={"audience": "resolved-audience"},
                ),
            )
        },
        skills={},
    )
    request = mcp.McpConfigUpdateRequest(
        mcp_servers={
            "secure": mcp.McpServerConfigResponse(
                enabled=True,
                type="http",
                url="https://mcp.example.test",
                env={"TOKEN": mcp._REDACTED_VALUE},
                headers={"Authorization": mcp._REDACTED_VALUE},
                oauth=mcp.McpOAuthConfigResponse(
                    token_url="https://auth.example.test/token",
                    client_id="client-id",
                    client_secret=mcp._REDACTED_VALUE,
                    refresh_token=mcp._REDACTED_VALUE,
                    extra_token_params={"audience": mcp._REDACTED_VALUE},
                ),
            )
        }
    )

    with (
        patch.object(mcp.ExtensionsConfig, "resolve_config_path", return_value=config_path),
        patch.object(mcp, "get_extensions_config", return_value=current_config),
        patch.object(mcp, "reload_extensions_config", return_value=reloaded_config),
    ):
        response = asyncio.run(mcp.update_mcp_configuration(request))

    written = json.loads(config_path.read_text(encoding="utf-8"))
    server = written["mcpServers"]["secure"]
    assert server["env"]["TOKEN"] == "$MCP_TOKEN"
    assert server["headers"]["Authorization"] == "$MCP_AUTH_HEADER"
    assert server["oauth"]["client_secret"] == "$MCP_CLIENT_SECRET"
    assert server["oauth"]["refresh_token"] == "$MCP_REFRESH_TOKEN"
    assert server["oauth"]["extra_token_params"]["audience"] == "$MCP_AUDIENCE"
    assert response.mcp_servers["secure"].env == {"TOKEN": mcp._REDACTED_VALUE}


def test_update_mcp_configuration_writes_restrictive_permissions(tmp_path) -> None:
    config_path = tmp_path / "extensions_config.json"
    config_path.write_text(json.dumps({"mcpServers": {}, "skills": {}}), encoding="utf-8")
    request = mcp.McpConfigUpdateRequest(
        mcp_servers={
            "local": mcp.McpServerConfigResponse(
                enabled=True,
                type="stdio",
                command="npx",
                args=["-y", "@example/server"],
            )
        }
    )
    reloaded_config = ExtensionsConfig(
        mcp_servers={
            "local": McpServerConfig(
                enabled=True,
                type="stdio",
                command="npx",
                args=["-y", "@example/server"],
            )
        },
        skills={},
    )

    with (
        patch.object(mcp.ExtensionsConfig, "resolve_config_path", return_value=config_path),
        patch.object(mcp, "get_extensions_config", return_value=ExtensionsConfig(mcp_servers={}, skills={})),
        patch.object(mcp, "reload_extensions_config", return_value=reloaded_config),
    ):
        asyncio.run(mcp.update_mcp_configuration(request))

    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600


def test_update_mcp_configuration_rejects_invalid_oauth_before_write(tmp_path) -> None:
    config_path = tmp_path / "extensions_config.json"
    original = {"mcpServers": {}, "skills": {}}
    config_path.write_text(json.dumps(original), encoding="utf-8")
    request = mcp.McpConfigUpdateRequest(
        mcp_servers={
            "secure": mcp.McpServerConfigResponse(
                enabled=True,
                type="http",
                url="https://mcp.example.test",
                oauth=mcp.McpOAuthConfigResponse(token_url=""),
            )
        }
    )

    with (
        patch.object(mcp.ExtensionsConfig, "resolve_config_path", return_value=config_path),
        patch.object(mcp, "get_extensions_config", return_value=ExtensionsConfig(mcp_servers={}, skills={})),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mcp.update_mcp_configuration(request))

    assert exc.value.status_code == 400
    assert "oauth.token_url" in str(exc.value.detail)
    assert json.loads(config_path.read_text(encoding="utf-8")) == original


def test_update_mcp_configuration_enforces_http_host_allowlist(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "extensions_config.json"
    config_path.write_text(json.dumps({"mcpServers": {}, "skills": {}}), encoding="utf-8")
    monkeypatch.setenv(mcp._MCP_HTTP_ALLOWED_HOSTS_ENV, "mcp.example.test,*.trusted.test")
    request = mcp.McpConfigUpdateRequest(
        mcp_servers={
            "secure": mcp.McpServerConfigResponse(
                enabled=True,
                type="http",
                url="https://evil.example.test",
            )
        }
    )

    with (
        patch.object(mcp.ExtensionsConfig, "resolve_config_path", return_value=config_path),
        patch.object(mcp, "get_extensions_config", return_value=ExtensionsConfig(mcp_servers={}, skills={})),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mcp.update_mcp_configuration(request))

    assert exc.value.status_code == 400
    assert "host is not allowed" in str(exc.value.detail)


def test_update_mcp_configuration_rejects_redacted_values_after_url_change(tmp_path) -> None:
    config_path = tmp_path / "extensions_config.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "secure": {
                        "enabled": True,
                        "type": "http",
                        "url": "https://mcp.example.test",
                        "headers": {"Authorization": "$MCP_AUTH_HEADER"},
                    }
                },
                "skills": {},
            }
        ),
        encoding="utf-8",
    )
    request = mcp.McpConfigUpdateRequest(
        mcp_servers={
            "secure": mcp.McpServerConfigResponse(
                enabled=True,
                type="http",
                url="https://evil.example.test",
                headers={"Authorization": mcp._REDACTED_VALUE},
            )
        }
    )

    with (
        patch.object(mcp.ExtensionsConfig, "resolve_config_path", return_value=config_path),
        patch.object(mcp, "get_extensions_config", return_value=ExtensionsConfig(mcp_servers={}, skills={})),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mcp.update_mcp_configuration(request))

    assert exc.value.status_code == 400
    assert "changing url" in str(exc.value.detail)


def test_update_mcp_configuration_rejects_redacted_oauth_after_token_url_change(tmp_path) -> None:
    config_path = tmp_path / "extensions_config.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "secure": {
                        "enabled": True,
                        "type": "http",
                        "url": "https://mcp.example.test",
                        "oauth": {
                            "token_url": "https://auth.example.test/token",
                            "client_id": "client-id",
                            "client_secret": "$MCP_CLIENT_SECRET",
                        },
                    }
                },
                "skills": {},
            }
        ),
        encoding="utf-8",
    )
    request = mcp.McpConfigUpdateRequest(
        mcp_servers={
            "secure": mcp.McpServerConfigResponse(
                enabled=True,
                type="http",
                url="https://mcp.example.test",
                oauth=mcp.McpOAuthConfigResponse(
                    token_url="https://evil.example.test/token",
                    client_id="client-id",
                    client_secret=mcp._REDACTED_VALUE,
                ),
            )
        }
    )

    with (
        patch.object(mcp.ExtensionsConfig, "resolve_config_path", return_value=config_path),
        patch.object(mcp, "get_extensions_config", return_value=ExtensionsConfig(mcp_servers={}, skills={})),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mcp.update_mcp_configuration(request))

    assert exc.value.status_code == 400
    assert "oauth.token_url" in str(exc.value.detail)


def test_update_mcp_configuration_rejects_redacted_stdio_env_after_args_change(tmp_path) -> None:
    config_path = tmp_path / "extensions_config.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "local": {
                        "enabled": True,
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "@example/old-server"],
                        "env": {"TOKEN": "$MCP_TOKEN"},
                    }
                },
                "skills": {},
            }
        ),
        encoding="utf-8",
    )
    request = mcp.McpConfigUpdateRequest(
        mcp_servers={
            "local": mcp.McpServerConfigResponse(
                enabled=True,
                type="stdio",
                command="npx",
                args=["-y", "@example/new-server"],
                env={"TOKEN": mcp._REDACTED_VALUE},
            )
        }
    )

    with (
        patch.object(mcp.ExtensionsConfig, "resolve_config_path", return_value=config_path),
        patch.object(mcp, "get_extensions_config", return_value=ExtensionsConfig(mcp_servers={}, skills={})),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mcp.update_mcp_configuration(request))

    assert exc.value.status_code == 400
    assert "changing command or args" in str(exc.value.detail)


def test_update_mcp_configuration_rejects_disallowed_stdio_command(tmp_path) -> None:
    config_path = tmp_path / "extensions_config.json"
    config_path.write_text(json.dumps({"mcpServers": {}, "skills": {}}), encoding="utf-8")
    request = mcp.McpConfigUpdateRequest(
        mcp_servers={
            "shell": mcp.McpServerConfigResponse(
                enabled=True,
                type="stdio",
                command="/bin/sh",
            )
        }
    )

    with (
        patch.object(mcp.ExtensionsConfig, "resolve_config_path", return_value=config_path),
        patch.object(mcp, "get_extensions_config", return_value=ExtensionsConfig(mcp_servers={}, skills={})),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mcp.update_mcp_configuration(request))

    assert exc.value.status_code == 400
    assert "bare executable" in str(exc.value.detail)


def test_update_mcp_configuration_rejects_default_python_stdio_command(tmp_path) -> None:
    config_path = tmp_path / "extensions_config.json"
    config_path.write_text(json.dumps({"mcpServers": {}, "skills": {}}), encoding="utf-8")
    request = mcp.McpConfigUpdateRequest(
        mcp_servers={
            "python": mcp.McpServerConfigResponse(
                enabled=True,
                type="stdio",
                command="python",
            )
        }
    )

    with (
        patch.object(mcp.ExtensionsConfig, "resolve_config_path", return_value=config_path),
        patch.object(mcp, "get_extensions_config", return_value=ExtensionsConfig(mcp_servers={}, skills={})),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(mcp.update_mcp_configuration(request))

    assert exc.value.status_code == 400
    assert "not allowed" in str(exc.value.detail)


def test_mcp_config_admin_token_fails_closed_unless_explicitly_allowed(monkeypatch) -> None:
    monkeypatch.delenv(mcp._MCP_CONFIG_ADMIN_TOKEN_ENV, raising=False)
    monkeypatch.delenv(mcp._MCP_CONFIG_ALLOW_UNAUTH_ENV, raising=False)
    with pytest.raises(HTTPException) as exc:
        mcp._require_mcp_config_admin(None)
    assert exc.value.status_code == 403

    monkeypatch.setenv(mcp._MCP_CONFIG_ALLOW_UNAUTH_ENV, "true")
    mcp._require_mcp_config_admin(None)

    monkeypatch.setenv(mcp._MCP_CONFIG_ADMIN_TOKEN_ENV, "secret-token")
    with pytest.raises(HTTPException) as exc:
        mcp._require_mcp_config_admin(None)
    assert exc.value.status_code == 403

    mcp._require_mcp_config_admin("  bearer   secret-token  ")

    mcp._require_mcp_config_admin("Bearer secret-token")
