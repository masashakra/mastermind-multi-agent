"""
Round-Table Agent HTTP Servers (Autonomous Peer-to-Peer)

Each agent runs as an independent FastAPI HTTP server and:
1. Registers with registry on startup
2. Receives A2AMessage requests from peers
3. Processes work autonomously
4. Decides next peer via LLM
5. Sends A2AMessage to next peer (peer-to-peer, not orchestrator-mediated)
6. Returns A2AMessage response to original sender

Agents form a peer network where each can communicate with any other.
"""

import sys
import time
import threading
import asyncio
import json
from pathlib import Path
from typing import Dict, Any

import httpx
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel

# ── path setup ─────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from paradigms.round_table.agents.analyzer import AnalyzerAgent, AGENT_CARD as ANALYZER_CARD
from paradigms.round_table.agents.strategist import StrategistAgent, AGENT_CARD as STRATEGIST_CARD
from paradigms.round_table.agents.proposer import ProposerAgent, AGENT_CARD as PROPOSER_CARD
from paradigms.round_table.agents.validator import ValidatorAgent, AGENT_CARD as VALIDATOR_CARD
from communication.a2a_message import A2AMessage, A2AStatus


# ── shared helpers ──────────────────────────────────────────────────────────────

def _convert_card_to_a2a(card: Dict[str, Any]) -> Dict[str, Any]:
    """Convert agent card to A2A schema format."""
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
    """POST the agent card to registry."""
    for attempt in range(10):
        try:
            r = httpx.post(f"{registry_url}/register", json=card, timeout=5.0)
            if r.status_code == 200:
                print(f"[Registry] ✓ Registered: {card.get('agent_id')} @ {card.get('url')}")
                return
        except Exception as e:
            pass
        time.sleep(0.4)
    raise RuntimeError(f"Could not register agent {card.get('agent_id')} with registry")


# ── Analyzer server ────────────────────────────────────────────────────────────

def create_analyzer_app(provider: str, registry_url: str, self_url: str) -> FastAPI:
    """Create FastAPI app for autonomous Analyzer agent."""
    app = FastAPI(title="Analyzer Agent (Round-Table)")

    # Create agent with async capabilities
    agent = AnalyzerAgent(
        provider=provider,
        registry_url=registry_url,
    )

    card = _convert_card_to_a2a({
        **ANALYZER_CARD,
        "url": self_url,
        "agent_type": "analyzer",
        "paradigm": "round_table"
    })

    @app.on_event("startup")
    async def startup():
        """Register with registry on startup."""
        _register_with_registry(registry_url, card)

    @app.get("/health")
    async def health():
        return {"status": "ok", "agent": "analyzer"}

    @app.get("/.well-known/agent.json")
    async def agent_json():
        return card

    @app.post("/analyze")
    async def handle_analyze(request: Request):
        """Receive A2AMessage, process, autonomously route to next peer."""
        try:
            request_data = await request.json()
            msg = A2AMessage.from_dict(request_data)

            # Log received message in memory
            agent.memory.receive_message(
                from_agent=msg.sender_id.split("_")[0],
                action=msg.action,
                payload=msg.payload,
                msg_id=msg.message_id,
                is_reply=False
            )

            # If this is a question, answer it directly without forwarding
            if msg.is_question:
                last_guess = msg.payload.get("last_guess", [])
                feedback = msg.payload.get("feedback", {})
                guess_history = msg.payload.get("guess_history", [])

                result = agent.analyze_feedback(
                    last_guess=last_guess,
                    feedback=feedback,
                    previous_guesses=guess_history
                )

                response_msg = A2AMessage.response(
                    request=msg,
                    payload=result,
                    status=A2AStatus.OK,
                    is_reply=True
                )
                return response_msg.to_dict()

            # Extract payload
            last_guess = msg.payload.get("last_guess", [])
            feedback = msg.payload.get("feedback", {})
            guess_history = msg.payload.get("guess_history", [])

            # Do the work — pass accumulated knowledge base
            result = agent.analyze_feedback(
                last_guess=last_guess,
                feedback=feedback,
                previous_guesses=guess_history,
            )

            # Carry game context + constraints forward
            game_context = {
                "available_colors": msg.payload.get("available_colors", []),
                "guess_history":    msg.payload.get("guess_history", []),
                "difficulty":       msg.payload.get("difficulty", "easy"),
                "num_pegs":         msg.payload.get("num_pegs", 4),
            }
            outgoing_payload = {**result, **game_context}

            # Autonomously decide next peer via LLM
            game_state = msg.payload
            available_peers = ["strategist", "proposer", "validator"]

            routing = await agent.decide_next_peer(
                my_work=result,
                available_peers=available_peers,
                game_state=game_state
            )

            next_peer = routing.get("next_peer", "strategist")
            action = routing.get("action", "strategy")

            # Validate routing decision
            peer_actions = {"analyzer": "analyze", "strategist": "strategy", "proposer": "propose", "validator": "validate"}
            expected_action = peer_actions.get(next_peer, "strategy")

            if next_peer not in available_peers:
                print(f"[Analyzer] WARNING: Invalid peer '{next_peer}' not in {available_peers}. Using fallback.")
                next_peer = available_peers[0] if available_peers else "strategist"
                action = peer_actions.get(next_peer, "strategy")
            elif action != expected_action:
                print(f"[Analyzer] WARNING: Wrong action '{action}' for peer '{next_peer}'. Expected '{expected_action}'.")
                action = expected_action

            print(f"[Analyzer] Decision: send to {next_peer} via /{action}")

            # Autonomously send to next peer (fire-and-forget, non-blocking)
            async def send_peer_message():
                try:
                    await agent.send_a2a_message(
                        receiver_type=next_peer,
                        action=action,
                        payload=outgoing_payload
                    )
                except Exception as e:
                    print(f"[Analyzer] Error sending to {next_peer}: {e}")

            asyncio.create_task(send_peer_message())

            # Return response immediately to original sender (don't wait for peer send)
            response_msg = A2AMessage.response(
                request=msg,
                payload=result,
                status=A2AStatus.OK
            )
            return response_msg.to_dict()

        except Exception as e:
            print(f"[Analyzer] Error: {e}")
            if 'msg' in locals():
                from communication.a2a_message import A2AErrorCode
                error_msg = A2AMessage.error(
                    request=msg,
                    error_code=A2AErrorCode.INTERNAL_ERROR,
                    error_message=str(e)
                )
                return error_msg.to_dict()
            return {"error": str(e)}

    return app


# ── Strategist server ──────────────────────────────────────────────────────────

def create_strategist_app(provider: str, registry_url: str, self_url: str) -> FastAPI:
    """Create FastAPI app for autonomous Strategist agent."""
    app = FastAPI(title="Strategist Agent (Round-Table)")

    agent = StrategistAgent(
        provider=provider,
        registry_url=registry_url,
    )

    card = _convert_card_to_a2a({
        **STRATEGIST_CARD,
        "url": self_url,
        "agent_type": "strategist",
        "paradigm": "round_table"
    })

    @app.on_event("startup")
    async def startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    async def health():
        return {"status": "ok", "agent": "strategist"}

    @app.get("/.well-known/agent.json")
    async def agent_json():
        return card

    @app.post("/strategy")
    async def handle_strategy(request: Request):
        """Receive A2AMessage, process, autonomously route to next peer."""
        try:
            request_data = await request.json()
            msg = A2AMessage.from_dict(request_data)

            # Log received message in memory
            agent.memory.receive_message(
                from_agent=msg.sender_id.split("_")[0],
                action=msg.action,
                payload=msg.payload,
                msg_id=msg.message_id,
                is_reply=False
            )

            # If this is a question, answer it directly without forwarding
            if msg.is_question:
                guess_history = msg.payload.get("guess_history", [])
                difficulty = msg.payload.get("difficulty", "medium")

                result = agent.propose_strategy(
                    guess_history=guess_history,
                    difficulty=difficulty
                )

                response_msg = A2AMessage.response(
                    request=msg,
                    payload=result,
                    status=A2AStatus.OK,
                    is_reply=True
                )
                return response_msg.to_dict()

            guess_history = msg.payload.get("guess_history", [])
            difficulty = msg.payload.get("difficulty", "medium")

            # Do the work
            result = agent.propose_strategy(
                guess_history=guess_history,
                difficulty=difficulty
            )

            # Carry game context + constraints forward
            game_context = {
                "available_colors": msg.payload.get("available_colors", []),
                "guess_history":    msg.payload.get("guess_history", []),
                "difficulty":       msg.payload.get("difficulty", "easy"),
                "num_pegs":         msg.payload.get("num_pegs", 4),
            }
            outgoing_payload = {**result, **game_context}

            # Autonomously decide next peer
            game_state = msg.payload
            available_peers = ["analyzer", "proposer", "validator"]

            routing = await agent.decide_next_peer(
                my_work=result,
                available_peers=available_peers,
                game_state=game_state
            )

            next_peer = routing.get("next_peer", "proposer")
            action = routing.get("action", "propose")

            # Validate routing decision
            peer_actions = {"analyzer": "analyze", "strategist": "strategy", "proposer": "propose", "validator": "validate"}
            expected_action = peer_actions.get(next_peer, "propose")

            if next_peer not in available_peers:
                print(f"[Strategist] WARNING: Invalid peer '{next_peer}' not in {available_peers}. Using fallback.")
                next_peer = available_peers[0] if available_peers else "proposer"
                action = peer_actions.get(next_peer, "propose")
            elif action != expected_action:
                print(f"[Strategist] WARNING: Wrong action '{action}' for peer '{next_peer}'. Expected '{expected_action}'.")
                action = expected_action

            print(f"[Strategist] Decision: send to {next_peer} via /{action}")

            # Autonomously send to next peer (fire-and-forget, non-blocking)
            async def send_peer_message():
                try:
                    await agent.send_a2a_message(
                        receiver_type=next_peer,
                        action=action,
                        payload=outgoing_payload
                    )
                except Exception as e:
                    print(f"[Strategist] Error sending to {next_peer}: {e}")

            asyncio.create_task(send_peer_message())

            response_msg = A2AMessage.response(
                request=msg,
                payload=result,
                status=A2AStatus.OK
            )
            return response_msg.to_dict()

        except Exception as e:
            print(f"[Strategist] Error: {e}")
            if 'msg' in locals() and msg:
                from communication.a2a_message import A2AErrorCode
                error_msg = A2AMessage.error(
                    request=msg,
                    error_code=A2AErrorCode.INTERNAL_ERROR,
                    error_message=str(e)
                )
            else:
                return {"error": str(e)}
            return error_msg.to_dict()

    return app


# ── Proposer server ────────────────────────────────────────────────────────────

def create_proposer_app(provider: str, registry_url: str, self_url: str) -> FastAPI:
    """Create FastAPI app for autonomous Proposer agent."""
    app = FastAPI(title="Proposer Agent (Round-Table)")

    agent = ProposerAgent(
        provider=provider,
        registry_url=registry_url,
    )

    card = _convert_card_to_a2a({
        **PROPOSER_CARD,
        "url": self_url,
        "agent_type": "proposer",
        "paradigm": "round_table"
    })

    @app.on_event("startup")
    async def startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    async def health():
        return {"status": "ok", "agent": "proposer"}

    @app.get("/.well-known/agent.json")
    async def agent_json():
        return card

    @app.post("/propose")
    async def handle_propose(request: Request):
        """Receive A2AMessage, process, autonomously route to next peer."""
        try:
            request_data = await request.json()
            msg = A2AMessage.from_dict(request_data)

            # Log received message in memory
            agent.memory.receive_message(
                from_agent=msg.sender_id.split("_")[0],
                action=msg.action,
                payload=msg.payload,
                msg_id=msg.message_id,
                is_reply=False
            )

            # If this is a question, answer it directly without forwarding

            if msg.is_question:
                strategy = msg.payload.get("strategy", "")
                constraints_text = msg.payload.get("constraints", "")
                available_colors = msg.payload.get("available_colors", [])
                num_pegs = msg.payload.get("num_pegs", 4)
                guess_history = msg.payload.get("guess_history", [])

                result = agent.propose_guess(
                    strategy=strategy,
                    constraints_text=constraints_text,
                    available_colors=available_colors,
                    num_pegs=num_pegs,
                    previous_guesses=guess_history,
                )

                response_msg = A2AMessage.response(
                    request=msg,
                    payload=result,
                    status=A2AStatus.OK,
                    is_reply=True
                )
                return response_msg.to_dict()

            strategy = msg.payload.get("strategy", "")
            constraints_text = msg.payload.get("constraints", "")
            available_colors = msg.payload.get("available_colors", [])
            num_pegs = msg.payload.get("num_pegs", 4)
            guess_history = msg.payload.get("guess_history", [])

            result = agent.propose_guess(
                strategy=strategy,
                constraints_text=str(constraints_text),
                available_colors=available_colors,
                num_pegs=num_pegs,
                previous_guesses=guess_history,
            )

            # Normalise case + prevent duplicate — LLM does the reasoning,
            # we just ensure basic validity
            import random as _random
            past_guesses = [g.get("guess", g) if isinstance(g, dict) else g for g in guess_history]
            proposed = [c.lower() if isinstance(c, str) else c for c in result.get("proposed_guess", [])]

            if proposed in past_guesses:
                print(f"[Proposer] ⚠ Duplicate {proposed}, asking LLM to try again...")
                # Ask the LLM again with explicit reminder — uses conversation history
                retry_result = agent.propose_guess(
                    strategy=strategy,
                    constraints_text=f"IMPORTANT: {proposed} was ALREADY guessed! Propose something different.",
                    available_colors=available_colors,
                    num_pegs=num_pegs,
                    previous_guesses=guess_history,
                )
                retry = [c.lower() if isinstance(c, str) else c for c in retry_result.get("proposed_guess", [])]
                if retry and retry not in past_guesses:
                    proposed = retry
                else:
                    # Last resort random
                    safe = available_colors or ["red", "blue", "green", "yellow", "white", "black"]
                    for _ in range(50):
                        candidate = [_random.choice(safe) for _ in range(num_pegs or 4)]
                        if candidate not in past_guesses:
                            proposed = candidate
                            break

            result["proposed_guess"] = proposed

            # Carry game context forward
            game_context = {
                "available_colors": msg.payload.get("available_colors", []),
                "guess_history":    msg.payload.get("guess_history", []),
                "difficulty":       msg.payload.get("difficulty", "easy"),
                "num_pegs":         msg.payload.get("num_pegs", 4),
            }
            outgoing_payload = {**result, **game_context}

            # Proposer decides autonomously who to send to via LLM
            game_state = msg.payload
            available_peers = ["strategist", "validator"]

            routing = await agent.decide_next_peer(
                my_work=result,
                available_peers=available_peers,
                game_state=game_state
            )

            next_peer = routing.get("next_peer", "validator")
            action = routing.get("action", "validate")

            # Validate action matches the peer's endpoint
            peer_actions = {"analyzer": "analyze", "strategist": "strategy", "proposer": "propose", "validator": "validate"}
            expected_action = peer_actions.get(next_peer, "validate")

            if next_peer not in available_peers:
                print(f"[Proposer] WARNING: Invalid peer '{next_peer}', using validator.")
                next_peer = "validator"
                action = "validate"
            elif action != expected_action:
                print(f"[Proposer] WARNING: Wrong action '{action}' for '{next_peer}', correcting to '{expected_action}'.")
                action = expected_action

            print(f"[Proposer] Decision: send to {next_peer} via /{action}")

            # Autonomously send to next peer (fire-and-forget, non-blocking)
            async def send_peer_message():
                try:
                    await agent.send_a2a_message(
                        receiver_type=next_peer,
                        action=action,
                        payload=outgoing_payload
                    )
                except Exception as e:
                    print(f"[Proposer] Error sending to {next_peer}: {e}")

            asyncio.create_task(send_peer_message())

            response_msg = A2AMessage.response(
                request=msg,
                payload=result,
                status=A2AStatus.OK
            )
            return response_msg.to_dict()

        except Exception as e:
            print(f"[Proposer] Error: {e}")
            if 'msg' in locals() and msg:
                from communication.a2a_message import A2AErrorCode
                error_msg = A2AMessage.error(
                    request=msg,
                    error_code=A2AErrorCode.INTERNAL_ERROR,
                    error_message=str(e)
                )
            else:
                return {"error": str(e)}
            return error_msg.to_dict()

    return app


# ── Validator server ───────────────────────────────────────────────────────────

def create_validator_app(provider: str, registry_url: str, self_url: str) -> FastAPI:
    """Create FastAPI app for autonomous Validator agent."""
    app = FastAPI(title="Validator Agent (Round-Table)")

    agent = ValidatorAgent(
        provider=provider,
        registry_url=registry_url,
    )

    card = _convert_card_to_a2a({
        **VALIDATOR_CARD,
        "url": self_url,
        "agent_type": "validator",
        "paradigm": "round_table"
    })

    @app.on_event("startup")
    async def startup():
        _register_with_registry(registry_url, card)

    @app.get("/health")
    async def health():
        return {"status": "ok", "agent": "validator"}

    @app.get("/.well-known/agent.json")
    async def agent_json():
        return card

    @app.post("/validate")
    async def handle_validate(request: Request):
        """Receive A2AMessage, process, autonomously route (to orchestrator if valid)."""
        try:
            request_data = await request.json()
            msg = A2AMessage.from_dict(request_data)

            # Log received message in memory
            agent.memory.receive_message(
                from_agent=msg.sender_id.split("_")[0],
                action=msg.action,
                payload=msg.payload,
                msg_id=msg.message_id,
                is_reply=False
            )

            # If this is a question, answer it directly without forwarding
            if msg.is_question:
                guess = msg.payload.get("guess", msg.payload.get("proposed_guess", []))
                available_colors = msg.payload.get("available_colors", [])
                expected_length = msg.payload.get("expected_length", 4)
                guess_history = msg.payload.get("guess_history", [])
                constraints = msg.payload.get("constraints", {})

                result = agent.validate_guess(
                    guess=guess,
                    available_colors=available_colors,
                    expected_length=expected_length,
                    previous_guesses=guess_history,
                    constraints=constraints
                )

                response_msg = A2AMessage.response(
                    request=msg,
                    payload=result,
                    status=A2AStatus.OK,
                    is_reply=True
                )
                return response_msg.to_dict()

            guess = msg.payload.get("guess", msg.payload.get("proposed_guess", []))
            available_colors = msg.payload.get("available_colors", [])
            expected_length = msg.payload.get("expected_length", 4)
            guess_history = msg.payload.get("guess_history", [])
            constraints = msg.payload.get("constraints", {})

            # Do the work
            result = agent.validate_guess(
                guess=guess,
                available_colors=available_colors,
                expected_length=expected_length,
                previous_guesses=guess_history,
                constraints=constraints
            )

            # Add the guess and knowledge base to result so orchestrator gets it
            result["proposed_guess"] = guess
            result["guess"] = guess

            # Check if valid
            is_valid = result.get("valid", False)

            if is_valid:
                print(f"[Validator] ✓ Valid guess! Sending to orchestrator...")
                # Send to orchestrator's /receive_validation endpoint (fire-and-forget)
                async def send_to_orchestrator():
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            orch_msg = A2AMessage.request(
                                sender_id="validator_round_table",
                                receiver_id="orchestrator_round_table",
                                action="receive_validation",
                                payload=result
                            )
                            orch_resp = await client.post(
                                "http://localhost:8107/receive_validation",
                                json=orch_msg.to_dict(),
                                timeout=10.0
                            )
                            print(f"[Validator] Orchestrator received validation (status={orch_resp.status_code})")
                    except Exception as e:
                        print(f"[Validator] Error sending to orchestrator: {e}")

                asyncio.create_task(send_to_orchestrator())
            else:
                print(f"[Validator] ✗ Invalid guess, autonomously deciding next step...")

                # Autonomously decide where to send for revision
                game_state = msg.payload.copy()
                game_state["validation_errors"] = result.get("hard_violations", [])
                available_peers = ["proposer"]  # Send back to proposer for revision

                routing = await agent.decide_next_peer(
                    my_work=result,
                    available_peers=available_peers,
                    game_state=game_state
                )

                next_peer = routing.get("next_peer", "proposer")
                action = routing.get("action", "propose")

                # Validate routing decision
                peer_actions = {"analyzer": "analyze", "strategist": "strategy", "proposer": "propose", "validator": "validate"}
                expected_action = peer_actions.get(next_peer, "propose")

                if next_peer not in available_peers:
                    print(f"[Validator] WARNING: Invalid peer '{next_peer}' not in {available_peers}. Using fallback.")
                    next_peer = available_peers[0] if available_peers else "proposer"
                    action = peer_actions.get(next_peer, "propose")
                elif action != expected_action:
                    print(f"[Validator] WARNING: Wrong action '{action}' for peer '{next_peer}'. Expected '{expected_action}'.")
                    action = expected_action

                print(f"[Validator] Decision: send back to {next_peer} for revision")

                # Autonomously send back for revision (fire-and-forget, non-blocking)
                async def send_for_revision():
                    try:
                        await agent.send_a2a_message(
                            receiver_type=next_peer,
                            action=action,
                            payload=result
                        )
                    except Exception as e:
                        print(f"[Validator] Error sending to {next_peer}: {e}")

                asyncio.create_task(send_for_revision())

            response_msg = A2AMessage.response(
                request=msg,
                payload=result,
                status=A2AStatus.OK
            )
            return response_msg.to_dict()

        except Exception as e:
            print(f"[Validator] Error: {e}")
            if 'msg' in locals() and msg:
                from communication.a2a_message import A2AErrorCode
                error_msg = A2AMessage.error(
                    request=msg,
                    error_code=A2AErrorCode.INTERNAL_ERROR,
                    error_message=str(e)
                )
            else:
                return {"error": str(e)}
            return error_msg.to_dict()

    return app


# ── Server startup ─────────────────────────────────────────────────────────────

def start_agent_servers(
    provider: str,
    registry_url: str,
    base_port: int = 8101,
) -> Dict[str, str]:
    """Start all agent HTTP servers and wait for them to be healthy.

    Args:
        provider: LLM provider ("ollama", "kaggle", "claude", etc.)
        registry_url: URL of registry server
        base_port: Starting port (analyzer=base_port, strategist=+1, etc.)

    Returns:
        Dict mapping agent type to URL (e.g., {"analyzer": "http://localhost:8101"})
    """
    servers = {}
    apps = {}

    agents = [
        ("analyzer", create_analyzer_app, base_port),
        ("strategist", create_strategist_app, base_port + 1),
        ("proposer", create_proposer_app, base_port + 2),
        ("validator", create_validator_app, base_port + 3),
    ]

    for agent_type, create_app_func, port in agents:
        url = f"http://localhost:{port}"

        # Create app
        app = create_app_func(
            provider=provider,
            registry_url=registry_url,
            self_url=url,
        )
        apps[agent_type] = app

        # Start server in background thread
        def run_server(agent_type=agent_type, app=app, port=port):
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=port,
                log_level="error",
            )

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

        # Wait for server to be healthy
        _wait_for_healthy(url)
        servers[agent_type] = url
        print(f"[AgentServer] {agent_type} running at {url}")

    return servers


if __name__ == "__main__":
    # For local testing only
    import os

    registry_url = os.getenv("REGISTRY_URL", "http://localhost:8100")
    provider = os.getenv("PROVIDER", "kaggle")

    start_agent_servers(provider=provider, registry_url=registry_url)
    import time
    time.sleep(3600)  # Keep running for 1 hour
