# Proposer Agent V2
# RULE-BASED: Fast heuristic guess generation without slow LLM
# Generates specific next guess from constraints + strategy

from typing import List, Dict, Any
import random


class ProposerAgentV2:
    """Fast, rule-based guess generation.

    Strategy:
    1. Extract locked positions from constraints
    2. Test misplaced colors in new positions
    3. Test new colors in untested positions
    4. NEVER repeat guesses
    """

    def __init__(self):
        self.name = "Proposer-V2"

    def propose_guess(
        self,
        locked_positions: Dict[int, str],
        found_colors: set,
        misplaced_colors: set,
        available_colors: List[str],
        num_pegs: int,
        previous_guesses: List[List[str]] = None
    ) -> List[str]:
        """Generate guess using rule-based heuristics.

        Args:
            locked_positions: {pos: color} for confirmed positions
            found_colors: set of colors known to exist
            misplaced_colors: set of colors in wrong positions
            available_colors: all valid colors
            num_pegs: number of pegs
            previous_guesses: all previous guesses (to avoid duplicates)

        Returns:
            List of colors (the proposed guess)
        """
        if previous_guesses is None:
            previous_guesses = []

        # Build guess
        guess = [None] * num_pegs

        # Step 1: Fill locked positions
        for pos, color in locked_positions.items():
            if pos < num_pegs:
                guess[pos] = color

        # Step 2: For remaining positions, prioritize:
        # a) Misplaced colors (test in new positions)
        # b) New colors (explore untested)

        used_in_guess = set(c for c in guess if c)
        misplaced_to_test = list(misplaced_colors - set(locked_positions.values()))

        for pos in range(num_pegs):
            if guess[pos] is not None:
                continue  # Already filled

            # Prefer untested colors
            untested = [c for c in available_colors if c not in used_in_guess]

            if untested:
                guess[pos] = untested[0]
                used_in_guess.add(untested[0])
            elif misplaced_to_test:
                color = misplaced_to_test.pop(0)
                guess[pos] = color
                used_in_guess.add(color)
            else:
                guess[pos] = random.choice(available_colors)
                used_in_guess.add(guess[pos])

        # Step 3: Avoid duplicates
        max_attempts = 10
        for attempt in range(max_attempts):
            if guess not in previous_guesses:
                return guess

            # Modify to avoid duplicate
            for pos in range(num_pegs):
                if pos not in locked_positions:
                    other_colors = [c for c in available_colors if c != guess[pos]]
                    if other_colors:
                        guess[pos] = random.choice(other_colors)
                        break

        return guess
