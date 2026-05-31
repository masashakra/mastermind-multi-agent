# Boss-Worker Proposer Agent
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import List, Dict, Any, Optional
from base.base_agent import BaseAgent
from base.agent_card import PROPOSER_CARD
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType

AGENT_CARD = {
    **PROPOSER_CARD,
    "agent_id": "proposer_moderator_mediated",
    "paradigm": "moderator_mediated",
}

class ProposerAgent(BaseAgent):
    """Boss-Worker Proposer Agent"""

    def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None,
                 role: Optional[AgentRole] = None, paradigm: Optional[ParadigmType] = None,
                 team_members: Optional[List[str]] = None, can_communicate: bool = True,
                 constraints_owned: Optional[List[str]] = None):
        super().__init__(
            name="Proposer_BossWorker", provider=provider, comm_layer=comm_layer,
            role=role or AgentRole.PROPOSER, paradigm=paradigm or ParadigmType.BOSS_WORKER,
            team_members=team_members or ["boss", "analyzer", "strategist", "validator"],
            can_communicate=can_communicate, constraints_owned=constraints_owned or ["Constraint-respecting guess generation"],
        )

    def propose_guess(self, strategy: str, constraints_text: str, available_colors: List[str],
                      num_pegs: int, previous_guesses: List[List[str]]) -> Dict[str, Any]:
        """Generate a guess respecting constraints."""
        role_context = self.get_role_system_prompt()

        colors_str = ", ".join(available_colors)
        prev_str = "\n".join([str(g) for g in previous_guesses[-3:]]) if previous_guesses else "None"

        prompt = f"""{role_context}

## YOUR TASK
Generate a guess respecting all constraints in Boss-Worker paradigm.

STRATEGY: {strategy}
CONSTRAINTS: {constraints_text}
AVAILABLE COLORS: {colors_str}
NUM PEGS: {num_pegs}
PREVIOUS GUESSES (last 3):
{prev_str}

Generate a new guess that respects all constraints.

OUTPUT (JSON ONLY):
{{
  "proposed_guess": [list of colors],
  "reasoning": "[Why these colors]"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result:
            result = {"proposed_guess": available_colors[:num_pegs], "reasoning": "Default guess"}

        return result
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process method for abstract base class compliance."""
        return self.propose_guess(
            state.get("strategy", "explore"),
            state.get("constraints", ""),
            state.get("available_colors", []),
            state.get("num_pegs", 4),
            state.get("guess_history", [])
        )
