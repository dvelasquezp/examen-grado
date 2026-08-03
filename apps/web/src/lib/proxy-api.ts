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

// En el plan gratuito de Render la API se duerme y tarda ~30 s en responder
// a la primera petición, así que reintentamos antes de dar error.
const COLD_START_RETRIES = 4;
const RETRY_DELAY_MS = 8000;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function proxyToApi(request: Request, path: string): Promise<Response> {
  const url = new URL(request.url);
  const target = `${apiTarget()}${path}${url.search}`;

  const headers = new Headers(request.headers);
  HOP_BY_HOP.forEach((h) => headers.delete(h));

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const body = hasBody ? await request.arrayBuffer() : undefined;

  let lastError = "";

  for (let attempt = 0; attempt <= COLD_START_RETRIES; attempt++) {
    try {
      const upstream = await fetch(target, {
        method: request.method,
        headers,
        body,
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
      lastError = error instanceof Error ? error.message : String(error);
      if (attempt < COLD_START_RETRIES) {
        await sleep(RETRY_DELAY_MS);
      }
    }
  }

  return Response.json(
    { detail: `No se pudo contactar la API (${apiTarget()}): ${lastError}` },
    { status: 502 },
  );
}
