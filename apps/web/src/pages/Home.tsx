import React, { useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const MARQUEE_ITEMS = [
  'BIM Ingestion', 'Scoped Memory', 'Cost-Aware AI', 'Semantic Caching',
  'Event-Driven Workflows', 'Multi-Tenant', 'Deterministic Outputs', 'GCP-First',
];

const FEATURES = [
  {
    num: '01',
    title: 'BIM Ingestion Engine',
    desc: 'Native IFC, PDF, schedule, and markup parsing. Every file becomes structured, queryable data — not a flat blob in object storage.',
  },
  {
    num: '02',
    title: 'Multi-Service Gateway',
    desc: 'Central control plane for auth, AI inference, billing, CRM, and workflow routing. One API surface — every capability.',
  },
  {
    num: '03',
    title: 'Scoped Memory',
    desc: 'Project-level semantic memory backed by pgvector. Context persists across sessions, verticals, and agents without leaking between tenants.',
  },
  {
    num: '04',
    title: 'Cost-Aware AI',
    desc: 'Semantic caching, smart model routing, and per-tenant usage tracking. You see every token spent and every dollar burned before it happens.',
  },
  {
    num: '05',
    title: 'Event-Driven Workflows',
    desc: 'Durable orchestration built for long-running BIM processes. Steps retry, checkpoint, and resume — no lost work, no silent failures.',
  },
  {
    num: '06',
    title: 'Multi-Tenant Architecture',
    desc: 'Fully isolated tenant contexts with API key auth, per-tenant billing, and scoped resource access. Enterprise-grade from day one.',
  },
];

const VERTICALS = [
  { name: 'Omniscale',          fn: 'Quantity takeoff + cost estimation', input: 'IFC / BIM files',  output: 'Structured cost data'  },
  { name: 'AI Consistency',     fn: 'Cross-doc quality checking',         input: 'Drawings + specs', output: 'Consistency report'    },
  { name: 'Workflow Architect',  fn: 'Workflow memory & planning',         input: 'Project context',  output: 'Execution plan'        },
  { name: 'Cyberscribe',        fn: 'Technical documentation',            input: 'BIM + markups',    output: 'Spec documents'        },
  { name: 'AutoPitch',          fn: 'Proposal generation',                input: 'Project brief',    output: 'Client proposal'       },
  { name: 'Digital It Girl',    fn: 'Brand + content AI',                 input: 'Brand guidelines', output: 'Marketing assets'      },
  { name: 'Public Beta',        fn: 'Open experimentation',               input: 'Any prompt',       output: 'Any deliverable'       },
];

const STEPS = [
  {
    num: '01',
    title: 'Ingest Your Data',
    desc: 'Upload IFC files, PDFs, schedules, and markups. The ingestion engine parses and indexes everything into structured, queryable form.',
  },
  {
    num: '02',
    title: 'Configure Your Vertical',
    desc: 'Select the AI vertical that matches your task. Each vertical is purpose-built — no prompt engineering required from your team.',
  },
  {
    num: '03',
    title: 'Run AI Workflows',
    desc: 'The gateway routes your request through the right models with semantic caching and cost tracking. Complex jobs orchestrate automatically.',
  },
  {
    num: '04',
    title: 'Export Structured Outputs',
    desc: 'Get deterministic, traceable JSON deliverables. Audit the full inference chain. Own your outputs — no vendor lock-in, ever.',
  },
];

export default function Home() {
  const navigate = useNavigate();
  const cursorRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cursor = cursorRef.current;
    const ring = ringRef.current;
    if (!cursor || !ring) return;

    let mx = 0, my = 0, rx = 0, ry = 0;
    let animId: number;

    const onMove = (e: MouseEvent) => {
      mx = e.clientX; my = e.clientY;
      cursor.style.left = mx + 'px';
      cursor.style.top = my + 'px';
    };

    const animRing = () => {
      rx += (mx - rx) * 0.12;
      ry += (my - ry) * 0.12;
      ring.style.left = rx + 'px';
      ring.style.top = ry + 'px';
      animId = requestAnimationFrame(animRing);
    };

    document.addEventListener('mousemove', onMove);
    animId = requestAnimationFrame(animRing);

    const reveals = document.querySelectorAll('.reveal');
    const observer = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('visible'); observer.unobserve(e.target); }
      }),
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    );
    reveals.forEach(r => observer.observe(r));

    document.querySelectorAll('.feature-card').forEach((c, i) => {
      (c as HTMLElement).style.transitionDelay = (i * 0.08) + 's';
    });

    return () => {
      document.removeEventListener('mousemove', onMove);
      cancelAnimationFrame(animId);
      observer.disconnect();
    };
  }, []);

  return (
    <>
      <div className="cursor" ref={cursorRef} />
      <div className="cursor-ring" ref={ringRef} />

      {/* NAV */}
      <nav>
        <a href="#" className="nav-logo">ROBCO<span>AI</span></a>
        <ul className="nav-links">
          <li><a href="#features">Platform</a></li>
          <li><a href="#verticals">Verticals</a></li>
          <li><a href="#how">How It Works</a></li>
          <li><a href="#contact">Contact</a></li>
          <li><Link to="/terms">Terms</Link></li>
        </ul>
        <button className="nav-cta" onClick={() => navigate('/login')} style={{ cursor: 'pointer' }}>
          Get Access
        </button>
      </nav>

      {/* HERO */}
      <section className="hero">
        <div className="hero-grid" />
        <div className="hero-badge">// BIM-First AI Platform — Now Live</div>
        <h1 className="hero-headline">
          INGEST.<br />
          <span className="accent-word">PROCESS.</span><br />
          <span className="stroke-word">DEPLOY.</span>
        </h1>
        <p className="hero-sub">
          One platform. Structured, traceable AI outputs from your project data.
          No vendor lock-in. No black-box loops.
          Just <strong>deterministic, reproducible intelligence</strong> — yours to audit, own, and deploy anywhere.
        </p>
        <div className="hero-actions">
          <button className="btn-primary" onClick={() => navigate('/login')} style={{ cursor: 'pointer' }}>
            Start Building
          </button>
          <a href="#how" className="btn-ghost">See How It Works</a>
        </div>
        <div className="hero-stats">
          <div className="stat-item">
            <span className="stat-num">13<span style={{ fontSize: '24px', color: 'var(--accent)' }}>+</span></span>
            <span className="stat-label">Microservices</span>
          </div>
          <div className="stat-item">
            <span className="stat-num">7</span>
            <span className="stat-label">AI Verticals</span>
          </div>
          <div className="stat-item">
            <span className="stat-num">1</span>
            <span className="stat-label">Control Plane</span>
          </div>
          <div className="stat-item">
            <span className="stat-num">∞</span>
            <span className="stat-label">Scalable Workflows</span>
          </div>
        </div>
      </section>

      {/* MARQUEE */}
      <div className="marquee-wrap">
        <div className="marquee-track">
          {[...MARQUEE_ITEMS, ...MARQUEE_ITEMS].map((item, i) => (
            <span key={i} className="marquee-item">{item}</span>
          ))}
        </div>
      </div>

      {/* DEMO TERMINAL */}
      <section className="demo-section">
        <div className="reveal">
          <div className="section-label">// Live Gateway</div>
          <h2 className="section-title">FROM BIM<br />TO OUTPUT</h2>
          <p className="section-body">
            Ingest IFC files, PDFs, and schedules. Route through the AI gateway.
            Get structured, traceable deliverables — no follow-up prompts, no broken dependencies,{' '}
            <strong>no subscription trap.</strong>
            <br /><br />
            Built on <strong>FastAPI + pgvector</strong> with intelligent model routing and semantic caching.
          </p>
        </div>
        <div className="terminal reveal">
          <div className="terminal-bar">
            <div className="dot dot-r" /><div className="dot dot-y" /><div className="dot dot-g" />
            <span className="terminal-title">robco-gateway — infer</span>
          </div>
          <div className="terminal-body">
            <div><span className="t-prompt">›</span> <span className="t-input">POST /api/v1/infer</span></div>
            <div><span className="t-output">  tenant: </span><span className="t-input">omniscale-prod</span></div>
            <div><span className="t-output">  vertical: </span><span className="t-input">bim_ingestion</span></div>
            <div><span className="t-output">  input: </span><span className="t-file">structural_model_v3.ifc</span></div>
            <div>&nbsp;</div>
            <div><span className="t-comment">// Authenticating API key...</span></div>
            <div><span className="t-comment">// Routing to BIM Ingestion vertical...</span></div>
            <div><span className="t-comment">// Checking semantic cache...</span></div>
            <div>&nbsp;</div>
            <div><span className="t-success">✓</span> <span className="t-output">Cache miss — running inference</span></div>
            <div><span className="t-success">✓</span> <span className="t-output">Output: </span><span className="t-file">deliverable_42.json</span></div>
            <div><span className="t-success">✓</span> <span className="t-output">Tokens used: </span><span className="t-success">1,240</span> <span className="t-output">/ Budget: </span><span className="t-success">OK</span></div>
            <div>&nbsp;</div>
            <div><span className="t-prompt">›</span> <span className="cursor-blink" /></div>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="features-section" id="features">
        <div className="features-header reveal">
          <div>
            <div className="section-label">// Platform Capabilities</div>
            <h2 className="section-title">BUILT<br />DIFFERENT</h2>
          </div>
          <p className="section-body" style={{ margin: 0 }}>
            Every other AI platform black-boxes your data. Robco hands you the keys — structured, auditable, yours.
          </p>
        </div>
        <div className="features-grid">
          {FEATURES.map(f => (
            <div className="feature-card reveal" key={f.num}>
              <div className="feature-num">{f.num}</div>
              <div className="feature-title">{f.title}</div>
              <p className="feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* VERTICALS TABLE */}
      <section className="vs-section" id="verticals">
        <div className="vs-inner">
          <div className="section-label reveal">// AI Verticals</div>
          <h2 className="section-title reveal">PICK YOUR<br />VERTICAL</h2>
          <table className="vs-table reveal">
            <thead>
              <tr>
                <th>Vertical</th>
                <th className="highlight-col">Core Function</th>
                <th>Primary Input</th>
                <th>Output Type</th>
              </tr>
            </thead>
            <tbody>
              {VERTICALS.map(v => (
                <tr key={v.name}>
                  <td>{v.name}</td>
                  <td className="highlight-col">{v.fn}</td>
                  <td>{v.input}</td>
                  <td>{v.output}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="how-section" id="how">
        <div className="how-inner">
          <div className="section-label reveal">// Process</div>
          <h2 className="section-title reveal">HOW IT<br />WORKS</h2>
          <div className="steps-grid reveal">
            {STEPS.map(s => (
              <div className="step-item" key={s.num}>
                <div className="step-num">{s.num}</div>
                <div className="step-title">{s.title}</div>
                <p className="step-desc">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section" id="contact">
        <div className="cta-glow" />
        <div className="section-label">// Get Started Today</div>
        <h2 className="cta-headline">
          YOUR NEXT<br />
          <span style={{ color: 'var(--accent)' }}>PROJECT</span><br />
          IS ALREADY<br />
          <span style={{ color: 'var(--muted)' }}>STRUCTURED.</span>
        </h2>
        <p className="cta-sub">Deterministic. Auditable. Yours.</p>
        <div className="cta-actions">
          <button className="btn-primary" onClick={() => navigate('/login')} style={{ cursor: 'pointer' }}>
            Start Building
          </button>
          <a href="#features" className="btn-ghost">Explore Platform</a>
        </div>
      </section>

      {/* FOOTER */}
      <footer>
        <div className="footer-logo">ROBCO<span>AI</span></div>
        <ul className="footer-links">
          <li><Link to="/privacy">Privacy</Link></li>
          <li><Link to="/terms">Terms</Link></li>
          <li><Link to="/indemnification">Indemnification</Link></li>
          <li><Link to="/refund-policy">Refunds</Link></li>
          <li><Link to="/billing">Billing</Link></li>
          <li><a href="#verticals">Verticals</a></li>
        </ul>
        <div className="footer-copy">© 2026 Robco AI · arkhamprison.com</div>
      </footer>
    </>
  );
}
