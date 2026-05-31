"""
Logger Agent — A2A HTTP server for distributed logging.

Other agents call the Logger via HTTP POST to record messages.
All messages logged to logs/communication_logs/ as JSONL.
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
from communication.a2a_contract import LOGGER_LOG_INPUT, LOGGER_LOG_OUTPUT


# ── Agent card ────────────────────────────────────────────────────────────────

LOGGER_AGENT_CARD = A2AAgentCard(
    agent_id="logger_boss_worker",
    agent_name="Logger",
    agent_type="logger",
    paradigm="boss_worker",
    version="1.0.0",
    description="Distributed logging agent. Other agents POST messages to be logged.",
    url="",  # Set at startup
    capabilities=[
        A2ACapability(
            name="log",
            description="Log a message to the communication log",
            input_schema=LOGGER_LOG_INPUT,
            output_schema=LOGGER_LOG_OUTPUT,
            timeout_seconds=10,
        ),
    ],
    constraints_owned=["Log completeness"],
    can_communicate=False,  # Logger doesn't initiate communication
)


# ── Logger class ──────────────────────────────────────────────────────────────

class LoggerAgent:
    """In-memory logger that stores messages."""

    def __init__(self, logs_dir: Path = None):
        self.logs_dir = logs_dir or Path(__file__).parent.parent / "logs" / "communication_logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.messages: list[Dict[str, Any]] = []
        self.message_count = 0

    def log_message(self, message: A2AMessage) -> Dict[str, Any]:
        """Store a message."""
        log_entry = {
            **message.to_dict(),
            "logged_at": time.time(),
            "log_sequence": self.message_count,
        }
        self.messages.append(log_entry)
        self.message_count += 1

        # Write to JSONL file
        log_file = self.logs_dir / f"communication_{int(time.time()*1000)}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        print(f"[Logger] Message {self.message_count}: {message.action} from {message.sender_id}")
        return {"logged": True, "log_id": message.message_id, "timestamp": time.time()}

    def get_logs(self, filter_by_type: str = None) -> list[Dict[str, Any]]:
        """Retrieve logged messages."""
        if filter_by_type:
            return [m for m in self.messages if m.get("action") == filter_by_type]
        return self.messages


# ── FastAPI app ───────────────────────────────────────────────────────────────

def create_logger_app(registry_url: str, self_url: str) -> FastAPI:
    app = FastAPI(title="Logger Agent")
    logger = LoggerAgent()
    card = LOGGER_AGENT_CARD
    card.url = self_url

    @app.on_event("startup")
    def on_startup():
        # Register with registry
        for attempt in range(10):
            try:
                r = httpx.post(f"{registry_url}/register", json=card.to_dict(), timeout=5.0)
                if r.status_code == 200:
                    print(f"[Logger] Registered with registry @ {self_url}")
                    return
            except Exception:
                pass
            time.sleep(0.4)
        print(f"[Logger] Warning: could not register with registry")

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": "logger"}

    @app.get("/.well-known/agent.json")
    def agent_card():
        return card.to_dict()

    @app.post("/log")
    def log_message(body: Dict[str, Any]) -> Dict[str, Any]:
        """A2A endpoint: log a message."""
        try:
            # Create A2A request from body
            msg = A2AMessage.from_dict(body)
            result = logger.log_message(msg)
            return {
                "status": "ok",
                "message_id": msg.message_id,
                **result,
            }
        except Exception as e:
            print(f"[Logger] Error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    @app.get("/logs")
    def get_logs():
        """Retrieve all logged messages."""
        return {
            "message_count": logger.message_count,
            "messages": logger.get_logs(),
        }

    return app


def start_logger_server(registry_url: str, port: int = 8105) -> str:
    """Start the logger server in a daemon thread."""
    self_url = f"http://localhost:{port}"
    app = create_logger_app(registry_url, self_url)

    def run():
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    # Wait for health
    for _ in range(25):
        try:
            r = httpx.get(f"{self_url}/health", timeout=2.0)
            if r.status_code == 200:
                print(f"[Orchestrator] Logger running at {self_url}")
                return self_url
        except Exception:
            pass
        time.sleep(0.3)

    raise RuntimeError(f"Logger at {self_url} never became healthy")
