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

        prompt = f"""You are the Strategist for a Mastermind puzzle solver.

MASTERMIND STRATEGY PRINCIPLES:
1. Information Entropy: Each guess should maximize information learned
   - Testing colors we're uncertain about is better than retesting known colors
   - Testing positions we're uncertain about is better than retesting locked positions
   - Avoid redundancy - don't test the same color/position combination twice

2. Systematic Exploration:
   - Phase 1 (Exploration): Find WHICH colors exist (test diverse colors)
   - Phase 2 (Localization): Find WHERE each color goes (test positions)
   - Phase 3 (Confirmation): Fill remaining gaps with confidence

3. Smart Position Testing:
   - Locked position: NEVER change it (you know it's correct)
   - Misplaced color: Test it in DIFFERENT position from before
   - Unknown position: Test NEW colors to find what exists

4. Avoid Wasting Guesses:
   - Don't guess same color in same position twice
   - Don't test a color you already know is impossible
   - Don't change locked positions

WORKED EXAMPLES:

Example 1 - EXPLORATION (Round 1, no data):
History: None
→ Phase: EXPLORATION
→ Strategy: "Test 4 diverse colors (red, blue, green, yellow) to learn existence"
→ Why: First guess determines which colors are even relevant
→ Confidence: 0.5

Example 2 - LOCALIZATION (found colors, finding positions):
History:
- Round 1: [red, blue, green, yellow] → 2 colors, 0 positions (none locked yet)
- Round 2: [white, blue, green, yellow] → 2 colors, 1 position (one is locked!)
→ Phase: CONSTRAINT_BUILDING
→ Analysis: White is new and now we have 1 locked. White is likely locked.
→ Strategy: "Keep white locked at position 0. Test blue in different position to see if it's locked"
→ Recommended: [white, NEW_COLOR, blue, yellow] OR [white, green, blue, yellow]
→ Why: Isolate whether blue or another color is locked
→ Confidence: 0.65

Example 3 - Found what exists, need positions:
History:
- Round 1: [red, blue, green, yellow] → 1 color, 0 positions
- Round 2: [white, blue, green, yellow] → 2 colors, 1 position
- Round 3: [white, red, green, yellow] → 2 colors, 1 position (feedback didn't change!)
→ Analysis: We have white locked. Round 2→3 feedback same, so we still don't know if 2nd is blue, red, or another
→ Phase: CONSTRAINT_BUILDING
→ Strategy: "Keep white. We found only 2 colors exist in 4 pegs. Test NEW colors to find the 2nd one"
→ Recommended: [white, black, purple, orange]
→ Why: Try completely new colors to identify which one is the 2nd existing color
→ Confidence: 0.7

Example 4 - Colors known, positions almost done:
History: Locked positions: [0→white, 2→green], Misplaced: [red]
→ Phase: REFINEMENT
→ Analysis: 3 of 4 determined. Red must be at position 1 or 3.
→ Strategy: "Red at position 1? Test: [white, red, green, new_color]"
→ Why: One test can confirm position 1, eliminating 1 possibility
→ Confidence: 0.85

Example 5 - Almost certain:
History: 3 locked positions known, just finding position 3
→ Phase: CONFIRMATION
→ Strategy: "Make high-confidence guess with all known locked positions + best guess for final"
→ Why: We've narrowed possibilities to just a few options
→ Confidence: 0.95

STRATEGY SELECTION RULES:
- MORE INFO NEEDED: If you have <3 colors confirmed, focus on finding more colors
- POSITION BUILDING: If you have 3+ colors, focus on testing their positions
- CONFIRMATION: If positions almost complete (3+ locked), make final guess
- AVOID WASTE: Never test same color in same position you already tested

TASK:

Difficulty: {difficulty}
Pegs needed: 4

FEEDBACK HISTORY:
{feedback_text}

Based on the history:
1. What information do we have confirmed?
2. What information gaps remain?
3. What's the best strategy to fill those gaps?
4. What phase are we in?

Output ONLY with valid JSON:
{{
  "phase": "REFINEMENT",
  "analysis": "We have white locked at 0, green exists. Need positions for green.",
  "strategy": "Keep white at 0. Test green at positions 1, 2, 3 to find where it goes. Test new colors.",
  "recommended_positions": {{
    "position_0": "white (LOCKED - don't change)",
    "position_1": "test green or new color",
    "position_2": "test green or new color",
    "position_3": "test green or new color"
  }},
  "reasoning": "We're halfway done. Systematic position testing will find green's position.",
  "confidence": 0.75
}}"""

        try:
            response = self.call_llm(prompt)
            result = self.parse_json_response(response)
        except Exception as e:
            # LLM failed - use heuristic strategy
            result = self._generate_heuristic_strategy(guess_history, difficulty)
            result["llm_failed"] = True
            result["error_reason"] = str(e)

        # Validate response
        if "error" in result:
            return {
                "phase": "EXPLORATION" if not guess_history else "REFINEMENT",
                "analysis": "Could not process feedback",
                "strategy": "Continue with diverse colors" if not guess_history else "Test new colors at unknown positions",
                "reasoning": "Fallback strategy",
                "confidence": 0.5,
                "parse_error": result.get("error")
            }

        return result

    def _generate_heuristic_strategy(
        self, guess_history: List[Dict[str, Any]], difficulty: str
    ) -> Dict[str, Any]:
        """Generate strategy using simple heuristics when LLM fails.

        Rules:
        - Round 1: EXPLORATION - test diverse colors
        - Rounds 2+: Look at feedback trend
          - If colors found < 2: still CONSTRAINT_BUILDING
          - If colors found ≥ 3: REFINEMENT
          - If positions locked ≥ 3: CONFIRMATION

        Args:
            guess_history: List of previous guesses with feedback
            difficulty: "easy", "medium", or "hard"

        Returns:
            Strategy dict
        """
        if not guess_history:
            return {
                "phase": "EXPLORATION",
                "analysis": "First guess - test diverse colors",
                "strategy": "Test 4 diverse common colors to find which ones exist",
                "reasoning": "Starting from scratch - need to know which colors are relevant",
                "confidence": 0.5,
                "is_heuristic": True
            }

        # Analyze feedback trends
        latest = guess_history[-1]
        feedback = latest.get("feedback", {})
        total_colors = feedback.get("correct_pegs", 0)
        locked_count = feedback.get("correct_positions", 0)

        if total_colors < 2:
            phase = "EXPLORATION"
            strategy = "Test more diverse colors to find what exists"
        elif total_colors >= 3 and locked_count < 2:
            phase = "CONSTRAINT_BUILDING"
            strategy = "Test the known colors in different positions to find which are locked"
        elif locked_count >= 3:
            phase = "CONFIRMATION"
            strategy = "Almost there - just fill in the final position(s)"
        else:
            phase = "REFINEMENT"
            strategy = "Find remaining colors and their positions"

        return {
            "phase": phase,
            "analysis": f"Found {total_colors} colors, {locked_count} in correct positions",
            "strategy": strategy,
            "reasoning": f"Heuristic based on feedback pattern: {total_colors}/{locked_count}",
            "confidence": 0.6,
            "is_heuristic": True
        }

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
