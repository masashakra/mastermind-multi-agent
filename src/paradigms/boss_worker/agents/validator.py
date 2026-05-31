# Boss-Worker Validator Agent
# Fully autonomous LLM-based validation with state tracking
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import List, Dict, Any, Optional
from base.base_agent import BaseAgent
from base.agent_card import VALIDATOR_CARD
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType

AGENT_CARD = {
    **VALIDATOR_CARD,
    "agent_id": "validator_boss_worker",
    "paradigm": "boss_worker",
}

class ValidatorAgent(BaseAgent):
    """Boss-Worker Validator Agent - Fully Autonomous

    Validates guesses against constraints using intelligent LLM reasoning.
    Maintains validation history and learns patterns across rounds.
    Makes independent decisions about guess validity based on strategy.
    """

    def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None,
                 role: Optional[AgentRole] = None, paradigm: Optional[ParadigmType] = None,
                 team_members: Optional[List[str]] = None, can_communicate: bool = True,
                 constraints_owned: Optional[List[str]] = None):
        super().__init__(
            name="Validator_BossWorker", provider=provider, comm_layer=comm_layer,
            role=role or AgentRole.VALIDATOR, paradigm=paradigm or ParadigmType.BOSS_WORKER,
            team_members=team_members or ["boss", "analyzer", "strategist", "proposer"],
            can_communicate=can_communicate, constraints_owned=constraints_owned or ["Hard constraint enforcement"],
        )
        # State tracking - Validator learns from its own validations
        self.validation_history = []
        self.rejected_guesses = []
        self.accepted_guesses = []
        self.rejection_reasons = {}

    def validate_guess(self, guess: List[str], available_colors: List[str],
                      expected_length: int, previous_guesses: List[List[str]],
                      constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Validate guess using intelligent LLM reasoning.

        The validator uses its own judgment to assess validity, considering:
        - Hard constraints (locked positions, impossible colors)
        - Soft constraints (misplaced colors, positioning logic)
        - Pattern analysis from previous validations
        - Strategic assessment of the guess quality
        - Diversity from previously tried guesses
        """
        role_context = self.get_role_system_prompt()

        colors_str = ", ".join(available_colors)
        prev_str = "\n".join([f"  {i+1}. {g}" for i, g in enumerate(previous_guesses[-3:])]) if previous_guesses else "None"

        # Include validation history for context
        acceptance_rate = len(self.accepted_guesses) / len(self.validation_history) if self.validation_history else 0
        history_context = f"You have validated {len(self.validation_history)} guesses so far. Acceptance rate: {acceptance_rate:.0%}"

        # Build constraint summary for the validator to reason about
        constraint_summary = f"""
CONSTRAINTS TO ENFORCE:
- Locked positions (must be correct): {constraints.get('correct_positions', []) or 'None'}
- Impossible colors (must avoid): {constraints.get('impossible_colors', []) or 'None'}
- Misplaced colors (must include but reposition): {constraints.get('correct_colors_wrong_position', []) or 'None'}
"""

        # Full LLM-based validation with strategic reasoning
        prompt = f"""{role_context}

## YOUR TASK (Validation in Boss-Worker Paradigm)
You are the Validator. Your job is to thoroughly assess if this guess is sound and respects all constraints.
Use your expertise to make independent decisions. You are responsible for validation quality.

PROPOSED GUESS: {guess}
AVAILABLE COLORS: {colors_str}
EXPECTED LENGTH: {expected_length}

{constraint_summary}

PREVIOUS GUESSES (last 3):
{prev_str}

{history_context}

VALIDATION ASSESSMENT - Consider:
1. Hard constraints: Does it violate any MUST rules?
   - Does it respect all locked positions?
   - Does it avoid all impossible colors?
   - Is the length correct?
   - Are there duplicates?

2. Soft constraints: Does it use the information effectively?
   - Does it include the misplaced colors (repositioned)?
   - Is it positioned differently from where it failed before?
   - Does it make strategic sense given the feedback?

3. Pattern analysis: Is it consistent with previous validations?
   - Is it similar to rejected patterns you've seen?
   - Does it avoid common mistakes?
   - Does it show learning from feedback?

4. Diversity: Is it different enough from previous attempts?
   - Is it a new combination?
   - Or just a minor variation of something already tried?

5. Strategic quality: Is it a good next step?
   - Does it advance the game state?
   - Is it too conservative or too risky?
   - What's your professional assessment?

Make your independent judgment call based on your expertise.

OUTPUT (JSON ONLY):
{{
  "valid": true/false,
  "confidence": 0.0-1.0,
  "hard_violations": ["list of rule violations, if any"],
  "soft_warnings": ["list of strategic concerns, if any"],
  "reasoning": "Your detailed reasoning about validity",
  "strategic_assessment": "Your assessment of this as a good next move",
  "recommendation": "ACCEPT|FLAG_WITH_WARNING|REJECT"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        # Fallback if LLM response fails
        if "error" in result:
            result = {
                "valid": len(guess) == expected_length and all(c in available_colors for c in guess),
                "confidence": 0.3,
                "hard_violations": [],
                "soft_warnings": ["LLM validation failed"],
                "reasoning": "Fallback to basic validation",
                "strategic_assessment": "Unable to assess due to LLM error",
                "recommendation": "ACCEPT"
            }

        # Determine final validity from recommendation
        is_valid = result.get("recommendation", "ACCEPT") != "REJECT"
        if result.get("valid") is not None:
            is_valid = result.get("valid", False) and result.get("recommendation", "ACCEPT") != "REJECT"

        # Track validation in state for learning
        validation_record = {
            "guess": guess,
            "valid": is_valid,
            "confidence": result.get("confidence", 0.5),
            "hard_violations": result.get("hard_violations", []),
            "reasoning": result.get("reasoning", "")
        }
        self.validation_history.append(validation_record)

        if is_valid:
            self.accepted_guesses.append(guess)
        else:
            self.rejected_guesses.append(guess)
            self.rejection_reasons[str(guess)] = result.get("hard_violations", [])

        # Return validation with recommendation
        return {
            "valid": is_valid,
            "confidence": result.get("confidence", 0.5),
            "hard_violations": result.get("hard_violations", []),
            "soft_warnings": result.get("soft_warnings", []),
            "reasoning": result.get("reasoning", ""),
            "strategic_assessment": result.get("strategic_assessment", ""),
            "recommendation": result.get("recommendation", "ACCEPT"),
            "acceptance_rate": len(self.accepted_guesses) / len(self.validation_history) if self.validation_history else 0
        }

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent abstract class.

        Delegates to validate_guess for this agent.
        """
        return self.validate_guess(
            guess=kwargs.get("guess", []),
            available_colors=kwargs.get("available_colors", []),
            expected_length=kwargs.get("expected_length", 4),
            previous_guesses=kwargs.get("previous_guesses", []),
            constraints=kwargs.get("constraints", {}),
        )
