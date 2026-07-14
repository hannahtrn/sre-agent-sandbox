from openai import OpenAI
from src.agent.state import SREAgentState
from src.tools.git_tool import (
    get_recent_commits,
    analyze_commits_with_llm,
    identify_suspicious_commits,
)
from src.tools.runbook_tool import search_runbooks
from src.tools.impact_tool import estimate_impact
from src.tools.slack_tool import post_to_slack, format_incident_brief
from config import config

llm_client = OpenAI(api_key=config.OPENAI_API_KEY)


def parse_alert(state: SREAgentState) -> dict:
    """
    Node 1: validate and parse the incoming alert payload.
    Extracts service name, error type, severity, and timestamp.
    """
    alert = state["alert"]
    print(f"[parse_alert] Processing: {alert.get('incident_type')} on {alert.get('service')}")

    return {
        "service_name":    alert.get("service", "unknown"),
        "error_type":      alert.get("incident_type", "unknown"),
        "severity":        alert.get("severity", "high"),
        "alert_timestamp": alert.get("timestamp", "2026-07-11T18:30:00Z"),
        "status":          "investigating",
        "steps_completed": ["parse_alert"],   # reducer will append this
    }


def search_git_logs(state: SREAgentState) -> dict:
    """
    Node 2: find recent commits on the affected service and use the LLM
    to reason about which ones are likely root causes.

    Two key design decisions here:
    1. Temporal fix — anchors to alert_timestamp, not datetime.now()
    2. LLM analysis — no hardcoded boolean flags, genuine AI reasoning
    """
    print(f"[search_git_logs] Searching git history for: {state['service_name']}")

    try:
        commits = get_recent_commits(
            service_name=state["service_name"] or "unknown",
            alert_timestamp=state["alert_timestamp"],   # temporal fix # type: ignore
            hours_back=2,
        )

        print(f"[search_git_logs] Found {len(commits)} recent commits")

        if not commits:
            return {
                "recent_commits":     [],
                "suspicious_commits": [],
                "steps_completed":    ["search_git_logs"],
            }

        # LLM analyzes each commit against the alert signature
        alert_desc = (
            f"{state['error_type']} on {state['service_name']}. "
            f"Severity: {state['severity']}. "
            f"{state['alert'].get('description', '')}"
        )

        print(f"[search_git_logs] Running LLM analysis on {len(commits)} commits...")
        analyzed   = analyze_commits_with_llm(alert_desc, commits)
        suspicious = identify_suspicious_commits(analyzed)

        print(f"[search_git_logs] LLM flagged {len(suspicious)} suspicious commits")

        return {
            "recent_commits":     analyzed,
            "suspicious_commits": suspicious,
            "steps_completed":    ["search_git_logs"],
        }

    except Exception as e:
        print(f"[search_git_logs] Error: {e}")
        return {
            "error":              f"Git log search failed: {str(e)}",
            "recent_commits":     [],
            "suspicious_commits": [],
            "steps_completed":    ["search_git_logs"],
        }


def search_runbooks_node(state: SREAgentState) -> dict:
    """
    Node 3: build a search query from the alert and find the most
    relevant runbook in ChromaDB.
    """
    print(f"[search_runbooks] Searching for: {state['error_type']}")

    search_query = (
        f"{state['error_type']} on {state['service_name']}. "
        f"Severity: {state['severity']}."
    )

    result = search_runbooks(search_query)

    if result:
        print(f"[search_runbooks] Found: {result['title']}")
        return {
            "relevant_runbook": result["content"],
            "runbook_title":    result["title"],
            "steps_completed":  ["search_runbooks"],
        }
    else:
        print("[search_runbooks] No specific runbook found — using generic playbook")
        return {
            "relevant_runbook": "No specific runbook found. Follow generic incident response: check logs, identify recent changes, escalate if unresolved in 15 minutes.",
            "runbook_title":    "Generic Incident Response",
            "steps_completed":  ["search_runbooks"],
        }


def estimate_impact_node(state: SREAgentState) -> dict:
    """
    Node 4: estimate how many users are affected and produce an
    impact summary.
    """
    print(f"[estimate_impact] Estimating impact for: {state['service_name']}")

    alert      = state["alert"]
    error_rate = alert.get("error_rate", 0.1)

    result = estimate_impact(
        service_name=state["service_name"], # type: ignore
        error_rate=error_rate,
        severity=state["severity"], # type: ignore
    )

    print(f"[estimate_impact] ~{result['estimated_users_affected']:,} users affected")

    return {
        "estimated_users_affected": result["estimated_users_affected"],
        "impact_summary":           result["impact_summary"],
        "steps_completed":          ["estimate_impact"],
    }


def post_slack_brief_node(state: SREAgentState) -> dict:
    """
    Node 5: format and post the incident brief to Slack.
    """
    print("[post_slack_brief] Formatting and posting Slack brief")

    brief   = format_incident_brief(state) # type: ignore
    success = post_to_slack(brief)

    return {
        "slack_brief":  brief,
        "slack_posted": success,
        "status":       "mitigated" if success else "failed",
        "steps_completed": ["post_slack_brief"],
    }


def generate_postmortem_node(state: SREAgentState) -> dict:
    """
    Node 6 (stretch): generate a structured postmortem document using
    everything the agent discovered during investigation.
    """
    print("[generate_postmortem] Generating postmortem report")

    suspicious = state.get("suspicious_commits", [])
    if suspicious:
        commits_summary = "\n".join(
            f"- [{c['hash']}] {c['message']} by {c['author']} "
            f"(confidence: {c.get('confidence', 0):.0%}): {c.get('reason', '')}"
            for c in suspicious
        )
    else:
        commits_summary = "No specific commits identified as root cause."

    prompt = f"""Generate a professional engineering postmortem for the following incident.

INCIDENT DETAILS:
- Service: {state.get('service_name')}
- Error Type: {state.get('error_type')}
- Severity: {state.get('severity')}
- Time Detected: {state.get('alert_timestamp')}
- Users Affected: {state.get('estimated_users_affected', 0):,}

ROOT CAUSE COMMITS (AI-identified):
{commits_summary}

RUNBOOK USED: {state.get('runbook_title', 'Generic Incident Response')}

Write a postmortem with these sections:
1. Incident Summary (2-3 sentences)
2. Timeline (bullet points)
3. Root Cause Analysis
4. Impact Assessment
5. Resolution Steps Taken
6. Action Items to Prevent Recurrence (3-5 specific items)

Be specific and technical. Format in clean markdown."""

    response = llm_client.chat.completions.create(
        model=config.GENERATION_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return {
        "postmortem":      response.choices[0].message.content,
        "status":          "done",
        "steps_completed": ["generate_postmortem"],
    }


def fallback_handler(state: SREAgentState) -> dict:
    """
    Fallback node: called when something goes wrong mid-pipeline.
    Posts a minimal escalation alert so humans know to investigate.
    """
    print(f"[fallback_handler] Handling failure: {state.get('error')}")

    message = (
        f"⚠️ *SRE Agent encountered an error during triage*\n\n"
        f"*Incident:* {state.get('error_type', 'unknown')} on "
        f"`{state.get('service_name', 'unknown')}`\n"
        f"*Agent Error:* {state.get('error', 'Unknown error')}\n\n"
        f"*Steps completed before failure:* "
        f"{', '.join(state.get('steps_completed', []))}\n\n"
        f"Manual investigation required."
    )

    post_to_slack(message)

    return {
        "slack_brief":  message,
        "slack_posted": True,
        "status":       "failed",
        "steps_completed": ["fallback_handler"],
    }
