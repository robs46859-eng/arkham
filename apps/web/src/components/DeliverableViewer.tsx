import React, { useState } from 'react';
import type {
  ConsistencyResponse,
  ProposalResponse,
  SpecResponse,
  TakeoffResponse,
} from '../api';

type DeliverableType = 'takeoff' | 'spec' | 'consistency' | 'proposal';
type DeliverableData = TakeoffResponse | SpecResponse | ConsistencyResponse | ProposalResponse;

interface DeliverableViewerProps {
  type: DeliverableType;
  data: DeliverableData;
  onClose: () => void;
}

const USD = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

// ── Takeoff view ─────────────────────────────────────────────────────────────

function TakeoffView({ data }: { data: TakeoffResponse }) {
  return (
    <div className="dv-content">
      <div className="dv-summary-row">
        <div className="dv-stat">
          <div className="dv-stat-label">Subtotal</div>
          <div className="dv-stat-value">{USD.format(data.subtotal_usd)}</div>
        </div>
        <div className="dv-stat">
          <div className="dv-stat-label">Contingency ({data.contingency_pct}%)</div>
          <div className="dv-stat-value">{USD.format(data.contingency_usd)}</div>
        </div>
        <div className="dv-stat highlight">
          <div className="dv-stat-label">Total Estimate</div>
          <div className="dv-stat-value accent">{USD.format(data.total_usd)}</div>
        </div>
      </div>

      <div className="dv-table-wrap">
        <table className="dv-table">
          <thead>
            <tr>
              <th>Division</th>
              <th>Description</th>
              <th>Unit</th>
              <th style={{ textAlign: 'right' }}>Qty</th>
              <th style={{ textAlign: 'right' }}>Unit Rate</th>
              <th style={{ textAlign: 'right' }}>Total</th>
            </tr>
          </thead>
          <tbody>
            {data.line_items.map((item, i) => (
              <tr key={i}>
                <td style={{ color: 'var(--accent)', fontFamily: 'var(--mono)', fontSize: '11px' }}>{item.division}</td>
                <td>
                  <div>{item.description}</div>
                  {item.notes && <div style={{ color: 'var(--muted)', fontSize: '11px', marginTop: '2px' }}>{item.notes}</div>}
                </td>
                <td>{item.unit}</td>
                <td style={{ textAlign: 'right' }}>{item.quantity.toLocaleString()}</td>
                <td style={{ textAlign: 'right' }}>{USD.format(item.unit_rate_usd)}</td>
                <td style={{ textAlign: 'right', color: 'var(--text)' }}>{USD.format(item.total_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="dv-notes-grid">
        <div>
          <div className="dv-notes-title">Assumptions</div>
          <ul className="dv-notes-list">{data.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
        </div>
        <div>
          <div className="dv-notes-title">Exclusions</div>
          <ul className="dv-notes-list">{data.exclusions.map((e, i) => <li key={i}>{e}</li>)}</ul>
        </div>
      </div>
    </div>
  );
}

// ── Spec view ─────────────────────────────────────────────────────────────────

function SpecView({ data }: { data: SpecResponse }) {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <div className="dv-content">
      <div className="dv-meta-row">
        <span className="dv-badge">{data.sections.length} sections</span>
        {data.referenced_standards.slice(0, 4).map(s => (
          <span key={s} className="dv-badge">{s}</span>
        ))}
      </div>
      {data.sections.map((sec, i) => (
        <div key={i} className="dv-accordion">
          <button className="dv-accordion-header" onClick={() => setOpen(open === i ? null : i)}>
            <span className="dv-section-num">{sec.section_number}</span>
            <span>{sec.section_title}</span>
            <span className="dv-chevron">{open === i ? '−' : '+'}</span>
          </button>
          {open === i && (
            <div className="dv-accordion-body">
              <div className="dv-spec-part"><strong>PART 1 — GENERAL</strong><pre>{sec.part_1_general}</pre></div>
              <div className="dv-spec-part"><strong>PART 2 — PRODUCTS</strong><pre>{sec.part_2_products}</pre></div>
              <div className="dv-spec-part"><strong>PART 3 — EXECUTION</strong><pre>{sec.part_3_execution}</pre></div>
            </div>
          )}
        </div>
      ))}
      {data.general_notes.length > 0 && (
        <div className="dv-section">
          <div className="dv-notes-title">General Notes</div>
          <ul className="dv-notes-list">{data.general_notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

// ── Consistency view ──────────────────────────────────────────────────────────

function ConsistencyView({ data }: { data: ConsistencyResponse }) {
  const scoreColor = data.consistency_score >= 80 ? 'var(--green)' : data.consistency_score >= 60 ? 'var(--accent)' : 'var(--red)';
  const severityColor = { Critical: 'var(--red)', Major: 'var(--accent2)', Minor: 'var(--muted)' };

  return (
    <div className="dv-content">
      <div className="dv-summary-row">
        <div className="dv-stat">
          <div className="dv-stat-label">Consistency Score</div>
          <div className="dv-stat-value" style={{ color: scoreColor }}>{data.consistency_score.toFixed(1)}</div>
        </div>
        <div className="dv-stat">
          <div className="dv-stat-label">Critical</div>
          <div className="dv-stat-value" style={{ color: 'var(--red)' }}>{data.critical_count}</div>
        </div>
        <div className="dv-stat">
          <div className="dv-stat-label">Major</div>
          <div className="dv-stat-value" style={{ color: 'var(--accent2)' }}>{data.major_count}</div>
        </div>
        <div className="dv-stat">
          <div className="dv-stat-label">Minor</div>
          <div className="dv-stat-value">{data.minor_count}</div>
        </div>
      </div>

      <div className="dv-section">
        <div className="dv-notes-title">Executive Summary</div>
        <p className="dv-body-text">{data.executive_summary}</p>
      </div>

      <div className="dv-section">
        <div className="dv-notes-title">Issues ({data.issues.length})</div>
        {data.issues.map((issue, i) => (
          <div key={i} className="dv-issue">
            <div className="dv-issue-header">
              <span className="dv-issue-id">{issue.issue_id}</span>
              <span className="dv-severity-badge" style={{ color: severityColor[issue.severity] ?? 'var(--muted)' }}>
                {issue.severity}
              </span>
              <span className="dv-badge">{issue.check_type.replace('_', ' ')}</span>
              <span style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: '11px' }}>{issue.disciplines_affected.join(' · ')}</span>
            </div>
            <div className="dv-issue-location">{issue.location}</div>
            <p className="dv-issue-desc">{issue.description}</p>
            <p className="dv-issue-rec"><strong>Recommendation:</strong> {issue.recommendation}</p>
            {issue.reference && <p style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: '11px', marginTop: '4px' }}>Ref: {issue.reference}</p>}
          </div>
        ))}
      </div>

      <div className="dv-section">
        <div className="dv-notes-title">Recommended Actions</div>
        <ul className="dv-notes-list">{data.recommended_actions.map((a, i) => <li key={i}>{a}</li>)}</ul>
      </div>
    </div>
  );
}

// ── Proposal view ─────────────────────────────────────────────────────────────

function ProposalView({ data }: { data: ProposalResponse }) {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <div className="dv-content">
      <div className="dv-summary-row">
        <div className="dv-stat highlight">
          <div className="dv-stat-label">Total Fee</div>
          <div className="dv-stat-value accent">{USD.format(data.total_fee_usd)}</div>
        </div>
        <div className="dv-stat">
          <div className="dv-stat-label">Timeline</div>
          <div className="dv-stat-value">{data.proposed_timeline_months} mo</div>
        </div>
        <div className="dv-stat">
          <div className="dv-stat-label">Prepared by</div>
          <div className="dv-stat-value" style={{ fontSize: '18px' }}>{data.prepared_by}</div>
        </div>
      </div>

      <div className="dv-section">
        <div className="dv-notes-title">Fee Schedule</div>
        <table className="dv-table">
          <thead>
            <tr>
              <th>Phase</th>
              <th>Description</th>
              <th style={{ textAlign: 'right' }}>%</th>
              <th style={{ textAlign: 'right' }}>Fee</th>
            </tr>
          </thead>
          <tbody>
            {data.fee_schedule.map((f, i) => (
              <tr key={i}>
                <td style={{ color: 'var(--accent)', fontFamily: 'var(--mono)', fontSize: '11px' }}>{f.phase}</td>
                <td>{f.description}</td>
                <td style={{ textAlign: 'right' }}>{f.percentage_of_total}%</td>
                <td style={{ textAlign: 'right', color: 'var(--text)' }}>{USD.format(f.fee_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.sections.map((sec, i) => (
        <div key={i} className="dv-accordion">
          <button className="dv-accordion-header" onClick={() => setOpen(open === i ? null : i)}>
            <span>{sec.heading}</span>
            <span className="dv-chevron">{open === i ? '−' : '+'}</span>
          </button>
          {open === i && (
            <div className="dv-accordion-body">
              <pre className="dv-proposal-text">{sec.content}</pre>
            </div>
          )}
        </div>
      ))}

      <div className="dv-notes-grid">
        <div>
          <div className="dv-notes-title">Key Assumptions</div>
          <ul className="dv-notes-list">{data.key_assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
        </div>
        <div>
          <div className="dv-notes-title">Exclusions</div>
          <ul className="dv-notes-list">{data.exclusions.map((e, i) => <li key={i}>{e}</li>)}</ul>
        </div>
      </div>
    </div>
  );
}

// ── Main viewer ───────────────────────────────────────────────────────────────

const LABELS: Record<DeliverableType, string> = {
  takeoff: 'Quantity Takeoff',
  spec: 'Technical Specification',
  consistency: 'Consistency Check',
  proposal: 'Project Proposal',
};

export default function DeliverableViewer({ type, data, onClose }: DeliverableViewerProps) {
  function handleCopy() {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
  }

  function handlePrint() {
    window.print();
  }

  return (
    <div className="dv-shell">
      <div className="dv-header">
        <div>
          <div className="section-label">{LABELS[type]}</div>
          <h2 className="dv-title">{'project_name' in data ? data.project_name : ''}</h2>
        </div>
        <div className="dv-actions">
          <button className="btn-ghost dv-btn" onClick={handleCopy}>Copy JSON</button>
          <button className="btn-ghost dv-btn" onClick={handlePrint}>Print</button>
          <button className="btn-ghost dv-btn" onClick={onClose}>✕ Close</button>
        </div>
      </div>

      {type === 'takeoff' && <TakeoffView data={data as TakeoffResponse} />}
      {type === 'spec' && <SpecView data={data as SpecResponse} />}
      {type === 'consistency' && <ConsistencyView data={data as ConsistencyResponse} />}
      {type === 'proposal' && <ProposalView data={data as ProposalResponse} />}
    </div>
  );
}
