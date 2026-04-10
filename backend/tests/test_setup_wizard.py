"""Unit tests for the Setup Wizard (scripts/wizard/).

Run from repo root:
    cd backend && uv run pytest tests/test_setup_wizard.py -v
"""

from __future__ import annotations

import yaml
from wizard.providers import LLM_PROVIDERS, SEARCH_PROVIDERS
from wizard.writer import (
    build_minimal_config,
    read_env_file,
    write_config_yaml,
    write_env_file,
)


class TestProviders:
    def test_llm_providers_not_empty(self):
        assert len(LLM_PROVIDERS) >= 4

    def test_llm_providers_have_required_fields(self):
        for p in LLM_PROVIDERS:
            assert p.name
            assert p.display_name
            assert p.use
            assert ":" in p.use, f"Provider '{p.name}' use path must contain ':'"
            assert p.env_var
            assert p.package
            assert p.models
            assert p.default_model in p.models

    def test_search_providers_have_required_fields(self):
        for sp in SEARCH_PROVIDERS:
            assert sp.name
            assert sp.display_name
            assert sp.use
            assert ":" in sp.use

    def test_at_least_one_free_search_provider(self):
        """At least one search provider needs no API key."""
        free = [sp for sp in SEARCH_PROVIDERS if sp.env_var is None]
        assert free, "Expected at least one free (no-key) search provider"


class TestBuildMinimalConfig:
    def test_produces_valid_yaml(self):
        content = build_minimal_config(
            provider_use="langchain_openai:ChatOpenAI",
            model_name="gpt-4o",
            display_name="OpenAI / gpt-4o",
            api_key_field="api_key",
            env_var="OPENAI_API_KEY",
        )
        data = yaml.safe_load(content)
        assert data is not None
        assert "models" in data
        assert len(data["models"]) == 1
        model = data["models"][0]
        assert model["name"] == "default"
        assert model["use"] == "langchain_openai:ChatOpenAI"
        assert model["model"] == "gpt-4o"
        assert model["api_key"] == "$OPENAI_API_KEY"

    def test_gemini_uses_gemini_api_key_field(self):
        content = build_minimal_config(
            provider_use="langchain_google_genai:ChatGoogleGenerativeAI",
            model_name="gemini-2.0-flash",
            display_name="Gemini",
            api_key_field="gemini_api_key",
            env_var="GEMINI_API_KEY",
        )
        data = yaml.safe_load(content)
        model = data["models"][0]
        assert "gemini_api_key" in model
        assert model["gemini_api_key"] == "$GEMINI_API_KEY"
        assert "api_key" not in model

    def test_search_tool_included(self):
        content = build_minimal_config(
            provider_use="langchain_openai:ChatOpenAI",
            model_name="gpt-4o",
            display_name="OpenAI",
            api_key_field="api_key",
            env_var="OPENAI_API_KEY",
            search_use="deerflow.community.tavily.tools:web_search_tool",
        )
        data = yaml.safe_load(content)
        tool_names = [t["name"] for t in data.get("tools", [])]
        assert "web_search" in tool_names

    def test_no_search_tool_when_not_configured(self):
        content = build_minimal_config(
            provider_use="langchain_openai:ChatOpenAI",
            model_name="gpt-4o",
            display_name="OpenAI",
            api_key_field="api_key",
            env_var="OPENAI_API_KEY",
        )
        data = yaml.safe_load(content)
        tool_names = [t["name"] for t in data.get("tools", [])]
        assert "web_search" not in tool_names

    def test_sandbox_included(self):
        content = build_minimal_config(
            provider_use="langchain_openai:ChatOpenAI",
            model_name="gpt-4o",
            display_name="OpenAI",
            api_key_field="api_key",
            env_var="OPENAI_API_KEY",
        )
        data = yaml.safe_load(content)
        assert "sandbox" in data
        assert "use" in data["sandbox"]
        assert data["sandbox"]["use"] == "deerflow.sandbox.local:LocalSandboxProvider"
        assert data["sandbox"]["allow_host_bash"] is False

    def test_bash_tool_disabled_by_default(self):
        content = build_minimal_config(
            provider_use="langchain_openai:ChatOpenAI",
            model_name="gpt-4o",
            display_name="OpenAI",
            api_key_field="api_key",
            env_var="OPENAI_API_KEY",
        )
        data = yaml.safe_load(content)
        tool_names = [t["name"] for t in data.get("tools", [])]
        assert "bash" not in tool_names

    def test_can_enable_container_sandbox_and_bash(self):
        content = build_minimal_config(
            provider_use="langchain_openai:ChatOpenAI",
            model_name="gpt-4o",
            display_name="OpenAI",
            api_key_field="api_key",
            env_var="OPENAI_API_KEY",
            sandbox_use="deerflow.community.aio_sandbox:AioSandboxProvider",
            include_bash_tool=True,
        )
        data = yaml.safe_load(content)
        assert data["sandbox"]["use"] == "deerflow.community.aio_sandbox:AioSandboxProvider"
        assert "allow_host_bash" not in data["sandbox"]
        tool_names = [t["name"] for t in data.get("tools", [])]
        assert "bash" in tool_names

    def test_can_disable_write_tools(self):
        content = build_minimal_config(
            provider_use="langchain_openai:ChatOpenAI",
            model_name="gpt-4o",
            display_name="OpenAI",
            api_key_field="api_key",
            env_var="OPENAI_API_KEY",
            include_write_tools=False,
        )
        data = yaml.safe_load(content)
        tool_names = [t["name"] for t in data.get("tools", [])]
        assert "write_file" not in tool_names
        assert "str_replace" not in tool_names

    def test_config_version_present(self):
        content = build_minimal_config(
            provider_use="langchain_openai:ChatOpenAI",
            model_name="gpt-4o",
            display_name="OpenAI",
            api_key_field="api_key",
            env_var="OPENAI_API_KEY",
            config_version=5,
        )
        data = yaml.safe_load(content)
        assert data["config_version"] == 5


# ---------------------------------------------------------------------------
# writer.py — env file helpers
# ---------------------------------------------------------------------------


class TestEnvFileHelpers:
    def test_write_and_read_new_file(self, tmp_path):
        env_file = tmp_path / ".env"
        write_env_file(env_file, {"OPENAI_API_KEY": "sk-test123"})
        pairs = read_env_file(env_file)
        assert pairs["OPENAI_API_KEY"] == "sk-test123"

    def test_update_existing_key(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=old-key\n")
        write_env_file(env_file, {"OPENAI_API_KEY": "new-key"})
        pairs = read_env_file(env_file)
        assert pairs["OPENAI_API_KEY"] == "new-key"
        # Should not duplicate
        content = env_file.read_text()
        assert content.count("OPENAI_API_KEY") == 1

    def test_preserve_existing_keys(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("TAVILY_API_KEY=tavily-val\n")
        write_env_file(env_file, {"OPENAI_API_KEY": "sk-new"})
        pairs = read_env_file(env_file)
        assert pairs["TAVILY_API_KEY"] == "tavily-val"
        assert pairs["OPENAI_API_KEY"] == "sk-new"

    def test_preserve_comments(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# My .env file\nOPENAI_API_KEY=old\n")
        write_env_file(env_file, {"OPENAI_API_KEY": "new"})
        content = env_file.read_text()
        assert "# My .env file" in content

    def test_read_ignores_comments(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\nKEY=value\n")
        pairs = read_env_file(env_file)
        assert "# comment" not in pairs
        assert pairs["KEY"] == "value"


# ---------------------------------------------------------------------------
# writer.py — write_config_yaml
# ---------------------------------------------------------------------------


class TestWriteConfigYaml:
    def test_generated_config_loadable_by_appconfig(self, tmp_path):
        """The generated config.yaml must be parseable (basic YAML validity)."""

        config_path = tmp_path / "config.yaml"
        write_config_yaml(
            config_path,
            provider_use="langchain_openai:ChatOpenAI",
            model_name="gpt-4o",
            display_name="OpenAI / gpt-4o",
            api_key_field="api_key",
            env_var="OPENAI_API_KEY",
        )
        assert config_path.exists()
        with open(config_path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "models" in data

    def test_config_version_read_from_example(self, tmp_path):
        """write_config_yaml should read config_version from config.example.yaml if present."""

        example_path = tmp_path / "config.example.yaml"
        example_path.write_text("config_version: 99\n")

        config_path = tmp_path / "config.yaml"
        write_config_yaml(
            config_path,
            provider_use="langchain_openai:ChatOpenAI",
            model_name="gpt-4o",
            display_name="OpenAI",
            api_key_field="api_key",
            env_var="OPENAI_API_KEY",
        )
        with open(config_path) as f:
            data = yaml.safe_load(f)
        assert data["config_version"] == 99
