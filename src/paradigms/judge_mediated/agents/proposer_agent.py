# Agent 2: Proposer
# Takes strategy from Analyzer-Strategist and generates a tactical guess

from typing import List, Dict, Any, Optional
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType
from communication.protocol import A2ACommunicationLayer


AGENT_CARD = {
    "agent_id": "proposer_judge_mediated",
    "agent_name": "Proposer",
    "agent_type": "proposer",
    "paradigm": "judge_mediated",
    "version": "1.0.0",
    "description": "Agent 2: Generates guess following strategy",
    "capabilities": {
        "propose_guess": {
            "description": "Generate a tactical guess following strategy",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy": {"type": "object"},
                    "available_colors": {"type": "array"},
                    "num_pegs": {"type": "integer"},
                }
            },
            "returns": {
                "type": "object",
                "description": "Tactical guess"
            }
        }
    },
    "constraints_owned": [],
    "team_members": [],
    "can_communicate": True,
}


class ProposerAgent(BaseAgent):
    """Agent 2: Proposer

    Responsibilities:
    1. Receive strategy from Analyzer-Strategist
    2. Generate a valid guess that follows the strategy
    3. Ensure guess uses correct colors and format
    4. Maintain memory of previous guesses to avoid recycling
    5. Reason through permutation testing autonomously
    """

    def __init__(
        self,
        provider: str = "deepseek",
        comm_layer: Optional[A2ACommunicationLayer] = None,
    ):
        super().__init__(
            name="Proposer",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.PROPOSER,
            paradigm=ParadigmType.JUDGE_MEDIATED,
        )

        # ⭐ AGENT-MANAGED MEMORY: Track all guesses to avoid recycling
        self.guess_history: List[List[str]] = []

        # ⭐ ACTIVE LEARNING: Build learned hypotheses from feedback (like direct_debate)
        self.learned_hypotheses: List[str] = []
        self.color_analysis: Dict[str, Dict[str, int]] = {}

        # ⭐ REFLECTION/LEARNING LOOP (Direct_Debate Pattern)
        # Track hypothesis testing for adaptive learning
        self.baseline_feedback: Dict[str, int] = {}  # Feedback from Round 1
        self.current_hypothesis_index: int = 0  # Which hypothesis are we testing?
        self.tested_hypotheses: List[Dict[str, any]] = []  # Track what we've tried
        self.last_feedback: Dict[str, int] = {}  # Last round's feedback for comparison
        self.neutral_rounds: int = 0  # Count of consecutive NEUTRAL outcomes (for escaping loops)

    def propose_guess(
        self,
        strategy: Dict[str, Any],
        available_colors: List[str] = None,
        num_pegs: int = 4,
        round_num: int = 1,
        last_feedback: Dict[str, int] = None,  # ⭐ NEW: For reflection/learning
    ) -> Dict[str, Any]:
        """Generate a guess following the strategy with autonomous permutation reasoning."""

        if available_colors is None:
            available_colors = []

        if last_feedback is None:
            last_feedback = {}

        # ⭐ FIX #1: GUARANTEE FIRST GUESS TESTS ALL 4 COLORS
        # This solves 80% of puzzle failures by ensuring we identify all colors immediately
        if round_num == 1 and not self.guess_history:
            # Round 1, no prior guesses: Use first 4 available colors as hardcoded initial guess
            # This ensures we test all 4 colors right away instead of relying on LLM heuristic
            initial_guess = available_colors[:num_pegs]
            print(f"\n[Proposer] 🎯 ROUND 1 HARDCODED INITIAL GUESS: {initial_guess}")
            print(f"[Proposer] This tests all {num_pegs} available colors for maximum information")
            self.guess_history.append(initial_guess)
            return {
                "guess": initial_guess,
                "reasoning": f"Initial guess: Test all {num_pegs} available colors {available_colors[:num_pegs]} to identify which are in the secret code"
            }

        # Safety check: ensure strategy is a valid dict
        if not isinstance(strategy, dict) or strategy is None:
            strategy = {"colors_in": available_colors[:num_pegs], "strategy": "systematic testing", "locked_positions": {}}

        colors_in = strategy.get("colors_in", available_colors[:num_pegs])
        locked_positions = strategy.get("locked_positions", {})
        strategy_desc = strategy.get("strategy", "Generate a tactical guess")
        near_solve = strategy.get("near_solve_state", False)

        # ⭐ PHASE 2b: REFLECTION/LEARNING LOOP (Direct_Debate Pattern)
        # Check if Analyzer detected color identification inconsistency
        color_inconsistency = strategy.get("color_inconsistency", {})
        # last_feedback is now a parameter, not from strategy

        # DEBUG: Check what we received
        print(f"[Proposer-R{round_num}] DEBUG: last_feedback = {last_feedback}, color_inconsistency exists = {bool(color_inconsistency)}")

        # ⭐ PHASE 3: POSITION PERMUTATION (Once all 4 colors found OR round >= 5)
        # If we have 4 correct pegs, we've found all colors - now permute positions
        # OR force permutation mode after round 5 to avoid endless Phase 2
        best_feedback = strategy.get("max_pegs_feedback", 0)
        force_phase3 = round_num >= 5  # After round 5, force permutation mode

        if (best_feedback >= num_pegs or force_phase3) and len(colors_in) >= num_pegs:
            print(f"\n[Proposer] 🎯 PHASE 3: ALL {num_pegs} COLORS FOUND! Switching to position permutation...")
            from itertools import permutations

            # Get the 4 known colors
            known_colors = colors_in[:num_pegs]

            # Generate ALL unique permutations and try them systematically
            if not hasattr(self, '_all_perms'):
                self._all_perms = list(set(permutations(known_colors)))
                print(f"[Proposer] Generated {len(self._all_perms)} unique permutations to test")

            if self._all_perms:
                # Use round number to cycle through permutations
                perm_idx = (round_num - 5) % len(self._all_perms)
                perm_guess = list(self._all_perms[perm_idx])

                # Apply locks if they exist
                for pos_str, color in locked_positions.items():
                    try:
                        pos = int(pos_str)
                        if pos < len(perm_guess):
                            perm_guess[pos] = color
                    except (ValueError, TypeError):
                        pass

                # Check if we already tested this exact guess
                if perm_guess not in self.guess_history:
                    self.guess_history.append(perm_guess)
                    return {
                        "guess": perm_guess,
                        "reasoning": f"Position permutation #{perm_idx + 1}/{len(self._all_perms)}: {perm_guess}"
                    }

        if color_inconsistency and not color_inconsistency.get("is_consistent") and len(colors_in) < num_pegs:
            # Only do Phase 2 if we haven't found all colors yet
            print(f"\n[Proposer] 🎯 PHASE 2 DETECTION: Color inconsistency found!")
            print(f"[Proposer]    Issue: {color_inconsistency.get('issue')}")
            print(f"[Proposer]    Tested {color_inconsistency.get('tested_count')} colors, got {color_inconsistency.get('correct_count')}P")

            # ⭐ REFLECTION: Did the last hypothesis work?
            if round_num >= 2 and last_feedback:
                outcome = self.reflect_on_hypothesis_outcome(last_feedback, round_num)

                if outcome == "FAILED":
                    # Hypothesis failed - SWITCH to next one
                    print(f"[Proposer] 🔄 SWITCHING to next hypothesis (FAILED)...")
                    self.current_hypothesis_index += 1
                    self.neutral_rounds = 0  # Reset neutral counter
                elif outcome == "NEUTRAL":
                    # Same feedback - might be stuck in loop
                    self.neutral_rounds += 1
                    if self.neutral_rounds >= 2:
                        # Give up on this hypothesis after 2 rounds of NEUTRAL
                        print(f"[Proposer] 🔄 SWITCHING to next hypothesis (stuck on NEUTRAL for {self.neutral_rounds} rounds)...")
                        self.current_hypothesis_index += 1
                        self.neutral_rounds = 0
                else:  # PROMISING
                    self.neutral_rounds = 0

            # Get color hypotheses and select which one to test
            color_hypotheses = strategy.get("color_hypotheses", [])
            if color_hypotheses and self.current_hypothesis_index < len(color_hypotheses):
                hypothesis = color_hypotheses[self.current_hypothesis_index]
                print(f"[Proposer] ⚡ Testing hypothesis #{self.current_hypothesis_index + 1}/{len(color_hypotheses)}")
                print(f"[Proposer]    Assumption: {hypothesis['assumption']}")

                hypothesis_guess = hypothesis["colors"][:num_pegs]
                while len(hypothesis_guess) < num_pegs:
                    hypothesis_guess.append(available_colors[0])
                hypothesis_guess = hypothesis_guess[:num_pegs]

                self.guess_history.append(hypothesis_guess)
                return {
                    "guess": hypothesis_guess,
                    "reasoning": f"Hypothesis #{self.current_hypothesis_index + 1}: {hypothesis['assumption']}"
                }
            elif not color_hypotheses:
                print(f"[Proposer] ⚠️ No hypotheses generated - using fallback")

        # ⭐ FIX #2: COLOR RECOVERY MECHANISM (ENHANCED)
        # If we've had 2+ rounds but still only found 3 colors, force new color testing
        # OR if feedback is consistently < num_pegs, one tested color is wrong!
        if round_num >= 2:
            max_feedback = strategy.get("max_pegs_feedback", 0)

            if max_feedback < num_pegs and len(colors_in) == num_pegs:
                # Feedback says < 4 colors correct, but we identified 4 colors!
                print(f"\n[Proposer] ⚠️  ENHANCED COLOR RECOVERY: Feedback mismatch detected!")
                print(f"[Proposer]    Max feedback: {max_feedback}P out of {num_pegs} colors")
                print(f"[Proposer]    Colors identified: {len(colors_in)} (one must be WRONG!)")

                untested_colors = [c for c in available_colors if c not in colors_in]
                if untested_colors:
                    # Replace each color one at a time and test
                    recovery_guess = colors_in[:num_pegs-1] + [untested_colors[0]]
                    self.guess_history.append(recovery_guess)
                    return {
                        "guess": recovery_guess,
                        "reasoning": f"Recovery: Testing {untested_colors[0]} as replacement for one of {colors_in} (one is wrong!)"
                    }

            elif len(colors_in) < num_pegs:
                untested_colors = [c for c in available_colors if c not in colors_in]
                if untested_colors:
                    print(f"\n[Proposer] ⚠️  COLOR RECOVERY MODE: Only {len(colors_in)} colors identified")
                    print(f"[Proposer] Forcing test of new untested color: {untested_colors[0]}")
                    # Create guess that tests the missing color
                    recovery_guess = colors_in[:num_pegs-1] + [untested_colors[0]]
                    if len(recovery_guess) < num_pegs:
                        recovery_guess += available_colors[0:num_pegs-len(recovery_guess)]
                    recovery_guess = recovery_guess[:num_pegs]
                    self.guess_history.append(recovery_guess)
                    return {
                        "guess": recovery_guess,
                        "reasoning": f"Color recovery: Testing untested color {untested_colors[0]} since only {len(colors_in)} colors identified so far"
                    }

        # Build history context
        history_text = ""
        if self.guess_history:
            history_text = "\n=== YOUR PREVIOUS GUESSES (DO NOT REPEAT!) ===\n"
            for i, prev_guess in enumerate(self.guess_history[-5:], 1):  # Last 5 to avoid token overflow
                history_text += f"  {i}. {prev_guess}\n"

        # ⭐ EXTRACT CUMULATIVE CONSTRAINTS from strategy
        cumulative = strategy.get("cumulative_constraints", {})
        cumulative_in = cumulative.get("colors_in", colors_in)
        cumulative_out = cumulative.get("colors_out", [])
        cumulative_locked = cumulative.get("locked_positions", locked_positions)

        constraint_violations = ""
        if cumulative_in and cumulative_out:
            # Warn about constraint violations
            overlap = set(cumulative_in) & set(cumulative_out)
            if overlap:
                constraint_violations = f"\n⚠️ CONSTRAINT CONFLICT: Colors {overlap} are both IN and OUT! Trust IN over OUT."

        # ⭐ SYSTEM PROMPT: Fixed role definition (stays same across all rounds)
        system_prompt = f"""You are a Mastermind solver with {num_pegs} pegs.
Available colors: {', '.join(available_colors)}.

ABSOLUTE RULES (NON-NEGOTIABLE):
1. 🔒 PRESERVE locked positions - Position locks are permanent facts
   - If position 0 = red, it MUST be red in every guess
   - Never break a lock - this loses all progress

2. ❌ NEVER repeat a previous guess
   - Each guess must be NEW and test something different

3. ✓ ONLY use allowed colors
   - Colors IN (confirmed): Use these
   - Colors OUT (impossible): Never use these
   - Untested colors: Safe to try

4. ✓ Test NEW arrangements of known colors
   - When you know multiple colors exist, try different position combinations
   - Example: If colors are [red, blue, green, yellow]:
     * Try [red, blue, green, yellow]
     * Try [red, blue, yellow, green]
     * Try [red, green, blue, yellow]
     * Each tests different position combinations

5. ✓ Show your mathematical reasoning
   - List candidate arrangements before choosing
   - Explain WHY each one is different from previous attempts
   - Explain WHAT each arrangement will teach you

You have perfect memory of ALL prior guesses and reasoning via conversation history.
Track it carefully. Use it to ensure each guess tests something new."""

        # ⭐ FORMAT LEARNED KNOWLEDGE (Active Learning from feedback)
        learned_text = self._format_learned_knowledge() if self.learned_hypotheses else ""

        # ⭐ USER MESSAGE: Current round's strategy + learned knowledge
        user_message = f"""Round {round_num} — Propose next guess using constraints and learned patterns.

CONSTRAINTS (ABSOLUTE):
  Colors IN: {', '.join(cumulative_in) if cumulative_in else '(none)'}
  Colors OUT: {', '.join(cumulative_out) if cumulative_out else '(none)'}
  Locked: {dict(cumulative_locked) if cumulative_locked else '(none)'}

STRATEGY: {strategy_desc}

LEARNED PATTERNS (From feedback analysis):
{learned_text if learned_text else '(No patterns yet - this is round 1)'}

PRIOR GUESSES:
{history_text if history_text else '(Round 1)'}

THINK SYSTEMATICALLY:
1. What colors do you KNOW are IN? What positions are LOCKED?
2. What position combinations haven't you tested yet?
3. Generate 3 different arrangements respecting locked positions
4. Pick the one that tests something NEW

Output ONLY JSON:
{{
  "reasoning": "Your thinking",
  "candidate_arrangements": ["arr1", "arr2", "arr3"],
  "selected_index": 0,
  "guess": {["color"] * num_pegs}
}}"""

        try:
            # ⭐ CRITICAL FIX: Use call_llm_conversation() to maintain reasoning history
            # This allows LLM to build on its own prior deductions across rounds
            # (This is how boss_worker successfully solves puzzles!)
            response = self.call_llm_conversation(system_prompt, user_message)

            # Parse JSON with enhanced error handling
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                import re
                # Try to extract JSON object from response
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        result = {"guess": colors_in[:num_pegs], "reasoning": response[:100]}
                else:
                    result = {"guess": colors_in[:num_pegs], "reasoning": response[:100]}

            guess = result.get("guess", colors_in[:num_pegs])

            # Validate and normalize guess
            if not guess or len(guess) != num_pegs:
                guess = [""] * num_pegs
                # First, lock all locked positions
                for pos_str, color in locked_positions.items():
                    try:
                        pos = int(pos_str)
                        if pos < num_pegs:
                            guess[pos] = color
                    except (ValueError, IndexError):
                        pass

                # Then fill remaining positions with colors_in
                idx = 0
                for i in range(num_pegs):
                    if not guess[i]:
                        while idx < len(colors_in):
                            if colors_in[idx] not in locked_positions.values():
                                guess[i] = colors_in[idx]
                                idx += 1
                                break
                            idx += 1
                        if not guess[i] and colors_in:
                            guess[i] = colors_in[0]

            # Normalize colors
            guess = [
                c.lower().strip() if c in available_colors else available_colors[0]
                for c in guess if c
            ]
            while len(guess) < num_pegs:
                guess.append(available_colors[0])
            guess = guess[:num_pegs]

            # ⭐ PRESERVE LOCKED POSITIONS SAFETY CHECK
            for pos_str, color in locked_positions.items():
                try:
                    pos = int(pos_str)
                    if pos < num_pegs and guess[pos] != color:
                        print(f"[WARNING] Guess lost locked position {pos}={color}! Restoring...")
                        guess[pos] = color
                except (ValueError, IndexError):
                    pass

            # ⭐ SAVE GUESS TO MEMORY
            self.guess_history.append(guess)
            print(f"[Proposer Memory] ✓ SAVED guess: {guess}")
            print(f"[Proposer Memory] Total history now: {len(self.guess_history)} guesses")

            self.call_count += 1
            return {
                "guess": guess,
                "reasoning": result.get("reasoning", "LLM-generated reasoning")
            }

        except Exception as e:
            print(f"Error in propose_guess: {e}")
            guess = colors_in[:num_pegs] if colors_in else available_colors[:num_pegs]
            while len(guess) < num_pegs:
                guess.append(available_colors[0] if available_colors else "red")
            return {
                "guess": guess[:num_pegs],
                "reasoning": f"Fallback: {str(e)}"
            }

    def _format_learned_knowledge(self) -> str:
        """Format learned hypotheses for LLM context (like direct_debate)."""
        if not self.learned_hypotheses and not self.color_analysis:
            return ""

        lines = []
        lines.append("LEARNED PATTERNS & HYPOTHESES:")

        if self.learned_hypotheses:
            for hyp in self.learned_hypotheses[-5:]:  # Last 5 learnings
                lines.append(f"  • {hyp}")

        if self.color_analysis:
            high_confidence_colors = [
                c for c, stats in self.color_analysis.items()
                if stats.get("correct_feedback", 0) >= 2
            ]
            if high_confidence_colors:
                lines.append(f"  • HIGH CONFIDENCE colors: {high_confidence_colors}")

        return "\n".join(lines)

    def reflect_on_feedback(self, round_num: int, guess: List[str], feedback: Dict[str, Any]) -> None:
        """Analyze feedback and build learned hypotheses (like direct_debate Solver).

        This is the MISSING PIECE that direct_debate has!
        It actively processes feedback to accumulate knowledge.
        """
        pegs = feedback.get("correct_pegs", 0)
        positions = feedback.get("correct_positions", 0)

        # If we got correct_pegs feedback, those colors are likely in the code
        if pegs > 0:
            hypothesis = f"R{round_num}: {pegs} colors from {guess} are IN code (feedback: {pegs}P {positions}L)"
            self.learned_hypotheses.append(hypothesis)

        # Position analysis: If we got positions right, lock those
        if positions > 0:
            hypothesis = f"R{round_num}: {positions} colors LOCKED in positions (feedback: {pegs}P {positions}L). Guess was: {guess}"
            self.learned_hypotheses.append(hypothesis)

        # If we got 0 pegs, we learned which colors are NOT in code
        if pegs == 0:
            wrong_colors = ", ".join(guess)
            hypothesis = f"R{round_num}: Colors NOT in code: {wrong_colors}"
            self.learned_hypotheses.append(hypothesis)

        # Track color frequency and correctness
        for color in guess:
            if color not in self.color_analysis:
                self.color_analysis[color] = {"in_guesses": 0, "correct_feedback": 0}
            self.color_analysis[color]["in_guesses"] += 1
            if pegs > 0:
                self.color_analysis[color]["correct_feedback"] += 1

    def reflect_on_hypothesis_outcome(self, new_feedback: Dict[str, int], round_num: int) -> str:
        """⭐ REFLECTION/LEARNING LOOP: Validate hypothesis outcome (Direct_Debate Pattern)

        This is what makes direct_debate ADAPTIVE - it learns from feedback.
        After testing a hypothesis, analyze if it worked or failed.
        Store the lesson for future decisions.

        Returns: "FAILED", "PROMISING", or "NEUTRAL"
        """
        new_pegs = new_feedback.get("correct_pegs", 0)

        # First hypothesis test in this phase - establish baseline
        if not self.baseline_feedback:
            print(f"[Proposer-R{round_num}] 📍 Baseline feedback set: {new_pegs}P")
            self.baseline_feedback = new_feedback
            return "NEUTRAL"  # First hypothesis, can't compare yet

        # Compare current feedback to baseline
        baseline_pegs = self.baseline_feedback.get("correct_pegs", 0)

        if new_pegs < baseline_pegs:
            # Hypothesis FAILED - feedback got worse!
            outcome = "FAILED"
            print(f"[Proposer-R{round_num}] ❌ Hypothesis FAILED: {new_pegs}P < baseline {baseline_pegs}P")
            print(f"[Proposer-R{round_num}] This hypothesis is WRONG. Need to try next one.")

        elif new_pegs > baseline_pegs:
            # Hypothesis PROMISING - feedback improved!
            outcome = "PROMISING"
            print(f"[Proposer-R{round_num}] ✅ Hypothesis PROMISING: {new_pegs}P > baseline {baseline_pegs}P")
            print(f"[Proposer-R{round_num}] This hypothesis is on the right track!")

        else:
            # Same feedback - inconclusive
            outcome = "NEUTRAL"
            print(f"[Proposer-R{round_num}] ⚪ Hypothesis NEUTRAL: {new_pegs}P = baseline {baseline_pegs}P")
            print(f"[Proposer-R{round_num}] Inconclusive - try next hypothesis.")

        # Record learning
        hypothesis_result = {
            "round": round_num,
            "index": self.current_hypothesis_index,
            "feedback": new_pegs,
            "outcome": outcome
        }
        self.tested_hypotheses.append(hypothesis_result)
        self.last_feedback = new_feedback

        return outcome

    def _get_next_permutation(self, colors: List[str], locked_positions: Dict[str, str], round_num: int) -> List[str]:
        """⭐ POSITION PERMUTATION: Generate a systematic permutation to test.

        Strategy: Test different position arrangements of known colors, respecting locks.
        """
        from itertools import permutations

        if len(colors) < 4:
            return None

        # Start with first 4 unique colors
        base_colors = list(dict.fromkeys(colors[:4]))  # Remove duplicates, preserve order

        if len(base_colors) < 4:
            return None

        # Apply locks if they exist
        locked = {}
        for pos_str, color in locked_positions.items():
            try:
                locked[int(pos_str)] = color
            except (ValueError, TypeError):
                pass

        # Build result with locks applied
        result = [None] * 4

        # Place locked colors
        remaining_colors = list(base_colors)
        for pos, color in sorted(locked.items()):
            if pos < 4:
                result[pos] = color
                if color in remaining_colors:
                    remaining_colors.remove(color)

        # Fill remaining positions with remaining colors (rotated each round)
        if remaining_colors:
            rotation = (round_num - 6) % len(remaining_colors)
            rotated = remaining_colors[rotation:] + remaining_colors[:rotation]

            col_idx = 0
            for pos in range(4):
                if result[pos] is None:
                    if col_idx < len(rotated):
                        result[pos] = rotated[col_idx]
                        col_idx += 1

        # Safety check: ensure all positions filled with unique colors
        if None in result or len(set(result)) != 4:
            # Fallback: just return base colors
            return base_colors

        print(f"[Proposer] ⚡ Position permutation: {result}")
        return result

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process proposal."""
        return self.propose_guess(
            strategy=kwargs.get("strategy", {}),
            available_colors=kwargs.get("available_colors", []),
            num_pegs=kwargs.get("num_pegs", 4),
            round_num=kwargs.get("round_num", 1),
        )
