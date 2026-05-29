# Strategist Agent
# Proposes high-level guessing strategy based on feedback patterns
# Analyzes past guesses, identifies constraints, recommends next approach
# Input: guess history + feedback. Output: strategy JSON (analysis, strategy, reasoning)

import json
from typing import List, Dict, Any
from .base_agent import BaseAgent


class StrategistAgent(BaseAgent):
    """Proposes high-level strategy for next guess(es).

    Role: Strategic planning based on feedback patterns

    Input: List of previous guesses with feedback
    Output: JSON with analysis, strategy, and reasoning
    """

    def __init__(self, provider: str = "ollama"):
        super().__init__(name="Strategist", provider=provider)

    def propose_strategy(self, guess_history: List[Dict[str, Any]], difficulty: str) -> Dict[str, Any]:
        """Propose strategy for next guess(es).

        Args:
            guess_history: List of {"round": int, "guess": list, "feedback": dict}
            difficulty: "easy", "medium", or "hard"

        Returns:
            {
                "phase": str,           # EXPLORATION, CONSTRAINT BUILDING, REFINEMENT, CONFIRMATION
                "analysis": str,        # What we learned so far
                "strategy": str,        # Our approach
                "recommended_positions": dict,  # Specific positions to test
                "reasoning": str,       # Why this strategy
                "confidence": float     # 0.0-1.0 confidence in strategy
            }
        """
        # Format feedback for prompt
        feedback_text = self._format_feedback(guess_history)

        prompt = f"""SYSTEM: You are analyzing a Mastermind game. The goal is to guess a 4-color code.

CONTEXT:
{feedback_text}

TASK: Determine the strategy for the next guess.

RULES:
- Exploration phase: Test diverse colors to find which ones exist
- Constraint-building: Test found colors in different positions
- Refinement: Lock positions one by one
- Confirmation: Final guess when nearly solved

RESPOND WITH ONLY THIS JSON (no other text):
{{
  "phase": "EXPLORATION or CONSTRAINT_BUILDING or REFINEMENT or CONFIRMATION",
  "analysis": "Brief description of what we know",
  "strategy": "One sentence strategy for next guess",
  "confidence": 0.5
}}

Example output:
{{
  "phase": "EXPLORATION",
  "analysis": "No information yet",
  "strategy": "Test 4 diverse colors to find which exist",
  "confidence": 0.5
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        # If JSON parsing failed, raise error (no fallback)
        if "error" in result:
            raise ValueError(f"Strategist JSON parse failed: {result.get('error')}")

        return result

    def _format_feedback(self, guess_history: List[Dict[str, Any]]) -> str:
        """Format guess history for prompt."""
        if not guess_history:
            return "No previous guesses yet."

        lines = []
        for item in guess_history:
            guess = item.get("guess", [])
            feedback = item.get("feedback", {})
            round_num = item.get("round", 1)

            correct_pegs = feedback.get("correct_pegs", 0)
            correct_positions = feedback.get("correct_positions", 0)

            lines.append(
                f"Round {round_num}: {guess} → "
                f"{correct_pegs} correct colors, {correct_positions} correct positions"
            )

        return "\n".join(lines)

    def process(self, guess_history: List[Dict[str, Any]] = None, difficulty: str = "easy") -> Dict[str, Any]:
        """Standard process interface.

        Args:
            guess_history: List of previous guesses with feedback
            difficulty: Puzzle difficulty

        Returns:
            Strategy proposal dictionary
        """
        if guess_history is None:
            guess_history = []

        return self.propose_strategy(guess_history, difficulty)
