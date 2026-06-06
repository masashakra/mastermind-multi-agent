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

    def propose_guess(
        self,
        strategy: Dict[str, Any],
        available_colors: List[str] = None,
        num_pegs: int = 4,
        round_num: int = 1,
    ) -> Dict[str, Any]:
        """Generate a guess following the strategy with autonomous permutation reasoning."""

        if available_colors is None:
            available_colors = []

        # Safety check: ensure strategy is a valid dict
        if not isinstance(strategy, dict) or strategy is None:
            strategy = {"colors_in": available_colors[:num_pegs], "strategy": "systematic testing", "locked_positions": {}}

        colors_in = strategy.get("colors_in", available_colors[:num_pegs])
        locked_positions = strategy.get("locked_positions", {})
        strategy_desc = strategy.get("strategy", "Generate a tactical guess")
        near_solve = strategy.get("near_solve_state", False)

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

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process proposal."""
        return self.propose_guess(
            strategy=kwargs.get("strategy", {}),
            available_colors=kwargs.get("available_colors", []),
            num_pegs=kwargs.get("num_pegs", 4),
            round_num=kwargs.get("round_num", 1),
        )
