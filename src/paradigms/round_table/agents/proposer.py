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
                      num_pegs: int, previous_guesses: List[List[str]],
                      constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a guess.  Code enforces constraints, LLM focuses on generation."""
        import random
        role_context = self.get_role_system_prompt()
        c = constraints or {}

        # ── Pre-computed hard facts from constraint solver ────────────────────
        impossible  = c.get("impossible_colors", [])
        confirmed   = c.get("confirmed_colors", [])
        locked      = c.get("locked_positions", {})   # {"0": "white", ...}
        min_counts  = c.get("min_color_counts", {})
        valid       = c.get("valid_colors", available_colors) or available_colors

        prev_guesses_list = [g.get("guess", g) if isinstance(g, dict) else g for g in previous_guesses]
        prev_str = "\n".join(
            f"  Round {i+1}: {g.get('guess', g)} → pegs={g['feedback'].get('correct_pegs',0)}  pos={g['feedback'].get('correct_positions',0)}"
            if isinstance(g, dict) else f"  {g}"
            for i, g in enumerate(previous_guesses)
        ) if previous_guesses else "  None yet"

        # Format locked positions clearly
        locked_str = ", ".join(f"pos {k}='{v}'" for k, v in locked.items()) if locked else "none yet"
        min_counts_str = ", ".join(f"{c}≥{n}" for c, n in min_counts.items()) if min_counts else "none"

        prompt = f"""{role_context}

## YOUR TASK — Propose Next Guess

You are playing Mastermind. The constraint engine has already computed these HARD FACTS
(mathematically guaranteed — do NOT violate them):

  ✗ Colors NOT in the secret:  {impossible if impossible else "none eliminated yet"}
  ✓ Colors IN the secret:      {confirmed if confirmed else "none confirmed yet"}
  🔒 Locked positions:         {locked_str}
  🔢 Min color counts:         {min_counts_str}
  ✅ Colors you CAN use:       {valid}

STRATEGY FROM TEAM: {strategy}
ADDITIONAL ANALYSIS: {constraints_text}

ALL PREVIOUS GUESSES:
{prev_str}

Generate a guess with exactly {num_pegs} slots using only valid colors.
Do NOT use impossible colors.  Keep locked positions fixed.
Include confirmed colors at least the minimum number of times.
Do NOT repeat a previous guess.

OUTPUT (JSON ONLY):
{{
  "proposed_guess": ["color1", "color2", "color3", "color4"],
  "reasoning": "Why this guess"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result or "proposed_guess" not in result:
            # Fallback: random from valid colors
            guess = [random.choice(valid) for _ in range(num_pegs)]
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
