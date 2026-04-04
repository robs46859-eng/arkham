import React, { useEffect, useState, useCallback } from 'react';
import { api, UsageRollup, Tenant } from '../api';

const PERIOD_OPTIONS = [7, 14, 30, 60, 90] as const;

function BarChart({ data }: { data: { date: string; cost_usd: number; requests: number }[] }) {
  if (!data.length) return null;
  const maxCost = Math.max(...data.map(d => d.cost_usd), 0.001);
  const maxReq  = Math.max(...data.map(d => d.requests), 1);

  return (
    <div className="chart-wrap">
      <div className="chart-legend">
        <span className="legend-dot" style={{ background: 'var(--accent)' }} /> Cost (USD)
        <span className="legend-dot" style={{ background: 'var(--accent2)', marginLeft: 16 }} /> Requests
      </div>
      <div className="bar-chart">
        {data.map(d => (
          <div key={d.date} className="bar-group">
            <div className="bar-pair">
              <div
                className="bar bar-cost"
                style={{ height: `${(d.cost_usd / maxCost) * 100}%` }}
                title={`$${d.cost_usd.toFixed(4)}`}
              />
              <div
                className="bar bar-req"
                style={{ height: `${(d.requests / maxReq) * 100}%` }}
                title={`${d.requests} requests`}
              />
            </div>
            <div className="bar-label">{d.date.slice(5)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function UsageView() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState('');
  const [days, setDays] = useState<number>(30);
  const [data, setData] = useState<UsageRollup | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.tenants.list().then(setTenants).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    setErr(null);
    try {
      const d = await api.usage.rollup(tenantId, days);
      setData(d);
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }, [tenantId, days]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="view">
      <div className="view-header">
        <h2>Usage &amp; Billing</h2>
        <div className="header-actions">
          <select
            value={tenantId}
            onChange={e => setTenantId(e.target.value)}
            style={{ minWidth: 220 }}
          >
            <option value="">— Select tenant —</option>
            {tenants.map(t => (
              <option key={t.tenant_id} value={t.tenant_id}>{t.name}</option>
            ))}
          </select>
          <select value={days} onChange={e => setDays(Number(e.target.value))}>
            {PERIOD_OPTIONS.map(d => (
              <option key={d} value={d}>Last {d} days</option>
            ))}
          </select>
          <button className="btn-ghost" onClick={load} disabled={!tenantId}>↺ Refresh</button>
        </div>
      </div>

      {err && <p className="error">{err}</p>}

      {!tenantId ? (
        <p className="muted">Select a tenant to view usage.</p>
      ) : loading ? (
        <p className="muted">Loading…</p>
      ) : !data ? null : (
        <>
          <div className="stat-row">
            <div className="stat-card">
              <div className="stat-value">{data.total_requests.toLocaleString()}</div>
              <div className="stat-label">Total Requests</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">${data.total_cost_usd.toFixed(4)}</div>
              <div className="stat-label">Total Cost</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{data.period_days}d</div>
              <div className="stat-label">Period</div>
            </div>
          </div>

          {data.daily_breakdown.length > 0 && (
            <section className="chart-section">
              <h3>Daily Breakdown</h3>
              <BarChart data={[...data.daily_breakdown].reverse()} />
            </section>
          )}

          {data.by_service.length > 0 && (
            <section>
              <h3>By Service</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Service</th>
                      <th>Requests</th>
                      <th>Cost (USD)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.by_service.map(s => (
                      <tr key={s.service}>
                        <td>{s.service}</td>
                        <td>{s.requests.toLocaleString()}</td>
                        <td>${s.cost_usd.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
