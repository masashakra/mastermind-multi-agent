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
    "agent_id": "proposer_round_table",
    "paradigm": "round_table",
}

class ProposerAgent(BaseAgent):
    """Boss-Worker Proposer Agent"""

    def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None,
                 role: Optional[AgentRole] = None, paradigm: Optional[ParadigmType] = None,
                 team_members: Optional[List[str]] = None, can_communicate: bool = True,
                 constraints_owned: Optional[List[str]] = None, registry_url: Optional[str] = None):
        super().__init__(
            name="Proposer_RoundTable", provider=provider, comm_layer=comm_layer,
            role=role or AgentRole.PROPOSER, paradigm=paradigm or ParadigmType.ROUND_TABLE,
            team_members=team_members or ["analyzer", "strategist", "validator"],
            can_communicate=can_communicate, constraints_owned=constraints_owned or ["Constraint-respecting guess generation"],
            registry_url=registry_url,
        )

    def propose_guess(self, strategy: str, constraints_text: str, available_colors: List[str],
                      num_pegs: int, previous_guesses: List[List[str]]) -> Dict[str, Any]:
        """Generate a guess respecting all feedback so far."""
        import random
        role_context = self.get_role_system_prompt()

        colors_str = ", ".join(available_colors)
        prev_guesses_list = [g.get("guess", g) if isinstance(g, dict) else g for g in previous_guesses]
        prev_str = "\n".join(
            f"  Round {i+1}: {g.get('guess', g)} → pegs={g['feedback'].get('correct_pegs',0)}  pos={g['feedback'].get('correct_positions',0)}"
            if isinstance(g, dict) else f"  {g}"
            for i, g in enumerate(previous_guesses)
        ) if previous_guesses else "  None yet"

        prompt = f"""{role_context}

## YOUR TASK — Propose Next Guess

You are playing Mastermind. Use ALL previous guesses and feedback to generate the best next guess.

RULES:
- Exactly {num_pegs} color slots, colors can repeat
- Use ONLY colors from: {colors_str}
- DO NOT repeat a previous guess exactly

STRATEGY FROM TEAM: {strategy}
CONSTRAINTS FROM ANALYZER: {constraints_text}

ALL PREVIOUS GUESSES AND FEEDBACK:
{prev_str}

THINK STEP BY STEP:
1. Which colors are eliminated? (appeared in a round with pegs=0)
2. Which colors are confirmed? (appeared in rounds with pegs>0)
3. Which positions look locked? (same color got correct_positions in multiple rounds)
4. What new guess avoids duplicates and tests new information?

OUTPUT (JSON ONLY):
{{
  "proposed_guess": ["color1", "color2", "color3", "color4"],
  "reasoning": "Why this guess based on the history"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result or "proposed_guess" not in result:
            # Random fallback avoiding previous guesses
            fallback_guess = [random.choice(available_colors) for _ in range(num_pegs)]
            attempts = 0
            while fallback_guess in prev_guesses_list and attempts < 20:
                fallback_guess = [random.choice(available_colors) for _ in range(num_pegs)]
                attempts += 1
            result = {"proposed_guess": fallback_guess, "reasoning": "Random fallback"}

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
