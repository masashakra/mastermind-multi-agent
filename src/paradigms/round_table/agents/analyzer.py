# Boss-Worker Analyzer Agent
# Interprets feedback and extracts constraints
# Boss-Worker specific implementation with paradigm-specific prompts

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.agent_card import ANALYZER_CARD
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType


# Agent Card for Boss-Worker Analyzer (OpenAPI format)
AGENT_CARD = {
    **ANALYZER_CARD,
    "agent_id": "analyzer_round_table",
    "paradigm": "round_table",
    "description": "Analyzer for Boss-Worker paradigm. Takes directions from Boss, extracts constraints from feedback.",
}


class AnalyzerAgent(BaseAgent):
    """Boss-Worker Analyzer Agent

    Interprets feedback and extracts constraints.
    Receives assignments from Boss, reports back to Boss with analysis.
    """

    def __init__(
        self,
        provider: str = "ollama",
        comm_layer: Optional[A2ACommunicationLayer] = None,
        role: Optional[AgentRole] = None,
        paradigm: Optional[ParadigmType] = None,
        team_members: Optional[List[str]] = None,
        can_communicate: bool = True,
        constraints_owned: Optional[List[str]] = None,
        registry_url: Optional[str] = None,
    ):
        super().__init__(
            name="Analyzer_RoundTable",
            provider=provider,
            comm_layer=comm_layer,
            role=role or AgentRole.ANALYZER,
            paradigm=paradigm or ParadigmType.ROUND_TABLE,
            team_members=team_members or ["strategist", "proposer", "validator"],
            can_communicate=can_communicate,
            constraints_owned=constraints_owned or ["Constraint extraction"],
            registry_url=registry_url,
        )

    def analyze_feedback(
        self,
        last_guess: List[str],
        feedback: Dict[str, int],
        previous_guesses: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze latest feedback using persistent conversation history.

        The agent remembers all its prior reasoning via self.conversation —
        it only needs to see the NEW round's info each time.
        """
        correct_pegs = feedback.get("correct_pegs", 0)
        correct_positions = feedback.get("correct_positions", 0)
        round_num = len(previous_guesses or []) + 1

        system_prompt = f"""You are the Analyzer agent in a Mastermind game.
Your role: extract constraints from every guess+feedback pair and accumulate knowledge across rounds.

MASTERMIND RULES:
- correct_pegs = total colors in the guess that exist in the secret (any position)
- correct_positions = colors in the EXACT right position
- If pegs=0 → NONE of those colors are in the secret
- pegs - positions = colors that exist but are in the WRONG position
- Colors CAN repeat in the secret

You have a perfect memory of all your prior analysis above. Build on it — never contradict what you already know."""

        user_message = f"""Round {round_num} result:
Guess: {last_guess}
Feedback: {correct_pegs} correct colors (pegs), {correct_positions} correct positions

Based on ALL rounds so far (including your prior analysis), what do we now know?
What new constraints does this feedback add?

OUTPUT (JSON ONLY):
{{
  "analysis": "What this round tells us + cumulative knowledge",
  "impossible_colors": ["all colors confirmed absent from secret"],
  "confirmed_colors": ["all colors confirmed present in secret"],
  "locked_positions": [{{"position": 0, "color": "white"}}],
  "constraints": ["every constraint we know so far"],
  "confidence": 0.9
}}"""

        response = self.call_llm_conversation(system_prompt, user_message)
        result = self.parse_json_response(response)

        if "error" in result or "analysis" not in result:
            result = {
                "impossible_colors": [],
                "confirmed_colors": [],
                "locked_positions": [],
                "constraints": [],
                "analysis": "Parse failed",
                "confidence": 0.0,
            }

        return result

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process method for abstract base class compliance."""
        return self.analyze_feedback(
            state.get("last_guess", []),
            state.get("last_feedback", {}),
            state.get("guess_history", [])
        )
