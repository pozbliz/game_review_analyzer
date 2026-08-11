import { useEffect, useState } from "react";
import { getHealth, getPublicConfig } from "../api/shell";

type HealthState = "loading" | "ready" | "unavailable";

export default function App(): JSX.Element {
  const [health, setHealth] = useState<HealthState>("loading");

  useEffect(() => {
    let active = true;
    Promise.all([getHealth(), getPublicConfig()])
      .then(() => {
        if (active) setHealth("ready");
      })
      .catch(() => {
        if (active) setHealth("unavailable");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="shell">
      <p className="eyebrow">GAME REVIEW ANALYZER</p>
      <h1>Evidence-backed review research, locally.</h1>
      <p className="intro">The application shell is ready for the Catalog workflow.</p>
      <p className={`health health-${health}`} role="status">
        Backend {health === "loading" ? "checking…" : health === "ready" ? "connected" : "unavailable"}
      </p>
    </main>
  );
}
