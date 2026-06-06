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
        provider: str = "deepseek",
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
Your role: extract constraints from every guess+feedback pair using EXPLICIT step-by-step reasoning.

MASTERMIND RULES:
- correct_pegs = total colors in guess that exist in secret (counting duplicates!)
- correct_positions = colors in the EXACT right position
- If pegs=0 → NONE of those colors are in the secret (all impossible)
- misplaced = pegs - positions = colors that exist but in WRONG position
- Colors CAN repeat in the secret (CRITICAL: a color can appear 1, 2, 3, or 4 times!)

IMPORTANT DUPLICATE HANDLING:
- If a guess has a color twice (e.g., position 0 and 3), and it gets locked in one position, check the other
- Example: guess=['white', 'red', 'black', 'white'], pos_match=2 → white at pos 0 matches, but white at pos 3 is misplaced
- Track each color occurrence separately by position, not just as a unique color

ANALYSIS STEPS (follow exactly):
1. IDENTIFY EXISTING COLORS: Which colors (including duplicates) from this guess exist in secret?
   → Count total occurrences: if pegs=3 with 2 position matches, 3 colors match the secret
   → A color can appear multiple times in secret (handle this explicitly!)

2. IDENTIFY LOCKED POSITIONS: Which guess colors match the exact position?
   → For each position, mark it as locked if it matches
   → If a color appears multiple times in guess, some can be locked while others are misplaced

3. IDENTIFY MISPLACED COLORS: Which colors are in secret but wrong position?
   → misplaced = correct_pegs - correct_positions (count occurrences!)
   → Track each misplaced occurrence and its wrong positions
   → Key: A color can have some occurrences locked AND some misplaced

4. IDENTIFY IMPOSSIBLE COLORS: Which colors are definitely NOT in secret?
   → Any color with pegs=0 in any guess where it appeared
   → Even if color appears once elsewhere, if one occurrence gets pegs=0, it's impossible

5. IDENTIFY UNKNOWNS: What's left to discover?
   → How many more color slots need to be filled?
   → Which positions are still open?
   → How many duplicates do we need to find?

You have a perfect memory of all prior analysis above. Build on it — never contradict previous rounds."""

        user_message = f"""Round {round_num} result:
Guess: {last_guess}
Feedback: {correct_pegs} correct colors (pegs), {correct_positions} correct positions
Misplaced: {correct_pegs - correct_positions} colors in secret but wrong position

Apply analysis steps 1-5 from above for this round ONLY. Then combine with ALL prior analysis.

OUTPUT (JSON ONLY):
{{
  "reasoning_steps": [
    "Step 1: IDENTIFY EXISTING COLORS - ...",
    "Step 2: IDENTIFY LOCKED POSITIONS - ...",
    "Step 3: IDENTIFY MISPLACED COLORS - ...",
    "Step 4: IDENTIFY IMPOSSIBLE COLORS - ...",
    "Step 5: IDENTIFY UNKNOWNS - ..."
  ],
  "analysis": "Summary of what we know now from all rounds combined",
  "impossible_colors": ["all colors confirmed absent"],
  "confirmed_colors": ["all colors confirmed present"],
  "locked_positions": [{{"position": 0, "color": "white", "rounds_confirmed": 1}}],
  "misplaced_colors": [{{"color": "red", "wrong_positions": [2, 3]}}],
  "constraints": ["explicit constraints for strategy"],
  "confidence": 0.85
}}"""

        try:
            response = self.call_llm_conversation(system_prompt, user_message)
        except Exception as e:
            print(f"[Analyzer] ERROR in call_llm_conversation: {type(e).__name__}: {e}")
            raise

        try:
            result = self.parse_json_response(response)
        except Exception as e:
            print(f"[Analyzer] ERROR in parse_json_response: {type(e).__name__}: {e}")
            raise

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
