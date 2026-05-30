# Proposer Agent
# Generates specific next guess from strategy and constraints
# Input: strategy + constraints + available colors. Output: proposed guess JSON

from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent
from communication.protocol import A2ACommunicationLayer


class ProposerAgent(BaseAgent):
    """Generates concrete guess from strategy and constraints."""

    def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None):
        super().__init__(name="Proposer", provider=provider, comm_layer=comm_layer)

    def propose_guess(
        self,
        strategy: str,
        constraints_text: str,
        available_colors: List[str],
        num_pegs: int,
        previous_guesses: List[List[str]] = None
    ) -> Dict[str, Any]:
        """Propose next guess based on strategy and constraints."""

        # CRITICAL: Extract constraints from text
        locked_positions = self._extract_locked_positions(constraints_text, num_pegs)
        impossible_colors = self._extract_impossible_colors(constraints_text)

        # Determine which colors to avoid
        colors_to_avoid = impossible_colors
        valid_colors = [c for c in available_colors if c not in colors_to_avoid]
        if not valid_colors:  # Safety: use all if none left
            valid_colors = available_colors

        # Build locked positions section with absolute clarity
        locked_section = ""
        if locked_positions:
            locked_section = "LOCKED POSITIONS (CANNOT CHANGE - these are 100% confirmed):\n"
            for pos in sorted(locked_positions.keys()):
                locked_section += f"  Position {pos}: MUST be '{locked_positions[pos]}' - DO NOT CHANGE THIS\n"
        else:
            locked_section = "LOCKED POSITIONS: None yet\n"

        prompt = f"""SYSTEM: Generate a Mastermind guess.

CRITICAL RULES (FOLLOW EXACTLY):
1. Positions 0-{num_pegs-1} that are LOCKED must stay LOCKED with the exact same color
2. Colors not in the available list are FORBIDDEN
3. Colors in the impossible list are FORBIDDEN
4. Generate ONLY valid guesses

STRATEGY: {strategy}

CONSTRAINTS (recent discoveries):
{constraints_text}

{locked_section}

IMPOSSIBLE COLORS (never use): {', '.join(colors_to_avoid) if colors_to_avoid else "None"}
AVAILABLE COLORS (only use these): {', '.join(valid_colors)}

FILL IN THE BLANKS (keep locked positions exactly as shown):
{self._build_template_from_locked(locked_positions, num_pegs, valid_colors)}

RESPOND WITH ONLY THIS JSON (no markdown, no explanation):
{{
  "proposed_guess": ["pos0_color", "pos1_color", "pos2_color", "pos3_color"],
  "justification": "one sentence"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        # If JSON parsing failed, raise error
        if "error" in result:
            raise ValueError(f"Proposer JSON parse failed: {result.get('error')}")

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

        Looks for patterns like:
        - "red locked at position 0"
        - "position 0: red (LOCKED)"
        - "Position 0: red (LOCKED)"
        """
        locked = {}
        for line in constraints_text.split("\n"):
            line_lower = line.lower()

            # Pattern 1: "position X: color (LOCKED)"
            if "position" in line_lower and "locked" in line_lower:
                try:
                    # Extract position number
                    pos_idx = line_lower.index("position") + 8
                    pos_text = line_lower[pos_idx:].split(":")[0].strip()
                    pos = int(pos_text)

                    # Extract color (between : and ( or end of line)
                    if ":" in line:
                        after_colon = line.split(":", 1)[1]
                        # Remove (LOCKED) or similar
                        color_part = after_colon.split("(")[0].strip()
                        color = color_part.lower()

                        if 0 <= pos < num_pegs and color:
                            locked[pos] = color
                except (ValueError, IndexError):
                    pass

            # Pattern 2: "color locked at position X"
            elif "locked at position" in line_lower:
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

    def _extract_impossible_colors(self, constraints_text: str) -> List[str]:
        """Extract impossible colors from constraints text.

        Looks for patterns like:
        - "red is IMPOSSIBLE"
        - "red is impossible - not in code"
        """
        impossible = []
        for line in constraints_text.split("\n"):
            line_lower = line.lower()
            if "impossible" in line_lower:
                # Extract color (word before "is impossible")
                try:
                    words = line.split()
                    for i, word in enumerate(words):
                        if "impossible" in word.lower():
                            # Color is usually before this word
                            if i > 0:
                                color = words[i-1].lower().strip()
                                if color and not color.startswith("-"):
                                    impossible.append(color)
                except:
                    pass
        return impossible

    def _format_locked_positions(self, locked_positions: Dict[int, str]) -> str:
        """Format locked positions for the prompt."""
        if not locked_positions:
            return "None - all positions unknown"

        lines = []
        for pos in sorted(locked_positions.keys()):
            lines.append(f"  Position {pos}: {locked_positions[pos]} (MUST NOT CHANGE)")
        return "\n".join(lines)

    def _build_template_from_locked(self, locked_positions: Dict[int, str], num_pegs: int, available_colors: List[str]) -> str:
        """Build a template showing locked positions that LLM must preserve.

        Shows locked positions with placeholders for other positions.
        """
        template = []
        for pos in range(num_pegs):
            if pos in locked_positions:
                # This position is LOCKED - show the exact color
                template.append(f"Position {pos}: ['{locked_positions[pos]}' - LOCKED, DO NOT CHANGE]")
            else:
                # This position is open - LLM must fill it
                template.append(f"Position {pos}: [choose from: {', '.join(available_colors)}]")
        return "\n".join(template)

    def _enforce_locked_positions(
        self,
        guess: List[str],
        locked_positions: Dict[int, str],
        num_pegs: int,
        available_colors: List[str]
    ) -> List[str]:
        """Enforce locked positions in the guess.

        If LLM didn't respect locked positions, fix them manually.
        Also validates that all colors are in available_colors.
        """
        # Make a copy
        enforced = list(guess) if guess else []

        # Ensure correct length
        while len(enforced) < num_pegs:
            enforced.append(available_colors[0])  # Default fallback
        enforced = enforced[:num_pegs]

        # Validate and fix invalid colors
        for i, color in enumerate(enforced):
            if color not in available_colors:
                enforced[i] = available_colors[0]  # Replace with first valid color

        # FORCE locked positions (must be after color validation)
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
