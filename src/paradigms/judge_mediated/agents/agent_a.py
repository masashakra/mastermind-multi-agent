# Agent A: Analyzer + Proposer Hybrid
# Analyzes constraints and proposes guesses

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType
from communication.protocol import A2ACommunicationLayer


class AgentA(BaseAgent):
    """Hybrid Agent A: Analyzer + Proposer

    Combines:
    1. Analyze feedback and extract constraints
    2. Propose next guess based on constraints
    """

    def __init__(
        self,
        provider: str = "deepseek",
        comm_layer: Optional[A2ACommunicationLayer] = None,
    ):
        super().__init__(
            name="AgentA_AnalyzerProposer",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.ANALYZER,
            paradigm=ParadigmType.JUDGE_MEDIATED,
        )

    def analyze_and_propose(
        self,
        guess_history: List[List[str]],
        last_feedback: Dict[str, Any],
        difficulty: str,
        available_colors: List[str],
        num_pegs: int,
    ) -> Dict[str, Any]:
        """Analyze constraints and propose a guess in one step.

        Args:
            guess_history: Previous guesses
            last_feedback: Feedback from last guess
            difficulty: Puzzle difficulty
            available_colors: Available colors
            num_pegs: Number of pegs

        Returns:
            {"guess": [...], "analysis": "...", "confidence": 0-1}
        """

        # Build history
        history_text = ""
        if guess_history:
            history_text = "Previous guesses and feedback:\n"
            for i, guess in enumerate(guess_history):
                history_text += f"  {i+1}. {guess}\n"

        last_feedback_text = ""
        if last_feedback:
            last_feedback_text = f"""
Last feedback:
- Correct pegs (right color, wrong position): {last_feedback.get('correct_pegs', 0)}
- Correct positions (right color, right position): {last_feedback.get('correct_positions', 0)}
"""

        prompt = f"""You are solving a Mastermind puzzle. Analyze the constraints and propose the NEXT guess.

Puzzle Info:
- Difficulty: {difficulty}
- Pegs: {num_pegs}
- Available colors: {', '.join(available_colors)}

{history_text}{last_feedback_text}

Task:
1. Analyze: What constraints can you extract from the feedback?
2. Propose: What is your next guess based on these constraints?

Respond ONLY with:
ANALYSIS: [key constraints]
GUESS: [color1, color2, color3, ...]

Example: GUESS: red, blue, green, yellow
"""

        try:
            response = self.call_llm(prompt)

            # Parse response
            analysis = ""
            guess = []

            lines = response.split('\n')
            for line in lines:
                if line.startswith("ANALYSIS:"):
                    analysis = line.replace("ANALYSIS:", "").strip()
                elif line.startswith("GUESS:"):
                    guess_text = line.replace("GUESS:", "").strip()
                    guess = [c.strip().lower() for c in guess_text.split(',')]
                    guess = guess[:num_pegs]

            # Validate
            if len(guess) < num_pegs:
                guess.extend([available_colors[0]] * (num_pegs - len(guess)))

            guess = [c if c in available_colors else available_colors[0] for c in guess]

            self.call_count += 1
            return {
                "guess": guess,
                "analysis": analysis,
                "confidence": min(1.0, max(0.0, (len(guess_history) + 1) / 8.0)),  # Increase with rounds
            }

        except Exception as e:
            print(f"Error in Agent A: {e}")
            import random
            guess = [random.choice(available_colors) for _ in range(num_pegs)]
            return {
                "guess": guess,
                "analysis": f"Error: {str(e)}",
                "confidence": 0.1,
            }

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process request."""
        return self.analyze_and_propose(
            guess_history=kwargs.get("guess_history", []),
            last_feedback=kwargs.get("last_feedback", {}),
            difficulty=kwargs.get("difficulty", "easy"),
            available_colors=kwargs.get("available_colors", []),
            num_pegs=kwargs.get("num_pegs", 4),
        )
