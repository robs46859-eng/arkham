import { useCallback, useState } from "react";
import { api } from "../api";

export default function StixView() {
  const [bundle, setBundle] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    try {
      const data = await api.stix();
      setBundle(data);
    } catch (ex) { setErr(String(ex)); }
    finally { setLoading(false); }
  }, []);

  function download() {
    if (!bundle) return;
    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `arkham-stix-${Date.now()}.json`;
    a.click();
  }

  const objects = (bundle?.objects as unknown[]) ?? [];
  const verdicts = objects.filter((o: unknown) => (o as Record<string,unknown>)["type"] === "observed-data");
  const threats = objects.filter((o: unknown) => (o as Record<string,unknown>)["type"] === "threat-actor");

  return (
    <div>
      <div className="view-title">STIX EXPORT</div>
      <div className="view-sub">THREAT INTELLIGENCE BUNDLE — STIX 2.1 FORMAT — REAL GOVERNANCE DATA</div>

      <div className="row-gap">
        <button className="btn" onClick={load} disabled={loading}>
          {loading ? "Loading..." : "⬇ Fetch Bundle"}
        </button>
        {bundle && (
          <button className="btn btn-green" onClick={download}>↓ Download JSON</button>
        )}
        {bundle && (
          <>
            <span className="badge badge-approve">{verdicts.length} verdicts</span>
            <span className="badge badge-reject">{threats.length} threat actors</span>
          </>
        )}
      </div>

      {err && <div className="err">{err}</div>}

      {bundle && (
        <>
          <div style={{ marginBottom: 12, fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--muted)" }}>
            Bundle ID: <span style={{ color: "var(--text)" }}>{bundle["id"] as string}</span>
            {"  "}Spec: <span style={{ color: "var(--blue)" }}>{bundle["spec_version"] as string}</span>
          </div>
          <div className="stix-box">
            {JSON.stringify(bundle, null, 2)}
          </div>
        </>
      )}
    </div>
  );
}
