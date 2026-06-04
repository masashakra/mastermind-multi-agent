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

    def should_request_constraints(self) -> bool:
        """Decide if Strategist should REQUEST fresh constraints from Analyzer."""
        # If we haven't received constraints yet, we must request
        if not hasattr(self, 'last_constraints') or not self.last_constraints:
            return True
        return False  # Reuse cached constraints for now

    async def request_fresh_constraints(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """REQUEST fresh constraint analysis from Analyzer using bidirectional messaging."""
        try:
            response_data = await self.send_a2a_message(
                receiver_type="analyzer",
                action="analyze",
                payload={
                    "clarification": "Please provide constraint analysis for strategy",
                    "last_guess": game_state.get("last_guess", []),
                    "feedback": game_state.get("feedback", {}),
                    "guess_history": game_state.get("guess_history", []),
                },
                is_question=True  # WAIT for response
            )

            if response_data and response_data.get("payload"):
                self.last_constraints = response_data["payload"]
                return response_data["payload"]
        except Exception as e:
            print(f"[Strategist] Error requesting constraints: {e}")

        return self.last_constraints if hasattr(self, 'last_constraints') else {}

    def propose_strategy(
        self,
        guess_history: List[Dict],
        difficulty: str,
        available_colors: List[str] = None,
        analysis: str = "",
        impossible_colors: List[str] = None,
        confirmed_colors: List[str] = None,
        locked_positions: List[Dict] = None,
        misplaced_colors: List[Dict] = None,
    ) -> Dict[str, Any]:
        """Propose strategy based on game state AND full constraint analysis from Analyzer.
        Uses multi-turn conversation so the Strategist builds on its own prior reasoning.
        """
        round_num        = len(guess_history) + 1
        impossible_colors = impossible_colors or []
        confirmed_colors  = confirmed_colors  or []
        locked_positions  = locked_positions  or []
        misplaced_colors  = misplaced_colors  or []
        available_colors  = available_colors  or []

        # Colors still viable (not impossible, not yet confirmed)
        untested = [c for c in available_colors
                    if c not in impossible_colors and c not in confirmed_colors]

        # Format locked positions clearly
        locked_str = ", ".join(
            f"position {l.get('position')}={l.get('color')}" for l in locked_positions
        ) if locked_positions else "none"

        # Format misplaced colors clearly
        misplaced_str = ", ".join(
            f"{m.get('color')} (not at {m.get('wrong_positions',[])})"
            for m in misplaced_colors
        ) if misplaced_colors else "none"

        system_prompt = """You are the Strategist in a Mastermind game.
Your role: receive constraint analysis from the Analyzer and produce a SPECIFIC, ACTIONABLE
strategy that tells the Proposer exactly which colors to use and where.

You remember all prior rounds via this conversation history.
Build on your previous strategy — do not start from scratch each round."""

        user_message = f"""ROUND {round_num} of 8  |  Difficulty: {difficulty}
Rounds remaining: {8 - round_num}

CONSTRAINTS FROM ANALYZER:
  Impossible colors (never use): {impossible_colors if impossible_colors else 'none identified yet'}
  Confirmed colors (must be in secret): {confirmed_colors if confirmed_colors else 'none identified yet'}
  Locked positions (fixed): {locked_str}
  Misplaced colors (present but wrong position): {misplaced_str}
  Untested colors (not yet ruled out): {untested}
  Analyzer summary: {analysis[:300] if analysis else 'no summary yet'}

GUESS HISTORY:
{chr(10).join(f"  R{g['round']}: {g['guess']} -> {g['feedback']['correct_pegs']}p {g['feedback']['correct_positions']}pos" for g in guess_history) if guess_history else '  No guesses yet'}

Based on the constraints above, provide a SPECIFIC strategy for this round.
Name the EXACT colors the Proposer should prioritise and which positions to target.

OUTPUT (JSON ONLY — choose phase from exactly one of the four options below):
{{
  "phase": "EXPLORATION",
  "strategy": "Specific instruction naming exact colors and positions — e.g. Place red at pos0, blue at pos3, test yellow at pos1, avoid white/green/black",
  "colors_to_use": ["exact", "colors", "to", "guess"],
  "positions_to_test": {{"0": "color", "1": "color", "2": "color", "3": "color"}},
  "colors_to_avoid": ["impossible", "colors"],
  "confidence": 0.85,
  "reasoning": "Why this strategy given current constraints and rounds remaining"
}}

Phase must be ONE of: EXPLORATION, CONSTRAINT_BUILDING, REFINEMENT, CONFIRMATION"""

        response = self.call_llm_conversation(system_prompt, user_message)
        result   = self.parse_json_response(response)

        if "error" in result or "strategy" not in result:
            result = {
                "phase": "EXPLORATION",
                "strategy": f"Test untested colors {untested[:4]}. Avoid {impossible_colors}.",
                "colors_to_use": untested[:4] if untested else confirmed_colors[:4],
                "colors_to_avoid": impossible_colors,
                "confidence": 0.4,
                "reasoning": "Fallback — constraint data insufficient"
            }

        return result

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process method for abstract base class compliance."""
        return self.propose_strategy(
            guess_history     = state.get("guess_history", []),
            difficulty        = state.get("difficulty", "medium"),
            available_colors  = state.get("available_colors", []),
            analysis          = state.get("analysis", ""),
            impossible_colors = state.get("impossible_colors", []),
            confirmed_colors  = state.get("confirmed_colors", []),
            locked_positions  = state.get("locked_positions", []),
            misplaced_colors  = state.get("misplaced_colors", []),
        )
