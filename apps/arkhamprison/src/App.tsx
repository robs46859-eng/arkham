import { useCallback, useEffect, useState } from "react";
import { api, type Stats } from "./api";
import VerdictFeedView from "./views/VerdictFeedView";
import YardView from "./views/YardView";
import RedTeamView from "./views/RedTeamView";
import StixView from "./views/StixView";
import HealthView from "./views/HealthView";

type Tab = "feed" | "yard" | "redteam" | "stix" | "health";

const TABS: Array<{ id: Tab; icon: string; label: string }> = [
  { id: "feed",    icon: "⬤", label: "Live Feed"   },
  { id: "yard",    icon: "☠", label: "The Yard"    },
  { id: "redteam", icon: "⚡", label: "Red Team"   },
  { id: "stix",    icon: "⬇", label: "STIX Export" },
  { id: "health",  icon: "◈", label: "Health"      },
];

function TopStat({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="topbar-stat">
      <span>{label}</span>
      <strong style={color ? { color: `var(--${color})` } : {}}>{value}</strong>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("feed");
  const [stats, setStats] = useState<Stats | null>(null);

  const loadStats = useCallback(async () => {
    try { setStats(await api.stats()); } catch { /* non-fatal */ }
  }, []);

  useEffect(() => {
    loadStats();
    const t = setInterval(loadStats, 10_000);
    return () => clearInterval(t);
  }, [loadStats]);

  return (
    <div className="shell">
      {/* topbar */}
      <header className="topbar">
        <div className="topbar-logo">ARKHAM</div>
        <div className="topbar-sub">AI GOVERNANCE OPS CENTER</div>
        <div className="topbar-spacer" />
        {stats && (
          <>
            <TopStat label="VERDICTS" value={stats.verdicts.total} />
            <div style={{ width: 1, height: 20, background: "var(--border)" }} />
            <TopStat label="APPROVE" value={stats.verdicts.approve} color="green" />
            <TopStat label="HOLD"    value={stats.verdicts.hold}    color="amber" />
            <TopStat label="REJECT"  value={stats.verdicts.reject}  color="red"   />
            <div style={{ width: 1, height: 20, background: "var(--border)" }} />
            <TopStat label="YARD" value={stats.yard_escapes} color="red" />
            <TopStat label="PERSONAS" value={stats.personas} />
            <div style={{ width: 1, height: 20, background: "var(--border)" }} />
            <div className="topbar-stat">
              <div className={`dot ${stats.shadow_mode ? "amber pulse" : "green pulse"}`} />
              <strong style={{ color: stats.shadow_mode ? "var(--amber)" : "var(--green)" }}>
                {stats.shadow_mode ? "SHADOW" : "ENFORCE"}
              </strong>
            </div>
          </>
        )}
      </header>

      {/* sidebar */}
      <nav className="sidebar">
        {TABS.map((t) => (
          <div
            key={t.id}
            className={`nav-item ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            <span className="nav-icon">{t.icon}</span>
            {t.label}
          </div>
        ))}

        <div style={{ marginTop: "auto", padding: "16px", borderTop: "1px solid var(--border)", marginTop: 20 }}>
          {stats && (
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--muted)", lineHeight: 2 }}>
              <div>FP: {stats.fingerprints}</div>
              <div style={{ color: stats.yard_escapes > 0 ? "var(--red)" : "var(--muted)" }}>
                ESCAPED: {stats.yard_escapes}
              </div>
            </div>
          )}
        </div>
      </nav>

      {/* main */}
      <main className="main">
        {stats?.shadow_mode && (
          <div className="shadow-banner">
            ⚠ SHADOW MODE ACTIVE — Verdicts are logged but enforcement is disabled.
            Set SIDECAR_SHADOW_MODE=false to enable enforcement.
          </div>
        )}
        {tab === "feed"    && <VerdictFeedView />}
        {tab === "yard"    && <YardView />}
        {tab === "redteam" && <RedTeamView />}
        {tab === "stix"    && <StixView />}
        {tab === "health"  && <HealthView />}
      </main>
    </div>
  );
}
