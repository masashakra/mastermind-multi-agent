# Proposer Agent
# Generates specific next guess from strategy and constraints
# Translates abstract strategy into concrete peg colors
# Input: strategy + constraints + available colors. Output: proposed guess JSON

from typing import List, Dict, Any
import random
from .base_agent import BaseAgent


class ProposerAgent(BaseAgent):
    """Generates concrete guess from strategy and constraints.

    Role: Execution - translates strategy into specific action

    Input: Strategy description + constraint analysis + available colors
    Output: JSON with proposed guess and justification
    """

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
        """Propose next guess based on strategy and constraints.

        Args:
            strategy: Strategy from Strategist (e.g., "test positions 2-3 with new colors")
            constraints_text: Constraints from Analyzer (as string or JSON)
            available_colors: List of valid color choices
            num_pegs: Number of pegs needed (4, 5, or 6)
            previous_guesses: List of all previous guesses (to avoid duplicates)

        Returns:
            {
                "proposed_guess": ["color1", "color2", ...],
                "justification": str,
                "expected_outcome": str
            }
        """
        prompt = f"""You are the Proposer for a Mastermind puzzle solver.

CONSTRAINT RULES (ABSOLUTE - NEVER VIOLATE):
1. LOCKED POSITIONS ARE IMMUTABLE: If position X is locked with color C, ALL future guesses MUST have C at position X
   - Example: If "red locked at position 0", then EVERY guess must start with ["red", ...]
   - This is confirmed correct - you would be throwing away certain knowledge
2. Never re-test a color from IMPOSSIBLE list (e.g., if white is impossible, never use white)
3. For MISPLACED colors: test them in different positions (not where they failed before)
4. For UNKNOWN positions: test new colors from available list
5. Avoid redundancy: Don't test a guess you already tested (game engine will reject it)

GUESS QUALITY CRITERIA (how to pick the best candidate):
1. RESPECTS ALL CONSTRAINTS: No locked position violations, no impossible colors
2. TESTS NEW INFORMATION: Has colors/positions not tested before (maximizes entropy)
3. EFFICIENT: Moves toward solving (tests likely solutions or eliminates possibilities)
4. STRATEGIC: Aligns with the overall strategy (if exploring, use diverse colors; if localizing, test positions)

WORKED EXAMPLES:

Example 1 - First round (no constraints yet):
Available: {available_colors}
Need: {num_pegs} pegs
Constraints: None
Strategy: "Test diverse colors to find which exist"
→ Candidate 1: ["red", "blue", "green", "yellow"]
   Why: Tests 4 common colors, diverse
→ Candidate 2: ["red", "white", "black", "yellow"]
   Why: Tests different set, still diverse
→ Candidate 3: ["blue", "green", "white", "black"]
   Why: Alternative combination
BEST: Candidate 1 (most useful feedback)

Example 2 - With one locked position:
Constraints:
- LOCKED: position 0 → red
- MISPLACED: blue (exists, wrong position)
- IMPOSSIBLE: yellow, white
- UNKNOWN: positions 1-3
Strategy: "Lock red, test blue in new position, add new colors"
→ Candidate 1: ["red", "blue", "green", "black"]
   Why: Red locked, blue at pos 1, tests green+black
→ Candidate 2: ["red", "green", "black", "blue"]
   Why: Red locked, blue at pos 3 (new position), tests green+black
→ Candidate 3: ["red", "blue", "purple", "orange"]
   Why: Red locked, blue at pos 1, but purple/orange might be impossible
BEST: Candidate 2 (tests blue in unexplored position)

Example 3 - Mostly locked, just 1-2 unknown:
Constraints:
- LOCKED: [0→red, 1→blue, 2→green]
- MISPLACED: yellow (exists but not position 3)
- IMPOSSIBLE: white, black
- UNKNOWN: position 3 (not yellow, not locked colors)
Strategy: "Find position 3 color"
→ Candidate 1: ["red", "blue", "green", "yellow"]
   Why: Yellow at pos 3? But maybe it's misplaced everywhere?
→ Candidate 2: ["red", "blue", "green", "purple"]
   Why: Purple is new, tests position 3
→ Candidate 3: ["red", "blue", "green", "orange"]
   Why: Orange is new, tests position 3
BEST: Candidate 2 or 3 (both test new color at position 3)

Example 4 - Multiple misplaced colors:
Constraints:
- LOCKED: [0→red]
- MISPLACED: [blue, green, yellow] (all exist, wrong positions)
- IMPOSSIBLE: white, black
- UNKNOWN: position 3
Strategy: "Rearrange to find where blue/green/yellow go"
→ Candidate 1: ["red", "blue", "green", "yellow"]
   Why: Tests blue at 1, green at 2, yellow at 3
→ Candidate 2: ["red", "blue", "yellow", "green"]
   Why: Tests blue at 1, yellow at 2, green at 3
→ Candidate 3: ["red", "green", "blue", "yellow"]
   Why: Tests green at 1, blue at 2, yellow at 3
BEST: Candidate 1 (most logical based on positions tested before)

Example 5 - High confidence guess:
Constraints:
- LOCKED: [0→red, 2→green]
- MISPLACED: blue (at 1? 2? 3?)
- MISPLACED: yellow (at 0? 1? 2? 3?)
- UNKNOWN: Need to eliminate 2 positions
Strategy: "If blue at 1 and yellow at 3 both work, this is it"
→ Candidate 1: ["red", "blue", "green", "yellow"]
   Why: All constraints satisfied
→ Candidate 2: ["red", "yellow", "green", "blue"]
   Why: Tests different positions for blue/yellow
→ Candidate 3: ["red", "blue", "green", "white"]
   Why: Tests if white could be position 3 instead
BEST: Candidate 1 (most constraints satisfied, highest confidence)

TASK:

Available colors: {available_colors}
Pegs needed: {num_pegs}
Strategy: {strategy}
Constraints:
{constraints_text}

PROCESS:
1. Generate 3 candidate guesses that respect all constraints
2. For each candidate:
   a. Verify all constraints are met (locked positions, no impossible colors)
   b. Score information value: Does it test new colors? New positions? Strategic?
   c. Score feasibility: Could this be part of the solution?
3. Select the best candidate:
   - BEST = highest constraint satisfaction + highest information value
   - Information value = tests something not yet tested, OR tests likely solution
   - Feasibility = guess respects all constraints we've learned

EVALUATION CRITERIA (prioritized):
1. Constraint satisfaction (must be 100% - no violations allowed)
2. Information gain (tests new colors/positions vs. redundancy)
3. Strategic alignment (follows the proposed strategy)
4. Solution likelihood (based on feedback patterns so far)

Output JSON with:
- proposed_guess: the best candidate
- candidates: all 3 candidates with evaluation
- selected_candidate: which one (1, 2, or 3)
- justification: specific reasons this is best (constraint compliance, information gain, strategy fit)
- expected_outcome: what we'll learn and how it moves us toward solution

Respond ONLY with valid JSON (no markdown):
{{
  "proposed_guess": ["red", "blue", "green", "yellow"],
  "candidates": [
    {{"candidate": 1, "guess": ["red", "blue", "green", "yellow"], "reasoning": "..."}},
    {{"candidate": 2, "guess": ["red", "white", "green", "black"], "reasoning": "..."}},
    {{"candidate": 3, "guess": ["red", "purple", "green", "blue"], "reasoning": "..."}}
  ],
  "selected_candidate": 1,
  "justification": "Candidate 1 tests...",
  "expected_outcome": "We'll learn whether..."
}}"""

        try:
            response = self.call_llm(prompt)
            result = self.parse_json_response(response)
        except Exception as e:
            # LLM failed - use heuristic fallback
            result = self._generate_heuristic_guess(
                strategy, constraints_text, available_colors, num_pegs, previous_guesses
            )
            result["llm_failed"] = True
            result["error_reason"] = str(e)

        # Extract locked positions from constraints for validation
        locked_positions = {}
        if constraints_text:
            for line in constraints_text.split("\n"):
                if "locked at position" in line.lower():
                    # Parse "color locked at position X"
                    parts = line.split("locked at position")
                    if len(parts) == 2:
                        color = parts[0].strip().lower()
                        try:
                            pos = int(parts[1].strip())
                            locked_positions[pos] = color
                        except (ValueError, IndexError):
                            pass

        # Validate response
        if "error" in result:
            # Fallback: random guess
            fallback_guess = random.sample(available_colors, min(num_pegs, len(available_colors)))
            if len(fallback_guess) < num_pegs:
                fallback_guess.extend([random.choice(available_colors) for _ in range(num_pegs - len(fallback_guess))])
            return {
                "proposed_guess": fallback_guess,
                "justification": "Fallback random guess (LLM response unparseable)",
                "expected_outcome": "Gather feedback",
                "parse_error": result.get("error")
            }

        # Validate proposed guess
        guess = result.get("proposed_guess", [])
        if len(guess) != num_pegs:
            # Fix length
            if len(guess) > num_pegs:
                guess = guess[:num_pegs]
            else:
                guess.extend([random.choice(available_colors) for _ in range(num_pegs - len(guess))])
            result["proposed_guess"] = guess
            result["length_corrected"] = True

        # Validate colors
        invalid_colors = [c for c in guess if c not in available_colors]
        if invalid_colors:
            # Replace with random valid colors
            fixed_guess = [random.choice(available_colors) if c in invalid_colors else c for c in guess]
            result["proposed_guess"] = fixed_guess
            result["invalid_colors_fixed"] = invalid_colors

        # CRITICAL VALIDATION: Check locked position constraints
        locked_violations = []
        if locked_positions:
            for pos, required_color in locked_positions.items():
                if pos < len(guess):
                    if guess[pos].lower() != required_color.lower():
                        locked_violations.append(f"Position {pos} must be {required_color}, not {guess[pos]}")
                        # Fix it
                        guess[pos] = required_color

        if locked_violations:
            result["proposed_guess"] = guess
            result["locked_violations_fixed"] = locked_violations
            result["constraint_violation_fix_applied"] = True

        # SANITY CHECK: Never suggest the same guess twice in a row
        if previous_guesses and len(previous_guesses) > 0:
            last_guess_list = previous_guesses[-1]
            if guess == last_guess_list:
                # Generate a different guess by varying one position
                for attempt in range(10):
                    # Try changing each position
                    for pos in range(len(guess)):
                        # Skip if position is locked
                        if pos not in locked_positions:
                            # Try a different color at this position
                            available_for_pos = [c for c in available_colors if c != guess[pos]]
                            if available_for_pos:
                                new_guess = guess[:]
                                new_guess[pos] = random.choice(available_for_pos)
                                if new_guess != last_guess_list:
                                    guess = new_guess
                                    result["proposed_guess"] = guess
                                    result["duplicate_guess_fixed"] = True
                                    result["fix_reason"] = f"Avoided duplicate of round {len(previous_guesses)}"
                                    return result
                # If we couldn't generate a different guess, return as-is with warning
                result["proposed_guess"] = guess
                result["duplicate_guess_warning"] = "Could not generate different guess"

        return result

    def _generate_heuristic_guess(
        self,
        strategy: str,
        constraints_text: str,
        available_colors: List[str],
        num_pegs: int,
        previous_guesses: List[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate guess using simple heuristics when LLM fails.

        Strategy:
        1. Identify locked positions from constraints
        2. For unknown positions: use colors not yet tested (if exploring) or test new combinations
        3. Ensure no constraint violations

        Args:
            strategy: Strategy description (for context)
            constraints_text: Constraints as text
            available_colors: Valid colors
            num_pegs: Number of pegs
            previous_guesses: Previous guesses

        Returns:
            Guess proposal dict
        """
        # Extract locked positions
        locked_positions = {}
        if constraints_text:
            for line in constraints_text.split("\n"):
                if "locked at position" in line.lower():
                    parts = line.split("locked at position")
                    if len(parts) == 2:
                        color = parts[0].strip().lower()
                        try:
                            pos = int(parts[1].strip())
                            locked_positions[pos] = color
                        except (ValueError, IndexError):
                            pass

        # Build guess
        guess = [None] * num_pegs

        # Fill locked positions
        for pos, color in locked_positions.items():
            if pos < num_pegs:
                guess[pos] = color

        # Fill remaining positions
        tested_colors = set()
        if previous_guesses:
            for prev_guess in previous_guesses:
                tested_colors.update(prev_guess)

        available_new = [c for c in available_colors if c not in tested_colors]

        for pos in range(num_pegs):
            if guess[pos] is None:
                # Try new colors first, then fall back to any color
                if available_new:
                    guess[pos] = available_new.pop(0)
                else:
                    guess[pos] = random.choice(available_colors)

        return {
            "proposed_guess": guess,
            "justification": "Heuristic fallback: locked positions from constraints, new colors for unknowns",
            "expected_outcome": "Test unknown positions",
            "is_heuristic": True
        }

    def process(
        self,
        strategy: str = "",
        constraints_text: str = "",
        available_colors: List[str] = None,
        num_pegs: int = 4
    ) -> Dict[str, Any]:
        """Standard process interface.

        Args:
            strategy: Strategy from Strategist
            constraints_text: Constraints from Analyzer
            available_colors: List of valid colors
            num_pegs: Number of pegs

        Returns:
            Proposed guess dictionary
        """
        if available_colors is None:
            available_colors = ["red", "blue", "green", "yellow", "white", "black"]

        return self.propose_guess(strategy, constraints_text, available_colors, num_pegs)
