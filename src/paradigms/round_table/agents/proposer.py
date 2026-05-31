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
        """Generate a guess respecting constraints."""
        role_context = self.get_role_system_prompt()

        colors_str = ", ".join(available_colors)
        prev_str = "\n".join([str(g) for g in previous_guesses[-3:]]) if previous_guesses else "None"

        # Extract previously guessed color combos to avoid repeats
        prev_guesses_list = [g.get("guess", g) if isinstance(g, dict) else g for g in previous_guesses]

        prompt = f"""{role_context}

## YOUR TASK
Generate a NEW guess for Mastermind. You are trying to discover a secret code.

RULES:
- The secret code has exactly {num_pegs} color slots
- Colors can repeat
- You must use ONLY colors from the available list (exact case)
- DO NOT repeat a previous guess exactly
- Use the strategy and constraints to narrow down candidates

STRATEGY: {strategy}
CONSTRAINTS FROM ANALYSIS: {constraints_text}
AVAILABLE COLORS (use exact spelling): {colors_str}
PREVIOUS GUESSES (DO NOT repeat these):
{prev_str}

Think step by step:
1. What does the feedback from previous guesses tell us?
2. Which colors are eliminated? Which are confirmed?
3. Which positions are locked?
4. What new guess will give us the most information?

OUTPUT (JSON ONLY):
{{
  "proposed_guess": ["color1", "color2", "color3", "color4"],
  "reasoning": "Why these colors based on constraints"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result or "proposed_guess" not in result:
            # Fallback: pick randomly from available colors, avoiding previous guesses
            import random
            shuffled = available_colors.copy()
            random.shuffle(shuffled)
            fallback_guess = [random.choice(available_colors) for _ in range(num_pegs)]
            # Make sure fallback is not a repeat of a previous guess
            while fallback_guess in prev_guesses_list and len(prev_guesses_list) < 50:
                fallback_guess = [random.choice(available_colors) for _ in range(num_pegs)]
            result = {"proposed_guess": fallback_guess, "reasoning": "Random fallback (LLM parse failed)"}

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
