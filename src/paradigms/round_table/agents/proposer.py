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

    def should_request_constraints(self) -> bool:
        """Decide if Proposer should REQUEST fresh constraints from Analyzer.

        Uses LLM to determine if we need up-to-date constraint info or can rely on cached version.
        """
        # If we haven't received constraints yet, we must request
        if not hasattr(self, 'last_constraints') or not self.last_constraints:
            return True

        # Check if we have significant new information (more guesses since last constraints)
        try:
            num_new_guesses = len(self.conversation) - (self.last_constraint_round or 0)
            if num_new_guesses > 2:  # More than 2 new exchanges with constraints
                return True
        except:
            pass

        return False  # Reuse cached constraints

    async def request_fresh_constraints(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """REQUEST fresh constraint analysis from Analyzer using bidirectional messaging."""
        try:
            # Send REQUEST (is_question=True) to Analyzer
            response_data = await self.send_a2a_message(
                receiver_type="analyzer",
                action="analyze",
                payload={
                    "clarification": "Please provide updated constraint analysis",
                    "last_guess": game_state.get("last_guess", []),
                    "feedback": game_state.get("feedback", {}),
                    "guess_history": game_state.get("guess_history", []),
                },
                is_question=True  # WAIT for response
            )

            # Store the result and remember when we got it
            if response_data and response_data.get("payload"):
                self.last_constraints = response_data["payload"]
                self.last_constraint_round = len(self.conversation)
                return response_data["payload"]
        except Exception as e:
            print(f"[Proposer] Error requesting constraints: {e}")

        return self.last_constraints if hasattr(self, 'last_constraints') else {}

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
Your role: propose the BEST next guess by STRICTLY respecting constraints and using strategy.

CRITICAL RULES:
- Secret code: exactly {num_pegs} color slots, colors CAN repeat
- Available colors: {', '.join(available_colors)}
- NEVER repeat any previous guess
- NEVER use impossible colors (marked as impossible in constraint analysis)
- NEVER violate locked positions
- ALWAYS reposition misplaced colors to different positions
- Every color must either be: (A) tested, (B) locked, or (C) repositioned

CONSTRAINT-DRIVEN GUESS GENERATION:
1. PARSE CONSTRAINTS STRICTLY:
   - Extract EXACTLY which colors are impossible
   - Extract EXACTLY which positions are locked with their colors
   - Extract EXACTLY which colors must be repositioned
   - CRITICAL: Identify colors that appear MULTIPLE TIMES in the secret (duplicates!)

2. ELIMINATE OPTIONS:
   - Remove all impossible colors from consideration
   - For locked positions, fix those colors
   - For confirmed-but-misplaced colors, pick different positions
   - If a color must appear multiple times, plan all occurrences strategically

3. FILL REMAINING POSITIONS:
   - Use strategy guidance (exploration vs refinement)
   - If exploring: test untested colors AND test duplicate color placements
   - If refining: test confirmed colors in NEW position combinations
   - Generate DIVERSE guesses that try different position placements for duplicates

4. STRICT VALIDATION BEFORE FINALIZING:
   - Does every color in my guess respect constraints?
   - Are locked positions exactly matched?
   - Are misplaced colors in different positions?
   - Is this guess DIFFERENT from all past guesses? (NEVER resubmit!)
   - If colors repeat, did I test new position combinations?

5. OUTPUT: Commit to the guess with detailed reasoning

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
