import React, { useEffect, useState, useCallback } from 'react';
import { api, Tenant, TenantCreate } from '../api';

const PLANS = ['free', 'pro', 'enterprise'] as const;

function Badge({ active }: { active: boolean }) {
  return (
    <span className={`badge ${active ? 'badge-green' : 'badge-gray'}`}>
      {active ? 'active' : 'inactive'}
    </span>
  );
}

function PlanBadge({ plan }: { plan: string }) {
  const cls = plan === 'enterprise' ? 'badge-purple' : plan === 'pro' ? 'badge-blue' : 'badge-gray';
  return <span className={`badge ${cls}`}>{plan}</span>;
}

interface CreateFormProps {
  onCreated: () => void;
  onCancel: () => void;
}

function CreateForm({ onCreated, onCancel }: CreateFormProps) {
  const [form, setForm] = useState<TenantCreate>({ name: '', plan: 'free' });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErr(null);
    try {
      await api.tenants.create(form);
      onCreated();
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="create-form" onSubmit={submit}>
      <h3>New Tenant</h3>
      <label>
        Name
        <input
          type="text"
          value={form.name}
          onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          required
          placeholder="Acme Corp"
        />
      </label>
      <label>
        Plan
        <select value={form.plan} onChange={e => setForm(f => ({ ...f, plan: e.target.value as typeof form.plan }))}>
          {PLANS.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
      </label>
      {err && <p className="error">{err}</p>}
      <div className="form-actions">
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Creating…' : 'Create'}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

interface EditRowProps {
  tenant: Tenant;
  onSaved: () => void;
  onCancel: () => void;
}

function EditRow({ tenant, onSaved, onCancel }: EditRowProps) {
  const [plan, setPlan] = useState(tenant.plan);
  const [active, setActive] = useState(tenant.is_active);
  const [premium, setPremium] = useState(tenant.enable_premium_escalation);
  const [cache, setCache] = useState(tenant.enable_semantic_cache);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    setLoading(true);
    setErr(null);
    try {
      await api.tenants.update(tenant.tenant_id, {
        plan,
        is_active: active,
        enable_premium_escalation: premium,
        enable_semantic_cache: cache,
      });
      onSaved();
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }

  return (
    <tr className="editing-row">
      <td colSpan={7}>
        <div className="inline-edit">
          <span className="edit-label">Editing: <strong>{tenant.name}</strong></span>
          <label>
            Plan
            <select value={plan} onChange={e => setPlan(e.target.value as typeof plan)}>
              {PLANS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} />
            Active
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={premium} onChange={e => setPremium(e.target.checked)} />
            Premium
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={cache} onChange={e => setCache(e.target.checked)} />
            Sem. Cache
          </label>
          {err && <span className="error">{err}</span>}
          <div className="form-actions">
            <button className="btn-primary" onClick={save} disabled={loading}>
              {loading ? 'Saving…' : 'Save'}
            </button>
            <button className="btn-ghost" onClick={onCancel}>Cancel</button>
          </div>
        </div>
      </td>
    </tr>
  );
}

export default function TenantsView() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [activeOnly, setActiveOnly] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const data = await api.tenants.list(activeOnly);
      setTenants(data);
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }, [activeOnly]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="view">
      <div className="view-header">
        <h2>Tenants</h2>
        <div className="header-actions">
          <label className="checkbox-label">
            <input type="checkbox" checked={activeOnly} onChange={e => setActiveOnly(e.target.checked)} />
            Active only
          </label>
          <button className="btn-primary" onClick={() => setShowCreate(s => !s)}>
            {showCreate ? 'Cancel' : '+ New Tenant'}
          </button>
          <button className="btn-ghost" onClick={load}>↺ Refresh</button>
        </div>
      </div>

      {showCreate && (
        <CreateForm
          onCreated={() => { setShowCreate(false); load(); }}
          onCancel={() => setShowCreate(false)}
        />
      )}

      {err && <p className="error">{err}</p>}

      {loading ? (
        <p className="muted">Loading…</p>
      ) : tenants.length === 0 ? (
        <p className="muted">No tenants yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Plan</th>
                <th>Status</th>
                <th>Premium</th>
                <th>Sem. Cache</th>
                <th>Max Req/Day</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {tenants.map(t => (
                editId === t.tenant_id
                  ? <EditRow key={t.tenant_id} tenant={t} onSaved={() => { setEditId(null); load(); }} onCancel={() => setEditId(null)} />
                  : (
                    <tr key={t.tenant_id}>
                      <td>
                        <div className="cell-primary">{t.name}</div>
                        <div className="cell-sub">{t.tenant_id}</div>
                      </td>
                      <td><PlanBadge plan={t.plan} /></td>
                      <td><Badge active={t.is_active} /></td>
                      <td>{t.enable_premium_escalation ? '✓' : '—'}</td>
                      <td>{t.enable_semantic_cache ? '✓' : '—'}</td>
                      <td>{t.max_requests_per_day ?? '∞'}</td>
                      <td>
                        <button className="btn-sm" onClick={() => setEditId(t.tenant_id)}>Edit</button>
                      </td>
                    </tr>
                  )
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
