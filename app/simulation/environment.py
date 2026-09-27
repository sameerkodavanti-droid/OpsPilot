class SimulatedEnvironment:
    """
    A singleton class holding the mutable state of our simulated production environment.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimulatedEnvironment, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance

    def reset(self):
        """Resets the environment to the initial 'broken' state."""
        self.payment_api_error_rate = 18.0  # %
        self.payment_api_latency = 2.8      # seconds
        self.payment_api_500_count = 120
        self.payment_api_timeout_count = 45
        
        self.db_pool_max = 20
        self.db_pool_active = 20
        self.db_cpu = 45.0                  # %
        
        self.gateway_timeout_rate = 0.0     # %
        self.db_deadlocks = 0
        
        self.disk_space_used = 45.0         # %
        self.api_429_count = 0
        
        self.scenario = "payment_db_pool"   # "payment_db_pool", "gateway_timeout", "deadlock", "disk_full", "rate_limiting"

    def set_scenario(self, scenario: str):
        """Configure the environment for a specific scenario."""
        self.reset()
        self.scenario = scenario
        if scenario == "gateway_timeout":
            self.payment_api_error_rate = 12.0
            self.payment_api_latency = 5.2
            self.gateway_timeout_rate = 12.0
            self.db_pool_active = 10
            self.payment_api_500_count = 0
            self.payment_api_timeout_count = 0
        elif scenario == "deadlock":
            self.db_deadlocks = 5
            self.db_pool_active = 18
            self.payment_api_error_rate = 6.0
            self.payment_api_latency = 8.5
            self.payment_api_500_count = 0
            self.payment_api_timeout_count = 0
        elif scenario == "disk_full":
            self.disk_space_used = 99.5
            self.payment_api_error_rate = 25.0
            self.payment_api_500_count = 850
            self.payment_api_latency = 5.0
        elif scenario == "rate_limiting":
            self.api_429_count = 500
            self.payment_api_error_rate = 15.0
            self.payment_api_500_count = 0
            self.payment_api_latency = 1.5

    def increase_db_pool(self, new_size: int) -> str:
        """Remediation action: Increase database connection pool."""
        if self.scenario != "payment_db_pool":
            return f"Action executed. (No significant effect in current scenario '{self.scenario}')."
            
        old_size = self.db_pool_max
        self.db_pool_max = new_size
        # Simulate active connections spreading out and dropping if they were just queued
        self.db_pool_active = 11
        
        # This fixes the core issue
        self.payment_api_error_rate = 0.4
        self.payment_api_latency = 0.14
        self.payment_api_500_count = 2
        self.payment_api_timeout_count = 0
        
        return f"Successfully increased DB connection pool from {old_size} to {new_size}. Active connections dropped to 11. Error rate stabilized."

    def restart_service(self, service_name: str) -> str:
        """Remediation action: Restart a service."""
        service = service_name.lower()
        if "payment" in service and self.scenario == "payment_db_pool":
            self.db_pool_active = max(0, self.db_pool_active - 5)
            return f"Successfully restarted {service_name}. Hung connections flushed."
        return f"Restarted {service_name}."
        
    def failover_gateway(self) -> str:
        """Remediation action: Failover to secondary gateway."""
        if self.scenario == "gateway_timeout":
            self.gateway_timeout_rate = 0.0
            self.payment_api_error_rate = 0.1
            self.payment_api_latency = 0.2
            return "Failed over to secondary payment gateway. Timeout rate dropped to 0%."
        return "Failover executed, but no primary gateway issue was detected."
        
    def kill_deadlocks(self) -> str:
        """Remediation action: Kill blocking PIDs."""
        if self.scenario == "deadlock":
            self.db_deadlocks = 0
            self.payment_api_error_rate = 0.5
            self.payment_api_latency = 0.3
            self.db_pool_active = 12
            return "Killed blocking transactions. Deadlocks resolved, latency returned to normal."
        return "No deadlocks found to kill."

    def clear_temp_logs(self) -> str:
        """Remediation action: Clear temporary log files."""
        if self.scenario == "disk_full":
            self.disk_space_used = 45.0
            self.payment_api_error_rate = 0.1
            self.payment_api_500_count = 0
            self.payment_api_latency = 0.12
            return "Cleared /var/log and /tmp directories. Disk space usage dropped to 45%."
        return "Cleared temp logs, but disk was not full."

    def increase_rate_limit(self, new_limit: int) -> str:
        """Remediation action: Increase API Gateway rate limit."""
        if self.scenario == "rate_limiting":
            self.api_429_count = 0
            self.payment_api_error_rate = 0.1
            self.payment_api_latency = 0.12
            return f"Increased rate limit to {new_limit} req/s. 429 Too Many Requests errors stopped."
        return f"Rate limit increased to {new_limit} req/s."

# Global instance
env = SimulatedEnvironment()
