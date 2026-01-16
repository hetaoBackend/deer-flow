import { type NextRequest } from "next/server";

export const runtime = "nodejs";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  return handleProxy(request, (await params).path);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  return handleProxy(request, (await params).path);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  return handleProxy(request, (await params).path);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  return handleProxy(request, (await params).path);
}

async function handleProxy(request: NextRequest, pathSegments: string[]) {
  const targetUrl = `http://localhost:8000/${pathSegments.join("/")}`;

  // Preserve query parameters
  const searchParams = request.nextUrl.searchParams.toString();
  const fullUrl = searchParams ? `${targetUrl}?${searchParams}` : targetUrl;

  // Prepare headers
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    // Skip Next.js specific headers
    if (!key.startsWith("x-") && key !== "host" && key !== "connection") {
      headers.set(key, value);
    }
  });

  // Prepare fetch options
  const fetchOptions: RequestInit = {
    method: request.method,
    headers,
  };

  // Add body for non-GET requests
  if (request.method !== "GET" && request.method !== "HEAD") {
    fetchOptions.body = await request.text();
  }

  try {
    const response = await fetch(fullUrl, fetchOptions);

    // Check if response is SSE
    const contentType = response.headers.get("content-type");
    const isSSE = contentType?.includes("text/event-stream");

    if (isSSE && response.body) {
      // Handle SSE streaming
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    }

    // Handle regular responses
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      responseHeaders.set(key, value);
    });

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("Proxy error:", error);
    return new Response(JSON.stringify({ error: "Proxy request failed" }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}
