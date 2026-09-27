from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database.session import Base
from sqlalchemy.orm import relationship

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    status = Column(String, default="INVESTIGATING") # INVESTIGATING, AWAITING_APPROVAL, REMEDIATING, RESOLVED, REMEDIATION_FAILED
    severity = Column(String)
    
    # Text summary of the initial problem
    description = Column(Text)
    
    # Results of the investigation
    root_cause = Column(Text, nullable=True)
    confidence = Column(String, nullable=True)
    
    # RAG/Runbook info
    retrieved_runbook = Column(Text, nullable=True)
    
    # Action plans
    proposed_remediation = Column(Text, nullable=True)
    human_decision = Column(String, nullable=True) # APPROVED, REJECTED, None
    executed_action = Column(Text, nullable=True)
    
    # Verification
    verification_result = Column(Text, nullable=True)
    final_report = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    evidence = relationship("Evidence", back_populates="incident")

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    
    source = Column(String) # "LOGS", "METRICS", "DATABASE"
    findings = Column(JSON) # Store raw JSON payload or text findings
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    incident = relationship("Incident", back_populates="evidence")
