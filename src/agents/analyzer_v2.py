# Analyzer V2
# RULE-BASED: Fast constraint extraction without slow LLM

from typing import List, Dict, Any


class AnalyzerV2:
    """Fast, rule-based constraint extraction.

    Analyzes feedback to identify:
    - Locked positions (confirmed correct)
    - Misplaced colors (exist but wrong position)
    - Impossible colors (don't exist)
    - Found colors (confirmed to exist)
    """

    def __init__(self):
        self.name = "Analyzer-V2"

    def analyze(
        self,
        guess_history: List[Dict[str, Any]],
        available_colors: List[str],
        num_pegs: int
    ) -> Dict[str, Any]:
        """Analyze guess history to extract constraints.

        Logic:
        1. Track which colors appear where
        2. When feedback changes, identify what changed
        3. Mark positions as locked when we're confident
        4. Mark colors as impossible when they never help feedback
        5. Mark colors as misplaced when they're in the guess but not at their position

        Args:
            guess_history: [{"guess": [...], "feedback": {"correct_pegs": N, "correct_positions": M}}]
            available_colors: all valid colors
            num_pegs: number of pegs

        Returns:
            {
                "locked_positions": {pos: color},
                "found_colors": [colors],
                "misplaced_colors": [colors],
                "impossible_colors": [colors],
                "total_colors_in_secret": int,
                "analysis": str
            }
        """
        if not guess_history:
            return {
                "locked_positions": {},
                "found_colors": [],
                "misplaced_colors": [],
                "impossible_colors": [],
                "total_colors_in_secret": 0,
                "analysis": "No guesses yet - use exploration strategy"
            }

        locked_positions = {}  # pos -> color (confirmed)
        found_colors = set()  # colors we know exist
        misplaced_colors = set()  # colors that exist but in wrong position
        impossible_colors = set()
        total_colors_in_secret = 0

        # Track position info
        position_tests = {pos: set() for pos in range(num_pegs)}  # Which colors tested at each position
        position_feedback = {pos: [] for pos in range(num_pegs)}  # (color, correct) for each position

        for i, item in enumerate(guess_history):
            guess = item.get("guess", [])
            feedback = item.get("feedback", {})
            correct_pegs = feedback.get("correct_pegs", 0)
            correct_positions = feedback.get("correct_positions", 0)

            # Update total_colors_in_secret based on latest feedback
            total_colors_in_secret = correct_pegs

            # Track what colors were tested at each position
            for pos, color in enumerate(guess):
                if pos < num_pegs:
                    position_tests[pos].add(color)

                # DON'T blindly add all colors to found - we need feedback confirmation
            # Only add colors if feedback says we found more colors this round

            # Analyze position improvements
            if i > 0:
                prev_feedback = guess_history[i - 1].get("feedback", {})
                prev_correct_pos = prev_feedback.get("correct_positions", 0)

                # If correct_positions increased, a new position got locked
                if correct_positions > prev_correct_pos:
                    # Find which position changed
                    prev_guess = guess_history[i - 1].get("guess", [])
                    for pos in range(num_pegs):
                        if pos < len(guess) and pos < len(prev_guess):
                            if guess[pos] != prev_guess[pos]:
                                # This position was changed and now locked!
                                locked_positions[pos] = guess[pos]

            # Check for new locked positions in this round
            # If feedback is "correct_pegs = correct_positions", many colors are locked
            if correct_pegs == correct_positions:
                for pos, color in enumerate(guess):
                    if pos < num_pegs and pos not in locked_positions:
                        # Likely locked
                        locked_positions[pos] = color

        # Refine: colors not found in any feedback are impossible
        all_tested_colors = set()
        for guess_data in guess_history:
            all_tested_colors.update(guess_data.get("guess", []))

        impossible_colors = set(all_tested_colors) - found_colors

        # Colors in found_colors but not in locked_positions are misplaced
        misplaced_colors = found_colors - set(locked_positions.values())

        return {
            "locked_positions": locked_positions,
            "found_colors": sorted(list(found_colors)),
            "misplaced_colors": sorted(list(misplaced_colors)),
            "impossible_colors": sorted(list(impossible_colors)),
            "total_colors_in_secret": total_colors_in_secret,
            "analysis": self._format_analysis(
                locked_positions,
                found_colors,
                misplaced_colors,
                impossible_colors,
                total_colors_in_secret,
                num_pegs
            )
        }

    def _format_analysis(
        self,
        locked_positions: Dict[int, str],
        found_colors: set,
        misplaced_colors: set,
        impossible_colors: set,
        total_colors_in_secret: int,
        num_pegs: int
    ) -> str:
        """Format analysis as readable text."""
        lines = []

        lines.append(f"Total colors in secret: {total_colors_in_secret}/{num_pegs}")

        if locked_positions:
            for pos in sorted(locked_positions.keys()):
                lines.append(f"  Position {pos}: {locked_positions[pos]} (LOCKED)")

        if found_colors:
            lines.append(f"Found colors: {', '.join(sorted(found_colors))}")

        if misplaced_colors:
            lines.append(f"Misplaced: {', '.join(sorted(misplaced_colors))} (exist, wrong positions)")

        if impossible_colors:
            lines.append(f"Impossible: {', '.join(sorted(impossible_colors))}")

        unknown_positions = num_pegs - len(locked_positions)
        if unknown_positions > 0:
            lines.append(f"Unknown: {unknown_positions} positions to fill")

        return "\n".join(lines)
