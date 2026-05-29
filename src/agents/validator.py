# Validator Agent
# Quality control before guess submission (irreversible action)
# Checks format, validates colors, detects duplicates/repeats
# Input: proposed guess + metadata. Output: validation JSON (is_valid, errors, ready_to_submit)

from typing import List, Dict, Any
from .base_agent import BaseAgent


class ValidatorAgent(BaseAgent):
    """Quality control before guess submission.

    Role: Validation and error prevention

    Input: Proposed guess from Proposer
    Output: JSON with validation result and any errors
    """

    def __init__(self, provider: str = "ollama"):
        super().__init__(name="Validator", provider=provider)

    def validate_guess(
        self,
        guess: List[str],
        available_colors: List[str],
        expected_length: int,
        previous_guesses: List[List[str]] = None
    ) -> Dict[str, Any]:
        """Validate guess before submission.

        Checks:
        1. Correct number of pegs
        2. All colors are valid
        3. Not a duplicate of previous guess
        4. No format errors

        Args:
            guess: Proposed guess (list of colors)
            available_colors: Valid colors for this puzzle
            expected_length: Expected number of pegs (4, 5, or 6)
            previous_guesses: List of all previous guesses

        Returns:
            {
                "is_valid": bool,
                "ready_to_submit": bool,
                "errors": [str, ...],
                "warnings": [str, ...],
                "comments": str
            }
        """
        errors = []
        warnings = []

        # Check length
        if not isinstance(guess, list):
            errors.append(f"Guess must be a list, got {type(guess).__name__}")

        if len(guess) != expected_length:
            errors.append(f"Wrong number of pegs: expected {expected_length}, got {len(guess)}")

        # Check colors
        for i, color in enumerate(guess):
            if not isinstance(color, str):
                errors.append(f"Position {i}: color must be string, got {type(color).__name__}")
            elif color not in available_colors:
                errors.append(f"Position {i}: invalid color '{color}'. Valid: {available_colors}")

        # Check for duplicates with previous guesses
        if previous_guesses is None:
            previous_guesses = []

        for prev_guess in previous_guesses:
            if guess == prev_guess:
                warnings.append(f"This guess was tried before: {prev_guess}")

        # Generate comments
        comments = ""
        if len(guess) == len(set(guess)):
            comments = "All colors are unique."
        else:
            unique_count = len(set(guess))
            comments = f"Guess has {unique_count} unique color(s) out of {len(guess)}."

        is_valid = len(errors) == 0
        ready_to_submit = is_valid and len(warnings) == 0

        return {
            "is_valid": is_valid,
            "ready_to_submit": ready_to_submit,
            "errors": errors,
            "warnings": warnings,
            "comments": comments
        }

    def validate_with_llm(
        self,
        guess: List[str],
        available_colors: List[str],
        expected_length: int,
        previous_guesses: List[List[str]] = None,
        constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Validate guess using LLM for deeper analysis.

        Can detect semantic and constraint violations, not just format issues.

        Args:
            guess: Proposed guess
            available_colors: Valid colors
            expected_length: Expected length
            previous_guesses: Previous guesses
            constraints: Dict with locked_positions, misplaced_colors, impossible_colors

        Returns:
            Detailed validation result from LLM
        """
        prev_guesses_str = ""
        if previous_guesses:
            prev_guesses_str = "\n".join([f"- {g}" for g in previous_guesses])

        # Format constraints for prompt
        constraints_text = "None yet"
        if constraints:
            constraint_lines = []

            if constraints.get("correct_positions"):
                for pos_info in constraints["correct_positions"]:
                    # Handle both dict and string formats
                    if isinstance(pos_info, dict):
                        constraint_lines.append(f"- LOCKED: position {pos_info['position']} → {pos_info['color']}")
                    else:
                        # String format
                        constraint_lines.append(f"- LOCKED: {pos_info}")

            if constraints.get("correct_colors_wrong_position"):
                for color in constraints["correct_colors_wrong_position"]:
                    constraint_lines.append(f"- MISPLACED: {color} (exists but wrong position)")

            if constraints.get("impossible_colors"):
                constraint_lines.append(f"- IMPOSSIBLE: {', '.join(constraints['impossible_colors'])}")

            if constraint_lines:
                constraints_text = "\n".join(constraint_lines)

        prompt = f"""You are the Validator for a Mastermind puzzle solver.

VALIDATION RULES (CRITICAL):
1. Guess must have exactly {expected_length} pegs, all valid colors
2. Never move a color from a LOCKED position (it's confirmed correct)
3. Never use a color from the IMPOSSIBLE list (already eliminated)
4. For MISPLACED colors: they MUST appear in the guess, but in a DIFFERENT position

WORKED EXAMPLES:

Example 1 - Valid guess (respects all constraints):
Constraints:
- LOCKED: [position 0→red]
- MISPLACED: [blue (not at 1), yellow (not at 3)]
- IMPOSSIBLE: [white, black]
Proposed guess: ["red", "yellow", "blue", "purple"]
→ Position 0: Red (locked, correct) ✓
→ Position 1: Yellow (misplaced, new position) ✓
→ Position 2: Blue (misplaced, new position) ✓
→ Position 3: Purple (new color, allowed) ✓
VALID: All constraints satisfied

Example 2 - Invalid guess (violates locked position):
Constraints:
- LOCKED: [position 0→red, position 2→green]
- MISPLACED: [blue]
Proposed guess: ["blue", "red", "green", "black"]
→ Position 0: Blue (but should be RED) ✗
INVALID: Violates locked position constraint

Example 3 - Invalid guess (uses impossible color):
Constraints:
- LOCKED: [position 1→blue]
- MISPLACED: [red]
- IMPOSSIBLE: [yellow, white, black]
Proposed guess: ["red", "blue", "yellow", "purple"]
→ Position 3: Yellow (impossible!) ✗
INVALID: Uses impossible color (yellow)

Example 4 - Invalid guess (misplaced in same position):
Constraints:
- LOCKED: [position 2→green]
- MISPLACED: [blue (not at 1)]
Proposed guess: ["yellow", "blue", "green", "orange"]
→ Position 1: Blue (same position as before!) ✗
INVALID: Misplaced color must be in new position

TASK:

Guess to validate: {guess}
Pegs needed: {expected_length}
Constraints:
{constraints_text}
Available colors: {available_colors}
Previous guesses: {prev_guesses_str if prev_guesses_str else "None"}

OUTPUT (ONLY JSON, no markdown):
{{
  "is_valid": true,
  "ready_to_submit": true,
  "errors": [],
  "warnings": [],
  "constraint_check": {{
    "locked_positions": "All locked positions preserved",
    "impossible_colors": "No impossible colors used",
    "misplaced_colors": "All in new positions",
    "format": "Correct"
  }},
  "comments": "Guess respects all constraints"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result:
            # Fall back to programmatic validation
            return self.validate_guess(guess, available_colors, expected_length, previous_guesses)

        return result

    def process(
        self,
        guess: List[str] = None,
        available_colors: List[str] = None,
        expected_length: int = 4,
        previous_guesses: List[List[str]] = None,
        constraints: Dict[str, Any] = None,
        use_llm: bool = False
    ) -> Dict[str, Any]:
        """Standard process interface.

        Args:
            guess: Proposed guess
            available_colors: Valid colors
            expected_length: Number of pegs
            previous_guesses: Previous guesses
            constraints: Dict with locked_positions, misplaced_colors, impossible_colors
            use_llm: Use LLM for validation (more thorough, slower)

        Returns:
            Validation result dictionary
        """
        if guess is None:
            guess = []
        if available_colors is None:
            available_colors = ["red", "blue", "green", "yellow", "white", "black"]
        if previous_guesses is None:
            previous_guesses = []
        if constraints is None:
            constraints = {}

        if use_llm:
            return self.validate_with_llm(guess, available_colors, expected_length, previous_guesses, constraints)
        else:
            return self.validate_guess(guess, available_colors, expected_length, previous_guesses)
