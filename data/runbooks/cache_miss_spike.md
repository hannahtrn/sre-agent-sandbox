# Runbook: Cache Miss Spike / Cache Invalidation

## Alert Signature
- Latency spike on read-heavy endpoints
- Database CPU suddenly elevated
- Cache hit rate drops below 50%
- Often follows a deployment or cache flush

## Root Cause Patterns
- Cache cleared or flushed during deployment
- Cache TTL set too short
- New cache key format introduced, invalidating existing entries
- Redis instance restarted or failover occurred

## Immediate Mitigation Steps
1. Check cache hit rate in metrics dashboard
2. Verify Redis connectivity and memory usage
3. If cache was recently cleared: allow warm-up period (10-15 minutes)
4. Temporarily increase cache TTL if appropriate
5. If Redis is down: check Redis container health and restart if needed

## Recovery Verification
- Cache hit rate should recover to > 80% within 15 minutes naturally
- Database CPU should return to baseline as cache warms up
