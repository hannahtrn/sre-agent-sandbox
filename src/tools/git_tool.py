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

    IMPORTANT: anchors to alert_timestamp, not datetime.now().
    If we used datetime.now(), the hardcoded timestamps in git_log.json
    would fall outside the window the moment you run this days later.
    Anchoring to the alert timestamp makes this deterministic regardless
    of when you run the project.
    """
    git_log_path = Path("data/git_log.json")
    if not git_log_path.exists():
        return []

    with open(git_log_path, "r") as f:
        all_commits = json.load(f)

    # anchor to the alert's timestamp, not current clock
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

    For each commit, the LLM reads the diff summary and alert description
    together and decides: is this commit suspicious? Why?

    This is what makes the agent genuinely AI-powered rather than just a
    Python script with a hardcoded flag. The LLM applies SRE reasoning to
    unstructured code change descriptions.

    Returns the same list of commits with three new fields added:
        - is_suspicious: bool
        - confidence: float (0.0 to 1.0)
        - reason: str (one-sentence SRE explanation)
    """
    if not commits:
        return []

    client = OpenAI(api_key=config.OPENAI_API_KEY)
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
            content = response.choices[0].message.content
            analysis = json.loads(content) if content else {
                "is_suspicious": False,
                "confidence": 0.0,
                "reason": "No content returned from the response."
            }
        except Exception as e:
            analysis = {
                "is_suspicious": False,
                "confidence": 0.0,
                "reason": f"Analysis failed: {str(e)}",
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
    """Format commits for readable output."""
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
