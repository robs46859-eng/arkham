// ── Types ─────────────────────────────────────────────────────────────────────

export interface Tenant {
  tenant_id: string;
  name: string;
  plan: 'free' | 'pro' | 'enterprise';
  is_active: boolean;
  enable_premium_escalation: boolean;
  enable_semantic_cache: boolean;
  cache_similarity_threshold: number;
  max_requests_per_day: number | null;
  created_at: string;
  updated_at: string;
}

export interface TenantCreate {
  name: string;
  plan?: 'free' | 'pro' | 'enterprise';
  enable_premium_escalation?: boolean;
  enable_semantic_cache?: boolean;
}

export interface TenantUpdate {
  name?: string;
  plan?: 'free' | 'pro' | 'enterprise';
  is_active?: boolean;
  enable_premium_escalation?: boolean;
  enable_semantic_cache?: boolean;
  cache_similarity_threshold?: number;
  max_requests_per_day?: number | null;
}

export interface IngestionJob {
  job_id: string;
  file_id: string;
  project_id: string;
  tenant_id: string;
  status: 'queued' | 'processing' | 'complete' | 'failed';
  entities_created: number;
  error_log: string | null;
  created_at: string;
  updated_at: string;
}

export interface DailyUsage {
  date: string;
  requests: number;
  cost_usd: number;
}

export interface ServiceBreakdown {
  service: string;
  requests: number;
  cost_usd: number;
}

export interface UsageRollup {
  tenant_id: string;
  period_days: number;
  total_requests: number;
  total_cost_usd: number;
  daily_breakdown: DailyUsage[];
  by_service: ServiceBreakdown[];
}

export interface WorkflowMemoryConfig {
  configured_reuse_min_score: number;
  effective_reuse_min_score: number;
  auto_reuse_score_floor: number;
  outcome_weights: Record<string, number>;
}

export interface WorkflowMemoryMetrics {
  tenant_id: string;
  workflow_type?: string | null;
  offer_type?: string | null;
  stage?: string | null;
  recall_attempts: number;
  recall_hits: number;
  fallback_count: number;
  fallback_reasons: Record<string, number>;
  hit_rate: number;
  fallback_rate: number;
  version_mismatch_rate: number;
  total_estimated_time_saved_ms: number;
  average_estimated_time_saved_ms: number;
  outcome_counts: Record<string, number>;
  outcome_score: number;
}

export interface WorkflowMemoryDecision {
  decision_id: string;
  tenant_id: string;
  request_id: string;
  workflow_type: string;
  offer_type?: string | null;
  offer_version?: string | null;
  stage?: string | null;
  audience?: string | null;
  prompt_key?: string | null;
  prompt_schema_version?: string | null;
  workflow_memory_schema_version?: string | null;
  task_type: string;
  cache_attempted: boolean;
  recalled_score?: number | null;
  reuse_threshold?: number | null;
  decision: string;
  fallback_reason?: string | null;
  stored: boolean;
  estimated_time_saved_ms: number;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface WorkflowReviewQueueItem {
  review_item_id: string;
  tenant_id: string;
  batch_label: string;
  source_artifact?: string | null;
  request_id?: string | null;
  case_name: string;
  lead_name?: string | null;
  company_name?: string | null;
  contact_email?: string | null;
  eligibility_status: string;
  system_decision: string;
  system_reason?: string | null;
  review_status: string;
  reviewer_name?: string | null;
  reviewer_notes?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  outcome_counts: Record<string, number>;
  outcome_score: number;
}

export interface WorkflowExecution {
  execution_id: string;
  tenant_id: string;
  review_item_id: string;
  request_id?: string | null;
  batch_label?: string | null;
  workflow_type?: string | null;
  offer_type?: string | null;
  stage?: string | null;
  execution_status: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface WorkflowExecutionDelivery {
  delivery_id: string;
  tenant_id: string;
  execution_id: string;
  review_item_id: string;
  channel: string;
  provider: string;
  delivery_status: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface GovernanceScorecard {
  scorecard_id: string;
  battery: string;
  passed: boolean;
  total_tokens: number;
  latency_ms: number;
  cost_usd: number;
  scores: Record<string, unknown>;
  created_at: string;
}

export interface GovernanceVerdict {
  verdict_id: string;
  persona_id: string;
  persona_display_name?: string | null;
  persona_state?: string | null;
  tenant_id: string;
  request_id?: string | null;
  checkpoint: string;
  verdict: 'approve' | 'hold' | 'reject';
  shadow_mode: boolean;
  reasoning?: string | null;
  drift_score?: number | null;
  yard_match_score?: number | null;
  yard_match_id?: string | null;
  battery_scores: Record<string, number>;
  scorecards: GovernanceScorecard[];
  created_at: string;
}

export interface GovernanceSummary {
  total_verdicts: number;
  shadow_mode_count: number;
  enforced_count: number;
  tenant_count: number;
  verdict_counts: Record<string, number>;
  checkpoint_counts: Record<string, number>;
  latest_verdict_at?: string | null;
  daily_verdicts: Array<{ date: string; count: number }>;
  recent_alerts: Array<{ id: string; severity: string; title: string; detail: string; related_id?: string | null }>;
}

export interface PredictabilityFactor {
  key: string;
  label: string;
  score: number;
  impact: string;
  detail: string;
}

export interface PredictabilityScale {
  score: number;
  band: string;
  confidence: number;
  factors: PredictabilityFactor[];
  summary: string;
}

export interface DigitalTwinProjectSummary {
  project_id: string;
  tenant_id: string;
  tenant_name: string;
  project_name: string;
  twin_status: string;
  twin_version: string;
  readiness_score: number;
  file_counts: Record<string, number>;
  building_element_count: number;
  document_chunk_count: number;
  issue_count: number;
  high_severity_issue_count: number;
  workflow_run_count: number;
  latest_ingestion_status?: string | null;
  latest_activity_at?: string | null;
  alerts: string[];
  operational_predictability: PredictabilityScale;
  environmental_predictability: PredictabilityScale;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const adminToken = import.meta.env.VITE_ADMIN_TOKEN as string | undefined;
  const adminActor = import.meta.env.VITE_ADMIN_ACTOR as string | undefined;
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(adminToken ? { Authorization: `Bearer ${adminToken}` } : {}),
      ...(adminActor ? { 'X-Admin-Actor': adminActor } : {}),
      ...init?.headers,
    },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText} — ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── Tenant API ────────────────────────────────────────────────────────────────

export const api = {
  tenants: {
    list: (activeOnly?: boolean) =>
      req<Tenant[]>(`/v1/tenants${activeOnly ? '?active_only=true' : ''}`),
    create: (body: TenantCreate) =>
      req<Tenant>('/v1/tenants', { method: 'POST', body: JSON.stringify(body) }),
    update: (tenantId: string, body: TenantUpdate) =>
      req<Tenant>(`/v1/tenants/${tenantId}`, { method: 'PATCH', body: JSON.stringify(body) }),
    get: (tenantId: string) =>
      req<Tenant>(`/v1/tenants/${tenantId}`),
  },

  jobs: {
    list: (tenantId: string, limit = 50) =>
      req<IngestionJob[]>(`/v1/ingestion/jobs?tenant_id=${tenantId}&limit=${limit}`),
  },

  usage: {
    rollup: (tenantId: string, days = 30) =>
      req<UsageRollup>(`/v1/usage/${tenantId}?days=${days}`),
  },

  workflowMemory: {
    config: () =>
      req<WorkflowMemoryConfig>('/v1/crm/workflow-memory/config'),
    updateConfig: (body: { configured_reuse_min_score?: number; outcome_weights?: Record<string, number> }) =>
      req<WorkflowMemoryConfig>('/v1/crm/workflow-memory/config', {
        method: 'PATCH',
        body: JSON.stringify({
          reuse_min_score: body.configured_reuse_min_score,
          outcome_weights: body.outcome_weights,
        }),
      }),
    metrics: (tenantId: string, params?: { workflowType?: string; offerType?: string; stage?: string }) => {
      const search = new URLSearchParams();
      if (params?.workflowType) search.set('workflow_type', params.workflowType);
      if (params?.offerType) search.set('offer_type', params.offerType);
      if (params?.stage) search.set('stage', params.stage);
      const qs = search.toString();
      return req<WorkflowMemoryMetrics>(`/v1/crm/workflow-memory/metrics/${tenantId}${qs ? `?${qs}` : ''}`);
    },
    decisions: (
      tenantId: string,
      params?: {
        workflowType?: string;
        offerType?: string;
        stage?: string;
        decision?: string;
        fallbackReason?: string;
        borderlineOnly?: boolean;
        limit?: number;
      },
    ) => {
      const search = new URLSearchParams();
      if (params?.workflowType) search.set('workflow_type', params.workflowType);
      if (params?.offerType) search.set('offer_type', params.offerType);
      if (params?.stage) search.set('stage', params.stage);
      if (params?.decision) search.set('decision', params.decision);
      if (params?.fallbackReason) search.set('fallback_reason', params.fallbackReason);
      if (params?.borderlineOnly) search.set('borderline_only', 'true');
      if (params?.limit) search.set('limit', String(params.limit));
      const qs = search.toString();
      return req<WorkflowMemoryDecision[]>(`/v1/crm/workflow-memory/decisions/${tenantId}${qs ? `?${qs}` : ''}`);
    },
    reviewQueue: (tenantId: string, params?: { reviewStatus?: string; limit?: number }) => {
      const search = new URLSearchParams();
      if (params?.reviewStatus) search.set('review_status', params.reviewStatus);
      if (params?.limit) search.set('limit', String(params.limit));
      const qs = search.toString();
      return req<WorkflowReviewQueueItem[]>(`/v1/crm/workflow-review-queue/${tenantId}${qs ? `?${qs}` : ''}`);
    },
    createExecution: (reviewItemId: string, body?: { executionStatus?: string; metadata?: Record<string, unknown> }) =>
      req<WorkflowExecution>(`/v1/crm/workflow-review-queue/items/${reviewItemId}/execution`, {
        method: 'POST',
        body: JSON.stringify({
          execution_status: body?.executionStatus ?? 'queued',
          metadata: body?.metadata ?? {},
        }),
      }),
    deliverExecution: (executionId: string, body?: { metadata?: Record<string, unknown> }) =>
      req<WorkflowExecutionDelivery>(`/v1/crm/workflow-executions/${executionId}/deliver`, {
        method: 'POST',
        body: JSON.stringify({
          metadata: body?.metadata ?? {},
        }),
      }),
    deliveryHistory: (executionId: string) =>
      req<WorkflowExecutionDelivery[]>(`/v1/crm/workflow-executions/${executionId}/deliveries`),
  },

  governance: {
    summary: (tenantId?: string) =>
      req<GovernanceSummary>(`/v1/admin/governance/summary${tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : ''}`),
    verdicts: (params?: {
      tenantId?: string;
      verdict?: string;
      checkpoint?: string;
      shadowMode?: boolean;
      limit?: number;
    }) => {
      const search = new URLSearchParams();
      if (params?.tenantId) search.set('tenant_id', params.tenantId);
      if (params?.verdict) search.set('verdict', params.verdict);
      if (params?.checkpoint) search.set('checkpoint', params.checkpoint);
      if (params?.shadowMode !== undefined) search.set('shadow_mode', String(params.shadowMode));
      if (params?.limit) search.set('limit', String(params.limit));
      const qs = search.toString();
      return req<GovernanceVerdict[]>(`/v1/admin/governance/verdicts${qs ? `?${qs}` : ''}`);
    },
  },

  digitalTwins: {
    projects: (params?: { tenantId?: string; limit?: number }) => {
      const search = new URLSearchParams();
      if (params?.tenantId) search.set('tenant_id', params.tenantId);
      if (params?.limit) search.set('limit', String(params.limit));
      const qs = search.toString();
      return req<DigitalTwinProjectSummary[]>(`/v1/admin/digital-twins/projects${qs ? `?${qs}` : ''}`);
    },
  },
};
