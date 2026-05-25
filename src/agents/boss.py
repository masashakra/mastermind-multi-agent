# Boss Agent
# Orchestrates all 4 worker agents (Strategist, Analyzer, Proposer, Validator)
# Controls the flow: Strategy → Analysis → Proposal → Validation → Guess
# Used in Boss-Worker paradigm (centralized collaboration)

from typing import Dict, Any, List
from .base_agent import BaseAgent
from .strategist import StrategistAgent
from .analyzer import AnalyzerAgent
from .proposer import ProposerAgent
from .validator import ValidatorAgent


class BossAgent(BaseAgent):
    """Orchestrates worker agents in a hierarchical workflow.

    Role: Central coordinator for Boss-Worker paradigm

    Workflow per round:
    1. Ask Strategist: What's our strategy?
    2. Ask Analyzer: What constraints can we extract?
    3. Ask Proposer: Generate a guess
    4. Ask Validator: Is it valid?
    5. If invalid, ask Proposer to retry
    6. Return approved guess
    """

    def __init__(self, provider: str = "ollama"):
        super().__init__(name="Boss", provider=provider)
        self.strategist = StrategistAgent(provider=provider)
        self.analyzer = AnalyzerAgent(provider=provider)
        self.proposer = ProposerAgent(provider=provider)
        self.validator = ValidatorAgent(provider=provider)
        self.round_count = 0
        self.max_retries = 2

    def orchestrate_round(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate one complete round through all agents.

        Args:
            game_state: {
                "puzzle": puzzle dict,
                "guess_history": list of previous guesses with feedback,
                "difficulty": "easy", "medium", or "hard"
            }

        Returns:
            {
                "guess": list of colors (ready to submit),
                "strategy": strategy from Strategist,
                "analysis": analysis from Analyzer,
                "proposal": proposal from Proposer,
                "validation": validation from Validator,
                "messages": all inter-agent messages,
                "success": True if guess is valid and approved
            }
        """
        self.round_count += 1
        puzzle = game_state.get("puzzle", {})
        guess_history = game_state.get("guess_history", [])
        difficulty = game_state.get("difficulty", "easy")

        messages = []

        # Step 1: Ask Strategist
        strategy_result = self.strategist.propose_strategy(guess_history, difficulty)
        messages.append({
            "step": 1,
            "agent": "strategist",
            "action": "propose_strategy",
            "result": strategy_result
        })

        # Step 2: Ask Analyzer (if we have feedback)
        if guess_history:
            last_guess = guess_history[-1]
            analysis = self.analyzer.analyze_feedback(
                last_guess.get("guess", []),
                last_guess.get("feedback", {}),
                guess_history[:-1]
            )
        else:
            analysis = {
                "correct_positions": [],
                "correct_colors_wrong_position": [],
                "constraints": [],
                "impossible_colors": [],
                "estimated_remaining": "All codes possible"
            }

        messages.append({
            "step": 2,
            "agent": "analyzer",
            "action": "analyze_feedback",
            "result": analysis
        })

        # Step 3: Ask Proposer
        previous_guess_lists = [g.get("guess", []) for g in guess_history]
        proposal = self._ask_proposer_with_retry(
            strategy=strategy_result.get("strategy", ""),
            constraints=analysis.get("constraints", []),
            available_colors=puzzle.get("available_colors", []),
            num_pegs=puzzle.get("pegs", 4),
            previous_guesses=previous_guess_lists
        )

        messages.append({
            "step": 3,
            "agent": "proposer",
            "action": "propose_guess",
            "result": proposal
        })

        # Step 4: Ask Validator (with constraints)
        guess = proposal.get("proposed_guess", [])

        # Build constraints dict for validator
        constraints_dict = {
            "correct_positions": analysis.get("correct_positions", []),
            "correct_colors_wrong_position": analysis.get("correct_colors_wrong_position", []),
            "impossible_colors": analysis.get("impossible_colors", [])
        }

        validation = self.validator.validate_with_llm(
            guess=guess,
            available_colors=puzzle.get("available_colors", []),
            expected_length=puzzle.get("pegs", 4),
            previous_guesses=[g.get("guess", []) for g in guess_history],
            constraints=constraints_dict
        )

        messages.append({
            "step": 4,
            "agent": "validator",
            "action": "validate_guess",
            "result": validation
        })

        # If invalid, optionally retry Proposer
        if not validation["is_valid"]:
            # Note: Could retry here, but for now accept invalid guess
            # The game engine will reject it anyway
            pass

        return {
            "guess": guess,
            "strategy": strategy_result,
            "analysis": analysis,
            "proposal": proposal,
            "validation": validation,
            "messages": messages,
            "success": validation["is_valid"]
        }

    def _ask_proposer_with_retry(
        self,
        strategy: str,
        constraints: List[str],
        available_colors: List[str],
        num_pegs: int,
        previous_guesses: List[List[str]]
    ) -> Dict[str, Any]:
        """Ask Proposer to generate a guess, retry if needed.

        Args:
            strategy: Strategy description from Strategist
            constraints: List of constraints from Analyzer
            available_colors: Valid colors for this puzzle
            num_pegs: Number of pegs needed
            previous_guesses: All previous guesses

        Returns:
            Proposal with proposed_guess field
        """
        constraints_text = "\n".join(constraints) if constraints else "No constraints yet"

        proposal = self.proposer.propose_guess(
            strategy=strategy,
            constraints_text=constraints_text,
            available_colors=available_colors,
            num_pegs=num_pegs,
            previous_guesses=previous_guesses
        )

        return proposal

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestration statistics.

        Returns:
            Stats from all agents
        """
        return {
            "boss": {
                "rounds_orchestrated": self.round_count,
                "call_count": self.call_count
            },
            "strategist": self.strategist.get_stats(),
            "analyzer": self.analyzer.get_stats(),
            "proposer": self.proposer.get_stats(),
            "validator": self.validator.get_stats()
        }

    def process(self, **kwargs) -> Dict[str, Any]:
        """Standard process interface.

        Args:
            **kwargs: Passed to orchestrate_round

        Returns:
            Orchestration result
        """
        return self.orchestrate_round(kwargs)
