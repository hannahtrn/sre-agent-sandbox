# src/agent/state.py
from typing import TypedDict, Optional, Annotated


def append_steps(existing: list, new: list) -> list:
    """
    Reducer function for steps_completed.
    LangGraph calls this whenever a node returns {"steps_completed": [...]}.
    Instead of replacing the list, it appends the new steps to the existing ones.
    This is safer than manually doing state["steps_completed"] + ["x"] in every node.
    """
    return existing + new


class SREAgentState(TypedDict):
    """
    Shared state object that flows through every node in the graph.
    Every node reads what it needs and writes what it produces.
    Fields start as None and get populated as the agent progresses.

    The error field acts as a circuit breaker — if any node sets it,
    conditional edges route to fallback_handler instead of continuing.
    """

    # input
    alert: dict

    # populated by parse_alert
    service_name:    Optional[str]
    error_type:      Optional[str]
    severity:        Optional[str]
    alert_timestamp: Optional[str]

    # populated by search_git_logs
    recent_commits:    Optional[list]
    suspicious_commits: Optional[list]

    # populated by search_runbooks
    relevant_runbook: Optional[str]
    runbook_title:    Optional[str]

    # populated by estimate_impact
    estimated_users_affected: Optional[int]
    impact_summary:           Optional[str]

    # populated by post_slack_brief
    slack_brief:  Optional[str]
    slack_posted: Optional[bool]

    # populated by generate_postmortem
    postmortem: Optional[str]

    # control
    error:  Optional[str]
    status: str
    steps_completed: Annotated[list, append_steps]