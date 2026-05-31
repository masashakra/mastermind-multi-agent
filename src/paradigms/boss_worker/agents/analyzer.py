# Boss-Worker Analyzer Agent
# Fully autonomous LLM-based constraint extraction with state tracking
# Interprets feedback and extracts constraints

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
    "agent_id": "analyzer_boss_worker",
    "paradigm": "boss_worker",
    "description": "Analyzer for Boss-Worker paradigm. Extracts constraints from feedback using intelligent reasoning.",
}


class AnalyzerAgent(BaseAgent):
    """Boss-Worker Analyzer Agent - Fully Autonomous

    Interprets feedback and extracts constraints using intelligent reasoning.
    Maintains hypothesis tracking and builds confidence over multiple rounds.
    Makes independent decisions about constraint validity and confidence.
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
        # State tracking - Analyzer learns and refines hypotheses
        self.analysis_history = []
        self.constraint_hypotheses = []
        self.confidence_evolution = []
        self.identified_colors = set()
        self.locked_positions = {}

    def analyze_feedback(
        self,
        last_guess: List[str],
        feedback: Dict[str, int],
        previous_guesses: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze feedback and extract constraints using intelligent reasoning.

        The analyzer uses its own judgment to interpret feedback, considering:
        - All historical data to identify patterns
        - Multiple hypotheses about which colors are involved
        - Confidence evolution as more data is collected
        - Strategic implications of the findings
        """
        correct_pegs = feedback.get("correct_pegs", 0)
        correct_positions = feedback.get("correct_positions", 0)
        previous_guesses = previous_guesses or []

        # Include analysis history for context
        history_context = f"Round {len(previous_guesses) + 1}"
        if previous_guesses:
            history_context += f": {len(previous_guesses)} rounds completed so far"

        # Format detailed history
        history_text = ""
        if previous_guesses:
            history_text = "\n".join([
                f"  Round {i+1}: Guess {g.get('guess')} → {g.get('feedback', {}).get('correct_pegs', 0)} colors, {g.get('feedback', {}).get('correct_positions', 0)} positions"
                for i, g in enumerate(previous_guesses[-5:])  # Last 5 rounds for context
            ])
        else:
            history_text = "  [This is the first round - no previous data]"

        # Get explicit role context
        role_context = self.get_role_system_prompt()

        # Full LLM-based analysis with strategic reasoning
        prompt = f"""{role_context}

## YOUR TASK (Constraint Extraction in Boss-Worker Paradigm)
You are the Analyzer. Your job is to interpret feedback and extract meaningful constraints.
Use your reasoning to make sense of the data and identify patterns.

CURRENT FEEDBACK:
- Last Guess: {last_guess}
- Correct Pegs: {correct_pegs} (colors in the code)
- Correct Positions: {correct_positions} (colors in right positions)

{history_context}

PREVIOUS GUESSES (with feedback):
{history_text}

ANALYSIS APPROACH:
1. Color identification: Which colors are definitely in the code?
2. Position analysis: Which positions are locked/secure?
3. Misplaced analysis: Which colors exist but are in wrong positions?
4. Elimination: Which colors are definitely NOT in the code?
5. Confidence: How certain are you about each constraint?

Use deductive reasoning:
- If correct_pegs increased from previous round, what new colors entered?
- If correct_positions increased, which position(s) likely locked?
- If a color was in a previous guess with 0 feedback, it's definitely out.
- Track patterns across multiple rounds.

Your analysis should:
- Explain your reasoning step-by-step
- Identify the most confident constraints
- Flag any ambiguities or alternative hypotheses
- Consider what you still need to figure out

OUTPUT (JSON ONLY):
{{
  "reasoning_steps": [
    "[Step 1: Color identification reasoning]",
    "[Step 2: Position analysis reasoning]",
    "[Step 3: Misplaced colors reasoning]",
    "[Step 4: Elimination reasoning]",
    "[Step 5: Confidence assessment]"
  ],
  "correct_positions": [
    {{"position": 0, "color": "red", "confidence": 0.9}}
  ],
  "correct_colors_wrong_position": ["green", "yellow"],
  "impossible_colors": ["blue", "white"],
  "color_analysis": {{
    "confirmed_in_code": ["red", "green", "yellow"],
    "possibly_in_code": ["orange"],
    "definitely_not_in_code": ["blue", "white", "black"],
    "still_unknown": ["all others"]
  }},
  "constraints": [
    "Position 0: red (CONFIRMED - locked)",
    "green exists but not at position 2",
    "yellow exists but not at position 3",
    "blue is IMPOSSIBLE - failed in round 1"
  ],
  "analysis": "Found 3 colors (1 locked, 2 misplaced). Blue eliminated. Need to find 4th color.",
  "confidence": 0.8,
  "next_focus": "Find 4th color and lock remaining positions",
  "alternative_hypotheses": ["Could orange be in code instead of yellow"]
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        # Fallback if parsing fails
        if "error" in result:
            result = {
                "correct_positions": [],
                "correct_colors_wrong_position": [],
                "impossible_colors": [],
                "constraints": [
                    f"{correct_pegs} colors in code",
                    f"{correct_positions} in correct positions",
                    f"{correct_pegs - correct_positions} misplaced colors"
                ],
                "analysis": "Basic analysis (LLM parsing failed)",
                "confidence": 0.3,
                "reasoning_steps": ["Error in LLM response - using basic math"],
                "next_focus": "Continue gathering data"
            }

        # Track analysis in state for learning
        self.analysis_history.append({
            "round": len(previous_guesses) + 1,
            "guess": last_guess,
            "feedback": feedback,
            "analysis": result.get("analysis", ""),
            "confidence": result.get("confidence", 0.5)
        })

        # Update identified colors and positions
        if "correct_positions" in result:
            for pos_data in result.get("correct_positions", []):
                if isinstance(pos_data, dict):
                    self.locked_positions[pos_data.get("position")] = pos_data.get("color")
                    self.identified_colors.add(pos_data.get("color"))

        for color in result.get("correct_colors_wrong_position", []):
            self.identified_colors.add(color)

        # Store confidence evolution
        self.confidence_evolution.append(result.get("confidence", 0.5))

        return result

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent abstract class.

        Delegates to analyze_feedback for this agent.
        """
        return self.analyze_feedback(
            last_guess=kwargs.get("last_guess", []),
            feedback=kwargs.get("feedback", {}),
            previous_guesses=kwargs.get("previous_guesses", []),
        )
