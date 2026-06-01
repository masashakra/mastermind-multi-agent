# Round-Table Paradigm Orchestrator (Async Peer-to-Peer)
# True autonomous peer-to-peer with agents making their own routing decisions

import sys
import time
import asyncio
import threading
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from game_engine import GameEngine
from puzzle_generator import load_puzzles
from communication.a2a_message import A2AMessage, A2AStatus
from registry.registry_server import start_registry_server
from paradigms.round_table.agents.agent_server import start_agent_servers
import uvicorn


class ConstraintSolver:
    """Candidate-elimination Mastermind solver (no LLM involved).

    Maintains the full set of codes still consistent with every
    guess+feedback seen so far.  After each update, hard facts are
    derived directly from the candidate set:

    - impossible_colors : colors absent from ALL remaining candidates
    - confirmed_colors  : colors present in ALL remaining candidates
    - locked_positions  : positions where every candidate has the same color
    - min_color_counts  : minimum occurrences of a color across all candidates
    - candidates        : remaining consistent codes (shrinks each round)
    """

    def __init__(self, available_colors: List[str], num_pegs: int):
        from itertools import product as _product
        self.available_colors = [c.lower() for c in available_colors]
        self.num_pegs = num_pegs
        # All possible codes to start with
        self.candidates: List[tuple] = list(_product(self.available_colors, repeat=num_pegs))
        self.impossible_colors: set = set()
        self.confirmed_colors: set = set()
        self.locked_positions: Dict[int, str] = {}
        self.min_color_counts: Dict[str, int] = {}

    @staticmethod
    def _score(guess: tuple, secret: tuple) -> tuple:
        """Return (pegs, positions) for guess vs secret."""
        from collections import Counter
        positions = sum(g == s for g, s in zip(guess, secret))
        gc = Counter(guess)
        sc = Counter(secret)
        pegs = sum(min(gc[c], sc[c]) for c in gc)
        return pegs, positions

    def update(self, guess: List[str], feedback: Dict[str, int]) -> None:
        """Filter candidates by this round's result, then re-derive constraints."""
        g = tuple(c.lower() for c in guess)
        target = (feedback.get("correct_pegs", 0),
                  feedback.get("correct_positions", 0))

        # Keep only candidates consistent with the feedback
        self.candidates = [c for c in self.candidates if self._score(g, c) == target]

        # Re-derive all constraints from the surviving candidates
        self._derive()

    def _derive(self) -> None:
        """Compute hard facts from the current candidate set."""
        from collections import Counter
        if not self.candidates:
            return

        colors = set(self.available_colors)
        colors_seen = set(c for cand in self.candidates for c in cand)

        # impossible = colors that appear in no remaining candidate
        self.impossible_colors = colors - colors_seen

        # confirmed = colors that appear in every remaining candidate
        self.confirmed_colors = {
            c for c in colors
            if c not in self.impossible_colors
            and all(c in cand for cand in self.candidates)
        }

        # locked positions = same color in every candidate at that position
        self.locked_positions = {}
        for pos in range(self.num_pegs):
            at_pos = {cand[pos] for cand in self.candidates}
            if len(at_pos) == 1:
                self.locked_positions[pos] = at_pos.pop()

        # min_color_counts = minimum occurrences across all candidates
        self.min_color_counts = {}
        for color in colors_seen:
            min_n = min(Counter(cand)[color] for cand in self.candidates)
            if min_n > 0:
                self.min_color_counts[color] = min_n

    @property
    def valid_colors(self) -> List[str]:
        return [c for c in self.available_colors if c not in self.impossible_colors]

    def best_guess(self, past_guesses: List[List[str]]) -> List[str]:
        """Pick a random remaining candidate, avoiding past guesses."""
        import random
        options = [list(c) for c in self.candidates if list(c) not in past_guesses]
        if options:
            return random.choice(options)
        # Fallback if all candidates already tried (shouldn't happen)
        safe = self.valid_colors or self.available_colors
        g = [random.choice(safe) for _ in range(self.num_pegs)]
        for pos, color in self.locked_positions.items():
            g[pos] = color
        return g

    def enforce(self, guess: List[str], past_guesses: List[List[str]]) -> List[str]:
        """Fix a proposed guess to satisfy all hard constraints.
        If no candidates remain or guess violates constraints badly,
        return a candidate from the remaining set instead."""
        import random

        g = [c.lower() if isinstance(c, str) else c for c in guess]
        safe = self.valid_colors or self.available_colors

        # If the proposed guess is itself a valid candidate, keep it
        if tuple(g) in self.candidates and g not in past_guesses:
            return g

        # Replace impossible colors
        g = [c if c not in self.impossible_colors else random.choice(safe) for c in g]

        # Lock confirmed positions
        for pos, color in self.locked_positions.items():
            if pos < len(g):
                g[pos] = color

        # Satisfy min_color_counts
        for color, min_n in self.min_color_counts.items():
            if color in self.impossible_colors:
                continue
            deficit = min_n - g.count(color)
            if deficit > 0:
                free = [i for i in range(len(g)) if i not in self.locked_positions]
                random.shuffle(free)
                for slot in free[:deficit]:
                    g[slot] = color

        # If still a duplicate, grab a real candidate instead
        if g in past_guesses:
            return self.best_guess(past_guesses)

        return g

    def to_dict(self) -> Dict[str, Any]:
        import random
        # Pass a sample of up to 20 candidates so the Proposer can pick from them
        sample = [list(c) for c in random.sample(
            self.candidates, min(20, len(self.candidates))
        )] if self.candidates else []
        return {
            "impossible_colors":  sorted(self.impossible_colors),
            "confirmed_colors":   sorted(self.confirmed_colors),
            "locked_positions":   {str(k): v for k, v in self.locked_positions.items()},
            "min_color_counts":   self.min_color_counts,
            "valid_colors":       self.valid_colors,
            "candidates_left":    len(self.candidates),
            "candidate_sample":   sample,
        }

    def summary(self) -> str:
        n = len(self.candidates)
        parts = [f"candidates={n}"]
        if self.impossible_colors:
            parts.append(f"impossible={sorted(self.impossible_colors)}")
        if self.confirmed_colors:
            parts.append(f"confirmed={sorted(self.confirmed_colors)}")
        if self.locked_positions:
            parts.append(f"locked={self.locked_positions}")
        if self.min_color_counts:
            parts.append(f"min_counts={self.min_color_counts}")
        return "  ".join(parts)


class RoundTableOrchestrator:
    """Autonomous Peer-to-Peer Round-Table Paradigm

    Architecture:
    - Registry (8100): Agent discovery
    - Analyzer (8101): Autonomous analyzer agent
    - Strategist (8102): Autonomous strategist agent
    - Proposer (8103): Autonomous proposer agent
    - Validator (8104): Autonomous validator agent
    - Orchestrator (8107): Receives final results, manages feedback loop

    Workflow per round:
    1. Orchestrator sends initial feedback to Analyzer
    2. Analyzer processes, decides next peer, sends A2A message autonomously
    3. Agents form a peer network, messages flow between them
    4. Validator eventually sends final guess to Orchestrator
    5. Orchestrator submits to game engine
    6. If not solved: loop back with new feedback
    """

    def __init__(self, puzzle: Dict[str, Any], provider: str = "kaggle"):
        self.puzzle = puzzle
        self.provider = provider
        self.paradigm = "round_table"
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])
        self.start_time = time.time()

        # Server URLs (will be set during startup)
        self.registry_url: Optional[str] = None
        self.agent_urls: Optional[Dict[str, str]] = None
        self.orchestrator_url: str = "http://localhost:8107"

        # State for receiving validator response
        self.last_validation: Optional[Dict[str, Any]] = None
        self.validation_received = threading.Event()

        # Constraint solver — updated after every guess, passed to agents
        self.solver = ConstraintSolver(
            available_colors=puzzle.get("available_colors", []),
            num_pegs=puzzle.get("pegs", 4),
        )

    async def _start_servers(self) -> None:
        """Start registry, agent servers, and orchestrator server."""
        print("[Orchestrator] Starting servers...")

        # Start registry
        self.registry_url = await asyncio.to_thread(
            start_registry_server, 8100
        )
        print(f"[Orchestrator] Registry up at {self.registry_url}")

        # Start agent servers
        self.agent_urls = await asyncio.to_thread(
            start_agent_servers,
            self.provider,
            self.registry_url,
            8101  # base port
        )
        print(f"[Orchestrator] Workers online: {list(self.agent_urls.keys())}")

        # Start orchestrator HTTP server to receive validation
        app = self._create_orchestrator_app()

        def run_orch_server():
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=8107,
                log_level="error",
            )

        thread = threading.Thread(target=run_orch_server, daemon=True)
        thread.start()

        # Wait for orchestrator to be ready
        await asyncio.sleep(0.5)
        print(f"[Orchestrator] HTTP server listening at {self.orchestrator_url}")

    def _create_orchestrator_app(self) -> FastAPI:
        """Create FastAPI app for orchestrator to receive validation results."""
        app = FastAPI(title="Round-Table Orchestrator")

        @app.get("/health")
        async def health():
            return {"status": "ok", "service": "round_table_orchestrator"}

        @app.post("/receive_validation")
        async def receive_validation(request: Request):
            """Receive final validated guess from Validator agent."""
            try:
                request_data = await request.json()
                msg = A2AMessage.from_dict(request_data)

                print(f"[Orchestrator] Received validation from {msg.sender_id}")

                # Extract guess — normalise case
                guess = msg.payload.get("proposed_guess", msg.payload.get("guess", []))
                guess = [c.lower() if isinstance(c, str) else c for c in guess]
                valid = msg.payload.get("valid", False)

                self.last_validation = {
                    "guess": guess,
                    "valid": valid,
                    "payload": msg.payload
                }

                # Signal that validation is received
                self.validation_received.set()

                # Return response
                response = A2AMessage.response(
                    request=msg,
                    status=A2AStatus.OK,
                    payload={"received": True, "message": "Guess received by orchestrator"}
                )
                return response.to_dict()

            except Exception as e:
                print(f"[Orchestrator] Error receiving validation: {e}")
                return {"error": str(e)}

        return app

    async def _send_to_analyzer(self, feedback: Dict[str, int], guess_history: List[Dict]) -> None:
        """Send initial feedback to Analyzer to start the round.

        This triggers the peer-to-peer chain reaction.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            analyzer_url = self.agent_urls.get("analyzer")
            if not analyzer_url:
                raise RuntimeError("Analyzer not found in agent URLs")

            msg = A2AMessage.request(
                sender_id="orchestrator_round_table",
                receiver_id="analyzer_round_table",
                action="analyze",
                payload={
                    "last_guess":       guess_history[-1]["guess"] if guess_history else [],
                    "feedback":         feedback,
                    "guess_history":    guess_history,        # full history — shared truth
                    "available_colors": self.puzzle.get("available_colors", []),
                    "difficulty":       self.puzzle.get("difficulty", "easy"),
                    "num_pegs":         self.puzzle.get("pegs", 4),
                    # ── hard constraints from Python solver (never wrong) ──────
                    "constraints":      self.solver.to_dict(),
                }
            )

            print(f"[Orchestrator] Sending feedback to Analyzer (round {len(guess_history) + 1})")

            for attempt in range(3):
                try:
                    resp = await client.post(
                        f"{analyzer_url}/analyze",
                        json=msg.to_dict(),
                        timeout=120.0   # Analyzer may take time calling the LLM
                    )
                    if resp.status_code == 200:
                        print(f"[Orchestrator] ✓ Analyzer started processing")
                    else:
                        print(f"[Orchestrator] ! Analyzer returned {resp.status_code}")
                    break
                except Exception as e:
                    if attempt < 2:
                        wait = 10 * (attempt + 1)
                        print(f"[Orchestrator] Error calling Analyzer (attempt {attempt+1}/3), retrying in {wait}s: {e}")
                        await asyncio.sleep(wait)
                    else:
                        print(f"[Orchestrator] Error calling Analyzer after 3 attempts: {e}")
                        raise

    async def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Round-Table paradigm.

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "round_table",
                "success": bool,
                "guesses": int,
                "rounds": int,
                "elapsed_time": float,
                "guess_history": list,
            }
        """
        print("\n" + "="*70)
        print("ROUND-TABLE PARADIGM — Autonomous Peer-to-Peer")
        print("="*70)
        print(f"Puzzle: {self.puzzle['puzzle_id']}")
        print(f"Secret: {self.puzzle['secret_code']}")
        print(f"Colors: {self.puzzle.get('available_colors', [])}")
        print("="*70 + "\n")

        try:
            # Start all servers
            await self._start_servers()

            guess_history = []
            round_count = 0

            # Game loop
            while round_count < 8 and not self.game_engine.is_game_over():
                round_count += 1

                # Initial feedback (first round is all zeros)
                if round_count == 1:
                    feedback = {"correct_pegs": 0, "correct_positions": 0}
                else:
                    feedback = guess_history[-1]["feedback"]

                # Clear the event for new round
                self.validation_received.clear()
                self.last_validation = None

                # Send feedback to Analyzer (starts the peer chain)
                await self._send_to_analyzer(feedback, guess_history)

                # Wait for Validator to send back the final guess
                # Timeout after 60 seconds
                received = await asyncio.to_thread(
                    self.validation_received.wait, 60
                )

                if not received:
                    print(f"[Orchestrator] Timeout waiting for validation")
                    break

                if not self.last_validation:
                    print(f"[Orchestrator] No validation received")
                    break

                guess = self.last_validation.get("guess", [])

                # Submit guess to game engine
                if not guess:
                    print(f"[Orchestrator] Empty guess, skipping round")
                    continue

                print(f"[Orchestrator] Submitting guess: {guess}")
                resp = self.game_engine.submit_guess(guess)

                if not resp.get("valid", False):
                    print(f"[Orchestrator] Game engine rejected guess")
                    continue

                feedback = resp.get("feedback", {})
                solved = resp.get("solved", False)

                guess_history.append({
                    "round": round_count,
                    "guess": guess,
                    "feedback": feedback,
                })

                # ── Update constraint solver with hard mathematical facts ─────
                self.solver.update(guess, feedback)

                pegs = feedback.get("correct_pegs", 0)
                pos = feedback.get("correct_positions", 0)
                print(f"[Orchestrator] Round {round_count} → {guess} | "
                      f"pegs={pegs}  pos={pos}" + ("  ✓ SOLVED!" if solved else ""))
                print(f"[Constraints] {self.solver.summary()}")

                if solved:
                    break

            elapsed_time = time.time() - self.start_time

            # Determine success
            success = False
            if guess_history:
                last_feedback = guess_history[-1].get("feedback", {})
                success = last_feedback.get("correct_positions", 0) == self.puzzle.get("pegs", 4)

            result = {
                "puzzle_id": self.puzzle["puzzle_id"],
                "paradigm": self.paradigm,
                "difficulty": self.puzzle.get("difficulty", "easy"),
                "success": success,
                "guesses": len(guess_history),
                "rounds": round_count,
                "elapsed_time": elapsed_time,
                "guess_history": guess_history,
            }

            print("\n" + "="*70)
            print("RESULT")
            print("="*70)
            print(f"Success: {result['success']}")
            print(f"Guesses: {result['guesses']}")
            print(f"Rounds: {result['rounds']}")
            print(f"Elapsed: {result['elapsed_time']:.1f}s")
            print("="*70 + "\n")

            return result

        except Exception as e:
            print(f"[Orchestrator] Fatal error: {e}")
            import traceback
            traceback.print_exc()
            raise


# ── Main entrypoint ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    # Get puzzle
    puzzles = load_puzzles()
    puzzle = next(p for p in puzzles if p["puzzle_id"] == "MM_001")

    # Get provider from env (default to kaggle)
    provider = os.getenv("PROVIDER", "kaggle")

    # Run orchestrator
    orchestrator = RoundTableOrchestrator(puzzle, provider=provider)

    # Run async event loop
    result = asyncio.run(orchestrator.run())

    print(f"Puzzle solved: {result['success']}")
