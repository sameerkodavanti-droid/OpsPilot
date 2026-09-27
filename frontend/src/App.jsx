import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ShieldAlert, Activity } from 'lucide-react';
import CreateIncident from './components/CreateIncident';
import IncidentView from './components/IncidentView';
import './index.css';

function App() {
  return (
    <Router>
      <div className="app-container">
        <header className="glass-header">
          <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ background: 'rgba(59, 130, 246, 0.2)', padding: '10px', borderRadius: '12px' }}>
              <ShieldAlert size={28} color="var(--accent-blue)" />
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: '1.5rem', letterSpacing: '1px' }}>OpsPilot</h1>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', letterSpacing: '2px' }}>AGENTIC INCIDENT RESPONSE</span>
            </div>
          </Link>
          <div className="flex-row" style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '6px 12px', borderRadius: '20px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
            <Activity size={16} color="var(--accent-green)" />
            <span style={{ color: 'var(--accent-green)', fontSize: '0.85rem', fontWeight: 600 }}>SYSTEM ONLINE</span>
          </div>
        </header>

        <Routes>
          <Route path="/" element={<CreateIncident />} />
          <Route path="/incident/:id" element={<IncidentView />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
