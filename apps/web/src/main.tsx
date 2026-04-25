import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import './index.css';
import { getToken } from './api';
import Home from './pages/Home';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import LegalPage from './pages/LegalPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return getToken() ? <>{children}</> : <Navigate to="/login" replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Auth />} />
        <Route path="/privacy" element={<LegalPage variant="privacy" />} />
        <Route path="/terms" element={<LegalPage variant="terms" />} />
        <Route path="/refund-policy" element={<LegalPage variant="refund" />} />
        <Route path="/billing" element={<LegalPage variant="billing" />} />
        <Route path="/billing/success" element={<LegalPage variant="billing-success" />} />
        <Route path="/billing/cancel" element={<LegalPage variant="billing-cancel" />} />
        <Route path="/indemnification" element={<LegalPage variant="terms" />} />
        <Route
          path="/app"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
