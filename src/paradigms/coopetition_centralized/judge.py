# Coopetition Centralized Judge — ReConcile-Style Multi-Turn Dialogue
# Judge moderates a negotiation between teams until consensus or voting

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType


class JudgeAgent(BaseAgent):
    """ReConcile-style Judge for Coopetition Centralized paradigm.

    Implements multi-turn dialogue negotiation:
    1. Both teams propose independently
    2. Teams try to convince each other (multiple rounds)
    3. Judge tracks proposals and arguments
    4. If consensus reached → use that guess
    5. If no consensus after N turns → confidence-weighted voting
    """

    MAX_NEGOTIATION_TURNS = 3

    def __init__(
        self,
        agent_urls: Dict[str, str],
        provider: str = "deepseek",
    ):
        self.agent_urls = agent_urls

        # Initialize as BaseAgent for LLM access + conversation history
        super().__init__(
            name="Judge",
            provider=provider,
            role=AgentRole.VALIDATOR,
            paradigm=ParadigmType.COOPETITION_CENTRALIZED,
            team_members=["analyzer_strategist_a", "analyzer_strategist_b"],
            can_communicate=True,
            constraints_owned=["Decision making", "Negotiation mediation"],
            registry_url=None,
        )

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent abstract class."""
        return {"status": "ok", "message": "Judge is a LangGraph node, not called directly"}

    def call_team_a2a(self, team: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call team agent via A2A HTTP."""
        agent_id = f"analyzer_strategist_{team.lower()}"
        url = self.agent_urls.get(agent_id)

        if not url:
            return {"error": f"{agent_id} URL not found"}

        try:
            message = {"action": action, "payload": payload}
            response = requests.post(url, json=message, timeout=300)
            response.raise_for_status()
            return response.json().get("result", response.json())
        except Exception as e:
            print(f"[{self.name}] Error calling {agent_id}: {e}")
            return {"error": str(e)}

    def run_round(
        self,
        last_guess: List[str],
        feedback: Dict[str, int],
        previous_guesses: List[Dict[str, Any]],
        shared_knowledge: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """ReConcile-style round: propose → debate → consensus or vote."""

        print(f"\n[{self.name}] ReConcile-Style Round")
        print(f"{'='*60}")

        # PHASE 1: Both teams generate proposals independently
        print(f"\n[Phase 1] Teams generate proposals independently (no communication)")

        payload = {
            "last_guess": last_guess,
            "feedback": feedback,
            "previous_guesses": previous_guesses,
            "shared_knowledge": shared_knowledge,
        }

        team_a_result = self.call_team_a2a("A", "generate_proposal", payload)
        team_b_result = self.call_team_a2a("B", "generate_proposal", payload)

        print(f"[Debug] Team A result: {team_a_result}")
        print(f"[Debug] Team B result: {team_b_result}")

        if team_a_result.get("error") or team_b_result.get("error"):
            return {
                "error": "Failed to get proposals",
                "team_a_error": team_a_result.get("error"),
                "team_b_error": team_b_result.get("error"),
            }

        team_a_proposal = team_a_result.get("proposal", {})
        team_b_proposal = team_b_result.get("proposal", {})

        print(f"Team A proposes: {team_a_proposal.get('guess')} (confidence: {team_a_proposal.get('confidence')}%)")
        print(f"Team B proposes: {team_b_proposal.get('guess')} (confidence: {team_b_proposal.get('confidence')}%)")

        # Check immediate consensus
        if team_a_proposal.get("guess") == team_b_proposal.get("guess"):
            print(f"\n✓ CONSENSUS on first proposal!")
            return {
                "status": "consensus",
                "winning_guess": team_a_proposal.get("guess"),
                "winning_team": "both",
                "decision_method": "consensus",
                "reasoning": "Teams independently proposed the same guess",
                "negotiation_turns": 0,
            }

        # PHASE 2: Multi-turn negotiation mediated by Judge (ReConcile style)
        # Teams CANNOT talk to each other - only to Judge
        print(f"\n[Phase 2] Judge-mediated negotiation (up to {self.MAX_NEGOTIATION_TURNS} turns)")
        print(f"[Judge announces to both teams]")
        print(f"Team A: {team_a_proposal.get('guess')} ({team_a_proposal.get('confidence')}%)")
        print(f"Team B: {team_b_proposal.get('guess')} ({team_b_proposal.get('confidence')}%)")

        negotiation_history = []
        current_proposal_a = team_a_proposal
        current_proposal_b = team_b_proposal

        for turn in range(1, self.MAX_NEGOTIATION_TURNS + 1):
            print(f"\n--- Judge-Mediated Negotiation Turn {turn} ---")

            # Judge asks Team B: What do you think of Team A's proposal?
            print(f"[Judge to Team B] What do you think of Team A's proposal?")
            response_b = self.call_team_a2a(
                "B",
                "argue_for_proposal",
                {
                    "own_proposal": current_proposal_b,
                    "opponent_proposal": current_proposal_a,
                    "debate_context": f"Judge-mediated negotiation turn {turn} - respond to opponent",
                },
            )

            negotiation_history.append({
                "turn": turn,
                "speaker": "B",
                "response": response_b,
            })

            print(f"[Team B response]")
            print(f"  Main: {response_b.get('main_argument', '')}")
            print(f"  Willing to compromise: {response_b.get('willingness_to_compromise')}")

            # Judge asks Team A: How do you respond?
            print(f"\n[Judge to Team A] How do you respond to Team B's position?")
            response_a = self.call_team_a2a(
                "A",
                "argue_for_proposal",
                {
                    "own_proposal": current_proposal_a,
                    "opponent_proposal": current_proposal_b,
                    "debate_context": f"Judge-mediated negotiation turn {turn} - respond to opponent",
                },
            )

            negotiation_history.append({
                "turn": turn,
                "speaker": "A",
                "response": response_a,
            })

            print(f"[Team A response]")
            print(f"  Main: {response_a.get('main_argument', '')}")
            print(f"  Willing to compromise: {response_a.get('willingness_to_compromise')}")

            # Judge assesses consensus
            both_willing = response_a.get("willingness_to_compromise") and response_b.get("willingness_to_compromise")

            if both_willing:
                print(f"\n✓ Both teams willing to compromise!")
                # Try to converge on same guess
                if current_proposal_a.get("guess") == current_proposal_b.get("guess"):
                    print(f"✓ CONSENSUS reached after {turn} turns!")
                    return {
                        "status": "consensus",
                        "winning_guess": current_proposal_a.get("guess"),
                        "winning_team": "both",
                        "decision_method": "consensus_after_negotiation",
                        "reasoning": f"Teams reached consensus after {turn} turns of Judge-mediated negotiation",
                        "negotiation_turns": turn,
                        "negotiation_history": negotiation_history,
                    }
                else:
                    print(f"  But still proposing different guesses. Judge will decide.")
                    break  # Go to voting
            else:
                # Teams stuck - continue or give up
                if turn < self.MAX_NEGOTIATION_TURNS:
                    print(f"  Teams at impasse. Continuing to turn {turn + 1}...")
                else:
                    print(f"  Reached max negotiation turns. Judge will vote.")
                    break

        # PHASE 3: No consensus - use confidence-weighted voting (ReConcile fallback)
        print(f"\n[Phase 3] No consensus reached → Judge uses confidence-weighted voting")

        decision = self._confidence_weighted_voting(current_proposal_a, current_proposal_b)
        decision["negotiation_turns"] = turn  # How many turns actually happened
        decision["negotiation_history"] = negotiation_history

        print(f"\n[Judge Voting] Team {decision['winning_team']} selected via confidence-weighted voting")
        print(f"[Judge Voting] Team A weight: {decision.get('weight_a', 0):.1%}")
        print(f"[Judge Voting] Team B weight: {decision.get('weight_b', 0):.1%}")

        return decision

    def _confidence_weighted_voting(
        self,
        proposal_a: Dict[str, Any],
        proposal_b: Dict[str, Any],
    ) -> Dict[str, Any]:
        """ReConcile-style Judge decision: multi-turn confidence-weighted analysis."""

        conf_a = proposal_a.get("confidence", 50)
        conf_b = proposal_b.get("confidence", 50)
        total = conf_a + conf_b if (conf_a + conf_b) > 0 else 1
        weight_a = conf_a / total
        weight_b = conf_b / total

        print(f"\n[{self.name}] ReConcile-Style Confidence-Weighted Voting")
        print(f"[{self.name}] Turn 1: Evaluate proposals")

        # TURN 1: Evaluate both proposals objectively
        system_prompt_1 = """You are a Judge evaluating two Mastermind proposals.
Analyze each proposal objectively - not picking a side, just assessing quality.

Assess:
1. Strategy soundness (0-100)
2. How well it addresses current constraints
3. Information gain potential
4. Logical reasoning quality

Format response as JSON:
{
  "team_a_strategy_quality": 0-100,
  "team_b_strategy_quality": 0-100,
  "team_a_strengths": ["strength1", "strength2"],
  "team_b_strengths": ["strength1", "strength2"],
  "team_a_weaknesses": ["weakness1"],
  "team_b_weaknesses": ["weakness1"],
  "initial_preference": "A|B|equal"
}"""

        user_message_1 = f"""Evaluate both proposals:

TEAM A:
Guess: {proposal_a.get('guess')}
Confidence: {conf_a}%
Rationale: {proposal_a.get('rationale')}
Strategy: {proposal_a.get('strategy', 'Unknown')}

TEAM B:
Guess: {proposal_b.get('guess')}
Confidence: {conf_b}%
Rationale: {proposal_b.get('rationale')}
Strategy: {proposal_b.get('strategy', 'Unknown')}

Analyze both objectively."""

        try:
            response_1 = self.call_llm_conversation(system_prompt_1, user_message_1)
            eval_1 = self.parse_json_response(response_1)
            print(f"[{self.name}] Team A strategy quality: {eval_1.get('team_a_strategy_quality', 50)}/100")
            print(f"[{self.name}] Team B strategy quality: {eval_1.get('team_b_strategy_quality', 50)}/100")
        except Exception as e:
            print(f"[{self.name}] Error in Turn 1: {e}")
            eval_1 = {"team_a_strategy_quality": 50, "team_b_strategy_quality": 50}

        # TURN 2: Consider confidence + strategy quality
        print(f"\n[{self.name}] Turn 2: Weigh confidence with strategy quality")

        system_prompt_2 = """You are a Judge deliberating on which proposal to choose.
Consider both confidence scores AND strategy quality from your previous analysis.

ReConcile approach:
1. Confidence weight = confidence / total_confidence
2. Strategy quality = objective assessment
3. Combined score = (confidence_weight * 0.6) + (strategy_quality_normalized * 0.4)

Make your reasoning explicit.

Format response as JSON:
{
  "team_a_confidence_weight": 0-1,
  "team_b_confidence_weight": 0-1,
  "team_a_combined_score": 0-100,
  "team_b_combined_score": 0-100,
  "deciding_factor": "confidence|strategy|equal",
  "preliminary_choice": "A|B"
}"""

        user_message_2 = f"""Weigh the decision:

Team A:
- Confidence: {conf_a}%
- Strategy Quality: {eval_1.get('team_a_strategy_quality', 50)}/100
- Weight: {weight_a:.1%}

Team B:
- Confidence: {conf_b}%
- Strategy Quality: {eval_1.get('team_b_strategy_quality', 50)}/100
- Weight: {weight_b:.1%}

What's your preliminary choice?"""

        try:
            response_2 = self.call_llm_conversation(system_prompt_2, user_message_2)
            eval_2 = self.parse_json_response(response_2)
            print(f"[{self.name}] Preliminary choice: Team {eval_2.get('preliminary_choice', 'A')}")
            print(f"[{self.name}] Deciding factor: {eval_2.get('deciding_factor', 'unknown')}")
        except Exception as e:
            print(f"[{self.name}] Error in Turn 2: {e}")
            # Fallback to simple confidence weighting
            eval_2 = {
                "preliminary_choice": "A" if weight_a >= weight_b else "B",
                "team_a_combined_score": weight_a * 100,
                "team_b_combined_score": weight_b * 100,
            }

        # TURN 3: Final deliberation with reasoning
        print(f"\n[{self.name}] Turn 3: Final deliberation")

        system_prompt_3 = """You are making the FINAL decision as Judge.
You've analyzed both proposals and their confidence levels.
Now commit to a choice with clear reasoning.

Remember ReConcile principles:
- Teams tried to convince each other but couldn't agree
- Confidence-weighted voting is the fair mechanism
- Higher confidence reflects stronger reasoning
- Your job is to ensure a sound, defensible choice

Format response as JSON:
{
  "winning_team": "A|B",
  "winning_guess": ["color1", "color2", "color3", "color4", "color5"],
  "confidence_in_choice": 0-100,
  "final_reasoning": "detailed explanation of why this team's approach is better"
}"""

        user_message_3 = f"""Make final decision:

Team A was chosen: {eval_2.get('preliminary_choice') == 'A'}
Team A confidence: {conf_a}%
Team A strategy quality: {eval_1.get('team_a_strategy_quality', 50)}/100

Team B confidence: {conf_b}%
Team B strategy quality: {eval_1.get('team_b_strategy_quality', 50)}/100

Both teams had their chance to convince each other.
Confidence-weighted voting says: {eval_2.get('preliminary_choice', 'Team A')}

Confirm your final choice and explain why this guess gives us the best shot at solving."""

        try:
            response_3 = self.call_llm_conversation(system_prompt_3, user_message_3)
            result = self.parse_json_response(response_3)

            # Ensure valid result
            if not result.get("winning_guess"):
                if weight_a >= weight_b:
                    result["winning_team"] = "A"
                    result["winning_guess"] = proposal_a.get("guess")
                else:
                    result["winning_team"] = "B"
                    result["winning_guess"] = proposal_b.get("guess")

            result["weight_a"] = weight_a
            result["weight_b"] = weight_b
            result["team_a_strategy_quality"] = eval_1.get("team_a_strategy_quality", 50)
            result["team_b_strategy_quality"] = eval_1.get("team_b_strategy_quality", 50)
            result["decision_method"] = "reconcile_confidence_weighted_voting"
            result["deliberation_turns"] = 3

            print(f"[{self.name}] FINAL DECISION: Team {result.get('winning_team')}")
            print(f"[{self.name}] Confidence in choice: {result.get('confidence_in_choice', 0)}/100")
            print(f"[{self.name}] Reasoning: {result.get('final_reasoning', '')[:100]}...")

            return result

        except Exception as e:
            print(f"[{self.name}] Error in Turn 3: {e}")
            # Fallback
            if weight_a >= weight_b:
                return {
                    "winning_team": "A",
                    "winning_guess": proposal_a.get("guess"),
                    "weight_a": weight_a,
                    "weight_b": weight_b,
                    "decision_method": "confidence_voting_fallback",
                    "final_reasoning": "Fallback to confidence voting",
                    "deliberation_turns": 3,
                }
            else:
                return {
                    "winning_team": "B",
                    "winning_guess": proposal_b.get("guess"),
                    "weight_a": weight_a,
                    "weight_b": weight_b,
                    "decision_method": "confidence_voting_fallback",
                    "final_reasoning": "Fallback to confidence voting",
                    "deliberation_turns": 3,
                }
