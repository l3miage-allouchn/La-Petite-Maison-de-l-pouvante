/** Liveness/readiness probe (container HEALTHCHECK, Kubernetes probes). */
export function GET() {
  return Response.json({ status: "UP" }, { headers: { "Cache-Control": "no-store" } });
}
