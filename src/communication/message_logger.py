"""
Message Logger — Comprehensive logging of all A2A messages and agent conversations.

Logs all inter-agent communication to JSON file for analysis and debugging.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class LogEntry:
    """Single log entry for a message or event."""
    timestamp: float
    datetime_str: str
    event_type: str  # "a2a_send", "a2a_receive", "conversation", "routing", "error"
    agent_name: str
    message_id: Optional[str] = None
    sender_id: Optional[str] = None
    receiver_id: Optional[str] = None
    action: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None  # Full A2A payload
    conversation_turn: Optional[int] = None  # Which turn in conversation
    role: Optional[str] = None  # "user" or "assistant"
    content: Optional[str] = None  # Conversation content
    routing_decision: Optional[str] = None  # Where agent decided to send
    status: str = "ok"
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


class MessageLogger:
    """Log all A2A messages and agent conversations to structured JSON."""

    def __init__(self, log_file: str = "puzzle_run.log"):
        """Initialize logger with output file.

        Args:
            log_file: Path to JSON log file
        """
        self.log_file = Path(log_file)
        self.entries: List[LogEntry] = []
        self.start_time = time.time()

        # Create parent directories if needed
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_a2a_send(
        self,
        agent_name: str,
        message_id: str,
        sender_id: str,
        receiver_id: str,
        action: str,
        payload: Dict[str, Any],
        routing_decision: Optional[str] = None,
    ):
        """Log an outgoing A2A message."""
        entry = LogEntry(
            timestamp=time.time(),
            datetime_str=datetime.now().isoformat(),
            event_type="a2a_send",
            agent_name=agent_name,
            message_id=message_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            action=action,
            payload=payload,
            routing_decision=routing_decision,
        )
        self._add_entry(entry)

    def log_a2a_receive(
        self,
        agent_name: str,
        message_id: str,
        sender_id: str,
        receiver_id: str,
        action: str,
        payload: Dict[str, Any],
        status: str = "ok",
    ):
        """Log an incoming A2A message."""
        entry = LogEntry(
            timestamp=time.time(),
            datetime_str=datetime.now().isoformat(),
            event_type="a2a_receive",
            agent_name=agent_name,
            message_id=message_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            action=action,
            payload=payload,
            status=status,
        )
        self._add_entry(entry)

    def log_conversation(
        self,
        agent_name: str,
        turn: int,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log a conversation turn (LLM request/response)."""
        entry = LogEntry(
            timestamp=time.time(),
            datetime_str=datetime.now().isoformat(),
            event_type="conversation",
            agent_name=agent_name,
            conversation_turn=turn,
            role=role,
            content=content,
            metadata=metadata,
        )
        self._add_entry(entry)

    def log_routing_decision(
        self,
        agent_name: str,
        decision: str,
        next_peer: str,
        action: str,
        reasoning: Optional[str] = None,
    ):
        """Log an agent's routing decision."""
        entry = LogEntry(
            timestamp=time.time(),
            datetime_str=datetime.now().isoformat(),
            event_type="routing",
            agent_name=agent_name,
            routing_decision=f"{decision} → {next_peer}/{action}",
            metadata={"next_peer": next_peer, "action": action, "reasoning": reasoning},
        )
        self._add_entry(entry)

    def log_error(
        self,
        agent_name: str,
        error: str,
        event_type: str = "error",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log an error event."""
        entry = LogEntry(
            timestamp=time.time(),
            datetime_str=datetime.now().isoformat(),
            event_type=event_type,
            agent_name=agent_name,
            status="error",
            error=error,
            metadata=metadata,
        )
        self._add_entry(entry)

    def _add_entry(self, entry: LogEntry):
        """Add entry to log and write to file."""
        self.entries.append(entry)
        # Write immediately for real-time monitoring
        self._write_to_file()

    def _write_to_file(self):
        """Write all entries to JSON log file."""
        try:
            with open(self.log_file, "w") as f:
                entries = [e.to_dict() for e in self.entries]
                json.dump(
                    {
                        "puzzle_run_log": {
                            "start_time": self.start_time,
                            "start_datetime": datetime.fromtimestamp(
                                self.start_time
                            ).isoformat(),
                            "total_entries": len(entries),
                            "entries": entries,
                        }
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            print(f"[MessageLogger] Error writing log: {e}")

    def summary(self) -> Dict[str, Any]:
        """Return summary of logged messages."""
        by_type = {}
        by_agent = {}

        for entry in self.entries:
            # Count by event type
            et = entry.event_type
            by_type[et] = by_type.get(et, 0) + 1

            # Count by agent
            an = entry.agent_name
            by_agent[an] = by_agent.get(an, 0) + 1

        return {
            "total_entries": len(self.entries),
            "by_event_type": by_type,
            "by_agent": by_agent,
            "duration_seconds": time.time() - self.start_time,
            "log_file": str(self.log_file),
        }

    def print_summary(self):
        """Print summary to stdout."""
        summary = self.summary()
        print("\n" + "=" * 70)
        print("MESSAGE LOG SUMMARY")
        print("=" * 70)
        print(f"Log file: {summary['log_file']}")
        print(f"Total entries: {summary['total_entries']}")
        print(f"Duration: {summary['duration_seconds']:.1f}s\n")

        print("By Event Type:")
        for event_type, count in summary["by_event_type"].items():
            print(f"  {event_type}: {count}")

        print("\nBy Agent:")
        for agent, count in summary["by_agent"].items():
            print(f"  {agent}: {count}")

        print("=" * 70 + "\n")


# Global logger instance
_logger: Optional[MessageLogger] = None


def get_message_logger(log_file: str = "puzzle_run.log") -> MessageLogger:
    """Get or create global message logger."""
    global _logger
    if _logger is None:
        _logger = MessageLogger(log_file)
    return _logger


def init_message_logger(log_file: str = "puzzle_run.log"):
    """Initialize message logger with custom log file."""
    global _logger
    _logger = MessageLogger(log_file)
    return _logger
