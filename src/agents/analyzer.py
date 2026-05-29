# Analyzer Agent
# Interprets feedback and extracts constraints
# Input: latest guess + feedback. Output: constraint analysis JSON

from typing import List, Dict, Any
from .base_agent import BaseAgent


class AnalyzerAgent(BaseAgent):
    """Interprets feedback and extracts constraints."""

    def __init__(self, provider: str = "ollama"):
        super().__init__(name="Analyzer", provider=provider)

    def analyze_feedback(
        self,
        last_guess: List[str],
        feedback: Dict[str, int],
        previous_guesses: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze feedback and extract constraints.

        Args:
            last_guess: List of colors in last guess
            feedback: {"correct_pegs": int, "correct_positions": int}
            previous_guesses: Optional list of previous guesses

        Returns:
            Constraint analysis dictionary
        """
        correct_pegs = feedback.get("correct_pegs", 0)
        correct_positions = feedback.get("correct_positions", 0)

        # Format history
        history_text = "No previous guesses" if not previous_guesses else "\n".join(
            f"Round {i+1}: {g.get('guess')} → {g.get('feedback')}"
            for i, g in enumerate(previous_guesses[-3:])  # Last 3 rounds
        )

        prompt = f"""SYSTEM: Analyze Mastermind feedback. Be CONSERVATIVE - only identify locked positions if CERTAIN.

LAST GUESS: {last_guess}
FEEDBACK: {correct_pegs} total colors exist, {correct_positions} in correct positions

RULES:
- A position is LOCKED only if the color at that position is NEW (never tested there before) AND feedback shows locked positions increased
- If feedback is UNCHANGED from previous round, don't declare new locked positions
- Only mark colors IMPOSSIBLE if they were in the guess but didn't help the feedback count

PREVIOUS GUESSES:
{history_text}

RESPOND WITH ONLY THIS JSON:
{{
  "correct_positions": [],
  "correct_colors_wrong_position": ["green"],
  "impossible_colors": ["red", "blue"],
  "constraints": ["green exists but not at position 0"],
  "analysis": "Found 1 color, need to test positions"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result:
            raise ValueError(f"Analyzer JSON parse failed: {result.get('error')}")

        return result

    def process(
        self,
        last_guess: List[str] = None,
        feedback: Dict[str, int] = None,
        previous_guesses: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Standard process interface."""
        if last_guess is None or feedback is None:
            return {
                "correct_positions": [],
                "correct_colors_wrong_position": [],
                "constraints": [],
                "impossible_colors": [],
                "analysis": "No feedback available"
            }

        if previous_guesses is None:
            previous_guesses = []

        return self.analyze_feedback(last_guess, feedback, previous_guesses)
