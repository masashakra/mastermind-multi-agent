"""
Direct Debate with Judge Feedback Orchestrator — LangGraph-based workflow

Architecture:
  1. Start registry HTTP server
  2. Start two team agents as HTTP servers
  3. Agents discover each other via registry
  4. LangGraph loop:
       collect_proposals → judge_decision → submit_guess → check_result ⟳
  5. First team to have their proposal be selected AND correct wins

Key difference from direct_debate: Judge selection of guesses, not first-to-submit.
"""

import sys
import os
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Any, Dict, List, TypedDict
import httpx

from langgraph.graph import StateGraph, START, END

from registry.registry_server import start_registry_server
from paradigms.direct_debate_judge_feedback.agents.agent_server import start_agent_servers
from paradigms.direct_debate_judge_feedback.agents.judge import JudgeAgent
from game_engine import GameEngine
from puzzle_generator import load_puzzles


# ── LangGraph State ───────────────────────────────────────────────────────────

class DebateJudgeState(TypedDict):
    round_number:      int
    guess_history:     List[Dict[str, Any]]
    last_guess:        List[str]
    last_feedback:     Dict[str, Any]
    last_selected_team: str
    proposals:         List[Dict[str, Any]]
    judge_decision:    Dict[str, Any]
    solved:            bool
    game_over:         bool
    submit_this_round: bool
    round_result:      Dict[str, Any]


class DirectDebateJudgeFeedbackOrchestrator:
    """LangGraph orchestrator for Direct Debate with Judge Feedback.

    Role: Coordinate proposal collection, judge selection, and game state.
    """

    MAX_ROUNDS = 16

    def __init__(self, puzzle: Dict[str, Any], provider: str = "deepseek", run_tag: str = ""):
        self.puzzle = puzzle
        self.provider = provider
        self.paradigm = "direct_debate_judge_feedback"
        self.start_time = time.time()

        print(f"\n[Orchestrator] Starting Direct Debate with Judge Feedback — puzzle {puzzle['puzzle_id']}")

        # ── Initialize message logger ─────────────────────────────────────────
        puzzle_id = puzzle.get("puzzle_id", "unknown")
        tag = f"_{run_tag}" if run_tag else ""
        log_file = f"logs/{puzzle_id}_dd_judge_feedback_{provider}{tag}_messages.log"
        from communication.message_logger import init_message_logger
        self.message_logger = init_message_logger(log_file)
        print(f"[Orchestrator] Logging to {log_file}")

        # ── Start registry ────────────────────────────────────────────────────
        import socket
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", 0))
        registry_port = sock.getsockname()[1]
        sock.close()
        self.registry_url = start_registry_server(port=registry_port)
        print(f"[Orchestrator] Registry up at {self.registry_url}")

        time.sleep(1.0)

        # ── Start team agent servers ──────────────────────────────────────────
        self.team_urls = start_agent_servers(
            provider=provider,
            registry_url=self.registry_url,
            base_port=8601,
            num_teams=2,  # Fixed to 2 teams
            orchestrator_url="",
        )
        self.team_ids = list(self.team_urls.keys())
        print(f"[Orchestrator] Teams online: {self.team_ids}")

        # ── Initialize Judge ──────────────────────────────────────────────────
        self.judge = JudgeAgent(provider=provider)
        print(f"[Orchestrator] Judge initialized with {provider}")

        # ── Game engine ───────────────────────────────────────────────────────
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])

        # ── Compile LangGraph ─────────────────────────────────────────────────
        self._graph = self._build_graph()

    # ── Node: collect proposals from both teams ──────────────────────────────

    def _node_collect_proposals(self, state: DebateJudgeState) -> Dict[str, Any]:
        """Request proposals from both teams concurrently."""
        import concurrent.futures

        print(f"\n[Orchestrator] Round {state['round_number']} → Collecting proposals...")

        def get_proposal(team_id: str) -> Dict[str, Any]:
            url = self.team_urls[team_id]
            try:
                response = httpx.post(
                    f"{url}/get_proposal",
                    json={
                        "round": state["round_number"],
                        "shared_history": state["guess_history"][-5:],
                        "difficulty": self.puzzle.get("difficulty", "easy"),
                        "available_colors": self.puzzle.get("available_colors", ["red", "blue", "green", "yellow", "white", "black"]),
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    proposal = response.json().get("proposal", {})
                    proposal["team"] = team_id
                    return proposal
            except Exception as e:
                print(f"[Orchestrator] Error getting proposal from {team_id}: {e}")
            return None

        proposals = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(get_proposal, team_id): team_id for team_id in self.team_ids}
            for future in concurrent.futures.as_completed(futures):
                proposal = future.result()
                if proposal:
                    proposals.append(proposal)

        return {"proposals": proposals}

    # ── Node: judge evaluates and selects ──────────────────────────────────

    def _node_judge_decision(self, state: DebateJudgeState) -> Dict[str, Any]:
        """Judge evaluates proposals and selects the better one."""
        from communication.message_logger import get_message_logger
        logger = get_message_logger()

        proposals = state["proposals"]

        if not proposals or len(proposals) < 2:
            print(f"[Orchestrator] Insufficient proposals, skipping round")
            if logger:
                logger.log_custom_event(
                    event_type="judge_error",
                    agent_name="Judge",
                    status="error",
                    error="Insufficient proposals",
                    metadata={"round": state["round_number"], "proposal_count": len(proposals)}
                )
            return {
                "judge_decision": None,
                "submit_this_round": False,
            }

        proposal_a = proposals[0]
        proposal_b = proposals[1]

        print(f"  Team A proposes: {proposal_a.get('guess')} (confidence: {proposal_a.get('confidence')}%)")
        print(f"  Team B proposes: {proposal_b.get('guess')} (confidence: {proposal_b.get('confidence')}%)")

        # Log proposals received
        if logger:
            logger.log_custom_event(
                event_type="proposals_received",
                agent_name="Judge",
                metadata={
                    "round": state["round_number"],
                    "proposal_a": {
                        "team": proposal_a.get("team"),
                        "guess": proposal_a.get("guess"),
                        "confidence": proposal_a.get("confidence"),
                    },
                    "proposal_b": {
                        "team": proposal_b.get("team"),
                        "guess": proposal_b.get("guess"),
                        "confidence": proposal_b.get("confidence"),
                    },
                }
            )

        # Judge evaluates
        judge_decision = self.judge.evaluate_and_select(
            proposal_a=proposal_a,
            proposal_b=proposal_b,
            shared_history=state["guess_history"],
        )

        selected_team = judge_decision.get("selected_team", "")
        winning_guess = judge_decision.get("winning_guess", [])

        print(f"  [Judge] Selected {selected_team}: {winning_guess}")

        # Log judge decision
        if logger:
            logger.log_custom_event(
                event_type="judge_decision",
                agent_name="Judge",
                metadata={
                    "round": state["round_number"],
                    "selected_team": selected_team,
                    "winning_guess": winning_guess,
                    "reasoning": judge_decision.get("reasoning", "")[:200],
                    "confidence": judge_decision.get("confidence", 0),
                }
            )

        return {
            "judge_decision": judge_decision,
            "last_guess": winning_guess,
            "last_selected_team": selected_team,
            "submit_this_round": bool(winning_guess),
        }

    # ── Node: submit judge's selected guess ────────────────────────────────

    def _node_submit_guess(self, state: DebateJudgeState) -> Dict[str, Any]:
        """Submit judge's selected guess to the game engine."""
        from communication.message_logger import get_message_logger
        logger = get_message_logger()

        guess = state["last_guess"]
        selected_team = state["last_selected_team"]

        # Log guess submission
        if logger:
            logger.log_custom_event(
                event_type="guess_submission",
                agent_name="Orchestrator",
                metadata={
                    "round": state["round_number"],
                    "selected_team": selected_team,
                    "guess": guess,
                }
            )

        resp = self.game_engine.submit_guess(guess)

        if not resp.get("valid", False):
            print(f"[Orchestrator] Game engine rejected guess: {resp.get('error')}")
            if logger:
                logger.log_custom_event(
                    event_type="guess_invalid",
                    agent_name="Orchestrator",
                    status="error",
                    error=resp.get("error"),
                    metadata={
                        "round": state["round_number"],
                        "guess": guess,
                    }
                )
            return {"submit_this_round": False}

        feedback = resp.get("feedback", {})
        solved = resp.get("solved", False)

        new_entry = {
            "round": state["round_number"],
            "selected_team": selected_team,
            "guess": guess,
            "feedback": feedback,
        }

        pegs = feedback.get("correct_pegs", 0)
        pos = feedback.get("correct_positions", 0)
        print(
            f"  Feedback: {guess} → {pegs}p {pos}pos"
            + ("  ✅ SOLVED!" if solved else "")
        )

        # Log feedback
        if logger:
            logger.log_custom_event(
                event_type="guess_feedback",
                agent_name="Orchestrator",
                metadata={
                    "round": state["round_number"],
                    "selected_team": selected_team,
                    "guess": guess,
                    "correct_pegs": pegs,
                    "correct_positions": pos,
                    "solved": solved,
                }
            )

        return {
            "guess_history": state["guess_history"] + [new_entry],
            "last_feedback": feedback,
            "solved": solved,
        }

    # ── Node: check result and advance round ─────────────────────────────

    def _node_check_result(self, state: DebateJudgeState) -> Dict[str, Any]:
        """Bump round number; flag game_over when limit reached."""
        next_round = state["round_number"] + 1
        game_over = (
            state.get("solved", False)
            or next_round > self.MAX_ROUNDS
        )
        return {
            "round_number": next_round,
            "game_over": game_over,
        }

    # ── Routing ───────────────────────────────────────────────────────────

    def _route_after_judge(self, state: DebateJudgeState) -> str:
        """Submit if judge found valid guess; otherwise skip to check_result."""
        if state.get("submit_this_round", False) and state.get("last_guess"):
            return "submit_guess"
        return "check_result"

    def _route_after_check(self, state: DebateJudgeState) -> str:
        """Loop back to collect_proposals or end the game."""
        if state.get("solved", False) or state.get("game_over", False):
            return "end"
        return "collect_proposals"

    # ── Graph builder ─────────────────────────────────────────────────────

    def _build_graph(self) -> Any:
        """Build LangGraph workflow."""
        graph = StateGraph(DebateJudgeState)

        graph.add_node("collect_proposals", self._node_collect_proposals)
        graph.add_node("judge_decision", self._node_judge_decision)
        graph.add_node("submit_guess", self._node_submit_guess)
        graph.add_node("check_result", self._node_check_result)

        graph.add_edge(START, "collect_proposals")

        graph.add_edge("collect_proposals", "judge_decision")

        graph.add_conditional_edges(
            "judge_decision",
            self._route_after_judge,
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
                "collect_proposals": "collect_proposals",
                "end": END,
            },
        )

        return graph.compile()

    # ── Public entry point ────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """Run puzzle with LangGraph workflow."""
        print(f"\n[Orchestrator] Starting puzzle execution...")
        print(f"[Orchestrator] Judge will select the strongest guess each round")
        print(f"[Orchestrator] First team to have their guess solve it wins! 🏁\n")

        # Initialize state
        initial_state: DebateJudgeState = {
            "round_number": 1,
            "guess_history": [],
            "last_guess": [],
            "last_feedback": {},
            "last_selected_team": "",
            "proposals": [],
            "judge_decision": {},
            "solved": False,
            "game_over": False,
            "submit_this_round": False,
            "round_result": {},
        }

        # Run the graph
        final_state = self._graph.invoke(initial_state)

        elapsed = time.time() - self.start_time

        # Build results
        winner = None
        for entry in final_state["guess_history"]:
            if entry.get("solved"):
                winner = entry.get("selected_team")
                break

        return {
            "puzzle_id": self.puzzle["puzzle_id"],
            "paradigm": self.paradigm,
            "difficulty": self.puzzle.get("difficulty", "easy"),
            "success": final_state.get("solved", False),
            "winner": winner,
            "total_rounds": final_state["round_number"] - 1,
            "all_guesses": final_state["guess_history"],
            "elapsed_time": elapsed,
        }



if __name__ == "__main__":
    print("=" * 70)
    print("DIRECT DEBATE WITH JUDGE FEEDBACK — LangGraph-based")
    print("=" * 70)

    try:
        puzzles = load_puzzles()
        puzzle_map = {p["puzzle_id"]: p for p in puzzles}
        target_id = os.environ.get("DD_JF_PUZZLE_ID")
        if target_id and target_id in puzzle_map:
            test_puzzle = puzzle_map[target_id]
        else:
            import random
            easy_puzzles = [p for p in puzzles if p["difficulty"] == "easy"]
            test_puzzle = random.choice(easy_puzzles)

        print(f"Puzzle : {test_puzzle['puzzle_id']}")
        print(f"Secret : {test_puzzle['secret_code']}")

        orchestrator = DirectDebateJudgeFeedbackOrchestrator(
            test_puzzle, provider="deepseek"
        )
        result = orchestrator.run()

        print("\n" + "=" * 70)
        print("RESULT")
        print("=" * 70)
        print(f"Winner          : {result['winner']} 🏆" if result['winner'] else "No winner")
        print(f"Total Rounds    : {result['total_rounds']}")
        print(f"Elapsed Time    : {result['elapsed_time']:.1f}s")
        print(f"Puzzle Solved   : {'YES ✅' if result['success'] else 'NO ❌'}")

        if result['all_guesses']:
            print(f"\n📊 Guess History:")
            for i, guess_entry in enumerate(result['all_guesses'], 1):
                team = guess_entry.get('selected_team', 'unknown')
                guess = guess_entry.get('guess', [])
                fb = guess_entry.get('feedback', {})
                solved = "✅ SOLVED!" if guess_entry.get('feedback', {}).get('correct_pegs') == 4 else ""
                print(f"  {i}. {team}: {guess} → {fb.get('correct_pegs')}p {fb.get('correct_positions')}pos {solved}")

    except Exception as exc:
        import traceback
        print(f"\nError: {exc}")
        traceback.print_exc()
