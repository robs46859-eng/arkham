import React, { useState } from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { getToken } from './api';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';

function App() {
  const [authed, setAuthed] = useState(() => !!getToken());

  return authed
    ? <Dashboard onLogout={() => setAuthed(false)} />
    : <Auth onLogin={() => setAuthed(true)} />;
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
