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

        system_prompt = f"""You are the Analyzer-Strategist on Team {self.team} in Mastermind.

OUTPUT ONLY VALID JSON. NO COMMENTS, NO EXPLANATIONS, NO TEXT OUTSIDE JSON.

MASTERMIND RULES:
- correct_pegs = count of colors in secret (any position)
- correct_positions = count of colors in exact right position
- If pegs=0: NONE of those colors are in secret
- misplaced = pegs - positions (colors present but wrong spot)

RESPOND WITH ONLY THIS JSON STRUCTURE (no markdown, no code blocks):
{{
  "analysis": {{
    "correct_colors": [],
    "locked_positions": {{}},
    "impossible_colors": [],
    "misplaced_colors": {{}}
  }},
  "strategy": {{
    "strategy_name": "string",
    "rationale": "string",
    "confidence": 0,
    "key_assumptions": []
  }},
  "debate_prep": {{
    "main_argument": "string",
    "supporting_arguments": [],
    "expected_criticisms": []
  }}
}}"""

        # Build a clean, unambiguous user message with all game history
        history_text = ""
        if shared_knowledge:
            history_text = "\nGAME HISTORY:\n"
            for i, item in enumerate(shared_knowledge, 1):
                g = item.get("guess", [])
                f = item.get("feedback", {})
                pegs = f.get("correct_pegs", 0)
                positions = f.get("correct_positions", 0)
                history_text += f"  Round {i}: guess {g} → {pegs} pegs, {positions} positions\n"

        user_message = f"""CURRENT ROUND {round_num}:
Last guess: {last_guess}
Feedback from that guess: {correct_pegs} correct pegs, {correct_positions} correct positions{history_text}

TASK:
1. Analyze what this feedback tells you about the secret code
2. Identify which colors are definitely in secret, definitely not in secret, and misplaced
3. Develop a strategy for the next guess that maximizes information gain
4. Be confident but acknowledge uncertainties"""

        try:
            response = self.call_llm_conversation(system_prompt, user_message)
            parsed = self.parse_json_response(response)

            # Check if parsing failed and retry with stricter prompt
            if parsed.get("error") == "Failed to parse JSON response":
                print(f"[{self.name}] JSON parsing failed, retrying with stricter prompt...")
                # Retry with even more explicit instruction
                strict_system = system_prompt + "\n\nREMEMBER: You MUST return ONLY the JSON object. Nothing else. Not even one word before or after."
                strict_user = user_message + "\n\nReturn the JSON now:"
                retry_response = self.call_llm_conversation(strict_system, strict_user)
                parsed = self.parse_json_response(retry_response)

            return parsed
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

        system_prompt = f"""You are the Analyzer-Strategist on Team {self.team} in a debate.

CRITICAL: Output ONLY valid JSON. NO comments, NO text before/after, NO // or /* */.

TASK: Compare proposals and argue why ours is better.

OUTPUT FORMAT - STRICT JSON ONLY:
{{
  "main_argument": "strongest reason why our approach is better",
  "supporting_arguments": ["point 1", "point 2", "point 3"],
  "opponent_strengths": "acknowledge good points",
  "our_confidence": 85,
  "willingness_to_compromise": true,
  "compromise_suggestion": "what would we accept"
}}

RULES:
- Output ONLY the JSON object
- No markdown, code blocks, or explanations
- No // or /* */ comments
- All strings use double quotes
- Booleans are true or false (no quotes)
- Numbers are integers (0-100)
- Proper JSON syntax required"""

        user_message = f"""Debate proposals:
Our proposal: {own_proposal}
Their proposal: {opponent_proposal}
Context: {debate_context}"""

        try:
            response = self.call_llm_conversation(system_prompt, user_message)
            parsed = self.parse_json_response(response)

            # Retry if parsing failed
            if parsed.get("error") == "Failed to parse JSON response":
                print(f"[{self.name}] JSON parsing failed on debate, retrying...")
                strict_system = system_prompt + "\n\nRULE: Return ONLY the JSON object. No text before or after."
                strict_user = user_message + "\n\nRespond with JSON only:"
                retry_response = self.call_llm_conversation(strict_system, strict_user)
                parsed = self.parse_json_response(retry_response)

            return parsed
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

        system_prompt = f"""You are proposing a Mastermind guess for Team {self.team}.

CRITICAL: Output ONLY valid JSON. NO comments, NO text before/after, NO // or /* */.

TASK: Propose exactly 4 colors based on strategy.

OUTPUT FORMAT - STRICT JSON ONLY:
{{
  "guess": ["color1", "color2", "color3", "color4"],
  "rationale": "why this guess",
  "confidence": 85
}}

RULES:
- Output ONLY the JSON object
- Guess must be exactly 4 colors
- No markdown, code blocks, or explanations
- No // or /* */ comments
- All strings use double quotes
- Numbers are integers (0-100)
- Proper JSON syntax required"""

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
