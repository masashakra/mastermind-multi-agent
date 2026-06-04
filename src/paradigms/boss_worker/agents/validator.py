# Boss-Worker Validator Agent
# Validates guesses against constraints from Boss

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
    """Boss-Worker Validator Agent

    Validates guesses against constraints using rigorous LLM reasoning.
    Receives proposed guess from Boss along with constraint analysis.
    Returns validation result to Boss for final submission decision.
    """

    def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None,
                 role: Optional[AgentRole] = None, paradigm: Optional[ParadigmType] = None,
                 team_members: Optional[List[str]] = None, can_communicate: bool = False,
                 constraints_owned: Optional[List[str]] = None, registry_url: Optional[str] = None):
        super().__init__(
            name="Validator_BossWorker", provider=provider, comm_layer=comm_layer,
            role=role or AgentRole.VALIDATOR, paradigm=paradigm or ParadigmType.BOSS_WORKER,
            team_members=team_members or ["boss"],
            can_communicate=can_communicate, constraints_owned=constraints_owned or ["Hard constraint enforcement"],
            registry_url=registry_url,
        )

    def validate_guess(
        self,
        proposed_guess: List[str],
        guess_history: List[Dict],
        analysis: Dict[str, Any],
        num_pegs: int = 4,
    ) -> Dict[str, Any]:
        """Validate guess against hard and soft constraints from Analyzer."""
        round_num = len(guess_history) + 1
        expected_length = num_pegs

        # Format previous guesses for context
        prev_str = "\n".join(
            [f"  {i+1}. {g.get('guess', g)}" for i, g in enumerate(guess_history[-3:])]
        ) if guess_history else "None"

        # Build constraint summary
        constraint_summary = f"""HARD CONSTRAINTS (MUST enforce):
- Locked positions (must match exactly): {analysis.get('locked_positions', []) or 'None'}
- Impossible colors (must avoid): {analysis.get('impossible_colors', []) or 'None'}
- Guess length: must be exactly {expected_length} colors

SOFT CONSTRAINTS (should follow):
- Misplaced colors (must reposition): {analysis.get('misplaced_colors', []) or 'None'}
- Confirmed colors (should include): {analysis.get('confirmed_colors', []) or 'None'}
- Must be different from all previous guesses
"""

        system_prompt = f"""You are the Validator in a Mastermind game.
Your role: Rigorously assess if the proposed guess RESPECTS ALL CONSTRAINTS and is ready to submit.

ROUND: {round_num} of 8

HARD CONSTRAINT ENFORCEMENT:
1. Length: Is it exactly {expected_length} colors?
2. Locked positions: Does every locked position match the exact color?
3. Impossible colors: Does it avoid ALL impossible colors?
4. Uniqueness: Is it different from all {len(guess_history)} previous guesses?

SOFT CONSTRAINT ASSESSMENT:
1. Misplaced colors: Are misplaced colors repositioned (not in same wrong position)?
2. Strategy coherence: Does it advance the game effectively?
3. Information gain: Will this guess teach us something new?

{constraint_summary}

PROPOSED GUESS: {proposed_guess}
PREVIOUS GUESSES (last 3):
{prev_str}

VALIDATION OUTPUT (JSON ONLY):
{{
  "valid": true/false,
  "proposed_guess": {proposed_guess},
  "hard_violations": ["list of hard constraint violations if any"],
  "soft_warnings": ["list of strategic concerns if any"],
  "reasoning": "Detailed explanation of validity assessment",
  "confidence": 0.95
}}"""

        user_message = f"""Validate the proposed guess: {proposed_guess}

Check each hard constraint:
1. Length: {len(proposed_guess)} vs required {expected_length}
2. Locked positions: {analysis.get('locked_positions', [])}
3. Impossible colors: {analysis.get('impossible_colors', [])}
4. Previous guesses: {len(guess_history)} guesses made so far

Provide a detailed validation assessment with specific violations and confidence level."""

        try:
            response = self.call_llm_conversation(system_prompt, user_message)
        except Exception as e:
            print(f"[Validator] ERROR: {type(e).__name__}: {e}")
            return {
                "valid": len(proposed_guess) == expected_length,
                "proposed_guess": proposed_guess,
                "hard_violations": [],
                "soft_warnings": ["LLM error"],
                "confidence": 0.3
            }

        try:
            result = self.parse_json_response(response)
            if "proposed_guess" not in result:
                result["proposed_guess"] = proposed_guess
        except Exception as e:
            print(f"[Validator] ERROR parsing response: {e}")
            result = {
                "valid": len(proposed_guess) == expected_length,
                "proposed_guess": proposed_guess,
                "hard_violations": [],
                "soft_warnings": ["Parse error"],
                "confidence": 0.3
            }

        if "error" in result:
            result = {
                "valid": len(proposed_guess) == expected_length,
                "proposed_guess": proposed_guess,
                "hard_violations": [],
                "soft_warnings": [],
                "confidence": 0.5
            }

        return result

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent."""
        return self.validate_guess(
            proposed_guess=kwargs.get("proposed_guess", []),
            guess_history=kwargs.get("guess_history", []),
            analysis=kwargs.get("analysis", {}),
            num_pegs=kwargs.get("num_pegs", 4),
        )
