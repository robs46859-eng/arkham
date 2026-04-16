const GATEWAY = import.meta.env.VITE_GATEWAY_URL ?? 'http://localhost:8000';

// ── Auth token storage ────────────────────────────────────────────────────────

const TOKEN_KEY = 'robco_token';
const TENANT_KEY = 'robco_tenant';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function getTenantId(): string | null {
  return localStorage.getItem(TENANT_KEY);
}
export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TENANT_KEY);
}

// ── Base fetch ────────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  authenticated = true,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> ?? {}),
  };
  if (authenticated) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(`${GATEWAY}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export async function login(tenantId: string, apiKey: string): Promise<TokenResponse> {
  const data = await apiFetch<TokenResponse>(
    '/v1/auth/token',
    { method: 'POST', body: JSON.stringify({ tenant_id: tenantId, api_key: apiKey }) },
    false,
  );
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(TENANT_KEY, tenantId);
  return data;
}

// ── Billing ───────────────────────────────────────────────────────────────────

export interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}

export async function createCheckout(plan: 'solo' | 'agency'): Promise<CheckoutResponse> {
  return apiFetch<CheckoutResponse>('/billing/checkout', {
    method: 'POST',
    body: JSON.stringify({ plan }),
  });
}

// ── BIM Ingestion ─────────────────────────────────────────────────────────────

export type FileType = 'ifc' | 'pdf' | 'csv' | 'xlsx' | 'markup';

export interface FileRecord {
  file_id: string;
  project_id: string;
  file_type: FileType;
  storage_path: string;
  registered_at: string;
}

export interface IngestionJob {
  job_id: string;
  status: 'queued' | 'processing' | 'complete' | 'failed';
  entities_created: number;
  errors: string[];
}

export async function registerFile(
  projectId: string,
  fileType: FileType,
  storagePath: string,
): Promise<FileRecord> {
  const tenantId = getTenantId()!;
  return apiFetch<FileRecord>('/v1/files/register', {
    method: 'POST',
    body: JSON.stringify({ tenant_id: tenantId, project_id: projectId, file_type: fileType, storage_path: storagePath }),
  });
}

export async function ingestFile(fileId: string, projectId: string): Promise<IngestionJob> {
  const tenantId = getTenantId()!;
  return apiFetch<IngestionJob>(`/v1/files/${fileId}/ingest`, {
    method: 'POST',
    body: JSON.stringify({ file_id: fileId, project_id: projectId, tenant_id: tenantId }),
  });
}

export async function getJobStatus(jobId: string): Promise<IngestionJob> {
  return apiFetch<IngestionJob>(`/v1/ingestion/jobs/${jobId}`);
}

// ── Vertical calls (via gateway proxy) ───────────────────────────────────────

export type VerticalId = 'omniscale' | 'cyberscribe' | 'ai-consistency' | 'autopitch';

export async function callVertical<TReq, TRes>(
  verticalId: VerticalId,
  endpoint: string,
  body: TReq,
): Promise<TRes> {
  return apiFetch<TRes>(`/v1/verticals/${verticalId}/${endpoint}`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ── Takeoff ───────────────────────────────────────────────────────────────────

export interface TakeoffRequest {
  project_name: string;
  project_type: string;
  location: string;
  gross_floor_area_sqft?: number;
  num_stories?: number;
  construction_type: string;
  scope_description: string;
  bim_data?: Record<string, unknown>;
}

export interface TakeoffLineItem {
  division: string;
  description: string;
  unit: string;
  quantity: number;
  unit_rate_usd: number;
  total_usd: number;
  notes: string;
}

export interface TakeoffResponse {
  project_name: string;
  project_type: string;
  line_items: TakeoffLineItem[];
  subtotal_usd: number;
  contingency_pct: number;
  contingency_usd: number;
  total_usd: number;
  assumptions: string[];
  exclusions: string[];
}

// ── Spec generation ───────────────────────────────────────────────────────────

export interface SpecSection {
  section_number: string;
  section_title: string;
  part_1_general: string;
  part_2_products: string;
  part_3_execution: string;
}

export interface SpecResponse {
  project_name: string;
  sections: SpecSection[];
  general_notes: string[];
  referenced_standards: string[];
}

// ── Consistency check ─────────────────────────────────────────────────────────

export interface DocumentSection {
  discipline: string;
  document_type: string;
  content: string;
}

export interface ConsistencyIssue {
  issue_id: string;
  check_type: string;
  severity: 'Critical' | 'Major' | 'Minor';
  disciplines_affected: string[];
  location: string;
  description: string;
  recommendation: string;
  reference: string;
}

export interface ConsistencyResponse {
  project_name: string;
  documents_reviewed: number;
  consistency_score: number;
  issues: ConsistencyIssue[];
  critical_count: number;
  major_count: number;
  minor_count: number;
  executive_summary: string;
  recommended_actions: string[];
}

// ── Proposal ──────────────────────────────────────────────────────────────────

export interface ProposalSection {
  heading: string;
  content: string;
}

export interface FeeLineItem {
  phase: string;
  description: string;
  fee_usd: number;
  percentage_of_total: number;
}

export interface ProposalResponse {
  project_name: string;
  client_name: string;
  prepared_by: string;
  sections: ProposalSection[];
  fee_schedule: FeeLineItem[];
  total_fee_usd: number;
  fee_basis: string;
  proposed_timeline_months: number;
  validity_days: number;
  key_assumptions: string[];
  exclusions: string[];
}
