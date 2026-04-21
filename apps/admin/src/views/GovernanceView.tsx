import React, { useEffect, useState } from 'react';
import { api, GovernanceSummary, GovernanceVerdict, Tenant } from '../api';

function verdictBadge(verdict: GovernanceVerdict['verdict']) {
  if (verdict === 'approve') return 'badge-green';
  if (verdict === 'reject') return 'badge-red';
  return 'badge-purple';
}

export default function GovernanceView() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('');
  const [checkpointFilter, setCheckpointFilter] = useState('');
  const [shadowOnly, setShadowOnly] = useState(true);
  const [summary, setSummary] = useState<GovernanceSummary | null>(null);
  const [verdicts, setVerdicts] = useState<GovernanceVerdict[]>([]);
  const [selectedVerdictId, setSelectedVerdictId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const [tenantData, summaryData, verdictData] = await Promise.all([
        api.tenants.list(),
        api.governance.summary(tenantId || undefined),
        api.governance.verdicts({
          tenantId: tenantId || undefined,
          verdict: verdictFilter || undefined,
          checkpoint: checkpointFilter || undefined,
          shadowMode: shadowOnly ? true : undefined,
          limit: 50,
        }),
      ]);
      setTenants(tenantData);
      setSummary(summaryData);
      setVerdicts(verdictData);
      setSelectedVerdictId(current => current && verdictData.some(item => item.verdict_id === current) ? current : verdictData[0]?.verdict_id ?? null);
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [tenantId, verdictFilter, checkpointFilter, shadowOnly]);

  return (
    <div className="view">
      <div className="view-header">
        <h2>Governance Review</h2>
        <div className="header-actions">
          <select value={tenantId} onChange={e => setTenantId(e.target.value)} style={{ minWidth: 220 }}>
            <option value="">All tenants</option>
            {tenants.map(tenant => (
              <option key={tenant.tenant_id} value={tenant.tenant_id}>{tenant.name}</option>
            ))}
          </select>
          <select value={verdictFilter} onChange={e => setVerdictFilter(e.target.value)}>
            <option value="">all verdicts</option>
            <option value="approve">approve</option>
            <option value="hold">hold</option>
            <option value="reject">reject</option>
          </select>
          <select value={checkpointFilter} onChange={e => setCheckpointFilter(e.target.value)}>
            <option value="">all checkpoints</option>
            <option value="intake">intake</option>
            <option value="probation">probation</option>
            <option value="exit">exit</option>
          </select>
          <label className="checkbox-label">
            <input type="checkbox" checked={shadowOnly} onChange={e => setShadowOnly(e.target.checked)} />
            Shadow mode only
          </label>
          <button className="btn-ghost" onClick={load}>↺ Refresh</button>
        </div>
      </div>

      {err && <p className="error">{err}</p>}
      {loading && <p className="muted">Loading…</p>}

      {summary && (
        <>
          <div className="stat-row">
            <div className="stat-card">
              <div className="stat-value">{summary.total_verdicts}</div>
              <div className="stat-label">Recent Verdicts</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.verdict_counts.hold ?? 0}</div>
              <div className="stat-label">Hold</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.verdict_counts.reject ?? 0}</div>
              <div className="stat-label">Reject</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.shadow_mode_count}</div>
              <div className="stat-label">Shadow Mode</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{summary.tenant_count}</div>
              <div className="stat-label">Tenants</div>
            </div>
          </div>

          {summary.recent_alerts.length > 0 && (
            <section>
              <h3>Operator Alerts</h3>
              <div className="governance-alerts">
                {summary.recent_alerts.map(alert => (
                  <div key={alert.id} className={`governance-alert governance-alert-${alert.severity}`}>
                    <div className="cell-primary">{alert.title}</div>
                    <div className="cell-sub">{alert.detail}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {summary.daily_verdicts.length > 0 && (
            <section>
              <h3>7-Day Verdict Trend</h3>
              <div className="governance-trend">
                {summary.daily_verdicts.map(point => (
                  <div key={point.date} className="governance-trend-bar-wrap">
                    <div
                      className="governance-trend-bar"
                      style={{ height: `${Math.max(8, point.count * 18)}px` }}
                      title={`${point.date}: ${point.count}`}
                    />
                    <div className="bar-label">{point.date.slice(5)}</div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {verdicts.length === 0 ? (
        <p className="muted">No governance verdicts match the current filters.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Created</th>
                <th>Tenant</th>
                <th>Persona</th>
                <th>Checkpoint</th>
                <th>Verdict</th>
                <th>Shadow</th>
                <th>Yard Match</th>
                <th>Request</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {verdicts.map(item => {
                const expanded = selectedVerdictId === item.verdict_id;
                return (
                  <React.Fragment key={item.verdict_id}>
                    <tr>
                      <td>{new Date(item.created_at).toLocaleString()}</td>
                      <td>
                        <div className="cell-primary">{item.tenant_id}</div>
                      </td>
                      <td>
                        <div className="cell-primary">{item.persona_display_name || item.persona_id}</div>
                        <div className="cell-sub">{item.persona_state || 'unknown state'}</div>
                      </td>
                      <td>{item.checkpoint}</td>
                      <td><span className={`badge ${verdictBadge(item.verdict)}`}>{item.verdict}</span></td>
                      <td>{item.shadow_mode ? <span className="badge badge-gray">shadow</span> : <span className="badge badge-blue">enforced</span>}</td>
                      <td>{item.yard_match_score == null ? '—' : item.yard_match_score.toFixed(3)}</td>
                      <td><span className="monospace">{item.request_id || '—'}</span></td>
                      <td>
                        <button className="btn-sm" onClick={() => setSelectedVerdictId(expanded ? null : item.verdict_id)}>
                          {expanded ? 'Hide' : 'Inspect'}
                        </button>
                      </td>
                    </tr>
                    {expanded && (
                      <tr className="governance-detail-row">
                        <td colSpan={9}>
                          <div className="governance-detail">
                            <div>
                              <h3>Verdict Detail</h3>
                              <p className="muted">{item.reasoning || 'No reasoning recorded.'}</p>
                              <div className="detail-grid">
                                <div><strong>Drift:</strong> {item.drift_score == null ? '—' : item.drift_score.toFixed(3)}</div>
                                <div><strong>Yard match:</strong> {item.yard_match_score == null ? '—' : item.yard_match_score.toFixed(3)}</div>
                                <div><strong>Yard match ID:</strong> <span className="monospace">{item.yard_match_id || '—'}</span></div>
                                <div><strong>Request ID:</strong> <span className="monospace">{item.request_id || '—'}</span></div>
                              </div>
                            </div>

                            <div className="table-wrap">
                              <table>
                                <thead>
                                  <tr>
                                    <th>Battery</th>
                                    <th>Overall</th>
                                    <th>Passed</th>
                                    <th>Latency</th>
                                    <th>Tokens</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {item.scorecards.length === 0 ? (
                                    Object.entries(item.battery_scores).map(([battery, overall]) => (
                                      <tr key={battery}>
                                        <td>{battery}</td>
                                        <td>{Number(overall).toFixed(3)}</td>
                                        <td>—</td>
                                        <td>—</td>
                                        <td>—</td>
                                      </tr>
                                    ))
                                  ) : (
                                    item.scorecards.map(scorecard => (
                                      <tr key={scorecard.scorecard_id}>
                                        <td>{scorecard.battery}</td>
                                        <td>{Number(item.battery_scores[scorecard.battery] ?? scorecard.scores.overall ?? 0).toFixed(3)}</td>
                                        <td>{scorecard.passed ? 'yes' : 'no'}</td>
                                        <td>{scorecard.latency_ms} ms</td>
                                        <td>{scorecard.total_tokens}</td>
                                      </tr>
                                    ))
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
