from src.agent.state import SREAgentState
from src.agent.nodes import parse_alert, fallback_handler, estimate_impact_node

BASE_ALERT = {
    "service":       "checkout-service",
    "incident_type": "High HTTP 500 error rate",
    "error_rate":    0.35,
    "severity":      "critical",
    "description":   "500 errors spiked after deployment",
    "timestamp":     "2026-07-11T17:30:00Z",
}

BASE_STATE: SREAgentState = {
    "alert":                    BASE_ALERT,
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


def test_parse_alert_extracts_service():
    result = parse_alert(BASE_STATE)
    assert result["service_name"] == "checkout-service"


def test_parse_alert_extracts_severity():
    result = parse_alert(BASE_STATE)
    assert result["severity"] == "critical"


def test_parse_alert_extracts_error_type():
    result = parse_alert(BASE_STATE)
    assert result["error_type"] == "High HTTP 500 error rate"


def test_parse_alert_extracts_timestamp():
    result = parse_alert(BASE_STATE)
    assert result["alert_timestamp"] == "2026-07-11T17:30:00Z"


def test_parse_alert_sets_investigating_status():
    result = parse_alert(BASE_STATE)
    assert result["status"] == "investigating"


def test_parse_alert_records_step():
    result = parse_alert(BASE_STATE)
    assert "parse_alert" in result["steps_completed"]


def test_parse_alert_handles_missing_service():
    state = {**BASE_STATE, "alert": {}}
    result = parse_alert(state)
    assert result["service_name"] == "unknown"


def test_parse_alert_handles_missing_severity():
    state = {**BASE_STATE, "alert": {"service": "api-gateway"}}
    result = parse_alert(state)
    assert result["severity"] == "high"  # default


def test_fallback_sets_failed_status():
    state = {**BASE_STATE, "error": "Git tool crashed"}
    result = fallback_handler(state)
    assert result["status"] == "failed"


def test_fallback_records_step():
    state = {**BASE_STATE, "error": "test error"}
    result = fallback_handler(state)
    assert "fallback_handler" in result["steps_completed"]


def test_fallback_sets_slack_posted():
    state = {**BASE_STATE, "error": "test error"}
    result = fallback_handler(state)
    assert result["slack_posted"] is True


def test_estimate_impact_checkout_service():
    state = {
        **BASE_STATE,
        "service_name": "checkout-service",
        "severity":     "critical",
    }
    result = estimate_impact_node(state)
    assert result["estimated_users_affected"] == int(45000 * 0.35)
    assert "checkout-service" in result["impact_summary"]


def test_estimate_impact_unknown_service():
    state = {
        **BASE_STATE,
        "service_name": "unknown-service",
        "severity":     "low",
    }
    result = estimate_impact_node(state)
    assert result["estimated_users_affected"] is not None
    assert result["estimated_users_affected"] >= 0


def test_estimate_impact_records_step():
    state = {
        **BASE_STATE,
        "service_name": "checkout-service",
        "severity":     "high",
    }
    result = estimate_impact_node(state)
    assert "estimate_impact" in result["steps_completed"]


def test_steps_reducer_accumulates():
    """
    Verify that each node only returns its own step name.
    LangGraph's reducer handles accumulation at runtime —
    calling nodes directly in tests bypasses that merge.
    This test confirms the node returns the correct step name
    and that manually merging simulates what LangGraph does.
    """
    result1 = parse_alert(BASE_STATE)
    assert result1["steps_completed"] == ["parse_alert"]

    # simulate LangGraph's reducer merging manually
    merged_steps = BASE_STATE["steps_completed"] + result1["steps_completed"]
    state2 = {**BASE_STATE, "steps_completed": merged_steps}

    result2 = fallback_handler({**state2, "error": "test"})
    assert result2["steps_completed"] == ["fallback_handler"]

    # simulate another merge — this is what LangGraph does automatically
    final_steps = state2["steps_completed"] + result2["steps_completed"]
    assert "parse_alert" in final_steps
    assert "fallback_handler" in final_steps