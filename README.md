# Autonomous SRE Agent Sandbox

An event-driven AI agent that autonomously triages production incidents the moment an alert fires. Built with LangGraph and FastAPI, the agent analyzes recent git commits using GPT-4o-mini to identify likely root causes, searches a ChromaDB runbook index for relevant mitigation procedures, estimates user impact, posts a structured Slack incident brief, and generates a full postmortem report — all within seconds of alert receipt.

Everything runs in a fully self-contained Docker environment. No real PagerDuty or AWS. Just a realistic simulation of the architecture that SRE teams at large companies use to reduce mean time to resolution.

---

## Architecture

```
[Simulated Alert Fires]
        ↓
[FastAPI Gateway — async ainvoke]
        ↓
[LangGraph State Machine]
        ↓
┌─────────────────────────────────────────────────────────┐
│  Node 1: parse_alert                                    │
│  Validates and extracts service, error type, severity   │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  Node 2: search_git_logs                                │
│  Reads mock git history anchored to alert timestamp     │
│  GPT-4o-mini analyzes each commit diff against alert    │
│  Returns suspicious commits with confidence + reason    │
└─────────────────────┬───────────────────────────────────┘
                      ↓ (error → fallback_handler)
┌─────────────────────────────────────────────────────────┐
│  Node 3: search_runbooks                                │
│  Embeds alert description, queries ChromaDB             │
│  Returns most relevant runbook or generic fallback      │
└─────────────────────┬───────────────────────────────────┘
                      ↓ (error → fallback_handler)
┌─────────────────────────────────────────────────────────┐
│  Node 4: estimate_impact                                │
│  Calculates affected users from simulated traffic data  │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  Node 5: post_slack_brief                               │
│  Formats and posts structured markdown incident brief   │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  Node 6: generate_postmortem                            │
│  Full postmortem doc using accumulated agent state      │
└─────────────────────┬───────────────────────────────────┘
                      ↓
                    [END]
```

**Key engineering decisions:**
- LangGraph models the workflow as a state machine with conditional edges — if any node fails, the graph routes to `fallback_handler` which posts a human-escalation alert to Slack instead of crashing silently
- The gateway uses `await sre_agent.ainvoke()` — async execution means the FastAPI worker is never blocked during the 20-40 second agent run
- Commit analysis uses GPT-4o-mini with structured JSON output to reason about code diffs against the active alert signature — no hardcoded flags, genuine AI reasoning
- `steps_completed` uses a LangGraph `Annotated` reducer for atomic state accumulation across nodes
- Git log lookback anchors to the alert's timestamp, not `datetime.now()` — making the simulation deterministic on any date

---

## Example output — db-exhaustion scenario

**Suspicious commits identified by LLM:**

```
[c9a4f33] priya.patel — update checkout flow for new payment provider
  Confidence: 85%
  Reason: The removal of error handling for timeout exceptions could lead to
  unhandled exceptions, causing the database connection pool to be exhausted
  due to increased failed connection attempts.

[b7d2e19] marcus.johnson — quick fix prod db timeout
  Confidence: 90%
  Reason: The commit reduced the database connection pool size from 20 to 5,
  which likely led to the exhaustion of available connections and timeouts.
```

**Slack brief (excerpt):**
```
INCIDENT ALERT — CRITICAL

Service: checkout-service
Error Type: Database connection pool exhausted
Detected: 2026-07-11T17:30:00Z

Impact Assessment
Approximately 20,250 users affected (45% of traffic). 540 requests/min
failing. Complete service outage. Revenue impact active.

Likely Root Cause (AI Analysis)
• [c9a4f33] by priya.patel (confidence: 85%)
• [b7d2e19] by marcus.johnson (confidence: 90%)

Recommended Runbook: Db Connection Pool
```

---

## Project structure

```
sre-agent-sandbox/
├── src/
│   ├── agent/
│   │   ├── state.py            ← shared state TypedDict with LangGraph reducer
│   │   ├── nodes.py            ← all 6 node functions + fallback handler
│   │   └── graph.py            ← LangGraph graph with conditional routing
│   └── tools/
│       ├── git_tool.py         ← git log reader + LLM commit analysis
│       ├── runbook_tool.py     ← ChromaDB vector search
│       ├── impact_tool.py      ← user impact estimation
│       └── slack_tool.py       ← Slack formatter and poster
├── gateway/
│   └── app.py                  ← async FastAPI entry point
├── data/
│   ├── git_log.json            ← 6 simulated commits across 3 services
│   └── runbooks/               ← 8 markdown runbooks ingested into ChromaDB
├── scripts/
│   ├── ingest_runbooks.py      ← loads runbooks into ChromaDB
│   ├── fire_alert.py           ← CLI demo script
│   └── test_run.py             ← direct graph invocation for testing
├── tests/
│   └── test_nodes.py           ← 15 unit tests with isolated node testing
├── config.py
├── Dockerfile
└── docker-compose.yml
```

---

## Simulation scenarios

Three pre-built incident types, each triggering different agent behavior:

| Scenario | Service | Error Type | Severity | Users Affected |
|---|---|---|---|---|
| `db-exhaustion` | checkout-service | Database connection pool exhausted | Critical | ~20,250 |
| `memory-leak` | api-gateway | Memory leak / OOM risk | High | ~6,750 |
| `high-error-rate` | checkout-service | High HTTP 500 error rate | High | ~14,400 |

Each scenario uses the same agent pipeline but retrieves different runbooks from ChromaDB and the LLM produces different commit analysis reasoning based on the specific alert signature.

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service health check |
| POST | `/alert` | Receive a custom alert payload and run the agent |
| GET | `/simulate/{incident_type}` | Trigger a pre-built scenario |

**Custom alert payload:**
```json
{
  "service": "checkout-service",
  "incident_type": "Database connection pool exhausted",
  "error_rate": 0.45,
  "severity": "critical",
  "description": "HTTP 500 spike on /checkout. DB connections failing.",
  "timestamp": "2026-07-11T17:30:00Z"
}
```

**Response includes:**
- `status` — done / mitigated / failed
- `steps_completed` — ordered list of nodes that ran
- `suspicious_commits` — LLM-identified commits with confidence scores and reasoning
- `runbook_used` — which runbook ChromaDB retrieved
- `users_affected` — estimated impact
- `postmortem` — full generated postmortem document

---

## Setup and running

### Prerequisites
- Docker Desktop installed and running
- OpenAI API key with credits

### Run the full stack

```bash
git clone https://github.com/hannahtrn/sre-agent-sandbox.git
cd sre-agent-sandbox
cp .env.example .env        # add your OpenAI API key
docker compose up --build
```

### Ingest runbooks (required after first startup)

ChromaDB starts empty. In a second terminal after `docker compose up` is running:

```bash
# ChromaDB is on port 8001, gateway is on port 8000
# Make sure CHROMA_PORT=8001 in your .env
PYTHONPATH=. python scripts/ingest_runbooks.py
```

### Trigger a simulation

```bash
# using the demo script
python scripts/fire_alert.py db-exhaustion
python scripts/fire_alert.py memory-leak
python scripts/fire_alert.py high-error-rate

# or directly via curl
curl http://localhost:8000/simulate/db-exhaustion
```

### Run tests

```bash
PYTHONPATH=. pytest tests/ -v
```

15 tests covering parse_alert, fallback_handler, estimate_impact, and the LangGraph reducer pattern.

---

## Tech stack

| Component | Technology |
|---|---|
| Agent framework | LangGraph (state machine with conditional routing) |
| API gateway | FastAPI + async Python |
| Commit analysis | GPT-4o-mini with structured JSON output |
| Runbook search | ChromaDB (HNSW vector indexing) |
| Embeddings | OpenAI text-embedding-3-small |
| Postmortem generation | GPT-4o-mini |
| Containerization | Docker + Docker Compose |
| Testing | pytest with isolated node unit tests |

---

## What a production version would look like

The sandbox replaces real infrastructure with realistic simulations. In production:

- `data/git_log.json` → GitHub API or `git log` on the actual repository
- `MOCK_SERVICE_TRAFFIC` → Prometheus, Datadog, or CloudWatch metrics
- Simulated alert payloads → Real PagerDuty or Datadog webhooks
- 8 runbooks → Hundreds of documents from Confluence or Notion
- Mock Slack → Real Slack webhook with channel routing by severity
- No human-in-the-loop → Human approval step before auto-remediation actions like rollbacks

The architecture is identical. Only the data sources change.
