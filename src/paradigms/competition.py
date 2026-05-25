# Competition Paradigm
# Multiple agents compete: Each proposes a guess independently
# Evaluator picks the best guess based on informativeness
# Hypothesis: Multiple perspectives lead to better guesses

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


class CompetitionOrchestrator:
    """Orchestrates Competition paradigm for solving Mastermind puzzles.

    Structure:
    - Shared: Analyzer extracts constraints (all agree on facts)
    - Shared: Strategist proposes strategy (all agree on approach)
    - Competition: 3 different Proposers generate guesses independently
      * Proposer 1: Conservative (careful, tested colors)
      * Proposer 2: Aggressive (bold, new colors)
      * Proposer 3: Balanced (middle ground)
    - Evaluator: Picks best guess based on informativeness
    - Validator: Quality check before submission

    Hypothesis:
    - Multiple strategies might reveal better guesses
    - Different risk profiles (conservative vs aggressive) both useful
    - More perspectives = more robust solution

    Metrics tracked:
    - Success (solved or not)
    - Efficiency (guesses, rounds)
    - Communication (messages, tokens)
    - Competition metrics (which proposer won? strategy effectiveness)
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

        # Shared agents (analyze once, use for all proposers)
        self.analyzer = AnalyzerAgent(provider=provider)
        self.strategist = StrategistAgent(provider=provider)

        # Competing proposers (generate proposals independently)
        self.proposer_conservative = ProposerAgent(provider=provider)
        self.proposer_aggressive = ProposerAgent(provider=provider)
        self.proposer_balanced = ProposerAgent(provider=provider)

        # Validators and evaluator
        self.validator = ValidatorAgent(provider=provider)

        self.logger = CommunicationLogger(puzzle["puzzle_id"], "competition")
        self.guess_history = []
        self.round_count = 0
        self.start_time = time.time()
        self.messages = []

        # Track which proposer won each round
        self.proposer_wins = {
            "conservative": 0,
            "aggressive": 0,
            "balanced": 0
        }

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Competition paradigm.

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "competition",
                "success": bool,
                "guesses": int,
                "rounds": int,
                "elapsed_time": float,
                "guess_history": list,
                "messages": list,
                "token_usage": dict,
                "agent_stats": dict,
                "competition_stats": dict  # Which proposer won most
            }
        """
        while self.round_count < 8 and not self.game_engine.is_game_over():
            self.round_count += 1

            try:
                # Competition round: Multiple proposers compete
                round_result = self._competition_round()

                # Log all messages
                for msg in round_result.get("messages", []):
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "competition",
                        "sender": msg.get("agent", "unknown"),
                        "receiver": msg.get("recipient", "unknown"),
                        "message_type": msg.get("type", "unknown"),
                        "content": msg.get("content", {})
                    }
                    self.logger.log_message(log_entry)

                # Extract chosen guess
                guess = round_result.get("guess", [])
                winner = round_result.get("winner", "unknown")

                # Track wins
                self.proposer_wins[winner] += 1

                # Submit to game engine
                feedback = self.game_engine.submit_guess(guess)

                if not feedback.get("valid", False):
                    # Invalid guess
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "competition",
                        "sender": "game_engine",
                        "receiver": "evaluator",
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
                    "winner": winner  # Track which proposer won this round
                })

                # Log feedback
                log_entry = {
                    "timestamp": time.time(),
                    "round_number": self.round_count,
                    "puzzle_id": self.puzzle["puzzle_id"],
                    "paradigm": "competition",
                    "sender": "game_engine",
                    "receiver": "all_agents",
                    "message_type": "feedback",
                    "content": {
                        "guess_number": feedback.get("guess_number", 0),
                        "correct_pegs": feedback.get("feedback", {}).get("correct_pegs", 0),
                        "correct_positions": feedback.get("feedback", {}).get("correct_positions", 0),
                        "solved": feedback.get("solved", False),
                        "winner": winner  # Note which strategy won this round
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
                    "paradigm": "competition",
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
            "paradigm": "competition",
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
            "competition_stats": {
                "proposer_wins": self.proposer_wins,
                "most_effective": max(self.proposer_wins, key=self.proposer_wins.get),
                "win_rates": {
                    "conservative": self.proposer_wins["conservative"] / max(1, self.round_count),
                    "aggressive": self.proposer_wins["aggressive"] / max(1, self.round_count),
                    "balanced": self.proposer_wins["balanced"] / max(1, self.round_count)
                }
            }
        }

    def _competition_round(self) -> Dict[str, Any]:
        """Execute one round with competing proposers.

        Workflow:
        1. Analyzer extracts constraints (once, shared)
        2. Strategist proposes strategy (once, shared)
        3. Three Proposers generate guesses independently:
           - Conservative: Use tested colors, minimize risk
           - Aggressive: Test new colors, maximize info
           - Balanced: Mix of both strategies
        4. Evaluator picks best guess based on informativeness
        5. Validator checks it
        6. Submit chosen guess

        Returns:
            {
                "guess": [selected colors],
                "winner": "conservative" | "aggressive" | "balanced",
                "messages": [communication log]
            }
        """
        messages = []

        # Step 1: Shared Analysis
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
            "agent": "analyzer",
            "recipient": "all_proposers",
            "type": "shared_analysis",
            "content": analysis
        })

        # Step 2: Shared Strategy
        strategy_result = self.strategist.propose_strategy(
            self.guess_history,
            self.puzzle["difficulty"]
        )

        messages.append({
            "agent": "strategist",
            "recipient": "all_proposers",
            "type": "shared_strategy",
            "content": strategy_result
        })

        # Step 3: Three Proposers Generate Independently
        previous_guess_lists = [g.get("guess", []) for g in self.guess_history]
        constraints_text = "\n".join(analysis.get("constraints", []))

        # Conservative proposer: "Use safe, tested colors"
        conservative_strategy = strategy_result.get("strategy", "") + "\nApproach: Conservative - prefer tested colors over new ones"
        proposal_conservative = self.proposer_conservative.propose_guess(
            strategy=conservative_strategy,
            constraints_text=constraints_text,
            available_colors=self.puzzle.get("available_colors", []),
            num_pegs=self.puzzle.get("pegs", 4),
            previous_guesses=previous_guess_lists
        )

        messages.append({
            "agent": "proposer_conservative",
            "recipient": "evaluator",
            "type": "proposal",
            "content": {
                "guess": proposal_conservative.get("proposed_guess", []),
                "strategy": "Conservative",
                "rationale": "Minimize risk, use tested colors"
            }
        })

        # Aggressive proposer: "Test new colors aggressively"
        aggressive_strategy = strategy_result.get("strategy", "") + "\nApproach: Aggressive - test new colors to gain maximum information"
        proposal_aggressive = self.proposer_aggressive.propose_guess(
            strategy=aggressive_strategy,
            constraints_text=constraints_text,
            available_colors=self.puzzle.get("available_colors", []),
            num_pegs=self.puzzle.get("pegs", 4),
            previous_guesses=previous_guess_lists
        )

        messages.append({
            "agent": "proposer_aggressive",
            "recipient": "evaluator",
            "type": "proposal",
            "content": {
                "guess": proposal_aggressive.get("proposed_guess", []),
                "strategy": "Aggressive",
                "rationale": "Maximize information gain, test new colors"
            }
        })

        # Balanced proposer: "Mix safe and new"
        balanced_strategy = strategy_result.get("strategy", "") + "\nApproach: Balanced - mix tested colors with some new ones"
        proposal_balanced = self.proposer_balanced.propose_guess(
            strategy=balanced_strategy,
            constraints_text=constraints_text,
            available_colors=self.puzzle.get("available_colors", []),
            num_pegs=self.puzzle.get("pegs", 4),
            previous_guesses=previous_guess_lists
        )

        messages.append({
            "agent": "proposer_balanced",
            "recipient": "evaluator",
            "type": "proposal",
            "content": {
                "guess": proposal_balanced.get("proposed_guess", []),
                "strategy": "Balanced",
                "rationale": "Balance risk and information"
            }
        })

        # Step 4: Evaluator Picks Best
        winner = self._evaluate_proposals(
            proposal_conservative.get("proposed_guess", []),
            proposal_aggressive.get("proposed_guess", []),
            proposal_balanced.get("proposed_guess", []),
            analysis
        )

        messages.append({
            "agent": "evaluator",
            "recipient": "validator",
            "type": "selection",
            "content": {
                "winner": winner,
                "rationale": f"Selected {winner} proposer"
            }
        })

        # Get the winning guess
        if winner == "conservative":
            chosen_guess = proposal_conservative.get("proposed_guess", [])
        elif winner == "aggressive":
            chosen_guess = proposal_aggressive.get("proposed_guess", [])
        else:  # balanced
            chosen_guess = proposal_balanced.get("proposed_guess", [])

        # Step 5: Validator checks it
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
            "agent": "validator",
            "recipient": "all",
            "type": "validation",
            "content": validation
        })

        # Store messages
        self.messages.extend(messages)

        return {
            "guess": chosen_guess,
            "winner": winner,
            "messages": messages
        }

    def _evaluate_proposals(
        self,
        guess_conservative: List[str],
        guess_aggressive: List[str],
        guess_balanced: List[str],
        analysis: Dict[str, Any]
    ) -> str:
        """Evaluate which proposal is best.

        Criteria:
        1. Respects constraints (all should, but rank by safety)
        2. Informativeness (which eliminates most possibilities?)
        3. Diversity (different from previous guesses)

        Args:
            guess_conservative: Proposal from conservative proposer
            guess_aggressive: Proposal from aggressive proposer
            guess_balanced: Proposal from balanced proposer
            analysis: Current constraint analysis

        Returns:
            "conservative" | "aggressive" | "balanced"
        """
        # Simple heuristic: At early rounds, prefer balanced/aggressive
        # At later rounds, prefer conservative (safer)
        round_ratio = self.round_count / 8.0

        # Score each proposal
        scores = {
            "conservative": self._score_guess(guess_conservative, 0.3 + round_ratio * 0.4),  # More safe later
            "aggressive": self._score_guess(guess_aggressive, 0.7 - round_ratio * 0.4),      # More bold early
            "balanced": self._score_guess(guess_balanced, 0.5)                                # Always balanced
        }

        # Return highest scoring
        return max(scores, key=scores.get)

    def _score_guess(self, guess: List[str], risk_tolerance: float) -> float:
        """Score a guess based on characteristics.

        Args:
            guess: The guess to score
            risk_tolerance: 0.0 (conservative) to 1.0 (aggressive)

        Returns:
            Score (higher is better)
        """
        if not guess:
            return 0.0

        # Score based on unique colors (higher is more informative)
        unique_count = len(set(guess))
        uniqueness_score = unique_count / len(guess)  # 0.0 to 1.0

        # Combine with risk tolerance
        # At risk_tolerance=1.0: prefer high uniqueness
        # At risk_tolerance=0.0: prefer lower uniqueness (tested colors)
        score = uniqueness_score * risk_tolerance + (1 - risk_tolerance) * (1 - uniqueness_score)

        # Slight bonus for having more unique colors
        score += uniqueness_score * 0.1

        return score
