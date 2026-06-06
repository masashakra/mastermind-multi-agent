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
        """Generate guess based on strategy from Analyser-Strategist.

        Args:
            guess_history: List of previous guesses and feedback
            difficulty: Puzzle difficulty level
            available_colors: Available colors
            num_pegs: Number of pegs in code
            strategy: Strategy guidance from analyser-strategist

        Returns:
            {
                "guess": [...],
                "reasoning": "...",
            }
        """
        # Build context from guess history
        history_text = self._format_history(guess_history)

        # Build knowledge from reflection & learning
        learned_text = self._format_learned_knowledge()

        prompt = f"""You are the Solver for {self.team_id}, executing puzzle solving.

PUZZLE STATE:
- Available colors: {available_colors}
- Code length: {num_pegs} pegs
- Difficulty: {difficulty}

YOUR PAST GUESSES:
{history_text if history_text else "No previous guesses yet."}

YOUR LEARNED KNOWLEDGE (patterns discovered):
{learned_text if learned_text else "No patterns learned yet - this is our first round."}

STRATEGY FROM ANALYSER-STRATEGIST:
{strategy if strategy else "No strategy provided yet - generate exploratory guess."}

YOUR TASK:
1. Follow the strategy if provided
2. Use learned knowledge to inform your guess
3. Generate a guess that maximizes information gain

Return ONLY valid JSON (no markdown):
{{
  "guess": ["color1", "color2", ...],
  "reasoning": "Why this guess follows strategy and learned patterns..."
}}

CONSTRAINTS:
- guess must have exactly {num_pegs} colors
- Each color must be from: {available_colors}
- Colors can be repeated
- Never repeat a previous guess
"""

        try:
            response = self.call_llm(prompt)
            result = self._parse_json_response(response)

            guess = result.get("guess", [])

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
