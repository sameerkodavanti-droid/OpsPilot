from typing import TypedDict, Optional, List

class IncidentState(TypedDict):
    incident_id: int
    title: str
    description: str
    
    # Gathered evidence
    logs_evidence: Optional[str]
    metrics_evidence: Optional[str]
    db_evidence: Optional[str]
    
    # Diagnosis
    root_cause: Optional[str]
    confidence: Optional[str]
    
    # RAG
    runbook_instructions: Optional[str]
    
    # Action
    proposed_remediation: Optional[str]
    
    # Approval & Execution
    approval_status: Optional[str] # PENDING, APPROVED, REJECTED
    executed_action: Optional[str]
    
    # Verification
    verification_status: Optional[str] # PASS, FAIL
    
    # Final output
    final_report: Optional[str]
