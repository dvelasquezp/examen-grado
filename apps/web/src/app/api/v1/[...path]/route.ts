import { proxyToApi } from "@/lib/proxy-api";

export const dynamic = "force-dynamic";
// Margen para que el proxy espere a que la API despierte.
export const maxDuration = 60;

async function handler(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return proxyToApi(request, `/api/v1/${path.join("/")}`);
}

export { handler as GET, handler as POST, handler as PUT, handler as PATCH, handler as DELETE };
