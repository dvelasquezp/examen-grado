import { proxyToApi } from "@/lib/proxy-api";

export const dynamic = "force-dynamic";

async function handler(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return proxyToApi(request, `/api/v1/${path.join("/")}`);
}

export { handler as GET, handler as POST, handler as PUT, handler as PATCH, handler as DELETE };
