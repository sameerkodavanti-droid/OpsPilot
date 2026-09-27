# OpsPilot — Complete Project Explanation

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [What OpsPilot Does](#2-what-opspilot-does)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Architecture](#5-architecture)
6. [Multi-Agent System](#6-multi-agent-system)
7. [LangGraph Workflow](#7-langgraph-workflow)
8. [LangGraph State](#8-langgraph-state)
9. [RAG / Runbook Retrieval](#9-rag--runbook-retrieval)
10. [Simulated Tool Layer](#10-simulated-tool-layer)
11. [Database Schema](#11-database-schema)
12. [API Endpoints](#12-api-endpoints)
13. [End-to-End Demo Flow](#13-end-to-end-demo-flow)
14. [Human-in-the-Loop Safety](#14-human-in-the-loop-safety)
15. [Verification Loop](#15-verification-loop)

---

## 1. Problem Statement

Incident response in modern software engineering is slow and manual. When an application like a Payment API starts failing, a developer/SRE typically has to:

1. Receive an alert
2. Manually check application logs
3. Manually check API error rates
4. Manually check CPU, memory, and latency dashboards
5. Manually check database metrics
6. Search through internal runbooks and documentation
7. Determine the root cause themselves
8. Decide on a fix
9. Execute the fix
10. Manually verify whether it worked
11. Write an incident report

This entire process can take **30 minutes to several hours**, during which the production system is degraded and users are affected.

**OpsPilot automates steps 2–11**, while keeping a human in control of any actual system change. The goal is not to replace engineers — it is to eliminate the tedious investigation work so engineers can focus on approving decisions, not discovering them.

---

## 2. What OpsPilot Does

OpsPilot is an **Agentic Incident Response System**. Given a natural-language description of an incident, it:

| Step | What Happens |
|------|-------------|
| **Detect** | Receives an incident via API call |
| **Investigate** | Queries logs, metrics, and database stats automatically using AI-powered tool-calling |
| **Correlate** | Cross-references multiple evidence sources |
| **Diagnose** | Uses an LLM to determine the root cause and a confidence score |
| **Retrieve** | Searches the runbook knowledge base via semantic RAG |
| **Recommend** | Proposes a concrete, runbook-grounded remediation plan |
| **Pause** | Suspends itself and waits for human YES/NO approval |
| **Execute** | Runs the approved remediation through controlled tools |
| **Verify** | Re-checks metrics to confirm the fix worked |
| **Report** | Generates a full auditable incident report |
| **Store** | Persists every step in PostgreSQL |

---

## 3. Technology Stack

| Technology | Role |
|-----------|------|
| **Python** | Primary language |
| **FastAPI** | REST API layer — exposes endpoints for incident management |
| **LangChain** | LLM integration, tool-calling, RAG, prompts |
| **LangGraph** | Stateful multi-agent workflow orchestration |
| **Groq + LLM** | Reasoning engine for all agents (swappable with OpenAI) |
| **ChromaDB** | Local vector store for runbook embeddings |
| **PostgreSQL** | Persistent store for incidents, evidence, and audit trail |
| **psycopg (v3)** | PostgreSQL driver used by both SQLAlchemy and LangGraph checkpointer |
| **psycopg-pool** | Connection pooling for the LangGraph PostgreSQL checkpointer |
| **SQLAlchemy** | ORM layer for PostgreSQL |
| **pydantic-settings** | Type-safe configuration loaded from `.env` |

### Why NOT Kafka, Kubernetes, Terraform, etc.?

OpsPilot is intentionally minimal. The purpose is to be **explainable, runnable locally, and focused on the core problem**: multi-agent incident reasoning. Platform-level tooling would add noise without adding value to the reasoning pipeline.

---

## 4. Project Structure

```
opspilot/
│
├── .env                          # API keys and DB connection string
├── requirements.txt              # Python dependencies
├── explanation.md                # This file
├── README.md                     # Quick-start guide
│
├── runbooks/                     # Organization knowledge base (RAG source)
│   ├── payment_api.md            # Payment API troubleshooting runbook
│   └── database.md               # Database troubleshooting runbook
│
├── chroma_db/                    # Auto-generated ChromaDB vector store (gitignore this)
│
└── app/
    ├── main.py                   # FastAPI app entrypoint + lifespan setup
    ├── config.py                 # Pydantic settings (reads .env)
    │
    ├── api/
    │   └── routes.py             # All REST API route handlers
    │
    ├── database/
    │   ├── session.py            # SQLAlchemy engine + session factory
    │   └── models.py             # PostgreSQL ORM models (Incident, Evidence)
    │
    ├── rag/
    │   └── retriever.py          # ChromaDB setup + runbook retrieval function
    │
    ├── tools/
    │   └── simulated_systems.py  # @tool-decorated mock log/metric/DB functions
    │
    └── workflow/
        ├── state.py              # LangGraph IncidentState TypedDict
        ├── nodes.py              # All agent node implementations
        └── graph.py              # LangGraph graph assembly + PostgreSQL checkpointer
```

---

## 5. Architecture

```
                        ┌─────────────────────────┐
                        │        FastAPI           │
                        │  POST /api/incident      │
                        │  GET  /api/incident/{id} │
                        │  POST /api/incident/{id} │
                        │       /approve           │
                        │  GET  /api/incident/{id} │
                        │       /report            │
                        └────────────┬────────────┘
                                     │ triggers (background task)
                                     ▼
                        ┌────────────────────────────┐
                        │      LangGraph Graph        │
                        │   (Stateful Workflow)        │
                        │                              │
                        │   Planner                    │
                        │      ├─► Log Agent           │◄── query_logs tool
                        │      ├─► Metrics Agent       │◄── query_metrics tool
                        │      └─► DB Agent            │◄── query_database_status tool
                        │              │               │
                        │         Diagnosis Agent      │
                        │              │               │
                        │          RAG Node            │◄── ChromaDB (runbooks/)
                        │              │               │
                        │       Remediation Agent      │
                        │              │               │
                        │    *** INTERRUPT ***         │◄── Human approval via API
                        │              │               │
                        │    Execute Remediation       │
                        │              │               │
                        │         Verify Node          │
                        │         ┌───┴───┐            │
                        │       PASS     FAIL          │
                        │         │       └─► re-investigate
                        │       Report                 │
                        └──────────┬───────────────────┘
                                   │
                                   ▼
                      ┌────────────────────────┐
                      │      PostgreSQL          │
                      │  • incidents table       │
                      │  • evidence table        │
                      │  • LangGraph checkpoint  │
                      │    tables (auto-created) │
                      └────────────────────────┘
```

---

## 6. Multi-Agent System

OpsPilot uses **5 specialized agents**, each with a clearly scoped responsibility.

### Agent 1: Planner Node
- **File:** `app/workflow/nodes.py` → `planner_node()`
- **Role:** Entry point of the workflow. Receives the incident and triggers investigation.
- **Note:** In the current version it passes the state through. In a more advanced version it could decide which agents to activate based on incident type.

---

### Agent 2: Log Agent
- **File:** `app/workflow/nodes.py` → `log_agent_node()`
- **Role:** Investigates application logs.
- **How it works:**
  1. The LLM is given the incident description and bound to the `query_logs` tool.
  2. The LLM decides which service to query and with what time range.
  3. The tool returns raw log lines (e.g., 45 `ConnectionPoolTimeout` errors).
  4. The LLM reads the tool output and writes a natural-language summary of what it found.
- **Key tool:** `query_logs(service_name, time_range)`

---

### Agent 3: Metrics Agent
- **File:** `app/workflow/nodes.py` → `metrics_agent_node()`
- **Role:** Investigates system-level metrics like error rate and latency.
- **How it works:** Same pattern — LLM with tool binding, decides what to query, calls `query_metrics`, reads and summarizes the result.
- **Key tool:** `query_metrics(service_name, metric_name)`

---

### Agent 4: DB Agent
- **File:** `app/workflow/nodes.py` → `db_agent_node()`
- **Role:** Investigates database health — connection pool saturation, active connections, CPU.
- **Key tool:** `query_database_status(db_name)`

> Log Agent, Metrics Agent, and DB Agent run **in parallel** in the LangGraph graph. All three feed their results into the Diagnosis Agent.

---

### Agent 5: Diagnosis Agent
- **File:** `app/workflow/nodes.py` → `diagnosis_agent_node()`
- **Role:** Correlates evidence from all 3 investigation agents to determine root cause.
- **How it works:** Receives a combined prompt containing all evidence. The LLM reasons across all signals and produces structured JSON:
  ```json
  { "root_cause": "Database connection pool exhaustion", "confidence": "0.93" }
  ```

---

### Agent 6: Remediation Agent
- **File:** `app/workflow/nodes.py` → `remediation_agent_node()`
- **Role:** Proposes a concrete, safe remediation plan grounded in the retrieved runbook.
- **Key constraint:** Instructed to base its proposal *only* on the runbook instructions, not invent arbitrary actions. This keeps remediations consistent with organizational procedures.

---

## 7. LangGraph Workflow

LangGraph is the **orchestration backbone**. It handles:

- **State** — a shared `TypedDict` passed through every node
- **Edges** — directed connections between nodes
- **Conditional edges** — branching logic (APPROVED → execute, REJECTED → report)
- **Interrupt** — pausing the graph mid-execution awaiting human input
- **Checkpointing** — serializing the full state to PostgreSQL so it can be resumed later

### Graph Compilation

```python
graph.compile(
    checkpointer=PostgresSaver(pool),
    interrupt_before=["human_approval_checkpoint"]
)
```

This tells LangGraph to:
1. Execute all nodes up to `human_approval_checkpoint`
2. Serialize the entire workflow state to PostgreSQL
3. Stop execution and return control to FastAPI

When a human approves, the API resumes the graph by calling `graph.stream(None, config)` — LangGraph reloads the state from PostgreSQL and continues from where it stopped.

---

## 8. LangGraph State

Defined in `app/workflow/state.py` as a `TypedDict`. Every field is optional (except core identifiers) because different nodes write different parts of it at different times.

| Field | Set By | Description |
|-------|--------|-------------|
| `incident_id` | API | Links LangGraph thread to PostgreSQL row |
| `title` | API | Human-readable incident title |
| `description` | API | Natural-language incident description |
| `logs_evidence` | Log Agent | LLM summary of log tool output |
| `metrics_evidence` | Metrics Agent | LLM summary of metrics tool output |
| `db_evidence` | DB Agent | LLM summary of database tool output |
| `root_cause` | Diagnosis Agent | Determined root cause string |
| `confidence` | Diagnosis Agent | Float confidence score as string (e.g., `"0.93"`) |
| `runbook_instructions` | RAG Node | Retrieved runbook text from ChromaDB |
| `proposed_remediation` | Remediation Agent | Full remediation plan text |
| `approval_status` | Human / API | `PENDING`, `APPROVED`, or `REJECTED` |
| `executed_action` | Execute Node | Log of what action was taken |
| `verification_status` | Verify Node | `PASS` or `FAIL` |
| `final_report` | Report Node | Complete Markdown incident report |

---

## 9. RAG / Runbook Retrieval

**File:** `app/rag/retriever.py`

### Purpose
Live logs and metrics tell us *what is happening now*. Runbooks tell us *what the organization recommends doing about it*. RAG bridges the diagnosis to the prescribed procedure.

### How It Works

1. On first startup, `init_vector_store()` loads all `.md` files from `runbooks/` using LangChain's `DirectoryLoader`.
2. Documents are split by Markdown headers (`##`) using `MarkdownHeaderTextSplitter` to create meaningful per-scenario chunks.
3. Chunks are further split with `RecursiveCharacterTextSplitter` to stay within token limits.
4. Each chunk is embedded and stored in **ChromaDB** in the `chroma_db/` directory.
5. On subsequent startups, the existing ChromaDB is loaded instead of re-embedding.
6. `retrieve_runbook(query)` performs a semantic similarity search for the top 2 matching runbook sections.

### Current Runbook Coverage

| Runbook File | Scenarios Covered |
|---|---|
| `payment_api.md` | HTTP 500 spikes, high latency, rate limiting (429), gateway timeouts (504), webhook delivery failures |
| `database.md` | Connection pool exhaustion, high CPU, deadlocks and long-running transactions, disk space issues |

---

## 10. Stateful Simulated Environment & Tools

Since this is a demo system without real Datadog, Splunk, or RDS APIs, we simulate those external systems using a **stateful, mutable Python class** and LangChain `@tool` functions.

### The Simulated Environment (`app/simulation/environment.py`)
This file contains the `SimulatedEnvironment` singleton. It holds the "live" metrics of our fake production system.

**Key functions in `environment.py`:**
- `reset()`: Resets all metrics to their base broken state (18% error rate, 100% DB pool, etc.).
- `set_scenario(scenario: str)`: Configures the metrics based on the incident type (`payment_db_pool`, `gateway_timeout`, `deadlock`). This is called automatically by the `POST /api/incident` endpoint based on keywords in your incident description.
- **Execution Modifiers** (e.g., `increase_db_pool(new_size)`): These functions represent actual remediations. When called, they **mutate the state variables** (e.g., forcefully dropping `payment_api_error_rate` from 18.0 to 0.4).

### 🛠️ How to Tweak the Simulation for a Resume/Demo
If you want to show this project to a recruiter or on a portfolio, you want the **"Before & After"** impact to look incredibly dramatic. You control exactly what numbers the system sees by editing variables directly inside `app/simulation/environment.py`.

#### Step 1: Change the "Before" (The Disaster State)
When you submit a new incident, the system calls `reset()` and then `set_scenario()`. This establishes the initial broken metrics.

**Open `app/simulation/environment.py` and find `def reset(self):` (around line 13).**
Currently, it looks like this:
```python
self.payment_api_error_rate = 18.0  # 18% error rate
self.payment_api_latency = 2.8      # 2.8s latency
```
**Tweak it:** Make the outage catastrophic! Change those lines to:
```python
self.payment_api_error_rate = 85.0  # System is almost entirely down!
self.payment_api_latency = 12.5     # Requests are timing out massively!
```
*Result:* When the investigation agents run, they will detect an 85% error rate and 12.5s latency, making the incident look incredibly severe.

#### Step 2: Change the "After" (The Heroic Fix)
When you click **APPROVE**, the system calls the execution functions, which forcefully rewrite the state variables to simulate the problem being solved.

**Find `def increase_db_pool(self, new_size: int):` (around line 48).**
Currently, the fix sets the metrics to this:
```python
self.payment_api_error_rate = 0.4
self.payment_api_latency = 0.14
```
**Tweak it:** Make the fix look absolutely perfect. Change those lines to:
```python
self.payment_api_error_rate = 0.01  # Errors are basically zero
self.payment_api_latency = 0.05     # Blazing fast 50ms latency
```
*Result:* After the execution completes, the Verify Node will query the environment again. In the final Markdown report, you will get a perfect Before-and-After proof showing the system going from 85% error rate down to 0.01% purely through the AI's autonomous remediation!

---### The Dynamic Read Tools (`app/tools/simulated_systems.py`)
The investigation agents use these tools to discover what is wrong. Because they read from `environment.py`, they return dynamic, real-time data:
- `query_logs(service, time)`: Generates log strings based on the error counts currently active in the `env` object.
- `query_metrics(service, metric)`: Returns the live error rate and latency percentages from the `env` object.
- `query_database_status(db)`: Returns the live connection pool utilization from the `env` object.

### The Dynamic Execution Tools
The execution agent uses these tools to actually apply fixes. They directly call the modifier functions in `environment.py`:
- `execute_increase_db_pool(new_size)`
- `execute_restart_service(service_name)`
- `execute_failover_gateway()`
- `execute_kill_deadlocks()`

> **Replacing with real APIs:** To hook this up to your actual production infrastructure (like Datadog or Kubernetes), you would simply delete the `environment.py` logic and rewrite the functions in `simulated_systems.py` to make real HTTP requests to your provider's API. No other part of OpsPilot needs to change!

---

## 11. Database Schema

**File:** `app/database/models.py`

### `incidents` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-incremented incident identifier |
| `title` | String | Human-readable title |
| `status` | String | `INVESTIGATING` → `AWAITING_APPROVAL` → `RESOLVED` / `REJECTED` / `REMEDIATION_FAILED` |
| `severity` | String | `HIGH`, `MEDIUM`, or `LOW` |
| `description` | Text | Full natural-language incident description |
| `root_cause` | Text | Root cause determined by Diagnosis Agent |
| `confidence` | String | Confidence score (e.g., `"0.93"`) |
| `retrieved_runbook` | Text | Runbook text retrieved from ChromaDB |
| `proposed_remediation` | Text | Full remediation plan from Remediation Agent |
| `human_decision` | String | `APPROVED`, `REJECTED`, or `null` (pending) |
| `executed_action` | Text | What was actually executed |
| `verification_result` | Text | `PASS`, `FAIL`, or `null` |
| `final_report` | Text | Full Markdown incident report |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp (auto-managed) |

### `evidence` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-incremented |
| `incident_id` | Integer FK | Foreign key to `incidents.id` |
| `source` | String | `LOGS`, `METRICS`, or `DATABASE` |
| `findings` | JSON | Raw evidence payload from the agent |
| `created_at` | DateTime | When this evidence was collected |

### LangGraph Checkpointing Tables (Auto-created on startup)

LangGraph's `PostgresSaver.setup()` creates three internal tables:

| Table | Purpose |
|-------|---------|
| `checkpoints` | Stores the workflow checkpoint metadata (thread_id, timestamp, next node) |
| `checkpoint_blobs` | Stores the serialized state blobs (binary content of each state field) |
| `checkpoint_migrations` | Tracks which schema migrations have been applied |

These tables are what make it possible to **pause the workflow between HTTP requests** and resume it later after human approval.

---

## 12. API Endpoints

**Base URL:** `http://localhost:8000`  
**Auto-generated docs:** `http://localhost:8000/docs` (Swagger UI)

### `POST /api/incident`
Trigger a new incident.

**Request:**
```json
{
  "title": "Payment API Failure",
  "description": "Payment API is experiencing a large increase in HTTP 500 errors. 18% failure rate, latency at 2.8s.",
  "severity": "HIGH"
}
```
**Response:**
```json
{ "incident_id": 1, "message": "Incident created and investigation started." }
```
Starts the LangGraph workflow in a FastAPI background task and returns immediately.

---

### `GET /api/incident/{id}`
Check investigation status.

**Response includes:**
- `db_info` — the PostgreSQL row (status, root_cause, proposed_remediation, etc.)
- `graph_state` — the full live LangGraph state (all agent findings)
- `waiting_on` — which node the graph is currently paused before (e.g., `["human_approval_checkpoint"]`)

---

### `POST /api/incident/{id}/approve`
Provide human approval or rejection.

**Request:**
```json
{ "action": "APPROVE" }
```
or
```json
{ "action": "REJECT" }
```
Updates `approval_status` in the LangGraph state and resumes the workflow.

---

### `GET /api/incident/{id}/report`
Retrieve the final incident report (once the workflow has completed).

**Response:**
```json
{ "report": "# INCIDENT REPORT #1\n..." }
```

---

## 13. End-to-End Demo Flow

```
Step 1 ─ POST /api/incident
         "Payment API is experiencing large increase in HTTP 500 errors."
         → Incident #1 created, investigation starts in background

Step 2 ─ [Background: LangGraph runs]
         Planner receives incident
           ├─ Log Agent    → calls query_logs("Payment API")
           │                 → finds 45 ConnectionPoolTimeout + 120 HTTP 500 errors
           ├─ Metrics Agent → calls query_metrics("Payment API")
           │                 → finds 18% error rate, 2.8s latency
           └─ DB Agent     → calls query_database_status("primary_db")
                             → finds 20/20 connections full (100% pool utilization)

         Diagnosis Agent receives all 3 evidence sources
           → Root cause: "Database connection pool exhaustion"
           → Confidence: 93%

         RAG Node queries ChromaDB with root cause
           → Retrieves: database.md (pool exhaustion section) + payment_api.md (HTTP 500 section)

         Remediation Agent reads diagnosis + runbook
           → Proposes: "Increase DB pool from 20→40. Restart payment service."

         *** GRAPH PAUSES — state saved to PostgreSQL ***

Step 3 ─ GET /api/incident/1
         → status: "AWAITING_APPROVAL"
         → proposed_remediation: [full structured plan]
         → waiting_on: ["human_approval_checkpoint"]

Step 4 ─ POST /api/incident/1/approve  { "action": "APPROVE" }
         → approval_status updated in graph state
         → graph resumes in background

Step 5 ─ [Background: LangGraph resumes]
         Execute Node → logs the approved action
         Verify Node  → checks metrics → PASS
         Report Node  → generates full Markdown report
         PostgreSQL updated: status = "RESOLVED"

Step 6 ─ GET /api/incident/1/report
         → Full incident report with root cause, evidence, runbook, decision, RESOLVED
```

---

## 14. Human-in-the-Loop Safety

OpsPilot enforces a strict **propose-then-approve** policy:

- The LangGraph graph is compiled with `interrupt_before=["human_approval_checkpoint"]`
- No remediation code runs unless a human explicitly calls `POST /incident/{id}/approve` with `"APPROVE"`
- If rejected, the system stops and generates a report with `status: REJECTED` — nothing is changed on any system
- The `execute_remediation` node is only reachable through the `APPROVED` conditional edge

**Design principle: The LLM proposes. The human decides. The system executes.**

---

## 15. Verification Loop

After executing a remediation, OpsPilot does **not** assume success. The `verify_node` checks whether the applied fix actually resolved the incident conditions.

### Verification Logic (Demo)
The verify node checks whether key remediation keywords (`"pool"`, `"restart"`, `"increase"`) appear in the proposed remediation text. If yes, it simulates improved metrics and returns `PASS`.

### If Verification Passes (`PASS`)
- `final_status = "RESOLVED"`
- Simulated post-remediation metrics:
  - HTTP 500 error rate: 18% → 0.4%
  - DB connection pool: 100% → 55%
  - Latency: 2.8s → 140ms

### If Verification Fails (`FAIL`)
- LangGraph routes back to the `planner` node
- The system re-investigates instead of falsely declaring success
- This prevents the dangerous failure mode of: *"fix was applied, problem persists, nobody noticed"*

---

*OpsPilot v1.0 — Project explanation generated September 2026*
