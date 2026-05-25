# Communication Logger
# Logs all inter-agent messages to JSON Lines format
# Each message records sender, receiver, type, content, timestamp, round, puzzle_id
# Used for analyzing communication patterns and efficiency across paradigms

import json
import time
from pathlib import Path
from typing import Any, Dict, List


class CommunicationLogger:
    """Logs all inter-agent messages for analysis and debugging."""

    def __init__(self, puzzle_id: str, paradigm: str, output_dir: str = "output/sessions"):
        """Initialize logger for a specific puzzle-paradigm combination.

        Args:
            puzzle_id: Puzzle identifier (e.g., "MM_001")
            paradigm: Paradigm name (e.g., "boss-worker", "round-table")
            output_dir: Directory to save session logs
        """
        self.puzzle_id = puzzle_id
        self.paradigm = paradigm
        self.messages = []
        self.log_file = Path(output_dir) / f"{puzzle_id}_{paradigm}.jsonl"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_message(self, message: Dict[str, Any]) -> None:
        """Log a single inter-agent message.

        Args:
            message: Message dictionary with sender, receiver, type, content, etc.
        """
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = time.time()

        self.messages.append(message)

        # Write immediately for robustness (survives crashes)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(message) + "\n")

    def get_all_messages(self) -> List[Dict[str, Any]]:
        """Get all logged messages."""
        return self.messages

    def get_messages_by_type(self, msg_type: str) -> List[Dict[str, Any]]:
        """Get messages of specific type.

        Args:
            msg_type: Message type to filter (e.g., "strategy", "analysis")

        Returns:
            List of messages matching the type
        """
        return [m for m in self.messages if m.get("message_type") == msg_type]

    def get_messages_by_round(self, round_num: int) -> List[Dict[str, Any]]:
        """Get messages from a specific round.

        Args:
            round_num: Round number to filter

        Returns:
            List of messages from that round
        """
        return [m for m in self.messages if m.get("round_number") == round_num]

    def summary(self) -> Dict[str, Any]:
        """Generate summary statistics of logged messages."""
        message_types = {}
        for msg in self.messages:
            msg_type = msg.get("message_type", "unknown")
            message_types[msg_type] = message_types.get(msg_type, 0) + 1

        return {
            "total_messages": len(self.messages),
            "message_types": message_types,
            "puzzle_id": self.puzzle_id,
            "paradigm": self.paradigm,
            "log_file": str(self.log_file)
        }
