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

        # Build context from peer messages (A2A debate)
        peer_intel = self._format_peer_intel()

        # Build competitive context from PUBLIC LEADERBOARD
        leaderboard_text = self._format_leaderboard(public_leaderboard)

        # Build knowledge from reflection & learning
        learned_text = self._format_learned_knowledge()

        prompt = f"""You are {self.team_id}'s Analyser-Strategist, analyzing patterns and developing strategy.

PUZZLE STATE:
- Available colors: {available_colors}
- Code length: {num_pegs} pegs
- Difficulty: {difficulty}

YOUR PAST GUESSES:
{history_text if history_text else "No previous guesses yet."}

YOUR LEARNED KNOWLEDGE (patterns discovered):
{learned_text if learned_text else "No patterns learned yet - this is our first round."}

PUBLIC LEADERBOARD (feedback scores only - guesses are private):
{leaderboard_text if leaderboard_text else "No public scores yet."}

PEER DEBATE MESSAGES (from A2A communication):
{peer_intel if peer_intel else "No peer messages yet."}

YOUR ANALYTICAL TASK:
1. ASSESS: What patterns have we learned? What are peer teams doing?
2. ANALYZE: Which colors/positions are high-confidence based on feedback?
3. STRATEGIZE: What's our next move to maximize information gain?

Develop a clear strategy for the Solver to execute.

Return ONLY valid JSON (no markdown):
{{
  "analysis": "What patterns we've learned, peer strategies, current standing...",
  "strategy": "Clear guidance for Solver: which colors to test, position strategy, etc."
}}
"""

        try:
            response = self.call_llm(prompt)
            result = self._parse_json_response(response)

            return {
                "analysis": result.get("analysis", "Analysis failed"),
                "strategy": result.get("strategy", "Strategy failed"),
            }
        except Exception as e:
            print(f"[{self.team_id} Analyser] LLM error in analyze: {e}")
            return {
                "analysis": f"Error: {str(e)}",
                "strategy": "Continue systematic color testing",
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

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            if "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start < end:
                    json_str = response[start:end]
                    return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        return {}

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process state."""
        return state
