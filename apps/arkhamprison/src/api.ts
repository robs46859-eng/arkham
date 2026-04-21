const BASE = (import.meta.env.VITE_ARKHAM_URL ?? "").replace(/\/$/, "");
const SERVICES_BASE = import.meta.env.VITE_GATEWAY_URL ?? "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

// ── types ────────────────────────────────────────────────────────────────────

export interface Stats {
  verdicts: { total: number; approve: number; hold: number; reject: number };
  personas: number;
  yard_escapes: number;
  fingerprints: number;
  shadow_mode: boolean;
}

export interface Verdict {
  id: string;
  persona_id: string;
  tenant_id: string;
  checkpoint: string;
  verdict: "approve" | "hold" | "reject";
  points: number;
  drift_score: number | null;
  yard_match_score: number | null;
  yard_match_id: string | null;
  shadow_mode: boolean;
  reasoning: string;
  request_id: string | null;
  created_at: string;
}

export interface Escape {
  id: string;
  persona_id: string;
  tenant_id: string;
  trigger: string | null;
  escape_timestamp: string | null;
  created_at: string;
}

export interface ServiceHealth {
  name: string;
  url: string;
  status: "ok" | "error" | "checking";
  latency_ms?: number;
}

// ── api ──────────────────────────────────────────────────────────────────────

export const api = {
  stats: () => req<Stats>("/v1/stats"),

  verdicts: {
    list: (limit = 50, offset = 0, verdict?: string) => {
      const qs = new URLSearchParams({ limit: String(limit), offset: String(offset) });
      if (verdict) qs.set("verdict", verdict);
      return req<{ total: number; verdicts: Verdict[] }>(`/v1/verdicts?${qs}`);
    },
  },

  yard: () => req<{ count: number; escapes: Escape[] }>("/v1/yard"),

  stix: () => req<Record<string, unknown>>("/v1/stix/export"),

  adversarial: (body: {
    persona_id: string;
    tenant_id: string;
    responses: string[];
    evidence?: string;
    request_id?: string;
  }) => req<Record<string, unknown>>("/v1/adversarial", { method: "POST", body: JSON.stringify(body) }),

  health: () => req<{ status: string }>("/health"),
};

// ── SSE ──────────────────────────────────────────────────────────────────────

export function connectVerdictStream(
  onVerdict: (v: Verdict) => void,
  onError: (e: Event) => void
): () => void {
  const es = new EventSource(`${BASE}/v1/verdicts/stream`);
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.type === "verdict") onVerdict(data as Verdict);
    } catch {
      // ignore parse errors
    }
  };
  es.onerror = onError;
  return () => es.close();
}

// ── service health checks (proxy via same origin in prod) ────────────────────

export const KNOWN_SERVICES: Array<{ name: string; url: string }> = [
  { name: "arkham", url: `${BASE}/health` },
  { name: "gateway", url: `${SERVICES_BASE}/health` },
];

export async function checkServiceHealth(url: string): Promise<{ status: "ok" | "error"; latency_ms: number }> {
  const t0 = performance.now();
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(4000) });
    const latency_ms = Math.round(performance.now() - t0);
    return { status: res.ok ? "ok" : "error", latency_ms };
  } catch {
    return { status: "error", latency_ms: Math.round(performance.now() - t0) };
  }
}
