# Coopetition Centralized Proposer Agent
# Proposes the next guess based on strategy and constraints
# Communicates with teammates via A2A

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from paradigms.coopetition_centralized.agents.base_agent import BaseAgent
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType


class ProposerAgent(BaseAgent):
    """Coopetition Centralized Proposer Agent

    Proposes the next guess based on team's strategy and constraints.
    Communicates with Analyzer and Strategist on the same team via A2A.
    """

    def __init__(
        self,
        team: str,
        provider: str = "deepseek",
        comm_layer: Optional[A2ACommunicationLayer] = None,
        paradigm: Optional[ParadigmType] = None,
        registry_url: Optional[str] = None,
    ):
        self.team = team
        super().__init__(
            name=f"Proposer_{team}",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.PROPOSER,
            paradigm=paradigm or ParadigmType.COOPETITION_CENTRALIZED,
            team_members=[f"analyzer_strategist_{team.lower()}"],
            can_communicate=True,
            constraints_owned=["Guess generation"],
            registry_url=registry_url,
        )

    def propose_guess(
        self,
        strategy: Dict[str, Any],
        constraints: Dict[str, Any],
        shared_knowledge: List[Dict[str, Any]] = None,
        available_colors: List[str] = None,
    ) -> Dict[str, Any]:
        """Propose a guess based on strategy and constraints."""

        if not available_colors:
            available_colors = ["red", "blue", "green", "yellow", "white", "black", "orange", "purple"]

        system_prompt = f"""You are the Proposer on Team {self.team}. You propose the next guess.

MASTERMIND RULES:
- Guess must be 5 colors from 8 available
- Colors can repeat
- Use constraints and strategy to guide selection

TASK:
Given the strategy and constraints, propose the best guess with:
- The actual guess (5 colors)
- Rationale (why this guess follows the strategy)
- Confidence (0-100%)
- Expected information gain

Format as JSON:
{{
  "guess": ["color1", "color2", "color3", "color4", "color5"],
  "rationale": "detailed explanation of why this guess",
  "confidence": 0-100,
  "expected_info_gain": "what will we learn from this guess?",
  "aligns_with_strategy": true|false,
  "alternatives_considered": ["alt1", "alt2"]
}}"""

        user_message = f"""Propose a guess:
Strategy: {strategy}
Constraints: {constraints}
Available colors: {available_colors}
Shared knowledge: {shared_knowledge or []}"""

        try:
            response = self.call_llm_conversation(system_prompt, user_message)
            proposal = self.parse_json_response(response)

            # Validate guess
            guess = proposal.get("guess", [])
            if len(guess) != 5 or not all(c in available_colors for c in guess):
                proposal["validation_warning"] = "Guess format may be invalid"

            return proposal
        except Exception as e:
            print(f"[{self.name}] Error proposing guess: {e}")
            return {
                "error": str(e),
                "guess": available_colors[:5],
                "rationale": "Error generating proposal",
                "confidence": 0,
                "expected_info_gain": "",
                "aligns_with_strategy": False,
                "alternatives_considered": [],
            }

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent abstract class."""
        action = kwargs.get("action")
        if action == "propose_guess":
            return self.propose_guess(
                strategy=kwargs.get("strategy", {}),
                constraints=kwargs.get("constraints", {}),
                shared_knowledge=kwargs.get("shared_knowledge", []),
                available_colors=kwargs.get("available_colors"),
            )
        return {"error": f"Unknown action: {action}"}

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming A2A message."""
        action = message.get("action")

        if action == "propose_guess":
            payload = message.get("payload", {})
            result = self.propose_guess(
                strategy=payload.get("strategy", {}),
                constraints=payload.get("constraints", {}),
                shared_knowledge=payload.get("shared_knowledge", []),
                available_colors=payload.get("available_colors"),
            )
            return {"status": "ok", "result": result}

        return {"status": "error", "message": f"Unknown action: {action}"}
