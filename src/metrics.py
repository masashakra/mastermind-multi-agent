#!/usr/bin/env python3
"""
Metrics module for tracking Mastermind solver performance.

Focused on essential metrics for paradigm comparison:
- Task Success: solve rate, guesses, failure rate
- Communication: token usage, message count
- Coordination: convergence, role adherence
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class MetricsCollector:
    """Collects metrics for a single puzzle-solving session."""

    def __init__(self, puzzle_id: str, paradigm: str, difficulty: str,
                 secret_code: Optional[List[str]] = None,
                 available_colors: Optional[List[str]] = None,
                 provider: str = "openai"):
        self.puzzle_id = puzzle_id
        self.paradigm = paradigm
        self.difficulty = difficulty

        # Puzzle metadata (for analysis)
        self.secret_code = secret_code
        self.available_colors = available_colors
        self.provider = provider

        # Timing
        self.timestamp_start = datetime.now().isoformat()
        self.timestamp_end: Optional[str] = None

        # Task success metrics
        self.success = False
        self.guesses = 0
        self.rounds = 0
        self.termination_reason = None

        # Communication metrics
        self.token_usage = {
            "total_input": 0,
            "total_output": 0,
            "per_round": []
        }

        # Messages (comprehensive for analysis)
        self.messages: List[Dict[str, Any]] = []

        # Per-round tracking
        self.round_data: Dict[int, Dict[str, Any]] = {}

        # Constraint tracking
        self.constraints_extracted: List[Dict] = []

        # Agent performance tracking (for coordination analysis)
        self.agent_performance: Dict[str, Dict[str, Any]] = {}

    def record_guess(self, round_num: int, guess: List[str], feedback: Dict[str, int]):
        """Record a single guess and feedback."""
        self.guesses += 1
        self.rounds = round_num

        if round_num not in self.round_data:
            self.round_data[round_num] = {}

        self.round_data[round_num].update({
            "guess": guess,
            "feedback": feedback,
            "correct_pegs": feedback.get("correct_pegs", 0),
            "correct_positions": feedback.get("correct_positions", 0)
        })

    def record_response(self, round_num: int, response_chars: int, model: str = "gpt-4-turbo"):
        """Record LLM response metrics."""
        if round_num not in self.round_data:
            self.round_data[round_num] = {}

        self.round_data[round_num]["response_chars"] = response_chars
        self.round_data[round_num]["model"] = model

    def record_tokens(self, round_num: int, input_tokens: int, output_tokens: int):
        """Record token usage for a round."""
        self.token_usage["total_input"] += input_tokens
        self.token_usage["total_output"] += output_tokens

        self.token_usage["per_round"].append({
            "round": round_num,
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens
        })

    def record_message(self, round_num: int, sender: str, receiver: str,
                      message_type: str, content: Dict[str, Any]):
        """Record an A2A message."""
        self.messages.append({
            "timestamp": datetime.now().isoformat(),
            "round": round_num,
            "sender": sender,
            "receiver": receiver,
            "message_type": message_type,
            "content": content
        })

    def record_constraints(self, round_num: int, analysis: Dict[str, Any]):
        """Record extracted constraints."""
        self.constraints_extracted.append({
            "round": round_num,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        })

    def record_agent_performance(self, agent_type: str, round_num: int,
                                response_quality: Dict[str, Any]):
        """Record per-agent performance metrics for coordination analysis."""
        if agent_type not in self.agent_performance:
            self.agent_performance[agent_type] = {"rounds": {}}

        self.agent_performance[agent_type]["rounds"][round_num] = response_quality

    def mark_solved(self, reason: str = "solution_found"):
        """Mark the puzzle as solved."""
        self.success = True
        self.termination_reason = reason
        self.timestamp_end = datetime.now().isoformat()

    def mark_failed(self, reason: str = "max_rounds_reached"):
        """Mark the puzzle as failed."""
        self.success = False
        self.termination_reason = reason
        self.timestamp_end = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            # Session metadata
            "puzzle_id": self.puzzle_id,
            "paradigm": self.paradigm,
            "difficulty": self.difficulty,
            "provider": self.provider,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,

            # Puzzle metadata (for verification and analysis)
            "puzzle_metadata": {
                "secret_code": self.secret_code,
                "available_colors": self.available_colors,
                "pegs": 4  # Standard Mastermind
            },

            # Results
            "result": {
                "success": self.success,
                "guesses": self.guesses,
                "rounds": self.rounds,
                "termination_reason": self.termination_reason
            },

            # Communication & resources
            "token_usage": self.token_usage,

            # Messages (for LLM-Judge evaluation of coordination quality)
            "messages": self.messages,

            # Per-round details
            "round_data": self.round_data,

            # Constraints analysis
            "constraints_extracted": self.constraints_extracted,

            # Agent performance (for role adherence and coordination)
            "agent_performance": self.agent_performance
        }

    def save(self, output_dir: str = "output/sessions") -> str:
        """Save metrics to JSON file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"{self.puzzle_id}_{self.paradigm}.json"
        filepath = output_path / filename

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return str(filepath)


class MetricsAggregator:
    """Aggregates metrics across multiple sessions."""

    def __init__(self):
        self.sessions: List[Dict[str, Any]] = []

    def add_session(self, session_data: Dict[str, Any]):
        """Add a completed session."""
        self.sessions.append(session_data)

    def compute_success_rate(self) -> float:
        """Compute percentage of puzzles solved."""
        if not self.sessions:
            return 0.0
        solved = sum(1 for s in self.sessions if s["result"]["success"])
        return (solved / len(self.sessions)) * 100

    def compute_avg_guesses(self) -> Dict[str, float]:
        """Compute average guesses for solved puzzles."""
        solved = [s for s in self.sessions if s["result"]["success"]]
        if not solved:
            return {"avg": None, "min": None, "max": None, "count": 0}

        guesses = [s["result"]["guesses"] for s in solved]
        return {
            "avg": sum(guesses) / len(guesses),
            "min": min(guesses),
            "max": max(guesses),
            "count": len(guesses)
        }

    def compute_avg_tokens(self) -> Dict[str, float]:
        """Compute average token usage."""
        if not self.sessions:
            return {"total": 0, "input": 0, "output": 0, "per_guess": 0}

        total_input = sum(s["token_usage"]["total_input"] for s in self.sessions)
        total_output = sum(s["token_usage"]["total_output"] for s in self.sessions)
        total_guesses = sum(s["result"]["guesses"] for s in self.sessions)

        return {
            "total": total_input + total_output,
            "input": total_input,
            "output": total_output,
            "per_guess": (total_input + total_output) / total_guesses if total_guesses > 0 else 0,
            "session_count": len(self.sessions)
        }

    def compute_avg_messages(self) -> float:
        """Compute average number of messages."""
        if not self.sessions:
            return 0.0
        total_messages = sum(len(s["messages"]) for s in self.sessions)
        return total_messages / len(self.sessions)

    def compute_by_difficulty(self) -> Dict[str, Dict[str, Any]]:
        """Compute metrics separated by difficulty level."""
        results = {}
        for difficulty in ["easy", "medium", "hard"]:
            subset = [s for s in self.sessions if s["difficulty"] == difficulty]

            if not subset:
                results[difficulty] = {"sample_size": 0}
                continue

            agg = MetricsAggregator()
            agg.sessions = subset

            results[difficulty] = {
                "success_rate": agg.compute_success_rate(),
                "avg_guesses": agg.compute_avg_guesses(),
                "avg_tokens": agg.compute_avg_tokens(),
                "sample_size": len(subset)
            }

        return results

    def summary(self) -> Dict[str, Any]:
        """Generate complete summary."""
        return {
            "sample_size": len(self.sessions),
            "success_rate": self.compute_success_rate(),
            "avg_guesses": self.compute_avg_guesses(),
            "avg_tokens": self.compute_avg_tokens(),
            "avg_messages": self.compute_avg_messages(),
            "by_difficulty": self.compute_by_difficulty()
        }

    def save_summary(self, paradigm: str, output_dir: str = "output/metrics") -> str:
        """Save aggregated metrics."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"{paradigm}_summary.json"
        filepath = output_path / filename

        with open(filepath, "w") as f:
            json.dump(self.summary(), f, indent=2)

        return str(filepath)


def print_metrics_table(aggregators: Dict[str, MetricsAggregator]):
    """Print comparison table across paradigms."""
    print("\n" + "="*100)
    print("PARADIGM COMPARISON - METRICS SUMMARY")
    print("="*100)

    print(f"\n{'Paradigm':<20} {'Success %':<12} {'Avg Guesses':<12} {'Tokens/Guess':<15} {'Messages':<10} {'Samples':<8}")
    print("-"*100)

    for paradigm, agg in aggregators.items():
        summary = agg.summary()
        success = summary["success_rate"]
        guesses = summary["avg_guesses"]
        tokens = summary["avg_tokens"]
        messages = summary["avg_messages"]
        samples = summary["sample_size"]

        avg_g = guesses.get("avg") or 0
        tokens_per_guess = tokens.get("per_guess") or 0

        print(f"{paradigm:<20} {success:>10.1f}% {avg_g:>11.1f} {tokens_per_guess:>14.0f} {messages:>9.1f} {samples:>7}")

    print("="*100 + "\n")
