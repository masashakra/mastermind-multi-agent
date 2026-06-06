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

        system_prompt = f"""You are the Analyzer-Strategist on Team {self.team} in a peer-to-peer Mastermind coopetition.
Your dual role:
1. Extract constraints from feedback
2. Develop strategy for next guess based on those constraints
3. Decide: should we share insights with opponent or keep them private?

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
5. Prepare arguments for why our approach is better
6. Assess: is this insight something to share with opponent or keep secret?

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
    "expected_criticisms": ["opponent might say X"],
    "willingness_to_compromise": true|false,
    "compromise_suggestion": "if willing, what would we accept?"
  }},
  "competitive_advantage": {{
    "share_analysis_with_opponent": true|false,
    "reasoning": "why share or not share"
  }}
}}"""

        user_message = f"""Round {round_num} Analysis:
Last Guess: {last_guess}
Feedback: {correct_pegs} correct pegs, {correct_positions} correct positions
Previous guesses: {previous_guesses or []}
Shared knowledge: {shared_knowledge or []}"""

        try:
            response = self.call_llm(system_prompt, user_message)
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

        system_prompt = f"""You are the Analyzer-Strategist on Team {self.team} in a peer-to-peer debate (no Judge).
Your role: Negotiate the best outcome for your team.

PEER-NEGOTIATION CONTEXT:
- Teams will vote on which guess to use (confidence-weighted)
- You need to make a compelling case to win the vote
- But also consider: good relations with opponent team for future rounds

DEBATE TASK:
Compare two proposals and argue why your team's is better.
Consider: would it be better to win this round or compromise to build goodwill?

Format as JSON:
{{
  "main_argument": "strongest reason why our approach is better",
  "supporting_arguments": ["point 1", "point 2", "point 3"],
  "opponent_strengths": "acknowledge good points they have",
  "our_confidence": 0-100,
  "willingness_to_compromise": true|false,
  "compromise_suggestion": "if willing, what would we accept?",
  "negotiation_strategy": "win_this_round|build_goodwill|true_consensus"
}}"""

        user_message = f"""Peer debate (no Judge):
Our proposal: {own_proposal}
Their proposal: {opponent_proposal}
Context: {debate_context}"""

        try:
            response = self.call_llm(system_prompt, user_message)
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
