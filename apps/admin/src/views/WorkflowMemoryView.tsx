import React, { useEffect, useState } from 'react';
import {
  api,
  Tenant,
  WorkflowExecution,
  WorkflowExecutionDelivery,
  WorkflowMemoryConfig,
  WorkflowMemoryDecision,
  WorkflowMemoryMetrics,
  WorkflowReviewQueueItem,
} from '../api';

const OUTCOME_KEYS = ['send_approval', 'delivered', 'reply', 'booking', 'rejection'] as const;

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function WorkflowMemoryView() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState('');
  const [workflowType, setWorkflowType] = useState('fullstack_outreach');
  const [offerType, setOfferType] = useState('agency');
  const [stage, setStage] = useState('first_touch');
  const [config, setConfig] = useState<WorkflowMemoryConfig | null>(null);
  const [metrics, setMetrics] = useState<WorkflowMemoryMetrics | null>(null);
  const [decisions, setDecisions] = useState<WorkflowMemoryDecision[]>([]);
  const [reviewQueue, setReviewQueue] = useState<WorkflowReviewQueueItem[]>([]);
  const [executionByReviewItem, setExecutionByReviewItem] = useState<Record<string, WorkflowExecution>>({});
  const [deliveryByReviewItem, setDeliveryByReviewItem] = useState<Record<string, WorkflowExecutionDelivery>>({});
  const [deliveryHistoryByReviewItem, setDeliveryHistoryByReviewItem] = useState<Record<string, WorkflowExecutionDelivery[]>>({});
  const [deliveringReviewItemId, setDeliveringReviewItemId] = useState<string | null>(null);
  const [decisionFilter, setDecisionFilter] = useState('');
  const [borderlineOnly, setBorderlineOnly] = useState(true);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function loadConfig() {
    const data = await api.workflowMemory.config();
    setConfig(data);
  }

  async function loadMetrics(currentTenantId: string) {
    if (!currentTenantId) return;
    const [metricsData, decisionsData, reviewQueueData] = await Promise.all([
      api.workflowMemory.metrics(currentTenantId, {
        workflowType,
        offerType,
        stage,
      }),
      api.workflowMemory.decisions(currentTenantId, {
        workflowType,
        offerType,
        stage,
        decision: decisionFilter || undefined,
        borderlineOnly,
        limit: 25,
      }),
      api.workflowMemory.reviewQueue(currentTenantId, {
        reviewStatus: 'approved',
        limit: 25,
      }),
    ]);
    setMetrics(metricsData);
    setDecisions(decisionsData);
    setReviewQueue(
      reviewQueueData.filter(item => {
        const metadata = item.metadata ?? {};
        const workflowContext = (metadata.workflow_context as Record<string, unknown> | undefined) ?? {};
        const executionContract = (metadata.execution_contract as Record<string, unknown> | undefined) ?? {};
        return (
          workflowContext.workflow_type === workflowType &&
          workflowContext.offer_type === offerType &&
          workflowContext.stage === stage &&
          executionContract.channel === 'email'
        );
      }),
    );
  }

  async function loadAll(currentTenantId = tenantId) {
    setLoading(true);
    setErr(null);
    try {
      const [tenantData] = await Promise.all([
        api.tenants.list(),
        loadConfig(),
      ]);
      setTenants(tenantData);
      if (!tenantId && tenantData[0]) {
        currentTenantId = tenantData[0].tenant_id;
        setTenantId(currentTenantId);
      }
      if (currentTenantId) {
        await loadMetrics(currentTenantId);
      }
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []);

  useEffect(() => {
    if (tenantId) {
      loadMetrics(tenantId).catch(ex => setErr(String(ex)));
    }
  }, [tenantId, workflowType, offerType, stage, decisionFilter, borderlineOnly]);

  async function saveConfig() {
    if (!config) return;
    setSaving(true);
    setErr(null);
    try {
      const updated = await api.workflowMemory.updateConfig({
        configured_reuse_min_score: config.configured_reuse_min_score,
        outcome_weights: config.outcome_weights,
      });
      setConfig(updated);
      if (tenantId) await loadMetrics(tenantId);
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setSaving(false);
    }
  }

  async function runDryRunDelivery(item: WorkflowReviewQueueItem) {
    setDeliveringReviewItemId(item.review_item_id);
    setErr(null);
    try {
      const execution = await api.workflowMemory.createExecution(item.review_item_id, {
        executionStatus: 'queued',
        metadata: {
          mode: 'admin_dry_run',
          source: 'workflow-memory-view',
        },
      });
      const delivery = await api.workflowMemory.deliverExecution(execution.execution_id, {
        metadata: {
          adapter: 'smtp-email',
          mode: 'dry_run',
          source: 'workflow-memory-view',
        },
      });
      const history = await api.workflowMemory.deliveryHistory(execution.execution_id);
      setExecutionByReviewItem(prev => ({ ...prev, [item.review_item_id]: execution }));
      setDeliveryByReviewItem(prev => ({ ...prev, [item.review_item_id]: delivery }));
      setDeliveryHistoryByReviewItem(prev => ({ ...prev, [item.review_item_id]: history }));
      if (tenantId) {
        await loadMetrics(tenantId);
      }
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setDeliveringReviewItemId(null);
    }
  }

  return (
    <div className="view">
      <div className="view-header">
        <h2>Workflow Memory</h2>
        <div className="header-actions">
          <button className="btn-ghost" onClick={() => loadAll()}>↺ Refresh</button>
        </div>
      </div>

      {err && <p className="error">{err}</p>}
      {loading && <p className="muted">Loading…</p>}

      {config && (
        <section className="create-form" style={{ marginBottom: 20 }}>
          <h3>Threshold & Weights</h3>
          <label>
            Configured reuse minimum score
            <input
              type="number"
              step="0.1"
              value={config.configured_reuse_min_score}
              onChange={e => setConfig({
                ...config,
                configured_reuse_min_score: Number(e.target.value),
              })}
            />
          </label>
          <p className="muted" style={{ marginTop: 8 }}>
            Automatic reuse requires a nonnegative score. Effective threshold is{' '}
            <strong>{config.effective_reuse_min_score.toFixed(1)}</strong>, with a hard floor of{' '}
            <strong>{config.auto_reuse_score_floor.toFixed(1)}</strong>.
          </p>
          <div className="stat-row" style={{ marginTop: 12 }}>
            {OUTCOME_KEYS.map(key => (
              <div className="stat-card" key={key} style={{ minWidth: 140 }}>
                <div className="stat-label" style={{ marginBottom: 8 }}>{key}</div>
                <input
                  type="number"
                  step="0.1"
                  value={config.outcome_weights[key] ?? 0}
                  onChange={e => setConfig({
                    ...config,
                    outcome_weights: {
                      ...config.outcome_weights,
                      [key]: Number(e.target.value),
                    },
                  })}
                  style={{ width: '100%' }}
                />
              </div>
            ))}
          </div>
          <div className="form-actions" style={{ marginTop: 12 }}>
            <button className="btn-primary" onClick={saveConfig} disabled={saving}>
              {saving ? 'Saving…' : 'Save Policy'}
            </button>
          </div>
        </section>
      )}

      <section className="create-form">
        <h3>Tenant Metrics</h3>
        <div className="header-actions" style={{ marginBottom: 12 }}>
          <select value={tenantId} onChange={e => setTenantId(e.target.value)} style={{ minWidth: 220 }}>
            <option value="">— Select tenant —</option>
            {tenants.map(t => (
              <option key={t.tenant_id} value={t.tenant_id}>{t.name}</option>
            ))}
          </select>
          <input value={workflowType} onChange={e => setWorkflowType(e.target.value)} placeholder="workflow_type" />
          <input value={offerType} onChange={e => setOfferType(e.target.value)} placeholder="offer_type" />
          <input value={stage} onChange={e => setStage(e.target.value)} placeholder="stage" />
          <select value={decisionFilter} onChange={e => setDecisionFilter(e.target.value)}>
            <option value="">all decisions</option>
            <option value="reuse">reuse</option>
            <option value="regenerate">regenerate</option>
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={borderlineOnly} onChange={e => setBorderlineOnly(e.target.checked)} />
            borderline only
          </label>
        </div>

        {!metrics ? (
          <p className="muted">Select a tenant to inspect workflow-memory behavior.</p>
        ) : (
          <>
            <div className="stat-row">
              <div className="stat-card">
                <div className="stat-value">{pct(metrics.hit_rate)}</div>
                <div className="stat-label">Hit Rate</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{pct(metrics.fallback_rate)}</div>
                <div className="stat-label">Fallback Rate</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{pct(metrics.version_mismatch_rate)}</div>
                <div className="stat-label">Version Mismatch</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{metrics.average_estimated_time_saved_ms.toFixed(0)} ms</div>
                <div className="stat-label">Avg Time Saved</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{metrics.outcome_score.toFixed(2)}</div>
                <div className="stat-label">Outcome Score</div>
              </div>
            </div>

            <div className="table-wrap" style={{ marginTop: 16 }}>
              <table>
                <thead>
                  <tr>
                    <th>Recall Attempts</th>
                    <th>Recall Hits</th>
                    <th>Fallbacks</th>
                    <th>Total Time Saved</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>{metrics.recall_attempts}</td>
                    <td>{metrics.recall_hits}</td>
                    <td>{metrics.fallback_count}</td>
                    <td>{metrics.total_estimated_time_saved_ms} ms</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="table-wrap" style={{ marginTop: 16 }}>
              <table>
                <thead>
                  <tr>
                    <th>Fallback Reason</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(metrics.fallback_reasons).length === 0 ? (
                    <tr><td colSpan={2}>No fallback reasons recorded.</td></tr>
                  ) : (
                    Object.entries(metrics.fallback_reasons).map(([reason, count]) => (
                      <tr key={reason}>
                        <td>{reason}</td>
                        <td>{count}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="table-wrap" style={{ marginTop: 16 }}>
              <table>
                <thead>
                  <tr>
                    <th>Outcome</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(metrics.outcome_counts).map(([outcome, count]) => (
                    <tr key={outcome}>
                      <td>{outcome}</td>
                      <td>{count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="table-wrap" style={{ marginTop: 16 }}>
              <table>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Decision</th>
                    <th>Reason</th>
                    <th>Score / Threshold</th>
                    <th>Why</th>
                    <th>Stored</th>
                    <th>Saved</th>
                    <th>Request</th>
                  </tr>
                </thead>
                <tbody>
                  {decisions.length === 0 ? (
                    <tr><td colSpan={8}>No decision traces match the current filters.</td></tr>
                  ) : (
                    decisions.map(item => (
                      <tr key={item.decision_id}>
                        <td>{new Date(item.created_at).toLocaleString()}</td>
                        <td>{item.decision}</td>
                        <td>{item.fallback_reason ?? 'hit'}</td>
                        <td>
                          {item.recalled_score?.toFixed(2) ?? '—'} / {item.reuse_threshold?.toFixed(2) ?? '—'}
                        </td>
                        <td title={String(item.metadata?.reason_path ?? '')}>
                          {String(item.metadata?.decision_summary ?? '—')}
                        </td>
                        <td>{item.stored ? 'yes' : 'no'}</td>
                        <td>{item.estimated_time_saved_ms} ms</td>
                        <td title={item.request_id}>{item.request_id.slice(0, 12)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="table-wrap" style={{ marginTop: 16 }}>
              <table>
                <thead>
                  <tr>
                    <th>Approved Item</th>
                    <th>Contact</th>
                    <th>Current Review</th>
                    <th>Execution Contract</th>
                    <th>Dry-run Delivery</th>
                    <th>Latest Attempt</th>
                  </tr>
                </thead>
                <tbody>
                  {reviewQueue.length === 0 ? (
                    <tr><td colSpan={6}>No approved execution-ready items match the current workflow filters.</td></tr>
                  ) : (
                    reviewQueue.map(item => {
                      const execution = executionByReviewItem[item.review_item_id];
                      const delivery = deliveryByReviewItem[item.review_item_id];
                      const history = deliveryHistoryByReviewItem[item.review_item_id] ?? [];
                      const metadata = item.metadata ?? {};
                      const executionContract = (metadata.execution_contract as Record<string, unknown> | undefined) ?? {};
                      const subject = String(executionContract.subject ?? '—');
                      const recipient = String(executionContract.to ?? item.contact_email ?? '—');
                      return (
                        <tr key={item.review_item_id}>
                          <td>
                            <div>{item.case_name}</div>
                            <div className="muted">{item.lead_name ?? 'Unknown lead'}</div>
                          </td>
                          <td>
                            <div>{recipient}</div>
                            <div className="muted">{item.company_name ?? '—'}</div>
                          </td>
                          <td>
                            <div>{item.review_status}</div>
                            <div className="muted">{item.reviewer_name ?? '—'}</div>
                          </td>
                          <td title={subject}>
                            <div>{String(executionContract.channel ?? '—')}</div>
                            <div className="muted">{subject.slice(0, 64)}</div>
                          </td>
                          <td>
                            <button
                              className="btn-primary"
                              onClick={() => runDryRunDelivery(item)}
                              disabled={deliveringReviewItemId === item.review_item_id || item.review_status !== 'approved'}
                            >
                              {deliveringReviewItemId === item.review_item_id ? 'Running…' : 'Dry-run Deliver'}
                            </button>
                          </td>
                          <td>
                            {delivery ? (
                              <>
                                <div>{delivery.delivery_status}</div>
                                <div className="muted">{delivery.provider}</div>
                                <div className="muted">history: {history.length}</div>
                                {execution && <div className="muted">execution: {execution.execution_status}</div>}
                              </>
                            ) : (
                              <span className="muted">No attempt yet</span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
