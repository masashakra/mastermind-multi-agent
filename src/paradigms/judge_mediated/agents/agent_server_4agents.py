"""
Judge-Mediated Agent HTTP Servers (4-Agent Architecture)
Each team has 4 agents: Analyzer, Strategist, Proposer, Validator
Organized as 2 pairs:
- Pair A: Analyzer → Proposer
- Pair B: Strategist → Validator
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

from paradigms.judge_mediated.agents.analyzer import AnalyzerAgent
from paradigms.judge_mediated.agents.strategist import StrategistAgent
from paradigms.judge_mediated.agents.proposer import ProposerAgent
from paradigms.judge_mediated.agents.validator import ValidatorAgent
from communication.a2a_message import A2AMessage, A2AStatus, A2AErrorCode


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


def create_analyzer_app(provider: str, registry_url: str, self_url: str, team_id: int) -> FastAPI:
    """Create FastAPI app for Analyzer agent."""
    app = FastAPI(title=f"Team {team_id} Analyzer")
    agent = AnalyzerAgent(provider=provider)

    card = {
        "agent_id": f"team-{team_id}-analyzer",
        "agent_name": f"Team {team_id} Analyzer",
        "agent_type": "analyzer",
        "paradigm": "judge_mediated",
        "version": "1.0.0",
        "url": self_url,
        "team_id": team_id,
    }

    @app.on_event("startup")
    def on_startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": f"team-{team_id}-analyzer"}

    @app.post("/analyze")
    def analyze(body: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze feedback and extract constraints."""
        try:
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            result = agent.analyze(
                guess_history=payload.get("guess_history", []),
                last_feedback=payload.get("last_feedback", {}),
                difficulty=payload.get("difficulty", "easy"),
                available_colors=payload.get("available_colors", []),
                num_pegs=payload.get("num_pegs", 4),
            )

            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
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


def create_strategist_app(provider: str, registry_url: str, self_url: str, team_id: int) -> FastAPI:
    """Create FastAPI app for Strategist agent."""
    app = FastAPI(title=f"Team {team_id} Strategist")
    agent = StrategistAgent(provider=provider)

    card = {
        "agent_id": f"team-{team_id}-strategist",
        "agent_name": f"Team {team_id} Strategist",
        "agent_type": "strategist",
        "paradigm": "judge_mediated",
        "version": "1.0.0",
        "url": self_url,
        "team_id": team_id,
    }

    @app.on_event("startup")
    def on_startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": f"team-{team_id}-strategist"}

    @app.post("/strategize")
    def strategize(body: Dict[str, Any]) -> Dict[str, Any]:
        """Develop strategy."""
        try:
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            result = agent.strategize(
                guess_history=payload.get("guess_history", []),
                last_feedback=payload.get("last_feedback", {}),
                current_guess=payload.get("current_guess", []),
                difficulty=payload.get("difficulty", "easy"),
            )

            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
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


def create_proposer_app(provider: str, registry_url: str, self_url: str, team_id: int) -> FastAPI:
    """Create FastAPI app for Proposer agent."""
    app = FastAPI(title=f"Team {team_id} Proposer")
    agent = ProposerAgent(provider=provider)

    card = {
        "agent_id": f"team-{team_id}-proposer",
        "agent_name": f"Team {team_id} Proposer",
        "agent_type": "proposer",
        "paradigm": "judge_mediated",
        "version": "1.0.0",
        "url": self_url,
        "team_id": team_id,
    }

    @app.on_event("startup")
    def on_startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": f"team-{team_id}-proposer"}

    @app.post("/propose")
    def propose(body: Dict[str, Any]) -> Dict[str, Any]:
        """Propose a guess."""
        try:
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            result = agent.propose(
                guess_history=payload.get("guess_history", []),
                analysis=payload.get("analysis", ""),
                constraints=payload.get("constraints", {}),
                available_colors=payload.get("available_colors", []),
                num_pegs=payload.get("num_pegs", 4),
            )

            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
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


def create_validator_app(provider: str, registry_url: str, self_url: str, team_id: int) -> FastAPI:
    """Create FastAPI app for Validator agent."""
    app = FastAPI(title=f"Team {team_id} Validator")
    agent = ValidatorAgent(provider=provider)

    card = {
        "agent_id": f"team-{team_id}-validator",
        "agent_name": f"Team {team_id} Validator",
        "agent_type": "validator",
        "paradigm": "judge_mediated",
        "version": "1.0.0",
        "url": self_url,
        "team_id": team_id,
    }

    @app.on_event("startup")
    def on_startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": f"team-{team_id}-validator"}

    @app.post("/validate")
    def validate(body: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a guess."""
        try:
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            result = agent.validate(
                guess=payload.get("guess", []),
                available_colors=payload.get("available_colors", []),
                num_pegs=payload.get("num_pegs", 4),
                strategy=payload.get("strategy", ""),
            )

            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
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


def start_agent_servers_4agents(
    provider: str,
    registry_url: str,
    team_id: int,
    base_port: int = 8301,
) -> Dict[str, str]:
    """
    Start 4 agent HTTP servers for a specific team.

    Args:
        provider: LLM provider (deepseek, groq, claude, etc.)
        registry_url: Registry server URL
        team_id: Team ID (1, 2, or 3)
        base_port: Base port for team 1

    Returns:
        Dict with URLs: {"analyzer": url, "strategist": url, "proposer": url, "validator": url}
    """
    # Port allocation: Team 1: 8301-8304, Team 2: 8351-8354, Team 3: 8401-8404
    team_base_port = base_port + (team_id - 1) * 50

    analyzer_port = _find_free_port(team_base_port)
    strategist_port = _find_free_port(analyzer_port + 1)
    proposer_port = _find_free_port(strategist_port + 1)
    validator_port = _find_free_port(proposer_port + 1)

    analyzer_url = f"http://localhost:{analyzer_port}"
    strategist_url = f"http://localhost:{strategist_port}"
    proposer_url = f"http://localhost:{proposer_port}"
    validator_url = f"http://localhost:{validator_port}"

    # Create apps
    analyzer_app = create_analyzer_app(provider, registry_url, analyzer_url, team_id)
    strategist_app = create_strategist_app(provider, registry_url, strategist_url, team_id)
    proposer_app = create_proposer_app(provider, registry_url, proposer_url, team_id)
    validator_app = create_validator_app(provider, registry_url, validator_url, team_id)

    # Start servers in threads
    threads = [
        threading.Thread(target=_run_server, args=(analyzer_app, analyzer_port), daemon=True),
        threading.Thread(target=_run_server, args=(strategist_app, strategist_port), daemon=True),
        threading.Thread(target=_run_server, args=(proposer_app, proposer_port), daemon=True),
        threading.Thread(target=_run_server, args=(validator_app, validator_port), daemon=True),
    ]

    for thread in threads:
        thread.start()

    # Wait for all servers to be healthy
    _wait_for_healthy(analyzer_url)
    _wait_for_healthy(strategist_url)
    _wait_for_healthy(proposer_url)
    _wait_for_healthy(validator_url)

    print(f"[AgentServer] Team {team_id} agents running:")
    print(f"  - Analyzer at {analyzer_url}")
    print(f"  - Strategist at {strategist_url}")
    print(f"  - Proposer at {proposer_url}")
    print(f"  - Validator at {validator_url}")

    return {
        "analyzer": analyzer_url,
        "strategist": strategist_url,
        "proposer": proposer_url,
        "validator": validator_url,
    }
