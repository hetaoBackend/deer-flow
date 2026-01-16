import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

# Base directory for thread data (relative to backend/)
THREAD_DATA_BASE_DIR = ".deer-flow/threads"

# Virtual path prefix used in sandbox environments (without leading slash for URL path matching)
VIRTUAL_PATH_PREFIX = "mnt/user-data"

router = APIRouter(prefix="/api", tags=["artifacts"])


def _resolve_artifact_path(thread_id: str, artifact_path: str) -> Path:
    """Resolve a virtual artifact path to the actual filesystem path.

    Args:
        thread_id: The thread ID.
        artifact_path: The virtual path (e.g., mnt/user-data/outputs/file.txt).

    Returns:
        The resolved filesystem path.

    Raises:
        HTTPException: If the path is invalid or outside allowed directories.
    """
    # Validate and remove virtual path prefix
    if not artifact_path.startswith(VIRTUAL_PATH_PREFIX):
        raise HTTPException(status_code=400, detail=f"Path must start with /{VIRTUAL_PATH_PREFIX}")
    relative_path = artifact_path[len(VIRTUAL_PATH_PREFIX) :].lstrip("/")

    # Build the actual path
    base_dir = Path(os.getcwd()) / THREAD_DATA_BASE_DIR / thread_id / "user-data"
    actual_path = base_dir / relative_path

    # Security check: ensure the path is within the thread's user-data directory
    try:
        actual_path = actual_path.resolve()
        base_dir = base_dir.resolve()
        if not str(actual_path).startswith(str(base_dir)):
            raise HTTPException(status_code=403, detail="Access denied: path traversal detected")
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=400, detail="Invalid path")

    return actual_path


@router.get("/threads/{thread_id}/artifacts/{path:path}")
async def get_artifact(thread_id: str, path: str) -> FileResponse:
    """Get an artifact file by its path.

    Args:
        thread_id: The thread ID.
        path: The artifact path with virtual prefix (e.g., mnt/user-data/outputs/file.txt).

    Returns:
        The file content as a FileResponse.

    Raises:
        HTTPException: 404 if file not found, 403 if access denied.
    """
    actual_path = _resolve_artifact_path(thread_id, path)

    if not actual_path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {path}")

    if not actual_path.is_file():
        raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")

    return FileResponse(
        path=actual_path,
        filename=actual_path.name,
    )
