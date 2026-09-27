# OpsPilot

Agentic Incident Detection, Diagnosis, Remediation & Verification System.

## Overview
OpsPilot is an AI-powered incident-response system that reduces the manual effort required to investigate and resolve application incidents. It uses LangGraph to coordinate several specialized AI agents that query logs and metrics, diagnose root causes, and retrieve relevant organization runbooks using RAG (ChromaDB).

OpsPilot incorporates a Human-in-the-Loop mechanism to safely pause execution and wait for human approval before applying any remediations.

## Architecture

- **FastAPI**: Provides API endpoints for starting incidents, fetching status, approving remediations, and retrieving reports.
- **PostgreSQL**: Stores an audit trail of incidents, evidence, approvals, and execution history. Also acts as the checkpointer for the LangGraph state.
- **LangGraph**: Orchestrates the multi-agent workflow (Planner, Log Agent, Metrics Agent, Diagnosis Agent, Remediation Agent, Verification Agent).
- **RAG / ChromaDB**: Retrieves organization-specific troubleshooting runbooks from the `runbooks/` directory.

## Getting Started

1. Fill in the `.env` file with your PostgreSQL connection strings and OpenAI API keys.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Demo Scenario API Flow
1. **Trigger Incident**
   `POST /api/incident`
   ```json
   {
       "title": "Payment API Failure",
       "description": "Payment API is experiencing a large increase in HTTP 500 errors. 18% failure rate, latency at 2.8s."
   }
   ```
2. **Check Status** (Wait for human approval)
   `GET /api/incident/{id}`

3. **Approve Remediation**
   `POST /api/incident/{id}/approve`
   ```json
   {
       "action": "APPROVE"
   }
   ```

4. **Retrieve Final Report**
   `GET /api/incident/{id}/report`
