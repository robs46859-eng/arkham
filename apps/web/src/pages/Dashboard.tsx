import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { callVertical, clearAuth, getTenantId } from '../api';
import type {
  ConsistencyResponse,
  DocumentSection,
  ProposalResponse,
  SpecResponse,
  TakeoffResponse,
} from '../api';
import FileUpload from '../components/FileUpload';
import DeliverableViewer from '../components/DeliverableViewer';

type VerticalKey = 'takeoff' | 'spec' | 'consistency' | 'proposal';

const VERTICALS: { id: VerticalKey; label: string; desc: string; badge: string }[] = [
  { id: 'takeoff',     label: 'Quantity Takeoff',    desc: 'Cost estimate with CSI line items',          badge: 'OMNISCALE'     },
  { id: 'spec',        label: 'Spec Generation',     desc: 'CSI 3-part specification sections',          badge: 'CYBERSCRIBE'   },
  { id: 'consistency', label: 'Doc Coordination',    desc: 'Cross-discipline consistency check',         badge: 'AI CONSISTENCY' },
  { id: 'proposal',    label: 'Proposal Writing',    desc: 'Full architectural project proposal',        badge: 'AUTOPITCH'     },
];

type DeliverableData = TakeoffResponse | SpecResponse | ConsistencyResponse | ProposalResponse;

interface Deliverable {
  id: string;
  type: VerticalKey;
  projectName: string;
  data: DeliverableData;
  createdAt: string;
}

const PROJECT_ID = 'proj_demo_001';

export default function Dashboard() {
  const navigate = useNavigate();
  const tenantId = getTenantId() ?? '';
  const [activeVertical, setActiveVertical] = useState<VerticalKey>('takeoff');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [viewing, setViewing] = useState<Deliverable | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<{ id: string; name: string }[]>([]);

  // ── Form state ─────────────────────────────────────────────────────────────

  const [projectName, setProjectName] = useState('');
  const [projectType, setProjectType] = useState('commercial');
  const [scopeDesc, setScopeDesc] = useState('');
  const [location, setLocation] = useState('');
  const [gfa, setGfa] = useState('');
  const [stories, setStories] = useState('');
  const [constructionType, setConstructionType] = useState('');
  const [clientName, setClientName] = useState('');
  const [firmName, setFirmName] = useState('');
  const [docContent, setDocContent] = useState('');
  const [discipline, setDiscipline] = useState('Architectural');

  function handleLogout() {
    clearAuth();
    navigate('/login', { replace: true });
  }

  function handleFileComplete(fileId: string, fileName: string) {
    setUploadedFiles(prev => [...prev, { id: fileId, name: fileName }]);
  }

  async function handleRun(e: React.FormEvent) {
    e.preventDefault();
    if (!projectName.trim()) { setError('Project name is required'); return; }
    setError('');
    setLoading(true);

    try {
      let data: DeliverableData;

      if (activeVertical === 'takeoff') {
        data = await callVertical<object, TakeoffResponse>('omniscale', 'takeoff', {
          project_name: projectName,
          project_type: projectType,
          location,
          gross_floor_area_sqft: gfa ? parseFloat(gfa) : undefined,
          num_stories: stories ? parseInt(stories) : undefined,
          construction_type: constructionType,
          scope_description: scopeDesc,
        });
      } else if (activeVertical === 'spec') {
        data = await callVertical<object, SpecResponse>('cyberscribe', 'spec', {
          project_name: projectName,
          project_type: projectType,
          scope_description: scopeDesc,
        });
      } else if (activeVertical === 'consistency') {
        const sections: DocumentSection[] = docContent
          ? [{ discipline, document_type: 'Document', content: docContent }]
          : [{ discipline: 'Architectural', document_type: 'Drawings', content: scopeDesc }];
        data = await callVertical<object, ConsistencyResponse>('ai-consistency', 'check', {
          project_name: projectName,
          sections,
        });
      } else {
        data = await callVertical<object, ProposalResponse>('autopitch', 'proposal', {
          project_name: projectName,
          client_name: clientName || 'Client',
          project_type: projectType,
          project_description: scopeDesc,
          location,
          gross_floor_area_sqft: gfa ? parseFloat(gfa) : undefined,
          firm: {
            name: firmName || 'Your Firm',
            years_in_business: 0,
            specialties: [projectType],
            notable_projects: [],
            team_size: 0,
            licenses: [],
          },
        });
      }

      const deliverable: Deliverable = {
        id: `del_${Date.now()}`,
        type: activeVertical,
        projectName,
        data,
        createdAt: new Date().toLocaleTimeString(),
      };
      setDeliverables(prev => [deliverable, ...prev]);
      setViewing(deliverable);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  if (viewing) {
    return (
      <DeliverableViewer
        type={viewing.type}
        data={viewing.data}
        onClose={() => setViewing(null)}
      />
    );
  }

  return (
    <div className="dashboard-shell">
      {/* NAV */}
      <nav>
        <a href="#" className="nav-logo">ROBCO<span>AI</span></a>
        <div style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--muted)', letterSpacing: '1px' }}>
          {tenantId}
        </div>
        <button className="nav-cta" onClick={handleLogout} style={{ cursor: 'pointer' }}>
          Sign Out
        </button>
      </nav>

      <div className="dashboard-body">
        {/* LEFT PANEL */}
        <div className="panel-left">
          <div className="panel-section">
            <div className="section-label">// Select Vertical</div>
            <div className="vertical-list">
              {VERTICALS.map(v => (
                <button
                  key={v.id}
                  className={`vertical-btn${activeVertical === v.id ? ' active' : ''}`}
                  onClick={() => { setActiveVertical(v.id); setError(''); }}
                >
                  <span className="vertical-badge">{v.badge}</span>
                  <div>
                    <div className="vertical-label">{v.label}</div>
                    <div className="vertical-desc">{v.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="panel-section">
            <div className="section-label">// Upload Files</div>
            <FileUpload projectId={PROJECT_ID} onComplete={handleFileComplete} />
            {uploadedFiles.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                {uploadedFiles.map(f => (
                  <div key={f.id} style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--muted)', padding: '4px 0' }}>
                    ✓ {f.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="panel-right">
          <form className="run-form" onSubmit={handleRun}>
            <div className="section-label">// {VERTICALS.find(v => v.id === activeVertical)?.label}</div>
            <h2 className="section-title" style={{ marginBottom: '32px' }}>
              {activeVertical === 'takeoff' && 'QUANTITY\nTAKEOFF'}
              {activeVertical === 'spec' && 'SPEC\nGENERATOR'}
              {activeVertical === 'consistency' && 'DOC\nCOORDINATION'}
              {activeVertical === 'proposal' && 'PROPOSAL\nWRITER'}
            </h2>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Project Name *</label>
                <input className="form-input" value={projectName} onChange={e => setProjectName(e.target.value)} placeholder="Riverside Community Center" required />
              </div>
              <div className="form-group">
                <label className="form-label">Project Type</label>
                <select className="form-input" value={projectType} onChange={e => setProjectType(e.target.value)}>
                  {['commercial', 'residential', 'industrial', 'civic', 'mixed-use', 'healthcare', 'education'].map(t => (
                    <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">
                {activeVertical === 'consistency' ? 'Document Content to Review' : 'Project Scope Description *'}
              </label>
              <textarea
                className="form-input form-textarea"
                value={activeVertical === 'consistency' ? docContent : scopeDesc}
                onChange={e => activeVertical === 'consistency' ? setDocContent(e.target.value) : setScopeDesc(e.target.value)}
                placeholder={
                  activeVertical === 'consistency'
                    ? 'Paste or describe the document content to check for inconsistencies...'
                    : 'Describe the project scope, key systems, special requirements...'
                }
                rows={5}
              />
            </div>

            {activeVertical === 'consistency' && (
              <div className="form-group">
                <label className="form-label">Discipline</label>
                <select className="form-input" value={discipline} onChange={e => setDiscipline(e.target.value)}>
                  {['Architectural', 'Structural', 'MEP', 'Civil', 'Landscape'].map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            )}

            {(activeVertical === 'takeoff' || activeVertical === 'proposal') && (
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Location</label>
                  <input className="form-input" value={location} onChange={e => setLocation(e.target.value)} placeholder="Denver, CO" />
                </div>
                <div className="form-group">
                  <label className="form-label">GFA (SF)</label>
                  <input className="form-input" type="number" value={gfa} onChange={e => setGfa(e.target.value)} placeholder="25000" />
                </div>
              </div>
            )}

            {activeVertical === 'takeoff' && (
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Stories</label>
                  <input className="form-input" type="number" value={stories} onChange={e => setStories(e.target.value)} placeholder="3" />
                </div>
                <div className="form-group">
                  <label className="form-label">Construction Type</label>
                  <input className="form-input" value={constructionType} onChange={e => setConstructionType(e.target.value)} placeholder="Type II-B steel frame" />
                </div>
              </div>
            )}

            {activeVertical === 'proposal' && (
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Client Name</label>
                  <input className="form-input" value={clientName} onChange={e => setClientName(e.target.value)} placeholder="City of Denver" />
                </div>
                <div className="form-group">
                  <label className="form-label">Your Firm Name</label>
                  <input className="form-input" value={firmName} onChange={e => setFirmName(e.target.value)} placeholder="Axis Architecture Group" />
                </div>
              </div>
            )}

            {error && <div className="auth-error">{error}</div>}

            <button className="btn-primary run-btn" type="submit" disabled={loading}>
              {loading ? (
                <><span className="upload-spinner" style={{ marginRight: '8px' }} />Generating...</>
              ) : (
                `Generate ${VERTICALS.find(v => v.id === activeVertical)?.label}`
              )}
            </button>
          </form>

          {/* RECENT DELIVERABLES */}
          {deliverables.length > 0 && (
            <div className="deliverables-list">
              <div className="section-label" style={{ marginBottom: '16px' }}>// Recent Deliverables</div>
              {deliverables.map(d => (
                <button key={d.id} className="deliverable-item" onClick={() => setViewing(d)}>
                  <div>
                    <div className="deliverable-name">{d.projectName}</div>
                    <div className="deliverable-meta">{VERTICALS.find(v => v.id === d.type)?.label} · {d.createdAt}</div>
                  </div>
                  <span className="dv-badge">{VERTICALS.find(v => v.id === d.type)?.badge}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
