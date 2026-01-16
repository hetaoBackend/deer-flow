import logging
from collections.abc import AsyncGenerator

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from src.gateway.config import get_gateway_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["proxy"])

# Hop-by-hop headers that should not be forwarded
EXCLUDED_HEADERS = {
    "host",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
}


async def stream_response(client: httpx.AsyncClient, method: str, url: str, headers: dict, body: bytes | None, timeout: float) -> AsyncGenerator[bytes, None]:
    """Stream response from the upstream server.

    Args:
        client: The httpx async client.
        method: HTTP method.
        url: Target URL.
        headers: Request headers.
        body: Request body.
        timeout: Request timeout.

    Yields:
        Response chunks.
    """
    async with client.stream(
        method=method,
        url=url,
        headers=headers,
        content=body,
        timeout=timeout,
    ) as response:
        async for chunk in response.aiter_bytes():
            yield chunk


async def proxy_request(request: Request, path: str) -> Response | StreamingResponse:
    """Proxy a request to the LangGraph server.

    Args:
        request: The incoming FastAPI request.
        path: The path to proxy to.

    Returns:
        Response or StreamingResponse depending on content type.
    """
    config = get_gateway_config()
    target_url = f"{config.langgraph_url}/{path}"

    # Preserve query parameters
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    # Prepare headers (exclude hop-by-hop headers)
    headers = {key: value for key, value in request.headers.items() if key.lower() not in EXCLUDED_HEADERS}

    # Read request body for non-GET requests
    body = None
    if request.method not in ("GET", "HEAD"):
        body = await request.body()

    async with httpx.AsyncClient() as client:
        try:
            # First, make a non-streaming request to check content type
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                timeout=config.proxy_timeout,
            )

            content_type = response.headers.get("content-type", "")

            # Check if response is SSE (Server-Sent Events)
            if "text/event-stream" in content_type:
                # For SSE, we need to re-request with streaming
                return StreamingResponse(
                    stream_response(client, request.method, target_url, headers, body, config.stream_timeout),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )

            # Prepare response headers
            response_headers = dict(response.headers)
            for header in ["transfer-encoding", "connection", "keep-alive"]:
                response_headers.pop(header, None)

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
            )

        except httpx.TimeoutException:
            logger.error(f"Proxy request to {target_url} timed out")
            return Response(
                content='{"error": "Proxy request timed out"}',
                status_code=504,
                media_type="application/json",
            )
        except httpx.RequestError as e:
            logger.error(f"Proxy request to {target_url} failed: {e}")
            return Response(
                content='{"error": "Proxy request failed"}',
                status_code=502,
                media_type="application/json",
            )


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_langgraph(request: Request, path: str) -> Response:
    """Proxy all requests to LangGraph server.

    This catch-all route forwards requests to the LangGraph server.
    """
    return await proxy_request(request, path)
