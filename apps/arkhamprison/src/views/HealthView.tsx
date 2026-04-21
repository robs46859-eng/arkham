import { useCallback, useEffect, useState } from "react";
import { checkServiceHealth, type ServiceHealth } from "../api";

const SERVICES: Array<{ name: string; url: string }> = [
  { name: "arkham", url: `${import.meta.env.VITE_ARKHAM_URL ?? ""}/health` },
  { name: "gateway", url: `${import.meta.env.VITE_GATEWAY_URL ?? ""}/health` },
  { name: "privacy", url: `${import.meta.env.VITE_PRIVACY_URL ?? ""}/health` },
  { name: "fs-ai", url: `${import.meta.env.VITE_FSAI_URL ?? ""}/health` },
  { name: "robco-core", url: `${import.meta.env.VITE_CORE_URL ?? ""}/health` },
  { name: "omniscale", url: `${import.meta.env.VITE_OMNISCALE_URL ?? ""}/health` },
];

export default function HealthView() {
  const [services, setServices] = useState<ServiceHealth[]>(
    SERVICES.map((s) => ({ ...s, status: "checking" }))
  );
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  const checkAll = useCallback(async () => {
    setServices(SERVICES.map((s) => ({ ...s, status: "checking" })));
    const results = await Promise.all(
      SERVICES.map(async (s) => {
        if (!s.url.startsWith("http")) return { ...s, status: "error" as const, latency_ms: 0 };
        const r = await checkServiceHealth(s.url);
        return { ...s, ...r };
      })
    );
    setServices(results);
    setLastChecked(new Date().toLocaleTimeString());
  }, []);

  useEffect(() => {
    checkAll();
    const t = setInterval(checkAll, 30_000);
    return () => clearInterval(t);
  }, [checkAll]);

  const ok = services.filter((s) => s.status === "ok").length;
  const err = services.filter((s) => s.status === "error").length;

  return (
    <div>
      <div className="view-title">SERVICE HEALTH</div>
      <div className="view-sub">LIVE STATUS — ALL CLOUD RUN SERVICES — AUTO-REFRESH 30s</div>

      <div className="stat-grid" style={{ marginBottom: 20 }}>
        <div className="stat-card">
          <div className="stat-label">Online</div>
          <div className="stat-value green">{ok}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Degraded</div>
          <div className="stat-value red">{err}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Last Check</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--text)", marginTop: 4 }}>
            {lastChecked ?? "—"}
          </div>
        </div>
      </div>

      <div className="row-gap">
        <button className="btn" onClick={checkAll}>↺ Check Now</button>
      </div>

      <div className="health-grid">
        {services.map((s) => (
          <div className="health-card" key={s.name}>
            <div className={`dot ${s.status === "ok" ? "green pulse" : s.status === "error" ? "red" : "amber pulse"}`} />
            <div>
              <div className="health-name">{s.name}</div>
              <div className="health-url">{s.url || "not configured"}</div>
            </div>
            {s.latency_ms != null && s.status !== "checking" && (
              <div className="health-latency">{s.latency_ms}ms</div>
            )}
            {s.status === "checking" && (
              <div className="health-latency" style={{ color: "var(--amber)" }}>…</div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 20, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, padding: "14px 16px" }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--muted)", lineHeight: 2 }}>
          <div>Configure service URLs via environment variables:</div>
          <div style={{ color: "var(--text)" }}>VITE_ARKHAM_URL, VITE_GATEWAY_URL, VITE_PRIVACY_URL,</div>
          <div style={{ color: "var(--text)" }}>VITE_FSAI_URL, VITE_CORE_URL, VITE_OMNISCALE_URL</div>
        </div>
      </div>
    </div>
  );
}
