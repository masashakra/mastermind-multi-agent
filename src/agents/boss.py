# Boss Agent with A2A Protocol
# Orchestrates all 4 worker agents using agent-to-agent communication protocol
# Controls the flow: Strategy → Analysis → Proposal → Validation → Guess
# Used in Boss-Worker paradigm (centralized collaboration)

from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
from .strategist import StrategistAgent
from .analyzer import AnalyzerAgent
from .proposer import ProposerAgent
from .validator import ValidatorAgent
from communication.protocol import A2ACommunicationLayer


class BossAgent(BaseAgent):
    """Orchestrates worker agents using A2A protocol.

    Role: Central coordinator for Boss-Worker paradigm

    Workflow per round (using A2A messages):
    1. Send strategy request to Strategist via A2A
    2. Send analysis request to Analyzer via A2A
    3. Send proposal request to Proposer via A2A
    4. Send validation request to Validator via A2A
    5. Return approved guess and A2A message history
    """

    def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None):
        # Create communication layer if not provided
        if comm_layer is None:
            comm_layer = A2ACommunicationLayer()

        super().__init__(name="Boss", provider=provider, comm_layer=comm_layer)

        # Create worker agents with same communication layer
        self.strategist = StrategistAgent(provider=provider, comm_layer=self.comm_layer)
        self.analyzer = AnalyzerAgent(provider=provider, comm_layer=self.comm_layer)
        self.proposer = ProposerAgent(provider=provider, comm_layer=self.comm_layer)
        self.validator = ValidatorAgent(provider=provider, comm_layer=self.comm_layer)

        self.round_count = 0
        self.max_retries = 2

    def orchestrate_round(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate one complete round through all agents using A2A protocol.

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
                "messages": A2A message history,
                "success": True if guess is valid and approved
            }
        """
        self.round_count += 1
        puzzle = game_state.get("puzzle", {})
        guess_history = game_state.get("guess_history", [])
        difficulty = game_state.get("difficulty", "easy")

        a2a_messages = []

        # ==== STEP 1: Request Strategy via A2A ====
        strategy_request = self.send_request(
            receiver_id="strategist",
            action="propose_strategy",
            payload={
                "guess_history": guess_history,
                "difficulty": difficulty
            }
        )
        a2a_messages.append(strategy_request.to_dict())

        # Call Strategist and send response
        try:
            strategy_result = self.strategist.propose_strategy(guess_history, difficulty)
            strategy_response = self.comm_layer.send_response(
                sender_id="strategist",
                receiver_id=self.agent_id,
                correlation_id=strategy_request.message_id,
                payload=strategy_result,
                status="success"
            )
            a2a_messages.append(strategy_response.to_dict())
        except Exception as e:
            strategy_response = self.comm_layer.send_response(
                sender_id="strategist",
                receiver_id=self.agent_id,
                correlation_id=strategy_request.message_id,
                payload={"error": str(e)},
                status="error"
            )
            a2a_messages.append(strategy_response.to_dict())
            raise RuntimeError(f"Strategist failed: {str(e)}")

        # ==== STEP 2: Request Analysis via A2A ====
        analysis_result = None
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
            a2a_messages.append(analysis_request.to_dict())

            try:
                analysis_result = self.analyzer.analyze_feedback(
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
                a2a_messages.append(analysis_response.to_dict())
            except Exception as e:
                analysis_response = self.comm_layer.send_response(
                    sender_id="analyzer",
                    receiver_id=self.agent_id,
                    correlation_id=analysis_request.message_id,
                    payload={"error": str(e)},
                    status="error"
                )
                a2a_messages.append(analysis_response.to_dict())
                raise RuntimeError(f"Analyzer failed: {str(e)}")
        else:
            # No history yet, send default analysis
            analysis_result = {
                "correct_positions": [],
                "correct_colors_wrong_position": [],
                "constraints": [],
                "impossible_colors": [],
                "estimated_remaining": "All codes possible"
            }
            analysis_notification = self.comm_layer.send_notification(
                sender_id="analyzer",
                receiver_id=self.agent_id,
                action="analyze_feedback",
                payload=analysis_result
            )
            a2a_messages.append(analysis_notification.to_dict())

        # ==== STEP 3: Request Proposal via A2A ====
        previous_guess_lists = [g.get("guess", []) for g in guess_history]
        proposal_request = self.send_request(
            receiver_id="proposer",
            action="propose_guess",
            payload={
                "strategy": strategy_result.get("strategy", ""),
                "constraints": analysis_result.get("constraints", []),
                "correct_positions": analysis_result.get("correct_positions", []),
                "correct_colors_wrong_position": analysis_result.get("correct_colors_wrong_position", []),
                "impossible_colors": analysis_result.get("impossible_colors", []),
                "available_colors": puzzle.get("available_colors", []),
                "num_pegs": puzzle.get("pegs", 4),
                "previous_guesses": previous_guess_lists
            }
        )
        a2a_messages.append(proposal_request.to_dict())

        try:
            proposal_result = self.proposer.propose_guess(
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
            a2a_messages.append(proposal_response.to_dict())
        except Exception as e:
            proposal_response = self.comm_layer.send_response(
                sender_id="proposer",
                receiver_id=self.agent_id,
                correlation_id=proposal_request.message_id,
                payload={"error": str(e)},
                status="error"
            )
            a2a_messages.append(proposal_response.to_dict())
            raise RuntimeError(f"Proposer failed: {str(e)}")

        # ==== STEP 4: Request Validation via A2A ====
        guess = proposal_result.get("proposed_guess", [])

        # Build constraints dict for validator
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
                "previous_guesses": [g.get("guess", []) for g in guess_history],
                "constraints": constraints_dict
            }
        )
        a2a_messages.append(validation_request.to_dict())

        try:
            validation_result = self.validator.validate_with_llm(
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
            a2a_messages.append(validation_response.to_dict())
        except Exception as e:
            validation_response = self.comm_layer.send_response(
                sender_id="validator",
                receiver_id=self.agent_id,
                correlation_id=validation_request.message_id,
                payload={"error": str(e)},
                status="error"
            )
            a2a_messages.append(validation_response.to_dict())
            raise RuntimeError(f"Validator failed: {str(e)}")

        return {
            "guess": guess,
            "strategy": strategy_result,
            "analysis": analysis_result,
            "proposal": proposal_result,
            "validation": validation_result,
            "messages": a2a_messages,  # Full A2A message history
            "success": validation_result.get("is_valid", False)
        }

    def get_communication_history(self) -> List[Dict[str, Any]]:
        """Get the A2A communication history for this orchestration.

        Returns:
            List of all messages exchanged between agents
        """
        return [msg.to_dict() for msg in self.comm_layer.message_history]

    def get_agent_conversation(self, agent1: str, agent2: str) -> List[Dict[str, Any]]:
        """Get messages exchanged between two specific agents.

        Args:
            agent1: First agent ID
            agent2: Second agent ID

        Returns:
            List of messages between them
        """
        return [msg.to_dict() for msg in self.comm_layer.get_conversation(agent1, agent2)]

    def process(self, **kwargs) -> Dict[str, Any]:
        """Standard process interface."""
        return self.orchestrate_round(kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestration statistics.

        Returns:
            Stats from all agents and communication layer
        """
        base_stats = super().get_stats()
        return {
            "boss": base_stats,
            "strategist": self.strategist.get_stats(),
            "analyzer": self.analyzer.get_stats(),
            "proposer": self.proposer.get_stats(),
            "validator": self.validator.get_stats(),
            "communication": {
                "total_messages": len(self.comm_layer.message_history),
                "pending_requests": len(self.comm_layer.pending_requests),
                "agents_registered": len(self.comm_layer.agents)
            }
        }
