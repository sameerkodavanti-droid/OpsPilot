import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Bot, CheckCircle, Clock, XCircle, AlertTriangle, ShieldCheck, Activity } from 'lucide-react';

export default function IncidentView() {
  const { id } = useParams();
  const [incident, setIncident] = useState(null);
  const [envData, setEnvData] = useState(null);
  const [loadingAction, setLoadingAction] = useState(false);
  
  const pollInterval = useRef(null);

  const fetchIncident = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/incident/${id}`);
      const data = await res.json();
      setIncident(data);
      
      // Stop polling if resolved/rejected
      if (data.db_info?.status === 'RESOLVED' || data.db_info?.status === 'REJECTED' || data.db_info?.status === 'REMEDIATION_FAILED') {
        clearInterval(pollInterval.current);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchEnvironment = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/environment');
      const data = await res.json();
      setEnvData(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchIncident();
    fetchEnvironment();
    
    pollInterval.current = setInterval(() => {
      fetchIncident();
      fetchEnvironment();
    }, 2000);
    
    return () => clearInterval(pollInterval.current);
  }, [id]);

  const handleApprove = async (action) => {
    setLoadingAction(true);
    try {
      await fetch(`http://localhost:8000/api/incident/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      // Immediately refresh
      fetchIncident();
    } catch (e) {
      console.error(e);
      alert('Action failed');
    }
    setLoadingAction(false);
  };

  if (!incident || !envData) return <div style={{ textAlign: 'center', padding: '100px' }}>Loading telemetry...</div>;

  const db = incident.db_info;
  const state = incident.graph_state;
  const isWaiting = incident.waiting_on?.includes('human_approval_checkpoint');

  const getStatusColor = (status) => {
    if (status === 'RESOLVED') return 'badge-success';
    if (status === 'REJECTED' || status === 'REMEDIATION_FAILED') return 'badge-high';
    if (status === 'AWAITING_APPROVAL') return 'badge-warning';
    return 'badge-info';
  };

  return (
    <div className="flex-col" style={{ gap: '24px' }}>
      
      {/* Header Info */}
      <div className="glass-panel flex-row" style={{ justifyContent: 'space-between' }}>
        <div>
          <div className="flex-row" style={{ marginBottom: '8px' }}>
            <span className={`badge ${getStatusColor(db.status)}`}>{db.status}</span>
            <span className="badge badge-high">{db.severity}</span>
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Incident #{db.id}</span>
          </div>
          <h2 style={{ margin: 0 }}>{db.title}</h2>
        </div>
      </div>

      <div className="grid-2">
        {/* Left Column: Workflow & Metrics */}
        <div className="flex-col" style={{ gap: '24px' }}>
          
          {/* Live Metrics */}
          <div className="glass-panel">
            <h3 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={20} color="var(--accent-blue)" /> 
              Live Environment Telemetry
            </h3>
            <div className="metric-grid">
              <div className={`metric-card ${envData.payment_api_error_rate > 1 ? 'alert' : 'good'}`}>
                <span className="metric-label">Error Rate</span>
                <span className="metric-value">{envData.payment_api_error_rate.toFixed(2)}%</span>
              </div>
              <div className={`metric-card ${envData.payment_api_latency > 1 ? 'alert' : 'good'}`}>
                <span className="metric-label">Latency (p95)</span>
                <span className="metric-value">{envData.payment_api_latency.toFixed(2)}s</span>
              </div>
              <div className={`metric-card ${(envData.db_pool_active/envData.db_pool_max) > 0.8 ? 'alert' : 'good'}`}>
                <span className="metric-label">DB Pool</span>
                <span className="metric-value">{envData.db_pool_active}/{envData.db_pool_max}</span>
              </div>
              {envData.scenario === 'disk_full' && (
                <div className={`metric-card ${envData.disk_space_used > 80 ? 'alert' : 'good'}`}>
                  <span className="metric-label">Disk Space</span>
                  <span className="metric-value">{envData.disk_space_used}%</span>
                </div>
              )}
              {envData.scenario === 'rate_limiting' && (
                <div className={`metric-card ${envData.api_429_count > 0 ? 'alert' : 'good'}`}>
                  <span className="metric-label">HTTP 429s</span>
                  <span className="metric-value">{envData.api_429_count}</span>
                </div>
              )}
            </div>
          </div>

          {/* Workflow Status */}
          <div className="glass-panel">
            <h3 style={{ margin: '0 0 16px 0' }}>AI Investigation Graph</h3>
            <div className="flex-col" style={{ gap: '0' }}>
              <NodeItem label="Planner Node" done={true} />
              <NodeItem label="Investigation Agents (Log, Metrics, DB)" done={!!state.logs_evidence} active={!state.logs_evidence && db.status === 'INVESTIGATING'} />
              <NodeItem label="Diagnosis Agent" done={!!state.root_cause} active={state.logs_evidence && !state.root_cause} />
              <NodeItem label="RAG Runbook Retrieval" done={!!state.runbook_instructions} active={state.root_cause && !state.runbook_instructions} />
              <NodeItem label="Remediation Agent" done={!!state.proposed_remediation} active={state.runbook_instructions && !state.proposed_remediation} />
              <NodeItem label="Human Approval" done={!!db.human_decision} active={isWaiting} warning={isWaiting} />
              <NodeItem label="Execution Agent" done={!!state.executed_action} active={db.human_decision === 'APPROVE' && !state.executed_action} />
              <NodeItem label="Verify & Report Node" done={!!state.final_report} active={state.executed_action && !state.final_report} />
            </div>
          </div>

        </div>

        {/* Right Column: AI Output & Actions */}
        <div className="glass-panel flex-col" style={{ maxHeight: '800px', overflowY: 'auto' }}>
          
          {db.status === 'INVESTIGATING' && !isWaiting && (
            <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-secondary)' }}>
              <Bot size={48} className="pulse" style={{ margin: '0 auto 16px', color: 'var(--accent-blue)' }} />
              <h3>Agents Investigating...</h3>
              <p>Analyzing telemetry and querying runbooks.</p>
            </div>
          )}

          {state.proposed_remediation && !state.final_report && (
            <div className="flex-col" style={{ gap: '16px' }}>
              <div style={{ padding: '16px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '12px', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-neon-blue)', margin: '0 0 12px 0' }}>
                  <AlertTriangle size={20} /> Diagnosis: {state.root_cause}
                </h3>
                <p style={{ margin: 0, fontSize: '0.9rem' }}>Confidence: {state.confidence}</p>
              </div>

              <div>
                <h3 style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>Proposed Remediation</h3>
                <div className="md-content">
                  <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', background: 'transparent', padding: 0, border: 'none' }}>
                    {state.proposed_remediation}
                  </pre>
                </div>
              </div>

              {isWaiting && (
                <div style={{ marginTop: '24px', padding: '24px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
                  <h3 style={{ textAlign: 'center', margin: '0 0 20px 0' }}>Execute this plan?</h3>
                  <div className="grid-2">
                    <button onClick={() => handleApprove('REJECT')} disabled={loadingAction} className="btn btn-outline" style={{ padding: '16px', color: 'var(--accent-red)', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
                      <XCircle size={20} /> REJECT
                    </button>
                    <button onClick={() => handleApprove('APPROVE')} disabled={loadingAction} className="btn btn-success">
                      <ShieldCheck size={20} /> APPROVE & EXECUTE
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {state.final_report && (
            <div className="flex-col">
              <div style={{ padding: '16px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '12px', border: '1px solid rgba(16, 185, 129, 0.2)', marginBottom: '16px' }}>
                <h3 style={{ color: 'var(--accent-green)', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CheckCircle size={20} /> Remediation Executed
                </h3>
                <p style={{ margin: 0 }}>Metrics verified successfully.</p>
              </div>
              <h3 style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>Final Incident Report</h3>
              <div className="md-content">
                <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', background: 'transparent', padding: 0, border: 'none' }}>
                  {state.final_report}
                </pre>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

function NodeItem({ label, done, active, warning }) {
  let icon = <Clock size={16} color="var(--text-secondary)" />;
  let className = "workflow-node";
  
  if (done) {
    icon = <CheckCircle size={16} color="var(--accent-green)" />;
    className += " done";
  } else if (active) {
    icon = <Activity size={16} color="var(--accent-blue)" />;
    className += " active pulse";
  }

  if (warning) {
    className = "workflow-node";
    className += " active";
    icon = <AlertTriangle size={16} color="var(--accent-yellow)" />;
  }

  return (
    <div className={className}>
      {icon}
      <span style={{ 
        fontWeight: active || done ? 500 : 400,
        color: done ? 'var(--text-primary)' : (active ? 'var(--accent-neon-blue)' : 'var(--text-secondary)')
      }}>
        {label}
      </span>
      {warning && <span className="badge badge-warning" style={{ marginLeft: 'auto' }}>ACTION REQUIRED</span>}
    </div>
  );
}
