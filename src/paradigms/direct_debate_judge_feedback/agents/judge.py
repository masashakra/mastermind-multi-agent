# Judge Agent for Direct Debate with Judge Feedback
# Evaluates two proposals and selects the stronger one

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType


class JudgeAgent(BaseAgent):
    """Judge that evaluates two guesses and selects the better one.

    Role: Analyze both team proposals and select the strategically superior guess
    based on reasoning quality, constraint alignment, and information gain potential.
    """

    def __init__(self, provider: str = "deepseek"):
        try:
            super().__init__(
                name="Judge",
                provider=provider,
                role=AgentRole.VALIDATOR,
                paradigm=ParadigmType.JUDGE_MEDIATED,
            )
            self.llm_available = True
        except (ValueError, Exception) as e:
            print(f"[Judge] LLM unavailable ({str(e)[:50]}...), using heuristic mode")
            self.name = "Judge"
            self.agent_id = "judge"
            self.provider = provider
            self.llm = None
            self.call_count = 0
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self.llm_available = False

    def evaluate_and_select(
        self,
        proposal_a: Dict[str, Any],
        proposal_b: Dict[str, Any],
        shared_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate both proposals and return the better one.

        Args:
            proposal_a: {"team": "team_1", "guess": [...], "reasoning": str, "confidence": 0-100}
            proposal_b: {"team": "team_2", "guess": [...], "reasoning": str, "confidence": 0-100}
            shared_history: List of previous guesses and feedback

        Returns:
            {"selected_team": "team_1" or "team_2", "winning_guess": [...],
             "reasoning": str, "confidence": 0-100}
        """

        print(f"\n[Judge] Evaluating proposals...")
        print(f"  Team A ({proposal_a.get('team')}): {proposal_a.get('guess')}")
        print(f"  Team B ({proposal_b.get('team')}): {proposal_b.get('guess')}")

        # If LLM available, use multi-turn analysis
        if self.llm_available:
            return self._evaluate_with_llm(proposal_a, proposal_b, shared_history)
        else:
            return self._evaluate_heuristic(proposal_a, proposal_b, shared_history)

    def _evaluate_with_llm(
        self,
        proposal_a: Dict[str, Any],
        proposal_b: Dict[str, Any],
        shared_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Use LLM to evaluate proposals with multi-turn reasoning.

        Enhanced with constraint detection and diversity scoring.
        """

        print(f"\n[Judge] Turn 1: Objective evaluation of both proposals")

        # Extract constraints from history (inspired by boss_worker)
        constraints = self._extract_constraints(shared_history)
        diversity_score_a = self._diversity_score(proposal_a.get('guess', []), shared_history)
        diversity_score_b = self._diversity_score(proposal_b.get('guess', []), shared_history)

        system_prompt_1 = """You are a Judge evaluating two Mastermind guesses.
Analyze both objectively WITHOUT picking sides. Use CONSTRAINT-BASED reasoning.

CRITICAL FACTORS (in priority order):
1. Constraint satisfaction (respects ALL confirmed constraints)
2. Pattern detection (tests for duplicates, locked positions, eliminated colors)
3. Information gain (maximizes new information from feedback)
4. Logical consistency (reasoning soundness)

⚠️ SPECIAL CASE - "VERY CLOSE" (correct_pegs ≥ 3 with high correct_positions):
When a guess achieved 3+ pegs and 3+ positions in recent rounds:
- You are VERY CLOSE to the solution
- PRIORITY: Find the missing 1-2 colors, don't waste rounds on untested colors
- BEST STRATEGY: Test colors that appeared earlier with positive feedback
- AVOID: Testing completely new/untested colors - these are RISKY when so close
- EXAMPLE: If ['yellow','blue','green','black']→3p 3pos, better to test 'red' (appeared in R1 with positive feedback) than 'white' (never tested)

Scoring MUST account for:
- Which colors are confirmed vs eliminated
- Which positions are locked vs flexible
- Whether guess tests new color combinations wisely
- CRITICAL: In "very close" scenarios, penalize risky new color introductions
- Risk of repeating partial information

Format response as JSON:
{
  "team_a_strategy_quality": 0-100,
  "team_b_strategy_quality": 0-100,
  "team_a_constraint_violations": ["violation1"] or [],
  "team_b_constraint_violations": ["violation1"] or [],
  "team_a_pattern_strength": 0-100,
  "team_b_pattern_strength": 0-100,
  "team_a_strengths": ["strength1", "strength2"],
  "team_b_strengths": ["strength1", "strength2"],
  "team_a_weaknesses": ["weakness1"],
  "team_b_weaknesses": ["weakness1"],
  "initial_lean": "A|B|equal"
}"""

        history_text = self._format_history(shared_history)
        constraints_text = self._format_constraints(constraints)

        user_message_1 = f"""Evaluate both proposals using CONSTRAINT-BASED analysis:

EXTRACTED CONSTRAINTS:
{constraints_text}

HISTORY (showing pattern):
{history_text}

TEAM A:
Guess: {proposal_a.get('guess')}
Confidence: {proposal_a.get('confidence', 50)}%
Diversity Score: {diversity_score_a}/100
Reasoning: {proposal_a.get('reasoning', 'Unknown')}

TEAM B:
Guess: {proposal_b.get('guess')}
Confidence: {proposal_b.get('confidence', 50)}%
Diversity Score: {diversity_score_b}/100
Reasoning: {proposal_b.get('reasoning', 'Unknown')}

KEY QUESTION: Which guess better exploits our current knowledge and maximizes information gain?"""

        try:
            response_1 = self.call_llm_conversation(system_prompt_1, user_message_1)
            eval_1 = self.parse_json_response(response_1)
            print(f"[Judge] Team A quality: {eval_1.get('team_a_strategy_quality', 50)}/100")
            print(f"[Judge] Team B quality: {eval_1.get('team_b_strategy_quality', 50)}/100")
        except Exception as e:
            print(f"[Judge] Error in Turn 1: {e}")
            eval_1 = {"team_a_strategy_quality": 50, "team_b_strategy_quality": 50}

        # TURN 2: Compare with confidence weighting
        print(f"\n[Judge] Turn 2: Weighted comparison")

        system_prompt_2 = """You are deciding between two proposals.
Consider both strategy quality AND confidence.

The team with higher confidence believes more strongly in their guess.
The team with better strategy has more sound reasoning.

ReConcile approach:
- Weight = (confidence * 0.4) + (strategy_quality * 0.6)
- Higher weight = stronger overall proposal

Format response as JSON:
{
  "team_a_weighted_score": 0-100,
  "team_b_weighted_score": 0-100,
  "deciding_factor": "confidence|strategy|equal",
  "preliminary_choice": "A|B"
}"""

        user_message_2 = f"""Compare weighted scores:

Team A:
- Confidence: {proposal_a.get('confidence', 50)}%
- Strategy Quality: {eval_1.get('team_a_strategy_quality', 50)}/100

Team B:
- Confidence: {proposal_b.get('confidence', 50)}%
- Strategy Quality: {eval_1.get('team_b_strategy_quality', 50)}/100

Which proposal is stronger overall?"""

        try:
            response_2 = self.call_llm_conversation(system_prompt_2, user_message_2)
            eval_2 = self.parse_json_response(response_2)
            print(f"[Judge] Preliminary choice: Team {eval_2.get('preliminary_choice', 'A')}")
        except Exception as e:
            print(f"[Judge] Error in Turn 2: {e}")
            eval_2 = {
                "preliminary_choice": "A" if proposal_a.get('confidence', 50) >= proposal_b.get('confidence', 50) else "B"
            }

        # TURN 3: Final decision with reasoning
        print(f"\n[Judge] Turn 3: Final decision")

        system_prompt_3 = """You are making the FINAL decision.
You've analyzed strategy quality, confidence, and compared them fairly.
Now commit to a choice with clear reasoning.

Ensure your decision is defensible and explains why this guess has the best chance of success.

Format response as JSON:
{
  "winning_team": "A|B",
  "winning_guess": ["color1", "color2", "color3", "color4"],
  "confidence_in_choice": 0-100,
  "final_reasoning": "clear explanation of why this team's guess is better"
}"""

        user_message_3 = f"""Make final decision:

Team A: {proposal_a.get('guess')} (confidence: {proposal_a.get('confidence', 50)}%, quality: {eval_1.get('team_a_strategy_quality', 50)}/100)
Team B: {proposal_b.get('guess')} (confidence: {proposal_b.get('confidence', 50)}%, quality: {eval_1.get('team_b_strategy_quality', 50)}/100)

Preliminary lean: {eval_2.get('preliminary_choice', 'A')}

What's your final choice and why does this guess give us the best shot?"""

        try:
            response_3 = self.call_llm_conversation(system_prompt_3, user_message_3)
            result = self.parse_json_response(response_3)

            if not result.get("winning_guess"):
                choice = eval_2.get('preliminary_choice', 'A')
                if choice == 'A':
                    result["winning_team"] = "A"
                    result["winning_guess"] = proposal_a.get("guess")
                else:
                    result["winning_team"] = "B"
                    result["winning_guess"] = proposal_b.get("guess")

            result["strategy_quality_a"] = eval_1.get("team_a_strategy_quality", 50)
            result["strategy_quality_b"] = eval_1.get("team_b_strategy_quality", 50)

            print(f"[Judge] SELECTED: Team {result.get('winning_team')} - {result.get('winning_guess')}")
            return result

        except Exception as e:
            print(f"[Judge] Error in Turn 3: {e}")
            choice = eval_2.get('preliminary_choice', 'A')
            if choice == 'A':
                return {
                    "selected_team": proposal_a.get('team'),
                    "winning_guess": proposal_a.get('guess'),
                    "reasoning": "LLM error fallback - Team A selected",
                    "confidence": proposal_a.get('confidence', 50),
                }
            else:
                return {
                    "selected_team": proposal_b.get('team'),
                    "winning_guess": proposal_b.get('guess'),
                    "reasoning": "LLM error fallback - Team B selected",
                    "confidence": proposal_b.get('confidence', 50),
                }

    def _evaluate_heuristic(
        self,
        proposal_a: Dict[str, Any],
        proposal_b: Dict[str, Any],
        shared_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Use heuristic evaluation when LLM is unavailable."""

        print(f"[Judge] Using heuristic evaluation mode")

        # Get constraint information for late-game decisions
        constraints = self._extract_constraints(shared_history)

        # Simple heuristic: higher confidence wins, with minor color diversity check
        conf_a = proposal_a.get('confidence', 50)
        conf_b = proposal_b.get('confidence', 50)

        guess_a = proposal_a.get('guess', [])
        guess_b = proposal_b.get('guess', [])

        # Check if we're in late game (correct_pegs >= 3 recently)
        is_late_game = False
        if shared_history:
            recent_feedback = shared_history[-1].get('feedback', {})
            pegs = recent_feedback.get('correct_pegs', 0)
            positions = recent_feedback.get('correct_positions', 0)
            is_late_game = pegs >= 3 or positions >= 2

        # Slight preference for diversity
        diversity_bonus = 5
        if len(set(guess_a)) > len(set(guess_b)):
            conf_a += diversity_bonus
        elif len(set(guess_b)) > len(set(guess_a)):
            conf_b += diversity_bonus

        # Late-game tiebreaker: prefer guesses that reuse confirmed colors
        if is_late_game and abs(conf_a - conf_b) < 10:
            confirmed = constraints.get('confirmed_colors', set())
            confirmed_in_a = sum(1 for c in guess_a if c in confirmed)
            confirmed_in_b = sum(1 for c in guess_b if c in confirmed)

            # Prefer proposal with more confirmed colors
            if confirmed_in_a > confirmed_in_b:
                conf_a += 10
            elif confirmed_in_b > confirmed_in_a:
                conf_b += 10

        if conf_a >= conf_b:
            return {
                "selected_team": proposal_a.get('team'),
                "winning_guess": guess_a,
                "reasoning": f"Team A confidence {proposal_a.get('confidence', 50)}% ≥ Team B {proposal_b.get('confidence', 50)}%",
                "confidence": conf_a,
            }
        else:
            return {
                "selected_team": proposal_b.get('team'),
                "winning_guess": guess_b,
                "reasoning": f"Team B confidence {proposal_b.get('confidence', 50)}% > Team A {proposal_a.get('confidence', 50)}%",
                "confidence": conf_b,
            }

    def _extract_constraints(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract constraints from game history (inspired by boss_worker).

        Analyzes feedback to determine:
        - Which colors are confirmed in the code
        - Which colors are definitely eliminated
        - Which positions are locked
        - Position hypotheses (when 4p with partial positions)
        - Color confidence scores (colors that appeared with positive feedback)
        """
        if not history:
            return {"confirmed_colors": set(), "eliminated_colors": set(),
                    "locked_positions": {}, "position_hypotheses": [], "color_confidence": {}}

        confirmed = set()
        eliminated = set()
        locked_pos = {}
        color_confidence = {}
        position_hypotheses = []

        for entry in history:
            guess = entry.get('guess', [])
            feedback = entry.get('feedback', {})
            pegs = feedback.get('correct_pegs', 0)
            pos = feedback.get('correct_positions', 0)

            # Track color confidence
            if pegs > 0:
                for color in guess:
                    if color not in color_confidence:
                        color_confidence[color] = 0
                    color_confidence[color] += 1

            if pegs == 0:
                eliminated.update(guess)
                for color in guess:
                    if color not in color_confidence:
                        color_confidence[color] = -1

            if pegs >= 2:
                confirmed.update(guess)

            # CRITICAL: Track position hypotheses when 4p with partial positions
            if pegs == 4 and pos < 4:
                # We have all 4 colors but only pos positions are correct
                # Track which positions might be locked
                position_hypotheses.append({
                    "round": len(history),
                    "guess": guess,
                    "correct_pegs": pegs,
                    "correct_positions": pos,
                    "unlocked_count": 4 - pos,  # How many positions need to be found
                })

            # If all 4 positions correct, we found locked positions
            if pos == 4:
                for i, color in enumerate(guess):
                    locked_pos[i] = color

        return {
            "confirmed_colors": confirmed,
            "eliminated_colors": eliminated,
            "locked_positions": locked_pos,
            "position_hypotheses": position_hypotheses,
            "color_confidence": color_confidence,
            "duplicate_hypothesis": len(confirmed) > 4 or (len(history) > 3 and len(history[-1].get('guess', [])) == len(set(history[-1].get('guess', [])))),
        }

    def _format_constraints(self, constraints: Dict[str, Any]) -> str:
        """Format extracted constraints for LLM."""
        lines = []

        confirmed = constraints.get('confirmed_colors', set())
        eliminated = constraints.get('eliminated_colors', set())
        locked = constraints.get('locked_positions', {})
        color_confidence = constraints.get('color_confidence', {})
        position_hypotheses = constraints.get('position_hypotheses', [])
        duplicate = constraints.get('duplicate_hypothesis', False)

        if confirmed:
            # Sort by confidence score
            confident_colors = sorted(
                [(c, color_confidence.get(c, 0)) for c in confirmed],
                key=lambda x: x[1],
                reverse=True
            )
            color_str = ", ".join([f"{c}({score})" for c, score in confident_colors])
            lines.append(f"✓ CONFIRMED in code: {color_str}")

        if eliminated:
            lines.append(f"✗ ELIMINATED (NOT in code): {list(eliminated)}")

        if locked:
            lines.append(f"🔒 LOCKED positions: {locked}")

        # Position refinement guidance when we have 4p feedback
        if position_hypotheses:
            latest_hyp = position_hypotheses[-1]
            lines.append(f"\n🎯 POSITION REFINEMENT STATUS:")
            lines.append(f"   ✓ All 4 colors confirmed: {list(confirmed)}")
            lines.append(f"   📍 Last guess had {latest_hyp['correct_positions']} correct positions")
            lines.append(f"   🔄 Need to find {latest_hyp['unlocked_count']} more position(s)")

            # Analyze position patterns to identify likely locked positions
            if len(position_hypotheses) >= 2:
                # Compare last two hypotheses to see which colors stayed in same positions
                prev_hyp = position_hypotheses[-2]
                curr_guess = latest_hyp['guess']
                prev_guess = prev_hyp['guess']

                stable_positions = []
                for i in range(len(curr_guess)):
                    if i < len(prev_guess) and curr_guess[i] == prev_guess[i]:
                        stable_positions.append(i)

                if stable_positions:
                    lines.append(f"   🔒 Likely LOCKED positions: {stable_positions} (colors didn't move between guesses)")
                    lines.append(f"   💡 STRATEGY: DO NOT change colors at positions {stable_positions}!")
                    lines.append(f"   Swap positions: {[i for i in range(4) if i not in stable_positions]}")
            else:
                lines.append(f"   💡 STRATEGY: Test swaps of only the unlocked positions")
                lines.append(f"   Example: If 1 position is correct, test moving other 3")

        if duplicate:
            lines.append(f"⚠️  HYPOTHESIS: Code contains duplicate colors")

        if not lines:
            lines.append("No strong constraints yet (early game)")

        return "\n".join(lines)

    def _diversity_score(self, guess: List[str], history: List[Dict[str, Any]]) -> int:
        """Score how different this guess is from recent guesses.

        Higher score = more diverse and less repetitive.
        Rewards:
        - Testing new color combinations
        - Different positions of known colors
        - Testing untested colors
        - Position permutation in REFINEMENT phase
        """
        if len(history) < 2:
            return 50  # Neutral for early rounds

        recent_guesses = [tuple(entry.get('guess', [])) for entry in history[-3:]]
        current_tuple = tuple(guess)

        # Penalty for exact repetition
        if current_tuple in recent_guesses:
            return 10

        # Bonus for diversity
        score = 50

        # Check if we're in REFINEMENT phase (4p feedback)
        in_refinement = len(history) >= 3
        recent_feedback = history[-1].get('feedback', {}) if history else {}
        pegs = recent_feedback.get('correct_pegs', 0)
        positions = recent_feedback.get('correct_positions', 0)

        is_refinement_phase = pegs == 4 and positions < 4

        # In REFINEMENT phase, heavily reward position changes
        if is_refinement_phase:
            position_changes = 0
            for i, (prev, curr) in enumerate(zip(recent_guesses[-1], guess)):
                if prev != curr:
                    position_changes += 1

            # In REFINEMENT, every position change is critical
            score = 30 + (position_changes * 15)  # 0 changes = 30, 4 changes = 90

            # Bonus if this is a systematic rotation (position-by-position shift)
            if position_changes >= 2:  # At least some permutation happening
                score += 20

            return min(100, score)

        # Regular phase: reward new colors and position diversity
        recent_colors = set()
        for g in recent_guesses:
            recent_colors.update(g)

        new_colors = set(guess) - recent_colors
        score += len(new_colors) * 10  # +10 for each new color tested

        # Bonus for different positions (less critical in exploration)
        position_changes = 0
        for i, (prev, curr) in enumerate(zip(recent_guesses[-1], guess)):
            if prev != curr:
                position_changes += 1
        score += position_changes * 5  # +5 for each position change

        return min(100, score)

    def _format_history(self, history: List[Dict[str, Any]]) -> str:
        """Format game history for LLM context."""
        if not history:
            return "No previous guesses yet."

        lines = []
        for i, entry in enumerate(history[-5:], 1):  # Last 5 rounds
            guess = entry.get('guess', [])
            feedback = entry.get('feedback', {})
            pegs = feedback.get('correct_pegs', 0)
            pos = feedback.get('correct_positions', 0)
            lines.append(f"  {i}. {guess} → {pegs}p {pos}pos")
        return "\n".join(lines) if lines else "No previous guesses yet."

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent."""
        return {"status": "ok", "message": "Judge is a pipeline node, not called directly"}
