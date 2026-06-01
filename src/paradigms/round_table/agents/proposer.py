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
        """Generate a guess using persistent conversation history.

        The agent remembers all its prior guesses and reasoning —
        it only needs to see the NEW round's context each time.
        """
        import random

        prev_guesses_list = [g.get("guess", g) if isinstance(g, dict) else g for g in previous_guesses]
        round_num = len(previous_guesses) + 1

        system_prompt = f"""You are the Proposer agent in a Mastermind game.
Your role: propose the best next guess based on all feedback so far.

RULES:
- Secret code has exactly {num_pegs} color slots, colors can repeat
- Available colors: {', '.join(available_colors)}
- NEVER repeat a previous guess exactly
- Use ALL feedback and your prior reasoning to make the best next guess

You remember all your previous guesses and the reasoning behind them above."""

        # Format previous guesses for this round's context
        prev_str = "\n".join(
            f"  Round {i+1}: {g.get('guess', g)} → pegs={g['feedback'].get('correct_pegs',0)}  pos={g['feedback'].get('correct_positions',0)}"
            if isinstance(g, dict) else f"  {g}"
            for i, g in enumerate(previous_guesses)
        ) if previous_guesses else "  No guesses yet — this is round 1"

        user_message = f"""Round {round_num} — propose your next guess.

Strategy from team: {strategy}
Analysis from Analyzer: {constraints_text}

All guesses so far:
{prev_str}

Based on your memory of prior rounds and this analysis, what is the BEST next guess?
Think step by step about what the feedback tells you, then commit to a guess.

OUTPUT (JSON ONLY):
{{
  "proposed_guess": ["color1", "color2", "color3", "color4"],
  "reasoning": "Step by step: what I know, what I'm testing"
}}"""

        response = self.call_llm_conversation(system_prompt, user_message)
        result = self.parse_json_response(response)

        if "error" in result or "proposed_guess" not in result:
            guess = [random.choice(available_colors) for _ in range(num_pegs)]
            result = {"proposed_guess": guess, "reasoning": "Random fallback"}

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
