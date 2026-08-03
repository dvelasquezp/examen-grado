const HOP_BY_HOP = new Set([
  "connection",
  "content-encoding",
  "content-length",
  "host",
  "keep-alive",
  "transfer-encoding",
  "upgrade",
]);

export function apiTarget(): string {
  const raw = (process.env.API_PROXY_TARGET || "http://localhost:8000").trim().replace(/\/$/, "");
  return /^https?:\/\//.test(raw) ? raw : `https://${raw}`;
}

export async function proxyToApi(request: Request, path: string): Promise<Response> {
  const url = new URL(request.url);
  const target = `${apiTarget()}${path}${url.search}`;

  const headers = new Headers(request.headers);
  HOP_BY_HOP.forEach((h) => headers.delete(h));

  const hasBody = request.method !== "GET" && request.method !== "HEAD";

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
    });

    const responseHeaders = new Headers(upstream.headers);
    HOP_BY_HOP.forEach((h) => responseHeaders.delete(h));

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    return Response.json(
      { detail: `No se pudo contactar la API (${apiTarget()}): ${detail}` },
      { status: 502 },
    );
  }
}
