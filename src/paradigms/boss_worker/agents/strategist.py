# Boss-Worker Strategist Agent
# Proposes strategy based on constraints
# Only receives from Boss, only replies to Boss

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import List, Dict, Any, Optional
from base.base_agent import BaseAgent
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType

AGENT_CARD = {
    "agent_id": "strategist_boss_worker",
    "agent_name": "Strategist",
    "agent_type": "worker",
    "paradigm": "boss_worker",
    "version": "1.0.0",
    "description": "Strategist for Boss-Worker paradigm",
    "url": "http://localhost:8103",
    "health_endpoint": "/health",
    "capabilities": {
        "propose_strategy": {
            "description": "Propose strategy based on constraints",
            "parameters": {"type": "object"},
            "returns": {"type": "object"},
        },
    },
    "constraints_owned": ["Strategy coherence"],
    "team_members": ["boss"],
    "can_communicate": False,
}

class StrategistAgent(BaseAgent):
    """Boss-Worker Strategist Agent"""

    def __init__(self, provider: str = "deepseek", comm_layer: Optional[A2ACommunicationLayer] = None,
                 role: Optional[AgentRole] = None, paradigm: Optional[ParadigmType] = None,
                 team_members: Optional[List[str]] = None, can_communicate: bool = False,
                 constraints_owned: Optional[List[str]] = None, registry_url: Optional[str] = None):
        super().__init__(
            name="Strategist_BossWorker", provider=provider, comm_layer=comm_layer,
            role=role or AgentRole.STRATEGIST, paradigm=paradigm or ParadigmType.BOSS_WORKER,
            team_members=team_members or ["boss"],
            can_communicate=can_communicate, constraints_owned=constraints_owned or ["Strategy coherence"],
            registry_url=registry_url,
        )

    def propose_strategy(
        self,
        guess_history: List[Dict],
        difficulty: str,
        analysis: str = "",
        impossible_colors: List[str] = None,
        locked_positions: List[Dict] = None,
        misplaced_colors: List[Dict] = None,
    ) -> Dict[str, Any]:
        """Propose strategy based on game state AND constraint analysis from Analyzer."""
        round_num = len(guess_history) + 1

        constraint_context = ""
        if impossible_colors:
            constraint_context += f"\nImpossible colors: {impossible_colors}"
        if locked_positions:
            constraint_context += f"\nLocked positions: {locked_positions}"
        if misplaced_colors:
            constraint_context += f"\nMisplaced colors: {misplaced_colors}"
        if analysis:
            constraint_context += f"\n\nAnalyzer's constraint analysis:\n{analysis}"

        system_prompt = f"""You are the Strategist in a Mastermind game.
Your role: Based on constraint analysis, recommend the OPTIMAL strategy to solve fastest.

DIFFICULTY: {difficulty}
ROUND: {round_num}
GUESSES SO FAR: {len(guess_history)}
ROUNDS REMAINING: {8 - round_num}

CURRENT CONSTRAINTS:
{constraint_context if constraint_context else "No constraints yet (first round)"}

STRATEGIC DECISION FRAMEWORK:
These phases use constraints to guide the Proposer:

1. EXPLORATION PHASE (Colors unknown):
   - Objective: Discover which colors exist in the secret
   - Constraints: Test colors NOT marked as impossible
   - Guidance: Try different untested colors across positions
   - When to use: Early rounds when we know little

2. CONSTRAINT_BUILDING PHASE (Some colors known):
   - Objective: Narrow down exact colors and locked positions
   - Constraints: Use impossible colors to eliminate options
   - Guidance: Test known colors in different positions
   - When to use: Mid-game after several guesses

3. REFINEMENT PHASE (Colors known, positions uncertain):
   - Objective: Lock down exact position for each color
   - Constraints: Respect locked positions, reposition misplaced colors
   - Guidance: Focus on confirming position of known colors
   - When to use: After knowing most colors but positions vary

4. CONFIRMATION PHASE (Almost solved):
   - Objective: Complete the final locks with minimal guesses
   - Constraints: Use all locked/confirmed info to finalize
   - Guidance: Trust locked positions, test position variations
   - When to use: When most positions are confirmed

Given the constraints above and rounds remaining, what's the OPTIMAL next strategy?

OUTPUT (JSON ONLY):
{{
  "phase": "EXPLORATION|CONSTRAINT_BUILDING|REFINEMENT|CONFIRMATION",
  "strategy": "Specific guidance: test these colors/positions, avoid these patterns, prioritize locked positions, etc.",
  "confidence": 0.85,
  "reasoning": "Why this phase minimizes remaining guesses given current constraints"
}}"""

        user_message = "Based on the analysis and current game state, determine the optimal strategy phase and guidance for the Proposer."

        try:
            response = self.call_llm_conversation(system_prompt, user_message)
        except Exception as e:
            print(f"[Strategist] ERROR: {type(e).__name__}: {e}")
            return {
                "phase": "EXPLORATION",
                "strategy": "Explore color space",
                "confidence": 0.5,
                "reasoning": "Error fallback",
            }

        try:
            result = self.parse_json_response(response)
        except Exception as e:
            print(f"[Strategist] ERROR parsing response: {e}")
            return {
                "phase": "EXPLORATION",
                "strategy": "Explore color space",
                "confidence": 0.5,
                "reasoning": "Error fallback",
            }

        if "error" in result:
            result = {
                "phase": "EXPLORATION",
                "strategy": "Explore color space",
                "confidence": 0.5,
                "reasoning": "Error fallback"
            }

        return result

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent."""
        return self.propose_strategy(
            guess_history=kwargs.get("guess_history", []),
            difficulty=kwargs.get("difficulty", "easy"),
            analysis=kwargs.get("analysis", ""),
            impossible_colors=kwargs.get("impossible_colors", []),
            locked_positions=kwargs.get("locked_positions", []),
            misplaced_colors=kwargs.get("misplaced_colors", []),
        )
