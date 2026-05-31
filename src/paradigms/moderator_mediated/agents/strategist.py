# Boss-Worker Strategist Agent
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import List, Dict, Any, Optional
from base.base_agent import BaseAgent
from base.agent_card import STRATEGIST_CARD
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType

AGENT_CARD = {
    **STRATEGIST_CARD,
    "agent_id": "strategist_moderator_mediated",
    "paradigm": "moderator_mediated",
}

class StrategistAgent(BaseAgent):
    """Boss-Worker Strategist Agent"""

    def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None,
                 role: Optional[AgentRole] = None, paradigm: Optional[ParadigmType] = None,
                 team_members: Optional[List[str]] = None, can_communicate: bool = True,
                 constraints_owned: Optional[List[str]] = None):
        super().__init__(
            name="Strategist_BossWorker", provider=provider, comm_layer=comm_layer,
            role=role or AgentRole.STRATEGIST, paradigm=paradigm or ParadigmType.BOSS_WORKER,
            team_members=team_members or ["boss", "analyzer", "proposer", "validator"],
            can_communicate=can_communicate, constraints_owned=constraints_owned or ["Strategy coherence"],
        )

    def propose_strategy(self, guess_history: List[Dict], difficulty: str) -> Dict[str, Any]:
        """Propose strategy based on game state."""
        role_context = self.get_role_system_prompt()

        history_summary = f"Round {len(guess_history) + 1}"
        if guess_history:
            history_summary += f": {len(guess_history)} guesses made"

        prompt = f"""{role_context}

## YOUR TASK
Propose high-level strategy for the next guess in Boss-Worker paradigm.

DIFFICULTY: {difficulty}
{history_summary}

Analyze the situation and propose a strategy (EXPLORATION, CONSTRAINT_BUILDING, REFINEMENT, or CONFIRMATION).

OUTPUT (JSON ONLY):
{{
  "phase": "EXPLORATION|CONSTRAINT_BUILDING|REFINEMENT|CONFIRMATION",
  "strategy": "[Brief strategy description]",
  "confidence": 0.8,
  "reasoning": "[Why this phase]"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result:
            result = {"phase": "EXPLORATION", "strategy": "Explore color space", "confidence": 0.5, "reasoning": "Default"}

        return result
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process method for abstract base class compliance."""
        return self.propose_strategy(
            state.get("guess_history", []),
            state.get("difficulty", "medium")
        )
