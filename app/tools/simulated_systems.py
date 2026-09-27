from langchain_core.tools import tool
from app.simulation.environment import env

@tool
def query_logs(service_name: str, time_range: str = "last_5_minutes") -> str:
    """
    Query application logs for a specific service.
    
    Args:
        service_name: Name of the service to query (e.g., 'Payment API', 'Auth Service').
        time_range: The time range to query logs for.
        
    Returns:
        A string containing a summary of recent log entries or specific error counts.
    """
    service = service_name.lower()
    
    if "payment" in service:
        logs = f"Logs for {service_name} over {time_range}:\n"
        if env.payment_api_timeout_count > 0:
            logs += f"- [ERROR] ConnectionPoolTimeout: Unable to acquire database connection (Count: {env.payment_api_timeout_count})\n"
        if env.payment_api_500_count > 0:
            logs += f"- [ERROR] Request failed with status 500 (Count: {env.payment_api_500_count})\n"
        if env.gateway_timeout_rate > 0:
            logs += f"- [ERROR] GatewayTimeout: Upstream payment processor did not respond in time (Count: {int(env.gateway_timeout_rate * 10)})\n"
        if env.db_deadlocks > 0:
            logs += f"- [ERROR] Deadlock detected: Process waiting for lock on transaction (Count: {env.db_deadlocks})\n"
        if env.api_429_count > 0:
            logs += f"- [WARN] HTTP 429 Too Many Requests: Rate limit exceeded (Count: {env.api_429_count})\n"
            
        logs += f"- [INFO] Processed successful transaction (Count: 843)"
        return logs
    elif "infrastructure" in service or "system" in service:
        logs = f"Logs for {service_name} over {time_range}:\n"
        if env.disk_space_used > 90:
            logs += f"- [CRITICAL] No space left on device: /var/log is full (Count: 150)\n"
        logs += "- [INFO] System heartbeat OK"
        return logs
    elif "auth" in service:
        return f"Logs for {service_name} over {time_range}:\n- [INFO] Token issued (Count: 4500)\n- No significant errors."
    else:
        return f"Logs for {service_name} over {time_range}:\n- No abnormal logs detected. System operating normally."

@tool
def query_metrics(service_name: str, metric_name: str = "all") -> str:
    """
    Query system or application metrics for a service (e.g., error rate, latency, CPU).
    
    Args:
        service_name: Name of the service to query.
        metric_name: Specific metric to query ('error_rate', 'latency', 'cpu', or 'all').
        
    Returns:
        A string containing the queried metric values.
    """
    service = service_name.lower()
    
    if "payment" in service:
        if metric_name == "error_rate":
            return f"HTTP 500 error rate: {env.payment_api_error_rate}%."
        elif metric_name == "latency":
            return f"p95 Latency: {env.payment_api_latency}s (Normal is ~0.12s)."
        elif metric_name == "rate_limit":
            return f"HTTP 429 Errors: {env.api_429_count}"
        else:
            return f"HTTP 500 error rate: {env.payment_api_error_rate}% | p95 Latency: {env.payment_api_latency}s | HTTP 429 Count: {env.api_429_count} | CPU: 45%"
    elif "infrastructure" in service or "system" in service or "node" in service:
        if metric_name == "disk":
            return f"Disk Space Used: {env.disk_space_used}%"
        return f"Disk Space Used: {env.disk_space_used}% | CPU: 30% | Memory: 45%"
    else:
        return f"Metrics for {service_name}: Error rate < 0.1%, Latency < 50ms, CPU normal."

@tool
def query_database_status(db_name: str = "primary_db") -> str:
    """
    Query the status and metrics of a database instance.
    
    Args:
        db_name: Name of the database to query.
        
    Returns:
        A string detailing connection pool status, active connections, and CPU.
    """
    if "primary" in db_name.lower() or "payment" in db_name.lower():
        utilization = (env.db_pool_active / env.db_pool_max) * 100
        return (
            f"Status for {db_name}:\n"
            f"- Connection pool utilization: {utilization:.1f}%\n"
            f"- Active connections: {env.db_pool_active}/{env.db_pool_max}\n"
            f"- Deadlocks detected: {env.db_deadlocks}\n"
            f"- CPU Utilization: {env.db_cpu}%"
        )
    else:
        return f"Status for {db_name}:\n- Connection pool utilization: 15%\n- Active connections: 5/100\n- CPU Utilization: 10%"

@tool
def execute_increase_db_pool(new_size: int) -> str:
    """
    Execute action: Increase the database connection pool size.
    
    Args:
        new_size: The new maximum size of the connection pool.
    """
    return env.increase_db_pool(new_size)

@tool
def execute_restart_service(service_name: str) -> str:
    """
    Execute action: Restart a given service.
    
    Args:
        service_name: The name of the service to restart.
    """
    return env.restart_service(service_name)
    
@tool
def execute_failover_gateway() -> str:
    """
    Execute action: Failover to the secondary payment gateway.
    """
    return env.failover_gateway()
    
@tool
def execute_kill_deadlocks() -> str:
    """
    Execute action: Kill blocking PIDs to resolve database deadlocks.
    """
    return env.kill_deadlocks()

@tool
def execute_clear_temp_logs() -> str:
    """
    Execute action: Clear temporary log files and free disk space.
    """
    return env.clear_temp_logs()

@tool
def execute_increase_rate_limit(new_limit: int) -> str:
    """
    Execute action: Temporarily increase API Gateway rate limit.
    
    Args:
        new_limit: The new req/s limit.
    """
    return env.increase_rate_limit(new_limit)
