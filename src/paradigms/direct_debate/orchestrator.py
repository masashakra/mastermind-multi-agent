"""
Direct Adversarial Speed Racing Orchestrator — Peer-to-Peer Agent System

Architecture:
  1. Start registry HTTP server
  2. Start team agents as HTTP servers (each autonomous)
  3. Agents discover each other via registry
  4. Agents solve independently, then debate via A2A
  5. Orchestrator validates guesses (neutral game referee)
  6. Orchestrator collects final results

Agents operate as peers: they communicate directly via A2A,
orchestrator manages game validation and state.
"""

import sys
import os
import time
import threading
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Any, Dict, List
import httpx
from fastapi import FastAPI
import uvicorn

from registry.registry_server import start_registry_server
from paradigms.direct_debate.agents.agent_server import start_agent_servers
from game_engine import GameEngine
from puzzle_generator import load_puzzles


class DirectDebateOrchestrator:
    """Orchestrator for autonomous peer-to-peer agents.

    Role: manage game validation and state (neutral referee).
    Agents solve and debate autonomously via A2A.
    """

    MAX_ROUNDS = 16

    def __init__(self, puzzle: Dict[str, Any], provider: str = "deepseek", num_teams: int = 2):
        self.puzzle = puzzle
        self.provider = provider
        self.paradigm = "direct_debate"
        self.num_teams = num_teams
        self.team_ids = [f"team_{i+1}" for i in range(num_teams)]
        self.start_time = time.time()

        print(f"\n[Orchestrator] Starting Direct Adversarial Speed Racing — puzzle {puzzle['puzzle_id']}")
        print(f"[Orchestrator] Teams: {self.num_teams} (autonomous peer-to-peer)")

        # ── Initialize message logger ─────────────────────────────────────────
        puzzle_id = puzzle.get("puzzle_id", "unknown")
        import os; os.makedirs("logs", exist_ok=True)
        log_file = f"logs/{puzzle_id}_direct_debate_{provider}_messages.log"
        # Each subprocess gets its own log file to avoid concurrent write conflicts.
        # The orchestrator merges them at the end into the main log file.
        self.main_log_file = log_file
        self.team_log_files = {}  # team_id → per-team log file path
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

        # Wait for registry to be ready
        time.sleep(1.0)

        # ── Start orchestrator HTTP server (for guess validation) ─────────────
        import socket
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", 0))
        orch_port = sock.getsockname()[1]
        sock.close()
        self.orchestrator_url = f"http://localhost:{orch_port}"
        self._setup_http_server(orch_port)

        # ── Start autonomous agent servers ───────────────────────────────────
        self.team_urls = start_agent_servers(
            provider=provider,
            registry_url=self.registry_url,
            base_port=8501,  # 8501+ — avoids conflict with judge_mediated (8301) and boss_worker (8201)
            num_teams=num_teams,
            orchestrator_url=self.orchestrator_url,
        )
        print(f"[Orchestrator] Teams online: {list(self.team_urls.keys())}")

        # ── Game state: shared with agents for coordination ───────────────────
        self.current_round = 1
        # ONE SHARED GAME ENGINE - All teams compete for the same puzzle
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])
        # Track all guesses in order (for leaderboard)
        self.all_guesses: List[Dict[str, Any]] = []  # {"team_id": str, "guess": list, "feedback": dict, "timestamp": float}
        # Track submission order for determining winner
        self.submission_order: List[str] = []  # Order teams submitted guesses
        self.solved_teams: List[str] = []
        self.game_over = False
        self.winner = None

    def _setup_http_server(self, port: int) -> None:
        """Setup HTTP server for guess validation."""
        app = FastAPI()

        @app.post("/submit_guess")
        def submit_guess(body: Dict[str, Any]) -> Dict[str, Any]:
            """Receive guess from agent, validate against SHARED game engine."""
            try:
                team_id = body.get("team_id", "")
                guess = body.get("guess", [])

                if team_id not in self.team_ids:
                    return {"valid": False, "error": f"Unknown team: {team_id}"}

                if not guess:
                    return {"valid": False, "error": "Empty guess"}

                # If game already over, reject new submissions
                if self.game_over:
                    return {
                        "valid": True,
                        "feedback": {"correct_pegs": 0, "correct_positions": 0},
                        "solved": False,
                        "game_over": True,
                        "winner": self.winner,
                    }

                # Submit to SHARED game engine
                feedback = self.game_engine.submit_guess(guess)

                if feedback.get("valid", False):
                    # Record guess (PUBLIC - visible to all teams)
                    submission = {
                        "team_id": team_id,
                        "guess": guess,
                        "feedback": feedback.get("feedback", {}),
                        "timestamp": time.time(),
                        "solved": feedback.get("solved", False),
                    }
                    self.all_guesses.append(submission)
                    self.submission_order.append(team_id)

                    # Check if solved
                    if feedback.get("solved", False):
                        if not self.winner:
                            self.winner = team_id
                            self.game_over = True
                            print(f"\n[Orchestrator] 🏆 {team_id} SOLVED THE PUZZLE!")
                            print(f"[Orchestrator] Game Over - First team to solve: {team_id}")

                    # Build PUBLIC LEADERBOARD (feedback only, guesses private)
                    public_leaderboard = []
                    for guess_entry in self.all_guesses:
                        public_leaderboard.append({
                            "team_id": guess_entry["team_id"],
                            "feedback": guess_entry["feedback"],
                            "solved": guess_entry["solved"],
                            # Note: "guess" is NOT included (guesses remain private)
                        })

                    return {
                        "valid": True,
                        "feedback": feedback.get("feedback", {}),
                        "solved": feedback.get("solved", False),
                        "public_leaderboard": public_leaderboard,  # Feedback scores only, no guesses
                    }
                else:
                    return {"valid": False, "error": feedback.get("error", "Invalid guess")}

            except Exception as e:
                return {"valid": False, "error": str(e)}

        # Run server in background
        def run_server():
            config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
            server = uvicorn.Server(config)
            asyncio.run(server.serve())

        import asyncio
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        print(f"[Orchestrator] HTTP server up at {self.orchestrator_url}")

        # Wait for server to start
        time.sleep(0.5)

    def run(self) -> Dict[str, Any]:
        """Run puzzle with autonomous agents competing for ONE shared puzzle.

        Orchestrator role: validate guesses, track leaderboard, declare winner.
        """
        print(f"\n[Orchestrator] Starting puzzle execution...")
        print(f"[Orchestrator] ONE SHARED PUZZLE - Teams compete for the same solution")
        print(f"[Orchestrator] First team to solve wins! 🏁")

        # Notify agents to start
        self._notify_agents_start()

        # Wait for first team to solve (game ends immediately)
        self._wait_for_completion()

        elapsed = time.time() - self.start_time

        # Merge per-team log files into the main log file
        self._merge_team_logs()
        print(f"\n[Orchestrator] Log saved → {self.main_log_file}")

        # Build leaderboard
        leaderboard = []
        teams_that_solved = set()
        for guess in self.all_guesses:
            team = guess["team_id"]
            if team not in teams_that_solved and guess["solved"]:
                leaderboard.append(team)
                teams_that_solved.add(team)

        return {
            "puzzle_id": self.puzzle["puzzle_id"],
            "paradigm": self.paradigm,
            "difficulty": self.puzzle.get("difficulty", "easy"),
            "success": len(leaderboard) > 0,
            "winner": self.winner,
            "leaderboard": leaderboard,  # Order of teams that solved
            "total_guesses": len(self.all_guesses),
            "elapsed_time": elapsed,
            "all_guesses": self.all_guesses,  # Complete public record
            "submission_order": self.submission_order,
        }

    def _notify_agents_start(self) -> None:
        """Tell agents to start solving."""
        print("\n[Orchestrator] Notifying agents to begin...")
        puzzle_id = self.puzzle.get("puzzle_id", "unknown")

        for team_id in self.team_ids:
            url = self.team_urls[team_id]
            # Each team writes to its own log file — merged at end
            team_log = f"logs/{puzzle_id}_direct_debate_{self.provider}_{team_id}_messages.log"
            self.team_log_files[team_id] = team_log
            try:
                httpx.post(
                    f"{url}/start_puzzle",
                    json={
                        "puzzle": self.puzzle,
                        "team_id": team_id,
                        "registry_url": self.registry_url,
                        "orchestrator_url": self.orchestrator_url,
                        "log_file": team_log,
                    },
                    timeout=5.0
                )
            except Exception as e:
                print(f"[Orchestrator] Warning: Could not notify {team_id}: {e}")

    def _merge_team_logs(self) -> None:
        """Merge per-team log files into one main log file, sorted by timestamp."""
        import json, time as _time
        all_entries = []

        for team_id, team_log in self.team_log_files.items():
            try:
                with open(team_log) as f:
                    data = json.load(f)
                entries = data.get("puzzle_run_log", {}).get("entries", [])
                all_entries.extend(entries)
                print(f"[Orchestrator] Merged {len(entries)} entries from {team_id}")
            except Exception as e:
                print(f"[Orchestrator] Could not merge log for {team_id}: {e}")

        # Sort by timestamp
        all_entries.sort(key=lambda e: e.get("timestamp", 0))

        merged = {
            "puzzle_run_log": {
                "start_time": self.message_logger.start_time,
                "start_datetime": __import__("datetime").datetime.fromtimestamp(
                    self.message_logger.start_time
                ).isoformat(),
                "total_entries": len(all_entries),
                "entries": all_entries,
            }
        }

        with open(self.main_log_file, "w") as f:
            json.dump(merged, f, indent=2)

        print(f"[Orchestrator] Merged {len(all_entries)} total entries → {self.main_log_file}")

    def _wait_for_completion(self) -> None:
        """Wait for first team to solve the shared puzzle."""
        timeout = time.time() + 1800  # 30 minute timeout (increased to allow solving)

        while time.time() < timeout and not self.game_over:
            # Game ends immediately when someone solves
            if self.winner:
                self.game_over = True
                break

            # Also check if max total guesses exceeded (team-independent)
            if len(self.all_guesses) >= (self.MAX_ROUNDS * len(self.team_ids)):
                self.game_over = True
                break

            time.sleep(1)


if __name__ == "__main__":
    print("=" * 70)
    print("DIRECT ADVERSARIAL SPEED RACING — ONE SHARED PUZZLE")
    print("=" * 70)

    try:
        puzzles = load_puzzles()
        puzzle_map = {p["puzzle_id"]: p for p in puzzles}
        # Batch mode: DD_PUZZLE_ID env var selects specific puzzle
        target_id = os.environ.get("DD_PUZZLE_ID")
        if target_id and target_id in puzzle_map:
            test_puzzle = puzzle_map[target_id]
        else:
            import random
            easy_puzzles = [p for p in puzzles if p["difficulty"] == "easy"]
            test_puzzle = random.choice(easy_puzzles)

        print(f"Puzzle : {test_puzzle['puzzle_id']}")
        print(f"Secret : {test_puzzle['secret_code']}")

        orchestrator = DirectDebateOrchestrator(test_puzzle, provider="deepseek", num_teams=2)
        result = orchestrator.run()

        print("\n" + "=" * 70)
        print("RESULT — PUBLIC LEADERBOARD")
        print("=" * 70)
        print(f"Winner          : {result['winner']} 🏆")
        print(f"Total Guesses   : {result['total_guesses']}")
        print(f"Elapsed Time    : {result['elapsed_time']:.1f}s")
        print(f"Puzzle Solved   : {'YES ✅' if result['success'] else 'NO ❌'}")

        if result['all_guesses']:
            print(f"\n📊 All Guesses (Public Record):")
            for i, guess_entry in enumerate(result['all_guesses'], 1):
                team = guess_entry['team_id']
                guess = guess_entry['guess']
                fb = guess_entry['feedback']
                solved = "✅ SOLVED!" if guess_entry['solved'] else ""
                print(f"  {i}. {team}: {guess} → {fb['correct_pegs']}p {fb['correct_positions']}pos {solved}")

    except Exception as exc:
        import traceback
        print(f"\nError: {exc}")
        traceback.print_exc()
