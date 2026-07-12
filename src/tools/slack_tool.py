import httpx
from config import config


def post_to_slack(message: str) -> bool:
    """
    Post to Slack via webhook. If no webhook URL is configured,
    prints to console (mock mode — useful for local dev and demos).
    """
    if not config.SLACK_WEBHOOK_URL:
        print("\n" + "=" * 60)
        print("MOCK SLACK MESSAGE:")
        print("=" * 60)
        print(message)
        print("=" * 60 + "\n")
        return True

    try:
        response = httpx.post(
            config.SLACK_WEBHOOK_URL,
            json={"text": message},
            timeout=10.0,
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Slack post failed: {e}")
        return False


def format_incident_brief(state: dict) -> str:
    """Format a structured Slack incident brief from agent state."""
    alert      = state.get("alert", {})
    suspicious = state.get("suspicious_commits", [])
    runbook    = state.get("runbook_title", "No specific runbook found")
    impact     = state.get("impact_summary", "Impact unknown")
    severity   = state.get("severity", "unknown").upper()

    if suspicious:
        commit_lines = []
        for c in suspicious:
            confidence = f"{c.get('confidence', 0):.0%}" if c.get("confidence") else ""
            commit_lines.append(
                f"• `{c['hash']}` by {c['author']} "
                f"{'(confidence: ' + confidence + ')' if confidence else ''}\n"
                f"  _{c['message']}_\n"
                f"  {c.get('reason', c.get('diff_summary', ''))}"
            )
        commits_section = "\n".join(commit_lines)
    else:
        commits_section = "• No suspicious commits identified in recent history"

    return f"""*INCIDENT ALERT — {severity}*

*Service:* `{state.get('service_name', 'unknown')}`
*Error Type:* {state.get('error_type', 'unknown')}
*Detected:* {state.get('alert_timestamp', 'unknown')}

---

*Impact Assessment*
{impact}

---

*Likely Root Cause (AI Analysis)*
{commits_section}

---

*Recommended Runbook*
{runbook}

---

*Immediate Actions*
1. Review the commits listed above
2. Follow runbook: {runbook}
3. Update incident status in #incidents channel
4. Page secondary on-call if not resolved in 15 minutes

_This brief was generated automatically by the SRE Agent._"""
