# Boss Agent - A2A Task Orchestrator
# Boss sends A2A tasks to worker agents and collects results
# Does NOT handle guess submission - that's LangGraph's responsibility
# Uses A2A protocol to communicate with all workers

from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from communication.protocol import A2ACommunicationLayer, A2AMessage
from communication.agent_discovery import AgentRegistry, AgentDiscovery


class BossA2AAgent(BaseAgent):
    """
    Boss Agent using A2A Protocol.

    Responsibility: Orchestrate worker agents via A2A protocol
    - Send A2A task requests to workers
    - Collect A2A responses from workers
    - Assemble final guess
    - Return guess (submission is LangGraph's job)

    Does NOT:
    - Submit guess to game engine (LangGraph does this)
    - Handle game feedback (LangGraph does this)
    - Define workflow order (that's LangGraph's job)
    """

    def __init__(
        self,
        provider: str = "groq",
        comm_layer: Optional[A2ACommunicationLayer] = None,
        registry: Optional[AgentRegistry] = None,
        discovery: Optional[AgentDiscovery] = None
    ):
        """Initialize Boss Agent with A2A communication.

        Args:
            provider: LLM provider (groq, kaggle, ollama, claude)
            comm_layer: A2A Communication layer
            registry: Agent registry for discovery
            discovery: Agent discovery service
        """
        if comm_layer is None:
            comm_layer = A2ACommunicationLayer()

        super().__init__(name="Boss", provider=provider, comm_layer=comm_layer)

        self.registry = registry
        self.discovery = discovery
        self.round_count = 0
        self.a2a_message_log: list = []

    def orchestrate_round(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrate one round by sending A2A tasks to workers.

        Flow:
        1. Send A2A task to Strategist
        2. Send A2A task to Analyzer
        3. Send A2A task to Proposer
        4. Send A2A task to Validator
        5. Return final guess (for LangGraph to submit)

        Args:
            game_state: Current game state
                {
                    "puzzle": puzzle dict,
                    "guess_history": list of previous guesses with feedback,
                    "difficulty": "easy"/"medium"/"hard"
                }

        Returns:
            {
                "guess": final proposed guess (ready for LangGraph to submit),
                "strategy": strategy result from Strategist,
                "analysis": analysis result from Analyzer,
                "proposal": proposal result from Proposer,
                "validation": validation result from Validator,
                "a2a_messages": all A2A messages exchanged,
                "success": whether validation passed
            }
        """
        self.round_count += 1
        puzzle = game_state.get("puzzle", {})
        guess_history = game_state.get("guess_history", [])
        difficulty = game_state.get("difficulty", "easy")

        # ============================================================
        # TASK 1: Ask Strategist for strategy (via A2A)
        # ============================================================
        strategy_request = self.send_request(
            receiver_id="strategist",
            action="propose_strategy",
            payload={
                "guess_history": guess_history,
                "difficulty": difficulty
            }
        )
        self.a2a_message_log.append(strategy_request.to_dict())

        # Execute strategy task
        from .strategist import StrategistAgent
        try:
            strategist = StrategistAgent(provider=self.provider, comm_layer=self.comm_layer)
            strategy_result = strategist.propose_strategy(guess_history, difficulty)

            # Send response via A2A
            strategy_response = self.comm_layer.send_response(
                sender_id="strategist",
                receiver_id=self.agent_id,
                correlation_id=strategy_request.message_id,
                payload=strategy_result,
                status="success"
            )
            self.a2a_message_log.append(strategy_response.to_dict())
        except Exception as e:
            strategy_response = self.comm_layer.send_response(
                sender_id="strategist",
                receiver_id=self.agent_id,
                correlation_id=strategy_request.message_id,
                payload={"error": str(e)},
                status="error"
            )
            self.a2a_message_log.append(strategy_response.to_dict())
            raise RuntimeError(f"Strategist task failed: {str(e)}")

        # ============================================================
        # TASK 2: Ask Analyzer for analysis (via A2A)
        # ============================================================
        from .analyzer import AnalyzerAgent

        if guess_history:
            last_guess = guess_history[-1]
            analysis_request = self.send_request(
                receiver_id="analyzer",
                action="analyze_feedback",
                payload={
                    "last_guess": last_guess.get("guess", []),
                    "feedback": last_guess.get("feedback", {}),
                    "previous_guesses": guess_history[:-1]
                }
            )
            self.a2a_message_log.append(analysis_request.to_dict())

            try:
                analyzer = AnalyzerAgent(provider=self.provider, comm_layer=self.comm_layer)
                analysis_result = analyzer.analyze_feedback(
                    last_guess.get("guess", []),
                    last_guess.get("feedback", {}),
                    guess_history[:-1]
                )

                analysis_response = self.comm_layer.send_response(
                    sender_id="analyzer",
                    receiver_id=self.agent_id,
                    correlation_id=analysis_request.message_id,
                    payload=analysis_result,
                    status="success"
                )
                self.a2a_message_log.append(analysis_response.to_dict())
            except Exception as e:
                analysis_response = self.comm_layer.send_response(
                    sender_id="analyzer",
                    receiver_id=self.agent_id,
                    correlation_id=analysis_request.message_id,
                    payload={"error": str(e)},
                    status="error"
                )
                self.a2a_message_log.append(analysis_response.to_dict())
                raise RuntimeError(f"Analyzer task failed: {str(e)}")
        else:
            # No history - send notification of default analysis
            analysis_request = self.send_request(
                receiver_id="analyzer",
                action="analyze_feedback",
                payload={
                    "last_guess": [],
                    "feedback": {},
                    "previous_guesses": []
                }
            )
            self.a2a_message_log.append(analysis_request.to_dict())

            analysis_result = {
                "correct_positions": [],
                "correct_colors_wrong_position": [],
                "constraints": [],
                "impossible_colors": [],
                "estimated_remaining": "All codes possible"
            }

            analysis_response = self.comm_layer.send_response(
                sender_id="analyzer",
                receiver_id=self.agent_id,
                correlation_id=analysis_request.message_id,
                payload=analysis_result,
                status="success"
            )
            self.a2a_message_log.append(analysis_response.to_dict())

        # ============================================================
        # TASK 3: Ask Proposer for guess proposal (via A2A)
        # ============================================================
        from .proposer import ProposerAgent

        previous_guess_lists = [g.get("guess", []) for g in guess_history]
        proposal_request = self.send_request(
            receiver_id="proposer",
            action="propose_guess",
            payload={
                "strategy": strategy_result.get("strategy", ""),
                "constraints": analysis_result.get("constraints", []),
                "available_colors": puzzle.get("available_colors", []),
                "num_pegs": puzzle.get("pegs", 4),
                "previous_guesses": previous_guess_lists
            }
        )
        self.a2a_message_log.append(proposal_request.to_dict())

        try:
            proposer = ProposerAgent(provider=self.provider, comm_layer=self.comm_layer)
            proposal_result = proposer.propose_guess(
                strategy=strategy_result.get("strategy", ""),
                constraints_text="\n".join(analysis_result.get("constraints", [])),
                available_colors=puzzle.get("available_colors", []),
                num_pegs=puzzle.get("pegs", 4),
                previous_guesses=previous_guess_lists
            )

            proposal_response = self.comm_layer.send_response(
                sender_id="proposer",
                receiver_id=self.agent_id,
                correlation_id=proposal_request.message_id,
                payload=proposal_result,
                status="success"
            )
            self.a2a_message_log.append(proposal_response.to_dict())
        except Exception as e:
            proposal_response = self.comm_layer.send_response(
                sender_id="proposer",
                receiver_id=self.agent_id,
                correlation_id=proposal_request.message_id,
                payload={"error": str(e)},
                status="error"
            )
            self.a2a_message_log.append(proposal_response.to_dict())
            raise RuntimeError(f"Proposer task failed: {str(e)}")

        # ============================================================
        # TASK 4: Ask Validator to validate proposal (via A2A)
        # ============================================================
        from .validator import ValidatorAgent

        guess = proposal_result.get("proposed_guess", [])
        constraints_dict = {
            "correct_positions": analysis_result.get("correct_positions", []),
            "correct_colors_wrong_position": analysis_result.get("correct_colors_wrong_position", []),
            "impossible_colors": analysis_result.get("impossible_colors", [])
        }

        validation_request = self.send_request(
            receiver_id="validator",
            action="validate_guess",
            payload={
                "guess": guess,
                "available_colors": puzzle.get("available_colors", []),
                "expected_length": puzzle.get("pegs", 4),
                "constraints": constraints_dict
            }
        )
        self.a2a_message_log.append(validation_request.to_dict())

        try:
            validator = ValidatorAgent(provider=self.provider, comm_layer=self.comm_layer)
            validation_result = validator.validate_with_llm(
                guess=guess,
                available_colors=puzzle.get("available_colors", []),
                expected_length=puzzle.get("pegs", 4),
                previous_guesses=[g.get("guess", []) for g in guess_history],
                constraints=constraints_dict
            )

            validation_response = self.comm_layer.send_response(
                sender_id="validator",
                receiver_id=self.agent_id,
                correlation_id=validation_request.message_id,
                payload=validation_result,
                status="success"
            )
            self.a2a_message_log.append(validation_response.to_dict())
        except Exception as e:
            validation_response = self.comm_layer.send_response(
                sender_id="validator",
                receiver_id=self.agent_id,
                correlation_id=validation_request.message_id,
                payload={"error": str(e)},
                status="error"
            )
            self.a2a_message_log.append(validation_response.to_dict())
            raise RuntimeError(f"Validator task failed: {str(e)}")

        # ============================================================
        # RETURN RESULTS TO LANGGRAPH
        # ============================================================
        # Boss returns the final guess for LangGraph to submit
        # LangGraph will submit and get feedback, then call Boss again next round

        return {
            "guess": guess,  # Ready for LangGraph to submit to game engine
            "strategy": strategy_result,
            "analysis": analysis_result,
            "proposal": proposal_result,
            "validation": validation_result,
            "a2a_messages": self.a2a_message_log.copy(),
            "success": validation_result.get("is_valid", False)
        }

    def process(self, **kwargs) -> Dict[str, Any]:
        """Standard process interface."""
        return self.orchestrate_round(kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get Boss statistics."""
        stats = super().get_stats()
        stats["rounds_orchestrated"] = self.round_count
        stats["total_a2a_messages"] = len(self.a2a_message_log)
        return stats
