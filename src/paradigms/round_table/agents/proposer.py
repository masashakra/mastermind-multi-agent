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
                      knowledge_base: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a guess respecting accumulated constraints."""
        import random
        role_context = self.get_role_system_prompt()

        colors_str = ", ".join(available_colors)
        prev_guesses_list = [g.get("guess", g) if isinstance(g, dict) else g for g in previous_guesses]
        prev_str = "\n".join(
            f"  Round {i+1}: {g.get('guess', g)} → pegs={g['feedback'].get('correct_pegs',0)} pos={g['feedback'].get('correct_positions',0)}"
            if isinstance(g, dict) else f"  {g}"
            for i, g in enumerate(previous_guesses)
        ) if previous_guesses else "  None yet"

        # Format knowledge base for prompt
        kb = knowledge_base or {}
        kb_text = ""
        if kb:
            kb_text = f"""
ACCUMULATED KNOWLEDGE (HARD FACTS — you MUST respect these):
  ✗ Colors NOT in secret: {kb.get('impossible_colors', [])}
  ✓ Colors confirmed IN secret: {kb.get('confirmed_colors', [])}
  🔒 Locked positions: {kb.get('locked_positions', {})}
  🔢 Min color counts: {kb.get('min_color_counts', {})}
  Constraints:
{chr(10).join('    • ' + c for c in kb.get('constraints', [])[-8:])}
"""

        prompt = f"""{role_context}

## YOUR TASK — Propose Next Guess

You are playing Mastermind. Generate the BEST next guess to find the secret code.

RULES:
- Exactly {num_pegs} color slots, colors can repeat
- Use ONLY colors from: {colors_str}
- DO NOT repeat a previous guess
- Respect ALL constraints in the knowledge base
{kb_text}
STRATEGY: {strategy}
ADDITIONAL CONSTRAINTS: {constraints_text}

ALL PREVIOUS GUESSES:
{prev_str}

THINK STEP BY STEP:
1. Which colors are impossible? (never guess them)
2. Which colors MUST appear? (always include confirmed colors)
3. Which positions are locked? (keep those fixed)
4. What color count requirements do we have? (e.g. black ≥ 2)
5. What guess best narrows down the remaining uncertainty?

OUTPUT (JSON ONLY):
{{
  "proposed_guess": ["color1", "color2", "color3", "color4"],
  "reasoning": "Why this guess based on constraints"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result or "proposed_guess" not in result:
            # Smart fallback: respect known constraints
            impossible = kb.get("impossible_colors", [])
            locked = kb.get("locked_positions", {})
            safe_colors = [c for c in available_colors if c not in impossible] or available_colors

            fallback_guess = []
            for i in range(num_pegs):
                if str(i) in locked or i in locked:
                    fallback_guess.append(locked.get(str(i), locked.get(i, random.choice(safe_colors))))
                else:
                    fallback_guess.append(random.choice(safe_colors))

            # Avoid repeating a previous guess
            attempts = 0
            while fallback_guess in prev_guesses_list and attempts < 20:
                fallback_guess = [
                    locked.get(str(i), locked.get(i, random.choice(safe_colors)))
                    for i in range(num_pegs)
                ]
                attempts += 1

            result = {"proposed_guess": fallback_guess, "reasoning": "Constraint-aware random fallback"}

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
