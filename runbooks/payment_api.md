# Payment API Runbook

## 1. HTTP 500 Error Spikes
If the HTTP 500 error rate spikes above 1%:
1. Check application logs for database connection issues or unhandled exceptions.
2. Check external payment gateway status pages (e.g., Stripe, PayPal).
3. If database connection timeouts are occurring, refer to the Database Runbook for connection pool exhaustion.
4. If the payment gateway is down, engage the third-party provider and communicate status to customers.
5. If traffic caused exhaustion, auto-scale the service by increasing the replica count by 2.

## 2. High Latency / Slow Responses
If the 95th percentile response time (p95 latency) exceeds 2 seconds:
1. Check if the downstream payment gateway is experiencing latency.
2. Verify database query performance. Are there locks or slow queries?
3. Check CPU/Memory utilization of the Payment API pods/containers.
4. If CPU is bottlenecking, vertically scale the API instances or increase pod limits.
5. If dependent services are slow, temporarily increase request timeout configurations from 3s to 5s to prevent dropped carts.

## 3. Rate Limiting (HTTP 429 Too Many Requests)
If clients are receiving HTTP 429 errors from the Payment API:
1. Investigate the source IP addresses. Is this a legitimate traffic spike or a DDoS attack?
2. If legitimate traffic (e.g., flash sale), temporarily increase the API Gateway rate limit from 100 req/s to 500 req/s per client.
3. If malicious, block the offending IP ranges at the WAF (Web Application Firewall) level.

## 4. Payment Gateway Timeouts (HTTP 504)
If the Payment API is returning HTTP 504 Gateway Timeouts when calling external providers:
1. Immediately check the external provider's status page.
2. If the provider is confirmed down, failover to the secondary payment provider (e.g., switch traffic from Stripe to Braintree).
3. Ensure circuit breakers are opening correctly so internal resources are not exhausted waiting for the third-party.

## 5. Webhook Delivery Failures
If asynchronous payment confirmation webhooks are failing:
1. Check the webhook consumer queue (e.g., RabbitMQ, SQS). Is it backed up?
2. Check the consumer logs for parsing errors or invalid payloads.
3. If the consumer service is overwhelmed, scale up the webhook consumer workers.
4. If failed, trigger the DLQ (Dead Letter Queue) redrive script to process missed webhooks once the consumer is stable.
