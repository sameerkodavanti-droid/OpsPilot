import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from app.workflow.state import IncidentState
from app.rag.retriever import retrieve_runbook
from app.config import settings
from app.tools.simulated_systems import (
    query_logs, query_metrics, query_database_status,
    execute_increase_db_pool, execute_restart_service,
    execute_failover_gateway, execute_kill_deadlocks,
    execute_clear_temp_logs, execute_increase_rate_limit
)
from app.simulation.environment import env

# Initialize LLM — using Groq with the open-source Mixtral model
llm = ChatGroq(temperature=0, model="openai/gpt-oss-120b", api_key=settings.GROQ_API_KEY)

def _run_single_tool_agent(task_description: str, tools: list) -> str:
    """Helper to run a basic LLM loop that calls tools and summarizes."""
    llm_with_tools = llm.bind_tools(tools)
    res = llm_with_tools.invoke([HumanMessage(content=task_description)])
    
    if not res.tool_calls:
        return res.content
        
    tool_results = []
    tool_map = {t.name: t for t in tools}
    
    for tool_call in res.tool_calls:
        tool_func = tool_map.get(tool_call["name"])
        if tool_func:
            try:
                output = tool_func.invoke(tool_call["args"])
                tool_results.append(f"Result from {tool_call['name']}:\n{output}")
            except Exception as e:
                tool_results.append(f"Error calling {tool_call['name']}: {str(e)}")
                
    final_prompt = (
        task_description + 
        "\n\nHere are the results from your tool calls:\n" + 
        "\n\n".join(tool_results) + 
        "\n\nPlease concisely summarize the evidence you found."
    )
    final_res = llm.invoke([HumanMessage(content=final_prompt)])
    return final_res.content

def planner_node(state: IncidentState) -> IncidentState:
    """Decides what to do next based on incident description."""
    return {}

def log_agent_node(state: IncidentState) -> IncidentState:
    """Uses LLM and query_logs tool to investigate."""
    prompt = f"Investigate logs for the following incident: {state.get('description')}\nDetermine which service to query and fetch the logs using your tool."
    evidence = _run_single_tool_agent(prompt, [query_logs])
    return {"logs_evidence": evidence}

def metrics_agent_node(state: IncidentState) -> IncidentState:
    """Uses LLM and query_metrics tool to investigate."""
    prompt = f"Investigate metrics for the following incident: {state.get('description')}\nDetermine which service and metrics to query using your tool."
    evidence = _run_single_tool_agent(prompt, [query_metrics])
    return {"metrics_evidence": evidence}

def db_agent_node(state: IncidentState) -> IncidentState:
    """Uses LLM and query_database_status tool to investigate."""
    prompt = f"Investigate database status for the following incident: {state.get('description')}\nQuery the relevant database instance using your tool."
    evidence = _run_single_tool_agent(prompt, [query_database_status])
    return {"db_evidence": evidence}

def diagnosis_agent_node(state: IncidentState) -> IncidentState:
    """Correlates evidence and determines root cause."""
    prompt = ChatPromptTemplate.from_template(
        "You are an expert SRE Diagnosis Agent.\n"
        "Incident Description: {description}\n"
        "Logs: {logs}\n"
        "Metrics: {metrics}\n"
        "Database: {db}\n\n"
        "Diagnose the root cause and provide a confidence score.\n"
        "Output ONLY valid JSON with keys 'root_cause' and 'confidence'. No markdown blocks."
    )
    chain = prompt | llm
    res = chain.invoke({
        "description": state.get("description", ""),
        "logs": state.get("logs_evidence", ""),
        "metrics": state.get("metrics_evidence", ""),
        "db": state.get("db_evidence", "")
    })
    
    try:
        text_content = res.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(text_content)
        return {"root_cause": data.get("root_cause", "Unknown"), "confidence": str(data.get("confidence", "0%"))}
    except Exception as e:
        return {"root_cause": res.content, "confidence": "Unknown"}

def rag_node(state: IncidentState) -> IncidentState:
    """Retrieves runbook instructions based on the root cause."""
    root_cause = state.get("root_cause", "")
    runbook_data = retrieve_runbook(root_cause)
    return {"runbook_instructions": runbook_data}

def remediation_agent_node(state: IncidentState) -> IncidentState:
    """Proposes a remediation plan based on runbooks."""
    prompt = ChatPromptTemplate.from_template(
        "You are a Remediation Agent.\n"
        "Incident: {description}\n"
        "Diagnosis: {diagnosis}\n"
        "Runbook Instructions:\n{runbook}\n\n"
        "Generate a concise, human-readable incident remediation plan based ONLY on the runbook instructions.\n\n"
        "Follow these rules strictly:\n"
        "- Use short paragraphs and numbered steps.\n"
        "- Prefer bullet points over tables.\n"
        "- Do not repeat the same information.\n"
        "- Keep each action concise and actionable.\n"
        "- Use Markdown headings only when they improve readability.\n"
        "- Use code blocks only for actual commands.\n"
        "- Clearly separate into these four sections:\n"
        "  1. Root Cause\n"
        "  2. Recommended Actions\n"
        "  3. Verification / Success Criteria\n"
        "  4. Rollback or Next Steps\n"
        "- Do not use emojis.\n"
        "- Do not write lengthy Why / Expected Outcome explanations.\n"
        "- Preserve important technical details such as thresholds, connection-pool sizes, error rates, and monitoring conditions.\n\n"
        "Return only the remediation plan."
    )
    chain = prompt | llm
    res = chain.invoke({
        "description": state.get("description", ""),
        "diagnosis": state.get("root_cause", ""),
        "runbook": state.get("runbook_instructions", "")
    })
    return {"proposed_remediation": res.content, "approval_status": "PENDING"}

def execute_remediation_node(state: IncidentState) -> IncidentState:
    """Executes the action if approved."""
    proposed = state.get("proposed_remediation", "")
    
    prompt = ChatPromptTemplate.from_template(
        "You are an Execution Agent.\n"
        "Here is the approved remediation plan:\n{plan}\n\n"
        "Call the appropriate execute tools to apply this remediation."
    )
    execute_tools = [
        execute_increase_db_pool, execute_restart_service, 
        execute_failover_gateway, execute_kill_deadlocks,
        execute_clear_temp_logs, execute_increase_rate_limit
    ]
    
    llm_with_tools = llm.bind_tools(execute_tools)
    res = llm_with_tools.invoke([HumanMessage(content=prompt.format(plan=proposed))])
    
    actions = []
    if res.tool_calls:
        tool_map = {t.name: t for t in execute_tools}
        for tool_call in res.tool_calls:
            tool_func = tool_map.get(tool_call["name"])
            if tool_func:
                try:
                    output = tool_func.invoke(tool_call["args"])
                    actions.append(f"Called {tool_call['name']}: {output}")
                except Exception as e:
                    actions.append(f"Error calling {tool_call['name']}: {str(e)}")
                    
    action_text = "\n".join(actions) if actions else "No tools were called by the execution agent."
    return {"executed_action": f"Executed Actions:\n{action_text}"}

def verify_node(state: IncidentState) -> IncidentState:
    """Simulates verifying if the metrics improved."""
    # Re-query metrics from environment to check if conditions improved
    status = "FAIL"
    if env.payment_api_error_rate < 1.0 and (env.db_pool_active / max(1, env.db_pool_max)) < 0.8:
        status = "PASS"
    elif env.gateway_timeout_rate < 1.0 and env.payment_api_error_rate < 1.0:
        status = "PASS"
    elif env.db_deadlocks == 0 and env.payment_api_error_rate < 1.0:
        status = "PASS"
    elif env.disk_space_used < 80.0:
        status = "PASS"
    elif env.api_429_count == 0 and env.payment_api_error_rate < 1.0:
        status = "PASS"
        
    return {"verification_status": status}

def report_node(state: IncidentState) -> IncidentState:
    """Generates the final incident report."""
    final_status = "INVESTIGATING"
    
    # Generate Post-Remediation Metrics for the report
    post_metrics = "Not checked"
    if state.get("approval_status") == "APPROVED":
        post_metrics = (
            f"- **Error Rate**: {env.payment_api_error_rate}%\n"
            f"- **Latency**: {env.payment_api_latency}s\n"
            f"- **DB Pool Active**: {env.db_pool_active}/{env.db_pool_max}\n"
            f"- **Deadlocks**: {env.db_deadlocks}\n"
            f"- **HTTP 429 Errors**: {env.api_429_count}\n"
            f"- **Disk Space**: {env.disk_space_used}%"
        )
        
    if state.get("verification_status") == "PASS":
        final_status = "RESOLVED"
    elif state.get("approval_status") == "REJECTED":
        final_status = "REJECTED"
    elif state.get("verification_status") == "FAIL":
        final_status = "REMEDIATION FAILED"
        
    report = f"""# INCIDENT REPORT #{state.get("incident_id", "Unknown")}

**Title:** {state.get("title", "N/A")}
**Problem:** {state.get("description", "N/A")}
**Root Cause:** {state.get("root_cause", "N/A")} (Confidence: {state.get("confidence", "N/A")})

**Evidence:**
- Logs: {state.get("logs_evidence", "N/A")}
- Metrics: {state.get("metrics_evidence", "N/A")}
- Database: {state.get("db_evidence", "N/A")}

**Retrieved Runbook:** 
{state.get("runbook_instructions", "N/A")}

**Recommended Remediation:** 
{state.get("proposed_remediation", "N/A")}

**Human Decision:** {state.get("approval_status", "N/A")}
**Executed Actions:**
{state.get("executed_action", "None")}

**Post-Remediation Verification:** 
Status: {state.get("verification_status", "N/A")}

Current System Metrics:
{post_metrics}

**Final Status:** {final_status}
"""
    return {"final_report": report.strip()}
