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
    ):
        super().__init__(
            name="Analyzer_BossWorker",
            provider=provider,
            comm_layer=comm_layer,
            role=role or AgentRole.ANALYZER,
            paradigm=paradigm or ParadigmType.BOSS_WORKER,
            team_members=team_members or ["boss", "strategist", "proposer", "validator"],
            can_communicate=can_communicate,
            constraints_owned=constraints_owned or ["Constraint extraction"],
        )

    def analyze_feedback(
        self,
        last_guess: List[str],
        feedback: Dict[str, int],
        previous_guesses: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze feedback and extract constraints.

        BOSS-WORKER SPECIFIC: Takes direction from Boss, reports findings.

        Args:
            last_guess: List of colors in last guess
            feedback: {"correct_pegs": int, "correct_positions": int}
            previous_guesses: Optional list of previous guesses

        Returns:
            Constraint analysis dictionary
        """
        correct_pegs = feedback.get("correct_pegs", 0)
        correct_positions = feedback.get("correct_positions", 0)

        # Format history
        history_text = "No previous guesses" if not previous_guesses else "\n".join(
            f"Round {i+1}: {g.get('guess')} → {g.get('feedback')}"
            for i, g in enumerate(previous_guesses[-3:])  # Last 3 rounds
        )

        # Get explicit role context (Adimulam et al. 2026)
        role_context = self.get_role_system_prompt()

        # BOSS-WORKER SPECIFIC PROMPT
        prompt = f"""{role_context}

## YOUR TASK
You are working in a Boss-Worker paradigm. The Boss has assigned you to analyze the latest feedback
and extract constraints. You will report your findings back to the Boss.

CONSTRAINT EXTRACTION LOGIC (Think Step-by-Step):

Step 1: IDENTIFY EXISTING COLORS
  - How many total colors exist in code? (from correct_pegs count)
  - Which colors from the guess might be the ones that exist?

Step 2: IDENTIFY LOCKED POSITIONS
  - How many positions are correct? (from correct_positions count)
  - Which positions changed from last round?
  - A position is LOCKED only if: color is in guess AND feedback increased

Step 3: IDENTIFY MISPLACED COLORS
  - If we have more correct_pegs than correct_positions: some colors exist but are misplaced
  - Which colors from this guess might be misplaced?

Step 4: IDENTIFY IMPOSSIBLE COLORS
  - If a color was in the guess but didn't increase either count: that color doesn't exist

Step 5: CONFIDENCE ASSESSMENT
  - How certain are we of each constraint?

WORKED EXAMPLE:
Last Guess: [red, blue, green, yellow]
Feedback: 2 colors exist, 1 correct position
Previous: [red, blue, white, black] → 1 color exists, 0 correct

Reasoning:
  Step 1: 2 colors exist total. From last round 1 color existed (red or blue).
          This round has 2, so one new color was found. New colors are green/yellow.
  Step 2: 1 position correct. We had 0 before, so we just locked 1 position.
          Red at 0, blue at 1, green at 2, yellow at 3 are all new positions.
          One of these 4 positions is now locked.
  Step 3: Misplaced = correct_pegs - correct_positions = 2 - 1 = 1
          One color exists but is in wrong position.
  Step 4: White and black were in previous guess but didn't improve, so IMPOSSIBLE.
  Step 5: Medium confidence (1 round of data is limited).

Constraints:
  - Correct positions: [{{"position": ?, "color": ?}}] (1 of 4 positions locked)
  - Misplaced colors: [one of red/blue/green/yellow]
  - Impossible colors: [white, black]
  - Analysis: Found 2 colors, 1 locked. Need to identify which position and find other 2 colors.

LAST GUESS: {last_guess}
FEEDBACK: {correct_pegs} total colors exist, {correct_positions} in correct positions

PREVIOUS GUESSES (last 3 rounds):
{history_text}

OUTPUT (JSON ONLY):
{{
  "reasoning_steps": [
    "Step 1 Colors: [analysis]",
    "Step 2 Locks: [analysis]",
    "Step 3 Misplaced: [analysis]",
    "Step 4 Impossible: [analysis]",
    "Step 5 Confidence: [assessment]"
  ],
  "correct_positions": [
    {{"position": 0, "color": "red"}}
  ],
  "correct_colors_wrong_position": ["green", "yellow"],
  "impossible_colors": ["blue", "white"],
  "constraints": [
    "Position 0: red (LOCKED)",
    "green exists but not at position 2",
    "yellow exists but not at position 3",
    "blue is IMPOSSIBLE",
    "white is IMPOSSIBLE"
  ],
  "analysis": "Found 3 colors (red locked, green/yellow misplaced), eliminated 2",
  "confidence": 0.85
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        # Fallback if parsing fails
        if "error" in result:
            result = {
                "correct_positions": [],
                "correct_colors_wrong_position": [],
                "impossible_colors": [],
                "constraints": [],
                "analysis": "Failed to parse feedback",
                "confidence": 0.0,
                "reasoning_steps": ["Error parsing response"]
            }

        return result
