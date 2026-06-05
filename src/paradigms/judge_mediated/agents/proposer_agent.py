# Agent 2: Proposer
# Takes strategy from Analyzer-Strategist and generates a tactical guess

from typing import List, Dict, Any, Optional
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType
from communication.protocol import A2ACommunicationLayer


AGENT_CARD = {
    "agent_id": "proposer_judge_mediated",
    "agent_name": "Proposer",
    "agent_type": "proposer",
    "paradigm": "judge_mediated",
    "version": "1.0.0",
    "description": "Agent 2: Generates guess following strategy",
    "capabilities": {
        "propose_guess": {
            "description": "Generate a tactical guess following strategy",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy": {"type": "object"},
                    "available_colors": {"type": "array"},
                    "num_pegs": {"type": "integer"},
                }
            },
            "returns": {
                "type": "object",
                "description": "Tactical guess"
            }
        }
    },
    "constraints_owned": [],
    "team_members": [],
    "can_communicate": True,
}


class ProposerAgent(BaseAgent):
    """Agent 2: Proposer

    Responsibilities:
    1. Receive strategy from Analyzer-Strategist
    2. Generate a valid guess that follows the strategy
    3. Ensure guess uses correct colors and format
    """

    def __init__(
        self,
        provider: str = "deepseek",
        comm_layer: Optional[A2ACommunicationLayer] = None,
    ):
        super().__init__(
            name="Proposer",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.PROPOSER,
            paradigm=ParadigmType.JUDGE_MEDIATED,
        )

    def propose_guess(
        self,
        strategy: Dict[str, Any],
        available_colors: List[str] = None,
        num_pegs: int = 4,
    ) -> Dict[str, Any]:
        """Generate a guess following the strategy."""

        if available_colors is None:
            available_colors = []

        colors_in = strategy.get("colors_in", available_colors[:num_pegs])
        locked_positions = strategy.get("locked_positions", {})
        strategy_desc = strategy.get("strategy", "Generate a tactical guess")

        # ===== IMPROVEMENT #3: HANDLE PERMUTATION STRATEGY =====
        permutation_strat = strategy.get("permutation_strategy")
        if permutation_strat is not None and isinstance(permutation_strat, dict) and permutation_strat.get("action") == "test_permutations":
            locked_colors = permutation_strat.get("locked_colors", {})
            remaining_colors = permutation_strat.get("remaining_colors", [])
            unknown_positions = permutation_strat.get("unknown_positions", [])

            if unknown_positions and remaining_colors:
                # Build guess with locked colors fixed
                guess = [""] * num_pegs

                # Fill locked positions
                for pos_str, color in locked_colors.items():
                    try:
                        pos = int(pos_str)
                        if pos < num_pegs:
                            guess[pos] = color
                    except (ValueError, IndexError):
                        pass

                # Fill unknown position(s) with remaining color(s)
                remaining_to_test = list(remaining_colors)
                for i, unknown_pos in enumerate(unknown_positions):
                    if i < len(remaining_to_test):
                        guess[unknown_pos] = remaining_to_test[i]

                # Fallback for any remaining empty slots
                for i in range(num_pegs):
                    if not guess[i]:
                        guess[i] = remaining_colors[0] if remaining_colors else available_colors[0]

                # Ensure all are valid colors
                guess = [c if c in available_colors else available_colors[0] for c in guess]
                guess = guess[:num_pegs]

                self.call_count += 1
                return {
                    "guess": guess,
                    "reasoning": f"Permutation test: locked positions fixed, testing position(s) {unknown_positions} with remaining colors"
                }

        # ⭐ SIMPLIFIED PROMPT: Direct guess generation
        # ⭐ OPTIMIZATION: Skip LLM call, use heuristic-based proposal
        # Build guess directly without expensive LLM call
        try:
            # Simple heuristic: use colors_in in order, keeping locked positions fixed
            guess = [""] * num_pegs

            # Fill locked positions
            for pos_str, color in locked_positions.items():
                try:
                    pos = int(pos_str)
                    if pos < num_pegs:
                        guess[pos] = color
                except (ValueError, IndexError):
                    pass

            # Fill remaining positions with colors_in
            color_idx = 0
            for i in range(num_pegs):
                if not guess[i]:
                    # Use next available color from colors_in
                    while color_idx < len(colors_in) and colors_in[color_idx] in guess:
                        color_idx += 1
                    if color_idx < len(colors_in):
                        guess[i] = colors_in[color_idx]
                        color_idx += 1
                    else:
                        # Fallback to first available color
                        guess[i] = colors_in[0] if colors_in else available_colors[0]

            # Validate and fix guess
            if not guess or len(guess) != num_pegs:
                guess = [""] * num_pegs
                for pos_str, color in locked_positions.items():
                    try:
                        pos = int(pos_str)
                        if pos < num_pegs:
                            guess[pos] = color
                    except (ValueError, IndexError):
                        pass

                idx = 0
                for i in range(num_pegs):
                    if not guess[i]:
                        while idx < len(colors_in):
                            if colors_in[idx] not in locked_positions.values():
                                guess[i] = colors_in[idx]
                                idx += 1
                                break
                            idx += 1
                        if not guess[i] and colors_in:
                            guess[i] = colors_in[0]

            guess = [
                c.lower().strip() if c in available_colors else available_colors[0]
                for c in guess if c
            ]
            while len(guess) < num_pegs:
                guess.append(available_colors[0])
            guess = guess[:num_pegs]

            # ===== IMPROVEMENT #4: SAFETY CHECK - PRESERVE LOCKED POSITIONS =====
            if strategy.get("near_solve_state"):
                locked_colors = strategy.get("permutation_strategy", {}).get("locked_colors", {})
                for pos_str, color in locked_colors.items():
                    try:
                        pos = int(pos_str)
                        if pos < num_pegs and guess[pos] != color:
                            print(f"[WARNING] Guess lost locked position {pos}={color}! Restoring...")
                            guess[pos] = color
                    except (ValueError, IndexError):
                        pass

            self.call_count += 1
            return {
                "guess": guess,
                "reasoning": "Heuristic guess: systematic color testing from analysis"
            }

        except Exception as e:
            print(f"Error in propose_guess: {e}")
            guess = colors_in[:num_pegs] if colors_in else available_colors[:num_pegs]
            while len(guess) < num_pegs:
                guess.append(available_colors[0] if available_colors else "red")
            return {
                "guess": guess[:num_pegs],
                "reasoning": f"Fallback: {str(e)}"
            }

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process proposal."""
        return self.propose_guess(
            strategy=kwargs.get("strategy", {}),
            available_colors=kwargs.get("available_colors", []),
            num_pegs=kwargs.get("num_pegs", 4),
        )
