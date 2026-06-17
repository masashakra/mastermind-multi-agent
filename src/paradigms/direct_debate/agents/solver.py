# Solver Agent — Focused on puzzle solving
# Takes guidance from Analyser-Strategist, generates and submits guesses

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType


AGENT_CARD = {
    "agent_id": "solver_direct_debate",
    "agent_name": "Solver Agent",
    "agent_type": "solver",
    "paradigm": "direct_debate",
    "version": "1.0.0",
    "description": "Solver agent focused on Mastermind puzzle solving via LLM-driven reasoning.",
    "url": "http://localhost:8301",
    "capabilities": {
        "solve_round": {
            "description": "Generate guess based on analysis and strategy",
            "parameters": {
                "type": "object",
                "properties": {
                    "guess_history": {"type": "array"},
                    "difficulty": {"type": "string"},
                    "available_colors": {"type": "array"},
                    "num_pegs": {"type": "integer"},
                    "strategy": {"type": "string"},
                },
            },
            "returns": {
                "type": "object",
                "properties": {
                    "guess": {"type": "array"},
                    "reasoning": {"type": "string"},
                },
            },
        },
    },
    "constraints_owned": ["Guess Generation", "Validation"],
    "team_members": [],
    "can_communicate": False,  # Solver does not communicate with other teams
}


class Solver(BaseAgent):
    """Solver Agent — Executes puzzle solving based on strategy from Analyser-Strategist.

    Responsibilities:
    - Generate guesses
    - Submit to orchestrator
    - Reflect on feedback
    - Report results to analyser-strategist
    """

    def __init__(self, provider: str = "deepseek", team_id: str = "team_1"):
        super().__init__(
            name=f"Solver_{team_id}",
            provider=provider,
            role=AgentRole.PROPOSER,
            paradigm=ParadigmType.DIRECT_DEBATE,
            team_members=[],
            can_communicate=False,  # Does not debate
            constraints_owned=["Guess Generation", "Validation"],
        )
        self.team_id = team_id
        # Game reflection & learning
        self.learned_hypotheses = []
        self.color_analysis = {}
        self.position_analysis = {}
        # Links to team partner
        self.analyser_strategist_url = None

    def solve_round(
        self,
        guess_history: List[Dict[str, Any]],
        difficulty: str,
        available_colors: List[str],
        num_pegs: int,
        strategy: str = "",
    ) -> Dict[str, Any]:
        """Generate guess using EXPLICIT CONSTRAINT ANALYSIS (boss_worker style).

        5-step process:
        1. Extract constraints from history
        2. Analyze current game state
        3. Eliminate impossible options
        4. Fill remaining positions strategically
        5. Validate and finalize
        """
        round_num = len(guess_history) + 1

        # ✅ EXTRACT CONSTRAINTS LIKE BOSS_WORKER ANALYZER
        constraints = self._extract_constraints(guess_history)

        # ✅ BUILD STRICT CONSTRAINT ANALYSIS
        constraint_facts = self._build_strict_constraints(guess_history, constraints, available_colors)

        prompt = f"""You are the Solver for {self.team_id} in Mastermind.
Your role: Generate guesses by STRICTLY respecting constraint facts.

CRITICAL RULES (NON-NEGOTIABLE):
- Secret code: exactly {num_pegs} colors, colors CAN repeat
- Available colors: {available_colors}
- GUESS MUST HAVE EXACTLY {num_pegs} COLORS!
- NEVER use IMPOSSIBLE COLORS
- ALWAYS preserve LOCKED POSITIONS (exact match)
- ALWAYS respect CONFIRMED COLORS (must use them)

═══ CONSTRAINT FACTS (From history analysis) ═══

{constraint_facts}

═══ PAST GUESSES (ABSOLUTE NO-REPEAT LIST) ═══
{str([g.get('guess', []) for g in guess_history[-8:]])}

═══ DECISION TREE ═══

IF you have 4 pegs correct (4p):
  → ALL COLORS ARE CORRECT
  → Only positions are wrong
  → STRICTLY: Test position swaps/rotations ONLY
  → Keep any locked positions EXACTLY as they are
  → Swap other positions systematically: [B,C,D,A], [C,D,A,B], [D,A,B,C]

ELSE IF you have 3 pegs (stuck at 3p multiple times):
  → ONE COLOR IS WRONG
  → STRICTLY: Replace each color candidate ONE AT A TIME with untested colors
  → Test order: [A,B,C,E], [A,B,F,D], [A,G,C,D], [H,B,C,D]
  → Never rotate! Always replace ONE position at a time!

ELSE IF you have 2+ pegs:
  → Continue discovering remaining colors
  → Test untested colors in different positions
  → Avoid colors marked impossible

ELSE (0-1 pegs):
  → Early exploration
  → Test diverse colors

═══ YOUR TASK ═══

1. Identify current state from feedback
2. Choose correct decision branch
3. Generate guess that STRICTLY follows chosen branch
4. Ensure guess: ✓ respects locked positions, ✓ uses confirmed colors, ✓ no impossible colors, ✓ not repeated, ✓ exactly {num_pegs} colors

STRATEGY FROM ANALYSER: {strategy if strategy else "Explore"}

Return VALID JSON:
{{"guess": ["c1", "c2", "c3", "c4"], "reasoning": "Decision branch + action taken"}}"""

        try:
            response = self.call_llm_conversation(
                prompt,
                f"Round {round_num}: Apply 5-step constraint analysis to generate guess"
            )
            result = self._parse_json_response(response)

            guess = result.get("guess", [])

            # ✅ AGGRESSIVE FALLBACK: If we have 4p but wrong positions, FORCE position refinement
            if guess_history:
                latest = guess_history[-1]
                pegs = latest.get('feedback', {}).get('correct_pegs', 0)
                positions = latest.get('feedback', {}).get('correct_positions', 0)
                prev_guesses_list = [g.get('guess', []) for g in guess_history]

                if pegs == 4 and positions < 4:
                    # Force systematic position refinement
                    last_guess = latest.get('guess', [])
                    wrong_positions = 4 - positions

                    if wrong_positions <= 2 and last_guess:
                        # For 1-2 wrong positions, systematically test swaps
                        for i in range(4):
                            for j in range(i+1, 4):
                                new_guess = list(last_guess)
                                new_guess[i], new_guess[j] = new_guess[j], new_guess[i]
                                if new_guess != last_guess and new_guess not in prev_guesses_list:
                                    guess = new_guess
                                    reasoning += f" [FALLBACK: Position swap {i}↔{j}]"
                                    break
                            if guess != result.get("guess", []):
                                break

            # Validate the guess
            if not self._is_valid_guess(guess, available_colors, num_pegs, guess_history):
                # If invalid, use fallback
                guess = self._fallback_guess(available_colors, num_pegs, guess_history)

            return {
                "guess": guess,
                "reasoning": result.get("reasoning", ""),
            }
        except Exception as e:
            print(f"[{self.team_id} Solver] LLM error in solve_round: {e}")
            guess = self._fallback_guess(available_colors, num_pegs, guess_history)
            return {
                "guess": guess,
                "reasoning": f"Error: {str(e)}",
            }

    def reflect_on_feedback(self, round_num: int, guess: List[str], feedback: Dict[str, Any]) -> None:
        """Analyze feedback and build learned hypotheses.

        Called after each guess to update learned patterns.
        """
        pegs = feedback.get("correct_pegs", 0)
        positions = feedback.get("correct_positions", 0)

        # Analyze color appearances
        for color in guess:
            if color not in self.color_analysis:
                self.color_analysis[color] = {"in_guesses": 0, "correct_feedback": 0}
            self.color_analysis[color]["in_guesses"] += 1

        # If we got correct_pegs feedback, those colors are likely in the code
        if pegs > 0:
            if not any(h.startswith(f"R{round_num}: Colors in code") for h in self.learned_hypotheses):
                hypothesis = f"R{round_num}: {pegs} colors from {guess} are in code (feedback: {pegs}p {positions}pos)"
                self.learned_hypotheses.append(hypothesis)

        # Position analysis: If we got positions right, lock those
        if positions > 0:
            hypothesis = f"R{round_num}: {positions} colors locked in positions (feedback: {pegs}p {positions}pos). Guess: {guess}"
            self.learned_hypotheses.append(hypothesis)

        # If we got 0 pegs, we learned which colors are NOT in code
        if pegs == 0:
            wrong_colors = ", ".join(guess)
            hypothesis = f"R{round_num}: Colors NOT in code: {wrong_colors}"
            self.learned_hypotheses.append(hypothesis)

        # Track color frequency
        for color in guess:
            if color not in self.color_analysis:
                self.color_analysis[color] = {"in_guesses": 0, "correct_feedback": 0}
            self.color_analysis[color]["in_guesses"] += 1
            if pegs > 0:
                self.color_analysis[color]["correct_feedback"] += 1

    def _build_strict_constraints(self, guess_history: List[Dict[str, Any]], constraints: Dict[str, Any], available_colors: List[str]) -> str:
        """Build STRICT constraint facts for the prompt (like boss_worker Analyzer output)."""
        lines = []

        # IMPOSSIBLE COLORS (confirmed absent)
        impossible = constraints.get('impossible_colors', [])
        if impossible:
            lines.append(f"🚫 IMPOSSIBLE COLORS (never in code): {impossible}")
        else:
            lines.append(f"🚫 No impossible colors yet")

        # CONFIRMED COLORS (definitely in code)
        confirmed = constraints.get('confirmed_colors', [])
        if confirmed:
            lines.append(f"✓ CONFIRMED COLORS (definitely in code): {confirmed}")
            need = 4 - len(confirmed)
            lines.append(f"   → Need {need} more colors to find")
        else:
            lines.append(f"✓ No colors confirmed yet")

        # LOCKED POSITIONS (exact position-color matches)
        locked = constraints.get('locked_positions', [])
        if locked:
            locked_str = ", ".join([f"pos{l['position']}={l['color']}" for l in locked])
            lines.append(f"🔒 LOCKED POSITIONS (NEVER change): {locked_str}")
        else:
            lines.append(f"🔒 No positions locked yet")

        # MISPLACED COLORS (in code but wrong position)
        misplaced = constraints.get('misplaced_colors', [])
        if misplaced:
            lines.append(f"↔️  MISPLACED COLORS (in code, wrong positions): {misplaced}")
        else:
            lines.append(f"↔️  No misplaced colors detected yet")

        # ANALYSIS FROM FEEDBACK PATTERNS
        if guess_history:
            latest = guess_history[-1]
            pegs = latest.get('feedback', {}).get('correct_pegs', 0)
            positions = latest.get('feedback', {}).get('correct_positions', 0)

            # Count patterns
            four_p_count = sum(1 for h in guess_history if h.get('feedback', {}).get('correct_pegs') == 4)
            three_p_count = sum(1 for h in guess_history if h.get('feedback', {}).get('correct_pegs') == 3)

            lines.append(f"\n📊 FEEDBACK PATTERNS:")
            lines.append(f"   Latest: {pegs}p {positions}pos")
            if four_p_count > 0:
                lines.append(f"   ✅ HAVE 4p IN {four_p_count} ROUND(S) → All colors correct, need position refinement!")
            if three_p_count >= 2:
                lines.append(f"   ⚠️  STUCK AT 3p FOR {three_p_count} ROUNDS → ONE COLOR IS WRONG, test replacements!")

        return "\n".join(lines)

    def _generate_position_refinement_guess(self, last_guess: List[str], positions_correct: int) -> List[str]:
        """Generate next guess by swapping non-locked positions.

        If you have 4p Npos, N positions are locked, need to swap the (4-N) wrong ones.
        """
        # Simple strategy: test adjacent swaps
        guess = list(last_guess)

        if positions_correct == 3:
            # 1 position wrong - try swapping it with each other position
            for i in range(4):
                for j in range(i+1, 4):
                    new_guess = list(last_guess)
                    new_guess[i], new_guess[j] = new_guess[j], new_guess[i]
                    return new_guess
        elif positions_correct == 2:
            # 2 positions wrong - try swapping them
            for i in range(4):
                for j in range(i+1, 4):
                    new_guess = list(last_guess)
                    new_guess[i], new_guess[j] = new_guess[j], new_guess[i]
                    if new_guess != last_guess:
                        return new_guess
        elif positions_correct == 1:
            # 3 positions wrong - try rotations
            new_guess = list(last_guess)
            new_guess[0], new_guess[1], new_guess[2], new_guess[3] = new_guess[1], new_guess[2], new_guess[3], new_guess[0]
            return new_guess
        elif positions_correct == 0:
            # All positions wrong - try full rotation
            new_guess = list(last_guess)
            new_guess[0], new_guess[1], new_guess[2], new_guess[3] = new_guess[1], new_guess[2], new_guess[3], new_guess[0]
            return new_guess

        return guess

    def _extract_constraints(self, guess_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract constraints like boss_worker Analyzer does."""
        impossible = set()
        confirmed = set()
        locked_pos = {}
        misplaced = []

        for entry in guess_history:
            guess = entry.get('guess', [])
            feedback = entry.get('feedback', {})
            pegs = feedback.get('correct_pegs', 0)
            positions = feedback.get('correct_positions', 0)

            # If 0 pegs, all colors in this guess are impossible
            if pegs == 0:
                impossible.update(guess)

            # If > 0 pegs, colors are confirmed
            if pegs > 0:
                confirmed.update(guess)

            # Track locked positions (4p means all colors correct)
            if pegs == 4 and positions == 4:
                for i, color in enumerate(guess):
                    locked_pos[i] = color

            # Track misplaced colors
            if pegs > positions:
                misplaced_count = pegs - positions
                for color in guess:
                    if color in confirmed:
                        misplaced.append(color)

        return {
            "impossible_colors": list(impossible),
            "confirmed_colors": list(confirmed),
            "locked_positions": [{"position": pos, "color": col} for pos, col in locked_pos.items()],
            "misplaced_colors": misplaced,
        }

    def _analyze_game_state(self, guess_history: List[Dict[str, Any]], constraints: Dict[str, Any]) -> str:
        """Analyze current game state to determine phase and action needed."""
        if not guess_history:
            return "ROUND 1: Exploration phase - test 4 distinct colors to discover palette"

        latest = guess_history[-1]
        pegs = latest.get('feedback', {}).get('correct_pegs', 0)
        positions = latest.get('feedback', {}).get('correct_positions', 0)

        confirmed = constraints.get('confirmed_colors', [])
        impossible = constraints.get('impossible_colors', [])
        locked = constraints.get('locked_positions', [])

        # Count 3p feedback (critical pattern)
        three_p_rounds = sum(1 for h in guess_history if h.get('feedback', {}).get('correct_pegs') == 3)

        # Determine phase
        if pegs == 4:
            return f"PHASE: POSITION REFINEMENT\nHave 4 correct colors, need to lock positions. Currently {positions}/4 locked."
        elif three_p_rounds >= 2:
            return f"PHASE: COLOR DISCOVERY (CRITICAL)\nStuck at 3p for {three_p_rounds} rounds. ONE color is WRONG. Test color replacements systematically."
        elif pegs >= 2:
            return f"PHASE: CONSTRAINT_BUILDING\nHave {len(confirmed)} confirmed colors, {len(impossible)} impossible. Need to find remaining colors."
        else:
            return f"PHASE: EXPLORATION\nEarly game - test untested colors to discover which are in the code."

    def _extract_feedback_summary(self, recent_history: List[Dict[str, Any]]) -> str:
        """Extract key feedback pattern to understand current state."""
        if not recent_history:
            return "No feedback yet - first round"

        latest = recent_history[-1]
        pegs = latest.get('feedback', {}).get('correct_pegs', 0)
        positions = latest.get('feedback', {}).get('correct_positions', 0)

        # Detect if stuck at 3p (the critical case)
        if pegs == 3:
            three_p_count = sum(1 for h in recent_history if h.get('feedback', {}).get('correct_pegs') == 3)
            if three_p_count >= 2:
                return f"⚠️ STUCK AT 3p for {three_p_count} rounds - ONE color is WRONG, find the 4th!"

        if pegs == 4 and positions < 4:
            return f"✅ ALL 4 COLORS FOUND ({pegs}p {positions}pos) - Now lock positions via permutation"

        return f"Progress: {pegs}p {positions}pos - Continue systematic exploration"

    def _format_learned_knowledge(self) -> str:
        """Format learned hypotheses and analysis for LLM context."""
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
                if stats["correct_feedback"] >= 2
            ]
            if high_confidence_colors:
                lines.append(f"  • HIGH CONFIDENCE colors: {high_confidence_colors}")

        return "\n".join(lines)

    def _format_history(self, guess_history: List[Dict[str, Any]]) -> str:
        """Format guess history for LLM context."""
        if not guess_history:
            return ""

        lines = []
        for entry in guess_history:
            guess = entry.get("guess", [])
            feedback = entry.get("feedback", {})
            pegs = feedback.get("correct_pegs", 0)
            positions = feedback.get("correct_positions", 0)
            lines.append(f"Round {entry.get('round')}: {guess} → {pegs} pegs, {positions} positions")

        return "\n".join(lines)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            if "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start < end:
                    json_str = response[start:end]
                    return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        return {}

    def _is_valid_guess(
        self,
        guess: List[str],
        available_colors: List[str],
        num_pegs: int,
        guess_history: List[Dict[str, Any]],
    ) -> bool:
        """Check if guess is valid."""
        if not isinstance(guess, list):
            return False
        if len(guess) != num_pegs:
            return False
        for color in guess:
            if color not in available_colors:
                return False

        prev_guesses = [g.get("guess", []) for g in guess_history]
        if guess in prev_guesses:
            return False

        return True

    def _fallback_guess(
        self,
        available_colors: List[str],
        num_pegs: int,
        guess_history: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate a simple fallback guess when LLM fails."""
        if not guess_history:
            return available_colors[:num_pegs]

        last_guess = guess_history[-1].get("guess", [])
        new_guess = []

        for i in range(num_pegs):
            if i < len(last_guess):
                current_color = last_guess[i]
                try:
                    current_idx = available_colors.index(current_color)
                    next_idx = (current_idx + 1) % len(available_colors)
                    new_guess.append(available_colors[next_idx])
                except ValueError:
                    new_guess.append(available_colors[i % len(available_colors)])
            else:
                new_guess.append(available_colors[i % len(available_colors)])

        return new_guess

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process state."""
        return state
