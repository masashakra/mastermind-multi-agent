# Strategist Agent
# Proposes high-level guessing strategy based on feedback patterns
# Analyzes past guesses, identifies constraints, recommends next approach
# Input: guess history + feedback. Output: strategy JSON (analysis, strategy, reasoning)

import json
from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent
from communication.protocol import A2ACommunicationLayer


class StrategistAgent(BaseAgent):
    """Proposes high-level strategy for next guess(es).

    Role: Strategic planning based on feedback patterns

    Input: List of previous guesses with feedback
    Output: JSON with analysis, strategy, and reasoning
    """

    def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None):
        super().__init__(name="Strategist", provider=provider, comm_layer=comm_layer)

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

        prompt = f"""You are the STRATEGIST in a Mastermind puzzle solver.

ROLE: Analyze feedback patterns and propose the next strategic direction.

STRATEGIC REASONING (Think Step-by-Step):

Step 1: ASSESSMENT - What do we know so far?
  - How many colors have we found?
  - How many positions are locked?
  - What colors are impossible?

Step 2: PHASE IDENTIFICATION - Where are we in the puzzle?
  - EXPLORATION: Testing which colors exist
  - CONSTRAINT_BUILDING: Testing found colors in different positions
  - REFINEMENT: Locking positions one by one
  - CONFIRMATION: Final verification when nearly solved

Step 3: OPPORTUNITY - What information is most valuable next?
  - Unknown positions? Test more position variations
  - Unknown colors? Test new colors
  - Locks uncertain? Try different arrangements

Step 4: STRATEGY - What should we test and why?

WORKED EXAMPLE:
History:
  Round 1: [red, blue, green, yellow] → 2 colors exist, 0 in right position
  Round 2: [red, green, white, black] → 2 colors exist, 1 in right position (improvement!)

Reasoning:
  Step 1: We have 2 colors from round 1. Red+green or red+blue or blue+green?
          Round 2 had red+green and got 2 colors + 1 position, so likely red+green exist.
          We also know one of red/green is locked.
  Step 2: We're in CONSTRAINT_BUILDING phase (know colors, testing positions)
  Step 3: Need to identify which of red/green is locked, and find other 2 colors
  Step 4: Test different arrangements of red/green, and try new colors

Strategy: "Keep red and green, vary their positions, introduce 2 new colors"
Phase: CONSTRAINT_BUILDING
Confidence: 0.8

GAME PROGRESS:
{feedback_text}

Difficulty: {difficulty}

TASK: Analyze the game state and propose the next strategic approach.

OUTPUT (JSON ONLY):
{{
  "phase": "EXPLORATION or CONSTRAINT_BUILDING or REFINEMENT or CONFIRMATION",
  "reasoning_steps": [
    "Step 1 Assessment: [what we know]",
    "Step 2 Phase: [where we are]",
    "Step 3 Opportunity: [what's most valuable]",
    "Step 4 Strategy: [what to do next and why]"
  ],
  "analysis": "Summary of what we learned so far",
  "strategy": "Specific next direction (2-3 sentences)",
  "confidence": 0.75
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
