"""
Boss-Worker Orchestrator — LangGraph-based workflow

Architecture:
  1. Start registry HTTP server (port 8100)
  2. Start 4 worker HTTP servers (ports 8101-8104)
     — each self-registers on the registry at startup
  3. Create BossAgent — discovers workers via registry HTTP
  4. LangGraph loop:
       boss_run_round → (submit?) → submit_guess → check_result ⟳
  5. Return results
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, START, END

from registry.registry_server import start_registry_server
from paradigms.boss_worker.agents.agent_server import start_agent_servers
from paradigms.boss_worker.agents.logger_server import start_logger_server
from paradigms.boss_worker.agents.metrics_server import start_metrics_server
from paradigms.boss_worker.agents.boss import BossAgent
from game_engine import GameEngine
from puzzle_generator import load_puzzles


# ── LangGraph State ───────────────────────────────────────────────────────────

class BossWorkerState(TypedDict):
    round_number:      int
    guess_history:     List[Dict[str, Any]]
    last_guess:        List[str]
    last_feedback:     Dict[str, Any]
    solved:            bool
    game_over:         bool
    submit_this_round: bool
    round_result:      Dict[str, Any]


# ── Orchestrator ──────────────────────────────────────────────────────────────

class BossWorkerOrchestrator:
    """LangGraph orchestrator for the Boss-Worker paradigm."""

    MAX_ROUNDS = 8

    def __init__(self, puzzle: Dict[str, Any], provider: str = "ollama"):
        self.puzzle   = puzzle
        self.provider = provider
        self.paradigm = "boss_worker"
        self.start_time = time.time()

        print(f"\n[Orchestrator] Starting Boss-Worker — puzzle {puzzle['puzzle_id']}")

        # ── Start registry ────────────────────────────────────────────────────
        self.registry_url = start_registry_server(port=8100)
        print(f"[Orchestrator] Registry up at {self.registry_url}")

        # ── Start 4 worker servers (each self-registers on startup) ───────────
        self.agent_urls = start_agent_servers(
            provider=provider,
            registry_url=self.registry_url,
            base_port=8101,
        )
        print(f"[Orchestrator] Workers online: {list(self.agent_urls.keys())}")

        # ── Start Logger and Metrics as real A2A agents ───────────────────────
        self.logger_url = start_logger_server(self.registry_url, port=8105)
        self.metrics_url = start_metrics_server(self.registry_url, port=8106)

        # ── Boss LLM agent ────────────────────────────────────────────────────
        self.boss = BossAgent(registry_url=self.registry_url, provider=provider)

        # ── Game engine ───────────────────────────────────────────────────────
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])

        # ── Compile LangGraph ─────────────────────────────────────────────────
        self._graph = self._build_graph()

    # ── Node: boss coordinates a full round ───────────────────────────────────

    def _node_boss_run_round(self, state: BossWorkerState) -> Dict[str, Any]:
        """Boss discovers workers, calls them via A2A, plans, evaluates, returns guess."""
        game_state = {
            "round_number":     state["round_number"],
            "difficulty":       self.puzzle.get("difficulty", "easy"),
            "available_colors": self.puzzle.get("available_colors", []),
            "pegs":             self.puzzle.get("pegs", 4),
            "guess_history":    state["guess_history"],
            "last_guess":       state.get("last_guess", []),
            "last_feedback":    state.get("last_feedback", {}),
        }

        result = self.boss.run_round(game_state)

        return {
            "round_result":      result,
            "submit_this_round": bool(result.get("submit", True)),
            "last_guess":        result.get("guess", []),
        }

    # ── Node: submit guess to game engine ────────────────────────────────────

    def _node_submit_guess(self, state: BossWorkerState) -> Dict[str, Any]:
        """Submit the boss's chosen guess to the game engine."""
        guess = state["last_guess"]

        resp = self.game_engine.submit_guess(guess)

        if not resp.get("valid", False):
            print(f"[Orchestrator] Game engine rejected guess: {resp.get('error')}")
            # Don't count this round — check_result will handle the loop
            return {"submit_this_round": False}

        feedback  = resp.get("feedback", {})
        solved    = resp.get("solved", False)
        game_over = self.game_engine.is_game_over()

        new_entry = {
            "round":    state["round_number"],
            "guess":    guess,
            "feedback": feedback,
        }

        print(
            f"[Orchestrator] Round {state['round_number']} → {guess} | "
            f"pegs={feedback.get('correct_pegs', 0)}  "
            f"pos={feedback.get('correct_positions', 0)}"
            + ("  ✓ SOLVED!" if solved else "")
        )

        return {
            "guess_history": state["guess_history"] + [new_entry],
            "last_feedback": feedback,
            "solved":        solved,
            "game_over":     game_over,
        }

    # ── Node: advance round counter / mark end ────────────────────────────────

    def _node_check_result(self, state: BossWorkerState) -> Dict[str, Any]:
        """Bump round number; flag game_over when limit reached."""
        next_round = state["round_number"] + 1
        game_over  = (
            state.get("solved", False)
            or next_round > self.MAX_ROUNDS
            or state.get("game_over", False)
        )
        return {
            "round_number": next_round,
            "game_over":    game_over,
        }

    # ── Routing ───────────────────────────────────────────────────────────────

    def _route_after_boss(self, state: BossWorkerState) -> str:
        """Submit if boss says so and there's a non-empty guess; otherwise skip."""
        if state.get("submit_this_round", True) and state.get("last_guess"):
            return "submit_guess"
        return "check_result"

    def _route_after_check(self, state: BossWorkerState) -> str:
        """Loop back to boss or end the game."""
        if state.get("solved", False) or state.get("game_over", False):
            return "end"
        return "boss_run_round"

    # ── Graph builder ─────────────────────────────────────────────────────────

    def _build_graph(self) -> Any:
        graph = StateGraph(BossWorkerState)

        graph.add_node("boss_run_round", self._node_boss_run_round)
        graph.add_node("submit_guess",   self._node_submit_guess)
        graph.add_node("check_result",   self._node_check_result)

        graph.add_edge(START, "boss_run_round")

        graph.add_conditional_edges(
            "boss_run_round",
            self._route_after_boss,
            {
                "submit_guess": "submit_guess",
                "check_result": "check_result",
            },
        )

        graph.add_edge("submit_guess", "check_result")

        graph.add_conditional_edges(
            "check_result",
            self._route_after_check,
            {
                "boss_run_round": "boss_run_round",
                "end":            END,
            },
        )

        return graph.compile()

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle and return results."""
        initial_state: BossWorkerState = {
            "round_number":      1,
            "guess_history":     [],
            "last_guess":        [],
            "last_feedback":     {},
            "solved":            False,
            "game_over":         False,
            "submit_this_round": True,
            "round_result":      {},
        }

        final_state = self._graph.invoke(initial_state)

        elapsed       = time.time() - self.start_time
        guess_history = final_state.get("guess_history", [])
        solved        = final_state.get("solved", False)
        # round_number was incremented one past the last played round
        rounds_played = final_state.get("round_number", 1) - 1

        boss_tokens = self.boss.total_input_tokens + self.boss.total_output_tokens

        self.boss.close()

        return {
            "puzzle_id":     self.puzzle["puzzle_id"],
            "paradigm":      self.paradigm,
            "difficulty":    self.puzzle.get("difficulty", "easy"),
            "success":       solved,
            "guesses":       len(guess_history),
            "rounds":        rounds_played,
            "elapsed_time":  elapsed,
            "guess_history": guess_history,
            "message_count": len(self.boss.round_logs),
            "token_usage": {
                "boss":  boss_tokens,
                "total": boss_tokens,
            },
            "agent_stats": {
                "boss": {
                    "calls":  self.boss.call_count,
                    "tokens": boss_tokens,
                },
            },
        }


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("BOSS-WORKER PARADIGM — standalone test")
    print("=" * 70)

    try:
        puzzles     = load_puzzles()
        test_puzzle = next(p for p in puzzles if p["difficulty"] == "easy")

        print(f"\nPuzzle : {test_puzzle['puzzle_id']}")
        print(f"Secret : {test_puzzle['secret_code']}")
        print(f"Colors : {test_puzzle['available_colors']}")

        orchestrator = BossWorkerOrchestrator(test_puzzle, provider="kaggle")
        result       = orchestrator.run()

        print("\n" + "=" * 70)
        print("RESULT")
        print("=" * 70)
        print(f"  Success      : {result['success']}")
        print(f"  Guesses      : {result['guesses']}")
        print(f"  Rounds       : {result['rounds']}")
        print(f"  Elapsed      : {result['elapsed_time']:.1f}s")
        print(f"  A2A rounds   : {result['message_count']}")
        print(f"  Boss tokens  : {result['token_usage']['boss']}")

        print("\nGuess history:")
        for g in result["guess_history"]:
            fb = g["feedback"]
            print(
                f"  Round {g['round']}: {g['guess']}  "
                f"→ pegs={fb.get('correct_pegs',0)}  pos={fb.get('correct_positions',0)}"
            )

    except Exception as exc:
        import traceback
        print(f"\nError: {exc}")
        traceback.print_exc()
