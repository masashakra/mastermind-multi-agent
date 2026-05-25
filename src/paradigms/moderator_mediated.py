# Moderator-Mediated Paradigm
# Coopetition with Centralized Moderator
# 3 teams propose competing approaches
# Moderator synthesizes and guides toward consensus

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


class ModeratorMediatedOrchestrator:
    """Moderator-Mediated Coopetition Paradigm.

    Three teams propose competing approaches.
    Moderator synthesizes all approaches and creates comprehensive summary.
    All teams see summary and attempt to converge.
    If no consensus: vote on best approach.
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

        # Three teams for coopetition
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

        self.logger = CommunicationLogger(puzzle["puzzle_id"], "moderator-mediated")
        self.guess_history = []
        self.round_count = 0
        self.start_time = time.time()
        self.messages = []

        # Track refinement and consensus
        self.consensus_rounds = 0
        self.vote_rounds = 0

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Moderator-Mediated paradigm.

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "moderator-mediated",
                "success": bool,
                "guesses": int,
                "rounds": int,
                "elapsed_time": float,
                "guess_history": list,
                "messages": list,
                "token_usage": dict,
                "agent_stats": dict,
                "coopetition_stats": dict
            }
        """
        while self.round_count < 8 and not self.game_engine.is_game_over():
            self.round_count += 1

            try:
                # Moderator-Mediated round
                round_result = self._moderator_mediated_round()

                # Log all messages
                for msg in round_result.get("messages", []):
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "moderator-mediated",
                        "phase": msg.get("phase", "unknown"),
                        "sender": msg.get("agent", "unknown"),
                        "receiver": msg.get("recipient", "unknown"),
                        "message_type": msg.get("type", "unknown"),
                        "content": msg.get("content", {})
                    }
                    self.logger.log_message(log_entry)

                # Get final guess
                final_guess = round_result.get("final_guess", [])
                decision_type = round_result.get("decision_type", "vote")

                if decision_type == "consensus":
                    self.consensus_rounds += 1
                else:
                    self.vote_rounds += 1

                # Submit guess
                feedback = self.game_engine.submit_guess(final_guess)

                if not feedback.get("valid", False):
                    continue

                # Add to history
                self.guess_history.append({
                    "round": self.round_count,
                    "guess": final_guess,
                    "feedback": feedback.get("feedback", {}),
                    "decision": decision_type
                })

                # Check if solved
                if feedback.get("solved", False):
                    break

            except Exception as e:
                log_entry = {
                    "timestamp": time.time(),
                    "round_number": self.round_count,
                    "puzzle_id": self.puzzle["puzzle_id"],
                    "paradigm": "moderator-mediated",
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
            "paradigm": "moderator-mediated",
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
            "coopetition_stats": {
                "consensus_rounds": self.consensus_rounds,
                "vote_rounds": self.vote_rounds,
                "total_rounds": self.round_count
            }
        }

    def _moderator_mediated_round(self) -> Dict[str, Any]:
        """Execute one round with Moderator-Mediated coopetition.

        PHASE 1: GENERATION
        - Each team generates a proposal with confidence

        PHASE 2: EVALUATION
        - All guesses executed
        - Confidence scores calculated

        PHASE 3: MODERATED SYNTHESIS
        - Moderator creates comprehensive summary
        - All teams see summary

        PHASE 4: CONSENSUS BUILDING
        - Teams attempt to converge
        - If consensus: use that guess
        - If no consensus: vote

        Returns:
            {
                "final_guess": [selected colors],
                "decision_type": "consensus" | "vote",
                "messages": [communication log]
            }
        """
        messages = []
        team_proposals = {}

        # PHASE 1: GENERATION (each team proposes with confidence)
        for team_idx, team in enumerate(self.teams, 1):
            # Analyzer analyzes
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

            messages.append({
                "phase": "generation",
                "agent": f"team_{team_idx}_analyzer",
                "type": "analysis",
                "content": analysis
            })

            # Strategist proposes strategy
            strategy_result = team["strategist"].propose_strategy(
                team["feedbacks"],
                self.puzzle["difficulty"]
            )

            messages.append({
                "phase": "generation",
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

            messages.append({
                "phase": "generation",
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

            # Store proposal with confidence
            team_proposals[team_idx] = {
                "guess": proposal.get("proposed_guess", []),
                "analysis": analysis,
                "strategy": strategy_result,
                "validation": validation,
                "confidence": 0.7 + (team_idx * 0.1)  # Simulated confidence
            }

        # PHASE 2: EVALUATION
        feedbacks = {}
        for team_id, proposal in team_proposals.items():
            guess = proposal["guess"]
            feedback = self.game_engine.submit_guess(guess)
            feedbacks[team_id] = {
                "guess": guess,
                "feedback": feedback.get("feedback", {}) if feedback.get("valid") else None
            }

            if feedback.get("valid"):
                self.teams[team_id - 1]["guesses"].append(guess)
                self.teams[team_id - 1]["feedbacks"].append({
                    "guess": guess,
                    "feedback": feedback.get("feedback", {})
                })

        messages.append({
            "phase": "evaluation",
            "agent": "moderator",
            "type": "feedback_received",
            "content": feedbacks
        })

        # PHASE 3: MODERATED SYNTHESIS
        # Moderator creates comprehensive summary
        synthesis = {
            "overview": f"Round {self.round_count}: Three proposals evaluated",
            "proposals": []
        }

        for team_id in [1, 2, 3]:
            if team_id in team_proposals:
                proposal = team_proposals[team_id]
                fb = feedbacks.get(team_id, {}).get("feedback")
                synthesis["proposals"].append({
                    "team": team_id,
                    "guess": proposal["guess"],
                    "confidence": proposal["confidence"],
                    "feedback": fb,
                    "strengths": self._get_strengths(fb),
                    "weaknesses": self._get_weaknesses(fb)
                })

        messages.append({
            "phase": "moderated_synthesis",
            "agent": "moderator",
            "recipient": "all_teams",
            "type": "comprehensive_summary",
            "content": synthesis
        })

        # PHASE 4: CONSENSUS BUILDING
        # Teams attempt to converge
        consensus_reached, consensus_team = self._attempt_consensus(team_proposals, feedbacks)

        if consensus_reached:
            # Use consensus guess
            final_guess = team_proposals[consensus_team]["guess"]
            decision_type = "consensus"

            messages.append({
                "phase": "consensus_building",
                "agent": "moderator",
                "recipient": "all_teams",
                "type": "consensus_reached",
                "content": {
                    "agreed_team": consensus_team,
                    "guess": final_guess
                }
            })
        else:
            # Vote for best
            voted_team = self._run_vote(team_proposals, feedbacks)
            final_guess = team_proposals[voted_team]["guess"]
            decision_type = "vote"

            messages.append({
                "phase": "consensus_building",
                "agent": "moderator",
                "recipient": "all_teams",
                "type": "vote_result",
                "content": {
                    "voted_team": voted_team,
                    "guess": final_guess
                }
            })

        self.messages.extend(messages)

        return {
            "final_guess": final_guess,
            "decision_type": decision_type,
            "messages": messages
        }

    def _attempt_consensus(self, proposals: Dict, feedbacks: Dict) -> tuple:
        """Attempt to reach consensus on best approach.

        Returns:
            (consensus_reached: bool, team_id: int)
        """
        # Simple consensus: if one team is clearly best, that's consensus
        best_team = None
        best_score = -1

        for team_id, fb in feedbacks.items():
            if fb["feedback"] is None:
                continue
            score = fb["feedback"].get("correct_positions", 0) * 10 + fb["feedback"].get("correct_pegs", 0)
            if score > best_score:
                best_score = score
                best_team = team_id

        # Consensus if best team is significantly better
        if best_score > 5:
            return (True, best_team)
        return (False, 1)

    def _run_vote(self, proposals: Dict, feedbacks: Dict) -> int:
        """Run team vote for best approach.

        Returns:
            Winning team ID
        """
        # Vote based on feedback performance
        votes = {}
        for team_id in [1, 2, 3]:
            fb = feedbacks.get(team_id, {}).get("feedback")
            if fb is None:
                votes[team_id] = -1
            else:
                votes[team_id] = fb.get("correct_positions", 0) * 10 + fb.get("correct_pegs", 0)

        return max(votes, key=votes.get)

    def _get_strengths(self, feedback: Dict) -> List[str]:
        """Get strengths of a proposal based on feedback."""
        if feedback is None:
            return ["None - invalid guess"]
        strengths = []
        if feedback.get("correct_positions", 0) > 0:
            strengths.append(f"{feedback['correct_positions']} positions correct")
        if feedback.get("correct_pegs", 0) > 0:
            strengths.append(f"{feedback['correct_pegs']} colors correct")
        return strengths if strengths else ["Valid attempt"]

    def _get_weaknesses(self, feedback: Dict) -> List[str]:
        """Get weaknesses of a proposal based on feedback."""
        if feedback is None:
            return ["Invalid guess - violates constraints"]
        pegs = self.puzzle.get("pegs", 4)
        weaknesses = []
        if feedback.get("correct_positions", 0) < pegs:
            weaknesses.append(f"Only {feedback['correct_positions']}/{pegs} positions correct")
        if feedback.get("correct_pegs", 0) == 0:
            weaknesses.append("No correct colors found")
        return weaknesses if weaknesses else ["None - good attempt"]
