# Runbook: Memory Leak / OOM

## Alert Signature
- Memory utilization trending upward over time (not a spike)
- Process restarts increasing
- Response times degrading gradually
- OOM killer logs in system journal

## Root Cause Patterns
- Unbounded cache growth without eviction policy
- Event listener or callback accumulation without cleanup
- Large objects held in request scope beyond request lifetime
- Worker thread count increased without memory limits

## Immediate Mitigation Steps
1. Identify memory-consuming processes: `top` or check container metrics
2. If single process: restart that specific worker
3. If widespread: rolling restart of service instances
4. Temporarily reduce worker thread count if recently increased
5. Enable memory profiling on one instance to capture heap snapshot

## Recovery Verification
- Memory utilization should stabilize or decrease after restart
- Monitor for recurrence — if it returns within an hour, leak is still active
