# A2A Protocol - Agent-to-Agent Communication Protocol
# Standardized message format and communication layer for agent interactions

import json
import time
import uuid
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, asdict


class MessageType(Enum):
    """Standard message types in A2A protocol."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class A2AMessage:
    """Standardized A2A protocol message format."""

    # Core fields
    message_id: str  # Unique message ID
    sender_id: str  # Agent sending the message
    receiver_id: str  # Agent receiving the message
    message_type: str  # request, response, notification, error
    action: str  # What action to perform (e.g., "analyze_feedback", "propose_guess")
    payload: Dict[str, Any]  # Message data

    # Metadata
    timestamp: float = None
    correlation_id: str = None  # Links request-response pairs
    status: str = "pending"  # pending, delivered, processed
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.correlation_id is None:
            self.correlation_id = self.message_id
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'A2AMessage':
        """Create message from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Convert message to JSON."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'A2AMessage':
        """Create message from JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class A2ACommunicationLayer:
    """
    Communication layer for agent-to-agent interactions.

    Implements:
    - Message routing between agents
    - Request-response correlation
    - Agent registry
    - Message history
    """

    def __init__(self):
        """Initialize communication layer."""
        self.agents: Dict[str, 'Agent'] = {}  # Agent registry
        self.message_history: List[A2AMessage] = []
        self.pending_requests: Dict[str, A2AMessage] = {}  # Correlation ID → Request
        self.message_handlers: Dict[str, Callable] = {}  # Agent ID → Handler function

    def register_agent(self, agent_id: str, agent: Any) -> None:
        """Register an agent in the communication layer.

        Args:
            agent_id: Unique agent identifier
            agent: Agent instance
        """
        self.agents[agent_id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]

    def register_handler(self, agent_id: str, handler: Callable) -> None:
        """Register a message handler for an agent.

        Args:
            agent_id: Agent to handle messages for
            handler: Async function(message) that processes the message
        """
        self.message_handlers[agent_id] = handler

    def send_request(
        self,
        sender_id: str,
        receiver_id: str,
        action: str,
        payload: Dict[str, Any]
    ) -> A2AMessage:
        """Send a request from one agent to another.

        Args:
            sender_id: Agent sending the request
            receiver_id: Target agent
            action: Action to perform
            payload: Request data

        Returns:
            Message object with generated message_id
        """
        message = A2AMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.REQUEST.value,
            action=action,
            payload=payload
        )

        self.message_history.append(message)
        self.pending_requests[message.correlation_id] = message

        return message

    def send_response(
        self,
        sender_id: str,
        receiver_id: str,
        correlation_id: str,
        payload: Dict[str, Any],
        status: str = "success"
    ) -> A2AMessage:
        """Send a response from one agent to another.

        Args:
            sender_id: Agent sending the response
            receiver_id: Target agent
            correlation_id: Links to original request
            payload: Response data
            status: success or error

        Returns:
            Message object
        """
        message = A2AMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.RESPONSE.value if status == "success" else MessageType.ERROR.value,
            action=self.pending_requests.get(correlation_id, {}).action if correlation_id in self.pending_requests else "unknown",
            payload=payload,
            correlation_id=correlation_id,
            status=status
        )

        self.message_history.append(message)

        # Clean up pending request
        if correlation_id in self.pending_requests:
            del self.pending_requests[correlation_id]

        return message

    def send_notification(
        self,
        sender_id: str,
        receiver_id: str,
        action: str,
        payload: Dict[str, Any]
    ) -> A2AMessage:
        """Send a notification from one agent to another (fire-and-forget).

        Args:
            sender_id: Agent sending the notification
            receiver_id: Target agent
            action: Action/event type
            payload: Notification data

        Returns:
            Message object
        """
        message = A2AMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.NOTIFICATION.value,
            action=action,
            payload=payload
        )

        self.message_history.append(message)
        return message

    def get_agent_messages(self, agent_id: str) -> List[A2AMessage]:
        """Get all messages involving an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of messages where agent is sender or receiver
        """
        return [
            msg for msg in self.message_history
            if msg.sender_id == agent_id or msg.receiver_id == agent_id
        ]

    def get_conversation(self, agent1: str, agent2: str) -> List[A2AMessage]:
        """Get all messages between two agents.

        Args:
            agent1: First agent
            agent2: Second agent

        Returns:
            Ordered list of messages between them
        """
        return [
            msg for msg in self.message_history
            if (msg.sender_id == agent1 and msg.receiver_id == agent2) or
               (msg.sender_id == agent2 and msg.receiver_id == agent1)
        ]

    def get_pending_requests(self) -> Dict[str, A2AMessage]:
        """Get all pending requests waiting for responses."""
        return self.pending_requests.copy()

    def clear_history(self) -> None:
        """Clear message history."""
        self.message_history.clear()
        self.pending_requests.clear()
