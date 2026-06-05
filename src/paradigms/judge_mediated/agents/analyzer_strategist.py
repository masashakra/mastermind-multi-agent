# Agent 1: Analyzer-Strategist
# Extracts constraints AND develops strategy based on competitive intelligence

from typing import List, Dict, Any, Optional
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType
from communication.protocol import A2ACommunicationLayer


AGENT_CARD = {
    "agent_id": "analyzer_strategist_judge_mediated",
    "agent_name": "Analyzer-Strategist",
    "agent_type": "analyzer_strategist",
    "paradigm": "judge_mediated",
    "version": "1.0.0",
    "description": "Agent 1: Analyzes constraints and develops winning strategy",
    "capabilities": {
        "analyze_and_strategize": {
            "description": "Extract constraints and develop strategy",
            "parameters": {
                "type": "object",
                "properties": {
                    "guess_history": {"type": "array"},
                    "last_feedback": {"type": "object"},
                    "competitive_analysis": {"type": "object"},
                    "difficulty": {"type": "string"},
                    "available_colors": {"type": "array"},
                    "num_pegs": {"type": "integer"},
                }
            },
            "returns": {
                "type": "object",
                "description": "Constraints and strategy"
            }
        }
    },
    "constraints_owned": [],
    "team_members": [],
    "can_communicate": True,
}


class AnalyzerStrategistAgent(BaseAgent):
    """Agent 1: Analyzer-Strategist

    Responsibilities:
    1. Extract constraints from game history
    2. Consider competitive status
    3. Develop winning strategy
    4. Pass clear strategy to Proposer

    MEMORY: This agent maintains its own analysis_history (stateful).
    Memory grows with each round as constraints are discovered.
    """

    def __init__(
        self,
        provider: str = "deepseek",
        comm_layer: Optional[A2ACommunicationLayer] = None,
    ):
        super().__init__(
            name="AnalyzerStrategist",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.ANALYZER,
            paradigm=ParadigmType.JUDGE_MEDIATED,
        )

        # ⭐ AGENT-MANAGED MEMORY: Initialize analysis history
        self.analysis_history: List[Dict[str, Any]] = []  # Per-agent memory!

    def analyze_and_strategize(
        self,
        guess_history: List[List[str]] = None,
        last_feedback: Dict[str, Any] = None,
        competitive_analysis: Dict[str, Any] = None,
        difficulty: str = "easy",
        available_colors: List[str] = None,
        num_pegs: int = 4,
        round_num: int = 1,
    ) -> Dict[str, Any]:
        """Analyze constraints and develop strategy.

        ⭐ Uses self.analysis_history (agent's own memory) instead of parameter.
        After analyzing, updates self.analysis_history with new deductions.
        """

        if guess_history is None:
            guess_history = []
        if last_feedback is None:
            last_feedback = {}
        if competitive_analysis is None:
            competitive_analysis = {}
        if available_colors is None:
            available_colors = []

        # Build analysis history context from AGENT'S OWN MEMORY
        analysis_history_text = ""
        # ⭐ DEBUG: Verify memory is persisting
        print(f"[Agent Memory] Round {round_num}: self.analysis_history has {len(self.analysis_history)} entries")
        if self.analysis_history:
            print(f"[Agent Memory] Last entry: Round {self.analysis_history[-1].get('round')}, colors_in={self.analysis_history[-1].get('colors_in')}")

        if self.analysis_history:  # ← Read from self, not parameter!
            analysis_history_text = "=== YOUR PREVIOUS DEDUCTIONS (Build on this!) ===\n"
            for entry in self.analysis_history[-3:]:  # Last 3 rounds to avoid token overflow
                try:
                    round_num_prev = entry.get("round", "?")
                    colors_in = entry.get("colors_in", [])
                    colors_out = entry.get("colors_out", [])
                    locked = entry.get("locked_positions", {})

                    analysis_history_text += f"\nRound {round_num_prev}:\n"
                    if colors_in:
                        analysis_history_text += f"  ✓ IN: {', '.join(colors_in)}\n"
                    if colors_out:
                        analysis_history_text += f"  ✗ OUT: {', '.join(colors_out)}\n"
                    if locked:
                        for pos, col in sorted(locked.items()):
                            analysis_history_text += f"  🔒 Position {pos} = {col}\n"
                except:
                    pass
            analysis_history_text += "\n"

        # Build context
        history_text = ""
        if guess_history:
            history_text = "Previous guesses:\n"
            for i, guess in enumerate(guess_history, 1):
                history_text += f"  {i}. {guess}\n"

        # Build feedback context
        feedback_text = ""
        if last_feedback and "game_feedback" in last_feedback:
            fb = last_feedback["game_feedback"]
            feedback_text = f"\nLast Result: {fb.get('correct_pegs', 0)} pegs, {fb.get('correct_positions', 0)} positions\n"
            feedback_text += f"Your Rank: #{last_feedback.get('your_rank', '?')}\n"

        # Build competitive context
        competitive_text = ""
        if competitive_analysis:
            competitive_text = "\n=== COMPETITIVE STATUS ===\n"
            for team_key, analysis in competitive_analysis.items():
                colors = analysis.get("colors_found", 0)
                positions = analysis.get("positions_locked", 0)
                strategy = analysis.get("strategy", "unknown")
                competitive_text += f"{team_key}: {colors} colors, {positions} positions locked ({strategy})\n"

        # ⭐ SIMPLIFIED PROMPT: Direct, minimal reasoning needed
        prompt = f"""Mastermind solver ({num_pegs} pegs).
Colors: {', '.join(available_colors)}

{analysis_history_text}{history_text}{feedback_text}

Extract constraints and strategy:
1. Colors IN the code (from past feedback)
2. Colors OUT (eliminated)
3. Locked positions (correct position)
4. Unknown positions
5. Next strategy

Keep {num_pegs} colors in "colors_in" list.

JSON:
{{
  "colors_in": ["color1", "color2", ...],
  "colors_out": ["eliminated_color"],
  "locked_positions": {{"0": "color1"}},
  "unknown_positions": [1, 2],
  "strategy": "Next test approach"
}}
"""

        try:
            response = self.call_llm(prompt)

            # Parse JSON with better error handling
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                import re
                # Strip markdown code blocks first
                cleaned = re.sub(r'```json\s*\n?|\n?```', '', response, flags=re.DOTALL)
                # Try to find JSON object
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        # Fall back to systematic testing
                        result = {
                            "colors_in": available_colors[:num_pegs],
                            "colors_out": [],
                            "locked_positions": {},
                            "unknown_positions": list(range(num_pegs)),
                            "strategy": "Systematic color testing"
                        }
                else:
                    result = {
                        "colors_in": available_colors[:num_pegs],
                        "colors_out": [],
                        "locked_positions": {},
                        "unknown_positions": list(range(num_pegs)),
                        "strategy": "Systematic color testing"
                    }

            # Ensure colors_in has at least num_pegs colors
            colors_in = result.get("colors_in", [])
            if len(colors_in) < num_pegs:
                # Add untested colors to reach num_pegs
                colors_out = set(result.get("colors_out", []))
                for color in available_colors:
                    if color not in colors_in and color not in colors_out and len(colors_in) < num_pegs:
                        colors_in.append(color)
                result["colors_in"] = colors_in

            # ===== IMPROVEMENT #1 & #2: DETECT NEAR-SOLVE STATE =====
            pegs_found = len(result.get("colors_in", []))
            locked_positions = result.get("locked_positions", {})
            positions_locked = len(locked_positions)

            # If 3+ pegs found and 2+ positions locked = NEAR SOLVE
            if pegs_found >= 3 and positions_locked >= 2:
                result["near_solve_state"] = True
                result["missing_color_count"] = num_pegs - pegs_found
                result["unknown_positions"] = [i for i in range(num_pegs)
                                              if str(i) not in locked_positions]

                # Set explicit permutation strategy
                result["permutation_strategy"] = {
                    "action": "test_permutations",
                    "locked_colors": locked_positions,
                    "remaining_colors": result.get("colors_in", []),
                    "unknown_positions": [i for i in range(num_pegs)
                                         if str(i) not in locked_positions],
                }

                # Update strategy description for permutation mode
                unknown_pos = result["permutation_strategy"]["unknown_positions"]
                missing_count = result["missing_color_count"]
                result["strategy"] = (
                    f"NEAR-SOLVE: {pegs_found}/{num_pegs} correct pegs, "
                    f"{positions_locked}/{num_pegs} positions locked. "
                    f"Permute the {len(unknown_pos)} unknown position(s) with the "
                    f"{missing_count} remaining color(s) while keeping locked positions fixed."
                )

            # ⭐ UPDATE AGENT'S OWN MEMORY
            memory_entry = {
                "round": round_num,
                "colors_in": result.get("colors_in", []),
                "colors_out": result.get("colors_out", []),
                "locked_positions": result.get("locked_positions", {}),
                "strategy": result.get("strategy", ""),
                "near_solve_state": result.get("near_solve_state", False),
            }
            self.analysis_history.append(memory_entry)
            print(f"[Agent Memory] ✓ SAVED Round {round_num}: colors_in={memory_entry['colors_in']}, locked={memory_entry['locked_positions']}")
            print(f"[Agent Memory] Total history now: {len(self.analysis_history)} entries")

            self.call_count += 1
            return result

        except Exception as e:
            print(f"Error in analyze_and_strategize: {e}")
            # Ensure at least num_pegs colors in fallback
            colors_in = available_colors[:num_pegs]
            while len(colors_in) < num_pegs and len(colors_in) < len(available_colors):
                colors_in.append(available_colors[len(colors_in)])

            fallback_result = {
                "colors_in": colors_in[:num_pegs],
                "colors_out": [],
                "locked_positions": {},
                "unknown_positions": list(range(num_pegs)),
                "strategy": f"Error: {str(e)}",
                "near_solve_state": False,
                "permutation_strategy": None,
            }

            # ⭐ SAVE FALLBACK TO MEMORY TOO (even on error)
            fallback_memory = {
                "round": round_num,
                "colors_in": fallback_result["colors_in"],
                "colors_out": fallback_result["colors_out"],
                "locked_positions": fallback_result["locked_positions"],
                "strategy": fallback_result["strategy"],
                "near_solve_state": False,
            }
            self.analysis_history.append(fallback_memory)
            print(f"[Agent Memory] SAVED FALLBACK Round {round_num}: error={str(e)[:60]}")
            print(f"[Agent Memory] Total history now: {len(self.analysis_history)} entries")

            return fallback_result

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process analysis and strategy."""
        return self.analyze_and_strategize(
            guess_history=kwargs.get("guess_history", []),
            last_feedback=kwargs.get("last_feedback", {}),
            competitive_analysis=kwargs.get("competitive_analysis", {}),
            difficulty=kwargs.get("difficulty", "easy"),
            available_colors=kwargs.get("available_colors", []),
            num_pegs=kwargs.get("num_pegs", 4),
            round_num=kwargs.get("round_num", 1),
        )
