# Agent Card - Metadata and Schema for A2A Agents
# Defines agent capabilities, interfaces, and contract

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class AgentType(Enum):
    """Standard agent type classifications."""
    STRATEGIST = "strategist"
    ANALYZER = "analyzer"
    PROPOSER = "proposer"
    VALIDATOR = "validator"
    ORCHESTRATOR = "orchestrator"
    WORKER = "worker"


@dataclass
class IOSchema:
    """Input/Output schema for agent actions."""
    action_name: str
    input_schema: Dict[str, Any]  # JSON schema
    output_schema: Dict[str, Any]  # JSON schema
    description: str


@dataclass
class AgentCapability:
    """Represents a capability an agent can perform."""
    action: str  # e.g., "propose_strategy", "analyze_feedback"
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    dependencies: List[str] = None  # Other agents this depends on

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class AgentCard:
    """
    A2A Agent Card - Standardized metadata about an agent.

    Serves as the agent's "business card" in the system.
    Contains all information needed to discover, communicate with, and use the agent.
    """

    # Identity
    agent_id: str  # Unique identifier (e.g., "strategist", "analyzer")
    agent_name: str  # Human-readable name
    agent_type: str  # Type classification
    version: str = "1.0.0"

    # Description
    description: str = ""
    purpose: str = ""
    author: str = ""

    # Capabilities
    capabilities: List[AgentCapability] = None

    # Configuration
    llm_provider: str = "groq"  # LLM provider used
    llm_model: str = "llama-3.1-8b-instant"
    timeout_seconds: int = 30

    # Network/Discovery
    endpoint: str = ""  # Where to reach this agent (HTTP/gRPC/local)
    discovery_tags: List[str] = None  # Tags for discovery (#strategist, #mastermind, etc.)

    # Metadata
    metadata: Dict[str, Any] = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.discovery_tags is None:
            self.discovery_tags = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert card to dictionary."""
        data = asdict(self)
        # Convert enums to strings
        data['agent_type'] = self.agent_type
        # Convert capability objects
        data['capabilities'] = [asdict(c) for c in self.capabilities]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentCard':
        """Create card from dictionary."""
        # Convert capability dicts back to objects
        capabilities = []
        if 'capabilities' in data:
            for cap in data.pop('capabilities', []):
                capabilities.append(AgentCapability(**cap))

        return cls(capabilities=capabilities, **data)

    def has_capability(self, action: str) -> bool:
        """Check if agent has a specific capability."""
        return any(c.action == action for c in self.capabilities)

    def get_capability(self, action: str) -> Optional[AgentCapability]:
        """Get a specific capability by action name."""
        for c in self.capabilities:
            if c.action == action:
                return c
        return None

    def get_input_schema(self, action: str) -> Optional[Dict[str, Any]]:
        """Get input schema for an action."""
        cap = self.get_capability(action)
        return cap.input_schema if cap else None

    def get_output_schema(self, action: str) -> Optional[Dict[str, Any]]:
        """Get output schema for an action."""
        cap = self.get_capability(action)
        return cap.output_schema if cap else None


# Predefined Agent Cards for Mastermind Agents

STRATEGIST_CARD = AgentCard(
    agent_id="strategist",
    agent_name="Strategist",
    agent_type=AgentType.STRATEGIST.value,
    description="Proposes high-level guessing strategy based on feedback patterns",
    purpose="Analyze past guesses and recommend strategic approach for next guess",
    capabilities=[
        AgentCapability(
            action="propose_strategy",
            description="Propose strategy based on guess history",
            input_schema={
                "type": "object",
                "properties": {
                    "guess_history": {
                        "type": "array",
                        "description": "Previous guesses with feedback"
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard"]
                    }
                },
                "required": ["guess_history", "difficulty"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "strategy": {"type": "string"},
                    "analysis": {"type": "string"},
                    "confidence": {"type": "number"}
                }
            }
        )
    ],
    discovery_tags=["mastermind", "strategist", "planning"]
)

ANALYZER_CARD = AgentCard(
    agent_id="analyzer",
    agent_name="Analyzer",
    agent_type=AgentType.ANALYZER.value,
    description="Interprets feedback and extracts constraints",
    purpose="Extract locked positions, misplaced colors, and impossible colors from feedback",
    capabilities=[
        AgentCapability(
            action="analyze_feedback",
            description="Analyze feedback and extract constraints",
            input_schema={
                "type": "object",
                "properties": {
                    "last_guess": {"type": "array"},
                    "feedback": {"type": "object"},
                    "previous_guesses": {"type": "array"}
                },
                "required": ["last_guess", "feedback"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "correct_positions": {"type": "array"},
                    "correct_colors_wrong_position": {"type": "array"},
                    "impossible_colors": {"type": "array"},
                    "constraints": {"type": "array"}
                }
            }
        )
    ],
    discovery_tags=["mastermind", "analyzer", "constraints"]
)

PROPOSER_CARD = AgentCard(
    agent_id="proposer",
    agent_name="Proposer",
    agent_type=AgentType.PROPOSER.value,
    description="Generates next guess based on strategy and constraints",
    purpose="Propose concrete guess respecting all constraints and strategy",
    capabilities=[
        AgentCapability(
            action="propose_guess",
            description="Propose next guess",
            input_schema={
                "type": "object",
                "properties": {
                    "strategy": {"type": "string"},
                    "constraints_text": {"type": "string"},
                    "available_colors": {"type": "array"},
                    "num_pegs": {"type": "integer"}
                },
                "required": ["strategy", "available_colors", "num_pegs"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "proposed_guess": {"type": "array"},
                    "justification": {"type": "string"}
                }
            }
        )
    ],
    discovery_tags=["mastermind", "proposer", "guessing"]
)

VALIDATOR_CARD = AgentCard(
    agent_id="validator",
    agent_name="Validator",
    agent_type=AgentType.VALIDATOR.value,
    description="Validates guess against constraints before submission",
    purpose="Ensure proposed guess respects all constraints and is valid",
    capabilities=[
        AgentCapability(
            action="validate_guess",
            description="Validate a proposed guess",
            input_schema={
                "type": "object",
                "properties": {
                    "guess": {"type": "array"},
                    "available_colors": {"type": "array"},
                    "expected_length": {"type": "integer"},
                    "constraints": {"type": "object"}
                },
                "required": ["guess", "available_colors", "expected_length"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "is_valid": {"type": "boolean"},
                    "errors": {"type": "array"},
                    "warnings": {"type": "array"}
                }
            }
        )
    ],
    discovery_tags=["mastermind", "validator", "validation"]
)
