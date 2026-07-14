"""
Trigger a simulated incident and watch the agent respond end-to-end.

Usage:
    python scripts/fire_alert.py db-exhaustion
    python scripts/fire_alert.py memory-leak
    python scripts/fire_alert.py high-error-rate
"""
import sys
import httpx

GATEWAY_URL = "http://localhost:8000"


def fire(scenario: str):
    print(f"\nFiring scenario: {scenario}")
    print("Waiting for agent to complete...\n")

    response = httpx.get(
        f"{GATEWAY_URL}/simulate/{scenario}",
        timeout=120.0,
    )

    if response.status_code != 200:
        print(f"Error: {response.status_code} — {response.text}")
        return

    result = response.json()
    print(f"Status:          {result['status']}")
    print(f"Steps completed: {' → '.join(result['steps_completed'])}")
    print(f"Service:         {result.get('service')}")
    print(f"Users affected:  {result.get('users_affected', 0):,}")
    print(f"Slack posted:    {result.get('slack_posted')}")

    if result.get("postmortem"):
        print(f"\nPostmortem generated ({len(result['postmortem'])} chars)")
        print("\n--- POSTMORTEM PREVIEW (first 500 chars) ---")
        print(result["postmortem"][:500])


if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "db-exhaustion"
    fire(scenario)
