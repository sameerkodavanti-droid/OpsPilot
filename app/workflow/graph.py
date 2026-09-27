from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from app.workflow.state import IncidentState
from app.workflow.nodes import (
    planner_node,
    log_agent_node,
    metrics_agent_node,
    db_agent_node,
    diagnosis_agent_node,
    rag_node,
    remediation_agent_node,
    execute_remediation_node,
    verify_node,
    report_node
)

def route_after_planner(state: IncidentState):
    # Route to all three parallel agents
    return ["log_agent", "metrics_agent", "db_agent"]

def route_after_approval(state: IncidentState):
    status = state.get("approval_status")
    if status == "APPROVED":
        return "execute_remediation"
    else:
        return "report"

def route_after_verify(state: IncidentState):
    status = state.get("verification_status")
    if status == "PASS":
        return "report"
    else:
        # Re-investigate if failed
        return "planner"

def build_graph():
    builder = StateGraph(IncidentState)
    
    # Add nodes
    builder.add_node("planner", planner_node)
    builder.add_node("log_agent", log_agent_node)
    builder.add_node("metrics_agent", metrics_agent_node)
    builder.add_node("db_agent", db_agent_node)
    builder.add_node("diagnosis", diagnosis_agent_node)
    builder.add_node("rag", rag_node)
    builder.add_node("remediation", remediation_agent_node)
    builder.add_node("human_approval_checkpoint", lambda state: state) # Dummy node to interrupt before
    builder.add_node("execute_remediation", execute_remediation_node)
    builder.add_node("verify", verify_node)
    builder.add_node("report", report_node)
    
    # Add edges
    builder.add_edge(START, "planner")
    
    # Planner -> Parallel Agents
    builder.add_conditional_edges(
        "planner", 
        route_after_planner, 
        ["log_agent", "metrics_agent", "db_agent"]
    )
    
    # Parallel Agents -> Diagnosis
    builder.add_edge("log_agent", "diagnosis")
    builder.add_edge("metrics_agent", "diagnosis")
    builder.add_edge("db_agent", "diagnosis")
    
    builder.add_edge("diagnosis", "rag")
    builder.add_edge("rag", "remediation")
    builder.add_edge("remediation", "human_approval_checkpoint")
    
    # Conditional route based on human approval
    builder.add_conditional_edges(
        "human_approval_checkpoint", 
        route_after_approval, 
        ["execute_remediation", "report"]
    )
    
    builder.add_edge("execute_remediation", "verify")
    
    # Conditional route based on verification
    builder.add_conditional_edges(
        "verify", 
        route_after_verify, 
        ["planner", "report"]
    )
    
    builder.add_edge("report", END)
    
    return builder

graph_builder = build_graph()

def get_compiled_graph(pool: ConnectionPool = None):
    """
    Returns the compiled graph. 
    If pool is provided, attaches Postgres checkpointer.
    interrupt_before pauses execution before the human_approval_checkpoint.
    """
    if pool:
        checkpointer = PostgresSaver(pool)
        return graph_builder.compile(
            checkpointer=checkpointer,
            interrupt_before=["human_approval_checkpoint"]
        )
    return graph_builder.compile(interrupt_before=["human_approval_checkpoint"])
