# Mastermind Game Engine
# Core game logic: feedback computation, guess validation, round tracking
# Tracks secret code, validates guesses, returns feedback (correct_pegs, correct_positions)
# Implements 8-round max, detects win condition

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class Feedback:
    correct_pegs: int
    correct_positions: int


class GameEngine:
    """Mastermind game engine for evaluating puzzle-solving strategies.

    Stores secret code, validates guesses, computes feedback, and tracks game state.
    """

    def __init__(self, secret_code: List[str], difficulty: str):
        """Initialize game with secret code.

        Args:
            secret_code: List of color strings (e.g., ["red", "blue", "green", "yellow"])
            difficulty: "easy" (4 pegs), "medium" (5 pegs), or "hard" (6 pegs)
        """
        self.secret_code = secret_code
        self.difficulty = difficulty
        self.guess_count = 0
        self.max_rounds = 8
        self.guess_history = []

    def submit_guess(self, guess: List[str]) -> Dict[str, Any]:
        """Submit a guess and receive feedback.

        Returns:
            {
                "valid": bool,
                "error": str or None,
                "guess_number": int,
                "feedback": {"correct_pegs": int, "correct_positions": int},
                "solved": bool,
                "rounds_remaining": int
            }
        """
        # Validate length
        if len(guess) != len(self.secret_code):
            return {
                "valid": False,
                "error": f"Wrong number of pegs. Expected {len(self.secret_code)}, got {len(guess)}"
            }

        # Compute correct positions (exact matches)
        correct_positions = sum(1 for i, c in enumerate(guess) if c == self.secret_code[i])

        # Compute correct pegs (any position) using color counting
        guess_colors = {c: guess.count(c) for c in set(guess)}
        secret_colors = {c: self.secret_code.count(c) for c in set(self.secret_code)}
        correct_pegs = sum(min(guess_colors[c], secret_colors.get(c, 0)) for c in guess_colors)

        self.guess_count += 1
        self.guess_history.append({
            "round": self.guess_count,
            "guess": guess,
            "feedback": {
                "correct_pegs": correct_pegs,
                "correct_positions": correct_positions
            }
        })

        return {
            "valid": True,
            "guess_number": self.guess_count,
            "feedback": {
                "correct_pegs": correct_pegs,
                "correct_positions": correct_positions
            },
            "solved": correct_positions == len(self.secret_code),
            "rounds_remaining": self.max_rounds - self.guess_count
        }

    def is_game_over(self) -> bool:
        """Check if game is over (max rounds or solved)."""
        if self.guess_count >= self.max_rounds:
            return True
        if self.guess_history:
            last = self.guess_history[-1]
            if last["feedback"]["correct_positions"] == len(self.secret_code):
                return True
        return False

    def get_state(self) -> Dict[str, Any]:
        """Return current game state."""
        return {
            "guess_count": self.guess_count,
            "max_rounds": self.max_rounds,
            "guess_history": self.guess_history,
            "secret_code_length": len(self.secret_code),
            "is_over": self.is_game_over()
        }
