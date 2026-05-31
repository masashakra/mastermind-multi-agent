# Boss-Worker Strategist Agent
# Fully autonomous LLM-based strategy with adaptive learning
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import List, Dict, Any, Optional
from base.base_agent import BaseAgent
from base.agent_card import STRATEGIST_CARD
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType

AGENT_CARD = {
    **STRATEGIST_CARD,
    "agent_id": "strategist_boss_worker",
    "paradigm": "boss_worker",
}

class StrategistAgent(BaseAgent):
    """Boss-Worker Strategist Agent - Fully Autonomous

    Proposes strategies using intelligent reasoning about game state.
    Maintains strategy history and adapts based on results.
    Makes independent decisions about approach changes.
    """

    def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None,
                 role: Optional[AgentRole] = None, paradigm: Optional[ParadigmType] = None,
                 team_members: Optional[List[str]] = None, can_communicate: bool = True,
                 constraints_owned: Optional[List[str]] = None):
        super().__init__(
            name="Strategist_BossWorker", provider=provider, comm_layer=comm_layer,
            role=role or AgentRole.STRATEGIST, paradigm=paradigm or ParadigmType.BOSS_WORKER,
            team_members=team_members or ["boss", "analyzer", "proposer", "validator"],
            can_communicate=can_communicate, constraints_owned=constraints_owned or ["Strategy coherence"],
        )
        # State tracking - Strategist learns and evolves strategy
        self.strategy_history = []
        self.phase_transitions = []
        self.success_metrics = []
        self.current_phase = None

    def propose_strategy(self, guess_history: List[Dict], difficulty: str) -> Dict[str, Any]:
        """Propose strategy using intelligent reasoning.

        The strategist uses its own judgment to:
        - Assess current game progress
        - Decide when to transition between phases
        - Adapt strategy based on results
        - Consider risk/reward tradeoffs
        """
        role_context = self.get_role_system_prompt()

        # Build game state summary
        game_summary = f"Round {len(guess_history) + 1} of 8 (Difficulty: {difficulty})"

        # Analyze guess history for context
        history_analysis = ""
        if guess_history:
            total_colors = guess_history[-1].get("feedback", {}).get("correct_pegs", 0)
            total_positions = guess_history[-1].get("feedback", {}).get("correct_positions", 0)
            history_analysis = f"""
Current Status (from last guess):
- {total_colors} colors found
- {total_positions} correct positions
- {4 - total_colors} colors remaining (assuming 4-peg game)
- {4 - total_positions} positions remaining

Progress Log:
"""
            for i, guess_data in enumerate(guess_history[-4:]):
                fb = guess_data.get("feedback", {})
                colors = fb.get("correct_pegs", 0)
                positions = fb.get("correct_positions", 0)
                history_analysis += f"  Round {len(guess_history) - 3 + i}: {colors} colors, {positions} positions\n"
        else:
            history_analysis = "First round - no data yet. All colors are possible."

        # Strategy history context
        strategy_context = f"Generated {len(self.strategy_history)} strategies so far"

        # Full LLM-based strategy with reasoning
        prompt = f"""{role_context}

## YOUR TASK (Strategy Proposal in Boss-Worker Paradigm)
You are the Strategist. Your job is to propose a high-level approach for the next guesses.
Use your reasoning to decide what phase we're in and what to focus on.

{game_summary}

{history_analysis}

STRATEGIC DECISION PHASES:
1. EXPLORATION: Find all colors in the code (early game, few colors found)
2. CONSTRAINT_BUILDING: Lock positions for confirmed colors (middle game)
3. REFINEMENT: Fine-tune remaining position uncertainty (late game)
4. CONFIRMATION: Verify final solution (very late game)

STRATEGIC THINKING:
1. Progress Assessment:
   - How many colors have we found?
   - How many positions are locked?
   - What's our confidence level?
   - Are we on track for 8 guesses?

2. Phase Determination:
   - Should we stay in current phase or transition?
   - What triggers a phase change?
   - Is difficulty level affecting pace?

3. Risk Management:
   - How many guesses remaining?
   - Should we be conservative or aggressive?
   - What's the risk of running out of guesses?

4. Adaptive Strategy:
   - What worked well in previous rounds?
   - What didn't work - and why?
   - Should we adjust our approach?

5. Next Steps:
   - What should Proposer focus on?
   - What should Analyzer look for?
   - What would advance the game most?

Make your best judgment about the strategy.

OUTPUT (JSON ONLY):
{{
  "phase": "EXPLORATION|CONSTRAINT_BUILDING|REFINEMENT|CONFIRMATION",
  "strategy": "Detailed strategy description",
  "rationale": "Why this phase and strategy at this point",
  "confidence": 0.8,
  "phase_change": false,
  "previous_phase": "EXPLORATION",
  "focus_areas": ["Find 4th color", "Lock position 0"],
  "risk_level": "CONSERVATIVE|BALANCED|AGGRESSIVE",
  "expected_progress": "Expect to find 4th color in this round",
  "contingency": "If this fails, we'll pivot to constraint_building",
  "guidance_for_team": "Proposer should test new color combinations. Analyzer should look for patterns."
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        # Fallback if LLM fails
        if "error" in result:
            result = {
                "phase": "EXPLORATION" if len(guess_history) < 2 else "CONSTRAINT_BUILDING",
                "strategy": "Continue gathering information",
                "rationale": "LLM failed, using default",
                "confidence": 0.3,
                "phase_change": False,
                "risk_level": "BALANCED",
                "guidance_for_team": "Keep exploring"
            }

        # Track strategy in state
        strategy_record = {
            "round": len(guess_history) + 1,
            "phase": result.get("phase", "EXPLORATION"),
            "strategy": result.get("strategy", ""),
            "confidence": result.get("confidence", 0.5),
            "risk_level": result.get("risk_level", "BALANCED")
        }
        self.strategy_history.append(strategy_record)

        # Track phase transitions
        new_phase = result.get("phase", "EXPLORATION")
        if new_phase != self.current_phase:
            self.phase_transitions.append({
                "round": len(guess_history) + 1,
                "from_phase": self.current_phase,
                "to_phase": new_phase,
                "reason": result.get("rationale", "")
            })
            self.current_phase = new_phase

        return result

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent abstract class.

        Delegates to propose_strategy for this agent.
        """
        return self.propose_strategy(
            guess_history=kwargs.get("guess_history", []),
            difficulty=kwargs.get("difficulty", "easy"),
        )
