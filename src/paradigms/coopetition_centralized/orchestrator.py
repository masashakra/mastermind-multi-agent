"""
Coopetition Centralized Orchestrator — LangGraph with LLM-Backed Judge Node

Architecture:
  1. Start registry HTTP server
  2. Start 4 A2A agent servers (2 per team)
  3. Initialize LLM-backed Judge (persistent agent)
  4. Create LangGraph with Judge node
  5. Judge node (via A2A):
     - Calls team agents to generate proposals
     - Uses LLM to evaluate proposals
     - Uses LLM to moderate debate
     - Uses LLM to make final decision
     - Returns winning guess
  6. Orchestrator submits guess to game engine
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
from paradigms.coopetition_centralized.agents.agent_server import start_agent_servers
from paradigms.coopetition_centralized.judge import JudgeAgent
from game_engine import GameEngine
from puzzle_generator import load_puzzles


# ── LangGraph State ───────────────────────────────────────────────


class CoopetitionCentralizedState(TypedDict):
    round_number: int
    guess_history: List[Dict[str, Any]]
    last_guess: List[str]
    last_feedback: Dict[str, int]
    solved: bool
    game_over: bool
    winning_guess: List[str]
    shared_knowledge: List[Dict[str, Any]]


# ── Orchestrator ──────────────────────────────────────────────


class CoopetitionCentralizedOrchestrator:
    """LangGraph orchestrator for 2-team coopetition with LLM-backed Judge node."""

    MAX_ROUNDS = 8

    def __init__(self, puzzle: Dict[str, Any], provider: str = "deepseek", run_tag: str = ""):
        self.puzzle = puzzle
        self.provider = provider
        self.paradigm = "coopetition_centralized"
        self.start_time = time.time()

        print(f"\n[Orchestrator] Starting Coopetition Centralized — puzzle {puzzle['puzzle_id']}")
        print(f"[Orchestrator] Judge is an LLM-backed LangGraph node")

        # Initialize message logger
        puzzle_id = puzzle.get("puzzle_id", "unknown")
        tag = f"_{run_tag}" if run_tag else ""
        log_file = f"logs/{puzzle_id}_coopetition_centralized_{provider}{tag}_messages.log"
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
            base_port=8301,
        )
        print(f"[Orchestrator] Agents online: {list(self.agent_urls.keys())}")

        # Create LLM-backed Judge (persists across rounds)
        self.judge = JudgeAgent(self.agent_urls, provider=provider)
        print(f"[Orchestrator] Judge initialized (LLM-backed with conversation history)")

        # Initialize game engine
        self.game_engine = GameEngine(
            secret_code=puzzle.get("secret_code", []),
            difficulty=puzzle.get("difficulty", "medium")
        )

        # Build LangGraph
        self._build_graph()

    def _build_graph(self):
        """Build LangGraph state machine."""
        builder = StateGraph(CoopetitionCentralizedState)

        # Add Judge node
        builder.add_node("judge", self._judge_node)

        # Add submit node
        builder.add_node("submit", self._submit_guess_node)

        # Add edges
        builder.add_edge(START, "judge")
        builder.add_conditional_edges(
            "judge",
            self._should_continue,
            {
                "continue": "submit",
                "end": END,
            },
        )
        builder.add_edge("submit", "judge")

        self.graph = builder.compile()

    def _judge_node(self, state: CoopetitionCentralizedState) -> CoopetitionCentralizedState:
        """Judge node: LLM-backed orchestration of teams."""
        round_num = state["round_number"]
        print(f"\n[Judge Node] Round {round_num}: Orchestrating teams")

        # Get last guess/feedback for context
        last_guess = state["last_guess"] if state["last_guess"] else []
        last_feedback = state["last_feedback"] if state["last_feedback"] else {}
        shared_knowledge = state["shared_knowledge"]
        previous_guesses = [sk["guess"] for sk in shared_knowledge[:-1]] if shared_knowledge else []

        # Judge.run_round() handles everything: proposals, debate, decision
        result = self.judge.run_round(last_guess, last_feedback, previous_guesses, shared_knowledge)

        if result.get("error"):
            print(f"[Judge Node] Error: {result['error']}")
            state["winning_guess"] = last_guess if last_guess else ["red", "blue", "green", "yellow", "white"]
        else:
            state["winning_guess"] = result.get("winning_guess", [])
            print(f"[Judge] Decision: Team {result.get('winning_team')} via {result.get('decision_method')}")
            print(f"[Judge] Reasoning: {result.get('reasoning', 'N/A')}")

        return state

    def _should_continue(self, state: CoopetitionCentralizedState) -> str:
        """Decide if we should continue or end."""
        if state.get("solved") or state.get("game_over"):
            return "end"
        return "continue"

    def _submit_guess_node(self, state: CoopetitionCentralizedState) -> CoopetitionCentralizedState:
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
        if feedback.get("correct_positions") == 5:
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

        initial_state = CoopetitionCentralizedState(
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
