import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createCheckout, login } from '../api';

type Mode = 'login' | 'signup';

const PLANS = [
  {
    id: 'solo' as const,
    name: 'Solo',
    price: '$12',
    period: '/mo',
    credits: '50 credits / mo',
    features: ['Quantity takeoffs', 'Spec generation', 'Proposal writing', 'Document consistency'],
  },
  {
    id: 'agency' as const,
    name: 'Agency',
    price: '$30',
    period: '/mo',
    credits: '200 credits / mo',
    features: ['Everything in Solo', 'Multi-project dashboard', 'Team API access', 'Priority processing'],
  },
];

export default function Auth() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('login');
  const [tenantId, setTenantId] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState('');

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading('login');
    try {
      await login(tenantId.trim(), apiKey.trim());
      navigate('/app', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading('');
    }
  }

  async function handleSignup(planId: 'solo' | 'agency') {
    setError('');
    setLoading(planId);
    try {
      const { checkout_url } = await createCheckout(planId);
      window.location.href = checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create checkout session');
      setLoading('');
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-left">
        <div className="auth-brand">
          <a href="/" className="nav-logo">ROBCO<span>AI</span></a>
          <p className="auth-tagline">
            BIM-first AI for architecture and construction.<br />
            Specs. Takeoffs. Proposals. In seconds.
          </p>
        </div>
        <div className="auth-features">
          {['Quantity Takeoff', 'Spec Generation', 'Document Coordination', 'Proposal Writing'].map(f => (
            <div key={f} className="auth-feature-item">
              <span className="auth-feature-check">✓</span>
              <span>{f}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="auth-right">
        <div className="auth-tabs">
          <button
            className={`auth-tab${mode === 'login' ? ' active' : ''}`}
            onClick={() => { setMode('login'); setError(''); }}
          >
            Sign In
          </button>
          <button
            className={`auth-tab${mode === 'signup' ? ' active' : ''}`}
            onClick={() => { setMode('signup'); setError(''); }}
          >
            Get Started
          </button>
        </div>

        {mode === 'login' ? (
          <form className="auth-form" onSubmit={handleLogin}>
            <div className="form-group">
              <label className="form-label">Tenant ID</label>
              <input
                className="form-input"
                type="text"
                placeholder="tenant_..."
                value={tenantId}
                onChange={e => setTenantId(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">API Key</label>
              <input
                className="form-input"
                type="password"
                placeholder="sk-..."
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                required
              />
            </div>
            {error && <div className="auth-error">{error}</div>}
            <button className="btn-primary auth-submit" type="submit" disabled={!!loading}>
              {loading === 'login' ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        ) : (
          <div className="signup-plans">
            <p className="signup-subtitle">Choose a plan to get started. Billed monthly, cancel anytime.</p>
            {PLANS.map(plan => (
              <div key={plan.id} className={`signup-plan${plan.id === 'agency' ? ' featured' : ''}`}>
                <div className="signup-plan-header">
                  <div>
                    <div className="plan-name">{plan.name}</div>
                    <div className="plan-credits">{plan.credits}</div>
                  </div>
                  <div className="plan-price">
                    <span className="price-num">{plan.price}</span>
                    <span className="price-period">{plan.period}</span>
                  </div>
                </div>
                <ul className="signup-plan-features">
                  {plan.features.map(f => (
                    <li key={f}><span className="check">✓</span> {f}</li>
                  ))}
                </ul>
                <button
                  className={`plan-btn${plan.id === 'agency' ? ' featured-btn' : ''}`}
                  onClick={() => handleSignup(plan.id)}
                  disabled={!!loading}
                >
                  {loading === plan.id ? 'Redirecting...' : `Get ${plan.name}`}
                </button>
              </div>
            ))}
            {error && <div className="auth-error">{error}</div>}
          </div>
        )}
      </div>
    </div>
  );
}
