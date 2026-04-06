"""Tool for creating and evolving custom skills."""

from __future__ import annotations

import asyncio
import logging
import shutil
from typing import Any

from langchain.tools import ToolRuntime, tool
from langgraph.typing import ContextT

from deerflow.agents.lead_agent.prompt import clear_skills_system_prompt_cache
from deerflow.agents.thread_state import ThreadState
from deerflow.mcp.tools import _make_sync_tool_wrapper
from deerflow.skills.manager import (
    append_history,
    atomic_write,
    custom_skill_exists,
    ensure_custom_skill_is_editable,
    ensure_safe_support_path,
    get_custom_skill_dir,
    get_custom_skill_file,
    public_skill_exists,
    read_custom_skill_content,
    validate_skill_markdown_content,
    validate_skill_name,
)
from deerflow.skills.security_scanner import scan_skill_content

logger = logging.getLogger(__name__)

_skill_locks: dict[str, asyncio.Lock] = {}


def _get_lock(name: str) -> asyncio.Lock:
    lock = _skill_locks.get(name)
    if lock is None:
        lock = asyncio.Lock()
        _skill_locks[name] = lock
    return lock


def _get_thread_id(runtime: ToolRuntime[ContextT, ThreadState] | None) -> str | None:
    if runtime is None:
        return None
    if runtime.context and runtime.context.get("thread_id"):
        return runtime.context.get("thread_id")
    return runtime.config.get("configurable", {}).get("thread_id")


def _history_record(*, action: str, file_path: str, prev_content: str | None, new_content: str | None, thread_id: str | None, scanner: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": action,
        "author": "agent",
        "thread_id": thread_id,
        "file_path": file_path,
        "prev_content": prev_content,
        "new_content": new_content,
        "scanner": scanner,
    }


async def _scan_or_raise(content: str, *, executable: bool, location: str) -> dict[str, str]:
    result = await scan_skill_content(content, executable=executable, location=location)
    if result.decision == "block":
        raise ValueError(f"Security scan blocked the write: {result.reason}")
    if executable and result.decision != "allow":
        raise ValueError(f"Security scan rejected executable content: {result.reason}")
    return {"decision": result.decision, "reason": result.reason}


async def _skill_manage_impl(
    runtime: ToolRuntime[ContextT, ThreadState],
    action: str,
    name: str,
    content: str | None = None,
    path: str | None = None,
    find: str | None = None,
    replace: str | None = None,
    expected_count: int | None = None,
) -> str:
    """Manage custom skills under skills/custom/.

    Args:
        action: One of create, patch, edit, delete, write_file, remove_file.
        name: Skill name in hyphen-case.
        content: New file content for create, edit, or write_file.
        path: Supporting file path for write_file or remove_file.
        find: Existing text to replace for patch.
        replace: Replacement text for patch.
        expected_count: Optional expected number of replacements for patch.
    """
    name = validate_skill_name(name)
    lock = _get_lock(name)
    thread_id = _get_thread_id(runtime)

    async with lock:
        if action == "create":
            if custom_skill_exists(name):
                raise ValueError(f"Custom skill '{name}' already exists.")
            if content is None:
                raise ValueError("content is required for create.")
            validate_skill_markdown_content(name, content)
            scan = await _scan_or_raise(content, executable=False, location=f"{name}/SKILL.md")
            skill_file = get_custom_skill_file(name)
            atomic_write(skill_file, content)
            append_history(name, _history_record(action="create", file_path="SKILL.md", prev_content=None, new_content=content, thread_id=thread_id, scanner=scan))
            clear_skills_system_prompt_cache()
            return f"Created custom skill '{name}'."

        if action == "edit":
            ensure_custom_skill_is_editable(name)
            if content is None:
                raise ValueError("content is required for edit.")
            validate_skill_markdown_content(name, content)
            scan = await _scan_or_raise(content, executable=False, location=f"{name}/SKILL.md")
            skill_file = get_custom_skill_file(name)
            prev_content = skill_file.read_text(encoding="utf-8")
            atomic_write(skill_file, content)
            append_history(name, _history_record(action="edit", file_path="SKILL.md", prev_content=prev_content, new_content=content, thread_id=thread_id, scanner=scan))
            clear_skills_system_prompt_cache()
            return f"Updated custom skill '{name}'."

        if action == "patch":
            ensure_custom_skill_is_editable(name)
            if find is None or replace is None:
                raise ValueError("find and replace are required for patch.")
            skill_file = get_custom_skill_file(name)
            prev_content = skill_file.read_text(encoding="utf-8")
            occurrences = prev_content.count(find)
            if occurrences == 0:
                raise ValueError("Patch target not found in SKILL.md.")
            if expected_count is not None and occurrences != expected_count:
                raise ValueError(f"Expected {expected_count} replacements but found {occurrences}.")
            replacement_count = expected_count if expected_count is not None else 1
            new_content = prev_content.replace(find, replace, replacement_count)
            validate_skill_markdown_content(name, new_content)
            scan = await _scan_or_raise(new_content, executable=False, location=f"{name}/SKILL.md")
            atomic_write(skill_file, new_content)
            append_history(name, _history_record(action="patch", file_path="SKILL.md", prev_content=prev_content, new_content=new_content, thread_id=thread_id, scanner=scan))
            clear_skills_system_prompt_cache()
            return f"Patched custom skill '{name}' ({replacement_count} replacement(s) applied, {occurrences} match(es) found)."

        if action == "delete":
            ensure_custom_skill_is_editable(name)
            skill_dir = get_custom_skill_dir(name)
            prev_content = read_custom_skill_content(name)
            append_history(name, _history_record(action="delete", file_path="SKILL.md", prev_content=prev_content, new_content=None, thread_id=thread_id, scanner={"decision": "allow", "reason": "Deletion requested."}))
            shutil.rmtree(skill_dir)
            clear_skills_system_prompt_cache()
            return f"Deleted custom skill '{name}'."

        if action == "write_file":
            ensure_custom_skill_is_editable(name)
            if path is None or content is None:
                raise ValueError("path and content are required for write_file.")
            target = ensure_safe_support_path(name, path)
            prev_content = target.read_text(encoding="utf-8") if target.exists() else None
            executable = "scripts/" in path or path.startswith("scripts/")
            scan = await _scan_or_raise(content, executable=executable, location=f"{name}/{path}")
            atomic_write(target, content)
            append_history(name, _history_record(action="write_file", file_path=path, prev_content=prev_content, new_content=content, thread_id=thread_id, scanner=scan))
            return f"Wrote '{path}' for custom skill '{name}'."

        if action == "remove_file":
            ensure_custom_skill_is_editable(name)
            if path is None:
                raise ValueError("path is required for remove_file.")
            target = ensure_safe_support_path(name, path)
            if not target.exists():
                raise FileNotFoundError(f"Supporting file '{path}' not found for skill '{name}'.")
            prev_content = target.read_text(encoding="utf-8")
            target.unlink()
            append_history(name, _history_record(action="remove_file", file_path=path, prev_content=prev_content, new_content=None, thread_id=thread_id, scanner={"decision": "allow", "reason": "Deletion requested."}))
            return f"Removed '{path}' from custom skill '{name}'."

        if public_skill_exists(name):
            raise ValueError(f"'{name}' is a built-in skill. To customise it, create a new skill with the same name under skills/custom/.")
        raise ValueError(f"Unsupported action '{action}'.")


@tool("skill_manage", parse_docstring=True)
async def skill_manage_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    action: str,
    name: str,
    content: str | None = None,
    path: str | None = None,
    find: str | None = None,
    replace: str | None = None,
    expected_count: int | None = None,
) -> str:
    """Manage custom skills under skills/custom/.

    Args:
        action: One of create, patch, edit, delete, write_file, remove_file.
        name: Skill name in hyphen-case.
        content: New file content for create, edit, or write_file.
        path: Supporting file path for write_file or remove_file.
        find: Existing text to replace for patch.
        replace: Replacement text for patch.
        expected_count: Optional expected number of replacements for patch.
    """
    return await _skill_manage_impl(
        runtime=runtime,
        action=action,
        name=name,
        content=content,
        path=path,
        find=find,
        replace=replace,
        expected_count=expected_count,
    )


skill_manage_tool.func = _make_sync_tool_wrapper(_skill_manage_impl, "skill_manage")
