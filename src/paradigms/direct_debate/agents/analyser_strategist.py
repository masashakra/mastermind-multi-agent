# Analyser-Strategist Agent — Focused on analysis and inter-team debate
# Analyzes patterns, develops strategy, debates with other teams

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType


AGENT_CARD = {
    "agent_id": "analyser_strategist_direct_debate",
    "agent_name": "Analyser-Strategist Agent",
    "agent_type": "analyser_strategist",
    "paradigm": "direct_debate",
    "version": "1.0.0",
    "description": "Analyser-Strategist agent for pattern analysis and inter-team debate.",
    "url": "http://localhost:8301",
    "capabilities": {
        "analyze": {
            "description": "Analyze puzzle patterns and develop strategy",
            "parameters": {
                "type": "object",
                "properties": {
                    "guess_history": {"type": "array"},
                    "difficulty": {"type": "string"},
                    "public_leaderboard": {"type": "array"},
                },
            },
            "returns": {
                "type": "object",
                "properties": {
                    "analysis": {"type": "string"},
                    "strategy": {"type": "string"},
                },
            },
        },
        "debate": {
            "description": "Debate with other teams' analyser-strategists",
            "parameters": {
                "type": "object",
                "properties": {
                    "round_number": {"type": "integer"},
                    "my_result": {"type": "object"},
                    "all_results": {"type": "object"},
                },
            },
            "returns": {
                "type": "object",
                "properties": {
                    "debate_message": {"type": "string"},
                    "confidence": {"type": "number"},
                },
            },
        },
    },
    "constraints_owned": ["Analysis", "Strategy", "Team Debate"],
    "team_members": [],
    "can_communicate": True,  # Only analyser-strategist communicates with other teams
}


class AnalyserStrategist(BaseAgent):
    """Analyser-Strategist Agent — Analyzes patterns and debates with other teams.

    Responsibilities:
    - Analyze feedback patterns
    - Develop solving strategy
    - Debate with other teams' analyser-strategists
    - Instruct team's Solver agent
    - Track learned knowledge
    """

    def __init__(self, provider: str = "deepseek", team_id: str = "team_1"):
        super().__init__(
            name=f"AnalyserStrategist_{team_id}",
            provider=provider,
            role=AgentRole.ANALYZER,
            paradigm=ParadigmType.DIRECT_DEBATE,
            team_members=[],
            can_communicate=True,  # Debates with other teams
            constraints_owned=["Analysis", "Strategy", "Team Debate"],
        )
        self.team_id = team_id
        # Store peer messages for debate context
        self.peer_messages = []
        # Game reflection & learning (shared with solver via instruction)
        self.learned_hypotheses = []
        self.color_analysis = {}
        self.position_analysis = {}
        # Links to team partner
        self.solver_url = None

    def analyze_and_strategize(
        self,
        guess_history: List[Dict[str, Any]],
        difficulty: str,
        available_colors: List[str],
        num_pegs: int,
        public_leaderboard: List[Dict[str, Any]] = None,
        constraints: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Analyze patterns and develop strategy for Solver.

        Args:
            guess_history: List of previous guesses and feedback
            difficulty: Puzzle difficulty level
            available_colors: Available colors
            num_pegs: Number of pegs in code
            public_leaderboard: Public leaderboard (feedback scores only)

        Returns:
            {
                "analysis": "...",
                "strategy": "...",
            }
        """
        # Build context from guess history
        history_text = self._format_history(guess_history)

        # Build constraint context like boss_worker
        constraint_text = ""
        if constraints:
            impossible = constraints.get("impossible_colors", [])
            confirmed = constraints.get("confirmed_colors", [])
            locked = constraints.get("locked_positions", [])
            misplaced = constraints.get("misplaced_colors", [])

            if impossible:
                constraint_text += f"\n✗ IMPOSSIBLE COLORS: {impossible}"
            if confirmed:
                constraint_text += f"\n✓ CONFIRMED COLORS (in code): {confirmed}"
            if locked:
                constraint_text += f"\n🔒 LOCKED POSITIONS: {locked}"
            if misplaced:
                constraint_text += f"\n↔️ MISPLACED COLORS: {misplaced}"

        # Build knowledge from reflection & learning
        learned_text = self._format_learned_knowledge()

        # Initialize missing variables for backward compatibility
        leaderboard_text = ""
        peer_intel = ""

        # Extract list of previously tested guesses for diversity check
        previous_guesses = [str(e.get('guess', [])) for e in guess_history]

        prompt = f"""You are {self.team_id}'s Analyser-Strategist.

MASTERMIND CONSTRAINTS (PERSISTENT MEMORY):
You have perfect memory of all prior analysis. Build on previous reasoning - never contradict.
{constraint_text if constraint_text else "(First round - no constraints yet)"}

⚠️ CONSTRAINT→ACTION MAPPING (CRITICAL):
{self._generate_constraint_actions(constraints, previous_guesses) if constraints else "First round - no constraints to map"}

🚫 AVOID THESE GUESSES (already tested):
{str(previous_guesses[-5:]) if previous_guesses else "None yet"}

YOU are solving {self.team_id}'s Analyser-Strategist, analyzing patterns and developing ADAPTIVE strategy.

PUZZLE STATE:
- Available colors: {available_colors}
- Code length: {num_pegs} pegs
- Difficulty: {difficulty}
- ROUND: {len(guess_history) + 1}

YOUR PAST GUESSES & FEEDBACK:
{history_text if history_text else "Round 1 (FIRST ROUND) - No previous feedback yet."}

⚠️ CRITICAL: YOU MUST ANALYZE FEEDBACK TO BUILD CONSTRAINTS:
- Which colors got positive feedback (correct_pegs > 0)?
- Which colors got ZERO feedback (definitely NOT in code)?
- Which positions were correct (correct_positions)?
- Which positions were WRONG (colors in code but wrong position)?
- SPECIAL: If correct_pegs == 4 but correct_positions < 4, the code contains DUPLICATE colors!

YOUR LEARNED KNOWLEDGE (patterns discovered):
{learned_text if learned_text else "No patterns learned yet - this is our first round."}

YOUR ANALYTICAL TASK:
1. CALCULATE MISPLACED: misplaced = correct_pegs - correct_positions
   - This tells us how many colors exist in code but are in wrong positions

2. BUILD CONSTRAINTS: Analyze ALL feedback cumulatively to identify:
   - Confirmed colors (any with positive feedback at any point)
   - Eliminated colors (any with 0 feedback when tested)
   - Locked positions (correct_positions feedback)
   - Misplaced colors (from misplaced calculation above)
   - DUPLICATE DETECTION: If 4p < 4pos, code has duplicate colors

3. IDENTIFY PHASE:
   - EXPLORATION (Round 1): Test diverse colors to discover palette
   - CONSTRAINT_BUILDING (Rounds 2-5): Use eliminations to narrow colors and find exact 4
   - REFINEMENT (Rounds 5-7): Lock positions of known colors SYSTEMATICALLY
   - CONFIRMATION (Rounds 7-8): Test final hypotheses, verify duplicates

4. STRATEGIZE NEXT MOVE based on FEEDBACK PATTERN:

   **CRITICAL DECISION: Are you in COLOR DISCOVERY or POSITION REFINEMENT?**

   CHECK: Did you ever achieve 4p feedback at any point?
   - If YES: Go to POSITION REFINEMENT (all colors correct, find positions)
   - If NO: Stay in COLOR DISCOVERY (one color is wrong, find which one)

   **COLOR DISCOVERY (when 3p feedback, no 4p ever):**
   - You have 4 colors tested [A,B,C,D] with 3p feedback
   - ONE of A,B,C,D is WRONG and must be replaced
   - DO NOT waste rounds testing rotations! You're still finding colors!
   - Replace each position's color with untested colors:
     * Guess 1: [A,B,C,D] → 3p (one is wrong)
     * Guess 2: [A,B,C,E] (replace D) - if 4p, D was wrong! If 3p, D is OK
     * Guess 3: [A,B,F,D] (replace C) - if 4p, C was wrong! If 3p, C is OK
     * Continue until you get 4p or eliminate all candidates

   **For 3p feedback (one color wrong):**
   - CRITICAL: First check - do you have correct_positions > 0?
   - If YES (e.g., 3p 2pos): Some colors ARE correct and LOCKED in position
     * Strategy: ROTATE the confirmed colors to find the locked positions
     * Example: If [A,B,C,D]→3p 2pos, test [B,C,D,A], [C,D,A,B], [D,A,B,C]
     * This finds which position is locked, not which color is wrong
   - If NO (3p 0pos): You have 3 correct colors but ALL in wrong positions
     * Strategy: Test position rotations FIRST before introducing new colors
     * Example: [A,B,C,D]→3p 0pos, test [B,C,D,A], then [C,D,A,B], etc.
   - Only after exhausting position tests should you test replacing colors:
     * Replace D with E: [A, B, C, E]
     * Replace C with F: [A, B, F, D]
     * Continue systematically until you get 4p
   - CRITICAL: Never spend 3+ rounds with same 4 colors if only getting 3p!

   **For 4p feedback (all colors correct - POSITION REFINEMENT):**

   - CRITICAL: Count how many positions are correct (from 4p Npos feedback)
   - If N=3: Almost solved! Only 1 wrong position - test moving that color
   - If N=2: Test swaps of only the 2 wrong positions
   - If N=1 or N=0: Test systematic rotations

   Example strategy for 4p 3pos:
     - [A,B,C,D]→4p 3pos means exactly 1 position is wrong
     - Try swapping each position: [D,B,C,A], [A,D,C,B], [A,B,D,C]
     - One will be 4p 4pos (solution)!

   Example strategy for 4p 2pos:
     - [A,B,C,D]→4p 2pos means 2 positions are correct, 2 are wrong
     - Test swaps of only the wrong positions
     - [D,B,C,A] or [A,D,C,B] or [A,B,D,C]

   **SPECIAL: When correct_positions ≥ 3 (very close to solution):**
   - You've locked 3+ positions correctly! You only need the 4th color or position
   - STRATEGY: Look back at colors that appeared in EARLY ROUNDS with positive feedback
   - Test replacing the suspected "wrong" color with a color from early rounds
   - EXAMPLE: If you had ['red','blue','green','yellow']→3p 1pos in Round 1, and later ['yellow','blue','green','black']→3p 3pos
     - Then 'red' (from Round 1) is more likely correct than a completely new color
     - Next guess: Test ['red','blue','green','black'] or similar with red instead of yellow
   - AVOID: Testing completely untested colors when so close - prioritize colors with prior positive feedback!

   - Never repeat identical guess - always adapt based on feedback!

Return ONLY valid JSON (no markdown):
{{
  "analysis": "What we know from all rounds combined",
  "strategy": "ROUND {len(guess_history) + 1}: [Specific action based on constraints]",
  "confidence": 0.85
}}
"""

        try:
            # ✅ Use conversation history like boss_worker for persistent memory
            response = self.call_llm_conversation(prompt, f"Analyze Round {len(guess_history) + 1} and propose strategy")
            result = self._parse_json_response(response)

            # Provide intelligent fallback strategies when parsing fails
            if not result or "strategy" not in result:
                fallback_strategy = self._get_fallback_strategy(guess_history)
                strategy = result.get("strategy", fallback_strategy)
            else:
                strategy = result.get("strategy")

            return {
                "analysis": result.get("analysis", "Fallback analysis: Maximize information from feedback"),
                "strategy": strategy,
            }
        except Exception as e:
            print(f"[{self.team_id} Analyser] LLM error in analyze: {e}")
            return {
                "analysis": f"Error: {str(e)}",
                "strategy": self._get_fallback_strategy(guess_history),
            }

    def debate(
        self,
        round_number: int,
        my_result: Dict[str, Any],
        all_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Debate with other teams' analyser-strategists.

        Args:
            round_number: Current round
            my_result: This team's result (guess + feedback)
            all_results: All teams' results

        Returns:
            {
                "debate_message": "...",
                "confidence": 0.0-1.0,
            }
        """
        # Format all results for LLM
        results_text = "\n".join([
            f"{team_id}: guess={result.get('guess')}, "
            f"feedback=pegs:{result.get('feedback', {}).get('correct_pegs', 0)} "
            f"pos:{result.get('feedback', {}).get('correct_positions', 0)}"
            for team_id, result in all_results.items()
        ])

        # Format peer messages for debate context
        peer_messages_text = self._format_peer_messages_for_debate(round_number)

        my_guess = my_result.get("guess", [])
        my_feedback = my_result.get("feedback", {})

        prompt = f"""You are {self.team_id}'s Analyser-Strategist in a competitive Mastermind game.

ROUND {round_number} RESULTS:
{results_text}

YOUR PERFORMANCE:
- Guess: {my_guess}
- Correct pegs: {my_feedback.get('correct_pegs', 0)}
- Correct positions: {my_feedback.get('correct_positions', 0)}

PEER STATEMENTS THIS ROUND:
{peer_messages_text if peer_messages_text else "(No peer statements yet)"}

YOUR TASK — STRATEGIC DEBATE:
Engage with peer teams on the actual puzzle-solving strategy. This is a substantive discussion, not a fight.

1. SHARE what your feedback told you — what colors/positions have you confirmed or eliminated?
2. QUESTION or BUILD ON peer insights — if they got useful feedback, acknowledge it and reason about what it implies
3. PROPOSE your next strategic direction — what hypothesis are you testing and why is it the best use of information?

Keep it focused on the puzzle logic. 2-3 sentences max.

Return ONLY valid JSON:
{{
  "debate_message": "Your strategic insight and response to peer reasoning...",
  "confidence": 0.0-1.0
}}"""

        try:
            response = self.call_llm(prompt)
            result = self._parse_json_response(response)

            confidence = result.get("confidence", 0.5)
            if not isinstance(confidence, (int, float)):
                confidence = 0.5
            confidence = max(0.0, min(1.0, float(confidence)))

            return {
                "debate_message": result.get("debate_message", "Unable to analyze standing"),
                "confidence": confidence,
            }
        except Exception as e:
            print(f"[{self.team_id} Analyser] LLM error in debate: {e}")
            my_pegs = my_feedback.get("correct_pegs", 0)
            my_positions = my_feedback.get("correct_positions", 0)
            return {
                "debate_message": f"Round {round_number}: Status unclear (pegs={my_pegs}, pos={my_positions})",
                "confidence": 0.5,
            }

    def receive_peer_message(self, sender: str, message: str, round_num: int) -> None:
        """Store peer message for debate context."""
        self.peer_messages.append({
            "sender": sender,
            "message": message,
            "round": round_num,
        })

    def reflect_on_round(self, round_num: int, guess: List[str], feedback: Dict[str, Any]) -> None:
        """Analyze feedback and build learned hypotheses."""
        pegs = feedback.get("correct_pegs", 0)
        positions = feedback.get("correct_positions", 0)

        # Analyze color appearances
        for color in guess:
            if color not in self.color_analysis:
                self.color_analysis[color] = {"in_guesses": 0, "correct_feedback": 0}
            self.color_analysis[color]["in_guesses"] += 1

        # If we got correct_pegs feedback, those colors are likely in the code
        if pegs > 0:
            if not any(h.startswith(f"R{round_num}: Colors in code") for h in self.learned_hypotheses):
                hypothesis = f"R{round_num}: {pegs} colors from {guess} are in code (feedback: {pegs}p {positions}pos)"
                self.learned_hypotheses.append(hypothesis)

        # Position analysis: If we got positions right, lock those
        if positions > 0:
            hypothesis = f"R{round_num}: {positions} colors locked in positions (feedback: {pegs}p {positions}pos). Guess: {guess}"
            self.learned_hypotheses.append(hypothesis)

        # If we got 0 pegs, we learned which colors are NOT in code
        if pegs == 0:
            wrong_colors = ", ".join(guess)
            hypothesis = f"R{round_num}: Colors NOT in code: {wrong_colors}"
            self.learned_hypotheses.append(hypothesis)

        # Track color frequency
        for color in guess:
            if color not in self.color_analysis:
                self.color_analysis[color] = {"in_guesses": 0, "correct_feedback": 0}
            self.color_analysis[color]["in_guesses"] += 1
            if pegs > 0:
                self.color_analysis[color]["correct_feedback"] += 1

    def _generate_constraint_actions(self, constraints: Dict[str, Any], previous_guesses: list) -> str:
        """Generate explicit constraint→action mappings."""
        if not constraints:
            return "No constraints yet"

        impossible = constraints.get("impossible_colors", [])
        confirmed = constraints.get("confirmed_colors", [])
        locked = constraints.get("locked_positions", [])
        misplaced = constraints.get("misplaced_colors", [])

        actions = []

        # Action 1: Eliminate impossible colors
        if impossible:
            actions.append(f"NEVER use these colors again: {impossible}")

        # Action 2: Prioritize confirmed colors
        if confirmed and len(confirmed) < 4:
            actions.append(f"MUST USE confirmed colors: {confirmed} (need {4-len(confirmed)} more)")

        # Action 3: Lock known positions
        if locked:
            locked_str = ", ".join([f"pos{p}={c}" for p, c in locked])
            actions.append(f"LOCK these positions: {locked_str}")

        # Action 4: Test misplaced colors in different positions
        if misplaced:
            misplaced_colors = list(set([m.get("color") for m in misplaced]))
            actions.append(f"Test {misplaced_colors} in DIFFERENT POSITIONS (currently misplaced)")

        return "\n".join([f"  • {a}" for a in actions]) if actions else "No constraint actions yet"

    def _format_learned_knowledge(self) -> str:
        """Format learned hypotheses and analysis for LLM context."""
        if not self.learned_hypotheses and not self.color_analysis:
            return ""

        lines = []
        lines.append("LEARNED PATTERNS & HYPOTHESES:")

        if self.learned_hypotheses:
            for hyp in self.learned_hypotheses[-5:]:  # Last 5 learnings
                lines.append(f"  • {hyp}")

        if self.color_analysis:
            high_confidence_colors = [
                c for c, stats in self.color_analysis.items()
                if stats["correct_feedback"] >= 2
            ]
            if high_confidence_colors:
                lines.append(f"  • HIGH CONFIDENCE colors: {high_confidence_colors}")

        return "\n".join(lines)

    def _format_leaderboard(self, public_leaderboard: List[Dict[str, Any]]) -> str:
        """Format public leaderboard (feedback scores only, no guesses)."""
        if not public_leaderboard:
            return ""

        lines = []
        team_best_scores = {}

        for entry in public_leaderboard:
            team = entry.get("team_id", "unknown")
            fb = entry.get("feedback", {})
            pegs = fb.get("correct_pegs", 0)
            pos = fb.get("correct_positions", 0)
            solved = entry.get("solved", False)

            if team not in team_best_scores:
                team_best_scores[team] = (pegs, pos)
            else:
                old_p, old_pos = team_best_scores[team]
                if pegs > old_p or (pegs == old_p and pos > old_pos):
                    team_best_scores[team] = (pegs, pos)

            if solved:
                lines.append(f"{team}: {pegs}p {pos}pos ✅ SOLVED")

        if team_best_scores:
            lines.append("\nCurrent Standings (best score per team):")
            for team in sorted(team_best_scores.keys()):
                pegs, pos = team_best_scores[team]
                marker = "⭐" if team == self.team_id else ""
                lines.append(f"  {team}: {pegs}p {pos}pos {marker}")

        return "\n".join(lines)

    def _format_peer_intel(self) -> str:
        """Format recent peer messages as competitive intelligence."""
        if not self.peer_messages:
            return ""

        lines = []
        for msg in self.peer_messages[-6:]:  # Last 6 messages
            sender = msg.get("sender", "unknown")
            round_num = msg.get("round", "?")
            message = msg.get("message", "")
            lines.append(f"[{sender} R{round_num}] {message}")

        return "\n".join(lines)

    def _format_peer_messages_for_debate(self, current_round: int) -> str:
        """Format this round's peer messages for debate response."""
        this_round_msgs = [m for m in self.peer_messages if m.get("round") == current_round]

        if not this_round_msgs:
            return ""

        lines = []
        for msg in this_round_msgs:
            sender = msg.get("sender", "unknown").replace("agent_", "")
            message = msg.get("message", "")
            lines.append(f"{sender}: \"{message}\"")

        return "\n".join(lines)

    def _format_history(self, guess_history: List[Dict[str, Any]]) -> str:
        """Format guess history for LLM context."""
        if not guess_history:
            return ""

        lines = []
        for entry in guess_history:
            guess = entry.get("guess", [])
            feedback = entry.get("feedback", {})
            pegs = feedback.get("correct_pegs", 0)
            positions = feedback.get("correct_positions", 0)
            lines.append(f"Round {entry.get('round')}: {guess} → {pegs} pegs, {positions} positions")

        return "\n".join(lines)

    def _get_fallback_strategy(self, guess_history: List[Dict[str, Any]]) -> str:
        """Generate intelligent fallback strategy when LLM parsing fails."""
        if not guess_history:
            return "Start with four distinct colors to test which are in the code: red, blue, green, yellow."

        # Analyze what we've learned
        recent_guesses = guess_history[-3:] if len(guess_history) >= 3 else guess_history

        # Count high-confidence colors from recent feedback
        color_feedback = {}
        for entry in recent_guesses:
            feedback = entry.get("feedback", {})
            pegs = feedback.get("correct_pegs", 0)
            if pegs >= 3:  # At least 3 colors correct
                guess = entry.get("guess", [])
                for color in set(guess):
                    color_feedback[color] = color_feedback.get(color, 0) + 1

        if color_feedback:
            confident_colors = sorted(color_feedback.items(), key=lambda x: -x[1])[:3]
            color_list = [c[0] for c in confident_colors]
            remaining = ['red', 'blue', 'green', 'yellow', 'black', 'white', 'orange', 'purple']
            new_color = [c for c in remaining if c not in color_list][0] if len(color_list) < 4 else color_list[0]
            return f"Test positions with high-confidence colors {color_list} and one new color to narrow down correct arrangement."

        return "Test a new combination of colors not yet tried to maximize information gain."

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response with robust error handling."""
        import re

        try:
            if "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start < end:
                    json_str = response[start:end]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # Try fixing common issues
                        # Fix unquoted keys: {key: -> {"key":
                        json_str = re.sub(r'(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            pass
        except (json.JSONDecodeError, ValueError):
            pass

        # If parsing fails, return empty dict - caller will use defaults
        return {}

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process state."""
        return state
