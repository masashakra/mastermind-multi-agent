"""
Judge-Mediated Speed Racing - 2-Agent Optimized Version
- 2 Teams (optimized for cost/performance)
- 2 Agents per team (Analyzer-Strategist + Proposer)
- Enhanced Judge with competitive intelligence
- Cost: ~35-40 LLM calls total (vs 96 for 4-agent)
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
        self.paradigm = "judge_mediated_2agents"
        self.start_time = time.time()

        print(f"\n[Orchestrator] Starting 2-Agent Judge-Mediated — puzzle {puzzle['puzzle_id']}")
        print(f"[Orchestrator] Teams: {self.NUM_TEAMS}, Agents per team: 2")

        # Team management
        self.team_analyzer_urls: Dict[int, str] = {}
        self.team_proposer_urls: Dict[int, str] = {}
        self.team_histories: Dict[int, List[Dict[str, Any]]] = {
            i: [] for i in range(1, self.NUM_TEAMS + 1)
        }
        self.team_last_feedback: Dict[int, Dict[str, Any]] = {
            i: {} for i in range(1, self.NUM_TEAMS + 1)
        }

        # ⭐ REMOVED: team_analysis_histories - Agents now manage their own memory!

        # Judge doesn't need provider since we skip LLM calls
        try:
            self.judge = JudgeAgent(provider=provider)
        except ValueError:
            # No API keys available - create judge without provider
            print(f"[Orchestrator] Judge: No API keys, using hardcoded rankings")
            sys.stdout.flush()
            # We'll use inline ranking instead
            self.judge = None

        self.game_engine = GameEngine(puzzle.get("secret_code", []), puzzle.get("difficulty", "easy"))

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
            analyzer_msg = A2AMessage.request(
                sender_id="orchestrator",
                receiver_id=f"analyzer-{team_id}",
                action="analyze_and_strategize",
                payload={
                    "guess_history": [g.get("guess", []) for g in self.team_histories[team_id]],
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

            analyzer_result = A2AMessage.from_dict(analyzer_response.json()).payload
            strategy_desc = analyzer_result.get("strategy", "")[:60]
            print(f"[DEBUG] Team {team_id} Analyzer: strategy = {strategy_desc}...")
            sys.stdout.flush()

            # ⭐ REMOVED: No longer storing analysis_history here!
            # Analyzer maintains its own memory now (stateful agent)

            # STEP 2: Call Proposer with strategy
            proposer_msg = A2AMessage.request(
                sender_id="orchestrator",
                receiver_id=f"proposer-{team_id}",
                action="propose_guess",
                payload={
                    "strategy": analyzer_result,
                    "available_colors": self.puzzle.get("available_colors", []),
                    "num_pegs": self.puzzle.get("pegs", 4),
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
            # Extract guesses
            guesses = [r["guess"] for r in team_results]
            print(f"[DEBUG] Extracted guesses: {guesses}")
            sys.stdout.flush()

            # FIRST: Submit top team's guess to get feedback
            # For now, just use Team 1's guess (or better: use Judge to pick)
            # TODO: Let judge pick which team's guess to submit
            top_team_id = 1  # Default to Team 1
            top_guess = guesses[top_team_id - 1]

            print(f"[DEBUG] Submitting Team {top_team_id}'s guess: {top_guess}")
            sys.stdout.flush()

            feedback = self.game_engine.submit_guess(top_guess)
            print(f"[DEBUG] Got feedback: {feedback}")
            sys.stdout.flush()
        except Exception as e:
            print(f"[ERROR] Processing results: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            raise

        if not feedback.get("valid", False):
            print(f"[ERROR] Invalid guess: {feedback.get('error', 'Unknown error')}")
            return False

        # SECOND: Now rank teams with actual feedback
        if self.judge:
            ranking = self.judge.rank_teams(
                team_results=[
                    {
                        "team_id": r["team_id"],
                        "guess": r["guess"],
                        "feedback": feedback.get("feedback", {}),  # NOW we have actual feedback!
                    }
                    for r in team_results
                ],
                all_team_histories=self.team_histories,
                pegs_to_solve=self.puzzle.get("pegs", 4),
            )
        else:
            # Hardcoded ranking when Judge unavailable
            ranking = []
            for r in team_results:
                team_id = r["team_id"]
                correct_pos = feedback.get("feedback", {}).get("correct_positions", 0)
                distance = self.puzzle.get("pegs", 4) - correct_pos
                ranking.append({
                    "team_id": team_id,
                    "rank": len(ranking) + 1,
                    "distance": distance,
                    "correct_positions": correct_pos,
                    "correct_pegs": feedback.get("feedback", {}).get("correct_pegs", 0),
                    "competitive_analysis": {},
                    "strategic_advice": "Focus on locking positions systematically.",
                })

        print(f"[DEBUG] Ranking computed: {len(ranking)} teams")
        sys.stdout.flush()

        # Update histories
        for team_id in range(1, self.NUM_TEAMS + 1):
            try:
                your_rank_data = next(r for r in ranking if r["team_id"] == team_id)

                team_feedback = {
                    "your_distance": your_rank_data.get("distance", 0),
                    "your_rank": your_rank_data.get("rank", 0),
                    "game_feedback": feedback.get("feedback", {}),
                    "competitive_analysis": your_rank_data.get("competitive_analysis", {}),
                    "strategic_advice": your_rank_data.get("strategic_advice", ""),
                    "round": round_num,
                }

                self.team_histories[team_id].append({
                    "round": round_num,
                    "guess": guesses[team_id - 1],
                    "result": feedback.get("feedback", {}),
                    "ranking": ranking,
                })

                self.team_last_feedback[team_id] = team_feedback
            except StopIteration:
                print(f"[WARNING] Team {team_id} not found in ranking")
                sys.stdout.flush()

        # Print results
        ranking_str = ", ".join([
            f"Team {r['team_id']} ({r['rank']}{'st' if r['rank']==1 else 'nd'} - d:{r['distance']})"
            for r in ranking
        ])
        print(f"[Round {round_num}] RANKING: {ranking_str}")
        
        game_fb = feedback.get("feedback", {})
        pegs = game_fb.get("correct_pegs", 0)
        positions = game_fb.get("correct_positions", 0)
        print(f"[Round {round_num}] Submitted Team {top_team_id}'s guess: {top_guess} → pegs={pegs}, pos={positions}", end="")

        if feedback.get("solved", False):
            print(" ✅ SOLVED!")
            return True
        else:
            print()
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

        return {
            "success": solved,
            "rounds": len(self.team_histories[1]),
            "time": elapsed_time,
            "teams": {
                team_id: {
                    "guesses": len(self.team_histories[team_id]),
                    "final_rank": next(
                        (r["rank"] for r in self.team_histories[team_id][-1].get("ranking", [])
                         if r["team_id"] == team_id),
                        "N/A"
                    ) if self.team_histories[team_id] else "N/A",
                }
                for team_id in range(1, self.NUM_TEAMS + 1)
            },
        }


if __name__ == "__main__":
    import os

    provider = os.getenv("PROVIDER", "deepseek")

    puzzles = load_puzzles()
    # Find MM_001 (easy) for testing
    puzzle = next((p for p in puzzles if p['puzzle_id'] == 'MM_001'), puzzles[0])

    print("\n" + "=" * 80)
    print("2-AGENT JUDGE-MEDIATED SPEED RACING (2 Teams)")
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
        print(f"✅ SOLVED in {result['rounds']} rounds!")
    else:
        print(f"❌ NOT SOLVED after {result['rounds']} round(s)")

    for team_id, stats in result["teams"].items():
        print(f"  Team {team_id}: {stats['guesses']} guess(es), final rank: {stats['final_rank']}")

    print(f"\nTotal time: {result['time']:.1f} seconds")
