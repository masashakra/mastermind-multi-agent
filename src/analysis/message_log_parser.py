"""
Parser for extracting A2A messages from puzzle run logs.
Organizes messages by agent and action for analysis.
"""

import json
import re
from typing import Dict, List
from pathlib import Path
from dataclasses import dataclass


@dataclass
class A2AMessage:
    """Structured representation of an A2A message."""

    message_id: str
    timestamp: str
    sender_id: str
    receiver_id: str
    action: str
    payload: Dict
    status: str
    response_to: str = None
    is_reply: bool = False

    def __repr__(self) -> str:
        return (
            f"A2AMessage(sender={self.sender_id}, action={self.action}, "
            f"status={self.status}, is_reply={self.is_reply})"
        )


class MessageLogParser:
    """Parser for extracting messages from puzzle run logs."""

    def __init__(self, log_file: str):
        """Initialize parser with log file path."""
        self.log_file = Path(log_file)
        self.messages: List[A2AMessage] = []
        self.messages_by_agent: Dict[str, List[str]] = {}  # Maps agent names to message contents
        self.raw_log_entries: List[Dict] = []

    def parse(self) -> List[A2AMessage]:
        """Parse log file and extract messages."""
        if not self.log_file.exists():
            raise FileNotFoundError(f"Log file not found: {self.log_file}")

        with open(self.log_file, "r") as f:
            log_content = f.read()

        # Try to parse as JSON-formatted log
        try:
            log_data = json.loads(log_content)
            self._parse_json_log(log_data)
        except json.JSONDecodeError:
            # Try parsing as line-delimited or other format
            self._parse_text_log(log_content)

        # Organize by agent
        self._organize_by_agent()

        return self.messages

    def _parse_json_log(self, log_data: Dict):
        """Parse JSON-formatted log file (from puzzle_run_log format)."""
        # Check if it's the puzzle_run_log format
        if "puzzle_run_log" in log_data:
            entries = log_data["puzzle_run_log"].get("entries", [])
        elif isinstance(log_data, list):
            entries = log_data
        else:
            entries = []

        self.raw_log_entries = entries

        # Extract conversation entries
        for entry in entries:
            if entry.get("event_type") == "conversation":
                agent_name = entry.get("agent_name", "unknown")
                content = entry.get("content", "")
                role = entry.get("role", "assistant")

                # Only capture assistant responses (the actual agent outputs)
                if role == "assistant" and content:
                    # Create a synthetic A2A message
                    msg = A2AMessage(
                        message_id=f"{agent_name}_{entry.get('timestamp', 0)}",
                        timestamp=entry.get("datetime_str", ""),
                        sender_id=agent_name.lower().replace("_bossworker", "_bw"),
                        receiver_id="boss",
                        action="response",
                        payload={"content": content},
                        status="OK",
                        is_reply=True,
                    )
                    self.messages.append(msg)

    def _parse_text_log(self, log_content: str):
        """Parse text-formatted log file (fallback)."""
        # Try to find A2A-style messages
        message_pattern = r'\{[^{}]*"message_id"[^{}]*"sender_id"[^{}]*\}'
        matches = re.finditer(message_pattern, log_content, re.DOTALL)

        for match in matches:
            try:
                msg_dict = json.loads(match.group())

                # Verify it's an A2A message
                if self._is_valid_a2a_message(msg_dict):
                    msg = self._dict_to_message(msg_dict)
                    self.messages.append(msg)
            except (json.JSONDecodeError, KeyError):
                pass

    def _is_valid_a2a_message(self, msg_dict: Dict) -> bool:
        """Check if a dict is a valid A2A message."""
        required_fields = ["message_id", "sender_id", "receiver_id", "action"]
        return all(field in msg_dict for field in required_fields)

    def _dict_to_message(self, msg_dict: Dict) -> A2AMessage:
        """Convert dict to A2AMessage."""
        return A2AMessage(
            message_id=msg_dict.get("message_id", ""),
            timestamp=msg_dict.get("timestamp", ""),
            sender_id=msg_dict.get("sender_id", ""),
            receiver_id=msg_dict.get("receiver_id", ""),
            action=msg_dict.get("action", ""),
            payload=msg_dict.get("payload", {}),
            status=msg_dict.get("status", ""),
            response_to=msg_dict.get("response_to"),
            is_reply=msg_dict.get("is_reply", False),
        )

    def _organize_by_agent(self):
        """Organize messages by sender agent."""
        self.messages_by_agent = {}

        for msg in self.messages:
            # Extract agent name from sender_id (e.g., "analyzer_bw" -> "analyzer")
            agent_name = msg.sender_id.split("_")[0].lower()

            if agent_name not in self.messages_by_agent:
                self.messages_by_agent[agent_name] = []

            # Store message content for role adherence analysis
            content = msg.payload.get("content", "")
            if content:
                self.messages_by_agent[agent_name].append(content)

    def get_messages_by_agent(self) -> Dict[str, List[str]]:
        """Get all messages organized by agent (as string contents)."""
        return self.messages_by_agent.copy()

    def get_agent_messages(self, agent_name: str) -> List[str]:
        """Get all messages from a specific agent (as string contents)."""
        agent_key = agent_name.lower().strip()
        return self.messages_by_agent.get(agent_key, [])

    def get_messages_for_action(self, action: str) -> List[A2AMessage]:
        """Get all messages for a specific action."""
        return [msg for msg in self.messages if msg.action == action]

    def get_agent_action_messages(
        self, agent_name: str, action: str
    ) -> List[A2AMessage]:
        """Get messages from a specific agent for a specific action."""
        agent_messages = self.get_agent_messages(agent_name)
        return [msg for msg in agent_messages if msg.action == action]

    def print_summary(self):
        """Print summary of parsed messages."""
        print("\n" + "=" * 70)
        print("MESSAGE LOG SUMMARY")
        print("=" * 70)
        print(f"Total messages parsed: {len(self.messages)}")
        print(f"\nMessages by agent:")

        for agent_name in sorted(self.messages_by_agent.keys()):
            messages = self.messages_by_agent[agent_name]
            print(f"  {agent_name.upper()}: {len(messages)} messages")

        print("=" * 70)


def extract_message_text_for_analysis(msg: A2AMessage) -> str:
    """
    Extract readable message text from an A2A message for role adherence analysis.

    This converts the structured A2A message into natural language for the LLM judge.
    """
    parts = []

    # Message metadata
    parts.append(f"[{msg.action}]")

    # Add sender and receiver info
    parts.append(f"From: {msg.sender_id} To: {msg.receiver_id}")

    # Add status if not OK
    if msg.status != "OK":
        parts.append(f"Status: {msg.status}")

    # Add payload content (the actual message content)
    if msg.payload:
        parts.append("\nContent:")

        # Different actions have different payload structures
        if msg.action == "analyze":
            if "guess" in msg.payload:
                parts.append(f"  Analyzing guess: {msg.payload.get('guess')}")
            if "feedback" in msg.payload:
                parts.append(f"  With feedback: {msg.payload.get('feedback')}")
            if "constraints" in msg.payload:
                parts.append(f"  Constraints identified: {msg.payload.get('constraints')}")

        elif msg.action == "propose_strategy":
            if "constraints" in msg.payload:
                parts.append(f"  Constraints received: {msg.payload.get('constraints')}")
            if "strategy" in msg.payload:
                parts.append(f"  Strategy: {msg.payload.get('strategy')}")

        elif msg.action == "propose_guess":
            if "strategy" in msg.payload:
                parts.append(f"  Based on strategy: {msg.payload.get('strategy')}")
            if "proposed_guess" in msg.payload:
                parts.append(f"  Proposed guess: {msg.payload.get('proposed_guess')}")

        elif msg.action == "validate_guess":
            if "guess" in msg.payload:
                parts.append(f"  Validating guess: {msg.payload.get('guess')}")
            if "is_valid" in msg.payload:
                parts.append(f"  Valid: {msg.payload.get('is_valid')}")

        elif msg.action in ["discover_agents", "submit_guess", "check_result"]:
            # Boss actions
            parts.append(f"  Payload: {json.dumps(msg.payload, indent=2)}")

        else:
            # Generic payload display
            parts.append(f"  {json.dumps(msg.payload, indent=2)}")

    return "\n".join(parts)
