import { proxyToApi } from "@/lib/proxy-api";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  return proxyToApi(request, "/health");
}
