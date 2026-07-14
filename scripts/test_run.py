"""
Direct graph invocation — no gateway needed.
Use this to test the full agent pipeline before building the API.
"""
import asyncio
from src.agent.graph import sre_agent
from src.agent.state import SREAgentState


async def main():
    print("=" * 60)
    print("SRE AGENT — DIRECT TEST RUN")
    print("=" * 60)

    initial_state: SREAgentState = {
        "alert": {
            "service":       "checkout-service",
            "incident_type": "Database connection pool exhausted",
            "error_rate":    0.45,
            "severity":      "critical",
            "description":   "HTTP 500 spike on /checkout endpoint. DB connections failing. Errors: connection timeout, pool exhausted.",
            "timestamp":     "2026-07-11T17:30:00Z",
        },
        "service_name":             None,
        "error_type":               None,
        "severity":                 None,
        "alert_timestamp":          None,
        "recent_commits":           None,
        "suspicious_commits":       None,
        "relevant_runbook":         None,
        "runbook_title":            None,
        "estimated_users_affected": None,
        "impact_summary":           None,
        "slack_brief":              None,
        "slack_posted":             None,
        "postmortem":               None,
        "error":                    None,
        "status":                   "investigating",
        "steps_completed":          [],
    }

    result = await sre_agent.ainvoke(initial_state)

    print("\n" + "=" * 60)
    print("AGENT COMPLETED")
    print("=" * 60)
    print(f"Status:          {result['status']}")
    print(f"Steps completed: {' → '.join(result['steps_completed'])}")
    print(f"Users affected:  {result.get('estimated_users_affected', 0):,}")
    print(f"Runbook used:    {result.get('runbook_title')}")
    print(f"Slack posted:    {result.get('slack_posted')}")

    if result.get("suspicious_commits"):
        print(f"\nSuspicious commits found ({len(result['suspicious_commits'])}):")
        for c in result["suspicious_commits"]:
            print(f"  [{c['hash']}] {c['message']}")
            print(f"  Confidence: {c.get('confidence', 0):.0%}")
            print(f"  Reason: {c.get('reason', '')}")

    if result.get("postmortem"):
        print(f"\nPostmortem generated ({len(result['postmortem'])} chars)")
        print("\n--- POSTMORTEM PREVIEW ---")
        print(result["postmortem"][:600])


if __name__ == "__main__":
    asyncio.run(main())