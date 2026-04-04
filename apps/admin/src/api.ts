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

// ── Helpers ───────────────────────────────────────────────────────────────────

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
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
};
