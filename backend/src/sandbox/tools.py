import re

from langchain.tools import ToolRuntime, tool
from langgraph.typing import ContextT

from src.agents.thread_state import ThreadDataState, ThreadState
from src.sandbox.sandbox import Sandbox
from src.sandbox.sandbox_provider import get_sandbox_provider

# Virtual path prefix used in sandbox environments
VIRTUAL_PATH_PREFIX = "/mnt/user-data"


def replace_virtual_path(path: str, thread_data: ThreadDataState | None) -> str:
    """Replace virtual /mnt/user-data paths with actual thread data paths.

    Mapping:
        /mnt/user-data/workspace/* -> thread_data['workspace_path']/*
        /mnt/user-data/uploads/* -> thread_data['uploads_path']/*
        /mnt/user-data/outputs/* -> thread_data['outputs_path']/*

    Args:
        path: The path that may contain virtual path prefix.
        thread_data: The thread data containing actual paths.

    Returns:
        The path with virtual prefix replaced by actual path.
    """
    if not path.startswith(VIRTUAL_PATH_PREFIX):
        return path

    if thread_data is None:
        return path

    # Map virtual subdirectories to thread_data keys
    path_mapping = {
        "workspace": thread_data.get("workspace_path"),
        "uploads": thread_data.get("uploads_path"),
        "outputs": thread_data.get("outputs_path"),
    }

    # Extract the subdirectory after /mnt/user-data/
    relative_path = path[len(VIRTUAL_PATH_PREFIX) :].lstrip("/")
    if not relative_path:
        return path

    # Find which subdirectory this path belongs to
    parts = relative_path.split("/", 1)
    subdir = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    actual_base = path_mapping.get(subdir)
    if actual_base is None:
        return path

    if rest:
        return f"{actual_base}/{rest}"
    return actual_base


def replace_virtual_paths_in_command(command: str, thread_data: ThreadDataState | None) -> str:
    """Replace all virtual /mnt/user-data paths in a command string.

    Args:
        command: The command string that may contain virtual paths.
        thread_data: The thread data containing actual paths.

    Returns:
        The command with all virtual paths replaced.
    """
    if VIRTUAL_PATH_PREFIX not in command:
        return command

    if thread_data is None:
        return command

    # Pattern to match /mnt/user-data followed by path characters
    pattern = re.compile(rf"{re.escape(VIRTUAL_PATH_PREFIX)}(/[^\s\"';&|<>()]*)?")

    def replace_match(match: re.Match) -> str:
        full_path = match.group(0)
        return replace_virtual_path(full_path, thread_data)

    return pattern.sub(replace_match, command)


def get_thread_data(runtime: ToolRuntime[ContextT, ThreadState] | None) -> ThreadDataState | None:
    """Extract thread_data from runtime state."""
    if runtime is None:
        return None
    return runtime.state.get("thread_data")


def is_local_sandbox(runtime: ToolRuntime[ContextT, ThreadState] | None) -> bool:
    """Check if the current sandbox is a local sandbox.

    Path replacement is only needed for local sandbox since aio sandbox
    already has /mnt/user-data mounted in the container.
    """
    if runtime is None:
        return False
    sandbox_state = runtime.state.get("sandbox")
    if sandbox_state is None:
        return False
    return sandbox_state.get("sandbox_id") == "local"


def sandbox_from_runtime(runtime: ToolRuntime[ContextT, ThreadState] | None = None) -> Sandbox:
    if runtime is None:
        raise ValueError("No sandbox found: No runtime found")
    sandbox_state = runtime.state.get("sandbox")
    if sandbox_state is None:
        raise ValueError("No sandbox found: No sandbox state found in runtime")
    sandbox_id = sandbox_state.get("sandbox_id")
    if sandbox_id is None:
        raise ValueError("No sandbox ID found: No sandbox ID found in sandbox state")
    sandbox = get_sandbox_provider().get(sandbox_id)
    if sandbox is None:
        raise ValueError(f"No sandbox found: sandbox with ID {sandbox_id} not found")
    return sandbox


@tool("bash", parse_docstring=True)
def bash_tool(runtime: ToolRuntime[ContextT, ThreadState], description: str, command: str) -> str:
    """Execute a bash command in a Linux environment.


    - Use `python` to run Python code.
    - Use `pip install` to install Python packages.

    Args:
        description: Explain why you are running this command in short words. ALWAYS PROVIDE THIS PARAMETER FIRST.
        command: The bash command to execute. Always use absolute paths for files and directories.
    """
    try:
        sandbox = sandbox_from_runtime(runtime)
        if is_local_sandbox(runtime):
            thread_data = get_thread_data(runtime)
            command = replace_virtual_paths_in_command(command, thread_data)
        return sandbox.execute_command(command)
    except Exception as e:
        return f"Error: {e}"


@tool("ls", parse_docstring=True)
def ls_tool(runtime: ToolRuntime[ContextT, ThreadState], description: str, path: str) -> str:
    """List the contents of a directory up to 2 levels deep in tree format.

    Args:
        description: Explain why you are listing this directory in short words. ALWAYS PROVIDE THIS PARAMETER FIRST.
        path: The **absolute** path to the directory to list.
    """
    try:
        sandbox = sandbox_from_runtime(runtime)
        if is_local_sandbox(runtime):
            thread_data = get_thread_data(runtime)
            path = replace_virtual_path(path, thread_data)
        children = sandbox.list_dir(path)
        if not children:
            return "(empty)"
        return "\n".join(children)
    except Exception as e:
        return f"Error: {e}"


@tool("read_file", parse_docstring=True)
def read_file_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    description: str,
    path: str,
    view_range: tuple[int, int] | None = None,
) -> str:
    """Read the contents of a text file.

    Args:
        description: Explain why you are viewing this file in short words. ALWAYS PROVIDE THIS PARAMETER FIRST.
        path: The **absolute** path to the file to read.
        view_range: The range of lines to view. The range is inclusive and starts at 1. For example, (1, 10) will view the first 10 lines of the file.
    """
    try:
        sandbox = sandbox_from_runtime(runtime)
        if is_local_sandbox(runtime):
            thread_data = get_thread_data(runtime)
            path = replace_virtual_path(path, thread_data)
        content = sandbox.read_file(path)
        if not content:
            return "(empty)"
        if view_range:
            start, end = view_range
            content = "\n".join(content.splitlines()[start - 1 : end])
        return content
    except Exception as e:
        return f"Error: {e}"


@tool("write_file", parse_docstring=True)
def write_file_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    description: str,
    path: str,
    content: str,
    append: bool = False,
) -> str:
    """Write text content to a file.

    Args:
        description: Explain why you are writing to this file in short words. ALWAYS PROVIDE THIS PARAMETER FIRST.
        path: The **absolute** path to the file to write to. ALWAYS PROVIDE THIS PARAMETER SECOND.
        content: The content to write to the file. ALWAYS PROVIDE THIS PARAMETER THIRD.
    """
    try:
        sandbox = sandbox_from_runtime(runtime)
        if is_local_sandbox(runtime):
            thread_data = get_thread_data(runtime)
            path = replace_virtual_path(path, thread_data)
        sandbox.write_file(path, content, append)
        return "OK"
    except Exception as e:
        return f"Error: {e}"


@tool("str_replace", parse_docstring=True)
def str_replace_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    description: str,
    path: str,
    old_str: str,
    new_str: str,
    replace_all: bool = False,
) -> str:
    """Replace a substring in a file with another substring.
    If `replace_all` is False (default), the substring to replace must appear **exactly once** in the file.

    Args:
        description: Explain why you are replacing the substring in short words. ALWAYS PROVIDE THIS PARAMETER FIRST.
        path: The **absolute** path to the file to replace the substring in. ALWAYS PROVIDE THIS PARAMETER SECOND.
        old_str: The substring to replace. ALWAYS PROVIDE THIS PARAMETER THIRD.
        new_str: The new substring. ALWAYS PROVIDE THIS PARAMETER FOURTH.
        replace_all: Whether to replace all occurrences of the substring. If False, only the first occurrence will be replaced. Default is False.
    """
    try:
        sandbox = sandbox_from_runtime(runtime)
        if is_local_sandbox(runtime):
            thread_data = get_thread_data(runtime)
            path = replace_virtual_path(path, thread_data)
        content = sandbox.read_file(path)
        if not content:
            return "OK"
        if replace_all:
            content = content.replace(old_str, new_str)
        else:
            content = content.replace(old_str, new_str, 1)
        sandbox.write_file(path, content)
        return "OK"
    except Exception as e:
        return f"Error: {e}"
