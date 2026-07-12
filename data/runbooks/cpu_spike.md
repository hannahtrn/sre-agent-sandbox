# Runbook: CPU Spike / High CPU Utilization

## Alert Signature
- CPU utilization > 90% sustained for more than 5 minutes
- Response times increasing alongside CPU
- Service: any

## Root Cause Patterns
- Inefficient algorithm processing large input (O(n²) behavior)
- Infinite loop or tight retry loop without backoff
- Cryptography operations at unexpected scale
- Compression/decompression on every request instead of cached

## Immediate Mitigation Steps
1. Identify CPU-consuming process: `top -c` or container CPU metrics
2. Profile the hot path: attach profiler or check flame graphs if available
3. If tight retry loop: check error logs for the root cause being retried
4. If traffic spike: rate limit or shed load upstream temporarily
5. If single bad request: kill the process and identify the offending input

## Recovery Verification
- CPU should return below 60% within 2 minutes of fix
- Verify no cascading failures from requests that timed out during spike
