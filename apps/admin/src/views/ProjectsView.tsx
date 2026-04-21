import React, { Fragment, useEffect, useState } from 'react';
import { api, DigitalTwinProjectSummary, PredictabilityScale, Tenant } from '../api';

const STATUS_CLASS: Record<string, string> = {
  seeded: 'badge-gray',
  registered: 'badge-blue',
  syncing: 'badge-blue',
  ingested: 'badge-purple',
  active: 'badge-green',
};

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
}

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function bandClass(band: string) {
  switch (band) {
    case 'high':
      return 'badge-green';
    case 'moderate':
      return 'badge-blue';
    case 'low':
      return 'badge-purple';
    default:
      return 'badge-red';
  }
}

function PredictabilityCard({ title, scale }: { title: string; scale: PredictabilityScale }) {
  return (
    <div className="predictability-card">
      <div className="predictability-header">
        <div>
          <div className="cell-primary">{title}</div>
          <div className="cell-sub">{scale.summary}</div>
        </div>
        <div className="predictability-meta">
          <span className={`badge ${bandClass(scale.band)}`}>{scale.band}</span>
          <span className="cell-sub">confidence {pct(scale.confidence)}</span>
        </div>
      </div>
      <div className="predictability-score-row">
        <div className="predictability-scorebar">
          <span style={{ width: `${Math.max(scale.score * 100, 6)}%` }} />
        </div>
        <div className="monospace">{pct(scale.score)}</div>
      </div>
      <div className="predictability-factors">
        {scale.factors.map(factor => (
          <div key={factor.key} className="predictability-factor">
            <div className="predictability-factor-top">
              <span>{factor.label}</span>
              <span className="monospace">{pct(factor.score)}</span>
            </div>
            <div className="predictability-factor-bar">
              <span style={{ width: `${Math.max(factor.score * 100, 4)}%` }} />
            </div>
            <div className="cell-sub">{factor.detail}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ProjectsView() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [projects, setProjects] = useState<DigitalTwinProjectSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function loadAll() {
    setLoading(true);
    setErr(null);
    try {
      const ts = await api.tenants.list();
      setTenants(ts);
      const twins = await api.digitalTwins.projects({ limit: 200 });
      setProjects(twins);
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
        Digital twin readiness across all {tenants.length} tenant{tenants.length !== 1 ? 's' : ''}. Spatial identity remains the future master record; this view starts from current project/domain truth.
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
                <th>Project</th>
                <th>Tenant</th>
                <th>Twin Status</th>
                <th>Readiness</th>
                <th>Coverage</th>
                <th>Issues</th>
                <th>Last Activity</th>
              </tr>
            </thead>
            <tbody>
              {projects.map(p => (
                <Fragment key={p.project_id}>
                  <tr>
                    <td>
                      <div className="cell-primary">{p.project_name}</div>
                      <div className="cell-sub monospace">{p.project_id} · {p.twin_version}</div>
                    </td>
                    <td>{p.tenant_name}</td>
                    <td>
                      <span className={`badge ${STATUS_CLASS[p.twin_status] ?? 'badge-gray'}`}>
                        {p.twin_status}
                      </span>
                    </td>
                    <td>{Math.round(p.readiness_score * 100)}%</td>
                    <td>
                      <div className="cell-primary">{p.building_element_count} elements · {p.document_chunk_count} chunks</div>
                      <div className="cell-sub">
                        {Object.entries(p.file_counts).length === 0
                          ? 'No registered files'
                          : Object.entries(p.file_counts).map(([type, count]) => `${type}:${count}`).join(' · ')}
                      </div>
                    </td>
                    <td>
                      <div className="cell-primary">{p.issue_count} total · {p.high_severity_issue_count} high</div>
                      <div className="cell-sub">{p.alerts.length ? p.alerts.join(' · ') : 'no active alerts'}</div>
                    </td>
                    <td>
                      <div className="cell-primary">{p.latest_activity_at ? fmt(p.latest_activity_at) : '—'}</div>
                      <div className="cell-sub">ingestion {p.latest_ingestion_status ?? 'not started'}</div>
                    </td>
                  </tr>
                  <tr className="governance-detail-row">
                    <td colSpan={7}>
                      <div className="predictability-grid">
                        <PredictabilityCard title="Operational Predictability" scale={p.operational_predictability} />
                        <PredictabilityCard title="Environmental Predictability" scale={p.environmental_predictability} />
                      </div>
                    </td>
                  </tr>
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
