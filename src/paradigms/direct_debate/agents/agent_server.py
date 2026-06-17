"""
Direct Debate Agent HTTP Servers — Two agents per team (2v2)

Each team has 2 agents:
  - Analyser-Strategist: Analyzes patterns, develops strategy, debates with other teams
  - Solver: Generates guesses, submits to orchestrator

For multiple teams:
  Team 1: Analyser → port 8301, Solver → port 8302
  Team 2: Analyser → port 8303, Solver → port 8304

Endpoints:
  Analyser-Strategist:
    GET  /health                  → liveness check
    GET  /.well-known/agent.json  → agent card
    POST /analyze                 → Analyze patterns + develop strategy
    POST /debate                  → Debate with other analyser-strategists
    POST /receive_message         → Receive A2A debate message

  Solver:
    GET  /health                  → liveness check
    GET  /.well-known/agent.json  → agent card
    POST /solve_round             → Generate guess based on strategy
"""

import sys
import time
import threading
import socket
import asyncio
import multiprocessing
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from paradigms.direct_debate.agents.solver import Solver, AGENT_CARD as SOLVER_CARD
from paradigms.direct_debate.agents.analyser_strategist import AnalyserStrategist, AGENT_CARD as ANALYSER_CARD
from base.agent_card_schema import A2ACapability
from communication.a2a_message import A2AMessage, A2AStatus, A2AErrorCode


def _find_free_port(start_port: int = 8300) -> int:
    """Find next available port."""
    for port in range(start_port, start_port + 100):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", port))
            sock.close()
            return port
        except OSError:
            continue
    raise RuntimeError("No available ports")


async def asyncio_run_server(app: FastAPI, port: int) -> None:
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)
    await server.serve()


def _convert_card_to_a2a(card: Dict[str, Any]) -> Dict[str, Any]:
    """Convert old-format agent card to A2A schema format."""
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
    """POST the agent card to the registry."""
    for attempt in range(20):  # Increased from 10 to 20
        try:
            r = httpx.post(f"{registry_url}/register", json=card, timeout=5.0)
            if r.status_code == 200:
                return
        except Exception as e:
            pass
        time.sleep(0.5)  # Increased from 0.4 to 0.5
    raise RuntimeError(f"Could not register agent {card.get('agent_id')} with registry")


# ── Subprocess entry points (must be top-level for multiprocessing pickling) ──

def _subprocess_solver(provider: str, registry_url: str, self_url: str, team_id: str, port: int, src_path: str):
    """Run a Solver server in an isolated subprocess."""
    import sys
    sys.path.insert(0, src_path)
    from paradigms.direct_debate.agents.agent_server import create_solver_app
    import uvicorn, asyncio
    app = create_solver_app(provider, registry_url, self_url, team_id)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def _subprocess_analyser(provider: str, registry_url: str, self_url: str, team_id: str, solver_url: str, port: int, src_path: str):
    """Run an Analyser-Strategist server in an isolated subprocess."""
    import sys
    sys.path.insert(0, src_path)
    from paradigms.direct_debate.agents.agent_server import create_analyser_strategist_app
    import uvicorn, asyncio
    app = create_analyser_strategist_app(provider, registry_url, self_url, team_id, solver_url)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


# ── Agent server factory functions ──────────────────────────────────────────

def create_solver_app(
    provider: str, registry_url: str, self_url: str, team_id: str
) -> FastAPI:
    """Create FastAPI app for Solver agent."""
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    app = FastAPI(title=f"Solver {team_id}")
    agent = Solver(provider=provider, team_id=team_id)
    card = _convert_card_to_a2a({
        **SOLVER_CARD,
        "url": self_url,
        "agent_id": f"solver_{team_id}",
        "agent_name": f"Solver {team_id}",
    })

    # Log every incoming request so we can see what's hitting the solver
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        print(f"[Solver {team_id}] → {request.method} {request.url.path}", flush=True)
        response = await call_next(request)
        print(f"[Solver {team_id}] ← {response.status_code} {request.url.path}", flush=True)
        return response

    @app.on_event("startup")
    def on_startup():
        print(f"[Solver] on_startup: Registering {team_id}...", flush=True)
        try:
            _register_with_registry(registry_url, card)
            print(f"[Solver] on_startup: Successfully registered {team_id}", flush=True)
        except Exception as e:
            print(f"[Solver] on_startup: ERROR registering {team_id}: {e}", flush=True)
            raise

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": f"solver_{team_id}"}

    @app.get("/.well-known/agent.json")
    def agent_card():
        return card

    @app.post("/solve_round")
    def solve_round(body: Dict[str, Any]) -> Dict[str, Any]:
        """Receive A2A message from Analyser-Strategist, return A2A response with guess."""
        try:
            # Unwrap A2A envelope
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload
            print(f"[Solver {team_id}] Received A2A solve_round from {request_msg.sender_id}, history_len={len(payload.get('guess_history', []))}", flush=True)

            result = agent.solve_round(
                guess_history=payload.get("guess_history", []),
                difficulty=payload.get("difficulty", "easy"),
                available_colors=payload.get("available_colors", []),
                num_pegs=payload.get("num_pegs", 4),
                strategy=payload.get("strategy", ""),
            )
            print(f"[Solver {team_id}] Guess: {result.get('guess')}", flush=True)

            # Wrap in A2A response
            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True,
            )
            return response_msg.to_dict()

        except Exception as e:
            import traceback
            print(f"[Solver {team_id}] ERROR in solve_round: {e}", flush=True)
            traceback.print_exc()
            error_msg = A2AMessage.error(
                request=A2AMessage.from_dict(body) if body else None,
                error_code=A2AErrorCode.INTERNAL_ERROR,
                error_message=str(e),
                status=A2AStatus.ERROR,
            )
            return error_msg.to_dict()

    return app


def create_analyser_strategist_app(
    provider: str, registry_url: str, self_url: str, team_id: str, solver_url: str
) -> FastAPI:
    """Create FastAPI app for Analyser-Strategist agent."""
    app = FastAPI(title=f"AnalyserStrategist {team_id}")
    agent = AnalyserStrategist(provider=provider, team_id=team_id)
    agent.solver_url = solver_url  # Link to team's solver

    card = _convert_card_to_a2a({
        **ANALYSER_CARD,
        "url": self_url,
        "agent_id": f"analyser_{team_id}",
        "agent_name": f"Analyser-Strategist {team_id}",
    })

    @app.on_event("startup")
    def on_startup():
        print(f"[AnalyserStrategist] on_startup: Registering {team_id}...", flush=True)
        try:
            _register_with_registry(registry_url, card)
            print(f"[AnalyserStrategist] on_startup: Successfully registered {team_id}", flush=True)
        except Exception as e:
            print(f"[AnalyserStrategist] on_startup: ERROR registering {team_id}: {e}", flush=True)
            raise

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": f"analyser_{team_id}"}

    @app.get("/.well-known/agent.json")
    def agent_card():
        return card

    @app.post("/analyze")
    def analyze(body: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns and develop strategy."""
        try:
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            from communication.message_logger import get_message_logger
            _logger = get_message_logger()
            _logger.log_a2a_receive(
                agent_name=f"AnalyserStrategist_{team_id}",
                message_id=request_msg.message_id,
                sender_id=request_msg.sender_id,
                receiver_id=f"analyser_{team_id}",
                action="analyze",
                payload=payload,
                is_reply=False,
            )

            result = agent.analyze_and_strategize(
                guess_history=payload.get("guess_history", []),
                difficulty=payload.get("difficulty", "easy"),
                available_colors=payload.get("available_colors", []),
                num_pegs=payload.get("num_pegs", 4),
                public_leaderboard=payload.get("public_leaderboard", []),
            )

            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
            )

            _logger.log_a2a_send(
                agent_name=f"AnalyserStrategist_{team_id}",
                message_id=response_msg.message_id,
                sender_id=f"analyser_{team_id}",
                receiver_id=request_msg.sender_id,
                action="analyze_reply",
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

    @app.post("/receive_message")
    def receive_message(body: Dict[str, Any]) -> Dict[str, Any]:
        """Receive A2A debate message from another analyser-strategist."""
        try:
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            from communication.message_logger import get_message_logger
            _logger = get_message_logger()
            _logger.log_a2a_receive(
                agent_name=f"AnalyserStrategist_{team_id}",
                message_id=request_msg.message_id,
                sender_id=request_msg.sender_id,
                receiver_id=f"analyser_{team_id}",
                action="receive_debate_statement",
                payload=payload,
                is_reply=False,
            )

            sender = request_msg.sender_id
            message = payload.get("message", "")
            round_num = payload.get("round", 0)
            agent.receive_peer_message(sender, message, round_num)

            return {"status": "received"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @app.post("/debate")
    def debate(body: Dict[str, Any]) -> Dict[str, Any]:
        """Debate with other teams' analyser-strategists."""
        try:
            request_msg = A2AMessage.from_dict(body)
            payload = request_msg.payload

            from communication.message_logger import get_message_logger
            _logger = get_message_logger()
            _logger.log_a2a_receive(
                agent_name=f"AnalyserStrategist_{team_id}",
                message_id=request_msg.message_id,
                sender_id=request_msg.sender_id,
                receiver_id=f"analyser_{team_id}",
                action="debate",
                payload=payload,
                is_reply=False,
            )

            result = agent.debate(
                round_number=payload.get("round_number", 1),
                my_result=payload.get("my_result", {}),
                all_results=payload.get("all_results", {}),
            )

            response_msg = A2AMessage.response(
                request=request_msg,
                payload=result,
                status=A2AStatus.OK,
                is_reply=True
            )

            _logger.log_a2a_send(
                agent_name=f"AnalyserStrategist_{team_id}",
                message_id=response_msg.message_id,
                sender_id=f"analyser_{team_id}",
                receiver_id=request_msg.sender_id,
                action="debate_reply",
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

    @app.post("/start_puzzle")
    def start_puzzle(body: Dict[str, Any]) -> Dict[str, Any]:
        """Start autonomous puzzle solving (runs solver loop)."""
        try:
            puzzle = body.get("puzzle", {})
            registry_url = body.get("registry_url", "")
            orchestrator_url = body.get("orchestrator_url", "")
            log_file = body.get("log_file", "")

            # Run autonomous loop in background
            def run_loop():
                try:
                    run_team_autonomous_loop(
                        team_id=team_id,
                        analyser=agent,
                        solver_url=agent.solver_url,
                        puzzle=puzzle,
                        registry_url=registry_url,
                        orchestrator_url=orchestrator_url,
                        log_file=log_file,
                    )
                except Exception as _e:
                    import traceback
                    print(f"[{team_id}] LOOP CRASHED: {_e}", flush=True)
                    traceback.print_exc()

            thread = threading.Thread(target=run_loop, daemon=True)
            thread.start()

            return {"status": "started", "team": team_id}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    return app


def run_team_autonomous_loop(
    team_id: str,
    analyser: AnalyserStrategist,
    solver_url: str,
    puzzle: Dict[str, Any],
    registry_url: str,
    orchestrator_url: str,
    log_file: str = "",
) -> None:
    """Run the autonomous loop: analyser → solver → submit → reflect → debate."""
    try:
        _run_team_autonomous_loop_inner(team_id, analyser, solver_url, puzzle, registry_url, orchestrator_url, log_file)
    except Exception as e:
        import traceback
        print(f"[{team_id}] FATAL ERROR in autonomous loop: {e}", flush=True)
        traceback.print_exc()


def _run_team_autonomous_loop_inner(
    team_id: str,
    analyser: AnalyserStrategist,
    solver_url: str,
    puzzle: Dict[str, Any],
    registry_url: str,
    orchestrator_url: str,
    log_file: str = "",
) -> None:
    """Inner loop — wrapped by run_team_autonomous_loop for crash catching."""
    analyser.registry_url = registry_url
    analyser.orchestrator_url = orchestrator_url
    analyser.puzzle = puzzle

    # Initialize message logger in this subprocess with the shared log file
    from communication.message_logger import init_message_logger
    _logger = init_message_logger(log_file) if log_file else None

    available_colors = puzzle.get("available_colors", [])
    num_pegs = puzzle.get("pegs", 4)
    difficulty = puzzle.get("difficulty", "easy")

    print(f"[{team_id}] Starting autonomous puzzle solving...")

    guess_history = []
    public_leaderboard = []
    max_rounds = 16

    for round_num in range(1, max_rounds + 1):
        print(f"\n[{team_id}] Round {round_num}")

        # Step 1: ANALYSER develops strategy
        analysis_result = analyser.analyze_and_strategize(
            guess_history=guess_history,
            difficulty=difficulty,
            available_colors=available_colors,
            num_pegs=num_pegs,
            public_leaderboard=public_leaderboard,
        )

        strategy = analysis_result.get("strategy", "")
        print(f"[{team_id}] Strategy: {strategy[:100]}...")

        # Step 2: ANALYSER sends A2A request to SOLVER
        try:
            # Build A2A request from analyser to solver
            solver_request = A2AMessage.request(
                sender_id=f"analyser_{team_id}",
                receiver_id=f"solver_{team_id}",
                action="solve_round",
                payload={
                    "guess_history": guess_history,
                    "difficulty": difficulty,
                    "available_colors": available_colors,
                    "num_pegs": num_pegs,
                    "strategy": strategy,
                },
            )

            # Log: Analyser → Solver (outgoing)
            if _logger:
                _logger.log_a2a_send(
                    agent_name=f"AnalyserStrategist_{team_id}",
                    message_id=solver_request.message_id,
                    sender_id=f"analyser_{team_id}",
                    receiver_id=f"solver_{team_id}",
                    action="solve_round",
                    payload={"strategy": strategy[:300], "round": round_num},
                    is_question=True,
                    expects_reply=True,
                )

            print(f"[{team_id}] Analyser → Solver A2A: solve_round (round {round_num})", flush=True)
            resp = httpx.post(
                f"{solver_url}/solve_round",
                json=solver_request.to_dict(),
                timeout=180.0  # Increased from 90s to allow LLM calls (up to 90s) + HTTP overhead
            )
            if resp.status_code != 200:
                print(f"[{team_id}] Solver HTTP {resp.status_code}: {resp.text[:500]}", flush=True)
                continue

            # Unwrap A2A response
            solver_response = A2AMessage.from_dict(resp.json())
            guess = solver_response.payload.get("guess", [])
            print(f"[{team_id}] Solver → Analyser A2A: guess={guess}", flush=True)

            # Log: Solver → Analyser (reply)
            if _logger:
                _logger.log_a2a_receive(
                    agent_name=f"AnalyserStrategist_{team_id}",
                    message_id=solver_response.message_id,
                    sender_id=f"solver_{team_id}",
                    receiver_id=f"analyser_{team_id}",
                    action="solve_round_reply",
                    payload={"guess": guess, "reasoning": solver_response.payload.get("reasoning", "")[:200]},
                    is_reply=True,
                    reply_to_id=solver_request.message_id,
                )

        except Exception as e:
            print(f"[{team_id}] A2A Analyser→Solver failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            continue  # Skip round instead of breaking entirely

        if not guess:
            print(f"[{team_id}] Failed to generate valid guess")
            break

        print(f"[{team_id}] Proposed: {guess}")

        # Step 3: Submit guess to orchestrator
        feedback = _submit_guess_to_orchestrator(team_id, guess, orchestrator_url)

        if feedback and feedback.get("valid", False):
            guess_result = feedback.get("feedback", {})
            guess_history.append({
                "round": round_num,
                "guess": guess,
                "feedback": guess_result,
            })

            # Step 4: ANALYSER reflects on feedback
            analyser.reflect_on_round(round_num, guess, guess_result)

            # Update public leaderboard
            if "public_leaderboard" in feedback:
                public_leaderboard = feedback.get("public_leaderboard", [])

            # Check if solved
            if feedback.get("solved", False):
                print(f"[{team_id}] ✓ SOLVED!")
                break
        else:
            print(f"[{team_id}] Guess rejected: {feedback}")
            break

        # Step 5: Discover peers and debate
        peers = _discover_peers(team_id, registry_url)
        if peers:
            _debate_with_peers(
                team_id=team_id,
                analyser=analyser,
                peers=peers,
                round_num=round_num,
                my_result={"guess": guess, "feedback": guess_result},
                all_guesses=guess_history,
                logger=_logger,
            )


def _submit_guess_to_orchestrator(
    team_id: str, guess: List[str], orchestrator_url: str
) -> Dict[str, Any]:
    """Submit guess to orchestrator for validation."""
    if not orchestrator_url:
        return {"valid": False, "error": "No orchestrator URL"}

    try:
        resp = httpx.post(
            f"{orchestrator_url}/submit_guess",
            json={"team_id": team_id, "guess": guess},
            timeout=10.0
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"valid": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        print(f"[{team_id}] Failed to submit guess: {e}")
        return {"valid": False, "error": str(e)}


def _discover_peers(team_id: str, registry_url: str) -> Dict[str, str]:
    """Discover other team's analyser-strategists from registry."""
    if not registry_url:
        return {}

    try:
        resp = httpx.get(f"{registry_url}/agents", timeout=5.0)
        if resp.status_code != 200:
            return {}

        data = resp.json()
        agents_list = data.get("payload", {}).get("agents", [])
        peers = {}

        for agent_data in agents_list:
            agent_id = agent_data.get("agent_id", "")
            url = agent_data.get("url", "")

            # Find OTHER teams' ANALYSER agents
            if "analyser_" in agent_id and team_id not in agent_id:
                peers[agent_id] = url

        return peers
    except Exception as e:
        print(f"[{team_id}] Failed to discover peers: {e}")
        return {}


def _debate_with_peers(
    team_id: str,
    analyser: AnalyserStrategist,
    peers: Dict[str, str],
    round_num: int,
    my_result: Dict[str, Any],
    all_guesses: List[Dict[str, Any]],
    logger=None,
) -> None:
    """Analyser sends debate messages to peer analysers via A2A."""
    if not peers:
        return

    my_guess = my_result.get("guess", [])
    my_feedback = my_result.get("feedback", {})

    # Format all results for debate context
    all_results = {}
    for guess_entry in all_guesses:
        all_results[guess_entry["team_id"] if "team_id" in guess_entry else team_id] = {
            "guess": guess_entry.get("guess", []),
            "feedback": guess_entry.get("feedback", {}),
        }

    # Get debate response from analyser LLM
    debate_result = analyser.debate(
        round_number=round_num,
        my_result=my_result,
        all_results=all_results,
    )

    message = debate_result.get("debate_message", f"Round {round_num}")
    print(f"[{team_id}] Debate: {message}")

    # Send to each peer ANALYSER via A2A
    from communication.a2a_message import A2AMessage
    for peer_id, peer_url in peers.items():
        msg = A2AMessage.request(
            sender_id=f"analyser_{team_id}",
            receiver_id=peer_id,
            action="debate_statement",
            payload={"message": message, "round": round_num,
                     "my_feedback": my_feedback, "my_guess": my_guess},
        )

        # Log: outgoing debate message
        if logger:
            logger.log_a2a_send(
                agent_name=f"AnalyserStrategist_{team_id}",
                message_id=msg.message_id,
                sender_id=f"analyser_{team_id}",
                receiver_id=peer_id,
                action="debate_statement",
                payload={"message": message, "round": round_num},
                is_question=False,
                expects_reply=False,
            )

        try:
            httpx.post(f"{peer_url}/receive_message", json=msg.to_dict(), timeout=5.0)
        except Exception as e:
            print(f"[{team_id}] Failed to send to {peer_id}: {e}")


# ── Server orchestration ──────────────────────────────────────────────────────

def start_agent_servers(
    provider: str,
    registry_url: str,
    base_port: int = 8501,  # 8501+ — avoids conflict with boss_worker (8201)
    num_teams: int = 2,
    orchestrator_url: str = "",
) -> Dict[str, str]:
    """
    Start 2 agents per team (Analyser-Strategist + Solver).
    For 2 teams: 4 agents total with ports 8301-8304.

    Team 1: Analyser (8301) + Solver (8302)
    Team 2: Analyser (8303) + Solver (8304)

    Returns dict mapping analyser_team_id → analyser_url (orchestrator uses this to send /start_puzzle).
    """
    # Use spawn context so each subprocess has a clean Python interpreter (required on macOS)
    ctx = multiprocessing.get_context("spawn")
    src_path = str(Path(__file__).parent.parent.parent.parent)
    _processes = []  # keep references so they aren't GC'd

    team_urls = {}
    current_port = base_port

    for team_num in range(num_teams):
        team_id = f"team_{team_num + 1}"

        # Step 1: Start SOLVER in its own process
        solver_port = _find_free_port(current_port)
        current_port = solver_port + 1
        solver_url = f"http://localhost:{solver_port}"

        solver_proc = ctx.Process(
            target=_subprocess_solver,
            args=(provider, registry_url, solver_url, team_id, solver_port, src_path),
            daemon=True,
        )
        solver_proc.start()
        _processes.append(solver_proc)

        # Wait for solver to be ready
        retries = 40
        print(f"[AgentServer] Waiting for solver {team_id} to be healthy...", flush=True)
        for attempt in range(retries):
            try:
                r = httpx.get(f"{solver_url}/health", timeout=2.0)
                if r.status_code == 200:
                    print(f"[AgentServer] Solver {team_id} healthy after {attempt+1} attempts", flush=True)
                    break
            except Exception as e:
                if attempt % 5 == 0:
                    print(f"[AgentServer] Solver {team_id} health check attempt {attempt+1}: {e}", flush=True)
            time.sleep(0.3)
        else:
            raise RuntimeError(f"Solver at {solver_url} never became healthy")

        print(f"[AgentServer] Solver {team_id} running at {solver_url}", flush=True)

        # Step 2: Start ANALYSER-STRATEGIST in its own process
        analyser_port = _find_free_port(current_port)
        current_port = analyser_port + 1
        analyser_url = f"http://localhost:{analyser_port}"

        analyser_proc = ctx.Process(
            target=_subprocess_analyser,
            args=(provider, registry_url, analyser_url, team_id, solver_url, analyser_port, src_path),
            daemon=True,
        )
        analyser_proc.start()
        _processes.append(analyser_proc)

        # Wait for analyser to be ready
        retries = 40
        print(f"[AgentServer] Waiting for analyser {team_id} to be healthy...", flush=True)
        for attempt in range(retries):
            try:
                r = httpx.get(f"{analyser_url}/health", timeout=2.0)
                if r.status_code == 200:
                    print(f"[AgentServer] Analyser {team_id} healthy after {attempt+1} attempts", flush=True)
                    break
            except Exception as e:
                if attempt % 5 == 0:  # Print every 5 attempts
                    print(f"[AgentServer] Analyser {team_id} health check attempt {attempt+1}: {e}", flush=True)
            time.sleep(0.3)
        else:
            raise RuntimeError(f"Analyser at {analyser_url} never became healthy")

        print(f"[AgentServer] Analyser-Strategist {team_id} running at {analyser_url}", flush=True)

        # Store analyser URL (orchestrator uses this to start puzzle)
        team_urls[team_id] = analyser_url

    return team_urls
