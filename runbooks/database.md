# Database Runbook

## 1. Database Connection Pool Exhaustion
If DB connection pool utilization exceeds 90%:
1. Inspect active connections and look for idle-in-transaction connections.
2. Check for connection leaks in the application code.
3. If legitimate traffic caused exhaustion, increase the pool according to service limits (e.g., increase from 20 to 40).
4. Restart the dependent service if required to flush hung connections.
5. Monitor error rate after remediation. Roll back or re-investigate if the problem persists.

## 2. High CPU Utilization
If query CPU utilization is consistently above 85%:
1. Identify slow or sequential scanning queries using `pg_stat_statements`.
2. Check if a recent deployment introduced unoptimized queries.
3. Verify if indexes are missing or corrupted.
4. If an expensive reporting query is running on the primary database, immediately kill the query (e.g., using `pg_cancel_backend()`).
5. Route reporting workloads to read-replicas.

## 3. Long-Running Transactions and Deadlocks
If you receive alerts for deadlocks or transactions running longer than 5 minutes:
1. Query `pg_locks` and `pg_stat_activity` to find the blocking PIDs.
2. If a batch job is blocking live traffic, terminate the batch job PID.
3. Identify the microservice responsible for the lock and notify the relevant team.
4. Consider adjusting `statement_timeout` at the application level to prevent future long-running holds.

## 4. Disk Space Approaching 100%
If the primary database storage exceeds 85% utilization:
1. Immediately check for runaway log tables or bloated audit tables.
2. If logs are bloated, perform a targeted `TRUNCATE` or `DELETE` on old rows, followed by a `VACUUM`.
3. If storage increase is legitimate data growth, proactively scale the disk size via the cloud provider console. Add at least 100GB or 20% additional capacity.
4. Ensure continuous archiving (e.g., WAL archiving) is working and not accumulating on the primary disk.
