# Coopetition Peer-to-Peer Analyzer-Strategist Agent (Combined)
# Analyzes feedback + develops strategy in single agent
# Communicates with teammate Proposer and opponent team agents via A2A

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from paradigms.coopetition_peer_to_peer.agents.base_agent import BaseAgent
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType


class AnalyzerStrategistAgent(BaseAgent):
    """Coopetition Peer-to-Peer Analyzer-Strategist Agent (Combined)

    Analyzes feedback AND develops strategy in one agent.
    Communicates with Proposer on same team AND opponent team agents via A2A.
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
        opponent_team = "B" if team == "A" else "A"

        super().__init__(
            name=f"AnalyzerStrategist_{team}",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.ANALYZER,  # Primary role
            paradigm=paradigm or ParadigmType.COOPETITION_PEER_TO_PEER,
            team_members=[
                f"proposer_{team.lower()}",
                f"analyzer_strategist_{opponent_team.lower()}",
                f"proposer_{opponent_team.lower()}",
            ],
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

        system_prompt = f"""You are the Analyzer-Strategist on Team {self.team} in a peer-to-peer Mastermind game.

CRITICAL: Output ONLY valid JSON. NO comments, NO text before/after JSON, NO // or /* */ in output.

TASK:
1. Extract constraints from feedback
2. Develop strategy for next guess

MASTERMIND RULES:
- correct_pegs = colors in secret (any position)
- correct_positions = colors in EXACT right position
- pegs=0 → NONE of those colors in secret
- misplaced = pegs - positions

OUTPUT FORMAT - STRICT JSON ONLY:
{{
  "analysis": {{
    "correct_colors": ["color1", "color2"],
    "locked_positions": {{"0": "red", "1": "blue"}},
    "impossible_colors": ["color"],
    "misplaced_colors": {{"red": [0, 2]}}
  }},
  "strategy": {{
    "strategy_name": "broad",
    "rationale": "explanation",
    "confidence": 85,
    "key_assumptions": ["assumption1", "assumption2"]
  }},
  "debate_prep": {{
    "main_argument": "argument",
    "supporting_arguments": ["point1", "point2"],
    "expected_criticisms": ["criticism1"],
    "willingness_to_compromise": true,
    "compromise_suggestion": "what would we accept"
  }},
  "competitive_advantage": {{
    "share_analysis_with_opponent": false,
    "reasoning": "why share or not"
  }}
}}

RULES:
- Output ONLY the JSON object
- No markdown, code blocks, or explanations
- No // or /* */ comments inside JSON
- All strings use double quotes
- Booleans are true or false (no quotes)
- Numbers are integers (0-100)
- All arrays and objects must be properly closed"""

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
                    "willingness_to_compromise": True,
                    "compromise_suggestion": "",
                },
                "competitive_advantage": {
                    "share_analysis_with_opponent": True,
                    "reasoning": "Error, defaulting to cooperation",
                },
            }

    def argue_for_proposal(
        self,
        own_proposal: Dict[str, Any],
        opponent_proposal: Dict[str, Any],
        debate_context: str = "",
    ) -> Dict[str, Any]:
        """Generate arguments for own proposal vs opponent's (peer negotiation)."""

        system_prompt = f"""You are arguing on Team {self.team} in peer-to-peer negotiation (no Judge).

CRITICAL: Output ONLY valid JSON. NO comments, NO text before/after, NO // or /* */.

TASK: Argue why our proposal is better. Consider: win or compromise for goodwill.

OUTPUT FORMAT - STRICT JSON ONLY:

{{
  "main_argument": "strongest reason",
  "supporting_arguments": ["point 1", "point 2"],
  "opponent_strengths": "good points",
  "our_confidence": 85,
  "willingness_to_compromise": true,
  "compromise_suggestion": "what we accept",
  "negotiation_strategy": "win_this_round"
}}

RULES:
- Output ONLY the JSON object
- No markdown, code blocks, or explanations
- No // or /* */ comments
- All strings use double quotes
- Booleans are true or false (no quotes)
- Numbers are integers (0-100)
- Proper JSON syntax required"""

        user_message = f"""Peer debate (no Judge):
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
                "negotiation_strategy": "true_consensus",
            }

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

        elif action == "argue_for_proposal":
            payload = message.get("payload", {})
            result = self.argue_for_proposal(
                own_proposal=payload.get("own_proposal", {}),
                opponent_proposal=payload.get("opponent_proposal", {}),
                debate_context=payload.get("debate_context", ""),
            )
            return {"status": "ok", "result": result}

        elif action == "negotiate_consensus":
            # Direct peer negotiation
            payload = message.get("payload", {})
            return {
                "status": "ok",
                "message": f"AnalyzerStrategist_{self.team} open to negotiation",
                "negotiating": True,
            }

        return {"status": "error", "message": f"Unknown action: {action}"}
