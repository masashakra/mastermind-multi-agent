# Direct Debate Paradigm Orchestrator
# Agents debate and discuss solutions openly before submitting

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
from typing import Dict, Any, List

from core.game_engine import GameEngine
from core.puzzle_generator import load_puzzles
from communication.protocol import A2ACommunicationLayer
from registry.registry import get_global_registry
from paradigms.direct_debate.agents import (
    AnalyzerAgent,
    StrategistAgent,
    ProposerAgent,
    ValidatorAgent,
    LoggerAgent,
    MetricsAgent,
)


class DirectDebateOrchestrator:
    """Orchestrates the Direct Debate paradigm

    Structure:
    - Agents debate and discuss solutions openly
    - Multiple rounds of discussion and refinement
    - Collaborative approach to problem-solving
    - Focus on consensus through dialogue
    """

    def __init__(self, puzzle: Dict[str, Any], provider: str = "ollama"):
        """Initialize orchestrator for one puzzle

        Args:
            puzzle: Puzzle dictionary from puzzle_generator
            provider: LLM provider ("ollama", "groq", "claude", "kaggle")
        """
        self.puzzle = puzzle
        self.provider = provider
        self.paradigm = "direct_debate"
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])
        self.start_time = time.time()

        # A2A Communication
        self.comm_layer = A2ACommunicationLayer()
        self.registry = get_global_registry(self.comm_layer)

        # Initialize agents (debate participants)
        self.analyzer = AnalyzerAgent(provider=provider, comm_layer=self.comm_layer)
        self.strategist = StrategistAgent(provider=provider, comm_layer=self.comm_layer)
        self.proposer = ProposerAgent(provider=provider, comm_layer=self.comm_layer)
        self.validator = ValidatorAgent(provider=provider, comm_layer=self.comm_layer)
        self.logger = LoggerAgent(paradigm_name=self.paradigm)
        self.metrics = MetricsAgent(paradigm_name=self.paradigm)

        # Register debate participants
        self.registry.register_agent({"agent_id": "analyzer", "agent_name": "Analyzer", "agent_type": "analyzer", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "strategist", "agent_name": "Strategist", "agent_type": "strategist", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "proposer", "agent_name": "Proposer", "agent_type": "proposer", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "validator", "agent_name": "Validator", "agent_type": "validator", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "logger", "agent_name": "Logger", "agent_type": "logger", "paradigm": self.paradigm})
        self.registry.register_agent({"agent_id": "metrics", "agent_name": "Metrics", "agent_type": "metrics", "paradigm": self.paradigm})

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Direct Debate paradigm

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "direct_debate",
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
                # Round opening: Debate phase
                self.logger.log_message({
                    "message_type": "debate_round_start",
                    "sender": "orchestrator",
                    "receiver": "all_agents",
                    "round": round_count,
                    "content": {"round": round_count, "phase": "debate_discussion"}
                })

                # Step 1: Analyzer presents analysis
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

                # Log analysis for debate
                self.logger.log_message({
                    "message_type": "debate_analysis",
                    "sender": "analyzer",
                    "receiver": "all_agents",
                    "round": round_count,
                    "content": analysis
                })

                # Step 2: Strategist proposes approach
                strategy = self.strategist.propose_strategy(
                    guess_history,
                    self.puzzle["difficulty"]
                )

                # Log strategy for debate
                self.logger.log_message({
                    "message_type": "debate_strategy",
                    "sender": "strategist",
                    "receiver": "all_agents",
                    "round": round_count,
                    "content": strategy
                })

                # Step 3: Proposer suggests guess
                constraints_text = "\n".join(analysis.get("constraints", []))
                proposal = self.proposer.propose_guess(
                    strategy=strategy.get("strategy", ""),
                    constraints_text=constraints_text,
                    available_colors=self.puzzle.get("available_colors", []),
                    num_pegs=self.puzzle.get("pegs", 4),
                    previous_guesses=[g.get("guess", []) for g in guess_history]
                )

                # Log proposal for debate discussion
                self.logger.log_message({
                    "message_type": "debate_proposal",
                    "sender": "proposer",
                    "receiver": "all_agents",
                    "round": round_count,
                    "content": proposal
                })

                # Step 4: Validator examines proposal
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

                # Log validation for debate
                self.logger.log_message({
                    "message_type": "debate_validation",
                    "sender": "validator",
                    "receiver": "all_agents",
                    "round": round_count,
                    "content": validation
                })

                # Debate conclusion: If invalid, discuss and refine
                if not validation.get("valid", True):
                    self.logger.log_message({
                        "message_type": "debate_concern",
                        "sender": "validator",
                        "receiver": "all_agents",
                        "round": round_count,
                        "content": {
                            "concern": "Invalid proposal",
                            "violations": validation.get("hard_violations", []),
                            "action": "continue_debate"
                        }
                    })
                    continue

                # Consensus reached: Submit agreed proposal
                self.logger.log_message({
                    "message_type": "debate_consensus",
                    "sender": "orchestrator",
                    "receiver": "all_agents",
                    "round": round_count,
                    "content": {"consensus": "Proposal accepted by all agents"}
                })

                # Step 5: Submit agreed guess
                feedback = self.game_engine.submit_guess(guess)

                if not feedback.get("valid", False):
                    self.logger.log_message({
                        "message_type": "error",
                        "sender": "game_engine",
                        "receiver": "all_agents",
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

                # Log feedback for all to learn from
                self.logger.log_message({
                    "message_type": "shared_feedback",
                    "sender": "game_engine",
                    "receiver": "all_agents",
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
                self.metrics.record_metric("debate_rounds_per_guess", 1)
                self.metrics.record_metric("correct_pegs", feedback.get("feedback", {}).get("correct_pegs", 0))
                self.metrics.record_metric("correct_positions", feedback.get("feedback", {}).get("correct_positions", 0))

                # Check if solved
                if feedback.get("solved", False):
                    break

            except Exception as e:
                self.logger.log_message({
                    "message_type": "error",
                    "sender": "orchestrator",
                    "receiver": "all_agents",
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
    print("DIRECT DEBATE PARADIGM TEST")
    print("=" * 80)

    try:
        puzzles = load_puzzles()
        test_puzzle = next(p for p in puzzles if p['difficulty'] == 'easy')

        print(f"\nTesting puzzle: {test_puzzle['puzzle_id']}")
        print(f"Difficulty: {test_puzzle['difficulty']}")

        orchestrator = DirectDebateOrchestrator(test_puzzle, provider="ollama")
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
