"""
Agent Server for Direct Debate with Judge Feedback

Each team has two agents:
  - Analyser-Strategist: Analyzes patterns, develops strategy
  - Proposer: Generates proposals based on strategy

Endpoints:
  GET  /health                  → liveness check
  GET  /.well-known/agent.json  → agent card
  POST /get_proposal            → Generate and return a proposal (no submission)
  POST /start_puzzle            → Start autonomous proposal generation loop
"""

import sys
import time
import threading
import socket
import asyncio
from pathlib import Path
from typing import Dict, Any, List

import httpx
import uvicorn
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from paradigms.direct_debate.agents.analyser_strategist import AnalyserStrategist
from paradigms.direct_debate.agents.solver import Solver


def _find_free_port(start_port: int = 8600) -> int:
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


def start_agent_servers(
    provider: str,
    registry_url: str,
    base_port: int = 8601,
    num_teams: int = 2,
    orchestrator_url: str = None,
) -> Dict[str, str]:
    """Start autonomous agent servers for teams.

    Returns: {team_id: url, ...}
    """
    team_urls = {}

    for team_num in range(1, num_teams + 1):
        team_id = f"team_{team_num}"
        port = base_port + (team_num - 1)
        url = f"http://localhost:{port}"

        app = create_team_app(
            provider=provider,
            team_id=team_id,
            registry_url=registry_url,
            orchestrator_url=orchestrator_url,
        )

        def run_server(app=app, port=port, team_id=team_id):
            config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
            server = uvicorn.Server(config)
            asyncio.run(server.serve())

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        team_urls[team_id] = url

        time.sleep(0.3)  # Stagger startup
        print(f"[Orchestrator] {team_id} starting on {url}")

    return team_urls


def create_team_app(
    provider: str,
    team_id: str,
    registry_url: str,
    orchestrator_url: str = None,
) -> FastAPI:
    """Create FastAPI app for a team's proposal agent."""
    app = FastAPI(title=f"Team {team_id}")

    # Initialize agents
    analyser = AnalyserStrategist(provider=provider, team_id=team_id)
    solver = Solver(provider=provider, team_id=team_id)

    # Shared state
    state = {
        "guess_history": [],
        "last_strategy": "",
        "last_feedback": {},
    }

    def _extract_constraints_from_history(history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract constraints like boss_worker does.

        Returns structured constraints:
        - impossible_colors: colors that appeared with 0 pegs
        - confirmed_colors: colors that appeared with >0 pegs
        - locked_positions: specific position-color pairs confirmed
        - misplaced_colors: colors in code but wrong position
        """
        impossible = set()
        confirmed = set()
        locked_pos = {}
        misplaced = []

        for entry in history:
            # Skip rejected attempts (marked with -1 feedback)
            if entry.get('rejected'):
                continue

            guess = entry.get('guess', [])
            feedback = entry.get('feedback', {})
            pegs = feedback.get('correct_pegs', 0)
            positions = feedback.get('correct_positions', 0)

            # Extract impossible colors (0 pegs means none of these are in code)
            if pegs == 0:
                impossible.update(guess)

            # Extract confirmed colors (any color with >0 pegs is in code)
            if pegs > 0:
                confirmed.update(guess)

                # Track locked positions (positions that match)
                if positions > 0:
                    for i, color in enumerate(guess):
                        if pegs == 4 and positions == 4:
                            # All correct = all positions locked
                            locked_pos[i] = color

            # Track misplaced colors
            misplaced_count = pegs - positions
            if misplaced_count > 0:
                for color in guess:
                    if color in confirmed:
                        misplaced.append({
                            "color": color,
                            "appeared_in_wrong_position": True
                        })

        return {
            "impossible_colors": list(impossible),
            "confirmed_colors": list(confirmed),
            "locked_positions": [{"position": pos, "color": color} for pos, color in locked_pos.items()],
            "misplaced_colors": misplaced,
        }

    def _validate_guess(guess: List[str], history: List[Dict[str, Any]], constraints: Dict[str, Any], available_colors: List[str]) -> tuple:
        """Validate if a guess is good (follows constraints and avoids bad patterns).

        Returns (is_valid, reason)
        """
        # Basic validation
        if len(guess) != 4:
            return False, f"Guess has {len(guess)} colors, need 4"

        for color in guess:
            if color not in available_colors:
                return False, f"Color {color} not in available colors"

        # Check if guess repeats a previous one
        for entry in history:
            if entry.get('guess') == guess and not entry.get('rejected'):
                return False, "Guess repeats a previous attempt"

        # Check constraint violations
        impossible = constraints.get('impossible_colors', [])
        if any(color in impossible for color in guess):
            return False, "Guess includes impossible colors"

        locked = constraints.get('locked_positions', [])
        for lock in locked:
            pos = lock.get('position')
            color = lock.get('color')
            if guess[pos] != color:
                return False, f"Violates locked position {pos}={color}"

        # ✅ CRITICAL: Check if stuck at 3p (need systematic strategy)
        three_p_rounds = sum(1 for h in history if h.get('feedback', {}).get('correct_pegs') == 3 and not h.get('rejected'))
        if three_p_rounds >= 2:
            # Should use systematic color replacement
            # For now just accept, but flag for future hardening
            pass

        return True, "Valid guess"

    @app.get("/health")
    def health():
        return {"status": "ok", "agent": team_id}

    @app.get("/.well-known/agent.json")
    def agent_card():
        return {
            "agent_id": team_id,
            "agent_name": f"Team {team_id}",
            "agent_type": "team",
            "paradigm": "direct_debate_judge_feedback",
            "version": "1.0.0",
            "description": f"Autonomous team proposing guesses",
            "url": f"http://localhost:8601",
        }

    @app.post("/get_proposal")
    def get_proposal(body: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a proposal with retry loop (like boss_worker)."""
        from communication.message_logger import get_message_logger
        logger = get_message_logger()

        try:
            round_num = body.get("round", 1)
            shared_history = body.get("shared_history", [])
            difficulty = body.get("difficulty", "easy")
            available_colors = body.get("available_colors", ["red", "blue", "green", "yellow", "white", "black"])

            print(f"\n[{team_id}] Generating proposal for round {round_num}", flush=True)

            if logger:
                logger.log_custom_event(
                    event_type="proposal_request",
                    agent_name=team_id,
                    metadata={"round": round_num, "shared_history_len": len(shared_history)}
                )

            history_for_agents = shared_history if shared_history else state["guess_history"]

            # ✅ RETRY LOOP (like boss_worker)
            max_retries = 3
            for attempt in range(max_retries):
                print(f"[{team_id}] Proposal attempt {attempt + 1}/{max_retries}", flush=True)

                # Extract constraints
                constraints = _extract_constraints_from_history(history_for_agents)

                # Analyze
                analysis = analyser.analyze_and_strategize(
                    guess_history=history_for_agents,
                    difficulty=difficulty,
                    available_colors=available_colors,
                    num_pegs=4,
                    public_leaderboard=shared_history,
                    constraints=constraints,
                )

                strategy = analysis.get("strategy", "")
                confidence = analysis.get("confidence", 50)

                # Generate guess
                guess_result = solver.solve_round(
                    guess_history=history_for_agents,
                    difficulty=difficulty,
                    available_colors=available_colors,
                    num_pegs=4,
                    strategy=strategy,
                )

                guess = guess_result.get("guess", [])
                reasoning = guess_result.get("reasoning", "")

                # ✅ VALIDATION: Check if guess is good enough
                is_valid, reason = _validate_guess(guess, history_for_agents, constraints, available_colors)

                print(f"[{team_id}] Attempt {attempt + 1}: {guess} → Valid: {is_valid}", flush=True)

                if is_valid or attempt == max_retries - 1:
                    # Either valid or out of retries → use this guess
                    print(f"[{team_id}] Accepted proposal: {guess}", flush=True)
                    state["last_strategy"] = strategy
                    break
                else:
                    # Invalid → retry with different strategy
                    print(f"[{team_id}] Rejecting: {reason}. Retrying...", flush=True)
                    # Add to history to force diversity on next attempt
                    history_for_agents = history_for_agents + [{
                        "guess": guess,
                        "feedback": {"correct_pegs": -1, "correct_positions": -1},  # Marker: rejected
                        "rejected": True,
                    }]

            proposal = {
                "team": team_id,
                "guess": guess,
                "reasoning": reasoning,
                "strategy": strategy,
                "confidence": confidence,
                "round": round_num,
            }

            # Log proposal generated
            if logger:
                logger.log_custom_event(
                    event_type="proposal_generated",
                    agent_name=team_id,
                    metadata={
                        "round": round_num,
                        "guess": guess,
                        "reasoning": reasoning[:100],  # Truncate for log readability
                        "strategy": strategy[:100],
                        "confidence": confidence,
                    }
                )

            return {"valid": True, "proposal": proposal}

        except Exception as e:
            import traceback
            print(f"[{team_id}] Error in get_proposal: {e}", flush=True)
            traceback.print_exc()

            # Log error
            if logger:
                logger.log_custom_event(
                    event_type="error",
                    agent_name=team_id,
                    status="error",
                    error=str(e),
                    metadata={"phase": "proposal_generation"}
                )

            return {"valid": False, "error": str(e)}

    @app.post("/update_feedback")
    def update_feedback(body: Dict[str, Any]) -> Dict[str, Any]:
        """Update team's state with feedback from judge decision."""
        try:
            selected_team = body.get("selected_team", "")
            guess = body.get("guess", [])
            feedback = body.get("feedback", {})

            print(f"[{team_id}] Feedback: {guess} → {feedback.get('correct_pegs')}p {feedback.get('correct_positions')}pos", flush=True)

            # Update history regardless of whether this team's guess was selected
            # (helps learning from all guesses)
            state["guess_history"].append({
                "guess": guess,
                "feedback": feedback,
                "selected_by": selected_team,
            })
            state["last_feedback"] = feedback

            return {"valid": True, "updated": True}

        except Exception as e:
            return {"valid": False, "error": str(e)}

    @app.post("/start_puzzle")
    def start_puzzle(body: Dict[str, Any]) -> Dict[str, Any]:
        """Start autonomous proposal generation (called once to init state)."""
        try:
            puzzle = body.get("puzzle", {})
            log_file = body.get("log_file", "")

            # Initialize message logger
            if log_file:
                from communication.message_logger import init_message_logger
                init_message_logger(log_file)

            print(f"[{team_id}] Puzzle started: {puzzle.get('puzzle_id')}", flush=True)

            # Store puzzle info
            state["puzzle"] = puzzle
            state["available_colors"] = puzzle.get("available_colors", [])
            state["num_pegs"] = puzzle.get("pegs", 4)
            state["difficulty"] = puzzle.get("difficulty", "easy")

            return {"status": "started", "team": team_id}

        except Exception as e:
            import traceback
            print(f"[{team_id}] Error in start_puzzle: {e}", flush=True)
            traceback.print_exc()
            return {"status": "error", "error": str(e)}

    return app
