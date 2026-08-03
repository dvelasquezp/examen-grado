import { proxyToApi } from "@/lib/proxy-api";

export const dynamic = "force-dynamic";
// Margen para que el proxy espere a que la API despierte.
export const maxDuration = 60;

export async function GET(request: Request) {
  return proxyToApi(request, "/health");
}
