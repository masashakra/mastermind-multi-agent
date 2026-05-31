# Boss-Worker Proposer Agent
# Fully autonomous LLM-based guess generation with strategic reasoning
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import List, Dict, Any, Optional
from base.base_agent import BaseAgent
from base.agent_card import PROPOSER_CARD
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType

AGENT_CARD = {
    **PROPOSER_CARD,
    "agent_id": "proposer_boss_worker",
    "paradigm": "boss_worker",
}

class ProposerAgent(BaseAgent):
    """Boss-Worker Proposer Agent - Fully Autonomous

    Generates guesses using intelligent reasoning and strategic thinking.
    Maintains state of proposed guesses and learns from feedback.
    Makes creative decisions about guess composition and positioning.
    """

    def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None,
                 role: Optional[AgentRole] = None, paradigm: Optional[ParadigmType] = None,
                 team_members: Optional[List[str]] = None, can_communicate: bool = True,
                 constraints_owned: Optional[List[str]] = None):
        super().__init__(
            name="Proposer_BossWorker", provider=provider, comm_layer=comm_layer,
            role=role or AgentRole.PROPOSER, paradigm=paradigm or ParadigmType.BOSS_WORKER,
            team_members=team_members or ["boss", "analyzer", "strategist", "validator"],
            can_communicate=can_communicate, constraints_owned=constraints_owned or ["Constraint-respecting guess generation"],
        )
        # State tracking - Proposer learns from previous proposals
        self.proposed_guesses = []
        self.accepted_guesses = []
        self.rejected_guesses = []
        self.proposal_history = []

    def propose_guess(self, strategy: str, constraints_text: str, available_colors: List[str],
                      num_pegs: int, previous_guesses: List[List[str]]) -> Dict[str, Any]:
        """Generate a guess using intelligent LLM reasoning.

        The proposer uses its own judgment to:
        - Interpret constraints creatively
        - Consider strategic implications
        - Maintain diversity in proposals
        - Balance exploration vs. exploitation
        """
        role_context = self.get_role_system_prompt()

        colors_str = ", ".join(available_colors)

        # Include previous guesses for context
        prev_str = ""
        if previous_guesses:
            prev_str = "\n".join([f"  {i+1}. {g}" for i, g in enumerate(previous_guesses[-4:])])
        else:
            prev_str = "  [No previous guesses - first round]"

        # Include proposal history for learning
        proposal_summary = f"Generated {len(self.proposed_guesses)} proposals so far"
        if self.accepted_guesses:
            proposal_summary += f", {len(self.accepted_guesses)} accepted"
        if self.rejected_guesses:
            proposal_summary += f", {len(self.rejected_guesses)} rejected"

        # Full LLM-based proposal with strategic reasoning
        prompt = f"""{role_context}

## YOUR TASK (Guess Proposal in Boss-Worker Paradigm)
You are the Proposer. Your job is to generate a clever, strategic guess that respects constraints.
Use your creativity and judgment to make the best possible next move.

CURRENT STRATEGY: {strategy}

CONSTRAINTS TO RESPECT:
{constraints_text if constraints_text.strip() else "  [No hard constraints yet - all colors possible]"}

AVAILABLE COLORS: {colors_str}
NUMBER OF PEGS: {num_pegs}

PREVIOUS GUESSES:
{prev_str}

{proposal_summary}

PROPOSAL STRATEGY - Think about:

1. Constraint Satisfaction:
   - What locked positions MUST you use?
   - What impossible colors MUST you avoid?
   - What misplaced colors should you reposition?

2. Exploration vs. Exploitation:
   - Should you explore new colors (early game)?
   - Or refine positions of known colors (late game)?
   - What does the strategy suggest?

3. Diversity:
   - Is this sufficiently different from previous guesses?
   - Or is the new positioning justified by constraints?

4. Strategic Reasoning:
   - What information will this guess reveal?
   - What questions does it answer?
   - Is it risky or conservative - and is that appropriate?

5. Confidence:
   - How confident are you in this guess?
   - Any doubts or alternative proposals?

Think creatively about the color combinations and positions.
Make smart decisions about what to test next.

OUTPUT (JSON ONLY):
{{
  "proposed_guess": ["color1", "color2", "color3", "color4"],
  "reasoning": "Detailed explanation of why you chose this combination",
  "strategy_alignment": "How this aligns with the stated strategy",
  "expected_outcome": "What you expect to learn from this guess",
  "confidence": 0.8,
  "alternatives_considered": ["[color alternatives you thought about]"],
  "risk_assessment": "Is this conservative, balanced, or risky?"
}}"""

        response = self.call_llm(prompt)
        result = self.parse_json_response(response)

        # Fallback if LLM fails
        if "error" in result or "proposed_guess" not in result:
            result = {
                "proposed_guess": available_colors[:num_pegs] if len(available_colors) >= num_pegs else available_colors + ["red"] * (num_pegs - len(available_colors)),
                "reasoning": "LLM generation failed, using default",
                "strategy_alignment": "Unknown",
                "expected_outcome": "Gather baseline data",
                "confidence": 0.2,
                "alternatives_considered": [],
                "risk_assessment": "Conservative (fallback)"
            }

        # Track proposal in state
        proposal_record = {
            "round": len(self.proposed_guesses) + 1,
            "guess": result.get("proposed_guess", []),
            "reasoning": result.get("reasoning", ""),
            "confidence": result.get("confidence", 0.5),
            "status": "proposed"
        }
        self.proposed_guesses.append(result.get("proposed_guess", []))
        self.proposal_history.append(proposal_record)

        return result

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent abstract class.

        Delegates to propose_guess for this agent.
        """
        return self.propose_guess(
            strategy=kwargs.get("strategy", ""),
            constraints_text=kwargs.get("constraints_text", ""),
            available_colors=kwargs.get("available_colors", []),
            num_pegs=kwargs.get("num_pegs", 4),
            previous_guesses=kwargs.get("previous_guesses", []),
        )
