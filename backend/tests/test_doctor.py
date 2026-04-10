"""Unit tests for scripts/doctor.py.

Run from repo root:
    cd backend && uv run pytest tests/test_doctor.py -v
"""

from __future__ import annotations

import sys

import doctor

# ---------------------------------------------------------------------------
# check_python
# ---------------------------------------------------------------------------


class TestCheckPython:
    def test_current_python_passes(self):
        result = doctor.check_python()
        assert sys.version_info >= (3, 12)
        assert result.status == "ok"


# ---------------------------------------------------------------------------
# check_config_exists
# ---------------------------------------------------------------------------


class TestCheckConfigExists:
    def test_missing_config(self, tmp_path):
        result = doctor.check_config_exists(tmp_path / "config.yaml")
        assert result.status == "fail"
        assert result.fix is not None

    def test_present_config(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("config_version: 5\n")
        result = doctor.check_config_exists(cfg)
        assert result.status == "ok"


# ---------------------------------------------------------------------------
# check_config_version
# ---------------------------------------------------------------------------


class TestCheckConfigVersion:
    def test_up_to_date(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("config_version: 5\n")
        example = tmp_path / "config.example.yaml"
        example.write_text("config_version: 5\n")
        result = doctor.check_config_version(cfg, tmp_path)
        assert result.status == "ok"

    def test_outdated(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("config_version: 3\n")
        example = tmp_path / "config.example.yaml"
        example.write_text("config_version: 5\n")
        result = doctor.check_config_version(cfg, tmp_path)
        assert result.status == "warn"
        assert result.fix is not None

    def test_missing_config_skipped(self, tmp_path):
        result = doctor.check_config_version(tmp_path / "config.yaml", tmp_path)
        assert result.status == "skip"


# ---------------------------------------------------------------------------
# check_models_configured
# ---------------------------------------------------------------------------


class TestCheckModelsConfigured:
    def test_no_models(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("config_version: 5\nmodels: []\n")
        result = doctor.check_models_configured(cfg)
        assert result.status == "fail"

    def test_one_model(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("config_version: 5\nmodels:\n  - name: default\n    use: langchain_openai:ChatOpenAI\n    model: gpt-4o\n    api_key: $OPENAI_API_KEY\n")
        result = doctor.check_models_configured(cfg)
        assert result.status == "ok"

    def test_missing_config_skipped(self, tmp_path):
        result = doctor.check_models_configured(tmp_path / "config.yaml")
        assert result.status == "skip"


# ---------------------------------------------------------------------------
# check_llm_api_key
# ---------------------------------------------------------------------------


class TestCheckLLMApiKey:
    def test_key_set(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("config_version: 5\nmodels:\n  - name: default\n    use: langchain_openai:ChatOpenAI\n    model: gpt-4o\n    api_key: $OPENAI_API_KEY\n")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        results = doctor.check_llm_api_key(cfg)
        assert any(r.status == "ok" for r in results)
        assert all(r.status != "fail" for r in results)

    def test_key_missing(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("config_version: 5\nmodels:\n  - name: default\n    use: langchain_openai:ChatOpenAI\n    model: gpt-4o\n    api_key: $OPENAI_API_KEY\n")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        results = doctor.check_llm_api_key(cfg)
        assert any(r.status == "fail" for r in results)
        failed = [r for r in results if r.status == "fail"]
        assert all(r.fix is not None for r in failed)
        assert any("OPENAI_API_KEY" in (r.fix or "") for r in failed)

    def test_missing_config_returns_empty(self, tmp_path):
        results = doctor.check_llm_api_key(tmp_path / "config.yaml")
        assert results == []


# ---------------------------------------------------------------------------
# check_web_search
# ---------------------------------------------------------------------------


class TestCheckWebSearch:
    def test_ddg_always_ok(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "config_version: 5\nmodels:\n  - name: default\n    use: langchain_openai:ChatOpenAI\n    model: gpt-4o\n    api_key: $OPENAI_API_KEY\ntools:\n  - name: web_search\n    use: deerflow.community.ddg_search.tools:web_search_tool\n"
        )
        result = doctor.check_web_search(cfg)
        assert result.status == "ok"
        assert "DuckDuckGo" in result.detail

    def test_tavily_with_key_ok(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
        cfg = tmp_path / "config.yaml"
        cfg.write_text("config_version: 5\ntools:\n  - name: web_search\n    use: deerflow.community.tavily.tools:web_search_tool\n")
        result = doctor.check_web_search(cfg)
        assert result.status == "ok"

    def test_tavily_without_key_warns(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        cfg = tmp_path / "config.yaml"
        cfg.write_text("config_version: 5\ntools:\n  - name: web_search\n    use: deerflow.community.tavily.tools:web_search_tool\n")
        result = doctor.check_web_search(cfg)
        assert result.status == "warn"
        assert result.fix is not None
        assert "make setup" in result.fix

    def test_no_search_tool_warns(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("config_version: 5\ntools: []\n")
        result = doctor.check_web_search(cfg)
        assert result.status == "warn"
        assert result.fix is not None
        assert "make setup" in result.fix

    def test_missing_config_skipped(self, tmp_path):
        result = doctor.check_web_search(tmp_path / "config.yaml")
        assert result.status == "skip"


# ---------------------------------------------------------------------------
# check_env_file
# ---------------------------------------------------------------------------


class TestCheckEnvFile:
    def test_missing(self, tmp_path):
        result = doctor.check_env_file(tmp_path)
        assert result.status == "warn"

    def test_present(self, tmp_path):
        (tmp_path / ".env").write_text("KEY=val\n")
        result = doctor.check_env_file(tmp_path)
        assert result.status == "ok"


# ---------------------------------------------------------------------------
# main() exit code
# ---------------------------------------------------------------------------


class TestMainExitCode:
    def test_returns_int(self, tmp_path, monkeypatch, capsys):
        """main() should return 0 or 1 without raising."""
        repo_root = tmp_path / "repo"
        scripts_dir = repo_root / "scripts"
        scripts_dir.mkdir(parents=True)
        fake_doctor = scripts_dir / "doctor.py"
        fake_doctor.write_text("# test-only shim for __file__ resolution\n")

        monkeypatch.chdir(repo_root)
        monkeypatch.setattr(doctor, "__file__", str(fake_doctor))
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)

        exit_code = doctor.main()

        captured = capsys.readouterr()
        output = captured.out + captured.err

        assert exit_code in (0, 1)
        assert output
        assert "config.yaml" in output
        assert ".env" in output
