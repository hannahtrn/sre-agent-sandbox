from langgraph.graph import StateGraph, END
from src.agent.state import SREAgentState
from src.agent.nodes import (
    parse_alert,
    search_git_logs,
    search_runbooks_node,
    estimate_impact_node,
    post_slack_brief_node,
    generate_postmortem_node,
    fallback_handler,
)


def route_after_git(state: SREAgentState) -> str:
    """
    After git log search: route to fallback if an error occurred,
    otherwise always continue to runbook search.
    No commits found is not an error — the pipeline continues
    and the Slack brief will note no suspicious commits were found.
    """
    if state.get("error"):
        return "fallback_handler"
    return "search_runbooks"


def route_after_runbooks(state: SREAgentState) -> str:
    """
    After runbook search: always continue to impact estimation.
    A missing runbook is handled gracefully inside the node itself
    with a generic fallback — never a reason to abort.
    """
    if state.get("error"):
        return "fallback_handler"
    return "estimate_impact"


def build_graph():
    graph = StateGraph(SREAgentState)

    # register all nodes
    graph.add_node("parse_alert",         parse_alert)
    graph.add_node("search_git_logs",     search_git_logs)
    graph.add_node("search_runbooks",     search_runbooks_node)
    graph.add_node("estimate_impact",     estimate_impact_node)
    graph.add_node("post_slack_brief",    post_slack_brief_node)
    graph.add_node("generate_postmortem", generate_postmortem_node)
    graph.add_node("fallback_handler",    fallback_handler)

    # entry point
    graph.set_entry_point("parse_alert")

    # fixed edges
    graph.add_edge("parse_alert",      "search_git_logs")
    graph.add_edge("estimate_impact",  "post_slack_brief")
    graph.add_edge("post_slack_brief", "generate_postmortem")
    graph.add_edge("generate_postmortem", END)
    graph.add_edge("fallback_handler", END)

    # conditional edges
    graph.add_conditional_edges("search_git_logs", route_after_git)
    graph.add_conditional_edges("search_runbooks", route_after_runbooks)

    return graph.compile()


# compile once at import time — reused across all requests
sre_agent = build_graph()
