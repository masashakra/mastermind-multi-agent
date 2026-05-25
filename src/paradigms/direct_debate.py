# Direct Debate Paradigm
# Coopetition with Peer-to-Peer Unmoderated Discussion
# 3 teams propose competing approaches
# Teams debate and defend approaches directly (no moderator)
# Attempt consensus through self-organization

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


class DirectDebateOrchestrator:
    """Direct Debate Coopetition Paradigm.

    Three teams propose competing approaches.
    Unmoderated peer discussion and debate.
    Teams attempt to self-organize consensus.
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

        self.logger = CommunicationLogger(puzzle["puzzle_id"], "direct-debate")
        self.guess_history = []
        self.round_count = 0
        self.start_time = time.time()
        self.messages = []

        # Track consensus and debate outcomes
        self.consensus_rounds = 0
        self.debate_rounds = 0

    def run(self) -> Dict[str, Any]:
        """Run one complete puzzle with Direct Debate paradigm.

        Returns:
            {
                "puzzle_id": str,
                "paradigm": "direct-debate",
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
                # Direct Debate round
                round_result = self._direct_debate_round()

                # Log all messages
                for msg in round_result.get("messages", []):
                    log_entry = {
                        "timestamp": time.time(),
                        "round_number": self.round_count,
                        "puzzle_id": self.puzzle["puzzle_id"],
                        "paradigm": "direct-debate",
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
                    self.debate_rounds += 1

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
                    "paradigm": "direct-debate",
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
            "paradigm": "direct-debate",
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
                "debate_rounds": self.debate_rounds,
                "total_rounds": self.round_count
            }
        }

    def _direct_debate_round(self) -> Dict[str, Any]:
        """Execute one round with Direct Debate coopetition.

        PHASE 1: GENERATION
        - Each team generates proposal with confidence

        PHASE 2: EVALUATION
        - All guesses executed
        - Confidence scores calculated

        PHASE 3: DIRECT PEER COMMUNICATION
        - Teams share solutions + confidence levels
        - Unmoderated debate and discussion
        - Teams defend and critique approaches

        PHASE 4: CONSENSUS ATTEMPT
        - Teams attempt self-organized consensus
        - If consensus: use that guess
        - If no consensus: vote

        Returns:
            {
                "final_guess": [selected colors],
                "decision_type": "consensus" | "debate",
                "messages": [communication log]
            }
        """
        messages = []
        team_proposals = {}

        # PHASE 1: GENERATION (each team proposes)
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
                "confidence": 0.6 + (team_idx * 0.15)
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
            "agent": "game_engine",
            "type": "all_feedback",
            "content": feedbacks
        })

        # PHASE 3: DIRECT PEER COMMUNICATION (unmoderated)
        messages.append({
            "phase": "peer_communication",
            "agent": "all_teams",
            "recipient": "all_teams",
            "type": "debate_start",
            "content": {
                "proposals": team_proposals,
                "feedbacks": feedbacks,
                "topic": "Unmoderated discussion of approaches"
            }
        })

        # Simulate peer debate (in real system, this would be LLM-mediated discussion)
        debate_points = []
        for team_id in [1, 2, 3]:
            fb = feedbacks.get(team_id, {}).get("feedback")
            if fb and fb.get("correct_positions", 0) > 0:
                debate_points.append({
                    "team": team_id,
                    "argument": "Team has found correct positions, worth refining this approach"
                })
            elif fb and fb.get("correct_pegs", 0) > 2:
                debate_points.append({
                    "team": team_id,
                    "argument": "Team found multiple correct colors, worth exploring positions"
                })

        messages.append({
            "phase": "peer_communication",
            "agent": "all_teams",
            "type": "debate_arguments",
            "content": debate_points
        })

        # PHASE 4: CONSENSUS ATTEMPT
        consensus_reached, consensus_team = self._attempt_consensus(feedbacks)

        if consensus_reached:
            # Consensus reached
            final_guess = team_proposals[consensus_team]["guess"]
            decision_type = "consensus"

            messages.append({
                "phase": "consensus_attempt",
                "agent": "all_teams",
                "type": "consensus_reached",
                "content": {
                    "agreed_team": consensus_team,
                    "guess": final_guess,
                    "reasoning": "Teams agreed on best approach through discussion"
                }
            })
        else:
            # No consensus, run vote
            voted_team = self._run_vote(feedbacks)
            final_guess = team_proposals[voted_team]["guess"]
            decision_type = "debate"

            messages.append({
                "phase": "consensus_attempt",
                "agent": "all_teams",
                "type": "vote_needed",
                "content": {
                    "reason": "Teams could not reach consensus",
                    "winning_team": voted_team,
                    "guess": final_guess
                }
            })

        self.messages.extend(messages)

        return {
            "final_guess": final_guess,
            "decision_type": decision_type,
            "messages": messages
        }

    def _attempt_consensus(self, feedbacks: Dict) -> tuple:
        """Attempt to self-organize consensus.

        Returns:
            (consensus_reached: bool, team_id: int)
        """
        # Consensus if one team is clearly winning
        scores = {}
        for team_id, fb in feedbacks.items():
            if fb["feedback"] is None:
                scores[team_id] = -999
            else:
                scores[team_id] = fb["feedback"].get("correct_positions", 0) * 10 + fb["feedback"].get("correct_pegs", 0)

        best_team = max(scores, key=scores.get)
        best_score = scores[best_team]

        # Consensus if best is clearly better (not just by 1 point)
        if best_score > 5 and best_score > max([scores[t] for t in scores if t != best_team] + [0]) + 2:
            return (True, best_team)

        return (False, 1)

    def _run_vote(self, feedbacks: Dict) -> int:
        """Run voting for best approach.

        Returns:
            Winning team ID
        """
        votes = {}
        for team_id in [1, 2, 3]:
            fb = feedbacks.get(team_id, {}).get("feedback")
            if fb is None:
                votes[team_id] = -1
            else:
                votes[team_id] = fb.get("correct_positions", 0) * 10 + fb.get("correct_pegs", 0)

        return max(votes, key=votes.get)
