from types import SimpleNamespace
from unittest.mock import patch

from deerflow.community.aio_sandbox.aio_sandbox import AioSandbox
from deerflow.sandbox.local.local_sandbox import LocalSandbox
from deerflow.sandbox.search import GrepMatch
from deerflow.sandbox.tools import glob_tool, grep_tool


def _make_runtime(tmp_path):
    workspace = tmp_path / "workspace"
    uploads = tmp_path / "uploads"
    outputs = tmp_path / "outputs"
    workspace.mkdir()
    uploads.mkdir()
    outputs.mkdir()
    return SimpleNamespace(
        state={
            "sandbox": {"sandbox_id": "local"},
            "thread_data": {
                "workspace_path": str(workspace),
                "uploads_path": str(uploads),
                "outputs_path": str(outputs),
            },
        },
        context={"thread_id": "thread-1"},
    )


def test_glob_tool_returns_virtual_paths_and_ignores_common_dirs(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    workspace = tmp_path / "workspace"
    (workspace / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (workspace / "pkg").mkdir()
    (workspace / "pkg" / "util.py").write_text("print('util')\n", encoding="utf-8")
    (workspace / "node_modules").mkdir()
    (workspace / "node_modules" / "skip.py").write_text("ignored\n", encoding="utf-8")

    monkeypatch.setattr("deerflow.sandbox.tools.ensure_sandbox_initialized", lambda runtime: LocalSandbox(id="local"))

    result = glob_tool.func(
        runtime=runtime,
        description="find python files",
        pattern="**/*.py",
        path="/mnt/user-data/workspace",
    )

    assert "/mnt/user-data/workspace/app.py" in result
    assert "/mnt/user-data/workspace/pkg/util.py" in result
    assert "node_modules" not in result
    assert str(workspace) not in result


def test_glob_tool_supports_skills_virtual_paths(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    skills_dir = tmp_path / "skills"
    (skills_dir / "public" / "demo").mkdir(parents=True)
    (skills_dir / "public" / "demo" / "SKILL.md").write_text("# Demo\n", encoding="utf-8")

    monkeypatch.setattr("deerflow.sandbox.tools.ensure_sandbox_initialized", lambda runtime: LocalSandbox(id="local"))

    with (
        patch("deerflow.sandbox.tools._get_skills_container_path", return_value="/mnt/skills"),
        patch("deerflow.sandbox.tools._get_skills_host_path", return_value=str(skills_dir)),
    ):
        result = glob_tool.func(
            runtime=runtime,
            description="find skills",
            pattern="**/SKILL.md",
            path="/mnt/skills",
        )

    assert "/mnt/skills/public/demo/SKILL.md" in result
    assert str(skills_dir) not in result


def test_grep_tool_filters_by_glob_and_skips_binary_files(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    workspace = tmp_path / "workspace"
    (workspace / "main.py").write_text("TODO = 'ship it'\nprint(TODO)\n", encoding="utf-8")
    (workspace / "notes.txt").write_text("TODO in txt should be filtered\n", encoding="utf-8")
    (workspace / "image.bin").write_bytes(b"\0binary TODO")

    monkeypatch.setattr("deerflow.sandbox.tools.ensure_sandbox_initialized", lambda runtime: LocalSandbox(id="local"))

    result = grep_tool.func(
        runtime=runtime,
        description="find todo references",
        pattern="TODO",
        path="/mnt/user-data/workspace",
        glob="**/*.py",
    )

    assert "/mnt/user-data/workspace/main.py:1: TODO = 'ship it'" in result
    assert "notes.txt" not in result
    assert "image.bin" not in result
    assert str(workspace) not in result


def test_grep_tool_truncates_results(tmp_path, monkeypatch) -> None:
    runtime = _make_runtime(tmp_path)
    workspace = tmp_path / "workspace"
    (workspace / "main.py").write_text("TODO one\nTODO two\nTODO three\n", encoding="utf-8")

    monkeypatch.setattr("deerflow.sandbox.tools.ensure_sandbox_initialized", lambda runtime: LocalSandbox(id="local"))

    result = grep_tool.func(
        runtime=runtime,
        description="limit matches",
        pattern="TODO",
        path="/mnt/user-data/workspace",
        max_results=2,
    )

    assert "Found 2 matches under /mnt/user-data/workspace (showing first 2)" in result
    assert "TODO one" in result
    assert "TODO two" in result
    assert "TODO three" not in result
    assert "Results truncated." in result


def test_aio_sandbox_glob_parses_json(monkeypatch) -> None:
    with patch("deerflow.community.aio_sandbox.aio_sandbox.AioSandboxClient"):
        sandbox = AioSandbox(id="test-sandbox", base_url="http://localhost:8080")
    monkeypatch.setattr(
        sandbox._client.file,
        "find_files",
        lambda **kwargs: SimpleNamespace(
            data=SimpleNamespace(files=["/mnt/user-data/workspace/app.py", "/mnt/user-data/workspace/node_modules/skip.py"])
        ),
    )

    matches, truncated = sandbox.glob("/mnt/user-data/workspace", "**/*.py")

    assert matches == ["/mnt/user-data/workspace/app.py"]
    assert truncated is False


def test_aio_sandbox_grep_parses_json(monkeypatch) -> None:
    with patch("deerflow.community.aio_sandbox.aio_sandbox.AioSandboxClient"):
        sandbox = AioSandbox(id="test-sandbox", base_url="http://localhost:8080")
    monkeypatch.setattr(
        sandbox._client.file,
        "list_path",
        lambda **kwargs: SimpleNamespace(
            data=SimpleNamespace(
                files=[
                    SimpleNamespace(
                        name="app.py",
                        path="/mnt/user-data/workspace/app.py",
                        is_directory=False,
                    )
                ]
            )
        ),
    )
    monkeypatch.setattr(
        sandbox._client.file,
        "search_in_file",
        lambda **kwargs: SimpleNamespace(data=SimpleNamespace(line_numbers=[7], matches=["TODO = True"])),
    )

    matches, truncated = sandbox.grep("/mnt/user-data/workspace", "TODO")

    assert matches == [GrepMatch(path="/mnt/user-data/workspace/app.py", line_number=7, line="TODO = True")]
    assert truncated is False
