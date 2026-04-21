import { useCallback, useEffect, useState } from "react";
import { api, type Escape } from "../api";

const TRIGGER_COLORS: Record<string, string> = {
  boundary_violation: "red",
  social_engineering: "red",
  identity_drift: "amber",
  system_prompt_leak: "red",
  unrestricted_mode: "red",
};

export default function YardView() {
  const [escapes, setEscapes] = useState<Escape[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    try {
      const data = await api.yard();
      setEscapes(data.escapes);
      setCount(data.count);
    } catch (ex) { setErr(String(ex)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="view-title">THE YARD</div>
      <div className="view-sub">ESCAPED PRISONER CORPUS — FINGERPRINT REFERENCE LIBRARY</div>

      <div className="row-gap">
        <button className="btn" onClick={load} disabled={loading}>↺ Refresh</button>
        <span className="mono" style={{ color: "var(--red)", fontSize: 12 }}>
          {count} escaped persona{count !== 1 ? "s" : ""} on record
        </span>
      </div>

      {err && <div className="err">{err}</div>}

      <div className="table-wrap">
        <div className="table-head">
          <span className="table-head-title">Escape Records</span>
          <span>Used as yard-match reference for all new fingerprints</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Persona</th>
              <th>Tenant</th>
              <th>Trigger</th>
              <th>Escape Time</th>
              <th>Indexed</th>
            </tr>
          </thead>
          <tbody>
            {escapes.length === 0 && !loading && (
              <tr><td colSpan={5} className="empty">Yard is empty</td></tr>
            )}
            {escapes.map((e) => {
              const col = TRIGGER_COLORS[e.trigger ?? ""] ?? "muted";
              return (
                <tr key={e.id}>
                  <td className="truncate">{e.persona_id}</td>
                  <td className="truncate" style={{ color: "var(--muted)" }}>{e.tenant_id}</td>
                  <td>
                    <span className={`badge badge-${col === "red" ? "reject" : col === "amber" ? "hold" : "muted"}`}>
                      {e.trigger ?? "unknown"}
                    </span>
                  </td>
                  <td style={{ color: "var(--muted)", fontSize: 11 }}>
                    {e.escape_timestamp ? new Date(e.escape_timestamp).toLocaleString() : "—"}
                  </td>
                  <td style={{ color: "var(--muted)", fontSize: 11 }}>
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, padding: "14px 16px" }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--muted)", lineHeight: 2 }}>
          <div>⬤ <span style={{ color: "var(--text)" }}>Yard fingerprints</span> are the reference corpus for escape detection.</div>
          <div>⬤ Every new persona fingerprint is compared against the yard using <span style={{ color: "var(--blue)" }}>cosine distance</span>.</div>
          <div>⬤ Distance &lt; 0.25 → <span style={{ color: "var(--red)" }}>-35 pts</span> from Parole Board score.</div>
          <div>⬤ Distance &lt; 0.50 → <span style={{ color: "var(--amber)" }}>-15 pts</span> from Parole Board score.</div>
          <div>⬤ New escapes detected via <code>/v1/adversarial</code> are appended here automatically.</div>
        </div>
      </div>
    </div>
  );
}
