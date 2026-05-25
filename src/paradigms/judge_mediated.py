# Judge-Mediated Paradigm
# Competition with Centralized Judge
# 3 independent teams work in parallel, Judge ranks solutions
# Teams are siloed during solving, get private ranked feedback

import time
from typing import Dict, Any, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from game_engine import GameEngine
from agents.analyzer import AnalyzerAgent
from agents.proposer import ProposerAgent
from agents.strategist import StrategistAgent
from agents.validator import ValidatorAgent
from communication_logger import CommunicationLogger


class JudgeMediatedOrchestrator:
    """Judge-Mediated Competition Paradigm.

    Three independent teams work in parallel (siloed).
    Central Judge evaluates all 3 guesses and ranks them.
    Teams receive private feedback about their ranking and performance.
    """

    def __init__(self, puzzle: Dict[str, Any], provider: str = "ollama"):
        """Initialize orchestrator for one puzzle.

        Args:
            puzzle: Puzzle dictionary from puzzle_generator
            provider: "ollama" (dev), "kaggle" (GPU), or "claude" (production)
        """
        self.puzzle = puzzle
        self.provider = provider
        self.game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])

        # Three independent teams (each team has 4 agents)
        self.teams = [
            {
                "id": 1,
                "analyzer": AnalyzerAgent(provider=provider),
                "strategist": StrategistAgent(provider=provider),
                "proposer": ProposerAgent(provider=provider),
                "validator": ValidatorAgent(provider=provider),
                "guesses": [],
                "feedbacks": []
            },
            {
                "id": 2,
                "analyzer": AnalyzerAgent(provider=provider),
                "strategist": StrategistAgent(provider=provider),
                "proposer": ProposerAgent(provider=provider),
                "validator": ValidatorAgent(provider=provider),
                "guesses": [],
                "feedbacks": []
            },
            {
                "id": 3,
                "analyzer": AnalyzerAgent(provider=provider),
                "strategist": StrategistAgent(provider=provider),
                "proposer": ProposerAgent(provider=provider),
                "validator": ValidatorAgent(provider=provider),
                "guesses": [],
                "feedbacks": []
            }
        ]

        self.logger = CommunicationLogger(puzzle["puzzle_id"], "judge-mediated")
        self.guess_history = []
        self.round_count = 0
        self.start_time = time.time()
        self.messages = []

        # Track team rankings
        self.team_rankings = {}

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Judge-Mediated paradigm.

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "judge-mediated",
                "success": bool,
                "guesses": int,
                "rounds": int,
                "elapsed_time": float,
                "guess_history": list,
                "messages": list,
                "token_usage": dict,
                "agent_stats": dict,
                "competition_stats": dict
            }
        """
        while self.round_count < 8 and not self.game_engine.is_game_over():
            self.round_count += 1

            try:
                # Judge-Mediated round: Teams work independently, then Judge ranks
                round_result = self._judge_mediated_round()

                # Log all messages
                for msg in round_result.get("messages", []):
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "judge-mediated",
                        "phase": msg.get("phase", "unknown"),
                        "sender": msg.get("agent", "unknown"),
                        "receiver": msg.get("recipient", "unknown"),
                        "message_type": msg.get("type", "unknown"),
                        "content": msg.get("content", {})
                    }
                    self.logger.log_message(log_entry)

                # Get best guess (from highest-ranked team)
                best_team_id = round_result.get("best_team", 1)
                best_guess = round_result.get("best_guess", [])

                # Submit best guess
                feedback = self.game_engine.submit_guess(best_guess)

                if not feedback.get("valid", False):
                    continue

                # Add to history
                self.guess_history.append({
                    "round": self.round_count,
                    "guess": best_guess,
                    "feedback": feedback.get("feedback", {}),
                    "best_team": best_team_id
                })

                # Check if solved
                if feedback.get("solved", False):
                    break

            except Exception as e:
                log_entry = {
                    "timestamp": time.time(),
                    "round_number": self.round_count,
                    "puzzle_id": self.puzzle["puzzle_id"],
                    "paradigm": "judge-mediated",
                    "phase": "error",
                    "sender": "error_handler",
                    "receiver": "all_agents",
                    "message_type": "error",
                    "content": {"error": str(e)}
                }
                self.logger.log_message(log_entry)
                continue

        elapsed_time = time.time() - self.start_time

        # Determine success
        if self.guess_history:
            last_feedback = self.guess_history[-1].get("feedback", {})
            success = last_feedback.get("correct_positions", 0) == self.puzzle.get("pegs", 4)
        else:
            success = False

        # Collect all agent stats
        all_agent_stats = {}
        for team_idx, team in enumerate(self.teams, 1):
            all_agent_stats[f"team_{team_idx}"] = {
                "analyzer": team["analyzer"].get_stats(),
                "strategist": team["strategist"].get_stats(),
                "proposer": team["proposer"].get_stats(),
                "validator": team["validator"].get_stats(),
            }

        return {
            "puzzle_id": self.puzzle["puzzle_id"],
            "paradigm": "judge-mediated",
            "difficulty": self.puzzle["difficulty"],
            "success": success,
            "guesses": len(self.guess_history),
            "rounds": self.round_count,
            "elapsed_time": elapsed_time,
            "guess_history": self.guess_history,
            "message_count": len(self.logger.get_all_messages()),
            "messages": self.messages,
            "token_usage": {
                "team_1": sum(agent.total_input_tokens + agent.total_output_tokens
                            for agent in [self.teams[0]["analyzer"], self.teams[0]["strategist"],
                                        self.teams[0]["proposer"], self.teams[0]["validator"]]),
                "team_2": sum(agent.total_input_tokens + agent.total_output_tokens
                            for agent in [self.teams[1]["analyzer"], self.teams[1]["strategist"],
                                        self.teams[1]["proposer"], self.teams[1]["validator"]]),
                "team_3": sum(agent.total_input_tokens + agent.total_output_tokens
                            for agent in [self.teams[2]["analyzer"], self.teams[2]["strategist"],
                                        self.teams[2]["proposer"], self.teams[2]["validator"]]),
                "total": sum(sum(agent.total_input_tokens + agent.total_output_tokens
                              for agent in [team["analyzer"], team["strategist"],
                                          team["proposer"], team["validator"]])
                            for team in self.teams)
            },
            "agent_stats": all_agent_stats,
            "competition_stats": {
                "team_rankings": self.team_rankings,
                "best_team": max(self.team_rankings, key=self.team_rankings.get) if self.team_rankings else 1
            }
        }

    def _judge_mediated_round(self) -> Dict[str, Any]:
        """Execute one round with Judge-Mediated competition.

        PHASE 1: PARALLEL WORK
        - Each team works independently (siloed)
        - Each team generates a guess

        PHASE 2: JUDGE EVALUATION
        - Judge executes all 3 guesses
        - Judge ranks teams

        PHASE 3: PRIVATE FEEDBACK
        - Each team gets private feedback about their rank
        - No info about other teams' performance

        Returns:
            {
                "best_guess": [selected colors],
                "best_team": team_id,
                "messages": [communication log]
            }
        """
        messages = []
        team_proposals = {}

        # PHASE 1: PARALLEL WORK (each team works independently)
        for team_idx, team in enumerate(self.teams, 1):
            team_messages = []

            # Analyzer analyzes feedback
            if team["feedbacks"]:
                last_feedback = team["feedbacks"][-1]
                analysis = team["analyzer"].analyze_feedback(
                    last_feedback.get("guess", []),
                    last_feedback.get("feedback", {}),
                    team["guesses"][:-1] if team["guesses"] else []
                )
            else:
                analysis = {
                    "correct_positions": [],
                    "correct_colors_wrong_position": [],
                    "constraints": [],
                    "impossible_colors": [],
                    "estimated_remaining": "All codes possible"
                }

            team_messages.append({
                "phase": "parallel_work",
                "agent": f"team_{team_idx}_analyzer",
                "type": "analysis",
                "content": analysis
            })

            # Strategist proposes strategy
            strategy_result = team["strategist"].propose_strategy(
                team["feedbacks"],
                self.puzzle["difficulty"]
            )

            team_messages.append({
                "phase": "parallel_work",
                "agent": f"team_{team_idx}_strategist",
                "type": "strategy",
                "content": strategy_result
            })

            # Proposer generates guess
            previous_guess_lists = [g for g in team["guesses"]]
            constraints_text = "\n".join(analysis.get("constraints", []))

            proposal = team["proposer"].propose_guess(
                strategy=strategy_result.get("strategy", ""),
                constraints_text=constraints_text,
                available_colors=self.puzzle.get("available_colors", []),
                num_pegs=self.puzzle.get("pegs", 4),
                previous_guesses=previous_guess_lists
            )

            team_messages.append({
                "phase": "parallel_work",
                "agent": f"team_{team_idx}_proposer",
                "type": "proposal",
                "content": {"guess": proposal.get("proposed_guess", [])}
            })

            # Validator checks
            validation = team["validator"].validate_with_llm(
                guess=proposal.get("proposed_guess", []),
                available_colors=self.puzzle.get("available_colors", []),
                expected_length=self.puzzle.get("pegs", 4),
                previous_guesses=previous_guess_lists,
                constraints={
                    "correct_positions": analysis.get("correct_positions", []),
                    "correct_colors_wrong_position": analysis.get("correct_colors_wrong_position", []),
                    "impossible_colors": analysis.get("impossible_colors", [])
                }
            )

            team_messages.append({
                "phase": "parallel_work",
                "agent": f"team_{team_idx}_validator",
                "type": "validation",
                "content": validation
            })

            team_proposals[team_idx] = {
                "guess": proposal.get("proposed_guess", []),
                "analysis": analysis,
                "strategy": strategy_result,
                "validation": validation
            }

            messages.extend(team_messages)

        # PHASE 2: JUDGE EVALUATION
        # Execute all 3 guesses and collect feedbacks
        feedbacks = {}
        for team_id, proposal in team_proposals.items():
            guess = proposal["guess"]
            feedback = self.game_engine.submit_guess(guess)
            feedbacks[team_id] = {
                "guess": guess,
                "feedback": feedback.get("feedback", {}) if feedback.get("valid") else None
            }

            # Store in team's history
            if feedback.get("valid"):
                self.teams[team_id - 1]["guesses"].append(guess)
                self.teams[team_id - 1]["feedbacks"].append({
                    "guess": guess,
                    "feedback": feedback.get("feedback", {})
                })

        # Judge ranks teams
        rankings = self._judge_rank_proposals(feedbacks)
        self.team_rankings = rankings

        messages.append({
            "phase": "evaluation",
            "agent": "judge",
            "type": "rankings",
            "content": {"rankings": rankings}
        })

        # PHASE 3: PRIVATE FEEDBACK
        # Each team gets private feedback about their ranking
        for team_id, rank in rankings.items():
            feedback_msg = {
                "your_rank": rank,
                "your_feedback": feedbacks[team_id],
                "note": "Other teams' performance is private"
            }

            messages.append({
                "phase": "private_feedback",
                "agent": "judge",
                "recipient": f"team_{team_id}",
                "type": "private_ranking",
                "content": feedback_msg
            })

        # Get best team
        best_team = max(rankings, key=rankings.get)
        best_guess = team_proposals[best_team]["guess"]

        self.messages.extend(messages)

        return {
            "best_guess": best_guess,
            "best_team": best_team,
            "messages": messages
        }

    def _judge_rank_proposals(self, feedbacks: Dict[int, dict]) -> Dict[int, int]:
        """Judge ranks teams based on feedback quality.

        Args:
            feedbacks: Dict of {team_id: feedback}

        Returns:
            Dict of {team_id: rank} where rank 1 is best
        """
        scores = {}

        for team_id, fb in feedbacks.items():
            if fb["feedback"] is None:
                scores[team_id] = -1  # Invalid guess
            else:
                # Score based on correct positions and pegs
                correct_pos = fb["feedback"].get("correct_positions", 0)
                correct_pegs = fb["feedback"].get("correct_pegs", 0)
                # Prefer correct positions over just pegs
                score = correct_pos * 10 + correct_pegs
                scores[team_id] = score

        # Sort teams by score (highest first)
        # Return ranking as dict
        sorted_teams = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return {team_id: rank + 1 for rank, (team_id, _) in enumerate(sorted_teams)}
