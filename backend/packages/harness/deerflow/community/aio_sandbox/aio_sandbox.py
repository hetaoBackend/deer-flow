import base64
import json
import logging
import shlex
import threading
import uuid

from agent_sandbox import Sandbox as AioSandboxClient

from deerflow.sandbox.sandbox import Sandbox
from deerflow.sandbox.search import DEFAULT_LINE_SUMMARY_LENGTH, DEFAULT_MAX_FILE_SIZE_BYTES, IGNORE_PATTERNS, GrepMatch

logger = logging.getLogger(__name__)

_ERROR_OBSERVATION_SIGNATURE = "'ErrorObservation' object has no attribute 'exit_code'"


class AioSandbox(Sandbox):
    """Sandbox implementation using the agent-infra/sandbox Docker container.

    This sandbox connects to a running AIO sandbox container via HTTP API.
    A threading lock serializes shell commands to prevent concurrent requests
    from corrupting the container's single persistent session (see #1433).
    """

    def __init__(self, id: str, base_url: str, home_dir: str | None = None):
        """Initialize the AIO sandbox.

        Args:
            id: Unique identifier for this sandbox instance.
            base_url: URL of the sandbox API (e.g., http://localhost:8080).
            home_dir: Home directory inside the sandbox. If None, will be fetched from the sandbox.
        """
        super().__init__(id)
        self._base_url = base_url
        self._client = AioSandboxClient(base_url=base_url, timeout=600)
        self._home_dir = home_dir
        self._lock = threading.Lock()

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def home_dir(self) -> str:
        """Get the home directory inside the sandbox."""
        if self._home_dir is None:
            context = self._client.sandbox.get_context()
            self._home_dir = context.home_dir
        return self._home_dir

    def execute_command(self, command: str) -> str:
        """Execute a shell command in the sandbox.

        Uses a lock to serialize concurrent requests. The AIO sandbox
        container maintains a single persistent shell session that
        corrupts when hit with concurrent exec_command calls (returns
        ``ErrorObservation`` instead of real output). If corruption is
        detected despite the lock (e.g. multiple processes sharing a
        sandbox), the command is retried on a fresh session.

        Args:
            command: The command to execute.

        Returns:
            The output of the command.
        """
        with self._lock:
            try:
                result = self._client.shell.exec_command(command=command)
                output = result.data.output if result.data else ""

                if output and _ERROR_OBSERVATION_SIGNATURE in output:
                    logger.warning("ErrorObservation detected in sandbox output, retrying with a fresh session")
                    fresh_id = str(uuid.uuid4())
                    result = self._client.shell.exec_command(command=command, id=fresh_id)
                    output = result.data.output if result.data else ""

                return output if output else "(no output)"
            except Exception as e:
                logger.error(f"Failed to execute command in sandbox: {e}")
                return f"Error: {e}"

    def read_file(self, path: str) -> str:
        """Read the content of a file in the sandbox.

        Args:
            path: The absolute path of the file to read.

        Returns:
            The content of the file.
        """
        try:
            result = self._client.file.read_file(file=path)
            return result.data.content if result.data else ""
        except Exception as e:
            logger.error(f"Failed to read file in sandbox: {e}")
            return f"Error: {e}"

    def list_dir(self, path: str, max_depth: int = 2) -> list[str]:
        """List the contents of a directory in the sandbox.

        Args:
            path: The absolute path of the directory to list.
            max_depth: The maximum depth to traverse. Default is 2.

        Returns:
            The contents of the directory.
        """
        with self._lock:
            try:
                result = self._client.shell.exec_command(command=f"find {shlex.quote(path)} -maxdepth {max_depth} -type f -o -type d 2>/dev/null | head -500")
                output = result.data.output if result.data else ""
                if output:
                    return [line.strip() for line in output.strip().split("\n") if line.strip()]
                return []
            except Exception as e:
                logger.error(f"Failed to list directory in sandbox: {e}")
                return []

    def write_file(self, path: str, content: str, append: bool = False) -> None:
        """Write content to a file in the sandbox.

        Args:
            path: The absolute path of the file to write to.
            content: The text content to write to the file.
            append: Whether to append the content to the file.
        """
        with self._lock:
            try:
                if append:
                    existing = self.read_file(path)
                    if not existing.startswith("Error:"):
                        content = existing + content
                self._client.file.write_file(file=path, content=content)
            except Exception as e:
                logger.error(f"Failed to write file in sandbox: {e}")
                raise

    def _run_search_script(self, payload: dict, body: str) -> dict:
        payload_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        script = f"""python - <<'PY'
import base64
import json
{body}

payload = json.loads(base64.b64decode("{payload_b64}").decode("utf-8"))
print(json.dumps(main(payload)))
PY"""
        output = self.execute_command(script).strip()
        if output.startswith("Error:"):
            raise RuntimeError(output)
        try:
            return json.loads(output)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid sandbox search output: {output}") from exc

    def glob(self, path: str, pattern: str, *, include_dirs: bool = False, max_results: int = 200) -> tuple[list[str], bool]:
        body = """
import fnmatch
import os
from pathlib import Path, PurePosixPath

IGNORE_PATTERNS = """ + repr(IGNORE_PATTERNS) + """

def should_ignore(name):
    return any(fnmatch.fnmatch(name, pattern) for pattern in IGNORE_PATTERNS)

def path_matches(pattern, rel_path):
    path = PurePosixPath(rel_path)
    if path.match(pattern):
        return True
    if pattern.startswith("**/"):
        return path.match(pattern[3:])
    return False

def main(payload):
    root = Path(payload["path"]).resolve()
    if not root.exists():
        raise FileNotFoundError(str(root))
    if not root.is_dir():
        raise NotADirectoryError(str(root))

    matches = []
    truncated = False
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if not should_ignore(name)]
        rel_dir = Path(current_root).resolve().relative_to(root)

        if payload["include_dirs"]:
            for name in dirs:
                rel_path = (rel_dir / name).as_posix()
                if path_matches(payload["pattern"], rel_path):
                    matches.append(str((Path(current_root) / name).resolve()))
                    if len(matches) >= payload["max_results"]:
                        truncated = True
                        return {"matches": matches, "truncated": truncated}

        for name in files:
            if should_ignore(name):
                continue
            rel_path = (rel_dir / name).as_posix()
            if path_matches(payload["pattern"], rel_path):
                matches.append(str((Path(current_root) / name).resolve()))
                if len(matches) >= payload["max_results"]:
                    truncated = True
                    return {"matches": matches, "truncated": truncated}

    return {"matches": matches, "truncated": truncated}
"""
        data = self._run_search_script(
            {
                "path": path,
                "pattern": pattern,
                "include_dirs": include_dirs,
                "max_results": max_results,
            },
            body,
        )
        return data.get("matches", []), bool(data.get("truncated"))

    def grep(
        self,
        path: str,
        pattern: str,
        *,
        glob: str | None = None,
        literal: bool = False,
        case_sensitive: bool = False,
        max_results: int = 100,
    ) -> tuple[list[GrepMatch], bool]:
        body = """
import fnmatch
import os
import re
from pathlib import Path, PurePosixPath

IGNORE_PATTERNS = """ + repr(IGNORE_PATTERNS) + """

def should_ignore(name):
    return any(fnmatch.fnmatch(name, pattern) for pattern in IGNORE_PATTERNS)

def path_matches(pattern, rel_path):
    path = PurePosixPath(rel_path)
    if path.match(pattern):
        return True
    if pattern.startswith("**/"):
        return path.match(pattern[3:])
    return False

def truncate_line(line, max_chars):
    line = line.rstrip("\\n\\r")
    if len(line) <= max_chars:
        return line
    return line[: max_chars - 3] + "..."

def is_binary_file(path):
    try:
        with open(path, "rb") as handle:
            return b"\\0" in handle.read(8192)
    except OSError:
        return True

def main(payload):
    root = Path(payload["path"]).resolve()
    if not root.exists():
        raise FileNotFoundError(str(root))
    if not root.is_dir():
        raise NotADirectoryError(str(root))

    regex_source = re.escape(payload["pattern"]) if payload["literal"] else payload["pattern"]
    flags = 0 if payload["case_sensitive"] else re.IGNORECASE
    regex = re.compile(regex_source, flags)
    matches = []
    truncated = False

    for current_root, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if not should_ignore(name)]
        rel_dir = Path(current_root).resolve().relative_to(root)

        for name in files:
            if should_ignore(name):
                continue

            file_path = (Path(current_root) / name).resolve()
            rel_path = (rel_dir / name).as_posix()

            if payload["glob"] and not path_matches(payload["glob"], rel_path):
                continue

            try:
                if file_path.stat().st_size > payload["max_file_size"] or is_binary_file(file_path):
                    continue
                with open(file_path, encoding="utf-8", errors="replace") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        if regex.search(line):
                            matches.append({
                                "path": str(file_path),
                                "line_number": line_number,
                                "line": truncate_line(line, payload["line_summary_length"]),
                            })
                            if len(matches) >= payload["max_results"]:
                                truncated = True
                                return {"matches": matches, "truncated": truncated}
            except OSError:
                continue

    return {"matches": matches, "truncated": truncated}
"""
        data = self._run_search_script(
            {
                "path": path,
                "pattern": pattern,
                "glob": glob,
                "literal": literal,
                "case_sensitive": case_sensitive,
                "max_results": max_results,
                "max_file_size": DEFAULT_MAX_FILE_SIZE_BYTES,
                "line_summary_length": DEFAULT_LINE_SUMMARY_LENGTH,
            },
            body,
        )
        return [
            GrepMatch(
                path=match["path"],
                line_number=match["line_number"],
                line=match["line"],
            )
            for match in data.get("matches", [])
        ], bool(data.get("truncated"))

    def update_file(self, path: str, content: bytes) -> None:
        """Update a file with binary content in the sandbox.

        Args:
            path: The absolute path of the file to update.
            content: The binary content to write to the file.
        """
        with self._lock:
            try:
                base64_content = base64.b64encode(content).decode("utf-8")
                self._client.file.write_file(file=path, content=base64_content, encoding="base64")
            except Exception as e:
                logger.error(f"Failed to update file in sandbox: {e}")
                raise
