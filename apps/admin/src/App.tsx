import React, { useState } from 'react';
import TenantsView from './views/TenantsView';
import JobsView from './views/JobsView';
import UsageView from './views/UsageView';
import ProjectsView from './views/ProjectsView';
import WorkflowMemoryView from './views/WorkflowMemoryView';
import GovernanceView from './views/GovernanceView';

type Tab = 'tenants' | 'jobs' | 'usage' | 'projects' | 'workflow-memory' | 'governance';

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'tenants',  label: 'Tenants',  icon: '🏢' },
  { id: 'jobs',     label: 'Jobs',     icon: '⚙️' },
  { id: 'usage',    label: 'Usage',    icon: '📊' },
  { id: 'projects', label: 'Projects', icon: '📁' },
  { id: 'workflow-memory', label: 'Workflow Memory', icon: '🧠' },
  { id: 'governance', label: 'Governance', icon: '🛡️' },
];

export default function App() {
  const [tab, setTab] = useState<Tab>('tenants');

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span className="logo-mark">R</span>
          <span className="logo-text">Robco Admin</span>
        </div>
        <nav className="sidebar-nav">
          {TABS.map(t => (
            <button
              key={t.id}
              className={`nav-item ${tab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              <span className="nav-icon">{t.icon}</span>
              <span className="nav-label">{t.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="version-tag">v0.1.0 · dev</span>
        </div>
      </aside>

      <main className="content">
        {tab === 'tenants'  && <TenantsView />}
        {tab === 'jobs'     && <JobsView />}
        {tab === 'usage'    && <UsageView />}
        {tab === 'projects' && <ProjectsView />}
        {tab === 'workflow-memory' && <WorkflowMemoryView />}
        {tab === 'governance' && <GovernanceView />}
      </main>
    </div>
  );
}
