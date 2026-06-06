# Coopetition Centralized Analyzer-Strategist Agent (Combined)
# Analyzes feedback + develops strategy in single agent
# Communicates with Proposer on same team via A2A

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from paradigms.coopetition_centralized.agents.base_agent import BaseAgent
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType


class AnalyzerStrategistAgent(BaseAgent):
    """Coopetition Centralized Analyzer-Strategist Agent (Combined)

    Analyzes feedback AND develops strategy in one agent.
    Communicates with Proposer on the same team via A2A.
    """

    def __init__(
        self,
        team: str,
        provider: str = "deepseek",
        comm_layer: Optional[A2ACommunicationLayer] = None,
        paradigm: Optional[ParadigmType] = None,
        registry_url: Optional[str] = None,
    ):
        self.team = team
        self.registry_url = registry_url
        self.proposer_url = None  # Will be discovered/set by orchestrator

        super().__init__(
            name=f"AnalyzerStrategist_{team}",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.ANALYZER,  # Primary role
            paradigm=paradigm or ParadigmType.COOPETITION_CENTRALIZED,
            team_members=[f"proposer_{team.lower()}"],
            can_communicate=True,
            constraints_owned=["Constraint extraction", "Strategy development"],
            registry_url=registry_url,
        )

    def analyze_and_develop_strategy(
        self,
        last_guess: List[str],
        feedback: Dict[str, int],
        previous_guesses: List[Dict[str, Any]] = None,
        shared_knowledge: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze feedback AND develop strategy in one step using DeepSeek R1."""

        correct_pegs = feedback.get("correct_pegs", 0)
        correct_positions = feedback.get("correct_positions", 0)
        round_num = len(previous_guesses or []) + 1

        system_prompt = f"""You are the Analyzer-Strategist on Team {self.team} in a Mastermind coopetition game.
Your dual role:
1. Extract constraints from feedback
2. Develop strategy for next guess based on those constraints

MASTERMIND RULES:
- correct_pegs = total colors in guess that exist in secret
- correct_positions = colors in EXACT right position
- If pegs=0 → NONE of those colors are in secret
- misplaced = pegs - positions = colors that exist but WRONG position

ANALYSIS & STRATEGY TASK:
1. Extract constraints from latest feedback
2. Identify locked positions and impossible colors
3. Develop strategic approach: broad testing vs focused vs position elimination
4. Rate confidence in proposed strategy (0-100%)
5. Prepare arguments for why our approach is better than opponent's

Format response as JSON:
{{
  "analysis": {{
    "correct_colors": [list of colors in secret],
    "locked_positions": {{"position": "color"}},
    "impossible_colors": [list],
    "misplaced_colors": {{"color": [positions]}}
  }},
  "strategy": {{
    "strategy_name": "broad|focused|position|pattern",
    "rationale": "why this approach given current constraints",
    "confidence": 0-100,
    "key_assumptions": ["assumption 1", "assumption 2"]
  }},
  "debate_prep": {{
    "main_argument": "why our strategy is superior",
    "supporting_arguments": ["point 1", "point 2"],
    "expected_criticisms": ["opponent might say X"]
  }}
}}"""

        user_message = f"""Round {round_num} Analysis:
Last Guess: {last_guess}
Feedback: {correct_pegs} correct pegs, {correct_positions} correct positions
Previous guesses: {previous_guesses or []}
Shared knowledge: {shared_knowledge or []}"""

        try:
            response = self.call_llm_conversation(system_prompt, user_message)
            return self.parse_json_response(response)
        except Exception as e:
            print(f"[{self.name}] Error analyzing & developing strategy: {e}")
            return {
                "error": str(e),
                "analysis": {
                    "correct_colors": [],
                    "locked_positions": {},
                    "impossible_colors": [],
                    "misplaced_colors": {},
                },
                "strategy": {
                    "strategy_name": "broad",
                    "rationale": "Error, defaulting to broad testing",
                    "confidence": 0,
                    "key_assumptions": [],
                },
                "debate_prep": {
                    "main_argument": "",
                    "supporting_arguments": [],
                    "expected_criticisms": [],
                },
            }

    def argue_for_proposal(
        self,
        own_proposal: Dict[str, Any],
        opponent_proposal: Dict[str, Any],
        debate_context: str = "",
    ) -> Dict[str, Any]:
        """Generate arguments for own proposal vs opponent's."""

        system_prompt = f"""You are the Analyzer-Strategist on Team {self.team} in a coopetition debate.
Your role: Make the most compelling case for your team's proposal.

DEBATE TASK:
Compare two proposals and argue why your team's is better.
- Use logic and evidence
- Acknowledge opponent's strengths
- Offer to compromise if needed

Format as JSON:
{{
  "main_argument": "strongest reason why our approach is better",
  "supporting_arguments": ["point 1", "point 2", "point 3"],
  "opponent_strengths": "acknowledge good points they have",
  "our_confidence": 0-100,
  "willingness_to_compromise": true|false,
  "compromise_suggestion": "if willing, what would we accept?"
}}"""

        user_message = f"""Debate proposals:
Our proposal: {own_proposal}
Their proposal: {opponent_proposal}
Context: {debate_context}"""

        try:
            response = self.call_llm_conversation(system_prompt, user_message)
            return self.parse_json_response(response)
        except Exception as e:
            print(f"[{self.name}] Error generating arguments: {e}")
            return {
                "error": str(e),
                "main_argument": "Error",
                "supporting_arguments": [],
                "opponent_strengths": "",
                "our_confidence": 0,
                "willingness_to_compromise": True,
                "compromise_suggestion": "",
            }

    def call_proposer_a2a(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call Proposer agent via A2A HTTP POST."""
        if not self.proposer_url:
            # Discover proposer URL from registry
            proposer_id = f"proposer_{self.team.lower()}"
            try:
                reg_response = requests.get(
                    f"{self.registry_url}/agents/{proposer_id}",
                    timeout=5
                )
                if reg_response.status_code == 200:
                    self.proposer_url = reg_response.json().get("url")
            except Exception as e:
                print(f"[{self.name}] Error discovering Proposer from registry: {e}")
                return {"error": str(e)}

        if not self.proposer_url:
            return {"error": "Proposer URL not found"}

        try:
            message = {"action": action, "payload": payload}
            response = requests.post(self.proposer_url, json=message, timeout=60)
            response.raise_for_status()
            return response.json().get("result", response.json())
        except Exception as e:
            print(f"[{self.name}] Error calling Proposer via A2A: {e}")
            return {"error": str(e)}

    def propose_guess_directly(
        self,
        strategy: Dict[str, Any],
        constraints: Dict[str, Any],
        available_colors: List[str] = None,
    ) -> Dict[str, Any]:
        """Propose a guess based on strategy and constraints (fallback if Proposer unavailable)."""
        if not available_colors:
            available_colors = ["red", "blue", "green", "yellow", "white", "black", "orange", "purple"]

        system_prompt = f"""You are proposing the next Mastermind guess for Team {self.team}.
Given the strategy and constraints, propose the best guess (exactly 4 colors).

Format as JSON:
{{
  "guess": ["color1", "color2", "color3", "color4"],
  "rationale": "why this guess",
  "confidence": 0-100
}}"""

        user_message = f"""Strategy: {strategy}
Constraints: {constraints}
Available colors: {available_colors}"""

        try:
            response = self.call_llm_conversation(system_prompt, user_message)
            return self.parse_json_response(response)
        except Exception as e:
            return {
                "guess": available_colors[:4],
                "rationale": "Error, defaulting",
                "confidence": 0,
            }

    def generate_proposal(
        self,
        last_guess: List[str],
        feedback: Dict[str, int],
        previous_guesses: List[Dict[str, Any]] = None,
        shared_knowledge: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze feedback AND generate team proposal."""

        # Step 1: Analyze and develop strategy
        analysis_result = self.analyze_and_develop_strategy(
            last_guess=last_guess,
            feedback=feedback,
            previous_guesses=previous_guesses,
            shared_knowledge=shared_knowledge,
        )

        if analysis_result.get("error"):
            return analysis_result

        # Step 2: Generate proposal directly (or via Proposer if available)
        proposer_payload = {
            "strategy": analysis_result.get("strategy", {}),
            "constraints": analysis_result.get("analysis", {}),
            "available_colors": [
                "red",
                "blue",
                "green",
                "yellow",
                "white",
                "black",
                "orange",
                "purple",
            ],
        }

        # Try Proposer first, fallback to local generation
        proposal_response = self.call_proposer_a2a("propose_guess", proposer_payload)

        if proposal_response.get("error"):
            # Fallback: generate proposal locally
            proposal_response = self.propose_guess_directly(
                strategy=proposer_payload["strategy"],
                constraints=proposer_payload["constraints"],
                available_colors=proposer_payload["available_colors"],
            )

        # Combine analysis + proposal
        return {
            "status": "ok",
            "analysis": analysis_result.get("analysis"),
            "strategy": analysis_result.get("strategy"),
            "debate_prep": analysis_result.get("debate_prep"),
            "proposal": proposal_response,
        }

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent abstract class."""
        action = kwargs.get("action")
        if action == "generate_proposal":
            return self.generate_proposal(
                last_guess=kwargs.get("last_guess", []),
                feedback=kwargs.get("feedback", {}),
                previous_guesses=kwargs.get("previous_guesses", []),
                shared_knowledge=kwargs.get("shared_knowledge", []),
            )
        elif action == "argue_for_proposal":
            return self.argue_for_proposal(
                own_proposal=kwargs.get("own_proposal", {}),
                opponent_proposal=kwargs.get("opponent_proposal", {}),
                debate_context=kwargs.get("debate_context", ""),
            )
        return {"error": f"Unknown action: {action}"}

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming A2A message."""
        action = message.get("action")

        if action == "analyze_and_develop_strategy":
            payload = message.get("payload", {})
            result = self.analyze_and_develop_strategy(
                last_guess=payload.get("last_guess", []),
                feedback=payload.get("feedback", {}),
                previous_guesses=payload.get("previous_guesses", []),
                shared_knowledge=payload.get("shared_knowledge", []),
            )
            return {"status": "ok", "result": result}

        elif action == "generate_proposal":
            payload = message.get("payload", {})
            result = self.generate_proposal(
                last_guess=payload.get("last_guess", []),
                feedback=payload.get("feedback", {}),
                previous_guesses=payload.get("previous_guesses", []),
                shared_knowledge=payload.get("shared_knowledge", []),
            )
            return {"status": "ok", "result": result}

        elif action == "argue_for_proposal":
            payload = message.get("payload", {})
            result = self.argue_for_proposal(
                own_proposal=payload.get("own_proposal", {}),
                opponent_proposal=payload.get("opponent_proposal", {}),
                debate_context=payload.get("debate_context", ""),
            )
            return {"status": "ok", "result": result}

        return {"status": "error", "message": f"Unknown action: {action}"}
