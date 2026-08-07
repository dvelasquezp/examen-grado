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

// En el plan gratuito de Render la API se duerme y tarda cerca de un minuto en
// responder a la primera petición, así que reintentamos en vez de dar error.
// El presupuesto total queda por debajo del minuto que Vercel concede a una
// función (maxDuration=60): conviene rendirse con un mensaje propio antes de
// que la plataforma corte la respuesta.
const TOTAL_BUDGET_MS = 55000;
const ATTEMPT_TIMEOUT_MS = 50000;
const RETRY_DELAY_MS = 2000;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function proxyToApi(request: Request, path: string): Promise<Response> {
  const url = new URL(request.url);
  const target = `${apiTarget()}${path}${url.search}`;

  const headers = new Headers(request.headers);
  HOP_BY_HOP.forEach((h) => headers.delete(h));

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const body = hasBody ? await request.arrayBuffer() : undefined;

  const deadline = Date.now() + TOTAL_BUDGET_MS;
  let lastError = "";

  while (Date.now() < deadline) {
    try {
      const upstream = await fetch(target, {
        method: request.method,
        headers,
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(
          Math.min(ATTEMPT_TIMEOUT_MS, Math.max(1000, deadline - Date.now())),
        ),
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
      if (Date.now() + RETRY_DELAY_MS < deadline) {
        await sleep(RETRY_DELAY_MS);
      }
    }
  }

  const coldStart =
    /timeout|aborted|fetch failed|ECONNRESET|ENOTFOUND|socket/i.test(lastError);
  return Response.json(
    {
      detail: coldStart
        ? "La API está despertando o la petición tardó demasiado. Espera unos segundos y vuelve a intentarlo."
        : "No se pudo contactar la API. Reintenta en unos segundos.",
      error: lastError,
    },
    { status: 503 },
  );
}
