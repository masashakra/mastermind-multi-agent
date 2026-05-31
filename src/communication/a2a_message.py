"""
A2A Message Envelope — Standard communication protocol for agent-to-agent messaging.

All inter-agent HTTP communication (Boss ↔ Workers, anything ↔ Logger/Metrics)
uses this standardized envelope format with metadata, timestamps, and error codes.

Based on: W3C Activity Streams 2.0 + custom A2A extensions
"""

import uuid
import time
import json
from typing import Any, Dict, Optional
from enum import Enum
from dataclasses import dataclass, asdict


class A2AStatus(str, Enum):
    """Standard A2A message status codes."""
    OK        = "ok"
    ERROR     = "error"
    TIMEOUT   = "timeout"
    INVALID   = "invalid"
    NOT_FOUND = "not_found"


class A2AErrorCode(str, Enum):
    """Standard A2A error codes."""
    # 4xx-like errors
    INVALID_PAYLOAD    = "invalid_payload"
    MISSING_FIELD      = "missing_field"
    AGENT_NOT_FOUND    = "agent_not_found"
    CAPABILITY_NOT_SUPPORTED = "capability_not_supported"
    CONSTRAINT_VIOLATION = "constraint_violation"

    # 5xx-like errors
    INTERNAL_ERROR     = "internal_error"
    LLM_ERROR          = "llm_error"
    TIMEOUT            = "timeout"
    SERVICE_UNAVAILABLE = "service_unavailable"


@dataclass
class A2AMessage:
    """
    Standard A2A message envelope.

    All agent-to-agent HTTP communication uses this format.

    Fields:
      - message_id: Unique UUID for this message
      - timestamp: Unix timestamp when message was created
      - sender_id: Agent sending the message (e.g., "boss_boss_worker")
      - receiver_id: Agent receiving the message (e.g., "analyzer_boss_worker")
      - action: What the receiver should do (e.g., "analyze", "propose")
      - payload: The actual data (agent-specific)
      - status: ok | error | timeout | invalid | not_found
      - error_code: If status=error, which error type (e.g., INVALID_PAYLOAD)
      - error_message: Human-readable error description
      - response_to: If this is a response, the message_id of the request
    """

    message_id: str
    timestamp: float
    sender_id: str
    receiver_id: str
    action: str
    payload: Dict[str, Any]
    status: A2AStatus = A2AStatus.OK
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    response_to: Optional[str] = None

    @classmethod
    def request(
        cls,
        sender_id: str,
        receiver_id: str,
        action: str,
        payload: Dict[str, Any],
    ) -> "A2AMessage":
        """Create a new A2A request message."""
        return cls(
            message_id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender_id=sender_id,
            receiver_id=receiver_id,
            action=action,
            payload=payload,
            status=A2AStatus.OK,
        )

    @classmethod
    def response(
        cls,
        request: "A2AMessage",
        payload: Dict[str, Any],
        status: A2AStatus = A2AStatus.OK,
    ) -> "A2AMessage":
        """Create a response to an A2A request."""
        return cls(
            message_id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender_id=request.receiver_id,
            receiver_id=request.sender_id,
            action=request.action,
            payload=payload,
            status=status,
            response_to=request.message_id,
        )

    @classmethod
    def error(
        cls,
        request: "A2AMessage",
        error_code: A2AErrorCode,
        error_message: str,
        status: A2AStatus = A2AStatus.ERROR,
    ) -> "A2AMessage":
        """Create an error response."""
        return cls(
            message_id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender_id=request.receiver_id,
            receiver_id=request.sender_id,
            action=request.action,
            payload={},
            status=status,
            error_code=error_code.value,
            error_message=error_message,
            response_to=request.message_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dict for JSON serialization."""
        data = asdict(self)
        data["status"] = self.status.value
        if self.error_code:
            data["error_code"] = self.error_code if isinstance(self.error_code, str) else self.error_code.value
        return data

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        """Deserialize from dict."""
        data["status"] = A2AStatus(data.get("status", "ok"))
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "A2AMessage":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __repr__(self) -> str:
        return (
            f"A2AMessage("
            f"action={self.action}, "
            f"sender={self.sender_id}, "
            f"receiver={self.receiver_id}, "
            f"status={self.status.value}"
            f")"
        )
