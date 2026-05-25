# Boss-Worker Paradigm
# Collaboration + Centralized: Single Boss coordinates 4 worker agents
# Boss controls workflow, all agents see all messages, high coordination efficiency
# One paradigm: 1 Boss + 4 workers, 8 rounds max per puzzle

import time
from typing import Dict, Any, List
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game_engine import GameEngine
from agents.boss import BossAgent
from communication_logger import CommunicationLogger


class BossWorkerOrchestrator:
    """Orchestrates Boss-Worker paradigm for solving Mastermind puzzles.

    Structure:
    - 1 Boss (coordinator)
    - 4 Workers (Strategist, Analyzer, Proposer, Validator)
    - All agents see all messages (full transparency)
    - Boss controls workflow sequentially
    - High coordination efficiency, potential bottleneck at Boss

    Metrics tracked:
    - Success (solved or not)
    - Efficiency (guesses, rounds)
    - Communication (messages, tokens)
    """

    def __init__(self, puzzle: Dict[str, Any], provider: str = "ollama"):
        """Initialize orchestrator for one puzzle.

        Args:
            puzzle: Puzzle dictionary from puzzle_generator
            provider: "ollama" (dev) or "claude" (production)
        """
        self.puzzle = puzzle
        self.provider = provider
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])
        self.boss = BossAgent(provider=provider)
        self.logger = CommunicationLogger(puzzle["puzzle_id"], "boss-worker")
        self.guess_history = []
        self.round_count = 0
        self.start_time = time.time()

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Boss-Worker paradigm.

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "boss-worker",
                "success": bool,
                "guesses": int,
                "rounds": int,
                "elapsed_time": float,
                "guess_history": list,
                "messages": list,
                "token_usage": dict,
                "agent_stats": dict
            }
        """
        while self.round_count < 8 and not self.game_engine.is_game_over():
            self.round_count += 1

            # Boss orchestrates round
            try:
                round_result = self.boss.orchestrate_round({
                    "puzzle": self.puzzle,
                    "guess_history": self.guess_history,
                    "difficulty": self.puzzle["difficulty"]
                })

                # Log all inter-agent messages
                for msg in round_result.get("messages", []):
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "boss-worker",
                        "sender": msg.get("agent", "unknown"),
                        "receiver": "boss",
                        "message_type": msg.get("action", "unknown"),
                        "content": msg.get("result", {})
                    }
                    self.logger.log_message(log_entry)

                # Extract guess
                guess = round_result.get("guess", [])

                # Submit to game engine
                feedback = self.game_engine.submit_guess(guess)

                if not feedback.get("valid", False):
                    # Invalid guess (wrong length, etc.) - log and continue
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "boss-worker",
                        "sender": "game_engine",
                        "receiver": "boss",
                        "message_type": "invalid_guess",
                        "content": {"error": feedback.get("error", "Unknown error")}
                    }
                    self.logger.log_message(log_entry)
                    continue

                # Add to history
                self.guess_history.append({
                    "round": self.round_count,
                    "guess": guess,
                    "feedback": feedback.get("feedback", {})
                })

                # Log feedback
                log_entry = {
                    "timestamp": time.time(),
                    "round_number": self.round_count,
                    "puzzle_id": self.puzzle["puzzle_id"],
                    "paradigm": "boss-worker",
                    "sender": "game_engine",
                    "receiver": "boss",
                    "message_type": "feedback",
                    "content": {
                        "guess_number": feedback.get("guess_number", 0),
                        "correct_pegs": feedback.get("feedback", {}).get("correct_pegs", 0),
                        "correct_positions": feedback.get("feedback", {}).get("correct_positions", 0),
                        "solved": feedback.get("solved", False),
                        "rounds_remaining": feedback.get("rounds_remaining", 0)
                    }
                }
                self.logger.log_message(log_entry)

                # Check if solved
                if feedback.get("solved", False):
                    break

            except Exception as e:
                # Log error and continue
                log_entry = {
                    "timestamp": time.time(),
                    "round_number": self.round_count,
                    "puzzle_id": self.puzzle["puzzle_id"],
                    "paradigm": "boss-worker",
                    "sender": "boss",
                    "receiver": "error_log",
                    "message_type": "error",
                    "content": {"error": str(e)}
                }
                self.logger.log_message(log_entry)
                continue

        elapsed_time = time.time() - self.start_time

        # Determine success
        if self.guess_history:
            last_feedback = self.guess_history[-1].get("feedback", {})
            success = last_feedback.get("correct_positions", 0) == self.puzzle.get("pegs", 4)
        else:
            success = False

        return {
            "puzzle_id": self.puzzle["puzzle_id"],
            "paradigm": "boss-worker",
            "difficulty": self.puzzle["difficulty"],
            "success": success,
            "guesses": len(self.guess_history),
            "rounds": self.round_count,
            "elapsed_time": elapsed_time,
            "guess_history": self.guess_history,
            "message_count": len(self.logger.get_all_messages()),
            "token_usage": {
                "strategist": self.boss.strategist.total_input_tokens + self.boss.strategist.total_output_tokens,
                "analyzer": self.boss.analyzer.total_input_tokens + self.boss.analyzer.total_output_tokens,
                "proposer": self.boss.proposer.total_input_tokens + self.boss.proposer.total_output_tokens,
                "validator": self.boss.validator.total_input_tokens + self.boss.validator.total_output_tokens,
                "total": (
                    self.boss.strategist.total_input_tokens + self.boss.strategist.total_output_tokens +
                    self.boss.analyzer.total_input_tokens + self.boss.analyzer.total_output_tokens +
                    self.boss.proposer.total_input_tokens + self.boss.proposer.total_output_tokens +
                    self.boss.validator.total_input_tokens + self.boss.validator.total_output_tokens
                )
            },
            "agent_stats": self.boss.get_stats()
        }
