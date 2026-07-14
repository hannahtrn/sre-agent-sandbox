from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from src.agent.graph import sre_agent
from src.agent.state import SREAgentState

app = FastAPI(
    title="SRE Agent Gateway",
    description="Receives production alerts and triggers autonomous triage agent.",
    version="1.0.0",
)


class AlertPayload(BaseModel):
    service: str
    incident_type: str
    error_rate: float
    severity: str
    description: str
    timestamp: str = None


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "ready"}


@app.post("/alert")
async def receive_alert(payload: AlertPayload):
    """
    Receive an alert and run the SRE agent asynchronously.
    Uses ainvoke() so the FastAPI worker is not blocked
    during the agent's LLM calls.
    """
    alert_dict = payload.model_dump()
    if not alert_dict.get("timestamp"):
        alert_dict["timestamp"] = datetime.now(timezone.utc).isoformat()

    initial_state: SREAgentState = {
        "alert":                    alert_dict,
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

    return {
        "status":          result["status"],
        "steps_completed": result["steps_completed"],
        "service":         result.get("service_name"),
        "severity":        result.get("severity"),
        "users_affected":  result.get("estimated_users_affected"),
        "slack_posted":    result.get("slack_posted"),
        "runbook_used":    result.get("runbook_title"),
        "suspicious_commits": [
            {
                "hash":       c["hash"],
                "author":     c["author"],
                "message":    c["message"],
                "confidence": c.get("confidence", 0),
                "reason":     c.get("reason", ""),
            }
            for c in (result.get("suspicious_commits") or [])
        ],
        "brief_preview": (result.get("slack_brief") or "")[:300] + "...",
        "postmortem":    result.get("postmortem"),
    }


@app.get("/simulate/{incident_type}")
async def simulate_incident(incident_type: str):
    """
    Trigger a pre-built simulation scenario for demos.

    Available:
        GET /simulate/db-exhaustion
        GET /simulate/memory-leak
        GET /simulate/high-error-rate
    """
    scenarios = {
        "db-exhaustion": AlertPayload(
            service="checkout-service",
            incident_type="Database connection pool exhausted",
            error_rate=0.45,
            severity="critical",
            description="HTTP 500 spike on /checkout endpoint. DB connections failing. Errors: connection timeout, pool exhausted.",
            timestamp="2026-07-11T17:30:00Z",
        ),
        "memory-leak": AlertPayload(
            service="api-gateway",
            incident_type="Memory leak OOM risk",
            error_rate=0.15,
            severity="high",
            description="Memory utilization at 94% and climbing. Worker restarts increasing. OOM killer triggered twice.",
            timestamp="2026-07-11T17:30:00Z",
        ),
        "high-error-rate": AlertPayload(
            service="checkout-service",
            incident_type="High HTTP 500 error rate",
            error_rate=0.32,
            severity="high",
            description="500 error rate spiked from 0.1% to 32% after recent deployment. Unhandled exceptions in payment flow.",
            timestamp="2026-07-11T17:30:00Z",
        ),
    }

    if incident_type not in scenarios:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario. Available: {list(scenarios.keys())}"
        )

    return await receive_alert(scenarios[incident_type])
