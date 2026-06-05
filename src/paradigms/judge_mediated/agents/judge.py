# Enhanced Judge Agent for Judge-Mediated Speed Racing
# NOT just a scorekeeper - provides COMPETITIVE INTELLIGENCE and STRATEGIC GUIDANCE

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent
from base.role import AgentRole, ParadigmType
from communication.protocol import A2ACommunicationLayer


AGENT_CARD = {
    "agent_id": "judge_judge_mediated",
    "agent_name": "Judge",
    "agent_type": "judge",
    "paradigm": "judge_mediated",
    "version": "2.0.0",  # Enhanced: Now LLM-backed!
    "description": "Judge agent that ranks teams AND provides competitive intelligence",
    "capabilities": {
        "rank_teams": {
            "description": "Rank teams and provide strategic competitive advice",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_results": {"type": "array"},
                    "all_team_histories": {"type": "object"},
                    "pegs_to_solve": {"type": "integer"},
                }
            },
            "returns": {
                "type": "array",
                "description": "Ranking with competitive analysis and strategic advice"
            }
        }
    },
    "constraints_owned": [],
    "team_members": [],
    "can_communicate": True,
}


class JudgeAgent(BaseAgent):
    """Enhanced Judge Agent - Competitive Advisor + Scorekeeper

    Not just ranks teams, but:
    1. Analyzes each team's strategy pattern
    2. Compares performance and learning rate
    3. Identifies competitor strengths/weaknesses
    4. Generates LLM-based strategic advice
    5. Tells each team how to think like better competitors
    """

    def __init__(
        self,
        provider: str = "deepseek",
        comm_layer: Optional[A2ACommunicationLayer] = None,
    ):
        super().__init__(
            name="Judge",
            provider=provider,
            comm_layer=comm_layer,
            role=AgentRole.VALIDATOR,
            paradigm=ParadigmType.JUDGE_MEDIATED,
        )

    def _detect_strategy_pattern(self, team_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze a team's guessing patterns to detect their strategy."""
        if not team_history:
            return {"type": "unknown", "description": "No data yet"}

        guesses = [entry.get("guess", []) for entry in team_history]

        # Check for single-color pattern (all same color)
        single_color_rounds = 0
        for guess in guesses:
            if len(set(guess)) == 1:  # All same color
                single_color_rounds += 1

        if single_color_rounds >= len(guesses) * 0.7:
            return {
                "type": "single_color_testing",
                "description": "Systematically testing single colors",
                "dominance": single_color_rounds / len(guesses)
            }

        # Check for systematic rotation (different colors, consistent pattern)
        if len(set(tuple(g) for g in guesses)) > len(guesses) * 0.8:
            return {
                "type": "mixed_color_testing",
                "description": "Testing diverse color combinations",
                "diversity": len(set(tuple(g) for g in guesses)) / len(guesses)
            }

        return {
            "type": "adaptive",
            "description": "Adapting strategy based on feedback"
        }

    def _analyze_competitor(
        self,
        your_team_id: int,
        competitor_id: int,
        your_results: Dict[str, Any],
        competitor_results: Dict[str, Any],
        your_history: List[Dict[str, Any]],
        competitor_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyze how a competitor is doing and what you can learn."""

        your_pegs = your_results.get("correct_pegs", 0)
        your_positions = your_results.get("correct_positions", 0)
        comp_pegs = competitor_results.get("correct_pegs", 0)
        comp_positions = competitor_results.get("correct_positions", 0)

        comp_strategy = self._detect_strategy_pattern(competitor_history)

        analysis = {
            "team_id": competitor_id,
            "colors_found": comp_pegs,
            "positions_locked": comp_positions,
            "strategy": comp_strategy.get("type", "unknown"),
            "strategy_description": comp_strategy.get("description", ""),
            "how_behind": your_pegs - comp_pegs,
            "position_deficit": your_positions - comp_positions,
        }

        # What they do right
        if comp_pegs >= your_pegs - 1:
            analysis["what_they_do_right"] = "Finding colors at similar pace"
        elif comp_strategy.get("type") == "mixed_color_testing":
            analysis["what_they_do_right"] = "Testing diverse color combinations systematically"
        elif comp_strategy.get("type") == "single_color_testing":
            analysis["what_they_do_right"] = "Consistent, methodical approach"
        else:
            analysis["what_they_do_right"] = "Adapting strategy based on feedback"

        # How to exploit weakness
        if comp_pegs < your_pegs - 1:
            analysis["how_to_exploit"] = f"They're {your_pegs - comp_pegs} colors behind. You've won the color race."
        elif comp_positions < your_positions:
            analysis["how_to_exploit"] = "They found colors but struggle with positions. You're better at position-locking."
        else:
            analysis["how_to_exploit"] = "Stay ahead by consolidating your advantage."

        return analysis

    def _generate_competitive_advice(
        self,
        team_id: int,
        your_results: Dict[str, Any],
        all_results: Dict[int, Dict[str, Any]],
        all_histories: Dict[int, List[Dict[str, Any]]],
    ) -> str:
        """Use LLM to generate strategic advice based on competitive analysis."""

        your_pegs = your_results.get("correct_pegs", 0)
        your_positions = your_results.get("correct_positions", 0)

        # Build competitor summaries
        competitor_summaries = []
        for comp_id in all_results:
            if comp_id == team_id:
                continue

            comp_results = all_results[comp_id]
            comp_history = all_histories.get(comp_id, [])
            analysis = self._analyze_competitor(
                team_id, comp_id, your_results, comp_results,
                all_histories.get(team_id, []), comp_history
            )

            competitor_summaries.append(
                f"Team {comp_id}: Found {comp_results.get('correct_pegs', 0)} colors, "
                f"locked {comp_results.get('correct_positions', 0)} positions. "
                f"Strategy: {analysis['strategy']}. "
                f"Strength: {analysis['what_they_do_right']}. "
                f"Weakness: {analysis['how_to_exploit']}."
            )

        prompt = f"""You are a strategic advisor for a competitive puzzle-solving game.

YOUR TEAM STATUS:
- Colors found: {your_pegs}
- Positions locked: {your_positions}
- Rounds remaining: 1-2 (need to win quickly)

COMPETITOR STATUS:
{chr(10).join(competitor_summaries)}

TASK: Provide strategic advice for your team to win.

Consider:
1. What's your competitive advantage?
2. What can you learn from each competitor's approach?
3. How should you adapt your strategy to capitalize on being ahead?
4. What's your exact next move to consolidate and win?

Provide 3-4 actionable recommendations that:
- Reference specific competitor strategies to copy or avoid
- Give concrete next steps (e.g., "test position permutations of [r,b,g,y]")
- Explain why this beats the competition
- Show confidence based on your lead

Keep it tactical and brief (2-3 sentences max per point).
"""

        try:
            advice = self.call_llm(prompt)
            self.call_count += 1
            return advice
        except Exception as e:
            return f"Strategic analysis in progress: Focus on consolidating your {your_pegs}-color advantage with position testing."

    def rank_teams(
        self,
        team_results: List[Dict[str, Any]],
        all_team_histories: Dict[int, List[Dict[str, Any]]] = None,
        pegs_to_solve: int = 4,
    ) -> List[Dict[str, Any]]:
        """Rank teams by distance AND provide competitive intelligence.

        Args:
            team_results: Current round results from all teams
            all_team_histories: Full game history for all teams (for competitive analysis)
            pegs_to_solve: Number of pegs in the puzzle

        Returns:
            Ranking with competitive analysis and strategic advice for each team
        """

        if all_team_histories is None:
            all_team_histories = {}

        # Calculate basic ranking by distance
        team_scores = []
        for result in team_results:
            team_id = result.get("team_id")
            feedback = result.get("feedback", {})
            correct_positions = feedback.get("correct_positions", 0)
            distance = pegs_to_solve - correct_positions

            team_scores.append({
                "team_id": team_id,
                "distance": distance,
                "feedback": feedback,
            })

        sorted_teams = sorted(team_scores, key=lambda x: x["distance"])

        # Build ranking with competitive intelligence
        ranking = []
        results_by_team = {r.get("team_id"): r.get("feedback", {}) for r in team_results}

        for rank, team_data in enumerate(sorted_teams, start=1):
            team_id = team_data["team_id"]
            your_results = results_by_team.get(team_id, {})

            # Generate competitive analysis for this team
            competitive_analysis = {}
            for comp_id in results_by_team:
                if comp_id != team_id:
                    comp_results = results_by_team[comp_id]
                    analysis = self._analyze_competitor(
                        team_id, comp_id, your_results, comp_results,
                        all_team_histories.get(team_id, []),
                        all_team_histories.get(comp_id, [])
                    )
                    competitive_analysis[f"team_{comp_id}"] = analysis

            # ⭐ COMPETITIVE INTELLIGENCE: Use LLM to generate strategic advice
            # Judge provides actionable competitive recommendations based on team analysis
            strategic_advice = self._generate_competitive_advice(
                team_id,
                your_results,
                results_by_team,
                all_team_histories
            )

            ranking.append({
                "team_id": team_id,
                "rank": rank,
                "distance": team_data["distance"],
                "correct_positions": team_data["feedback"].get("correct_positions", 0),
                "correct_pegs": team_data["feedback"].get("correct_pegs", 0),
                # NEW: Competitive intelligence
                "competitive_analysis": competitive_analysis,
                "strategic_advice": strategic_advice,
            })

        return ranking

    def process(self, **kwargs) -> Dict[str, Any]:
        """Process team results and return ranking with competitive analysis."""
        team_results = kwargs.get("team_results", [])
        all_team_histories = kwargs.get("all_team_histories", {})
        pegs_to_solve = kwargs.get("pegs_to_solve", 4)

        return {
            "ranking": self.rank_teams(
                team_results,
                all_team_histories=all_team_histories,
                pegs_to_solve=pegs_to_solve
            )
        }
