import mimetypes
import os
import re
import zipfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

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


def is_text_file_by_content(path: Path, sample_size: int = 8192) -> bool:
    """Check if file is text by examining content for null bytes."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
            # Text files shouldn't contain null bytes
            return b"\x00" not in chunk
    except Exception:
        return False


def remove_citations_block(content: str) -> str:
    """Remove ALL citations from markdown content.
    
    Removes:
    - <citations>...</citations> blocks (complete and incomplete)
    - [cite-N] references
    - Citation markdown links that were converted from [cite-N]
    
    This is used for downloads to provide clean markdown without any citation references.
    
    Args:
        content: The markdown content that may contain citations blocks.
        
    Returns:
        Clean content with all citations completely removed.
    """
    if not content:
        return content
    
    result = content
    
    # Step 1: Parse and extract citation URLs before removing blocks
    citation_urls = set()
    citations_pattern = r'<citations>([\s\S]*?)</citations>'
    for match in re.finditer(citations_pattern, content):
        citations_block = match.group(1)
        # Extract URLs from JSON lines
        import json
        for line in citations_block.split('\n'):
            line = line.strip()
            if line.startswith('{'):
                try:
                    citation = json.loads(line)
                    if 'url' in citation:
                        citation_urls.add(citation['url'])
                except (json.JSONDecodeError, ValueError):
                    pass
    
    # Step 2: Remove complete citations blocks
    result = re.sub(r'<citations>[\s\S]*?</citations>', '', result)
    
    # Step 3: Remove incomplete citations blocks (at end of content during streaming)
    if "<citations>" in result:
        result = re.sub(r'<citations>[\s\S]*$', '', result)
    
    # Step 4: Remove all [cite-N] references
    result = re.sub(r'\[cite-\d+\]', '', result)
    
    # Step 5: Remove markdown links that point to citation URLs
    # Pattern: [text](url)
    if citation_urls:
        for url in citation_urls:
            # Escape special regex characters in URL
            escaped_url = re.escape(url)
            result = re.sub(rf'\[[^\]]+\]\({escaped_url}\)', '', result)
    
    # Step 6: Clean up extra whitespace and newlines
    result = re.sub(r'\n{3,}', '\n\n', result)  # Replace 3+ newlines with 2
    
    return result.strip()


def _extract_file_from_skill_archive(zip_path: Path, internal_path: str) -> bytes | None:
    """Extract a file from a .skill ZIP archive.

    Args:
        zip_path: Path to the .skill file (ZIP archive).
        internal_path: Path to the file inside the archive (e.g., "SKILL.md").

    Returns:
        The file content as bytes, or None if not found.
    """
    if not zipfile.is_zipfile(zip_path):
        return None

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # List all files in the archive
            namelist = zip_ref.namelist()

            # Try direct path first
            if internal_path in namelist:
                return zip_ref.read(internal_path)

            # Try with any top-level directory prefix (e.g., "skill-name/SKILL.md")
            for name in namelist:
                if name.endswith("/" + internal_path) or name == internal_path:
                    return zip_ref.read(name)

            # Not found
            return None
    except (zipfile.BadZipFile, KeyError):
        return None


@router.get(
    "/threads/{thread_id}/artifacts/{path:path}",
    summary="Get Artifact File",
    description="Retrieve an artifact file generated by the AI agent. Supports text, HTML, and binary files.",
)
async def get_artifact(thread_id: str, path: str, request: Request) -> FileResponse:
    """Get an artifact file by its path.

    The endpoint automatically detects file types and returns appropriate content types.
    Use the `?download=true` query parameter to force file download.

    Args:
        thread_id: The thread ID.
        path: The artifact path with virtual prefix (e.g., mnt/user-data/outputs/file.txt).
        request: FastAPI request object (automatically injected).

    Returns:
        The file content as a FileResponse with appropriate content type:
        - HTML files: Rendered as HTML
        - Text files: Plain text with proper MIME type
        - Binary files: Inline display with download option

    Raises:
        HTTPException:
            - 400 if path is invalid or not a file
            - 403 if access denied (path traversal detected)
            - 404 if file not found

    Query Parameters:
        download (bool): If true, returns file as attachment for download

    Example:
        - Get HTML file: `/api/threads/abc123/artifacts/mnt/user-data/outputs/index.html`
        - Download file: `/api/threads/abc123/artifacts/mnt/user-data/outputs/data.csv?download=true`
    """
    # Check if this is a request for a file inside a .skill archive (e.g., xxx.skill/SKILL.md)
    if ".skill/" in path:
        # Split the path at ".skill/" to get the ZIP file path and internal path
        skill_marker = ".skill/"
        marker_pos = path.find(skill_marker)
        skill_file_path = path[: marker_pos + len(".skill")]  # e.g., "mnt/user-data/outputs/my-skill.skill"
        internal_path = path[marker_pos + len(skill_marker) :]  # e.g., "SKILL.md"

        actual_skill_path = _resolve_artifact_path(thread_id, skill_file_path)

        if not actual_skill_path.exists():
            raise HTTPException(status_code=404, detail=f"Skill file not found: {skill_file_path}")

        if not actual_skill_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {skill_file_path}")

        # Extract the file from the .skill archive
        content = _extract_file_from_skill_archive(actual_skill_path, internal_path)
        if content is None:
            raise HTTPException(status_code=404, detail=f"File '{internal_path}' not found in skill archive")

        # Determine MIME type based on the internal file
        mime_type, _ = mimetypes.guess_type(internal_path)
        # Add cache headers to avoid repeated ZIP extraction (cache for 5 minutes)
        cache_headers = {"Cache-Control": "private, max-age=300"}
        if mime_type and mime_type.startswith("text/"):
            return PlainTextResponse(content=content.decode("utf-8"), media_type=mime_type, headers=cache_headers)

        # Default to plain text for unknown types that look like text
        try:
            return PlainTextResponse(content=content.decode("utf-8"), media_type="text/plain", headers=cache_headers)
        except UnicodeDecodeError:
            return Response(content=content, media_type=mime_type or "application/octet-stream", headers=cache_headers)

    actual_path = _resolve_artifact_path(thread_id, path)

    if not actual_path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {path}")

    if not actual_path.is_file():
        raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")

    mime_type, _ = mimetypes.guess_type(actual_path)

    # Encode filename for Content-Disposition header (RFC 5987)
    encoded_filename = quote(actual_path.name)
    
    # Check if this is a markdown file that might contain citations
    is_markdown = mime_type == "text/markdown" or actual_path.suffix.lower() in [".md", ".markdown"]
    
    # if `download` query parameter is true, return the file as a download
    if request.query_params.get("download"):
        # For markdown files, remove citations block before download
        if is_markdown:
            content = actual_path.read_text()
            clean_content = remove_citations_block(content)
            return Response(
                content=clean_content.encode("utf-8"),
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                    "Content-Type": "text/markdown; charset=utf-8"
                }
            )
        return FileResponse(path=actual_path, filename=actual_path.name, media_type=mime_type, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"})

    if mime_type and mime_type == "text/html":
        return HTMLResponse(content=actual_path.read_text())

    if mime_type and mime_type.startswith("text/"):
        return PlainTextResponse(content=actual_path.read_text(), media_type=mime_type)

    if is_text_file_by_content(actual_path):
        return PlainTextResponse(content=actual_path.read_text(), media_type=mime_type)

    return Response(content=actual_path.read_bytes(), media_type=mime_type, headers={"Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"})
