# Agent B: Strategist + Validator Hybrid
# Develops strategy and validates approach

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType
from communication.protocol import A2ACommunicationLayer


class AgentB(BaseAgent):
    """Hybrid Agent B: Strategist + Validator

    Combines:
    1. Develop strategy based on feedback
    2. Evaluate confidence in the puzzle-solving approach
    """

    def __init__(
        self,
        provider: str = "deepseek",
        comm_layer: Optional[A2ACommunicationLayer] = None,
    ):
        super().__init__(
            name="AgentB_StrategistValidator",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.STRATEGIST,
            paradigm=ParadigmType.JUDGE_MEDIATED,
        )

    def strategize_and_validate(
        self,
        guess_history: List[List[str]],
        last_feedback: Dict[str, Any],
        difficulty: str,
    ) -> Dict[str, Any]:
        """Develop strategy and validate approach.

        Args:
            guess_history: Previous guesses
            last_feedback: Feedback from last guess
            difficulty: Puzzle difficulty

        Returns:
            {"strategy": "...", "confidence": 0-1}
        """

        history_text = ""
        if guess_history:
            history_text = "Previous guesses and feedback:\n"
            for i, guess in enumerate(guess_history):
                history_text += f"  {i+1}. {guess}\n"

        last_feedback_text = ""
        if last_feedback:
            last_feedback_text = f"""
Last feedback:
- Correct pegs: {last_feedback.get('correct_pegs', 0)}
- Correct positions: {last_feedback.get('correct_positions', 0)}
"""

        prompt = f"""Based on the puzzle-solving progress, develop a strategy and rate confidence.

Puzzle Info:
- Difficulty: {difficulty}
- Rounds completed: {len(guess_history)}

{history_text}{last_feedback_text}

Task:
1. Strategy: What should the next guessing strategy be?
2. Confidence: Rate your confidence in solving this puzzle (0-10)

Respond ONLY with:
STRATEGY: [describe the approach]
CONFIDENCE: [0-10]
"""

        try:
            response = self.call_llm(prompt)

            # Parse response
            strategy = ""
            confidence = 5  # Default middle ground

            lines = response.split('\n')
            for line in lines:
                if line.startswith("STRATEGY:"):
                    strategy = line.replace("STRATEGY:", "").strip()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        conf_str = line.replace("CONFIDENCE:", "").strip()
                        conf_val = int(''.join(filter(str.isdigit, conf_str.split()[0])))
                        confidence = max(0, min(10, conf_val))
                    except:
                        confidence = 5

            self.call_count += 1
            return {
                "strategy": strategy,
                "confidence": confidence / 10.0,  # Normalize to 0-1
            }

        except Exception as e:
            print(f"Error in Agent B: {e}")
            return {
                "strategy": f"Error: {str(e)}",
                "confidence": 0.1,
            }

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process request."""
        return self.strategize_and_validate(
            guess_history=kwargs.get("guess_history", []),
            last_feedback=kwargs.get("last_feedback", {}),
            difficulty=kwargs.get("difficulty", "easy"),
        )
