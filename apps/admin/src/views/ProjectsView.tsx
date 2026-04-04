import React, { useEffect, useState } from 'react';
import { api, Tenant, IngestionJob } from '../api';

interface ProjectSummary {
  project_id: string;
  tenant_id: string;
  tenant_name: string;
  job_count: number;
  entities_created: number;
  latest_status: string;
  latest_updated: string;
}

function buildSummaries(jobs: IngestionJob[], tenantMap: Map<string, string>): ProjectSummary[] {
  const byProject = new Map<string, IngestionJob[]>();
  for (const j of jobs) {
    const list = byProject.get(j.project_id) ?? [];
    list.push(j);
    byProject.set(j.project_id, list);
  }

  const summaries: ProjectSummary[] = [];
  byProject.forEach((pjobs, project_id) => {
    const sorted = [...pjobs].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
    const latest = sorted[0];
    summaries.push({
      project_id,
      tenant_id: latest.tenant_id,
      tenant_name: tenantMap.get(latest.tenant_id) ?? latest.tenant_id,
      job_count: pjobs.length,
      entities_created: pjobs.reduce((s, j) => s + j.entities_created, 0),
      latest_status: latest.status,
      latest_updated: latest.updated_at,
    });
  });

  return summaries.sort(
    (a, b) => new Date(b.latest_updated).getTime() - new Date(a.latest_updated).getTime(),
  );
}

const STATUS_CLASS: Record<string, string> = {
  queued: 'badge-gray',
  processing: 'badge-blue',
  complete: 'badge-green',
  failed: 'badge-red',
};

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
}

export default function ProjectsView() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function loadAll() {
    setLoading(true);
    setErr(null);
    try {
      const ts = await api.tenants.list();
      setTenants(ts);
      const tenantMap = new Map(ts.map(t => [t.tenant_id, t.name]));

      const allJobs: IngestionJob[] = [];
      await Promise.all(
        ts.map(async t => {
          try {
            const jobs = await api.jobs.list(t.tenant_id, 200);
            allJobs.push(...jobs);
          } catch {
            // skip tenants with no job access
          }
        }),
      );

      setProjects(buildSummaries(allJobs, tenantMap));
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []);

  return (
    <div className="view">
      <div className="view-header">
        <h2>Projects</h2>
        <div className="header-actions">
          <button className="btn-ghost" onClick={loadAll}>↺ Refresh</button>
        </div>
      </div>
      <p className="muted" style={{ marginBottom: 16 }}>
        Aggregated from ingestion jobs across all {tenants.length} tenant{tenants.length !== 1 ? 's' : ''}.
      </p>

      {err && <p className="error">{err}</p>}

      {loading ? (
        <p className="muted">Loading…</p>
      ) : projects.length === 0 ? (
        <p className="muted">No projects found. Ingest some files to see them here.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project ID</th>
                <th>Tenant</th>
                <th>Jobs</th>
                <th>Entities</th>
                <th>Latest Status</th>
                <th>Last Updated</th>
              </tr>
            </thead>
            <tbody>
              {projects.map(p => (
                <tr key={p.project_id}>
                  <td className="monospace">{p.project_id}</td>
                  <td>{p.tenant_name}</td>
                  <td>{p.job_count}</td>
                  <td>{p.entities_created.toLocaleString()}</td>
                  <td>
                    <span className={`badge ${STATUS_CLASS[p.latest_status] ?? 'badge-gray'}`}>
                      {p.latest_status}
                    </span>
                  </td>
                  <td>{fmt(p.latest_updated)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
