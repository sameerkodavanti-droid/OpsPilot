from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import models, session
from app.workflow.graph import get_compiled_graph
from pydantic import BaseModel
from psycopg_pool import ConnectionPool
from app.simulation.environment import env

router = APIRouter()
pool = None

def set_pool(p: ConnectionPool):
    global pool
    pool = p

class IncidentRequest(BaseModel):
    title: str
    description: str
    severity: str = "HIGH"

class ApprovalRequest(BaseModel):
    action: str # "APPROVE" or "REJECT"

def run_graph_background(incident_id: int, title: str, description: str):
    graph = get_compiled_graph(pool)
    config = {"configurable": {"thread_id": str(incident_id)}}
    
    state_input = {
        "incident_id": incident_id,
        "title": title,
        "description": description
    }
    
    existing_state = graph.get_state(config)
    
    if not existing_state.next: # new run
        for _ in graph.stream(state_input, config):
            pass
    else:
        # resuming
        for _ in graph.stream(None, config):
            pass
    
    # Sync final graph state back to PostgreSQL incident record
    final_state = graph.get_state(config).values
    db = session.SessionLocal()
    db_incident = db.query(models.Incident).filter(models.Incident.id == incident_id).first()
    
    if db_incident:
        db_incident.root_cause = final_state.get("root_cause")
        db_incident.confidence = final_state.get("confidence")
        db_incident.retrieved_runbook = final_state.get("runbook_instructions")
        db_incident.proposed_remediation = final_state.get("proposed_remediation")
        db_incident.executed_action = final_state.get("executed_action")
        db_incident.verification_result = final_state.get("verification_status")
        db_incident.final_report = final_state.get("final_report")
        
        # Determine status
        next_nodes = graph.get_state(config).next
        if "human_approval_checkpoint" in next_nodes:
            db_incident.status = "AWAITING_APPROVAL"
        elif final_state.get("final_report"):
            if final_state.get("verification_status") == "PASS":
                db_incident.status = "RESOLVED"
            elif final_state.get("approval_status") == "REJECTED":
                db_incident.status = "REJECTED"
            else:
                db_incident.status = "REMEDIATION_FAILED"
        else:
            db_incident.status = "INVESTIGATING"
            
        db.commit()
    db.close()

@router.post("/incident")
def create_incident(req: IncidentRequest, background_tasks: BackgroundTasks, db: Session = Depends(session.get_db)):
    
    # Configure simulation based on incident description
    desc = req.description.lower()
    if "deadlock" in desc:
        env.set_scenario("deadlock")
    elif "504" in desc or "gateway" in desc:
        env.set_scenario("gateway_timeout")
    elif "disk" in desc or "space" in desc:
        env.set_scenario("disk_full")
    elif "429" in desc or "rate" in desc:
        env.set_scenario("rate_limiting")
    else:
        env.set_scenario("payment_db_pool")
        
    incident = models.Incident(
        title=req.title,
        description=req.description,
        severity=req.severity,
        status="INVESTIGATING"
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    
    background_tasks.add_task(run_graph_background, incident.id, req.title, req.description)
    return {"message": "Incident created and investigation started.", "incident_id": incident.id}

@router.get("/incident/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(session.get_db)):
    incident = db.query(models.Incident).filter(models.Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    graph = get_compiled_graph(pool)
    config = {"configurable": {"thread_id": str(incident_id)}}
    state = graph.get_state(config)
    
    return {
        "db_info": incident,
        "graph_state": state.values,
        "waiting_on": state.next
    }

@router.post("/incident/{incident_id}/approve")
def approve_incident(incident_id: int, req: ApprovalRequest, background_tasks: BackgroundTasks, db: Session = Depends(session.get_db)):
    incident = db.query(models.Incident).filter(models.Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    action = req.action.upper()
    if action not in ["APPROVE", "REJECT"]:
        raise HTTPException(status_code=400, detail="Action must be APPROVE or REJECT")
        
    incident.human_decision = action
    db.commit()
    
    graph = get_compiled_graph(pool)
    config = {"configurable": {"thread_id": str(incident_id)}}
    
    # Ensure it's actually waiting
    state = graph.get_state(config)
    if "human_approval_checkpoint" not in state.next:
        raise HTTPException(status_code=400, detail="Incident is not waiting for approval")
    
    # Update state in graph
    graph.update_state(config, {"approval_status": "APPROVED" if action == "APPROVE" else "REJECTED"})
    
    # Resume graph execution
    background_tasks.add_task(run_graph_background, incident_id, incident.title, incident.description)
    
    return {"message": f"Incident {action}D, workflow resumed."}

@router.get("/incident/{incident_id}/report")
def get_report(incident_id: int, db: Session = Depends(session.get_db)):
    incident = db.query(models.Incident).filter(models.Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if not incident.final_report:
        return {"message": "Report not generated yet. Check incident status.", "status": incident.status}
        
    return {"report": incident.final_report}

@router.get("/environment")
def get_environment():
    return {
        "payment_api_error_rate": env.payment_api_error_rate,
        "payment_api_latency": env.payment_api_latency,
        "db_pool_active": env.db_pool_active,
        "db_pool_max": env.db_pool_max,
        "db_deadlocks": env.db_deadlocks,
        "gateway_timeout_rate": env.gateway_timeout_rate,
        "disk_space_used": env.disk_space_used,
        "api_429_count": env.api_429_count,
        "scenario": env.scenario
    }
