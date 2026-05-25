# Analyzer Agent
# Interprets feedback and extracts hard constraints
# Identifies which colors/positions are locked, which are impossible
# Input: latest guess + feedback. Output: constraint analysis JSON

from typing import List, Dict, Any
from .base_agent import BaseAgent


class AnalyzerAgent(BaseAgent):
    """Interprets feedback and extracts constraints.

    Role: Information processing and constraint extraction

    Input: Latest guess + feedback from game engine
    Output: JSON with constraints, possible states, locked positions
    """

    def __init__(self, provider: str = "ollama"):
        super().__init__(name="Analyzer", provider=provider)

    def analyze_feedback(
        self,
        last_guess: List[str],
        feedback: Dict[str, int],
        previous_guesses: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze feedback and extract constraints conservatively.

        Args:
            last_guess: List of colors in last guess
            feedback: {"correct_pegs": int, "correct_positions": int}
            previous_guesses: Optional list of all previous guesses for context

        Returns:
            {
                "correct_positions": [{"position": int, "color": str}, ...],
                "correct_colors_wrong_position": [str, ...],
                "impossible_colors": [str, ...],
                "constraints": [str, ...],
                "estimated_remaining": str
            }
        """
        # Start with conservative analysis (don't over-infer)
        correct_pegs = feedback.get("correct_pegs", 0)
        correct_positions = feedback.get("correct_positions", 0)

        # Format context
        history_text = ""
        if previous_guesses:
            history_text = "\n".join([
                f"- {g.get('guess')} → {g.get('feedback', {}).get('correct_pegs')} pegs, "
                f"{g.get('feedback', {}).get('correct_positions')} positions"
                for g in previous_guesses
            ])

        prompt = f"""You are the Analyzer for a Mastermind puzzle solver.

CRITICAL FEEDBACK RULES:
1. correct_positions: Exactly N colors are in the EXACT right position
2. correct_pegs: TOTAL count of colors that exist anywhere in the secret
   - This INCLUDES the correct_positions count
   - Example: correct_pegs=3, correct_positions=1 means 3 colors exist, 1 in right place, 2 in wrong places
3. Misplaced colors = correct_pegs - correct_positions

LOCKED POSITION DETECTION (CRITICAL):
A position can ONLY be confirmed locked if:
- A NEW color appears at that position (never seen there before), AND
- The feedback says ≥1 color in correct position
- THEN: The new color is likely locked there

IMPOSSIBLE: Only mark colors IMPOSSIBLE if they appear in THIS guess and don't contribute to the feedback count.

MULTI-ROUND ANALYSIS (CRITICAL):
When comparing rounds with SAME feedback:
- Don't jump to conclusions about which color replaced which
- ONLY conclude about colors that changed position or are new
- Example: If both guesses have feedback "2 colors exist", changing 1 color doesn't tell you it that new color exists
- You MUST see the new color in a DIFFERENT feedback to confirm it

WORKED EXAMPLES:

Example 1 - Simple locked position:
Secret: ["red", "blue", "green", "yellow"]
Guess:  ["red", "blue", "green", "yellow"]
Feedback: correct_positions=4, correct_pegs=4
→ LOCKED: all 4 positions
→ MISPLACED: none
→ IMPOSSIBLE: none

Example 2 - Finding misplaced colors:
Secret: ["red", "blue", "green", "yellow"]
Guess:  ["blue", "red", "green", "yellow"]
Feedback: correct_positions=2, correct_pegs=4
→ Analysis: All 4 colors exist. 2 are in correct position.
→ Position 2 (green) and position 3 (yellow) are locked (they're correct)
→ LOCKED: [pos 2→green, pos 3→yellow]
→ MISPLACED: [red, blue] (exist but wrong positions)
→ IMPOSSIBLE: none

Example 3 - All new colors, none exist:
Secret: ["red", "blue", "green", "yellow"]
Guess:  ["white", "black", "purple", "orange"]
Feedback: correct_positions=0, correct_pegs=0
→ All 4 colors tested don't exist
→ IMPOSSIBLE: [white, black, purple, orange]

Example 4 - Finding locked position with position change:
Secret: ["white", "black", "black", "green"]
Round 1: ["red", "blue", "green", "yellow"] → 1 peg, 0 positions
  → Exactly 1 color exists, not in correct position
Round 2: ["white", "blue", "green", "yellow"] → 2 pegs, 1 position
  → Exactly 2 colors exist, 1 in correct position
  → Position 0 changed: red→white (new color)
  → Feedback improved: white is likely locked at position 0
  → The 2nd color is one of: blue, green, or yellow
  → LOCKED: [pos 0→white]
  → MISPLACED: one of [blue, green, yellow]
  → IMPOSSIBLE: [red]

Example 5 - CRITICAL: Same feedback with different guess:
Secret: ["white", "black", "black", "green"]
Round 2: ["white", "blue", "green", "yellow"] → 2 pegs, 1 position
  → White locked at pos 0, one of [blue/green/yellow] misplaced
Round 3: ["white", "red", "green", "yellow"] → 2 pegs, 1 position
  → IMPORTANT: Feedback didn't change!
  → Position 0 stays white (locked)
  → Position 1 changed: blue→red
  → Position 2 stayed green
  → Position 3 stayed yellow
  → Since feedback didn't change, red and blue have SAME result
  → Can't definitively say red exists - maybe blue was the 2nd color
  → LOCKED: [pos 0→white]
  → MISPLACED: unknown (one of [blue/green/yellow] OR [red/green/yellow])
  → IMPOSSIBLE: none (can't rule out any yet)
  → Need more guesses to disambiguate

YOUR TASK:
Carefully analyze feedback and extract definite constraints.

LAST GUESS: {last_guess}
FEEDBACK: {feedback['correct_pegs']} colors exist total, {feedback['correct_positions']} in exact right positions

PREVIOUS GUESSES (for comparison):
{history_text if history_text else "None yet"}

ANALYSIS STEPS:
1. Determine locked positions:
   - If this is round 1: Can't definitively lock anything (need position changes to identify locked)
   - If feedback improved AND a position changed: The new color at that position is likely locked
   - If feedback stayed same: Don't lock anything new
   - Count MUST equal correct_positions in feedback

2. Determine misplaced colors:
   - These are colors that definitely exist but are in wrong positions
   - Only colors you can be confident about (e.g., appeared in round 1, now appears in better feedback)
   - Count = correct_pegs - correct_positions

3. Determine impossible colors:
   - Colors in THIS guess that don't match any part of feedback
   - Only if they clearly contributed zero to the feedback count
   - Be conservative - if unclear, don't mark as impossible

4. Build constraints list:
   - One constraint per known fact
   - Format: "color locked at position X" or "color exists but not at position X"

5. Note uncertainty:
   - If feedback is ambiguous, mention in estimated_remaining

Respond ONLY with valid JSON:
{{
  "correct_positions": [
    {{"position": 0, "color": "red"}},
    {{"position": 3, "color": "yellow"}}
  ],
  "correct_colors_wrong_position": ["blue", "green"],
  "impossible_colors": ["white", "black"],
  "constraints": [
    "Red locked at position 0",
    "Yellow locked at position 3",
    "Blue exists but not at position 1",
    "Green exists but not at position 2"
  ],
  "estimated_remaining": "~10-20 possible codes"
}}"""

        # First, use simple heuristics to identify definite locked positions
        locked_from_logic = self._find_locked_positions_by_logic(
            last_guess, correct_positions, previous_guesses
        )

        try:
            response = self.call_llm(prompt)
            result = self.parse_json_response(response)
        except Exception as e:
            # LLM failed - use heuristic analysis
            result = self._generate_heuristic_analysis(
                last_guess, correct_pegs, correct_positions, previous_guesses
            )
            result["llm_failed"] = True
            result["error_reason"] = str(e)

        # If LLM found locked positions, use those; otherwise use logical analysis
        if not result.get("correct_positions") and locked_from_logic:
            result["correct_positions"] = locked_from_logic

        # Validate response
        if "error" in result:
            return {
                "correct_positions": [],
                "correct_colors_wrong_position": [],
                "constraints": [],
                "impossible_colors": [],
                "estimated_remaining": "unknown",
                "parse_error": result.get("error")
            }

        # CRITICAL VALIDATION: Locked positions count must match correct_positions feedback
        locked_count = len(result.get("correct_positions", []))
        expected_locked = feedback.get("correct_positions", 0)
        misplaced_count = len(result.get("correct_colors_wrong_position", []))
        expected_total = feedback.get("correct_pegs", 0)

        # Check for constraint extraction errors
        constraint_errors = []
        if locked_count > expected_locked:
            constraint_errors.append(f"Too many locked positions: {locked_count} > {expected_locked}")
        if locked_count + misplaced_count > expected_total:
            constraint_errors.append(f"Too many colors found: {locked_count + misplaced_count} > {expected_total}")

        if constraint_errors:
            # LLM constraint extraction was incorrect
            # Strategy: use position changes as guide for newly locked positions
            # A position can only be newly locked if it has a NEW color (not seen at that position before)

            candidate_locked = []
            if previous_guesses:
                last_guess_colors = set(last_guess)
                prev_guess_colors = set(previous_guesses[-1].get("guess", []) if previous_guesses else [])

                for pos in range(len(last_guess)):
                    color_at_pos = last_guess[pos]
                    # Check if this position has a new color
                    if previous_guesses:
                        color_at_pos_before = previous_guesses[-1].get("guess", [])[pos] if pos < len(previous_guesses[-1].get("guess", [])) else None
                        if color_at_pos != color_at_pos_before:
                            # This position changed - it's a candidate for being locked
                            candidate_locked.append((pos, color_at_pos))

            # If we found candidates, use them; otherwise trust LLM but limit to expected count
            if candidate_locked and expected_locked > 0:
                # Take the first expected_locked candidates
                result["correct_positions"] = [
                    {"position": pos, "color": color}
                    for pos, color in candidate_locked[:expected_locked]
                ]
                result["validation_corrected_by_position_change"] = True
            else:
                # Fallback: just truncate to match feedback
                result["correct_positions"] = result.get("correct_positions", [])[:expected_locked]
                result["validation_truncated"] = True

            # Recalculate misplaced to match total
            correct_misplaced = expected_total - expected_locked
            if correct_misplaced >= 0:
                result["correct_colors_wrong_position"] = result.get("correct_colors_wrong_position", [])[:correct_misplaced]

            # Clear/rebuild constraints since they might be wrong
            result["constraints"] = []
            for pos_dict in result.get("correct_positions", []):
                result["constraints"].append(f"{pos_dict['color']} locked at position {pos_dict['position']}")
            for color in result.get("correct_colors_wrong_position", []):
                result["constraints"].append(f"{color} exists but wrong position")

        return result

    def _generate_heuristic_analysis(
        self,
        last_guess: List[str],
        correct_pegs: int,
        correct_positions: int,
        previous_guesses: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate analysis using simple heuristics when LLM fails.

        Conservative approach:
        - Only report locked positions if they changed from previous guess
        - Count misplaced as: correct_pegs - correct_positions
        - Report impossible colors conservatively

        Args:
            last_guess: Current guess
            correct_pegs: Total colors that exist
            correct_positions: Colors in correct positions
            previous_guesses: Previous guesses for comparison

        Returns:
            Analysis dict
        """
        # Find locked by position change
        locked = self._find_locked_positions_by_logic(last_guess, correct_positions, previous_guesses)

        # Misplaced count = total - locked
        misplaced_count = correct_pegs - correct_positions
        misplaced = last_guess[:misplaced_count] if misplaced_count > 0 else []

        # Impossible: colors in THIS guess that shouldn't be here
        # (conservative - only mark if clear feedback says so)
        impossible = []
        if correct_pegs == 0:
            # All colors in this guess are impossible
            impossible = last_guess

        constraints = []
        for pos_dict in locked:
            constraints.append(f"{pos_dict['color']} locked at position {pos_dict['position']}")
        for color in misplaced:
            constraints.append(f"{color} exists but wrong position")

        return {
            "correct_positions": locked,
            "correct_colors_wrong_position": misplaced,
            "impossible_colors": impossible,
            "constraints": constraints,
            "estimated_remaining": f"~{max(1, 10 - len(locked))} possibilities",
            "is_heuristic": True
        }

    def _find_locked_positions_by_logic(
        self,
        last_guess: List[str],
        expected_locked: int,
        previous_guesses: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Find locked positions using simple, robust logic.

        A position is likely locked if:
        1. It has a NEW color (never appeared at that position before)
        2. Expected locked count > 0 (feedback says some positions are correct)

        Args:
            last_guess: Current guess
            expected_locked: Number of positions that should be locked (from feedback)
            previous_guesses: List of previous guesses

        Returns:
            List of [{"position": int, "color": str}, ...]
        """
        if not previous_guesses or expected_locked == 0:
            return []

        locked = []
        if previous_guesses:
            prev_guess = previous_guesses[-1].get("guess", [])
            for pos in range(len(last_guess)):
                color_now = last_guess[pos]
                color_before = prev_guess[pos] if pos < len(prev_guess) else None

                # If position changed to a new color, it's a candidate for being locked
                if color_now != color_before:
                    locked.append({"position": pos, "color": color_now})

                    # Stop when we've found enough
                    if len(locked) >= expected_locked:
                        return locked[:expected_locked]

        return locked

    def process(
        self,
        last_guess: List[str] = None,
        feedback: Dict[str, int] = None,
        previous_guesses: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Standard process interface.

        Args:
            last_guess: Latest guess made
            feedback: Feedback from game engine
            previous_guesses: All previous guesses for context

        Returns:
            Constraint analysis dictionary
        """
        if last_guess is None or feedback is None:
            return {
                "correct_positions": [],
                "correct_colors_wrong_position": [],
                "constraints": [],
                "impossible_colors": [],
                "estimated_remaining": "unknown"
            }

        if previous_guesses is None:
            previous_guesses = []

        return self.analyze_feedback(last_guess, feedback, previous_guesses)
