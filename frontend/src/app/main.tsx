import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "../styles/global.css";
import { recordBrowserDiagnostic } from "../api/diagnostics";

window.addEventListener("error", (event: ErrorEvent) => {
  recordBrowserDiagnostic("frontend.error", event.error?.name ?? "Error");
});
window.addEventListener("unhandledrejection", (event: PromiseRejectionEvent) => {
  const errorType: string = event.reason instanceof Error
    ? event.reason.name
    : typeof event.reason;
  recordBrowserDiagnostic("frontend.unhandled_rejection", errorType);
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
