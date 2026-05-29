# Analyzer V3
# BETTER: Simpler, more reliable constraint extraction

from typing import List, Dict, Any, Tuple


class AnalyzerV3:
    """Improved constraint extraction using more careful logic."""

    def analyze(
        self,
        guess_history: List[Dict[str, Any]],
        available_colors: List[str],
        num_pegs: int
    ) -> Dict[str, Any]:
        """Extract constraints from feedback.

        Key insights:
        1. correct_pegs tells us total colors that exist
        2. correct_positions tells us how many are locked
        3. By comparing rounds, we can identify locked positions
        4. Colors that increase feedback when added are real colors
        """
        if not guess_history:
            return {
                "locked_positions": {},
                "found_colors": [],
                "misplaced_colors": [],
                "impossible_colors": [],
                "total_colors_in_secret": 0,
                "analysis": "No guesses yet"
            }

        locked_positions = {}
        found_colors = set()
        impossible_colors = set()

        # Strategy: Track feedback changes between rounds
        latest_feedback = guess_history[-1].get("feedback", {})
        total_colors_in_secret = latest_feedback.get("correct_pegs", 0)

        # Collect all colors ever tested
        all_tested = set()
        for item in guess_history:
            all_tested.update(item.get("guess", []))

        # Simple heuristic for locked positions:
        # If a color appears in the same position in multiple guesses with increasing feedback,
        # that position is likely locked with that color
        for pos in range(num_pegs):
            color_at_pos = {}  # color -> best_feedback_when_tested
            for item in guess_history:
                guess = item.get("guess", [])
                if pos < len(guess):
                    color = guess[pos]
                    feedback = item.get("feedback", {})
                    pegs = feedback.get("correct_positions", 0)
                    if color not in color_at_pos or pegs > color_at_pos[color]:
                        color_at_pos[color] = pegs

            # If any color gave high feedback at this position, it's likely locked
            for color, max_pegs in color_at_pos.items():
                if max_pegs > 0:
                    locked_positions[pos] = color
                    found_colors.add(color)
                    break

        # Colors we know exist: those in locked positions + any that increased feedback
        for pos, color in locked_positions.items():
            found_colors.add(color)

        # Try to find other colors that exist by looking at feedback trends
        if len(found_colors) < total_colors_in_secret:
            # Some colors aren't locked but still exist
            # Test: colors that appear when feedback increases
            for i, item in enumerate(guess_history):
                if i == 0:
                    continue
                prev_feedback = guess_history[i - 1].get("feedback", {})
                curr_feedback = item.get("feedback", {})
                prev_pegs = prev_feedback.get("correct_pegs", 0)
                curr_pegs = curr_feedback.get("correct_pegs", 0)

                if curr_pegs > prev_pegs:
                    # Feedback improved! What's new in this guess?
                    prev_guess = guess_history[i - 1].get("guess", [])
                    curr_guess = item.get("guess", [])

                    new_colors = set(curr_guess) - set(prev_guess)
                    for color in new_colors:
                        found_colors.add(color)

        # Colors that never help are impossible
        impossible_colors = all_tested - found_colors

        # Misplaced colors: found but not locked
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
                total_colors_in_secret,
                num_pegs
            )
        }

    def _format_analysis(
        self,
        locked_positions: Dict[int, str],
        found_colors: set,
        misplaced_colors: set,
        total_colors_in_secret: int,
        num_pegs: int
    ) -> str:
        """Format analysis."""
        lines = []
        lines.append(f"Colors in secret: {total_colors_in_secret}/{num_pegs}")

        if locked_positions:
            for pos in sorted(locked_positions.keys()):
                lines.append(f"  Position {pos}: {locked_positions[pos]} (LOCKED)")

        if misplaced_colors:
            lines.append(f"Misplaced: {', '.join(sorted(misplaced_colors))}")

        unknown = num_pegs - len(locked_positions)
        if unknown > 0:
            lines.append(f"Unknown: {unknown} positions")

        return "\n".join(lines)
