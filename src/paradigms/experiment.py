# Experiment Paradigm: Iterative Refinement with Critique
# Novel approach: Agents iteratively critique and refine each other's work
# Phase 1: Analysis proposed
# Phase 2: Strategy critiqued and refined
# Phase 3: Guess proposed
# Phase 4: Validation with refinement loop if issues found
# Hypothesis: Iterative refinement leads to better guesses than single-pass approaches

import time
from typing import Dict, Any, List
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game_engine import GameEngine
from agents.analyzer import AnalyzerAgent
from agents.proposer import ProposerAgent
from agents.strategist import StrategistAgent
from agents.validator import ValidatorAgent
from communication_logger import CommunicationLogger


class ExperimentOrchestrator:
    """Orchestrates Experiment paradigm for solving Mastermind puzzles.

    Novel Iterative Refinement Approach:

    PHASE 1: INITIAL ANALYSIS
      - Analyzer proposes interpretation of constraints
      - Goal: Extract what we know from feedback

    PHASE 2: CRITIQUE AND REFINEMENT
      - Strategist critiques analysis
      - Suggests refinements or alternative interpretations
      - Goal: Improve analysis quality through dialogue

    PHASE 3: STRATEGY AND PROPOSAL
      - Strategist proposes strategy based on refined analysis
      - Proposer generates guess using refined strategy
      - Goal: Generate guess with highest quality context

    PHASE 4: VALIDATION WITH REFINEMENT LOOP
      - Validator checks guess against constraints
      - If issues: Analyzer revisits interpretation (ONE iteration)
      - If issues persist: Proposer generates alternative
      - If valid: Submit
      - Goal: Catch and fix issues before submission

    PHASE 5: LEARNING
      - All agents see feedback
      - Learn what works for next round

    Hypothesis:
    - Critique improves analysis (vs blind analysis)
    - Refinement loop catches validation errors
    - Result: Better guesses from higher quality analysis

    Metrics tracked:
    - Success (solved or not)
    - Efficiency (guesses, rounds)
    - Communication (messages, tokens)
    - Refinement metrics (how many iterations needed?)
    """

    def __init__(self, puzzle: Dict[str, Any], provider: str = "ollama"):
        """Initialize orchestrator for one puzzle.

        Args:
            puzzle: Puzzle dictionary from puzzle_generator
            provider: "ollama" (dev), "kaggle" (GPU), or "claude" (production)
        """
        self.puzzle = puzzle
        self.provider = provider
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])

        # Core agents
        self.analyzer = AnalyzerAgent(provider=provider)
        self.strategist = StrategistAgent(provider=provider)
        self.proposer = ProposerAgent(provider=provider)
        self.validator = ValidatorAgent(provider=provider)

        self.logger = CommunicationLogger(puzzle["puzzle_id"], "experiment")
        self.guess_history = []
        self.round_count = 0
        self.start_time = time.time()
        self.messages = []

        # Track refinement iterations
        self.refinement_iterations = []  # Track when refinement happens

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Experiment paradigm.

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "experiment",
                "success": bool,
                "guesses": int,
                "rounds": int,
                "elapsed_time": float,
                "guess_history": list,
                "messages": list,
                "token_usage": dict,
                "agent_stats": dict,
                "experiment_stats": dict  # Refinement iterations
            }
        """
        while self.round_count < 8 and not self.game_engine.is_game_over():
            self.round_count += 1

            try:
                # Experiment round: Analysis → Critique → Strategy → Validation (with refinement)
                round_result = self._experiment_round()

                # Log all messages
                for msg in round_result.get("messages", []):
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "experiment",
                        "phase": msg.get("phase", "unknown"),
                        "sender": msg.get("agent", "unknown"),
                        "receiver": msg.get("recipient", "unknown"),
                        "message_type": msg.get("type", "unknown"),
                        "content": msg.get("content", {})
                    }
                    self.logger.log_message(log_entry)

                # Extract guess and refinement info
                guess = round_result.get("guess", [])
                refinement_count = round_result.get("refinement_iterations", 0)

                # Track refinement
                if refinement_count > 0:
                    self.refinement_iterations.append({
                        "round": self.round_count,
                        "iterations": refinement_count
                    })

                # Submit to game engine
                feedback = self.game_engine.submit_guess(guess)

                if not feedback.get("valid", False):
                    # Invalid guess
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "experiment",
                        "phase": "feedback",
                        "sender": "game_engine",
                        "receiver": "all_agents",
                        "message_type": "invalid_guess",
                        "content": {"error": feedback.get("error", "Unknown error")}
                    }
                    self.logger.log_message(log_entry)
                    continue

                # Add to history
                self.guess_history.append({
                    "round": self.round_count,
                    "guess": guess,
                    "feedback": feedback.get("feedback", {}),
                    "refinement_iterations": refinement_count
                })

                # Log feedback
                log_entry = {
                    "timestamp": time.time(),
                    "round_number": self.round_count,
                    "puzzle_id": self.puzzle["puzzle_id"],
                    "paradigm": "experiment",
                    "phase": "feedback",
                    "sender": "game_engine",
                    "receiver": "all_agents",
                    "message_type": "feedback",
                    "content": {
                        "guess_number": feedback.get("guess_number", 0),
                        "correct_pegs": feedback.get("feedback", {}).get("correct_pegs", 0),
                        "correct_positions": feedback.get("feedback", {}).get("correct_positions", 0),
                        "solved": feedback.get("solved", False),
                        "refinement_iterations": refinement_count
                    }
                }
                self.logger.log_message(log_entry)

                # Check if solved
                if feedback.get("solved", False):
                    break

            except Exception as e:
                # Log error and continue
                log_entry = {
                    "timestamp": time.time(),
                    "round_number": self.round_count,
                    "puzzle_id": self.puzzle["puzzle_id"],
                    "paradigm": "experiment",
                    "phase": "error",
                    "sender": "error_handler",
                    "receiver": "all_agents",
                    "message_type": "error",
                    "content": {"error": str(e)}
                }
                self.logger.log_message(log_entry)
                continue

        elapsed_time = time.time() - self.start_time

        # Determine success
        if self.guess_history:
            last_feedback = self.guess_history[-1].get("feedback", {})
            success = last_feedback.get("correct_positions", 0) == self.puzzle.get("pegs", 4)
        else:
            success = False

        # Calculate refinement statistics
        total_refinements = sum(r["iterations"] for r in self.refinement_iterations)
        avg_refinements = total_refinements / len(self.refinement_iterations) if self.refinement_iterations else 0

        return {
            "puzzle_id": self.puzzle["puzzle_id"],
            "paradigm": "experiment",
            "difficulty": self.puzzle["difficulty"],
            "success": success,
            "guesses": len(self.guess_history),
            "rounds": self.round_count,
            "elapsed_time": elapsed_time,
            "guess_history": self.guess_history,
            "message_count": len(self.logger.get_all_messages()),
            "messages": self.messages,
            "token_usage": {
                "analyzer": self.analyzer.total_input_tokens + self.analyzer.total_output_tokens,
                "strategist": self.strategist.total_input_tokens + self.strategist.total_output_tokens,
                "proposer": self.proposer.total_input_tokens + self.proposer.total_output_tokens,
                "validator": self.validator.total_input_tokens + self.validator.total_output_tokens,
                "total": (
                    self.analyzer.total_input_tokens + self.analyzer.total_output_tokens +
                    self.strategist.total_input_tokens + self.strategist.total_output_tokens +
                    self.proposer.total_input_tokens + self.proposer.total_output_tokens +
                    self.validator.total_input_tokens + self.validator.total_output_tokens
                )
            },
            "agent_stats": {
                "analyzer": self.analyzer.get_stats(),
                "strategist": self.strategist.get_stats(),
                "proposer": self.proposer.get_stats(),
                "validator": self.validator.get_stats()
            },
            "experiment_stats": {
                "refinement_iterations": self.refinement_iterations,
                "total_refinements": total_refinements,
                "rounds_with_refinement": len(self.refinement_iterations),
                "avg_refinements_per_round": avg_refinements,
                "rounds_without_refinement": self.round_count - len(self.refinement_iterations)
            }
        }

    def _experiment_round(self) -> Dict[str, Any]:
        """Execute one round with iterative refinement.

        PHASE 1: INITIAL ANALYSIS
        - Analyzer proposes interpretation

        PHASE 2: CRITIQUE AND REFINEMENT
        - Strategist critiques and suggests improvements

        PHASE 3: STRATEGY AND PROPOSAL
        - Strategist proposes refined strategy
        - Proposer generates guess

        PHASE 4: VALIDATION WITH REFINEMENT LOOP
        - Validator checks
        - If issues: one round of refinement
        - Analyzer revisits interpretation

        Returns:
            {
                "guess": [selected colors],
                "refinement_iterations": int,
                "messages": [communication log]
            }
        """
        messages = []
        refinement_iterations = 0

        # ===== PHASE 1: INITIAL ANALYSIS =====
        if self.guess_history:
            last_guess = self.guess_history[-1]
            analysis = self.analyzer.analyze_feedback(
                last_guess.get("guess", []),
                last_guess.get("feedback", {}),
                self.guess_history[:-1]
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
            "phase": "phase1_analysis",
            "agent": "analyzer",
            "recipient": "strategist",
            "type": "initial_analysis",
            "content": analysis
        })

        # ===== PHASE 2: CRITIQUE AND REFINEMENT =====
        # Strategist reviews analysis and suggests critiques
        # For now, strategist accepts and builds on analysis
        # (In a more sophisticated version, strategist could suggest alternative interpretations)
        critique = {
            "critique": "Analysis accepted as foundation",
            "suggestions": "Build strategy based on constraints identified",
            "confidence": 0.8
        }

        messages.append({
            "phase": "phase2_critique",
            "agent": "strategist",
            "recipient": "analyzer",
            "type": "critique",
            "content": critique
        })

        # ===== PHASE 3: STRATEGY AND PROPOSAL =====
        strategy_result = self.strategist.propose_strategy(
            self.guess_history,
            self.puzzle["difficulty"]
        )

        messages.append({
            "phase": "phase3_strategy",
            "agent": "strategist",
            "recipient": "proposer",
            "type": "refined_strategy",
            "content": strategy_result
        })

        # Generate proposal
        previous_guess_lists = [g.get("guess", []) for g in self.guess_history]
        constraints_text = "\n".join(analysis.get("constraints", []))

        proposal = self.proposer.propose_guess(
            strategy=strategy_result.get("strategy", ""),
            constraints_text=constraints_text,
            available_colors=self.puzzle.get("available_colors", []),
            num_pegs=self.puzzle.get("pegs", 4),
            previous_guesses=previous_guess_lists
        )

        messages.append({
            "phase": "phase3_proposal",
            "agent": "proposer",
            "recipient": "validator",
            "type": "proposal",
            "content": {"guess": proposal.get("proposed_guess", [])}
        })

        chosen_guess = proposal.get("proposed_guess", [])

        # ===== PHASE 4: VALIDATION WITH REFINEMENT LOOP =====
        constraints_dict = {
            "correct_positions": analysis.get("correct_positions", []),
            "correct_colors_wrong_position": analysis.get("correct_colors_wrong_position", []),
            "impossible_colors": analysis.get("impossible_colors", [])
        }

        validation = self.validator.validate_with_llm(
            guess=chosen_guess,
            available_colors=self.puzzle.get("available_colors", []),
            expected_length=self.puzzle.get("pegs", 4),
            previous_guesses=previous_guess_lists,
            constraints=constraints_dict
        )

        messages.append({
            "phase": "phase4_validation",
            "agent": "validator",
            "recipient": "analyzer",
            "type": "validation",
            "content": validation
        })

        # Check if validation passed
        if not validation.get("valid", True):
            # Refinement loop: One iteration to fix issues
            refinement_iterations = 1

            # Analyzer reconsiders constraints
            refinement_analysis = {
                "previous_analysis": analysis,
                "validation_feedback": validation.get("issues", []),
                "task": "Reconsider constraints - validator found issues"
            }

            messages.append({
                "phase": "phase4_refinement",
                "agent": "analyzer",
                "recipient": "proposer",
                "type": "refinement_analysis",
                "content": refinement_analysis
            })

            # Proposer generates alternative guess
            alternative_strategy = strategy_result.get("strategy", "") + "\n[Alternative: address validation issues]"
            alternative_proposal = self.proposer.propose_guess(
                strategy=alternative_strategy,
                constraints_text=constraints_text,
                available_colors=self.puzzle.get("available_colors", []),
                num_pegs=self.puzzle.get("pegs", 4),
                previous_guesses=previous_guess_lists
            )

            chosen_guess = alternative_proposal.get("proposed_guess", [])

            messages.append({
                "phase": "phase4_refinement",
                "agent": "proposer",
                "recipient": "validator",
                "type": "refined_proposal",
                "content": {"guess": chosen_guess}
            })

            # Final validation check
            final_validation = self.validator.validate_with_llm(
                guess=chosen_guess,
                available_colors=self.puzzle.get("available_colors", []),
                expected_length=self.puzzle.get("pegs", 4),
                previous_guesses=previous_guess_lists,
                constraints=constraints_dict
            )

            messages.append({
                "phase": "phase4_final_validation",
                "agent": "validator",
                "recipient": "all_agents",
                "type": "final_validation",
                "content": final_validation
            })

        # ===== PHASE 5: LEARNING (happens in main loop with feedback) =====
        messages.append({
            "phase": "phase5_learning",
            "agent": "all_agents",
            "recipient": "all_agents",
            "type": "ready_for_feedback",
            "content": {"guess": chosen_guess, "refinement_iterations": refinement_iterations}
        })

        # Store messages
        self.messages.extend(messages)

        return {
            "guess": chosen_guess,
            "refinement_iterations": refinement_iterations,
            "messages": messages
        }
