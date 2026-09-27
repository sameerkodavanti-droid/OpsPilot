# Infrastructure Runbook

## 1. Disk Space Full (100% Usage)
If disk space usage reaches 99% or 100% on a node or container:
1. Identify which directories are consuming the most space. Usually, this is `/var/log` or `/tmp`.
2. Check for orphaned containers or dangling images taking up Docker space.
3. If logs are the culprit and log rotation failed, clear the temporary log files to immediately restore service.
4. Set up an alert for 85% disk usage to prevent future full-disk outages.
5. If persistent storage is full, increase the EBS volume size or PVC (Persistent Volume Claim).

## 2. Kubernetes Pod Evictions
If pods are being evicted due to Node Pressure:
1. Check the node metrics for memory or disk pressure.
2. If memory pressure, verify pod memory limits and requests. A pod without limits may consume the entire node.
3. Cordon the affected node to prevent new pods from scheduling on it until it recovers.

## 3. High CPU Utilization on Worker Nodes
If worker node CPU is consistently above 90%:
1. Scale out the cluster by adding more worker nodes to the autoscaling group.
2. Check if a specific background job (e.g., video processing) is hogging resources and move it to a dedicated node pool.
