# Judge-Mediated Speed Racing Paradigm - Simplified
# 3 teams, 1 agent each, parallel execution, judge ranking

import sys
import time
import socket
import asyncio
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from game_engine import GameEngine
from puzzle_generator import load_puzzles
from communication.a2a_message import A2AMessage
from registry.registry_server import start_registry_server
from paradigms.judge_mediated.agents.agent_server import start_agent_servers
from paradigms.judge_mediated.agents import JudgeAgent, LoggerAgent, MetricsAgent


class JudgeMediatedOrchestrator:
    """Simplified Judge-Mediated Speed Racing - 4 teams, 1 agent each, parallel execution."""

    MAX_ROUNDS = 8
    NUM_TEAMS = 3

    def __init__(self, puzzle: Dict[str, Any], provider: str = "deepseek"):
        self.puzzle = puzzle
        self.provider = provider
        self.paradigm = "judge_mediated"
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])
        self.start_time = time.time()

        # Logging
        self.logger = LoggerAgent(paradigm_name=self.paradigm)
        self.metrics = MetricsAgent(paradigm_name=self.paradigm)

        # Team management
        self.team_urls: Dict[int, str] = {}  # team_id → agent_url
        self.team_histories: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(1, self.NUM_TEAMS + 1)}
        self.team_last_feedback: Dict[int, Dict[str, Any]] = {i: {} for i in range(1, self.NUM_TEAMS + 1)}
        self.team_constraint_histories: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(1, self.NUM_TEAMS + 1)}  # NEW: Track constraints (like boss-worker!)

        # Judge
        self.judge = JudgeAgent(provider=provider)

        print(f"\n[Orchestrator] Starting Judge-Mediated Speed Racing — puzzle {puzzle['puzzle_id']}")
        print(f"[Orchestrator] Difficulty: {puzzle['difficulty']}")

    def _initialize_infrastructure(self) -> None:
        """Start registry and team agent servers."""
        # Start registry
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", 0))
        registry_port = sock.getsockname()[1]
        sock.close()

        self.registry_url = start_registry_server(port=registry_port)
        print(f"[Orchestrator] Registry up at {self.registry_url}")

        # Start one agent per team
        for team_id in range(1, self.NUM_TEAMS + 1):
            agent_url = start_agent_servers(
                provider=self.provider,
                registry_url=self.registry_url,
                team_id=team_id,
                base_port=8301,
            )
            self.team_urls[team_id] = agent_url
            print(f"[Orchestrator] Team {team_id} agent online: {agent_url}")

        print(f"[Orchestrator] All {self.NUM_TEAMS} teams initialized")

    async def _run_team_round(self, team_id: int, round_num: int) -> Dict[str, Any]:
        """Run one team's solve round."""
        try:
            print(f"[DEBUG] Team {team_id} Round {round_num}: Starting", flush=True)

            # Call team agent (need 300s for DeepSeek R1 reasoning)
            async with httpx.AsyncClient(timeout=300.0) as client:
                request_msg = A2AMessage.request(
                    sender_id="orchestrator",
                    receiver_id=f"team-{team_id}",
                    action="solve_round",
                    payload={
                        "guess_history": [g.get("guess", []) for g in self.team_histories[team_id]],
                        "constraint_history": self.team_constraint_histories[team_id],  # NEW: Pass constraints (boss-worker style!)
                        "last_feedback": self.team_last_feedback[team_id],
                        "difficulty": self.puzzle.get("difficulty", "easy"),
                        "available_colors": self.puzzle.get("available_colors", []),
                        "num_pegs": self.puzzle.get("pegs", 4),
                    },
                )

                response = await client.post(
                    self.team_urls[team_id] + "/solve_round",
                    json=request_msg.to_dict(),
                    timeout=300.0,
                )

                result_msg = A2AMessage.from_dict(response.json())
                result = result_msg.payload
                guess = result.get("guess", [])

                print(f"[DEBUG] Team {team_id} proposed: {guess}", flush=True)

                return {
                    "team_id": team_id,
                    "guess": guess,
                    "analysis": result.get("analysis", ""),
                    "strategy": result.get("strategy", ""),
                }

        except Exception as e:
            print(f"[ERROR] Team {team_id} Round {round_num}: {str(e)}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
            return {
                "team_id": team_id,
                "guess": [],
                "analysis": f"Error: {str(e)}",
                "strategy": "Error",
            }

    async def _run_round(self) -> bool:
        """Run one complete round: all teams solve in parallel, judge ranks, top guess submitted."""
        round_num = len(self.team_histories[1]) + 1
        print(f"[DEBUG] Starting round {round_num}, MAX_ROUNDS={self.MAX_ROUNDS}", flush=True)

        if round_num > self.MAX_ROUNDS:
            return False

        print(f"\n[Round {round_num}] Running {self.NUM_TEAMS} teams in parallel...", flush=True)

        # Run all teams in parallel
        print(f"[DEBUG] Gathering team results for round {round_num}...", flush=True)
        try:
            team_tasks = [
                self._run_team_round(team_id=team_id, round_num=round_num)
                for team_id in range(1, self.NUM_TEAMS + 1)
            ]
            team_results = await asyncio.gather(*team_tasks)
            print(f"[DEBUG] Got team results: {len(team_results)} teams", flush=True)
        except Exception as e:
            print(f"[ERROR] Gathering team results failed: {str(e)}", flush=True)
            raise

        # Extract guesses
        guesses = [r["guess"] for r in team_results]
        print(f"[DEBUG] Extracted guesses: {guesses}", flush=True)

        # Judge ranks teams by distance to solution AND provides competitive intelligence
        ranking = self.judge.rank_teams(
            team_results=[
                {
                    "team_id": r["team_id"],
                    "guess": r["guess"],
                    "feedback": {},
                }
                for r in team_results
            ],
            all_team_histories=self.team_histories,  # NEW: Pass full history for competitive analysis!
            pegs_to_solve=self.puzzle.get("pegs", 4),
        )

        # Submit top team's guess
        top_team_id = ranking[0]["team_id"]
        top_guess = guesses[top_team_id - 1]

        feedback = self.game_engine.submit_guess(top_guess)

        if not feedback.get("valid", False):
            self.logger.log_message({
                "message_type": "error",
                "sender": "game_engine",
                "round": round_num,
                "content": {"error": feedback.get("error", "Invalid guess")},
            })
            return False

        # Record in team histories and provide rich feedback to all teams
        for team_id in range(1, self.NUM_TEAMS + 1):
            your_rank_data = next(r for r in ranking if r["team_id"] == team_id)
            team_result = team_results[team_id - 1]

            # Create rich feedback for this team (no guess leakage, only metrics)
            team_feedback = {
                "your_distance": your_rank_data["distance"],
                "your_rank": your_rank_data["rank"],
                "all_distances": {f"team_{r['team_id']}": r["distance"] for r in ranking},
                "all_ranks": {f"team_{r['team_id']}": r["rank"] for r in ranking},
                "game_feedback": feedback.get("feedback", {}),  # Feedback from submitted guess
                "round": round_num,
                # NEW: Competitive intelligence from enhanced judge!
                "competitive_analysis": your_rank_data.get("competitive_analysis", {}),
                "strategic_advice": your_rank_data.get("strategic_advice", ""),
            }

            self.team_histories[team_id].append({
                "round": round_num,
                "guess": guesses[team_id - 1],
                "ranking": ranking,
                "your_rank": your_rank_data["rank"],
            })

            # NEW: Store STRUCTURED CONSTRAINTS (boss-worker style!)
            constraints = team_result.get("constraints", {})
            if constraints:  # Only store if agent extracted constraints
                constraints["round"] = round_num
                self.team_constraint_histories[team_id].append(constraints)

            # Store the rich feedback instead of just game feedback
            self.team_last_feedback[team_id] = team_feedback

        # Print round results
        ranking_str = ", ".join([
            f"Team {r['team_id']} ({r['rank']}{'st' if r['rank']==1 else 'nd' if r['rank']==2 else 'rd'} - d:{r['distance']})"
            for r in ranking
        ])
        print(f"[Round {round_num}] RANKING: {ranking_str}")
        print(f"[Round {round_num}] Submitted Team {top_team_id}'s guess: {top_guess} → pegs={feedback.get('feedback', {}).get('correct_pegs', 0)}, pos={feedback.get('feedback', {}).get('correct_positions', 0)}", end="")
        if feedback.get("solved", False):
            print(" ✓ SOLVED!")
        else:
            print()

        return feedback.get("solved", False)

    def run(self) -> Dict[str, Any]:
        """Run the competition."""
        self._initialize_infrastructure()

        print(f"\n[Orchestrator] Starting async round loop (max {self.MAX_ROUNDS} rounds)...")
        try:
            solved = asyncio.run(self._run_async_loop())
        except Exception as e:
            print(f"[Orchestrator] Error: {e}")
            solved = False

        elapsed_time = time.time() - self.start_time

        # Determine winner
        winner_team = None
        if solved:
            last_round_results = []
            for team_id in range(1, self.NUM_TEAMS + 1):
                if self.team_histories[team_id]:
                    last_entry = self.team_histories[team_id][-1]
                    last_round_results.append({
                        "team_id": team_id,
                        "rank": last_entry.get("your_rank", 0),
                    })
            if last_round_results:
                winner_team = min(last_round_results, key=lambda x: x["rank"])["team_id"]

        total_rounds = len(self.team_histories[1])

        # Save metrics
        self.metrics.record_metric("total_rounds", total_rounds)
        self.metrics.record_metric("success", solved)
        self.metrics.record_metric("winner_team", winner_team or "none")
        self.metrics.save_metrics()
        self.logger.save_logs()

        print(f"\n{'='*70}")
        print("GAME OVER")
        print(f"{'='*70}")
        if solved:
            print(f"✓ SOLVED in {total_rounds} round(s)!")
            print(f"Winner: Team {winner_team}")
        else:
            print(f"✗ NOT SOLVED after {total_rounds} round(s)")

        print(f"\nPer-Team Results:")
        for team_id in range(1, self.NUM_TEAMS + 1):
            final_rank = self.team_histories[team_id][-1].get("your_rank", 0) if self.team_histories[team_id] else 0
            print(f"  Team {team_id}: {len(self.team_histories[team_id])} guess(es), final rank: {final_rank}{'st' if final_rank==1 else 'nd' if final_rank==2 else 'rd'}")

        return {
            "puzzle_id": self.puzzle["puzzle_id"],
            "paradigm": self.paradigm,
            "difficulty": self.puzzle.get("difficulty", "easy"),
            "success": solved,
            "winner_team": winner_team,
            "total_rounds": total_rounds,
            "elapsed_time": elapsed_time,
            "team_results": {
                team_id: {
                    "guesses": len(self.team_histories[team_id]),
                    "history": self.team_histories[team_id],
                }
                for team_id in range(1, self.NUM_TEAMS + 1)
            },
            "message_count": len(self.logger),
        }

    async def _run_async_loop(self) -> bool:
        """Async loop for running rounds."""
        for _ in range(self.MAX_ROUNDS):
            solved = await self._run_round()
            if solved:
                return True
        return False


if __name__ == "__main__":
    import sys as sys_module

    print("=" * 80)
    print("JUDGE-MEDIATED SPEED RACING (SIMPLIFIED)")
    print("=" * 80)

    try:
        if len(sys_module.argv) < 2:
            print("Usage: python orchestrator.py <provider> [puzzle_index]")
            sys_module.exit(1)

        provider = sys_module.argv[1]
        puzzle_index = int(sys_module.argv[2]) if len(sys_module.argv) > 2 else 0

        puzzles = load_puzzles()
        easy_puzzles = [p for p in puzzles if p['difficulty'] == 'easy']
        puzzle = easy_puzzles[puzzle_index % len(easy_puzzles)]

        print(f"\nTesting puzzle: {puzzle['puzzle_id']}")
        print(f"Difficulty: {puzzle['difficulty']}")
        print(f"Provider: {provider}")

        orchestrator = JudgeMediatedOrchestrator(puzzle, provider=provider)
        result = orchestrator.run()

        print(f"\nResult:")
        print(f"  Success: {result['success']}")
        print(f"  Winner: Team {result.get('winner_team', 'N/A')}")
        print(f"  Rounds: {result['total_rounds']}")
        print(f"  Time: {result['elapsed_time']:.1f}s")
        print(f"  Messages: {result['message_count']}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
