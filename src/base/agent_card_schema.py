"""
Agent Card Schema — Standard OpenAPI-compatible agent metadata.

Every agent publishes a card describing:
  - Basic metadata (id, name, type, paradigm)
  - Capabilities (actions it can perform)
  - Constraints (what it enforces)
  - Network location (URL)

Based on OpenAPI 3.0 + A2A extensions
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class A2ACapability:
    """Describes one capability (action) an agent can perform."""

    name: str  # "analyze", "propose", "validate"
    description: str
    input_schema: Dict[str, Any]  # JSON Schema for input payload
    output_schema: Dict[str, Any]  # JSON Schema for output payload
    timeout_seconds: int = 30  # Max time to wait for response

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class A2AAgentCard:
    """
    Standard A2A agent card — published by every agent at startup.

    Agents POST this card to the registry so other agents can discover them
    and understand their capabilities.
    """

    # ── Identity ──────────────────────────────────────────────────────────
    agent_id: str  # Unique ID (e.g., "analyzer_boss_worker")
    agent_name: str  # Human name (e.g., "Analyzer")
    agent_type: str  # Role type (e.g., "analyzer", "logger", "metrics")
    paradigm: str  # Paradigm name (e.g., "boss_worker")
    version: str = "1.0.0"  # Agent implementation version

    # ── Description ───────────────────────────────────────────────────────
    description: str = ""
    icon_url: Optional[str] = None

    # ── Network ───────────────────────────────────────────────────────────
    url: str = ""  # HTTP base URL (e.g., "http://localhost:8101")
    health_endpoint: str = "/health"  # Where to check if agent is alive

    # ── Capabilities ──────────────────────────────────────────────────────
    capabilities: List[A2ACapability] = None

    # ── Constraints & Role ────────────────────────────────────────────────
    constraints_owned: List[str] = None  # What this agent is responsible for
    team_members: List[str] = None  # Agent IDs on the same team
    can_communicate: bool = True  # Can this agent send A2A messages?

    # ── Metadata ──────────────────────────────────────────────────────────
    registered_at: Optional[float] = None  # Unix timestamp of registration
    last_heartbeat: Optional[float] = None  # Last time agent checked in

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.constraints_owned is None:
            self.constraints_owned = []
        if self.team_members is None:
            self.team_members = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert card to dict (for JSON serialization)."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "paradigm": self.paradigm,
            "version": self.version,
            "description": self.description,
            "icon_url": self.icon_url,
            "url": self.url,
            "health_endpoint": self.health_endpoint,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "constraints_owned": self.constraints_owned,
            "team_members": self.team_members,
            "can_communicate": self.can_communicate,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AAgentCard":
        """Deserialize from dict."""
        caps = []
        for cap_data in data.get("capabilities", []):
            caps.append(A2ACapability(
                name=cap_data["name"],
                description=cap_data["description"],
                input_schema=cap_data["input_schema"],
                output_schema=cap_data["output_schema"],
                timeout_seconds=cap_data.get("timeout_seconds", 30),
            ))
        data["capabilities"] = caps
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def validate(self) -> List[str]:
        """Validate the card. Returns list of errors (empty if valid)."""
        errors = []
        if not self.agent_id:
            errors.append("agent_id is required")
        if not self.agent_name:
            errors.append("agent_name is required")
        if not self.agent_type:
            errors.append("agent_type is required")
        if not self.paradigm:
            errors.append("paradigm is required")
        if not self.url:
            errors.append("url is required")
        if not self.capabilities:
            errors.append("capabilities list must not be empty")
        return errors
