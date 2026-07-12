# Runbook: Disk Space Exhaustion

## Alert Signature
- Disk utilization > 90% on any node
- Write errors in application logs
- Database refusing new writes

## Root Cause Patterns
- Log files not rotated, accumulating without limit
- Large temporary files from batch jobs not cleaned up
- Database transaction logs growing unbounded
- Core dumps filling /tmp

## Immediate Mitigation Steps
1. Identify disk hog: `du -sh /* | sort -rh | head -20`
2. Clear old log files if safe: `find /var/log -name "*.log" -mtime +7 -delete`
3. Clear temporary files: `rm -rf /tmp/*`
4. Compress or archive old database transaction logs
5. If database: truncate transaction log after confirming backups are current

## Recovery Verification
- Disk utilization should drop below 75%
- Application write errors should cease
