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
    "agent_id": "strategist_round_table",
    "paradigm": "round_table",
}

class StrategistAgent(BaseAgent):
    """Boss-Worker Strategist Agent"""

    def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None,
                 role: Optional[AgentRole] = None, paradigm: Optional[ParadigmType] = None,
                 team_members: Optional[List[str]] = None, can_communicate: bool = True,
                 constraints_owned: Optional[List[str]] = None, registry_url: Optional[str] = None):
        super().__init__(
            name="Strategist_RoundTable", provider=provider, comm_layer=comm_layer,
            role=role or AgentRole.STRATEGIST, paradigm=paradigm or ParadigmType.ROUND_TABLE,
            team_members=team_members or ["analyzer", "proposer", "validator"],
            can_communicate=can_communicate, constraints_owned=constraints_owned or ["Strategy coherence"],
            registry_url=registry_url,
        )

    def propose_strategy(
        self,
        guess_history: List[Dict],
        difficulty: str,
        analysis: str = "",
        impossible_colors: List[str] = None,
        locked_positions: List[Dict] = None
    ) -> Dict[str, Any]:
        """Propose strategy based on game state AND constraint analysis from Analyzer."""
        round_num = len(guess_history) + 1

        # Build constraint context
        constraint_context = ""
        if impossible_colors:
            constraint_context += f"\nImpossible colors: {impossible_colors}"
        if locked_positions:
            constraint_context += f"\nLocked positions: {locked_positions}"
        if analysis:
            constraint_context += f"\n\nAnalyzer's constraint analysis:\n{analysis}"

        prompt = f"""You are the Strategist in a Mastermind game.
Your role: Based on constraint analysis, recommend the best strategy for the next guess.

DIFFICULTY: {difficulty}
ROUND: {round_num}
GUESSES SO FAR: {len(guess_history)}

CURRENT CONSTRAINTS:
{constraint_context if constraint_context else "No constraints yet (first round)"}

STRATEGY PHASES:
- EXPLORATION: Test untested colors to discover what's in the secret
- CONSTRAINT_BUILDING: Use feedback to narrow down which colors exist
- REFINEMENT: Test positions for colors we know exist
- CONFIRMATION: Lock down the final positions

Given the constraints above, what's the optimal next strategy?
- Which phase are we in?
- What should the Proposer focus on testing?
- Why is this the best approach now?

OUTPUT (JSON ONLY):
{{
  "phase": "EXPLORATION|CONSTRAINT_BUILDING|REFINEMENT|CONFIRMATION",
  "strategy": "Specific guidance for next guess: test these color positions, avoid these colors, etc.",
  "confidence": 0.85,
  "reasoning": "Why this phase is optimal given current constraints"
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
