# Runbook: Database Connection Pool Exhaustion

## Alert Signature
- High error rate on database-dependent endpoints
- Errors: "too many connections", "connection timeout", "pool exhausted"
- Service: any service with database dependency

## Root Cause Patterns
- Connection pool size reduced below required concurrency level
- Long-running transactions holding connections open
- Connection leak — connections opened but never returned to pool
- Traffic spike exceeding pool capacity

## Immediate Mitigation Steps
1. Check current pool size: `SHOW STATUS LIKE 'Threads_connected'`
2. Identify long-running queries: `SELECT * FROM information_schema.processlist WHERE time > 30`
3. Kill blocking queries if safe: `KILL QUERY [process_id]`
4. Temporarily increase pool size in config if possible without restart
5. If restart required: coordinate with on-call for maintenance window

## Recovery Verification
- Monitor error rate — should drop within 2 minutes of pool size increase
- Confirm connection count returns to baseline in Grafana dashboard

## Post-Incident
- Review recent config changes to connection pool settings
- Add alerting on pool utilization > 80%
- Consider connection pooling middleware (PgBouncer) for future resilience
