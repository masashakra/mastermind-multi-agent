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

        prompt = f"""SYSTEM: Generate a Mastermind guess.

STRATEGY: {strategy}

CONSTRAINTS:
{constraints_text}

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

        return result

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
