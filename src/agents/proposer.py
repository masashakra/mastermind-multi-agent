# Proposer Agent
# Generates specific next guess from strategy and constraints
# Input: strategy + constraints + available colors. Output: proposed guess JSON

from typing import List, Dict, Any
from .base_agent import BaseAgent


class ProposerAgent(BaseAgent):
    """Generates concrete guess from strategy and constraints."""

    def __init__(self, provider: str = "ollama"):
        super().__init__(name="Proposer", provider=provider)

    def propose_guess(
        self,
        strategy: str,
        constraints_text: str,
        available_colors: List[str],
        num_pegs: int,
        previous_guesses: List[List[str]] = None
    ) -> Dict[str, Any]:
        """Propose next guess based on strategy and constraints."""

        # CRITICAL: Extract locked positions from constraints
        locked_positions = self._extract_locked_positions(constraints_text, num_pegs)

        prompt = f"""SYSTEM: Generate a Mastermind guess.

STRATEGY: {strategy}

CONSTRAINTS:
{constraints_text}

LOCKED POSITIONS (MUST NOT CHANGE):
{self._format_locked_positions(locked_positions)}

AVAILABLE COLORS: {available_colors}
PEGS NEEDED: {num_pegs}

RESPOND WITH ONLY THIS JSON (no markdown):
{{
  "proposed_guess": ["color1", "color2", "color3", "color4"],
  "justification": "one sentence reason"
}}

Example:
{{
  "proposed_guess": ["red", "blue", "green", "yellow"],
  "justification": "Test diverse colors"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        # If JSON parsing failed, raise error
        if "error" in result:
            raise ValueError(f"Proposer JSON parse failed: {result.get('error')}")

        # CRITICAL: Enforce locked positions
        guess = result.get("proposed_guess", [])
        enforced_guess = self._enforce_locked_positions(guess, locked_positions, num_pegs, available_colors)
        result["proposed_guess"] = enforced_guess
        result["locked_positions_enforced"] = True

        return result

    def _extract_locked_positions(self, constraints_text: str, num_pegs: int) -> Dict[int, str]:
        """Extract locked positions from constraints text.

        Looks for patterns like "red locked at position 0" or "position 0: red (LOCKED)"
        """
        locked = {}
        for line in constraints_text.split("\n"):
            line_lower = line.lower()

            # Pattern: "color locked at position X"
            if "locked at position" in line_lower:
                try:
                    # Extract position
                    pos_start = line_lower.index("position") + 8
                    pos_text = line_lower[pos_start:].split()[0].rstrip(":")
                    pos = int(pos_text)

                    # Extract color (before "locked")
                    color_part = line[:line_lower.index("locked")].strip()
                    color = color_part.lower().strip()

                    if 0 <= pos < num_pegs and color:
                        locked[pos] = color
                except (ValueError, IndexError):
                    pass

        return locked

    def _format_locked_positions(self, locked_positions: Dict[int, str]) -> str:
        """Format locked positions for the prompt."""
        if not locked_positions:
            return "None - all positions unknown"

        lines = []
        for pos in sorted(locked_positions.keys()):
            lines.append(f"  Position {pos}: {locked_positions[pos]} (MUST NOT CHANGE)")
        return "\n".join(lines)

    def _enforce_locked_positions(
        self,
        guess: List[str],
        locked_positions: Dict[int, str],
        num_pegs: int,
        available_colors: List[str]
    ) -> List[str]:
        """Enforce locked positions in the guess.

        If LLM didn't respect locked positions, fix them manually.
        """
        # Make a copy
        enforced = list(guess) if guess else []

        # Ensure correct length
        while len(enforced) < num_pegs:
            enforced.append(available_colors[0])  # Default fallback
        enforced = enforced[:num_pegs]

        # FORCE locked positions
        for pos, color in locked_positions.items():
            if pos < num_pegs:
                enforced[pos] = color

        return enforced

    def process(
        self,
        strategy: str = "",
        constraints_text: str = "",
        available_colors: List[str] = None,
        num_pegs: int = 4
    ) -> Dict[str, Any]:
        """Standard process interface."""
        if available_colors is None:
            available_colors = ["red", "blue", "green", "yellow", "white", "black"]

        return self.propose_guess(strategy, constraints_text, available_colors, num_pegs)
