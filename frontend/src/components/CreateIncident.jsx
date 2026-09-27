import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, Zap, HardDrive, ShieldAlert, ArrowRight, ActivitySquare } from 'lucide-react';

const SCENARIOS = [
  {
    id: 'db_pool',
    title: 'DB Exhaustion',
    icon: <Database size={24} />,
    desc: 'Payment API is experiencing a large increase in HTTP 500 errors. 18% failure rate, latency at 2.8s.'
  },
  {
    id: 'gateway',
    title: 'Gateway Timeout',
    icon: <Zap size={24} />,
    desc: 'Payment API is returning HTTP 504 Gateway Timeout errors. Upstream provider timing out after 5s.'
  },
  {
    id: 'deadlock',
    title: 'DB Deadlocks',
    icon: <ActivitySquare size={24} />,
    desc: 'Multiple deadlock alerts firing on the primary database. Transactions running for over 8 minutes.'
  },
  {
    id: 'disk_full',
    title: 'Disk Space Full',
    icon: <HardDrive size={24} />,
    desc: 'CRITICAL: No space left on device in Payment API node. /var/log is full.'
  },
  {
    id: 'rate_limit',
    title: 'API Rate Limiting',
    icon: <ShieldAlert size={24} />,
    desc: 'Clients are receiving HTTP 429 Too Many Requests errors from the Payment API during a flash sale.'
  }
];

export default function CreateIncident() {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleScenarioClick = (scenario) => {
    setTitle(scenario.title);
    setDescription(scenario.desc);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title || !description) return;
    
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/incident', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description, severity: 'HIGH' })
      });
      const data = await res.json();
      navigate(`/incident/${data.incident_id}`);
    } catch (err) {
      console.error(err);
      alert('Failed to trigger incident. Is the backend running?');
      setLoading(false);
    }
  };

  return (
    <div className="flex-col" style={{ gap: '32px' }}>
      <div>
        <h2 style={{ fontSize: '2rem', marginBottom: '8px' }}>Trigger an Incident</h2>
        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Select a predefined disaster scenario or type your own.</p>
      </div>

      <div className="grid-2">
        <div className="glass-panel flex-col">
          <h3 style={{ marginBottom: '8px' }}>Scenarios</h3>
          <div className="flex-col" style={{ gap: '12px' }}>
            {SCENARIOS.map(s => (
              <div 
                key={s.id}
                onClick={() => handleScenarioClick(s)}
                style={{
                  display: 'flex',
                  gap: '16px',
                  padding: '16px',
                  background: title === s.title ? 'rgba(59, 130, 246, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                  border: `1px solid ${title === s.title ? 'var(--accent-blue)' : 'var(--border-subtle)'}`,
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ color: title === s.title ? 'var(--accent-blue)' : 'var(--text-secondary)' }}>
                  {s.icon}
                </div>
                <div>
                  <h4 style={{ margin: '0 0 4px 0', color: title === s.title ? '#fff' : 'var(--text-primary)' }}>{s.title}</h4>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel">
          <h3 style={{ marginBottom: '24px' }}>Custom Incident</h3>
          <form onSubmit={handleSubmit} className="flex-col" style={{ gap: '20px' }}>
            <div className="form-group">
              <label>Incident Title</label>
              <input 
                className="form-input"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="e.g. Database Exhaustion"
                required
              />
            </div>
            
            <div className="form-group">
              <label>PagerDuty Alert Description</label>
              <textarea 
                className="form-input"
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Paste the raw alert text here..."
                rows={6}
                required
              />
            </div>
            
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ padding: '16px', fontSize: '1.1rem', marginTop: '12px' }}>
              {loading ? 'Paging Agents...' : 'TRIGGER INCIDENT'}
              {!loading && <ArrowRight size={20} />}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
