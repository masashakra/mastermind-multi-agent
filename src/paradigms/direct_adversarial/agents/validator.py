# Boss-Worker Validator Agent
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
    "agent_id": "validator_direct_adversarial",
    "paradigm": "direct_adversarial",
}

class ValidatorAgent(BaseAgent):
    """Boss-Worker Validator Agent"""

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

    def validate_guess(self, guess: List[str], available_colors: List[str],
                      expected_length: int, previous_guesses: List[List[str]],
                      constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Validate guess against constraints."""
        role_context = self.get_role_system_prompt()

        colors_str = ", ".join(available_colors)
        prev_str = "\n".join([str(g) for g in previous_guesses[-3:]]) if previous_guesses else "None"

        prompt = f"""{role_context}

## YOUR TASK
Validate the proposed guess in Boss-Worker paradigm.

PROPOSED GUESS: {guess}
AVAILABLE COLORS: {colors_str}
EXPECTED LENGTH: {expected_length}
CONSTRAINTS: {constraints}
PREVIOUS GUESSES (last 3):
{prev_str}

Check for hard and soft constraint violations.

OUTPUT (JSON ONLY):
{{
  "valid": true/false,
  "hard_violations": [],
  "soft_warnings": []
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result:
            result = {"valid": len(guess) == expected_length, "hard_violations": [], "soft_warnings": []}

        return result
