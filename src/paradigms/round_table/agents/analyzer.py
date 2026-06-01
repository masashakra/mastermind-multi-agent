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
        knowledge_base: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Analyze feedback and extract NEW constraints, merged with accumulated knowledge.

        Args:
            last_guess: Colors in the most recent guess
            feedback: {"correct_pegs": int, "correct_positions": int}
            previous_guesses: Full guess history
            knowledge_base: Accumulated facts from ALL previous rounds

        Returns:
            Constraint analysis dictionary (merged with knowledge_base)
        """
        correct_pegs = feedback.get("correct_pegs", 0)
        correct_positions = feedback.get("correct_positions", 0)
        kb = knowledge_base or {}

        # Format full history (all rounds, not just last 3)
        history_text = "No previous guesses yet." if not previous_guesses else "\n".join(
            f"  Round {i+1}: {g.get('guess')} → pegs={g['feedback'].get('correct_pegs',0)} pos={g['feedback'].get('correct_positions',0)}"
            for i, g in enumerate(previous_guesses)
        )

        # Format accumulated knowledge base clearly
        kb_text = ""
        if kb:
            kb_text = f"""
ACCUMULATED KNOWLEDGE FROM ALL PREVIOUS ROUNDS (DO NOT CONTRADICT THESE):
  - Colors IMPOSSIBLE (not in secret): {kb.get('impossible_colors', [])}
  - Colors CONFIRMED (in secret somewhere): {kb.get('confirmed_colors', [])}
  - Positions LOCKED (exact match confirmed): {kb.get('locked_positions', {})}
  - Minimum color counts: {kb.get('min_color_counts', {})}
  - All constraints so far:
{chr(10).join('    • ' + c for c in kb.get('constraints', [])[-10:])}
"""

        role_context = self.get_role_system_prompt()

        prompt = f"""{role_context}

## YOUR TASK — Constraint Extraction (Round {len(previous_guesses or []) + 1})

You are the Analyzer in a Mastermind game. Your job is to extract ALL constraints
from the guess history and update the knowledge base. Build on what is already known —
never go backwards.
{kb_text}
FULL GUESS HISTORY:
{history_text}

LATEST GUESS: {last_guess}
LATEST FEEDBACK: {correct_pegs} correct colors (pegs), {correct_positions} in correct position

RULES FOR MASTERMIND:
- "correct_pegs" = total colors in secret that are also in the guess (any position)
- "correct_positions" = colors that are in the EXACT right position
- If pegs=0 → NONE of the guessed colors are in the secret at all
- If pegs=N (all pegs) → ALL guessed colors exist in the secret
- (pegs - positions) = number of correct colors in WRONG positions
- If a color appears twice in guess and pegs≥2, it appears at least twice in secret

STEP-BY-STEP ANALYSIS OF LATEST GUESS:
1. What new colors can we eliminate? (impossible_colors)
2. What new colors can we confirm? (confirmed_colors)
3. What positions can we now lock? (locked_positions)
4. How many times does each color appear? (min_color_counts)
5. What does this tell us about where colors are NOT? (impossible_positions)

OUTPUT (JSON ONLY):
{{
  "analysis": "One sentence summarising what was learned this round",
  "new_impossible_colors": ["colors confirmed absent this round"],
  "new_confirmed_colors": ["colors confirmed present this round"],
  "new_locked_positions": [{{"position": 0, "color": "red"}}],
  "new_min_counts": {{"black": 2}},
  "constraints": [
    "All known constraints including previous ones",
    "Be specific: 'black appears ≥2 times', 'white NOT in secret', 'green at position 3 (LOCKED)'"
  ],
  "confidence": 0.9
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        if "error" in result or "constraints" not in result:
            result = {
                "new_impossible_colors": [],
                "new_confirmed_colors": [],
                "new_locked_positions": [],
                "new_min_counts": {},
                "constraints": kb.get("constraints", []),
                "analysis": "Failed to parse — using existing knowledge",
                "confidence": 0.0,
            }

        # Merge new findings into the knowledge base snapshot passed to next agents
        merged_kb = dict(kb)
        for color in result.get("new_impossible_colors", []):
            if color not in merged_kb.get("impossible_colors", []):
                merged_kb.setdefault("impossible_colors", []).append(color)
        for color in result.get("new_confirmed_colors", []):
            if color not in merged_kb.get("confirmed_colors", []):
                merged_kb.setdefault("confirmed_colors", []).append(color)
        for lock in result.get("new_locked_positions", []):
            merged_kb.setdefault("locked_positions", {})[lock["position"]] = lock["color"]
        for color, count in result.get("new_min_counts", {}).items():
            prev = merged_kb.setdefault("min_color_counts", {}).get(color, 0)
            if count > prev:
                merged_kb["min_color_counts"][color] = count
        merged_kb["constraints"] = result.get("constraints", [])

        result["knowledge_base"] = merged_kb
        return result

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process method for abstract base class compliance."""
        return self.analyze_feedback(
            state.get("last_guess", []),
            state.get("last_feedback", {}),
            state.get("guess_history", [])
        )
