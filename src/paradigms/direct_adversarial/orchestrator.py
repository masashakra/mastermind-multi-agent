# Direct Adversarial Paradigm Orchestrator
# 3 competing agents proposing different guesses

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
from typing import Dict, Any, List

from game_engine import GameEngine
from puzzle_generator import load_puzzles
from communication.protocol import A2ACommunicationLayer
from registry.registry import get_global_registry
from paradigms.direct_adversarial.agents import (
    AnalyzerAgent,
    StrategistAgent,
    ProposerAgent,
    ValidatorAgent,
    LoggerAgent,
    MetricsAgent,
)


class DirectAdversarialOrchestrator:
    """Orchestrates the Direct Adversarial paradigm

    Structure:
    - 3 agents compete directly to solve the puzzle
    - Each proposes different strategies and guesses
    - Orchestrator selects winner or tries each guess
    - Competitive coordination without mediation
    """

    def __init__(self, puzzle: Dict[str, Any], provider: str = "deepseek"):
        """Initialize orchestrator for one puzzle

        Args:
            puzzle: Puzzle dictionary from puzzle_generator
            provider: LLM provider ("deepseek", "groq", "claude", "kaggle")
        """
        self.puzzle = puzzle
        self.provider = provider
        self.paradigm = "direct_adversarial"
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])
        self.start_time = time.time()

        # A2A Communication
        self.comm_layer = A2ACommunicationLayer()
        self.registry = get_global_registry(self.comm_layer)

        # Initialize agents (competing teams)
        self.analyzer = AnalyzerAgent(provider=provider, comm_layer=self.comm_layer)
        self.strategist = StrategistAgent(provider=provider, comm_layer=self.comm_layer)
        self.proposer = ProposerAgent(provider=provider, comm_layer=self.comm_layer)
        self.validator = ValidatorAgent(provider=provider, comm_layer=self.comm_layer)
        self.logger = LoggerAgent(paradigm_name=self.paradigm)
        self.metrics = MetricsAgent(paradigm_name=self.paradigm)

        # Register agents as competitors
        self.registry.register_agent({"agent_id": "analyzer", "agent_name": "Analyzer", "agent_type": "analyzer", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "strategist", "agent_name": "Strategist", "agent_type": "strategist", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "proposer", "agent_name": "Proposer", "agent_type": "proposer", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "validator", "agent_name": "Validator", "agent_type": "validator", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "logger", "agent_name": "Logger", "agent_type": "logger", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "metrics", "agent_name": "Metrics", "agent_type": "metrics", "paradigm": self.paradigm})

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Direct Adversarial paradigm

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "direct_adversarial",
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
                # Step 1: Analyzer - Analyze current state
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

                # Log analysis
                self.logger.log_message({
                    "message_type": "analysis",
                    "sender": "analyzer",
                    "receiver": "competitors",
                    "round": round_count,
                    "content": analysis
                })

                # Step 2: Strategist - Propose competing strategy
                strategy = self.strategist.propose_strategy(
                    guess_history,
                    self.puzzle["difficulty"]
                )

                # Log strategy
                self.logger.log_message({
                    "message_type": "strategy",
                    "sender": "strategist",
                    "receiver": "competitors",
                    "round": round_count,
                    "content": strategy
                })

                # Step 3: Proposer - Generate 3 competing proposals
                constraints_text = "\n".join(analysis.get("constraints", []))
                proposals = []
                for attempt in range(3):  # 3 competing proposals
                    proposal = self.proposer.propose_guess(
                        strategy=strategy.get("strategy", ""),
                        constraints_text=constraints_text,
                        available_colors=self.puzzle.get("available_colors", []),
                        num_pegs=self.puzzle.get("pegs", 4),
                        previous_guesses=[g.get("guess", []) for g in guess_history]
                    )
                    proposals.append(proposal)

                # Log competing proposals
                self.logger.log_message({
                    "message_type": "competing_proposals",
                    "sender": "proposer",
                    "receiver": "all",
                    "round": round_count,
                    "content": {"proposals": proposals, "competition": "3-way competition"}
                })

                # Step 4: Validator - Validate all proposals, pick first valid
                selected_proposal = None
                for i, proposal in enumerate(proposals):
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

                    if validation.get("valid", False):
                        selected_proposal = {
                            "proposal": proposal,
                            "validation": validation,
                            "proposal_index": i
                        }
                        break

                # Log competition result
                if selected_proposal:
                    self.logger.log_message({
                        "message_type": "competition_winner",
                        "sender": "validator",
                        "receiver": "all",
                        "round": round_count,
                        "content": {"winner_index": selected_proposal["proposal_index"]}
                    })
                else:
                    self.logger.log_message({
                        "message_type": "competition_failed",
                        "sender": "validator",
                        "receiver": "all",
                        "round": round_count,
                        "content": {"reason": "No valid proposals in competition"}
                    })

                guess = selected_proposal["proposal"].get("proposed_guess", []) if selected_proposal else None

                if not selected_proposal:
                    continue

                validation = selected_proposal["validation"]

                # Step 5: Submit winning guess
                feedback = self.game_engine.submit_guess(guess)

                if not feedback.get("valid", False):
                    self.logger.log_message({
                        "message_type": "error",
                        "sender": "game_engine",
                        "receiver": "all",
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

                # Log feedback
                self.logger.log_message({
                    "message_type": "feedback",
                    "sender": "game_engine",
                    "receiver": "all",
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
                self.metrics.record_metric("proposals_evaluated", 3)
                self.metrics.record_metric("correct_pegs", feedback.get("feedback", {}).get("correct_pegs", 0))
                self.metrics.record_metric("correct_positions", feedback.get("feedback", {}).get("correct_positions", 0))

                # Check if solved
                if feedback.get("solved", False):
                    break

            except Exception as e:
                self.logger.log_message({
                    "message_type": "error",
                    "sender": "orchestrator",
                    "receiver": "all",
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
    print("DIRECT ADVERSARIAL PARADIGM TEST")
    print("=" * 80)

    try:
        puzzles = load_puzzles()
        test_puzzle = next(p for p in puzzles if p['difficulty'] == 'easy')

        print(f"\nTesting puzzle: {test_puzzle['puzzle_id']}")
        print(f"Difficulty: {test_puzzle['difficulty']}")

        orchestrator = DirectAdversarialOrchestrator(test_puzzle, provider="deepseek")
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
