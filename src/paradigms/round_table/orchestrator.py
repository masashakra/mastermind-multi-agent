# Round-Table Paradigm Orchestrator
# Peer-to-peer collaboration. All agents equal, can communicate directly via A2A

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
from typing import Dict, Any, List

from game_engine import GameEngine
from puzzle_generator import load_puzzles
from communication.protocol import A2ACommunicationLayer
from paradigms.round_table.agents import (
    AnalyzerAgent,
    StrategistAgent,
    ProposerAgent,
    ValidatorAgent,
    LoggerAgent,
    MetricsAgent,
)


class RoundTableOrchestrator:
    """Orchestrates the Round-Table paradigm (peer-to-peer collaboration)

    Structure:
    - No boss/coordinator
    - All 4 agents are peers with equal status
    - Agents can communicate directly with each other via A2A
    - Orchestrator initiates workflow but agents can also message each other
    - Round-table discussions where all voices are heard equally
    """

    def __init__(self, puzzle: Dict[str, Any], provider: str = "ollama"):
        """Initialize orchestrator for one puzzle

        Args:
            puzzle: Puzzle dictionary from puzzle_generator
            provider: LLM provider ("ollama", "groq", "claude", "kaggle")
        """
        self.puzzle = puzzle
        self.provider = provider
        self.paradigm = "round_table"
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])
        self.start_time = time.time()

        # A2A Communication (in-process only for round-table)
        self.comm_layer = A2ACommunicationLayer()

        # Initialize all agents as peers (no boss/hierarchy)
        self.analyzer = AnalyzerAgent(provider=provider, comm_layer=self.comm_layer)
        self.strategist = StrategistAgent(provider=provider, comm_layer=self.comm_layer)
        self.proposer = ProposerAgent(provider=provider, comm_layer=self.comm_layer)
        self.validator = ValidatorAgent(provider=provider, comm_layer=self.comm_layer)
        self.logger = LoggerAgent(paradigm_name=self.paradigm)
        self.metrics = MetricsAgent(paradigm_name=self.paradigm)

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Round-Table paradigm

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "round_table",
                "success": bool,
                "guesses": int,
                "rounds": int,
                "elapsed_time": float,
                "guess_history": list,
                "message_count": int,
                "token_usage": dict,
                "agent_stats": dict
            }
        """
        guess_history = []
        round_count = 0

        while round_count < 8 and not self.game_engine.is_game_over():
            round_count += 1

            try:
                # Step 1: Analyzer - All agents listen to analysis (peer input)
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
                        "analysis": "First round - all codes possible",
                        "confidence": 0.5
                    }

                # Log analysis (peer contribution)
                self.logger.log_message({
                    "message_type": "analysis",
                    "sender": "analyzer",
                    "receiver": "all_peers",
                    "round": round_count,
                    "content": analysis
                })

                # Step 2: Strategist - Peer proposes strategy based on analysis
                strategy = self.strategist.propose_strategy(
                    guess_history,
                    self.puzzle["difficulty"]
                )

                # Log strategy (peer contribution)
                self.logger.log_message({
                    "message_type": "strategy",
                    "sender": "strategist",
                    "receiver": "all_peers",
                    "round": round_count,
                    "content": strategy
                })

                # Step 3: Proposer - Peer generates guess based on strategy
                constraints_text = "\n".join(analysis.get("constraints", []))
                proposal = self.proposer.propose_guess(
                    strategy=strategy.get("strategy", ""),
                    constraints_text=constraints_text,
                    available_colors=self.puzzle.get("available_colors", []),
                    num_pegs=self.puzzle.get("pegs", 4),
                    previous_guesses=[g.get("guess", []) for g in guess_history]
                )

                # Log proposal (peer contribution)
                self.logger.log_message({
                    "message_type": "proposal",
                    "sender": "proposer",
                    "receiver": "all_peers",
                    "round": round_count,
                    "content": proposal
                })

                # Step 4: Validator - Peer validates guess for whole table
                guess = proposal.get("proposed_guess", [])
                validation = self.validator.validate_guess(
                    guess=guess,
                    available_colors=self.puzzle.get("available_colors", []),
                    expected_length=self.puzzle.get("pegs", 4),
                    previous_guesses=[g.get("guess", []) for g in guess_history],
                    constraints={
                        "correct_positions": analysis.get("correct_positions", []),
                        "correct_colors_wrong_position": analysis.get("correct_colors_wrong_position", []),
                        "impossible_colors": analysis.get("impossible_colors", [])
                    }
                )

                # Log validation (peer feedback)
                self.logger.log_message({
                    "message_type": "validation",
                    "sender": "validator",
                    "receiver": "all_peers",
                    "round": round_count,
                    "content": validation
                })

                # If validation fails, table discusses and retries
                if not validation.get("valid", True):
                    self.logger.log_message({
                        "message_type": "discussion",
                        "sender": "table",
                        "receiver": "all_peers",
                        "round": round_count,
                        "content": {"discussion": "Invalid guess, round table discussing alternatives", "violations": validation.get("hard_violations", [])}
                    })
                    continue

                # Step 5: Submit guess to game engine
                feedback = self.game_engine.submit_guess(guess)

                if not feedback.get("valid", False):
                    self.logger.log_message({
                        "message_type": "error",
                        "sender": "game_engine",
                        "receiver": "all_peers",
                        "round": round_count,
                        "content": {"error": feedback.get("error", "Invalid guess")}
                    })
                    continue

                # Record in history
                guess_history.append({
                    "round": round_count,
                    "guess": guess,
                    "feedback": feedback.get("feedback", {})
                })

                # Log feedback (shared knowledge)
                self.logger.log_message({
                    "message_type": "feedback",
                    "sender": "game_engine",
                    "receiver": "all_peers",
                    "round": round_count,
                    "content": {
                        "correct_pegs": feedback.get("feedback", {}).get("correct_pegs", 0),
                        "correct_positions": feedback.get("feedback", {}).get("correct_positions", 0),
                        "solved": feedback.get("solved", False)
                    }
                })

                # Record metrics
                self.metrics.record_metric("round", round_count)
                self.metrics.record_metric("guess", str(guess))
                self.metrics.record_metric("correct_pegs", feedback.get("feedback", {}).get("correct_pegs", 0))
                self.metrics.record_metric("correct_positions", feedback.get("feedback", {}).get("correct_positions", 0))

                # Check if solved
                if feedback.get("solved", False):
                    break

            except Exception as e:
                self.logger.log_message({
                    "message_type": "error",
                    "sender": "orchestrator",
                    "receiver": "all_peers",
                    "round": round_count,
                    "content": {"error": str(e)}
                })
                continue

        elapsed_time = time.time() - self.start_time

        # Determine success
        success = False
        if guess_history:
            last_feedback = guess_history[-1].get("feedback", {})
            success = last_feedback.get("correct_positions", 0) == self.puzzle.get("pegs", 4)

        # Save metrics
        self.metrics.record_metric("total_guesses", len(guess_history))
        self.metrics.record_metric("total_rounds", round_count)
        self.metrics.record_metric("success", success)
        self.metrics.save_metrics()

        return {
            "puzzle_id": self.puzzle["puzzle_id"],
            "paradigm": self.paradigm,
            "difficulty": self.puzzle["difficulty"],
            "success": success,
            "guesses": len(guess_history),
            "rounds": round_count,
            "elapsed_time": elapsed_time,
            "guess_history": guess_history,
            "message_count": len(self.logger.logs),
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
                "analyzer": {"calls": self.analyzer.call_count, "tokens": self.analyzer.total_input_tokens + self.analyzer.total_output_tokens},
                "strategist": {"calls": self.strategist.call_count, "tokens": self.strategist.total_input_tokens + self.strategist.total_output_tokens},
                "proposer": {"calls": self.proposer.call_count, "tokens": self.proposer.total_input_tokens + self.proposer.total_output_tokens},
                "validator": {"calls": self.validator.call_count, "tokens": self.validator.total_input_tokens + self.validator.total_output_tokens},
            }
        }


if __name__ == "__main__":
    # Test: Run one puzzle
    print("=" * 80)
    print("ROUND-TABLE PARADIGM TEST")
    print("=" * 80)

    try:
        puzzles = load_puzzles()
        test_puzzle = next(p for p in puzzles if p['difficulty'] == 'easy')

        print(f"\nTesting puzzle: {test_puzzle['puzzle_id']}")
        print(f"Difficulty: {test_puzzle['difficulty']}")

        orchestrator = RoundTableOrchestrator(test_puzzle, provider="ollama")
        result = orchestrator.run()

        print(f"\nResult:")
        print(f"  Success: {result['success']}")
        print(f"  Guesses: {result['guesses']}")
        print(f"  Rounds: {result['rounds']}")
        print(f"  Time: {result['elapsed_time']:.1f}s")
        print(f"  Messages: {result['message_count']}")
        print(f"  Tokens: {result['token_usage']['total']}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
