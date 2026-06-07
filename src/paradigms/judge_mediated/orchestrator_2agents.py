"""
Parallel Independent Racing - 2-Agent Optimized Version
- 2 Teams (optimized for cost/performance)
- 2 Agents per team (Analyzer-Strategist + Proposer)
- Each team solves INDEPENDENTLY with their own puzzle instance
- Both guesses submitted SIMULTANEOUSLY
- Winner: First team to solve (by round count, not time)
- Judge provides LEADERBOARD ONLY (no guess interference)
"""

import sys
import time
import asyncio
import httpx
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from communication.a2a_message import A2AMessage
from paradigms.judge_mediated.agents.judge import JudgeAgent
from paradigms.judge_mediated.agents.agent_server_2agents import start_agent_servers
from game_engine import GameEngine
from puzzle_generator import load_puzzles


class TwoAgentOrchestrator:
    """Orchestrator for 2-agent per-team architecture with 2 teams."""

    NUM_TEAMS = 2
    MAX_ROUNDS = 8

    def __init__(self, puzzle: Dict[str, Any], provider: str = "deepseek"):
        self.puzzle = puzzle
        self.provider = provider
        self.paradigm = "parallel_independent_racing"
        self.start_time = time.time()

        # ⭐ CRITICAL FIX: Kill any existing server processes
        print(f"[Orchestrator] Cleaning up any stale server processes...")
        import subprocess
        try:
            # Kill processes using specific ports
            for port in [8301, 8302, 8351, 8352]:
                subprocess.run(f"lsof -ti :{port} | xargs kill -9", shell=True, timeout=2)
        except:
            pass
        time.sleep(1)  # Wait for ports to be released by OS

        print(f"\n[Orchestrator] Starting Parallel Independent Racing — puzzle {puzzle['puzzle_id']}")
        print(f"[Orchestrator] Teams: {self.NUM_TEAMS}, Agents per team: 2")
        print(f"[Orchestrator] ⚡ Each team solves their own puzzle instance independently")

        # Team management
        self.team_analyzer_urls: Dict[int, str] = {}
        self.team_proposer_urls: Dict[int, str] = {}
        self.team_histories: Dict[int, List[Dict[str, Any]]] = {
            i: [] for i in range(1, self.NUM_TEAMS + 1)
        }
        self.team_last_feedback: Dict[int, Dict[str, Any]] = {
            i: {} for i in range(1, self.NUM_TEAMS + 1)
        }

        # ⭐ Judge provides LEADERBOARD only (no guess interference)
        self.judge = JudgeAgent(provider=provider)
        if hasattr(self.judge, 'llm_available') and not self.judge.llm_available:
            print(f"[Orchestrator] Judge online (leaderboard + competitive analysis)")
        else:
            print(f"[Orchestrator] Judge online with {provider} LLM")

        # ⭐ PARALLEL INDEPENDENT RACING: Each team gets their OWN game engine!
        # Both teams solve the SAME puzzle (same secret) but with independent game instances
        self.team_game_engines: Dict[int, GameEngine] = {}
        for team_id in range(1, self.NUM_TEAMS + 1):
            self.team_game_engines[team_id] = GameEngine(
                puzzle.get("secret_code", []),
                puzzle.get("difficulty", "easy")
            )
            print(f"[Orchestrator] Created game engine for Team {team_id}")

        # Track which teams have solved
        self.team_solved: Dict[int, bool] = {i: False for i in range(1, self.NUM_TEAMS + 1)}
        self.team_solve_round: Dict[int, int] = {i: None for i in range(1, self.NUM_TEAMS + 1)}

        # ⭐ BOSS-WORKER STATE: Maintain locked positions per team
        # This is the key to preventing oscillation!
        self.team_locked_positions: Dict[int, Dict[int, str]] = {
            i: {} for i in range(1, self.NUM_TEAMS + 1)
        }
        self.team_colors_in: Dict[int, set] = {
            i: set() for i in range(1, self.NUM_TEAMS + 1)
        }
        self.team_colors_out: Dict[int, set] = {
            i: set() for i in range(1, self.NUM_TEAMS + 1)
        }

    def _extract_locked_positions(self, guess: List[str], feedback: Dict[str, Any]) -> Dict[int, str]:
        """Extract which positions are locked based on guess and feedback.

        A position is locked when:
        1. That peg color exists in the code (correct_pegs > 0 for that color)
        2. The feedback says we got correct_positions > 0
        3. We can infer which position(s) from the guess

        For now, use a heuristic: if we got N positions correct and N > 0,
        those positions match the guess at those indices.
        """
        # This is simplified - in practice you'd need to track which exact positions
        # For now, return empty dict and update from feedback pattern
        locked = {}

        # If we got correct_positions feedback and previously found certain positions,
        # they're likely still locked
        # This will be populated by analyzing multiple guesses
        return locked

    def _update_team_game_state(self, team_id: int, guess: List[str], feedback: Dict[str, Any]) -> None:
        """Update team's game state based on guess and feedback (Boss-Worker pattern)."""
        correct_pegs = feedback.get("feedback", {}).get("correct_pegs", 0)
        correct_positions = feedback.get("feedback", {}).get("correct_positions", 0)

        # Heuristic: If we got correct_positions and the guess has a stable pattern,
        # mark those positions as locked
        if correct_positions > 0 and guess:
            # For now, we'll trust the guess positions that gave us correct_positions
            # A more sophisticated approach would track position stability across rounds
            pass

        # Note: Full locked position extraction requires solving the permutation matching
        # problem, which is what the LLM is trying to solve.
        # We'll enhance this as we learn more patterns.

    def _initialize_infrastructure(self) -> None:
        """Start agent servers for both teams."""
        print(f"\n[Orchestrator] Starting agent servers...")
        sys.stdout.flush()

        for team_id in range(1, self.NUM_TEAMS + 1):
            print(f"[Orchestrator] Initializing Team {team_id}...")
            sys.stdout.flush()
            urls = start_agent_servers(
                provider=self.provider,
                team_id=team_id,
                base_port=8301,
            )
            self.team_analyzer_urls[team_id] = urls["analyzer_url"]
            self.team_proposer_urls[team_id] = urls["proposer_url"]
            print(f"[Orchestrator] Team {team_id} registered: {urls}")
            sys.stdout.flush()

        print(f"[Orchestrator] All {self.NUM_TEAMS} teams initialized (2 agents each)")
        sys.stdout.flush()

    async def _run_team_round(self, team_id: int, round_num: int, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Run one team's 2-agent pipeline in a round."""
        try:
            print(f"[DEBUG] Team {team_id} Round {round_num}: Starting 2-agent pipeline")

            # Build competitive analysis for this team
            competitive_analysis = {}
            for other_team_id in range(1, self.NUM_TEAMS + 1):
                if other_team_id != team_id and self.team_histories[other_team_id]:
                    latest = self.team_histories[other_team_id][-1]
                    competitive_analysis[f"team_{other_team_id}"] = {
                        "colors_found": latest.get("result", {}).get("correct_pegs", 0),
                        "positions_locked": latest.get("result", {}).get("correct_positions", 0),
                        "strategy": "Testing colors and positions",
                    }

            # ⭐ NOTE: Agent manages its own memory now (no debug output needed)

            # Call agent servers (client reused across rounds for efficiency)
            # STEP 1: Call Analyzer-Strategist
            # ⭐ CRITICAL FIX: Pass full history with feedback, not just guesses!
            # Position detection algorithm needs both guesses AND feedback to work
            full_history = []
            for entry in self.team_histories[team_id]:
                full_history.append({
                    "guess": entry.get("guess", []),
                    "feedback": entry.get("result", {}),  # The game feedback with correct_pegs/correct_positions
                })

            analyzer_msg = A2AMessage.request(
                sender_id="orchestrator",
                receiver_id=f"analyzer-{team_id}",
                action="analyze_and_strategize",
                payload={
                    "guess_history": full_history,  # Now includes feedback!
                    "last_feedback": self.team_last_feedback[team_id],
                    "competitive_analysis": competitive_analysis,
                    "difficulty": self.puzzle.get("difficulty", "easy"),
                    "available_colors": self.puzzle.get("available_colors", []),
                    "num_pegs": self.puzzle.get("pegs", 4),
                    "round_num": round_num,  # ⭐ Pass current round number
                }
            )

            print(f"[DEBUG] Team {team_id} Round {round_num}: Calling Analyzer at {self.team_analyzer_urls[team_id]}")
            sys.stdout.flush()

            analyzer_response = await client.post(
                self.team_analyzer_urls[team_id] + "/analyze_and_strategize",
                json=analyzer_msg.to_dict(),
                timeout=350.0
            )

            # DEBUG: Check response format
            response_json = analyzer_response.json()
            if "message" in response_json and "message_id" not in response_json:
                print(f"[DEBUG] Team {team_id} analyzer response has 'message' field but no 'message_id':")
                print(f"  Response keys: {list(response_json.keys())}")
                print(f"  Full response: {response_json}")

            analyzer_result = A2AMessage.from_dict(response_json).payload
            strategy_desc = analyzer_result.get("strategy", "")[:60]
            print(f"[DEBUG] Team {team_id} Analyzer: strategy = {strategy_desc}...")
            sys.stdout.flush()

            # ⭐ REMOVED: No longer storing analysis_history here!
            # Analyzer maintains its own memory now (stateful agent)

            # ⭐ REFLECTION/LEARNING: Get last feedback for hypothesis validation
            last_feedback = {}
            if round_num > 1 and team_id in self.team_histories:
                history = self.team_histories[team_id]
                if history:
                    last_entry = history[-1]
                    last_feedback = last_entry.get("result", {})  # ⭐ FIX: stored as "result", not "feedback"
                    print(f"[DEBUG] Team {team_id} Round {round_num}: last_feedback from history = {last_feedback}")

            # STEP 2: Call Proposer with strategy AND cumulative constraints
            proposer_msg = A2AMessage.request(
                sender_id="orchestrator",
                receiver_id=f"proposer-{team_id}",
                action="propose_guess",
                payload={
                    "strategy": analyzer_result,  # ⭐ Now includes cumulative_constraints
                    "last_feedback": last_feedback,  # ⭐ NEW: For reflection/learning
                    "available_colors": self.puzzle.get("available_colors", []),
                    "num_pegs": self.puzzle.get("pegs", 4),
                    "round_num": round_num,
                }
            )

            print(f"[DEBUG] Team {team_id} Round {round_num}: Calling Proposer")
            sys.stdout.flush()

            proposer_response = await client.post(
                self.team_proposer_urls[team_id] + "/propose_guess",
                json=proposer_msg.to_dict(),
                timeout=300.0
            )

            proposer_result = A2AMessage.from_dict(proposer_response.json()).payload
            guess = proposer_result.get("guess", [])

            print(f"[DEBUG] Team {team_id} proposed: {guess}")
            sys.stdout.flush()

            return {
                "team_id": team_id,
                "guess": guess,
                "analysis": analyzer_result.get("strategy", ""),
                "constraints": analyzer_result,
            }

        except Exception as e:
            print(f"[ERROR] Team {team_id} Round {round_num}: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            return {
                "team_id": team_id,
                "guess": [],
                "analysis": f"Error: {str(e)}",
                "constraints": {},
            }

    async def _run_round(self, client: httpx.AsyncClient) -> bool:
        """Run one complete round: all teams solve in parallel."""
        round_num = len(self.team_histories[1]) + 1
        print(f"[DEBUG] Starting round {round_num}, MAX_ROUNDS={self.MAX_ROUNDS}")

        if round_num > self.MAX_ROUNDS:
            return False

        print(f"\n[Round {round_num}] Running {self.NUM_TEAMS} teams in parallel...")

        try:
            team_tasks = [
                self._run_team_round(team_id=team_id, round_num=round_num, client=client)
                for team_id in range(1, self.NUM_TEAMS + 1)
            ]
            team_results = await asyncio.gather(*team_tasks)
            print(f"[DEBUG] Got team results: {len(team_results)} teams")
        except Exception as e:
            print(f"[ERROR] Gathering team results failed: {str(e)}")
            raise

        try:
            # ⭐ PARALLEL INDEPENDENT RACING: Extract guesses from both teams
            guesses_by_team = {r["team_id"]: r["guess"] for r in team_results}
            print(f"[DEBUG] Team guesses extracted: {guesses_by_team}")
            sys.stdout.flush()

            # ⭐ SUBMIT BOTH GUESSES IN PARALLEL to separate game engines
            print(f"[Round {round_num}] Submitting both teams' guesses SIMULTANEOUSLY...")
            sys.stdout.flush()

            feedback_by_team = {}
            for team_id in range(1, self.NUM_TEAMS + 1):
                guess = guesses_by_team[team_id]
                feedback = self.team_game_engines[team_id].submit_guess(guess)
                feedback_by_team[team_id] = feedback
                print(f"[DEBUG] Team {team_id} feedback: {feedback.get('feedback', {})}")

                # ⭐ ACTIVE LEARNING: Call reflect_on_feedback to build learned hypotheses
                try:
                    reflect_msg = A2AMessage.request(
                        sender_id="orchestrator",
                        receiver_id=f"proposer-{team_id}",
                        action="reflect_on_feedback",
                        payload={
                            "round_num": round_num,
                            "guess": guess,
                            "feedback": feedback.get("feedback", {}),
                        }
                    )
                    await client.post(
                        self.team_proposer_urls[team_id] + "/reflect_on_feedback",
                        json=reflect_msg.to_dict(),
                        timeout=30.0
                    )
                except Exception as e:
                    print(f"[DEBUG] Team {team_id} reflection failed (non-critical): {e}")

                sys.stdout.flush()

        except Exception as e:
            print(f"[ERROR] Processing results: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            raise

        # Validate all guesses
        for team_id, feedback in feedback_by_team.items():
            if not feedback.get("valid", False):
                print(f"[ERROR] Team {team_id} invalid guess: {feedback.get('error', 'Unknown error')}")

        # ⭐ BUILD LEADERBOARD: Show each team's progress (NO ranking, NO interference)
        leaderboard = []
        for team_id in range(1, self.NUM_TEAMS + 1):
            feedback = feedback_by_team[team_id]
            game_fb = feedback.get("feedback", {})
            correct_pegs = game_fb.get("correct_pegs", 0)
            correct_positions = game_fb.get("correct_positions", 0)
            solved = feedback.get("solved", False)

            # Update solve status
            if solved and not self.team_solved[team_id]:
                self.team_solved[team_id] = True
                self.team_solve_round[team_id] = round_num
                print(f"🏆 Team {team_id} SOLVED in round {round_num}!")

            leaderboard.append({
                "team_id": team_id,
                "round": round_num,
                "guess": guesses_by_team[team_id],
                "correct_pegs": correct_pegs,
                "correct_positions": correct_positions,
                "solved": solved,
            })

        # ⭐ Judge provides competitive feedback (optional LLM analysis)
        competitive_feedback = {}
        if self.judge:
            try:
                competitive_feedback = self.judge.generate_leaderboard_feedback(
                    leaderboard=leaderboard,
                    all_team_histories=self.team_histories,
                    pegs_to_solve=self.puzzle.get("pegs", 4),
                )
            except Exception as e:
                print(f"[DEBUG] Judge feedback failed (non-critical): {e}")

        # Update histories (each team gets ONLY their own feedback + leaderboard)
        for team_id in range(1, self.NUM_TEAMS + 1):
            feedback = feedback_by_team[team_id]
            game_fb = feedback.get("feedback", {})

            team_feedback = {
                "correct_pegs": game_fb.get("correct_pegs", 0),
                "correct_positions": game_fb.get("correct_positions", 0),
                "solved": feedback.get("solved", False),
                "round": round_num,
                # ⭐ Leaderboard shows opponent's progress (no guess details, just round count)
                "leaderboard": [
                    {
                        "team": f"Team {item['team_id']}",
                        "round": item['round'],
                        "colors_found": item['correct_pegs'],
                        "positions_locked": item['correct_positions'],
                        "solved": item['solved'],
                    }
                    for item in leaderboard
                ],
                "competitive_feedback": competitive_feedback.get(f"team_{team_id}", ""),
            }

            self.team_histories[team_id].append({
                "round": round_num,
                "guess": guesses_by_team[team_id],
                "result": game_fb,
                "solved": feedback.get("solved", False),
            })

            self.team_last_feedback[team_id] = team_feedback
            sys.stdout.flush()

        # Print leaderboard
        print(f"\n[Round {round_num}] 📊 LEADERBOARD:")
        for item in leaderboard:
            status = "✅ SOLVED" if item["solved"] else f"{item['correct_pegs']}P/{item['correct_positions']}L"
            print(f"  Team {item['team_id']}: {status}")

        # Check if any team has solved
        any_solved = any(self.team_solved.values())
        if any_solved:
            winner_id = next(team_id for team_id in range(1, self.NUM_TEAMS + 1) if self.team_solved[team_id])
            print(f"\n🏆 Team {winner_id} WINS in round {self.team_solve_round[winner_id]}!")
            return True
        else:
            return False

    async def _run_async_loop(self) -> bool:
        """Main async round loop."""
        # ⭐ CREATE CLIENT ONCE and reuse across all rounds
        # This prevents event loop issues from repeated client creation/destruction
        async with httpx.AsyncClient(timeout=350.0) as client:
            for _ in range(self.MAX_ROUNDS):
                solved = await self._run_round(client=client)
                if solved:
                    return True
            return False

    def run(self) -> Dict[str, Any]:
        """Run the competition."""
        self._initialize_infrastructure()

        print(f"\n[Orchestrator] Starting async round loop (max {self.MAX_ROUNDS} rounds)...")
        sys.stdout.flush()
        try:
            solved = asyncio.run(self._run_async_loop())
        except Exception as e:
            print(f"[Orchestrator] Error: {e}")
            solved = False

        elapsed_time = time.time() - self.start_time

        # ⭐ Determine winner (first team to solve)
        winner_id = None
        winning_round = None
        for team_id in range(1, self.NUM_TEAMS + 1):
            if self.team_solved[team_id]:
                winner_id = team_id
                winning_round = self.team_solve_round[team_id]
                break

        return {
            "success": solved,
            "winner": winner_id,
            "winning_round": winning_round,
            "paradigm": "parallel_independent_racing",
            "teams": {
                team_id: {
                    "rounds": len(self.team_histories[team_id]),
                    "guesses": len(self.team_histories[team_id]),
                    "solved": self.team_solved[team_id],
                    "solve_round": self.team_solve_round[team_id],
                    "final_stats": self.team_histories[team_id][-1].get("result", {}) if self.team_histories[team_id] else {},
                }
                for team_id in range(1, self.NUM_TEAMS + 1)
            },
            "time": elapsed_time,
        }


if __name__ == "__main__":
    import os

    provider = os.getenv("PROVIDER", "deepseek")

    puzzles = load_puzzles()
    # Find MM_001 (easy) for testing
    puzzle = next((p for p in puzzles if p['puzzle_id'] == 'MM_001'), puzzles[0])

    print("\n" + "=" * 80)
    print("PARALLEL INDEPENDENT RACING (2 Teams, 2 Agents Each)")
    print("=" * 80)
    print(f"\nTesting puzzle: {puzzle['puzzle_id']}")
    print(f"Difficulty: {puzzle['difficulty']}")
    print(f"Provider: {provider}\n")

    orchestrator = TwoAgentOrchestrator(puzzle, provider=provider)
    result = orchestrator.run()

    print("\n" + "=" * 80)
    print("GAME OVER")
    print("=" * 80)
    if result["success"]:
        print(f"✅ Team {result['winner']} SOLVED in {result['winning_round']} rounds!")
    else:
        print(f"❌ NO WINNER - Not solved after max rounds")

    print(f"\n📊 FINAL RESULTS:")
    for team_id, stats in result["teams"].items():
        status = "✅ SOLVED" if stats["solved"] else "❌ Not solved"
        solve_round = stats["solve_round"] if stats["solve_round"] else "N/A"
        print(f"  Team {team_id}: {stats['rounds']} rounds, {status} (Round {solve_round})")

    print(f"\nTotal time: {result['time']:.1f} seconds")
    print(f"Paradigm: {result['paradigm']}")
