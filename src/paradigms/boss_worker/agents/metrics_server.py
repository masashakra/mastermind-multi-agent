"""
Metrics Agent — A2A HTTP server for distributed metrics collection.

Other agents call the Metrics agent via HTTP POST to record metrics.
All metrics aggregated to logs/metrics.json.
"""

import sys
import json
import time
import threading
import httpx
import uvicorn
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from fastapi import FastAPI
from communication.a2a_message import A2AMessage, A2AStatus, A2AErrorCode
from base.agent_card_schema import A2AAgentCard, A2ACapability
from communication.a2a_contract import METRICS_RECORD_INPUT, METRICS_RECORD_OUTPUT


# ── Agent card ────────────────────────────────────────────────────────────────

METRICS_AGENT_CARD = A2AAgentCard(
    agent_id="metrics_boss_worker",
    agent_name="Metrics",
    agent_type="metrics",
    paradigm="boss_worker",
    version="1.0.0",
    description="Distributed metrics collection agent. Other agents POST metrics to be recorded.",
    url="",  # Set at startup
    capabilities=[
        A2ACapability(
            name="record",
            description="Record a metric value",
            input_schema=METRICS_RECORD_INPUT,
            output_schema=METRICS_RECORD_OUTPUT,
            timeout_seconds=10,
        ),
    ],
    constraints_owned=["Metrics accuracy"],
    can_communicate=False,  # Metrics doesn't initiate communication
)


# ── Metrics class ─────────────────────────────────────────────────────────────

class MetricsAgent:
    """In-memory metrics collector that aggregates to JSON."""

    def __init__(self, logs_dir: Path = None):
        self.logs_dir = logs_dir or Path(__file__).parent.parent / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.logs_dir / "metrics.json"
        self.metrics: Dict[str, Any] = self._load_metrics()
        self.record_count = 0

    def _load_metrics(self) -> Dict[str, Any]:
        """Load existing metrics from file."""
        if self.metrics_file.exists():
            try:
                return json.loads(self.metrics_file.read_text())
            except Exception:
                pass
        return {"records": [], "summary": {}}

    def record_metric(self, metric_name: str, value: Any, tags: Dict[str, Any] = None) -> Dict[str, Any]:
        """Record a metric."""
        record = {
            "metric_name": metric_name,
            "value": value,
            "tags": tags or {},
            "timestamp": time.time(),
            "sequence": self.record_count,
        }
        self.metrics["records"].append(record)
        self.record_count += 1

        # Update summary
        if metric_name not in self.metrics["summary"]:
            self.metrics["summary"][metric_name] = {
                "count": 0,
                "values": [],
                "latest": None,
            }
        self.metrics["summary"][metric_name]["count"] += 1
        if isinstance(value, (int, float)):
            self.metrics["summary"][metric_name]["values"].append(value)
        self.metrics["summary"][metric_name]["latest"] = value

        # Write to file
        self.metrics_file.write_text(json.dumps(self.metrics, indent=2))
        print(f"[Metrics] Recorded: {metric_name} = {value}")
        return {"recorded": True, "metric_name": metric_name}

    def get_metrics(self) -> Dict[str, Any]:
        """Retrieve all metrics."""
        return self.metrics


# ── FastAPI app ───────────────────────────────────────────────────────────────

def create_metrics_app(registry_url: str, self_url: str) -> FastAPI:
    app = FastAPI(title="Metrics Agent")
    metrics = MetricsAgent()
    card = METRICS_AGENT_CARD
    card.url = self_url

    @app.on_event("startup")
    def on_startup():
        # Register with registry
        for attempt in range(10):
            try:
                r = httpx.post(f"{registry_url}/register", json=card.to_dict(), timeout=5.0)
                if r.status_code == 200:
                    print(f"[Metrics] Registered with registry @ {self_url}")
                    return
            except Exception:
                pass
            time.sleep(0.4)
        print(f"[Metrics] Warning: could not register with registry")

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": "metrics"}

    @app.get("/.well-known/agent.json")
    def agent_card():
        return card.to_dict()

    @app.post("/record")
    def record_metric(body: Dict[str, Any]) -> Dict[str, Any]:
        """A2A endpoint: record a metric."""
        try:
            metric_name = body.get("metric_name")
            value = body.get("value")
            tags = body.get("tags", {})

            if not metric_name:
                return {
                    "status": "error",
                    "error": "metric_name is required",
                }

            result = metrics.record_metric(metric_name, value, tags)
            return {
                "status": "ok",
                **result,
            }
        except Exception as e:
            print(f"[Metrics] Error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    @app.get("/metrics")
    def get_metrics():
        """Retrieve all metrics."""
        return metrics.get_metrics()

    return app


def start_metrics_server(registry_url: str, port: int = 8106) -> str:
    """Start the metrics server in a daemon thread."""
    self_url = f"http://localhost:{port}"
    app = create_metrics_app(registry_url, self_url)

    def run():
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    # Wait for health
    for _ in range(25):
        try:
            r = httpx.get(f"{self_url}/health", timeout=2.0)
            if r.status_code == 200:
                print(f"[Orchestrator] Metrics running at {self_url}")
                return self_url
        except Exception:
            pass
        time.sleep(0.3)

    raise RuntimeError(f"Metrics at {self_url} never became healthy")
