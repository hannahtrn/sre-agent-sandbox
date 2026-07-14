import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from openai import OpenAI
from config import config


def get_recent_commits(
    service_name: str,
    alert_timestamp: str,
    hours_back: int = 2,
) -> list[dict]:
    """
    Read mock git log and return commits for the given service within
    `hours_back` hours BEFORE the alert fired.

    Anchors to alert_timestamp, not datetime.now() — this makes the
    project work correctly on any date, not just the day you wrote it.
    """
    git_log_path = Path("data/git_log.json")
    if not git_log_path.exists():
        return []

    with open(git_log_path, "r") as f:
        all_commits = json.load(f)

    alert_time = datetime.fromisoformat(
        alert_timestamp.replace("Z", "+00:00")
    )
    cutoff = alert_time - timedelta(hours=hours_back)

    recent = []
    for commit in all_commits:
        if commit.get("service") != service_name:
            continue
        commit_time = datetime.fromisoformat(
            commit["timestamp"].replace("Z", "+00:00")
        )
        if cutoff <= commit_time <= alert_time:
            recent.append(commit)

    return sorted(recent, key=lambda c: c["timestamp"], reverse=True)


def analyze_commits_with_llm(
    alert_description: str,
    commits: list[dict],
) -> list[dict]:
    """
    Use GPT-4o-mini to reason about which commits are likely root causes
    of the active incident.

    For each commit, the LLM reads the diff summary alongside the alert
    description and decides: is this suspicious? How confident? Why?

    This is what makes the agent genuinely AI-powered. No hardcoded flags —
    the LLM applies actual SRE reasoning to unstructured code change text.

    Returns the same list of commits with three new fields added:
        is_suspicious: bool
        confidence:    float 0.0 to 1.0
        reason:        str one-sentence SRE explanation
    """
    if not commits:
        return []

    client   = OpenAI(api_key=config.OPENAI_API_KEY)
    analyzed = []

    for commit in commits:
        prompt = f"""You are a Senior Site Reliability Engineer investigating a production incident.
Analyze this recent code commit against the active incident to determine if it is a likely root cause.

ACTIVE PRODUCTION ALERT:
{alert_description}

COMMIT TO ANALYZE:
- Hash: {commit['hash']}
- Author: {commit['author']}
- Timestamp: {commit['timestamp']}
- Message: {commit['message']}
- Files changed: {', '.join(commit['files_changed'])}
- Change summary: {commit['diff_summary']}

Based on the alert signature and this commit's changes, assess whether this commit
could have caused the incident.

Respond with ONLY a JSON object in this exact format:
{{
  "is_suspicious": true or false,
  "confidence": 0.0 to 1.0,
  "reason": "one sentence technical explanation of why or why not"
}}"""

        try:
            response = client.chat.completions.create(
                model=config.GENERATION_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            analysis = json.loads(response.choices[0].message.content) # type: ignore
        except Exception as e:
            analysis = {
                "is_suspicious": False,
                "confidence":    0.0,
                "reason":        f"Analysis failed: {str(e)}",
            }

        commit["is_suspicious"] = analysis.get("is_suspicious", False)
        commit["confidence"]    = analysis.get("confidence", 0.0)
        commit["reason"]        = analysis.get("reason", "")
        analyzed.append(commit)

    return analyzed


def identify_suspicious_commits(commits: list[dict]) -> list[dict]:
    """Return commits the LLM flagged as suspicious."""
    return [c for c in commits if c.get("is_suspicious", False)]


def format_commits_for_display(commits: list[dict]) -> str:
    """Format commits into readable text for logging."""
    if not commits:
        return "No recent commits found."
    lines = []
    for c in commits:
        lines.append(
            f"[{c['hash']}] {c['author']} — {c['message']}\n"
            f"  Files: {', '.join(c['files_changed'])}\n"
            f"  Changes: {c['diff_summary']}"
        )
    return "\n\n".join(lines)