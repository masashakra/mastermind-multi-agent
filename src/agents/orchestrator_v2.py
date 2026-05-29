# Orchestrator V2
# RULE-BASED: Fast game orchestration using V2 agents (no LLM calls)

from typing import Dict, List, Any
from .analyzer_v3 import AnalyzerV3
from .proposer_v2 import ProposerAgentV2


class OrchestratorV2:
    """Fast orchestrator using rule-based agents."""

    def __init__(self):
        self.analyzer = AnalyzerV3()
        self.proposer = ProposerAgentV2()

    def orchestrate_round(
        self,
        puzzle: Dict[str, Any],
        guess_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run one round of guessing.

        Args:
            puzzle: {"secret_code": [...], "pegs": N, "available_colors": [...]}
            guess_history: [{"guess": [...], "feedback": {...}}]

        Returns:
            {"guess": [...], "analysis": ..., "strategy": ...}
        """
        if guess_history is None:
            guess_history = []

        num_pegs = puzzle["pegs"]
        available_colors = puzzle["available_colors"]

        # Step 1: Analyze constraints from history
        analysis = self.analyzer.analyze(
            guess_history=guess_history,
            available_colors=available_colors,
            num_pegs=num_pegs
        )

        # Step 2: Generate guess
        previous_guesses = [g["guess"] for g in guess_history]

        guess = self.proposer.propose_guess(
            locked_positions=analysis["locked_positions"],
            found_colors=set(analysis["found_colors"]),
            misplaced_colors=set(analysis["misplaced_colors"]),
            available_colors=available_colors,
            num_pegs=num_pegs,
            previous_guesses=previous_guesses
        )

        return {
            "guess": guess,
            "analysis": analysis,
            "strategy": self._get_strategy(analysis, num_pegs),
            "round_number": len(guess_history) + 1
        }

    def _get_strategy(self, analysis: Dict[str, Any], num_pegs: int) -> str:
        """Determine strategy based on current state."""
        locked_count = len(analysis["locked_positions"])
        found_count = len(analysis["found_colors"])
        total_in_secret = analysis["total_colors_in_secret"]

        if locked_count == num_pegs:
            return "COMPLETE - All positions locked"
        elif locked_count >= num_pegs - 1:
            return "CONFIRMATION - Just 1 position left"
        elif locked_count >= num_pegs // 2:
            return "REFINEMENT - More than half locked"
        elif found_count >= total_in_secret - 1:
            return "LOCALIZATION - Found most colors, finding positions"
        elif found_count >= 2:
            return "CONSTRAINT_BUILDING - Found some colors, need more"
        else:
            return "EXPLORATION - Still finding which colors exist"
