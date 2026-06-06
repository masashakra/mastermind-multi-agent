"""
Coopetition Peer-to-Peer Orchestrator — LangGraph without Judge Node

Architecture:
  1. Start registry HTTP server
  2. Start 4 A2A agent servers (2 per team)
  3. Orchestrator directly manages rounds (no Judge)
  4. Teams negotiate peer-to-peer via A2A
  5. Orchestrator provides voting as fallback

Differences from Centralized:
  - No Judge node (orchestrator is lightweight)
  - Teams call each other directly for debate
  - Orchestrator coordinates flow
  - Voting is orchestrator's fallback, not Judge's
"""

import sys
import time
import json
from pathlib import Path
from typing import Any, Dict, List, TypedDict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langgraph.graph import StateGraph, START, END
import requests

from registry.registry_server import start_registry_server
from paradigms.coopetition_peer_to_peer.agents.agent_server import start_agent_servers
from game_engine import GameEngine
from puzzle_generator import load_puzzles


# ── LangGraph State ───────────────────────────────────────────────


class CoopetitionPeerToPeerState(TypedDict):
    round_number: int
    guess_history: List[Dict[str, Any]]
    last_guess: List[str]
    last_feedback: Dict[str, int]
    solved: bool
    game_over: bool
    winning_guess: List[str]
    shared_knowledge: List[Dict[str, Any]]


# ── Orchestrator ──────────────────────────────────────────────


class CoopetitionPeerToPeerOrchestrator:
    """LangGraph orchestrator for 2-team peer-to-peer coopetition.

    Teams negotiate directly via A2A, no Judge mediator.
    Orchestrator coordinates rounds and provides voting fallback.
    """

    MAX_ROUNDS = 8
    MAX_NEGOTIATION_TURNS = 3

    def __init__(self, puzzle: Dict[str, Any], provider: str = "deepseek", run_tag: str = ""):
        self.puzzle = puzzle
        self.provider = provider
        self.paradigm = "coopetition_peer_to_peer"
        self.start_time = time.time()

        print(f"\n[Orchestrator] Starting Coopetition Peer-to-Peer — puzzle {puzzle['puzzle_id']}")
        print(f"[Orchestrator] Teams communicate directly via A2A (no Judge)")

        # Initialize message logger
        puzzle_id = puzzle.get("puzzle_id", "unknown")
        tag = f"_{run_tag}" if run_tag else ""
        log_file = f"logs/{puzzle_id}_coopetition_peer_to_peer_{provider}{tag}_messages.log"
        from communication.message_logger import init_message_logger

        self.message_logger = init_message_logger(log_file)
        print(f"[Orchestrator] Logging to {log_file}")

        # Start registry
        import socket

        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", 0))
        registry_port = sock.getsockname()[1]
        sock.close()
        self.registry_url = start_registry_server(port=registry_port)
        print(f"[Orchestrator] Registry up at {self.registry_url}")

        # Start 4 A2A agent servers (2 per team)
        self.agent_urls = start_agent_servers(
            provider=provider,
            registry_url=self.registry_url,
            base_port=8401,
        )
        print(f"[Orchestrator] Agents online: {list(self.agent_urls.keys())}")

        # Initialize game engine
        self.game_engine = GameEngine(
            secret_code=puzzle.get("secret_code", []),
            difficulty=puzzle.get("difficulty", "medium")
        )

        # Build LangGraph
        self._build_graph()

    def _build_graph(self):
        """Build LangGraph state machine."""
        builder = StateGraph(CoopetitionPeerToPeerState)

        # Add orchestration node
        builder.add_node("orchestrate", self._orchestrate_node)

        # Add submit node
        builder.add_node("submit", self._submit_guess_node)

        # Add edges
        builder.add_edge(START, "orchestrate")
        builder.add_conditional_edges(
            "orchestrate",
            self._should_continue,
            {
                "continue": "submit",
                "end": END,
            },
        )
        builder.add_edge("submit", "orchestrate")

        self.graph = builder.compile()

    def _call_team_a2a(self, team: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call team agent via A2A HTTP."""
        agent_id = f"analyzer_strategist_{team.lower()}"
        url = self.agent_urls.get(agent_id)

        if not url:
            return {"error": f"{agent_id} URL not found"}

        try:
            message = {"action": action, "payload": payload}
            response = requests.post(url, json=message, timeout=300)
            response.raise_for_status()
            return response.json().get("result", response.json())
        except Exception as e:
            print(f"[Orchestrator] Error calling {agent_id}: {e}")
            return {"error": str(e)}

    def _orchestrate_node(self, state: CoopetitionPeerToPeerState) -> CoopetitionPeerToPeerState:
        """Orchestrator node: manage peer-to-peer negotiation."""
        round_num = state["round_number"]
        print(f"\n[Orchestrator] Round {round_num}: Peer-to-Peer Negotiation")

        # Get last guess/feedback for context
        last_guess = state["last_guess"] if state["last_guess"] else []
        last_feedback = state["last_feedback"] if state["last_feedback"] else {}
        shared_knowledge = state["shared_knowledge"]

        # Phase 1: Both teams generate proposals independently
        print(f"\n[Phase 1] Teams generate proposals independently")
        payload = {
            "last_guess": last_guess,
            "feedback": last_feedback,
            "previous_guesses": [sk["guess"] for sk in shared_knowledge[:-1]] if shared_knowledge else [],
            "shared_knowledge": shared_knowledge,
        }

        team_a_result = self._call_team_a2a("A", "generate_proposal", payload)
        team_b_result = self._call_team_a2a("B", "generate_proposal", payload)

        if team_a_result.get("error") or team_b_result.get("error"):
            print(f"[Orchestrator] Error getting proposals")
            state["winning_guess"] = last_guess if last_guess else ["red", "blue", "green", "yellow", "white"]
            return state

        team_a_proposal = team_a_result.get("proposal", {})
        team_b_proposal = team_b_result.get("proposal", {})

        print(f"Team A proposes: {team_a_proposal.get('guess')} ({team_a_proposal.get('confidence')}%)")
        print(f"Team B proposes: {team_b_proposal.get('guess')} ({team_b_proposal.get('confidence')}%)")

        # Check immediate consensus
        if team_a_proposal.get("guess") == team_b_proposal.get("guess"):
            print(f"✓ CONSENSUS on first proposal!")
            state["winning_guess"] = team_a_proposal.get("guess")
            return state

        # Phase 2: Peer-to-peer negotiation (teams call each other via A2A)
        print(f"\n[Phase 2] Peer-to-peer negotiation (up to {self.MAX_NEGOTIATION_TURNS} turns)")

        current_proposal_a = team_a_proposal
        current_proposal_b = team_b_proposal

        for turn in range(1, self.MAX_NEGOTIATION_TURNS + 1):
            print(f"\n--- Negotiation Turn {turn} ---")

            # Team A asks Team B via A2A: What do you think?
            print(f"[Orchestrator] Team A requests Team B's response via A2A")
            response_b = self._call_team_a2a(
                "B",
                "argue_for_proposal",
                {
                    "own_proposal": current_proposal_b,
                    "opponent_proposal": current_proposal_a,
                    "debate_context": f"Peer negotiation turn {turn}",
                },
            )

            print(f"[Team B] {response_b.get('main_argument', '')[:80]}...")

            # Team B asks Team A via A2A: How do you respond?
            print(f"[Orchestrator] Team B requests Team A's response via A2A")
            response_a = self._call_team_a2a(
                "A",
                "argue_for_proposal",
                {
                    "own_proposal": current_proposal_a,
                    "opponent_proposal": current_proposal_b,
                    "debate_context": f"Peer negotiation turn {turn}",
                },
            )

            print(f"[Team A] {response_a.get('main_argument', '')[:80]}...")

            # Check consensus
            both_willing = response_a.get("willingness_to_compromise") and response_b.get("willingness_to_compromise")

            if both_willing and current_proposal_a.get("guess") == current_proposal_b.get("guess"):
                print(f"✓ CONSENSUS after {turn} turns!")
                state["winning_guess"] = current_proposal_a.get("guess")
                return state

        # Phase 3: No consensus - Orchestrator decides via voting
        print(f"\n[Phase 3] No consensus → Orchestrator confidence-weighted voting")

        decision = self._confidence_weighted_voting(current_proposal_a, current_proposal_b)
        state["winning_guess"] = decision.get("winning_guess", current_proposal_a.get("guess"))

        print(f"[Voting] Team {decision.get('winning_team')} selected")
        print(f"[Voting] Team A weight: {decision.get('weight_a', 0):.1%}")
        print(f"[Voting] Team B weight: {decision.get('weight_b', 0):.1%}")

        return state

    def _confidence_weighted_voting(
        self,
        proposal_a: Dict[str, Any],
        proposal_b: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simple confidence-weighted voting (orchestrator fallback)."""

        conf_a = proposal_a.get("confidence", 50)
        conf_b = proposal_b.get("confidence", 50)
        total = conf_a + conf_b if (conf_a + conf_b) > 0 else 1
        weight_a = conf_a / total
        weight_b = conf_b / total

        if weight_a >= weight_b:
            return {
                "winning_team": "A",
                "winning_guess": proposal_a.get("guess"),
                "weight_a": weight_a,
                "weight_b": weight_b,
                "decision_method": "confidence_voting",
            }
        else:
            return {
                "winning_team": "B",
                "winning_guess": proposal_b.get("guess"),
                "weight_a": weight_a,
                "weight_b": weight_b,
                "decision_method": "confidence_voting",
            }

    def _should_continue(self, state: CoopetitionPeerToPeerState) -> str:
        """Decide if we should continue or end."""
        if state.get("solved") or state.get("game_over"):
            return "end"
        return "continue"

    def _submit_guess_node(self, state: CoopetitionPeerToPeerState) -> CoopetitionPeerToPeerState:
        """Submit guess to game engine and get feedback."""
        guess = state.get("winning_guess")
        print(f"\n[Orchestrator] Submitting: {guess}")

        feedback = self.game_engine.submit_guess(guess)
        print(f"[Orchestrator] Feedback: {feedback}")

        # Update state
        state["last_guess"] = guess
        state["last_feedback"] = feedback
        state["guess_history"].append({"guess": guess, "feedback": feedback})
        state["shared_knowledge"].append({"guess": guess, "feedback": feedback})

        # Check if solved
        if feedback.get("correct_positions") == len(guess):
            state["solved"] = True
            print(f"\n🎉 PUZZLE SOLVED in {state['round_number']} rounds!")
        elif state["round_number"] >= self.MAX_ROUNDS:
            state["game_over"] = True
            print(f"\n❌ PUZZLE NOT SOLVED after {self.MAX_ROUNDS} rounds")

        state["round_number"] += 1
        return state

    def run(self) -> Dict[str, Any]:
        """Run the LangGraph orchestration."""
        print(f"\n[Orchestrator] Starting LangGraph execution")

        initial_state = CoopetitionPeerToPeerState(
            round_number=1,
            guess_history=[],
            last_guess=[],
            last_feedback={},
            solved=False,
            game_over=False,
            winning_guess=[],
            shared_knowledge=[],
        )

        # Execute graph
        final_state = self.graph.invoke(initial_state)

        # Return results
        if final_state.get("solved"):
            return {
                "success": True,
                "rounds_used": final_state["round_number"] - 1,
                "final_guess": final_state["last_guess"],
                "paradigm": self.paradigm,
                "shared_knowledge": final_state["shared_knowledge"],
            }
        else:
            return {
                "success": False,
                "rounds_used": final_state["round_number"] - 1,
                "paradigm": self.paradigm,
                "shared_knowledge": final_state["shared_knowledge"],
            }
