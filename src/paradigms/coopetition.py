# Coopetition Paradigm
# Hybrid: Cooperation + Competition + Feedback
# Phase 1: Agents cooperate to extract constraints
# Phase 2: Proposers compete to generate best guess
# Phase 3: All agents learn from feedback
# Hypothesis: Best of both worlds - efficiency + robustness

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


class CoopetitionOrchestrator:
    """Orchestrates Coopetition paradigm for solving Mastermind puzzles.

    Structure: Three Phases Per Round

    PHASE 1: COOPERATION (Shared Learning)
      - Analyzer extracts constraints
      - Strategist plans strategy
      - All agents share results
      - Goal: Common understanding of puzzle state

    PHASE 2: COMPETITION (Diverse Proposals)
      - Multiple Proposers generate guesses independently
      - Different risk profiles (conservative, aggressive, balanced)
      - Evaluator picks best
      - Goal: Find best guess from multiple perspectives

    PHASE 3: FEEDBACK (Shared Learning)
      - All agents see result
      - Learn what worked
      - Prepare context for next round
      - Goal: Improve collective knowledge

    Hypothesis:
    - Cooperation: Efficient shared analysis (vs everyone analyzing)
    - Competition: Robust multiple perspectives (vs single proposal)
    - Feedback: Continuous learning (vs isolated decisions)
    - Result: Better than pure cooperation OR pure competition alone

    Metrics tracked:
    - Success (solved or not)
    - Efficiency (guesses, rounds)
    - Communication (messages, tokens)
    - Competition metrics (which proposer won, how often)
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

        # Cooperation Phase: Shared agents
        self.analyzer = AnalyzerAgent(provider=provider)
        self.strategist = StrategistAgent(provider=provider)

        # Competition Phase: Competing proposers
        self.proposer_conservative = ProposerAgent(provider=provider)
        self.proposer_aggressive = ProposerAgent(provider=provider)
        self.proposer_balanced = ProposerAgent(provider=provider)

        # Evaluation and validation
        self.validator = ValidatorAgent(provider=provider)

        self.logger = CommunicationLogger(puzzle["puzzle_id"], "coopetition")
        self.guess_history = []
        self.round_count = 0
        self.start_time = time.time()
        self.messages = []

        # Track competition outcomes
        self.proposer_wins = {
            "conservative": 0,
            "aggressive": 0,
            "balanced": 0
        }

        # Track shared context improvements
        self.shared_contexts = []  # All constraints learned so far

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Coopetition paradigm.

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "coopetition",
                "success": bool,
                "guesses": int,
                "rounds": int,
                "elapsed_time": float,
                "guess_history": list,
                "messages": list,
                "token_usage": dict,
                "agent_stats": dict,
                "coopetition_stats": dict  # Phases and effectiveness
            }
        """
        while self.round_count < 8 and not self.game_engine.is_game_over():
            self.round_count += 1

            try:
                # Coopetition round: Cooperation → Competition → Feedback
                round_result = self._coopetition_round()

                # Log all messages
                for msg in round_result.get("messages", []):
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "coopetition",
                        "phase": msg.get("phase", "unknown"),
                        "sender": msg.get("agent", "unknown"),
                        "receiver": msg.get("recipient", "unknown"),
                        "message_type": msg.get("type", "unknown"),
                        "content": msg.get("content", {})
                    }
                    self.logger.log_message(log_entry)

                # Extract guess and competition results
                guess = round_result.get("guess", [])
                winner = round_result.get("winner", "unknown")
                shared_analysis = round_result.get("shared_analysis", {})

                # Track competition
                self.proposer_wins[winner] += 1

                # Track shared context
                self.shared_contexts.append(shared_analysis)

                # Submit to game engine
                feedback = self.game_engine.submit_guess(guess)

                if not feedback.get("valid", False):
                    # Invalid guess
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "coopetition",
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
                    "winner": winner
                })

                # Log feedback
                log_entry = {
                    "timestamp": time.time(),
                    "round_number": self.round_count,
                    "puzzle_id": self.puzzle["puzzle_id"],
                    "paradigm": "coopetition",
                    "phase": "feedback",
                    "sender": "game_engine",
                    "receiver": "all_agents",
                    "message_type": "feedback",
                    "content": {
                        "guess_number": feedback.get("guess_number", 0),
                        "correct_pegs": feedback.get("feedback", {}).get("correct_pegs", 0),
                        "correct_positions": feedback.get("feedback", {}).get("correct_positions", 0),
                        "solved": feedback.get("solved", False),
                        "winner": winner
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
                    "paradigm": "coopetition",
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

        return {
            "puzzle_id": self.puzzle["puzzle_id"],
            "paradigm": "coopetition",
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
                "proposer_conservative": self.proposer_conservative.total_input_tokens + self.proposer_conservative.total_output_tokens,
                "proposer_aggressive": self.proposer_aggressive.total_input_tokens + self.proposer_aggressive.total_output_tokens,
                "proposer_balanced": self.proposer_balanced.total_input_tokens + self.proposer_balanced.total_output_tokens,
                "validator": self.validator.total_input_tokens + self.validator.total_output_tokens,
                "total": (
                    self.analyzer.total_input_tokens + self.analyzer.total_output_tokens +
                    self.strategist.total_input_tokens + self.strategist.total_output_tokens +
                    self.proposer_conservative.total_input_tokens + self.proposer_conservative.total_output_tokens +
                    self.proposer_aggressive.total_input_tokens + self.proposer_aggressive.total_output_tokens +
                    self.proposer_balanced.total_input_tokens + self.proposer_balanced.total_output_tokens +
                    self.validator.total_input_tokens + self.validator.total_output_tokens
                )
            },
            "agent_stats": {
                "analyzer": self.analyzer.get_stats(),
                "strategist": self.strategist.get_stats(),
                "proposer_conservative": self.proposer_conservative.get_stats(),
                "proposer_aggressive": self.proposer_aggressive.get_stats(),
                "proposer_balanced": self.proposer_balanced.get_stats(),
                "validator": self.validator.get_stats()
            },
            "coopetition_stats": {
                "proposer_wins": self.proposer_wins,
                "most_effective": max(self.proposer_wins, key=self.proposer_wins.get),
                "win_rates": {
                    "conservative": self.proposer_wins["conservative"] / max(1, self.round_count),
                    "aggressive": self.proposer_wins["aggressive"] / max(1, self.round_count),
                    "balanced": self.proposer_wins["balanced"] / max(1, self.round_count)
                },
                "phases": {
                    "cooperation_calls": self.round_count,  # One per round
                    "competition_calls": self.round_count * 3,  # 3 proposers per round
                    "feedback_rounds": self.round_count  # Learning phase per round
                }
            }
        }

    def _coopetition_round(self) -> Dict[str, Any]:
        """Execute one round with three phases.

        PHASE 1: COOPERATION
        - Analyzer and Strategist work together
        - Extract shared constraints
        - Plan shared strategy

        PHASE 2: COMPETITION
        - Three proposers generate independently
        - Different approaches (conservative, aggressive, balanced)
        - Evaluator picks best

        PHASE 3: FEEDBACK
        - All agents see result
        - Learn from feedback
        - Prepare for next round

        Returns:
            {
                "guess": [selected colors],
                "winner": "conservative" | "aggressive" | "balanced",
                "shared_analysis": {...},
                "messages": [communication log]
            }
        """
        messages = []

        # ===== PHASE 1: COOPERATION =====
        # All agents work together to understand puzzle state

        # Shared Analysis
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
            "phase": "cooperation",
            "agent": "analyzer",
            "recipient": "all_agents",
            "type": "shared_analysis",
            "content": analysis
        })

        # Shared Strategy
        strategy_result = self.strategist.propose_strategy(
            self.guess_history,
            self.puzzle["difficulty"]
        )

        messages.append({
            "phase": "cooperation",
            "agent": "strategist",
            "recipient": "all_agents",
            "type": "shared_strategy",
            "content": strategy_result
        })

        # Store shared analysis for context building
        shared_analysis = {
            "analysis": analysis,
            "strategy": strategy_result
        }

        # ===== PHASE 2: COMPETITION =====
        # Proposers compete with different strategies

        previous_guess_lists = [g.get("guess", []) for g in self.guess_history]
        constraints_text = "\n".join(analysis.get("constraints", []))

        # Conservative proposer
        conservative_strategy = strategy_result.get("strategy", "") + "\nApproach: Conservative"
        proposal_conservative = self.proposer_conservative.propose_guess(
            strategy=conservative_strategy,
            constraints_text=constraints_text,
            available_colors=self.puzzle.get("available_colors", []),
            num_pegs=self.puzzle.get("pegs", 4),
            previous_guesses=previous_guess_lists
        )

        messages.append({
            "phase": "competition",
            "agent": "proposer_conservative",
            "recipient": "evaluator",
            "type": "proposal",
            "content": {"guess": proposal_conservative.get("proposed_guess", [])}
        })

        # Aggressive proposer
        aggressive_strategy = strategy_result.get("strategy", "") + "\nApproach: Aggressive"
        proposal_aggressive = self.proposer_aggressive.propose_guess(
            strategy=aggressive_strategy,
            constraints_text=constraints_text,
            available_colors=self.puzzle.get("available_colors", []),
            num_pegs=self.puzzle.get("pegs", 4),
            previous_guesses=previous_guess_lists
        )

        messages.append({
            "phase": "competition",
            "agent": "proposer_aggressive",
            "recipient": "evaluator",
            "type": "proposal",
            "content": {"guess": proposal_aggressive.get("proposed_guess", [])}
        })

        # Balanced proposer
        balanced_strategy = strategy_result.get("strategy", "") + "\nApproach: Balanced"
        proposal_balanced = self.proposer_balanced.propose_guess(
            strategy=balanced_strategy,
            constraints_text=constraints_text,
            available_colors=self.puzzle.get("available_colors", []),
            num_pegs=self.puzzle.get("pegs", 4),
            previous_guesses=previous_guess_lists
        )

        messages.append({
            "phase": "competition",
            "agent": "proposer_balanced",
            "recipient": "evaluator",
            "type": "proposal",
            "content": {"guess": proposal_balanced.get("proposed_guess", [])}
        })

        # Evaluator picks best
        winner = self._evaluate_proposals(
            proposal_conservative.get("proposed_guess", []),
            proposal_aggressive.get("proposed_guess", []),
            proposal_balanced.get("proposed_guess", []),
            analysis
        )

        messages.append({
            "phase": "competition",
            "agent": "evaluator",
            "recipient": "validator",
            "type": "selection",
            "content": {"winner": winner}
        })

        # Get chosen guess
        if winner == "conservative":
            chosen_guess = proposal_conservative.get("proposed_guess", [])
        elif winner == "aggressive":
            chosen_guess = proposal_aggressive.get("proposed_guess", [])
        else:
            chosen_guess = proposal_balanced.get("proposed_guess", [])

        # Validator checks
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
            "phase": "competition",
            "agent": "validator",
            "recipient": "all_agents",
            "type": "validation",
            "content": validation
        })

        # ===== PHASE 3: FEEDBACK =====
        # All agents will learn from feedback after submission
        # (Actual feedback comes from game engine in main loop)

        messages.append({
            "phase": "feedback",
            "agent": "all_agents",
            "recipient": "all_agents",
            "type": "ready_for_feedback",
            "content": {"winner": winner, "guess": chosen_guess}
        })

        # Store messages
        self.messages.extend(messages)

        return {
            "guess": chosen_guess,
            "winner": winner,
            "shared_analysis": shared_analysis,
            "messages": messages
        }

    def _evaluate_proposals(
        self,
        guess_conservative: List[str],
        guess_aggressive: List[str],
        guess_balanced: List[str],
        analysis: Dict[str, Any]
    ) -> str:
        """Evaluate proposals (same logic as Competition)."""
        round_ratio = self.round_count / 8.0

        scores = {
            "conservative": self._score_guess(guess_conservative, 0.3 + round_ratio * 0.4),
            "aggressive": self._score_guess(guess_aggressive, 0.7 - round_ratio * 0.4),
            "balanced": self._score_guess(guess_balanced, 0.5)
        }

        return max(scores, key=scores.get)

    def _score_guess(self, guess: List[str], risk_tolerance: float) -> float:
        """Score guess (same logic as Competition)."""
        if not guess:
            return 0.0

        unique_count = len(set(guess))
        uniqueness_score = unique_count / len(guess)

        score = uniqueness_score * risk_tolerance + (1 - risk_tolerance) * (1 - uniqueness_score)
        score += uniqueness_score * 0.1

        return score
