# Orchestration Layer - LangGraph-based Workflow Orchestration
# COMPLETELY SEPARATE from Communication Layer
# Orchestration defines WORKFLOW, Communication handles AGENT INTERACTION

from typing import Dict, Any, List, Optional
from communication.protocol import A2ACommunicationLayer, A2AMessage
from communication.agent_discovery import AgentRegistry, AgentDiscovery
from communication import (
    STRATEGIST_CARD,
    ANALYZER_CARD,
    PROPOSER_CARD,
    VALIDATOR_CARD,
)


class MastermindOrchestrator:
    """
    LangGraph-based Orchestrator for Mastermind puzzle solving.

    Responsibility: Define and manage the WORKFLOW (not communication)
    - Decides order of agent invocations
    - Manages state transitions
    - Handles branching logic
    - Determines success/failure paths

    Does NOT handle:
    - Agent registration
    - Message passing
    - Protocol details

    These are handled by the Communication Layer.
    """

    def __init__(self, comm_layer: A2ACommunicationLayer, llm_provider: str = "groq"):
        """Initialize orchestrator with communication layer.

        Args:
            comm_layer: A2ACommunicationLayer for agent interaction
            llm_provider: LLM provider to use (groq, kaggle, ollama, claude)
        """
        self.comm_layer = comm_layer
        self.llm_provider = llm_provider

        # Set up agent discovery
        self.registry = AgentRegistry()
        self.discovery = AgentDiscovery(self.registry)

        # Register all agents with discovery service
        self._register_agents()

        # Orchestration state
        self.current_round = 0
        self.workflow_state: Dict[str, Any] = {}
        self.execution_history: List[Dict[str, Any]] = []

    def _register_agents(self) -> None:
        """Register all mastermind agents with discovery service."""
        self.registry.register_agent(STRATEGIST_CARD)
        self.registry.register_agent(ANALYZER_CARD)
        self.registry.register_agent(PROPOSER_CARD)
        self.registry.register_agent(VALIDATOR_CARD)

    def orchestrate_round(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrate one complete round using workflow graph.

        This defines the WORKFLOW for the Boss-Worker paradigm:
        1. Request strategy from Strategist (via A2A)
        2. Request analysis from Analyzer (via A2A)
        3. Request proposal from Proposer (via A2A)
        4. Request validation from Validator (via A2A)
        5. Return guess and message history

        Agents communicate ONLY through A2A protocol.
        Orchestration only manages WORKFLOW, not communication details.
        """
        self.current_round += 1
        round_execution = {
            "round": self.current_round,
            "game_state": game_state,
            "workflow_steps": []
        }

        try:
            # ============================================================
            # WORKFLOW STEP 1: Strategy Proposal
            # ============================================================
            strategist_card = self.discovery.find_strategist()
            if not strategist_card:
                raise RuntimeError("Strategist not found in registry")

            strategy_step = self._execute_workflow_step(
                step_name="propose_strategy",
                target_agent_card=strategist_card,
                action="propose_strategy",
                payload={
                    "guess_history": game_state.get("guess_history", []),
                    "difficulty": game_state.get("difficulty", "easy")
                }
            )
            round_execution["workflow_steps"].append(strategy_step)
            if strategy_step["status"] != "completed":
                raise RuntimeError(f"Strategy step failed: {strategy_step.get('error', 'Unknown error')}")
            strategy_result = strategy_step.get("result", {})

            # ============================================================
            # WORKFLOW STEP 2: Feedback Analysis
            # ============================================================
            analyzer_card = self.discovery.find_analyzer()
            if not analyzer_card:
                raise RuntimeError("Analyzer not found in registry")

            guess_history = game_state.get("guess_history", [])
            if guess_history:
                last_guess = guess_history[-1]
                analysis_step = self._execute_workflow_step(
                    step_name="analyze_feedback",
                    target_agent_card=analyzer_card,
                    action="analyze_feedback",
                    payload={
                        "last_guess": last_guess.get("guess", []),
                        "feedback": last_guess.get("feedback", {}),
                        "previous_guesses": guess_history[:-1]
                    }
                )
            else:
                # No history yet - use default analysis
                analysis_step = self._execute_workflow_step(
                    step_name="analyze_feedback_initial",
                    target_agent_card=analyzer_card,
                    action="analyze_feedback",
                    payload={
                        "last_guess": [],
                        "feedback": {},
                        "previous_guesses": []
                    },
                    is_initial=True
                )

            round_execution["workflow_steps"].append(analysis_step)
            if analysis_step["status"] != "completed":
                raise RuntimeError(f"Analysis step failed: {analysis_step.get('error', 'Unknown error')}")
            analysis_result = analysis_step.get("result", {})

            # ============================================================
            # WORKFLOW STEP 3: Guess Proposal
            # ============================================================
            proposer_card = self.discovery.find_proposer()
            if not proposer_card:
                raise RuntimeError("Proposer not found in registry")

            puzzle = game_state.get("puzzle", {})
            proposal_step = self._execute_workflow_step(
                step_name="propose_guess",
                target_agent_card=proposer_card,
                action="propose_guess",
                payload={
                    "strategy": strategy_result.get("strategy", ""),
                    "constraints": analysis_result.get("constraints", []),
                    "correct_positions": analysis_result.get("correct_positions", []),
                    "correct_colors_wrong_position": analysis_result.get("correct_colors_wrong_position", []),
                    "impossible_colors": analysis_result.get("impossible_colors", []),
                    "available_colors": puzzle.get("available_colors", []),
                    "num_pegs": puzzle.get("pegs", 4)
                }
            )
            round_execution["workflow_steps"].append(proposal_step)
            if proposal_step["status"] != "completed":
                raise RuntimeError(f"Proposal step failed: {proposal_step.get('error', 'Unknown error')}")
            proposal_result = proposal_step.get("result", {})

            # ============================================================
            # WORKFLOW STEP 4: Guess Validation
            # ============================================================
            validator_card = self.discovery.find_validator()
            if not validator_card:
                raise RuntimeError("Validator not found in registry")

            guess = proposal_result.get("proposed_guess", [])
            constraints_dict = {
                "correct_positions": analysis_result.get("correct_positions", []),
                "correct_colors_wrong_position": analysis_result.get("correct_colors_wrong_position", []),
                "impossible_colors": analysis_result.get("impossible_colors", [])
            }

            validation_step = self._execute_workflow_step(
                step_name="validate_guess",
                target_agent_card=validator_card,
                action="validate_guess",
                payload={
                    "guess": guess,
                    "available_colors": puzzle.get("available_colors", []),
                    "expected_length": puzzle.get("pegs", 4),
                    "constraints": constraints_dict
                }
            )
            round_execution["workflow_steps"].append(validation_step)
            if validation_step["status"] != "completed":
                raise RuntimeError(f"Validation step failed: {validation_step.get('error', 'Unknown error')}")
            validation_result = validation_step.get("result", {})

            # ============================================================
            # WORKFLOW COMPLETE - Return results
            # ============================================================
            round_execution["status"] = "success"
            self.execution_history.append(round_execution)

            return {
                "guess": guess,
                "strategy": strategy_result,
                "analysis": analysis_result,
                "proposal": proposal_result,
                "validation": validation_result,
                "messages": [msg.to_dict() for msg in self.comm_layer.message_history],
                "workflow_execution": round_execution,
                "success": validation_result.get("is_valid", False)
            }

        except Exception as e:
            round_execution["status"] = "failed"
            round_execution["error"] = str(e)
            self.execution_history.append(round_execution)
            raise

    def _execute_workflow_step(
        self,
        step_name: str,
        target_agent_card,
        action: str,
        payload: Dict[str, Any],
        is_initial: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a single workflow step.

        This is where ORCHESTRATION meets COMMUNICATION:
        - Orchestration decides to call an agent
        - Communication handles the A2A message passing

        Args:
            step_name: Name of this workflow step
            target_agent_card: AgentCard of target agent
            action: Action to request
            payload: Data for the action
            is_initial: Whether this is an initial step (no history)

        Returns:
            Dict with step results and metadata
        """
        step_info = {
            "step_name": step_name,
            "target_agent": target_agent_card.agent_id,
            "action": action,
            "status": "pending"
        }

        try:
            # Send A2A request through communication layer
            request_msg = self.comm_layer.send_request(
                sender_id="orchestrator",
                receiver_id=target_agent_card.agent_id,
                action=action,
                payload=payload
            )
            step_info["request_message_id"] = request_msg.message_id

            # In actual implementation, agent would respond via A2A
            # For now, we execute directly (agents are local)
            # TODO: Implement async A2A response handling

            # Simulate agent work (this would come from A2A response in distributed system)
            from agents.strategist import StrategistAgent
            from agents.analyzer import AnalyzerAgent
            from agents.proposer import ProposerAgent
            from agents.validator import ValidatorAgent

            agent_result = None
            if action == "propose_strategy":
                agent = StrategistAgent(provider=self.llm_provider, comm_layer=self.comm_layer)
                agent_result = agent.propose_strategy(
                    payload.get("guess_history", []),
                    payload.get("difficulty", "easy")
                )
            elif action == "analyze_feedback":
                agent = AnalyzerAgent(provider=self.llm_provider, comm_layer=self.comm_layer)
                if is_initial:
                    agent_result = {
                        "correct_positions": [],
                        "correct_colors_wrong_position": [],
                        "constraints": [],
                        "impossible_colors": [],
                        "estimated_remaining": "All codes possible"
                    }
                else:
                    agent_result = agent.analyze_feedback(
                        payload.get("last_guess", []),
                        payload.get("feedback", {}),
                        payload.get("previous_guesses", [])
                    )
            elif action == "propose_guess":
                agent = ProposerAgent(provider=self.llm_provider, comm_layer=self.comm_layer)
                agent_result = agent.propose_guess(
                    strategy=payload.get("strategy", ""),
                    constraints_text="\n".join(payload.get("constraints", [])),
                    available_colors=payload.get("available_colors", []),
                    num_pegs=payload.get("num_pegs", 4)
                )
            elif action == "validate_guess":
                agent = ValidatorAgent(provider=self.llm_provider, comm_layer=self.comm_layer)
                agent_result = agent.validate_with_llm(
                    guess=payload.get("guess", []),
                    available_colors=payload.get("available_colors", []),
                    expected_length=payload.get("expected_length", 4),
                    constraints=payload.get("constraints", {})
                )

            # Send A2A response through communication layer
            response_msg = self.comm_layer.send_response(
                sender_id=target_agent_card.agent_id,
                receiver_id="orchestrator",
                correlation_id=request_msg.message_id,
                payload=agent_result,
                status="success"
            )
            step_info["response_message_id"] = response_msg.message_id
            step_info["result"] = agent_result
            step_info["status"] = "completed"

            return step_info

        except Exception as e:
            step_info["status"] = "failed"
            step_info["error"] = str(e)
            return step_info

    def get_workflow_history(self) -> List[Dict[str, Any]]:
        """Get history of all workflow executions."""
        return self.execution_history

    def get_discovery_info(self) -> Dict[str, Any]:
        """Get information about registered agents."""
        return self.registry.get_registry_info()

    def get_agent_list(self) -> List[Dict[str, Any]]:
        """Get list of all discovered agents."""
        return [card.to_dict() for card in self.registry.list_all_agents()]
