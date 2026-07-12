# Runbook: Slow Response Times / High Latency

## Alert Signature
- P99 latency exceeding 2000ms on any endpoint
- Gradual degradation over 10-30 minute window
- Service: any

## Root Cause Patterns
- Downstream dependency slow or timing out
- Database query missing index or full table scan
- Increased traffic without horizontal scaling
- Synchronous blocking calls in async code paths

## Immediate Mitigation Steps
1. Check downstream dependency latency — is the slowness external?
2. Run EXPLAIN ANALYZE on the top slow queries in the database
3. Check thread pool saturation and queue depth
4. If traffic spike: trigger horizontal scaling or increase rate limiting upstream
5. Add circuit breaker if dependency is consistently slow

## Recovery Verification
- Latency should return to P99 < 500ms within 5 minutes of fix
- Monitor downstream dependency independently to confirm recovery
