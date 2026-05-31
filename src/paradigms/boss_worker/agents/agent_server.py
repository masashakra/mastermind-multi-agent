"""
Boss-Worker Agent HTTP Servers
Each agent type (Analyzer, Strategist, Proposer, Validator) runs as an
independent FastAPI HTTP server. On startup each server registers its URL
and agent card with the registry so the Boss can discover it.

Endpoints per agent:
    GET  /health                → liveness check
    GET  /.well-known/agent.json → agent card (A2A discovery standard)
    POST /analyze               → Analyzer
    POST /strategy              → Strategist
    POST /propose               → Proposer
    POST /validate              → Validator
"""

import sys
import time
import threading
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI
from typing import Dict, Any

# ── path setup ───────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from paradigms.boss_worker.agents.analyzer import AnalyzerAgent, AGENT_CARD as ANALYZER_CARD
from paradigms.boss_worker.agents.strategist import StrategistAgent, AGENT_CARD as STRATEGIST_CARD
from paradigms.boss_worker.agents.proposer import ProposerAgent, AGENT_CARD as PROPOSER_CARD
from paradigms.boss_worker.agents.validator import ValidatorAgent, AGENT_CARD as VALIDATOR_CARD
from base.agent_card_schema import A2ACapability


# ── shared helpers ────────────────────────────────────────────────────────────

def _convert_card_to_a2a(card: Dict[str, Any]) -> Dict[str, Any]:
    """Convert old-format agent card to A2A schema format."""
    capabilities = []

    # Convert capabilities from dict to list of A2ACapability objects
    if isinstance(card.get("capabilities"), dict):
        for cap_name, cap_spec in card["capabilities"].items():
            capabilities.append({
                "name": cap_name,
                "description": cap_spec.get("description", ""),
                "input_schema": cap_spec.get("parameters", {}),
                "output_schema": cap_spec.get("returns", {}),
                "timeout_seconds": 30,
            })

    # Return A2A format with capabilities list
    return {
        "agent_id": card.get("agent_id"),
        "agent_name": card.get("agent_name"),
        "agent_type": card.get("agent_type"),
        "paradigm": card.get("paradigm"),
        "version": card.get("version", "1.0.0"),
        "description": card.get("description", ""),
        "url": card.get("url", ""),
        "health_endpoint": "/health",
        "capabilities": capabilities,
        "constraints_owned": card.get("constraints_owned", []),
        "team_members": card.get("team_members", []),
        "can_communicate": card.get("can_communicate", True),
    }


def _wait_for_healthy(url: str, retries: int = 25, delay: float = 0.3) -> None:
    for _ in range(retries):
        try:
            r = httpx.get(f"{url}/health", timeout=2.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(delay)
    raise RuntimeError(f"Agent server at {url} never became healthy")


def _register_with_registry(registry_url: str, card: Dict[str, Any]) -> None:
    """POST the agent card (+ self URL) to the registry."""
    for attempt in range(10):
        try:
            r = httpx.post(f"{registry_url}/register", json=card, timeout=5.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError(f"Could not register agent {card.get('agent_id')} with registry")


# ── Analyzer server ───────────────────────────────────────────────────────────

def create_analyzer_app(provider: str, registry_url: str, self_url: str) -> FastAPI:
    app = FastAPI(title="Analyzer Agent")
    agent = AnalyzerAgent(provider=provider)
    card = _convert_card_to_a2a({**ANALYZER_CARD, "url": self_url, "agent_type": "analyzer"})

    @app.on_event("startup")
    def on_startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": "analyzer"}

    @app.get("/.well-known/agent.json")
    def agent_card():
        return card

    @app.post("/analyze")
    def analyze(body: Dict[str, Any]) -> Dict[str, Any]:
        return agent.analyze_feedback(
            last_guess=body.get("last_guess", []),
            feedback=body.get("feedback", {}),
            previous_guesses=body.get("previous_guesses", []),
        )

    return app


# ── Strategist server ─────────────────────────────────────────────────────────

def create_strategist_app(provider: str, registry_url: str, self_url: str) -> FastAPI:
    app = FastAPI(title="Strategist Agent")
    agent = StrategistAgent(provider=provider)
    card = _convert_card_to_a2a({**STRATEGIST_CARD, "url": self_url, "agent_type": "strategist"})

    @app.on_event("startup")
    def on_startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": "strategist"}

    @app.get("/.well-known/agent.json")
    def agent_card():
        return card

    @app.post("/strategy")
    def strategy(body: Dict[str, Any]) -> Dict[str, Any]:
        return agent.propose_strategy(
            guess_history=body.get("guess_history", []),
            difficulty=body.get("difficulty", "easy"),
        )

    return app


# ── Proposer server ───────────────────────────────────────────────────────────

def create_proposer_app(provider: str, registry_url: str, self_url: str) -> FastAPI:
    app = FastAPI(title="Proposer Agent")
    agent = ProposerAgent(provider=provider)
    card = _convert_card_to_a2a({**PROPOSER_CARD, "url": self_url, "agent_type": "proposer"})

    @app.on_event("startup")
    def on_startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": "proposer"}

    @app.get("/.well-known/agent.json")
    def agent_card():
        return card

    @app.post("/propose")
    def propose(body: Dict[str, Any]) -> Dict[str, Any]:
        return agent.propose_guess(
            strategy=body.get("strategy", ""),
            constraints_text=body.get("constraints_text", ""),
            available_colors=body.get("available_colors", []),
            num_pegs=body.get("num_pegs", 4),
            previous_guesses=body.get("previous_guesses", []),
        )

    return app


# ── Validator server ──────────────────────────────────────────────────────────

def create_validator_app(provider: str, registry_url: str, self_url: str) -> FastAPI:
    app = FastAPI(title="Validator Agent")
    agent = ValidatorAgent(provider=provider)
    card = _convert_card_to_a2a({**VALIDATOR_CARD, "url": self_url, "agent_type": "validator"})

    @app.on_event("startup")
    def on_startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": "validator"}

    @app.get("/.well-known/agent.json")
    def agent_card():
        return card

    @app.post("/validate")
    def validate(body: Dict[str, Any]) -> Dict[str, Any]:
        return agent.validate_guess(
            guess=body.get("guess", []),
            available_colors=body.get("available_colors", []),
            expected_length=body.get("expected_length", 4),
            previous_guesses=body.get("previous_guesses", []),
            constraints=body.get("constraints", {}),
        )

    return app


# ── Launch helpers ─────────────────────────────────────────────────────────────

def _run_server(app: FastAPI, port: int) -> None:
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")


def start_agent_servers(
    provider: str,
    registry_url: str,
    base_port: int = 8101,
) -> Dict[str, str]:
    """
    Start all 4 agent HTTP servers in daemon threads.
    Returns a dict mapping agent_type → URL.
    """
    configs = [
        ("analyzer",   create_analyzer_app,   base_port),
        ("strategist", create_strategist_app, base_port + 1),
        ("proposer",   create_proposer_app,   base_port + 2),
        ("validator",  create_validator_app,  base_port + 3),
    ]

    urls = {}
    for agent_type, factory_fn, port in configs:
        self_url = f"http://localhost:{port}"
        app = factory_fn(provider, registry_url, self_url)
        thread = threading.Thread(
            target=_run_server,
            args=(app, port),
            daemon=True,
        )
        thread.start()
        _wait_for_healthy(self_url)
        urls[agent_type] = self_url
        print(f"[AgentServer] {agent_type} running at {self_url}")

    return urls
