# Round-Table Paradigm
# Peer-to-peer collaboration: All agents equal, no Boss coordinator
# Agents call each other directly: Analyzer → Strategist → Proposer → Validator
# Sequential but without centralized control

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


class RoundTableOrchestrator:
    """Orchestrates Round-Table paradigm for solving Mastermind puzzles.

    Structure:
    - No Boss (centralized coordinator)
    - 4 Agents work as peers
    - Analyzer → Strategist → Proposer → Validator chain
    - Each agent passes results directly to next (no Boss in middle)
    - Agents have equal status, sequential workflow

    Difference from Boss-Worker:
    - Boss-Worker: Boss calls each agent, collects results, passes to next
    - Round-Table: Agents call each other directly (more direct communication)

    Metrics tracked:
    - Success (solved or not)
    - Efficiency (guesses, rounds)
    - Communication (messages, tokens)
    - Agent autonomy (who initiated calls)
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

        # Initialize agents (all equal status, no hierarchy)
        self.analyzer = AnalyzerAgent(provider=provider)
        self.strategist = StrategistAgent(provider=provider)
        self.proposer = ProposerAgent(provider=provider)
        self.validator = ValidatorAgent(provider=provider)

        self.logger = CommunicationLogger(puzzle["puzzle_id"], "round-table")
        self.guess_history = []
        self.round_count = 0
        self.start_time = time.time()
        self.messages = []  # Track communication between agents

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Round-Table paradigm.

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "round-table",
                "success": bool,
                "guesses": int,
                "rounds": int,
                "elapsed_time": float,
                "guess_history": list,
                "messages": list,
                "token_usage": dict,
                "agent_stats": dict
            }
        """
        while self.round_count < 8 and not self.game_engine.is_game_over():
            self.round_count += 1

            try:
                # Round-Table workflow: Agents call each other directly
                round_result = self._round_table_round()

                # Log all inter-agent messages
                for msg in round_result.get("messages", []):
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "round-table",
                        "sender": msg.get("agent", "unknown"),
                        "receiver": msg.get("recipient", "unknown"),
                        "message_type": msg.get("type", "unknown"),
                        "content": msg.get("content", {})
                    }
                    self.logger.log_message(log_entry)

                # Extract guess
                guess = round_result.get("guess", [])

                # Submit to game engine
                feedback = self.game_engine.submit_guess(guess)

                if not feedback.get("valid", False):
                    # Invalid guess - log and continue
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "round-table",
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
                    "feedback": feedback.get("feedback", {})
                })

                # Log feedback
                log_entry = {
                    "timestamp": time.time(),
                    "round_number": self.round_count,
                    "puzzle_id": self.puzzle["puzzle_id"],
                    "paradigm": "round-table",
                    "sender": "game_engine",
                    "receiver": "all_agents",
                    "message_type": "feedback",
                    "content": {
                        "guess_number": feedback.get("guess_number", 0),
                        "correct_pegs": feedback.get("feedback", {}).get("correct_pegs", 0),
                        "correct_positions": feedback.get("feedback", {}).get("correct_positions", 0),
                        "solved": feedback.get("solved", False),
                        "rounds_remaining": feedback.get("rounds_remaining", 0)
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
                    "paradigm": "round-table",
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
            "paradigm": "round-table",
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
            }
        }

    def _round_table_round(self) -> Dict[str, Any]:
        """Execute one round with peer-to-peer agent communication.

        Workflow:
        1. Analyzer reads feedback from last round
        2. Analyzer tells Strategist what was learned
        3. Strategist proposes strategy
        4. Strategist tells Proposer the strategy
        5. Proposer generates guess
        6. Proposer tells Validator the guess
        7. Validator checks it
        8. Validator returns approval/rejection

        Returns:
            {
                "guess": [list of colors],
                "messages": [inter-agent communication log]
            }
        """
        messages = []

        # Step 1: Analyzer reads feedback
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
            "recipient": "strategist",
            "type": "analysis",
            "content": analysis
        })

        # Step 2: Strategist receives analysis and proposes strategy
        strategy_result = self.strategist.propose_strategy(
            self.guess_history,
            self.puzzle["difficulty"]
        )

        messages.append({
            "agent": "strategist",
            "recipient": "proposer",
            "type": "strategy",
            "content": strategy_result
        })

        # Step 3: Proposer receives strategy and generates guess
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
            "agent": "proposer",
            "recipient": "validator",
            "type": "proposal",
            "content": proposal
        })

        # Step 4: Validator receives proposal and validates it
        guess = proposal.get("proposed_guess", [])

        # Build constraints dict for validator
        constraints_dict = {
            "correct_positions": analysis.get("correct_positions", []),
            "correct_colors_wrong_position": analysis.get("correct_colors_wrong_position", []),
            "impossible_colors": analysis.get("impossible_colors", [])
        }

        validation = self.validator.validate_with_llm(
            guess=guess,
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

        # Store messages for later
        self.messages.extend(messages)

        return {
            "guess": guess,
            "messages": messages
        }
