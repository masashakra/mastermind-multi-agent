"""
Judge-Mediated Agent HTTP Server (Simplified)
One unified TeamAgent per team - handles analysis, strategy, and proposal in one call.

Team-aware agent_id format: team-{team_id}
Example: team-1, team-2, team-3
"""

import sys
import time
import socket
import threading
from pathlib import Path
from typing import Dict, Any

import httpx
import uvicorn
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from paradigms.judge_mediated.agents.team_agent import TeamAgent, AGENT_CARD
from communication.a2a_message import A2AMessage, A2AStatus, A2AErrorCode


def _convert_card_to_a2a(card: Dict[str, Any], team_id: int) -> Dict[str, Any]:
    """Convert agent card to A2A schema format with team awareness."""
    capabilities = []
    if isinstance(card.get("capabilities"), dict):
        for cap_name, cap_spec in card["capabilities"].items():
            capabilities.append({
                "name": cap_name,
                "description": cap_spec.get("description", ""),
                "input_schema": cap_spec.get("parameters", {}),
                "output_schema": cap_spec.get("returns", {}),
                "timeout_seconds": 30,
            })

    return {
        "agent_id": f"team-{team_id}",
        "agent_name": f"Team {team_id} Agent",
        "agent_type": "team_agent",
        "paradigm": card.get("paradigm"),
        "version": card.get("version", "1.0.0"),
        "description": card.get("description", ""),
        "url": card.get("url", ""),
        "health_endpoint": "/health",
        "capabilities": capabilities,
        "constraints_owned": card.get("constraints_owned", []),
        "team_members": card.get("team_members", []),
        "can_communicate": card.get("can_communicate", True),
        "team_id": team_id,
    }


def _wait_for_healthy(url: str, retries: int = 25, delay: float = 0.3) -> None:
    """Wait for agent server to become healthy."""
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
    """Register agent with registry."""
    for attempt in range(10):
        try:
            r = httpx.post(f"{registry_url}/register", json=card, timeout=5.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError(f"Could not register agent {card.get('agent_id')} with registry")


def create_team_agent_app(provider: str, registry_url: str, self_url: str, team_id: int) -> FastAPI:
    """Create FastAPI app for one team agent."""
    app = FastAPI(title=f"Team {team_id} Agent")
    agent = TeamAgent(provider=provider)

    card = _convert_card_to_a2a({**AGENT_CARD, "url": self_url}, team_id)

    @app.on_event("startup")
    def on_startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": f"team-{team_id}", "team_id": team_id}

    @app.get("/.well-known/agent.json")
    def agent_card():
        return card

    @app.post("/solve_round")
    def solve_round(body: Dict[str, Any]) -> Dict[str, Any]:
        """Solve one round: analyze, strategize, and propose guess."""
        try:
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            from communication.message_logger import get_message_logger
            _logger = get_message_logger()
            _logger.log_a2a_receive(
                agent_name=f"Team{team_id}",
                message_id=request_msg.message_id,
                sender_id=request_msg.sender_id,
                receiver_id=f"team-{team_id}",
                action="solve_round",
                payload=payload,
                is_reply=False,
            )

            # Call agent to solve round
            result = agent.solve_round(
                guess_history=payload.get("guess_history", []),
                constraint_history=payload.get("constraint_history", []),  # NEW: Pass constraints (boss-worker style!)
                last_feedback=payload.get("last_feedback", {}),
                difficulty=payload.get("difficulty", "easy"),
                available_colors=payload.get("available_colors", []),
                num_pegs=payload.get("num_pegs", 4),
            )

            # Create response
            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
            )

            _logger.log_a2a_send(
                agent_name=f"Team{team_id}",
                message_id=response_msg.message_id,
                sender_id=f"team-{team_id}",
                receiver_id=request_msg.sender_id,
                action="solve_round_reply",
                payload=result,
                is_question=False,
                expects_reply=False,
            )

            return response_msg.to_dict()

        except Exception as e:
            error_msg = A2AMessage.error(
                request=A2AMessage.from_dict(body) if body else None,
                error_code=A2AErrorCode.INTERNAL_ERROR,
                error_message=str(e),
                status=A2AStatus.ERROR,
            )
            return error_msg.to_dict()

    return app


def _run_server(app: FastAPI, port: int) -> None:
    """Run FastAPI server."""
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")


def _find_free_port(start_port: int = 8301, max_attempts: int = 100) -> int:
    """Find a free port."""
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
    team_id: int,
    base_port: int = 8301,
) -> str:
    """
    Start one TeamAgent HTTP server for a specific team.

    Args:
        provider: LLM provider (deepseek, groq, claude, etc.)
        registry_url: Registry server URL
        team_id: Team ID (1, 2, or 3)
        base_port: Base port for team 1

    Returns:
        URL of the running agent server
    """
    # Find free port for this team
    team_base_port = base_port + (team_id - 1) * 50  # Team 1: 8301, Team 2: 8351, Team 3: 8401
    port = _find_free_port(team_base_port)

    self_url = f"http://localhost:{port}"
    app = create_team_agent_app(provider, registry_url, self_url, team_id)

    thread = threading.Thread(
        target=_run_server,
        args=(app, port),
        daemon=True,
    )
    thread.start()
    _wait_for_healthy(self_url)
    print(f"[AgentServer] Team {team_id} agent running at {self_url}")

    return self_url
