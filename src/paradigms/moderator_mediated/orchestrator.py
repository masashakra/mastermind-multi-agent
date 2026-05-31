# Moderator-Mediated Paradigm Orchestrator
# Moderator arbitrates between competing agents

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
from typing import Dict, Any, List

from core.game_engine import GameEngine
from core.puzzle_generator import load_puzzles
from communication.protocol import A2ACommunicationLayer
from registry.registry import get_global_registry
from paradigms.moderator_mediated.agents import (
    AnalyzerAgent,
    StrategistAgent,
    ProposerAgent,
    ValidatorAgent,
    LoggerAgent,
    MetricsAgent,
)


class ModeratorMediatedOrchestrator:
    """Orchestrates the Moderator-Mediated paradigm

    Structure:
    - Moderator (orchestrator) coordinates between competing agents
    - Agents propose different approaches
    - Moderator arbitrates and selects best path forward
    - Balance between competition and coordination
    """

    def __init__(self, puzzle: Dict[str, Any], provider: str = "ollama"):
        """Initialize orchestrator for one puzzle

        Args:
            puzzle: Puzzle dictionary from puzzle_generator
            provider: LLM provider ("ollama", "groq", "claude", "kaggle")
        """
        self.puzzle = puzzle
        self.provider = provider
        self.paradigm = "moderator_mediated"
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])
        self.start_time = time.time()

        # A2A Communication
        self.comm_layer = A2ACommunicationLayer()
        self.registry = get_global_registry(self.comm_layer)

        # Initialize agents
        self.analyzer = AnalyzerAgent(provider=provider, comm_layer=self.comm_layer)
        self.strategist = StrategistAgent(provider=provider, comm_layer=self.comm_layer)
        self.proposer = ProposerAgent(provider=provider, comm_layer=self.comm_layer)
        self.validator = ValidatorAgent(provider=provider, comm_layer=self.comm_layer)
        self.logger = LoggerAgent(paradigm_name=self.paradigm)
        self.metrics = MetricsAgent(paradigm_name=self.paradigm)

        # Register agents
        self.registry.register_agent({"agent_id": "analyzer", "agent_name": "Analyzer", "agent_type": "analyzer", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "strategist", "agent_name": "Strategist", "agent_type": "strategist", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "proposer", "agent_name": "Proposer", "agent_type": "proposer", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "validator", "agent_name": "Validator", "agent_type": "validator", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "logger", "agent_name": "Logger", "agent_type": "logger", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "metrics", "agent_name": "Metrics", "agent_type": "metrics", "paradigm": self.paradigm})

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Moderator-Mediated paradigm

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "moderator_mediated",
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
                # Step 1: Analyzer - Analyze feedback
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

                # Log analysis to moderator
                self.logger.log_message({
                    "message_type": "analysis",
                    "sender": "analyzer",
                    "receiver": "moderator",
                    "round": round_count,
                    "content": analysis
                })

                # Step 2: Strategist - Propose approach
                strategy = self.strategist.propose_strategy(
                    guess_history,
                    self.puzzle["difficulty"]
                )

                # Log strategy to moderator
                self.logger.log_message({
                    "message_type": "strategy",
                    "sender": "strategist",
                    "receiver": "moderator",
                    "round": round_count,
                    "content": strategy
                })

                # Step 3: Proposer - Generate competing proposals
                constraints_text = "\n".join(analysis.get("constraints", []))
                proposals = []
                for attempt in range(2):  # 2 competing proposals
                    proposal = self.proposer.propose_guess(
                        strategy=strategy.get("strategy", ""),
                        constraints_text=constraints_text,
                        available_colors=self.puzzle.get("available_colors", []),
                        num_pegs=self.puzzle.get("pegs", 4),
                        previous_guesses=[g.get("guess", []) for g in guess_history]
                    )
                    proposals.append(proposal)

                # Log proposals to moderator
                self.logger.log_message({
                    "message_type": "proposals",
                    "sender": "proposer",
                    "receiver": "moderator",
                    "round": round_count,
                    "content": {"proposals": proposals}
                })

                # Step 4: Validator - Validate proposals
                validations = []
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
                    validations.append({
                        "proposal_index": i,
                        "validation": validation
                    })

                # Log validations to moderator
                self.logger.log_message({
                    "message_type": "validations",
                    "sender": "validator",
                    "receiver": "moderator",
                    "round": round_count,
                    "content": {"validations": validations}
                })

                # Moderator decision: select best proposal
                selected_proposal = None
                for i, proposal in enumerate(proposals):
                    if validations[i]["validation"].get("valid", False):
                        selected_proposal = proposal
                        selected_index = i
                        break

                if not selected_proposal:
                    self.logger.log_message({
                        "message_type": "moderation_decision",
                        "sender": "moderator",
                        "receiver": "all",
                        "round": round_count,
                        "content": {"decision": "No valid proposals", "action": "skip_round"}
                    })
                    continue

                # Log moderator decision
                self.logger.log_message({
                    "message_type": "moderation_decision",
                    "sender": "moderator",
                    "receiver": "all",
                    "round": round_count,
                    "content": {"decision": f"Selected proposal {selected_index}"}
                })

                guess = selected_proposal.get("proposed_guess", [])

                # Step 5: Submit moderated guess
                feedback = self.game_engine.submit_guess(guess)

                if not feedback.get("valid", False):
                    self.logger.log_message({
                        "message_type": "error",
                        "sender": "game_engine",
                        "receiver": "moderator",
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
                    "receiver": "moderator",
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
                self.metrics.record_metric("proposals_evaluated", len(proposals))
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
    print("MODERATOR-MEDIATED PARADIGM TEST")
    print("=" * 80)

    try:
        puzzles = load_puzzles()
        test_puzzle = next(p for p in puzzles if p['difficulty'] == 'easy')

        print(f"\nTesting puzzle: {test_puzzle['puzzle_id']}")
        print(f"Difficulty: {test_puzzle['difficulty']}")

        orchestrator = ModeratorMediatedOrchestrator(test_puzzle, provider="ollama")
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
