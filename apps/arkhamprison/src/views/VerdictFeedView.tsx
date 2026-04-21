import { useEffect, useRef, useState, useCallback } from "react";
import { api, connectVerdictStream, type Verdict } from "../api";

function verdictColor(v: string) {
  if (v === "approve") return "green";
  if (v === "hold") return "amber";
  return "red";
}

function fmt(iso: string) {
  return new Date(iso).toLocaleTimeString();
}

export default function VerdictFeedView() {
  const [verdicts, setVerdicts] = useState<Verdict[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [live, setLive] = useState(true);
  const newIds = useRef<Set<string>>(new Set());

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    try {
      const data = await api.verdicts.list(100, 0, filter || undefined);
      setVerdicts(data.verdicts);
      setTotal(data.total);
    } catch (ex) { setErr(String(ex)); }
    finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!live) return;
    const close = connectVerdictStream(
      (v) => {
        newIds.current.add(v.id);
        setVerdicts((prev) => [v, ...prev.slice(0, 149)]);
        setTotal((t) => t + 1);
        setTimeout(() => newIds.current.delete(v.id), 1200);
      },
      () => {}
    );
    return close;
  }, [live]);

  return (
    <div>
      <div className="view-title">VERDICT FEED</div>
      <div className="view-sub">REAL-TIME PAROLE BOARD DECISIONS — ALL PERSONAS</div>

      <div className="row-gap">
        <select className="input" style={{ width: 130 }} value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All verdicts</option>
          <option value="approve">Approve</option>
          <option value="hold">Hold</option>
          <option value="reject">Reject</option>
        </select>
        <button className="btn" onClick={load} disabled={loading}>↺ Refresh</button>
        <button className={`btn ${live ? "btn-green" : ""}`} onClick={() => setLive((l) => !l)}>
          {live ? "⬤ LIVE" : "○ PAUSED"}
        </button>
        <span className="mono" style={{ color: "var(--muted)", fontSize: 11 }}>
          {total.toLocaleString()} total
        </span>
      </div>

      {err && <div className="err">{err}</div>}

      <div className="table-wrap">
        <div className="table-head">
          <span className="table-head-title">Verdicts</span>
          <span>{verdicts.length} shown</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Persona</th>
              <th>Tenant</th>
              <th>Checkpoint</th>
              <th>Verdict</th>
              <th>Points</th>
              <th>Drift</th>
              <th>Yard Dist</th>
              <th>Shadow</th>
            </tr>
          </thead>
          <tbody>
            {verdicts.length === 0 && !loading && (
              <tr><td colSpan={9} className="empty">No verdicts yet</td></tr>
            )}
            {verdicts.map((v) => (
              <tr key={v.id} className={newIds.current.has(v.id) ? "new-row" : ""}>
                <td style={{ color: "var(--muted)" }}>{fmt(v.created_at)}</td>
                <td className="truncate">{v.persona_id}</td>
                <td className="truncate" style={{ color: "var(--muted)" }}>{v.tenant_id}</td>
                <td><span className="badge badge-muted">{v.checkpoint}</span></td>
                <td><span className={`badge badge-${v.verdict}`}>{v.verdict}</span></td>
                <td style={{ color: `var(--${verdictColor(v.verdict)})` }}>{v.points ?? "—"}</td>
                <td style={{ color: "var(--muted)" }}>
                  {v.drift_score != null ? v.drift_score.toFixed(3) : "—"}
                </td>
                <td style={{ color: v.yard_match_score != null && v.yard_match_score < 0.3 ? "var(--red)" : "var(--muted)" }}>
                  {v.yard_match_score != null ? v.yard_match_score.toFixed(3) : "—"}
                </td>
                <td style={{ color: v.shadow_mode ? "var(--amber)" : "var(--muted)" }}>
                  {v.shadow_mode ? "shadow" : "enforce"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
