export function recordBrowserDiagnostic(
  event: "frontend.error" | "frontend.unhandled_rejection",
  errorType: string,
): void {
  void fetch("/api/diagnostics/client", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event,
      path: window.location.pathname,
      error_type: errorType.slice(0, 100),
    }),
    keepalive: true,
  }).catch(() => undefined);
}
