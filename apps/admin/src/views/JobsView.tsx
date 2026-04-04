import React, { useEffect, useState, useCallback } from 'react';
import { api, IngestionJob, Tenant } from '../api';

const STATUS_CLASS: Record<string, string> = {
  queued: 'badge-gray',
  processing: 'badge-blue',
  complete: 'badge-green',
  failed: 'badge-red',
};

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'short',
    timeStyle: 'short',
  });
}

export default function JobsView() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState('');
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    api.tenants.list().then(setTenants).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    setErr(null);
    try {
      const data = await api.jobs.list(tenantId);
      setJobs(data);
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="view">
      <div className="view-header">
        <h2>Ingestion Jobs</h2>
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
          <button className="btn-ghost" onClick={load} disabled={!tenantId}>↺ Refresh</button>
        </div>
      </div>

      {err && <p className="error">{err}</p>}

      {!tenantId ? (
        <p className="muted">Select a tenant to view their ingestion jobs.</p>
      ) : loading ? (
        <p className="muted">Loading…</p>
      ) : jobs.length === 0 ? (
        <p className="muted">No jobs found for this tenant.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Job ID</th>
                <th>File ID</th>
                <th>Project</th>
                <th>Status</th>
                <th>Entities</th>
                <th>Created</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(j => (
                <React.Fragment key={j.job_id}>
                  <tr
                    className={j.error_log ? 'has-error' : ''}
                    onClick={() => setExpanded(expanded === j.job_id ? null : j.job_id)}
                    style={{ cursor: j.error_log ? 'pointer' : 'default' }}
                  >
                    <td>
                      <div className="cell-primary monospace">{j.job_id.slice(0, 16)}…</div>
                    </td>
                    <td className="monospace">{j.file_id.slice(0, 12)}…</td>
                    <td className="monospace">{j.project_id}</td>
                    <td>
                      <span className={`badge ${STATUS_CLASS[j.status] ?? 'badge-gray'}`}>
                        {j.status}
                      </span>
                    </td>
                    <td>{j.entities_created.toLocaleString()}</td>
                    <td>{fmt(j.created_at)}</td>
                    <td>{fmt(j.updated_at)}</td>
                  </tr>
                  {expanded === j.job_id && j.error_log && (
                    <tr className="error-row">
                      <td colSpan={7}>
                        <pre className="error-log">{j.error_log}</pre>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
          <p className="muted" style={{ marginTop: 8 }}>
            {jobs.length} job{jobs.length !== 1 ? 's' : ''} — click a failed row to see the error log
          </p>
        </div>
      )}
    </div>
  );
}
