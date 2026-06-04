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
from communication.a2a_message import A2AMessage, A2AStatus, A2AErrorCode


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
        try:
            # ✅ Parse incoming A2AMessage
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            # Log incoming request
            from communication.message_logger import get_message_logger
            _logger = get_message_logger()
            _logger.log_a2a_receive(
                agent_name="Analyzer_BossWorker",
                message_id=request_msg.message_id,
                sender_id=request_msg.sender_id,
                receiver_id="analyzer_boss_worker",
                action="analyze",
                payload=payload,
                is_reply=False,
            )

            # Execute analysis
            result = agent.analyze_feedback(
                last_guess=payload.get("last_guess", []),
                feedback=payload.get("feedback", {}),
                previous_guesses=payload.get("guess_history", []),
            )

            # ✅ Create proper A2A response envelope
            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
            )

            # Log outgoing reply
            _logger.log_a2a_send(
                agent_name="Analyzer_BossWorker",
                message_id=response_msg.message_id,
                sender_id="analyzer_boss_worker",
                receiver_id=request_msg.sender_id,
                action="analyze_reply",
                payload=result,
                is_question=False,
                expects_reply=False,
            )

            return response_msg.to_dict()

        except Exception as e:
            # ✅ Return A2A error response
            error_msg = A2AMessage.error(
                request=A2AMessage.from_dict(body) if body else None,
                error_code=A2AErrorCode.INTERNAL_ERROR,
                error_message=str(e),
                status=A2AStatus.ERROR,
            )
            return error_msg.to_dict()

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

    @app.post("/propose_strategy")
    def propose_strategy(body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # ✅ Parse incoming A2AMessage
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            from communication.message_logger import get_message_logger
            _logger = get_message_logger()
            _logger.log_a2a_receive(
                agent_name="Strategist_BossWorker",
                message_id=request_msg.message_id,
                sender_id=request_msg.sender_id,
                receiver_id="strategist_boss_worker",
                action="propose_strategy",
                payload=payload,
                is_reply=False,
            )

            # Execute strategy
            result = agent.propose_strategy(
                guess_history=payload.get("guess_history", []),
                difficulty=payload.get("difficulty", "easy"),
                analysis=payload.get("analysis", ""),
                impossible_colors=payload.get("impossible_colors", []),
                locked_positions=payload.get("locked_positions", []),
                misplaced_colors=payload.get("misplaced_colors", []),
            )

            # ✅ Create proper A2A response envelope
            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
            )

            _logger.log_a2a_send(
                agent_name="Strategist_BossWorker",
                message_id=response_msg.message_id,
                sender_id="strategist_boss_worker",
                receiver_id=request_msg.sender_id,
                action="propose_strategy_reply",
                payload=result,
                is_question=False,
                expects_reply=False,
            )

            return response_msg.to_dict()

        except Exception as e:
            # ✅ Return A2A error response
            error_msg = A2AMessage.error(
                request=A2AMessage.from_dict(body) if body else None,
                error_code=A2AErrorCode.INTERNAL_ERROR,
                error_message=str(e),
                status=A2AStatus.ERROR,
            )
            return error_msg.to_dict()

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

    @app.post("/propose_guess")
    def propose_guess(body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # ✅ Parse incoming A2AMessage
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            from communication.message_logger import get_message_logger
            _logger = get_message_logger()
            _logger.log_a2a_receive(
                agent_name="Proposer_BossWorker",
                message_id=request_msg.message_id,
                sender_id=request_msg.sender_id,
                receiver_id="proposer_boss_worker",
                action="propose_guess",
                payload=payload,
                is_reply=False,
            )

            # Execute proposal
            result = agent.propose_guess(
                guess_history=payload.get("guess_history", []),
                available_colors=payload.get("available_colors", []),
                difficulty=payload.get("difficulty", "easy"),
                strategy=payload.get("strategy", {}),
                analysis=payload.get("analysis", {}),
                num_pegs=payload.get("num_pegs", 4),
            )

            # ✅ Create proper A2A response envelope
            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
            )

            _logger.log_a2a_send(
                agent_name="Proposer_BossWorker",
                message_id=response_msg.message_id,
                sender_id="proposer_boss_worker",
                receiver_id=request_msg.sender_id,
                action="propose_guess_reply",
                payload=result,
                is_question=False,
                expects_reply=False,
            )

            return response_msg.to_dict()

        except Exception as e:
            # ✅ Return A2A error response
            error_msg = A2AMessage.error(
                request=A2AMessage.from_dict(body) if body else None,
                error_code=A2AErrorCode.INTERNAL_ERROR,
                error_message=str(e),
                status=A2AStatus.ERROR,
            )
            return error_msg.to_dict()

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
        try:
            # ✅ Parse incoming A2AMessage
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            from communication.message_logger import get_message_logger
            _logger = get_message_logger()
            _logger.log_a2a_receive(
                agent_name="Validator_BossWorker",
                message_id=request_msg.message_id,
                sender_id=request_msg.sender_id,
                receiver_id="validator_boss_worker",
                action="validate",
                payload=payload,
                is_reply=False,
            )

            # Execute validation
            result = agent.validate_guess(
                proposed_guess=payload.get("proposed_guess", []),
                guess_history=payload.get("guess_history", []),
                analysis=payload.get("analysis", {}),
                num_pegs=payload.get("num_pegs", 4),
            )

            # ✅ Create proper A2A response envelope
            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
            )

            _logger.log_a2a_send(
                agent_name="Validator_BossWorker",
                message_id=response_msg.message_id,
                sender_id="validator_boss_worker",
                receiver_id=request_msg.sender_id,
                action="validate_reply",
                payload=result,
                is_question=False,
                expects_reply=False,
            )

            return response_msg.to_dict()

        except Exception as e:
            # ✅ Return A2A error response
            error_msg = A2AMessage.error(
                request=A2AMessage.from_dict(body) if body else None,
                error_code=A2AErrorCode.INTERNAL_ERROR,
                error_message=str(e),
                status=A2AStatus.ERROR,
            )
            return error_msg.to_dict()

    return app


# ── Launch helpers ─────────────────────────────────────────────────────────────

def _run_server(app: FastAPI, port: int) -> None:
    """Run server."""
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")


def _find_free_port(start_port: int = 8201, max_attempts: int = 100) -> int:
    """Find a free port starting from start_port."""
    import socket as sock_module
    for port in range(start_port, start_port + max_attempts):
        try:
            sock = sock_module.socket(sock_module.AF_INET, sock_module.SOCK_STREAM)
            sock.bind(("0.0.0.0", port))
            sock.close()
            return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find free port in range {start_port}-{start_port + max_attempts}")


def start_agent_servers(
    provider: str,
    registry_url: str,
    base_port: int = 8201,  # Boss-Worker uses 8200s (different from round-table 8100s)
) -> Dict[str, str]:
    """
    Start all 4 agent HTTP servers in daemon threads.
    Dynamically allocates ports to avoid TIME_WAIT conflicts.
    Returns a dict mapping agent_type → URL.
    """
    # Dynamically find free ports to avoid TIME_WAIT conflicts on rapid restarts
    configs = [
        ("analyzer",   create_analyzer_app),
        ("strategist", create_strategist_app),
        ("proposer",   create_proposer_app),
        ("validator",  create_validator_app),
    ]

    urls = {}
    current_port = base_port

    for agent_type, factory_fn in configs:
        # Find next available port
        port = _find_free_port(current_port)
        current_port = port + 1  # Next search starts after this port

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
