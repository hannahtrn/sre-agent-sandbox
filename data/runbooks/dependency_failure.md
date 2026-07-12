# Runbook: External Dependency Failure

## Alert Signature
- Errors referencing external service (payment provider, email service, etc.)
- Timeout errors on outbound HTTP calls
- Partial functionality — some features work, others fail

## Root Cause Patterns
- Third-party service outage or degradation
- API key expired or rotated without updating config
- Network partition between services
- SSL certificate expired on dependency endpoint

## Immediate Mitigation Steps
1. Check dependency status page for reported incidents
2. Test dependency manually: `curl -v [dependency_url]`
3. Check API key validity and expiration date
4. If dependency is down: activate fallback/graceful degradation mode
5. Notify users via status page if impact is customer-facing

## Recovery Verification
- Errors should cease when dependency recovers
- Verify fallback mode is working if dependency remains down
- Resume normal operations only after dependency is confirmed stable
