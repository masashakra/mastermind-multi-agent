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
        """Analyze all guess history and extract constraints.

        Args:
            last_guess: Colors in the most recent guess
            feedback: {"correct_pegs": int, "correct_positions": int}
            previous_guesses: Full guess history (all rounds)

        Returns:
            Constraint analysis dictionary
        """
        correct_pegs = feedback.get("correct_pegs", 0)
        correct_positions = feedback.get("correct_positions", 0)

        # Format full history — every round, not just recent ones
        history_text = "No previous guesses yet." if not previous_guesses else "\n".join(
            f"  Round {i+1}: {g.get('guess')} → pegs={g['feedback'].get('correct_pegs',0)}  pos={g['feedback'].get('correct_positions',0)}"
            for i, g in enumerate(previous_guesses)
        )

        role_context = self.get_role_system_prompt()

        prompt = f"""{role_context}

## YOUR TASK — Analyze Mastermind Feedback

You are the Analyzer. Study ALL previous guesses and their feedback, then extract
every constraint you can to help the team guess the secret code.

ALL GUESSES SO FAR:
{history_text}

LATEST GUESS: {last_guess}
LATEST FEEDBACK: {correct_pegs} correct colors (pegs), {correct_positions} correct positions

MASTERMIND RULES:
- correct_pegs = how many colors from the guess exist in the secret (any position)
- correct_positions = how many colors are in the exact right position
- If pegs=0 → NONE of those colors are in the secret
- (pegs - positions) = colors that exist but are in the wrong position
- Colors can repeat in the secret

Derive ALL constraints across every round:
1. Which colors are definitely NOT in the secret? (pegs=0 rounds)
2. Which colors ARE in the secret? (appeared when pegs>0)
3. Which positions are locked? (consistent across rounds)
4. What does each feedback tell us about color counts?

OUTPUT (JSON ONLY):
{{
  "analysis": "Summary of what we know so far",
  "impossible_colors": ["colors definitely not in secret"],
  "confirmed_colors": ["colors definitely in secret"],
  "locked_positions": [{{"position": 0, "color": "white"}}],
  "constraints": ["specific constraint 1", "specific constraint 2"],
  "confidence": 0.8
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result or "analysis" not in result:
            result = {
                "impossible_colors": [],
                "confirmed_colors": [],
                "locked_positions": [],
                "constraints": [],
                "analysis": "Failed to parse feedback",
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
