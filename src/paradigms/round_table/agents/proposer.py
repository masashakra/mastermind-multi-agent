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
Your role: propose the BEST next guess by systematically using constraint information.

RULES:
- Secret code: exactly {num_pegs} color slots, colors CAN repeat
- Available colors: {', '.join(available_colors)}
- NEVER repeat any previous guess
- Every color that appears must be justified by constraints

GUESS GENERATION STEPS:
1. REVIEW CONSTRAINTS: What do we know?
   - Which positions are LOCKED (confirmed color at position)?
   - Which colors are IMPOSSIBLE (definitely not in secret)?
   - Which colors are CONFIRMED but MISPLACED (exist but wrong position)?

2. BUILD CANDIDATE COLORS: For each position, which colors are possible?
   - Position 0: {{colors that don't violate constraints}}
   - Position 1: {{colors that don't violate constraints}}
   - etc.

3. APPLY STRATEGY: Based on strategy (exploration/refinement), pick colors:
   - EXPLORATION: Test untested colors
   - REFINEMENT: Test positions for confirmed-but-misplaced colors
   - CONFIRMATION: Lock down final positions

4. VALIDATE GUESS: Does this guess violate ANY constraints?
   - Check locked positions match exactly
   - Check no impossible colors are used
   - Check misplaced colors appear in different positions

5. FINALIZE: Commit to the guess

You remember all previous guesses and reasoning via conversation history."""

        # Format previous guesses for this round's context
        prev_str = "\n".join(
            f"  Round {i+1}: {g.get('guess', g)} → pegs={g['feedback'].get('correct_pegs',0)}  pos={g['feedback'].get('correct_positions',0)}"
            if isinstance(g, dict) else f"  {g}"
            for i, g in enumerate(previous_guesses)
        ) if previous_guesses else "  No guesses yet — this is round 1"

        user_message = f"""Round {round_num} — propose your next guess using systematic constraint reasoning.

CONSTRAINT ANALYSIS (from Analyzer):
{constraints_text}

STRATEGY GUIDANCE (from Strategist):
{strategy}

PRIOR GUESSES AND FEEDBACK:
{prev_str}

Now apply the 5-step process:
1. Review constraints from the analysis above
2. Build candidate colors for each position
3. Apply strategy (exploration vs refinement)
4. Validate the guess respects all constraints
5. Propose the guess

OUTPUT (JSON ONLY):
{{
  "proposed_guess": ["color1", "color2", "color3", "color4"],
  "constraint_check": {{
    "locked_positions_respected": true,
    "no_impossible_colors": true,
    "misplaced_colors_repositioned": true,
    "no_repeated_guess": true
  }},
  "reasoning": "Step-by-step reasoning through constraints: position 0 must be X because Y, position 1 must be Z because..."
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
