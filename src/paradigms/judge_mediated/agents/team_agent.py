# Unified Team Agent for Judge-Mediated Paradigm
# NOW WITH: Boss-Worker style constraint extraction!
# SIMPLIFIED: Single LLM call for reliability

from typing import List, Dict, Any, Optional
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType
from communication.protocol import A2ACommunicationLayer


AGENT_CARD = {
    "agent_id": "team_agent_judge_mediated",
    "agent_name": "Team Agent",
    "agent_type": "team_agent",
    "paradigm": "judge_mediated",
    "version": "2.1.0",
    "description": "Team agent with constraint extraction (boss-worker inspired)",
    "capabilities": {
        "solve_round": {
            "description": "Extract constraints and propose strategic guess",
            "parameters": {
                "type": "object",
                "properties": {
                    "guess_history": {"type": "array"},
                    "constraint_history": {"type": "array"},
                    "last_feedback": {"type": "object"},
                    "difficulty": {"type": "string"},
                    "available_colors": {"type": "array"},
                    "num_pegs": {"type": "integer"},
                }
            },
            "returns": {"type": "object"}
        }
    },
    "constraints_owned": [],
    "team_members": [],
    "can_communicate": True,
}


class TeamAgent(BaseAgent):
    """Team Agent with Boss-Worker Constraint Extraction"""

    def __init__(
        self,
        provider: str = "deepseek",
        comm_layer: Optional[A2ACommunicationLayer] = None,
    ):
        super().__init__(
            name="TeamAgent",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.STRATEGIST,
            paradigm=ParadigmType.JUDGE_MEDIATED,
        )

    def solve_round(
        self,
        guess_history: List[List[str]],
        constraint_history: List[Dict[str, Any]] = None,
        last_feedback: Dict[str, Any] = None,
        difficulty: str = "easy",
        available_colors: List[str] = None,
        num_pegs: int = 4,
    ) -> Dict[str, Any]:
        """Solve one round with constraint extraction AND competitive intelligence"""

        if constraint_history is None:
            constraint_history = []
        if last_feedback is None:
            last_feedback = {}
        if available_colors is None:
            available_colors = []

        # Build previous guesses context
        history_text = ""
        if guess_history:
            history_text = "Previous guesses:\n"
            for i, guess in enumerate(guess_history, 1):
                history_text += f"  {i}. {guess}\n"

        # Build constraint context from previous rounds (like boss-worker!)
        constraint_text = ""
        if constraint_history:
            constraint_text = "\nCONSTRAINTS FROM YOUR PREVIOUS ANALYSIS:\n"
            recent = constraint_history[-2:] if len(constraint_history) > 2 else constraint_history
            for entry in recent:
                try:
                    r = entry.get("round", "?")
                    colors_in = entry.get("colors_in", [])
                    colors_out = entry.get("colors_out", [])
                    locked = entry.get("locked_positions", {})

                    if colors_in or colors_out or locked:
                        constraint_text += f"\nRound {r}:\n"
                        if colors_in:
                            constraint_text += f"  ✓ IN: {', '.join(colors_in)}\n"
                        if colors_out:
                            constraint_text += f"  ✗ OUT: {', '.join(colors_out)}\n"
                        if locked:
                            for pos, col in locked.items():
                                constraint_text += f"  🔒 Position {pos} = {col}\n"
                except:
                    pass

        # Build feedback context
        feedback_text = ""
        competitive_intelligence_text = ""

        if last_feedback:
            if "game_feedback" in last_feedback:
                fb = last_feedback["game_feedback"]
                feedback_text = f"\nLast Result: {fb.get('correct_pegs', 0)} pegs, {fb.get('correct_positions', 0)} positions\n"

            # NEW: Add competitive intelligence from judge!
            if "competitive_analysis" in last_feedback:
                comp_analysis = last_feedback.get("competitive_analysis", {})
                if comp_analysis:
                    competitive_intelligence_text = "\n=== COMPETITIVE INTELLIGENCE (How Others Are Doing) ===\n"
                    for team_key, analysis in comp_analysis.items():
                        team_num = analysis.get("team_id", "?")
                        colors = analysis.get("colors_found", 0)
                        positions = analysis.get("positions_locked", 0)
                        strategy = analysis.get("strategy", "unknown")
                        advantage = analysis.get("what_they_do_right", "")
                        weakness = analysis.get("how_to_exploit", "")

                        competitive_intelligence_text += f"\n{team_key.upper()}:\n"
                        competitive_intelligence_text += f"  Status: {colors} colors found, {positions} positions locked\n"
                        competitive_intelligence_text += f"  Strategy: {strategy}\n"
                        competitive_intelligence_text += f"  Strength: {advantage}\n"
                        competitive_intelligence_text += f"  Weakness: {weakness}\n"

            # Add strategic advice from judge
            if "strategic_advice" in last_feedback:
                strategic_advice = last_feedback.get("strategic_advice", "")
                if strategic_advice:
                    competitive_intelligence_text += f"\n=== JUDGE'S STRATEGIC RECOMMENDATION ===\n{strategic_advice}\n"

        # SINGLE LLM CALL: Extract constraints AND propose guess
        prompt = f"""You are solving a Mastermind puzzle ({num_pegs} pegs) IN COMPETITION with other teams.
Colors available: {', '.join(available_colors)}

{history_text}{constraint_text}{feedback_text}{competitive_intelligence_text}

TASK: Use competitive intelligence to extract constraints and propose a strategic guess that BEATS OTHER TEAMS.

STEP 1: Analyze and extract STRUCTURED constraints:
- Which colors are DEFINITELY IN the code?
- Which colors are DEFINITELY OUT?
- Which positions are LOCKED (confirmed correct)?

STEP 2: Propose a STRATEGIC guess based on these facts.

RESPOND EXACTLY like this (JSON format):
{{
  "colors_in": ["color1", "color2"],
  "colors_out": ["color3"],
  "locked_positions": {{"0": "color1"}},
  "misplaced_colors": [],
  "reasoning": "Brief explanation of your strategy",
  "guess": ["color1", "color2", "color3", "color4"]
}}

CRITICAL:
- guess MUST be a JSON array of exactly {num_pegs} colors
- All colors in guess MUST be from: {', '.join(available_colors)}
- Only use colors_in OR untested colors, avoid colors_out
"""

        try:
            response = self.call_llm(prompt)

            # Parse JSON response
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")

            # Extract guess
            guess = result.get("guess", [])
            if not guess or len(guess) != num_pegs:
                # Fallback: use colors_in or all available
                colors_in = result.get("colors_in", [])
                guess = colors_in[:num_pegs] if colors_in else available_colors[:num_pegs]
                while len(guess) < num_pegs:
                    for c in available_colors:
                        if c not in guess and len(guess) < num_pegs:
                            guess.append(c)

            # Ensure valid colors
            guess = [c.lower().strip() if c in available_colors else available_colors[0] for c in guess]
            guess = guess[:num_pegs]

            self.call_count += 1

            return {
                "guess": guess,
                "analysis": result.get("reasoning", ""),
                "strategy": f"Constraints: {result.get('colors_in', [])} in, {result.get('colors_out', [])} out",
                "constraints": {
                    "colors_in": result.get("colors_in", []),
                    "colors_out": result.get("colors_out", []),
                    "locked_positions": result.get("locked_positions", {}),
                    "misplaced_colors": result.get("misplaced_colors", []),
                }
            }

        except Exception as e:
            print(f"[TeamAgent] Error: {e}", flush=True)
            import random
            guess = [random.choice(available_colors) for _ in range(num_pegs)]
            return {
                "guess": guess,
                "analysis": f"Error: {str(e)}",
                "strategy": "Fallback",
                "constraints": {}
            }

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process team round."""
        return self.solve_round(
            guess_history=kwargs.get("guess_history", []),
            constraint_history=kwargs.get("constraint_history", []),
            last_feedback=kwargs.get("last_feedback", {}),
            difficulty=kwargs.get("difficulty", "easy"),
            available_colors=kwargs.get("available_colors", []),
            num_pegs=kwargs.get("num_pegs", 4),
        )
