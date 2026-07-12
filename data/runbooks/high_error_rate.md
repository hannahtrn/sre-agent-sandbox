# Runbook: High HTTP 500 Error Rate

## Alert Signature
- HTTP 500 error rate > 5% on any endpoint
- Sudden spike from baseline (not gradual increase)
- Service: any

## Root Cause Patterns
- Recent code deployment with unhandled exceptions
- Dependency service returning unexpected response format
- Configuration change causing runtime errors
- Database query returning unexpected null values

## Immediate Mitigation Steps
1. Check recent deployments: review git log for last 2 hours on affected service
2. Check dependency health: ping downstream services manually
3. Review error logs for stack traces — identify the exact exception type
4. If recent deployment is suspect: initiate rollback procedure
5. Enable debug logging temporarily to capture full exception context

## Rollback Procedure
1. Identify the last known good commit hash
2. `git revert [bad_commit_hash]` or deploy previous artifact
3. Verify error rate drops after rollback completes

## Recovery Verification
- Error rate should return to < 1% within 5 minutes of rollback
- Run smoke tests on affected endpoints manually
