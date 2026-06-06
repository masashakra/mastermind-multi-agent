# Boss-Worker Proposer Agent
# Generates guesses based on strategy
# Only receives from Boss, only replies to Boss

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import List, Dict, Any, Optional
from base.base_agent import BaseAgent
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType

AGENT_CARD = {
    "agent_id": "proposer_boss_worker",
    "agent_name": "Proposer",
    "agent_type": "worker",
    "paradigm": "boss_worker",
    "version": "1.0.0",
    "description": "Proposer for Boss-Worker paradigm",
    "url": "http://localhost:8104",
    "health_endpoint": "/health",
    "capabilities": {
        "propose_guess": {
            "description": "Propose a guess based on strategy",
            "parameters": {"type": "object"},
            "returns": {"type": "object"},
        },
    },
    "constraints_owned": ["Guess generation"],
    "team_members": ["boss"],
    "can_communicate": False,
}

class ProposerAgent(BaseAgent):
    """Boss-Worker Proposer Agent"""

    def __init__(self, provider: str = "deepseek", comm_layer: Optional[A2ACommunicationLayer] = None,
                 role: Optional[AgentRole] = None, paradigm: Optional[ParadigmType] = None,
                 team_members: Optional[List[str]] = None, can_communicate: bool = False,
                 constraints_owned: Optional[List[str]] = None, registry_url: Optional[str] = None):
        super().__init__(
            name="Proposer_BossWorker", provider=provider, comm_layer=comm_layer,
            role=role or AgentRole.PROPOSER, paradigm=paradigm or ParadigmType.BOSS_WORKER,
            team_members=team_members or ["boss"],
            can_communicate=can_communicate, constraints_owned=constraints_owned or ["Guess generation"],
            registry_url=registry_url,
        )

    def propose_guess(
        self,
        guess_history: List[Dict],
        available_colors: List[str],
        difficulty: str,
        strategy: Dict[str, Any],
        analysis: Dict[str, Any],
        num_pegs: int = 4,
    ) -> Dict[str, Any]:
        """Generate a guess based on strategy and analysis with constraint-driven reasoning."""
        round_num = len(guess_history) + 1

        # Format previous guesses for context
        prev_guesses = []
        for g in guess_history:
            prev_guesses.append({
                "guess": g.get("guess", g),
                "feedback": g.get("feedback", {})
            })

        prev_str = "\n".join(
            f"  Round {i+1}: {g['guess']} → pegs={g['feedback'].get('correct_pegs',0)}  pos={g['feedback'].get('correct_positions',0)}"
            if isinstance(g, dict) else f"  {g}"
            for i, g in enumerate(prev_guesses)
        ) if prev_guesses else "  No guesses yet — this is round 1"

        system_prompt = f"""You are the Proposer agent in a Mastermind game.
Your role: propose the BEST next guess by STRICTLY respecting constraints and using strategy.

CRITICAL RULES:
- Secret code: exactly {num_pegs} color slots, colors CAN repeat
- Available colors: {', '.join(available_colors)}
- GUESS MUST HAVE EXACTLY {num_pegs} COLORS (no more, no less!)
- NEVER repeat any previous guess
- NEVER use impossible colors (marked as impossible in constraint analysis)
- NEVER violate locked positions
- ALWAYS reposition misplaced colors to different positions
- Every color must either be: (A) tested, (B) locked, or (C) repositioned

CONSTRAINT-DRIVEN GUESS GENERATION:
1. PARSE CONSTRAINTS STRICTLY:
   - Extract EXACTLY which colors are impossible
   - Extract EXACTLY which positions are locked with their colors
   - Extract EXACTLY which colors must be repositioned
   - CRITICAL: Identify colors that appear MULTIPLE TIMES in the secret (duplicates!)

2. ELIMINATE OPTIONS:
   - Remove all impossible colors from consideration
   - For locked positions, fix those colors
   - For confirmed-but-misplaced colors, pick different positions
   - If a color must appear multiple times, plan all occurrences strategically

3. FILL REMAINING POSITIONS:
   - Use strategy guidance (exploration vs refinement)
   - If exploring: test untested colors AND test duplicate color placements
   - If refining: test confirmed colors in NEW position combinations
   - Generate DIVERSE guesses that try different position placements for duplicates
   - ENSURE THE GUESS HAS EXACTLY {num_pegs} COLORS!

4. STRICT VALIDATION BEFORE FINALIZING:
   - Does every color in my guess respect constraints?
   - Are locked positions exactly matched?
   - Are misplaced colors in different positions?
   - Is this guess DIFFERENT from all past guesses? (NEVER resubmit!)
   - If colors repeat, did I test new position combinations?
   - DOES MY GUESS HAVE EXACTLY {num_pegs} COLORS?

5. OUTPUT: Commit to the guess with detailed reasoning

You remember all previous guesses and reasoning via conversation history."""

        strategy_guidance = f"""STRATEGY FROM STRATEGIST:
- Phase: {strategy.get('phase', 'EXPLORATION')}
- Strategy: {strategy.get('strategy', 'Test new colors')}
- Reasoning: {strategy.get('reasoning', 'N/A')}
- Confidence: {strategy.get('confidence', 0.5)}"""

        analysis_summary = f"""CONSTRAINT ANALYSIS FROM ANALYZER:
- Confirmed colors: {analysis.get('confirmed_colors', [])}
- Impossible colors: {analysis.get('impossible_colors', [])}
- Locked positions: {analysis.get('locked_positions', [])}
- Misplaced colors: {analysis.get('misplaced_colors', [])}
- Analysis: {analysis.get('analysis', 'None yet')}"""

        user_message = f"""Round {round_num} — propose your next guess using systematic constraint reasoning.
REMEMBER: Your guess MUST have EXACTLY {num_pegs} colors!

{strategy_guidance}

{analysis_summary}

PRIOR GUESSES AND FEEDBACK:
{prev_str}

Now apply the 5-step constraint-driven process to generate the BEST next guess with {num_pegs} colors.

OUTPUT (JSON ONLY):
{{
  "guess": {['color' + str(i+1) for i in range(num_pegs)]},
  "reasoning": "Detailed step-by-step reasoning following the 5-step process",
  "constraints_followed": ["list of constraints this guess respects"],
  "expected_outcome": "What this guess will teach us",
  "confidence": 0.85
}}"""

        try:
            response = self.call_llm_conversation(system_prompt, user_message)
        except Exception as e:
            print(f"[Proposer] ERROR: {type(e).__name__}: {e}")
            return {"guess": available_colors[:4], "reasoning": "Error fallback", "confidence": 0.1}

        try:
            result = self.parse_json_response(response)
            if "guess" not in result:
                result["guess"] = available_colors[:4]
        except Exception as e:
            print(f"[Proposer] ERROR parsing response: {e}")
            result = {"guess": available_colors[:4], "reasoning": "Parse error", "confidence": 0.1}

        return result

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process method required by BaseAgent."""
        return self.propose_guess(
            guess_history=kwargs.get("guess_history", []),
            available_colors=kwargs.get("available_colors", []),
            difficulty=kwargs.get("difficulty", "easy"),
            strategy=kwargs.get("strategy", {}),
            analysis=kwargs.get("analysis", {}),
            num_pegs=kwargs.get("num_pegs", 4),
        )
