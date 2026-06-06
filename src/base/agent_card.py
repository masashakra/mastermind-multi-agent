# Agent Card Schema (OpenAPI-style)
# Defines agent metadata for discovery and orchestration
# Follows Google AI Agents specification (OpenAPI format)

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class Parameter:
    """OpenAPI parameter definition"""
    type: str
    description: str
    items: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


@dataclass
class Capability:
    """Agent capability definition (operation)"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    returns: Dict[str, Any]  # JSON Schema


@dataclass
class AgentCard:
    """Agent card metadata (OpenAPI spec style)

    Defines agent identity, capabilities, and constraints.
    Used for:
    - Agent discovery in registry
    - A2A communication validation
    - Documentation and introspection
    """

    # Identity
    agent_id: str
    agent_name: str
    agent_type: str  # "analyzer", "strategist", "proposer", "validator", "logger", "metrics"
    paradigm: str  # "boss_worker", "round_table", etc.
    version: str = "1.0"

    # Description & Metadata
    description: str = ""

    # Capabilities (OpenAPI operations)
    capabilities: Dict[str, Dict[str, Any]] = None

    # Role & Constraints
    role: str = ""
    constraints_owned: List[str] = None
    can_communicate: bool = True
    team_members: List[str] = None

    # Configuration
    provider: str = "deepseek"
    model: str = "mistral"
    timeout: int = 60

    # Discovery tags
    discovery_tags: List[str] = None

    def __post_init__(self):
        """Initialize defaults"""
        if self.capabilities is None:
            self.capabilities = {}
        if self.constraints_owned is None:
            self.constraints_owned = []
        if self.team_members is None:
            self.team_members = []
        if self.discovery_tags is None:
            self.discovery_tags = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (OpenAPI format)"""
        return asdict(self)

    def to_openapi(self) -> Dict[str, Any]:
        """Convert to OpenAPI specification format"""
        return {
            "openapi": "3.1.0",
            "info": {
                "title": self.agent_name,
                "description": self.description,
                "version": self.version
            },
            "servers": [
                {
                    "url": f"/{self.paradigm}/{self.agent_id}",
                    "description": f"{self.agent_name} in {self.paradigm} paradigm"
                }
            ],
            "paths": {
                **{
                    f"/{capability}": {
                        "post": {
                            "summary": spec.get("description", ""),
                            "operationId": capability,
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": spec.get("parameters", {})
                                    }
                                }
                            },
                            "responses": {
                                "200": {
                                    "description": "Success",
                                    "content": {
                                        "application/json": {
                                            "schema": spec.get("returns", {})
                                        }
                                    }
                                }
                            }
                        }
                    }
                    for capability, spec in self.capabilities.items()
                }
            },
            "components": {
                "schemas": {
                    "AgentMetadata": {
                        "type": "object",
                        "properties": {
                            "agent_id": {"type": "string"},
                            "agent_name": {"type": "string"},
                            "role": {"type": "string"},
                            "paradigm": {"type": "string"},
                            "constraints_owned": {"type": "array", "items": {"type": "string"}},
                            "team_members": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            },
            "x-agent-metadata": {
                "role": self.role,
                "constraints_owned": self.constraints_owned,
                "can_communicate": self.can_communicate,
                "team_members": self.team_members,
                "discovery_tags": self.discovery_tags
            }
        }


# Pre-defined agent cards for Mastermind agents

ANALYZER_CARD = {
    "agent_id": "analyzer",
    "agent_name": "Analyzer",
    "agent_type": "analyzer",
    "paradigm": "base",  # Overridden per paradigm
    "version": "1.0",
    "description": "Extracts constraints from feedback and identifies locked positions",
    "role": "analyzer",
    "constraints_owned": ["Constraint extraction", "Position analysis"],
    "can_communicate": True,
    "team_members": ["strategist", "proposer", "validator", "boss"],
    "discovery_tags": ["constraint", "analysis", "feedback"],
    "capabilities": {
        "analyze_feedback": {
            "description": "Analyze feedback and extract constraints",
            "parameters": {
                "type": "object",
                "properties": {
                    "guess": {"type": "array", "items": {"type": "integer"}},
                    "feedback": {
                        "type": "object",
                        "properties": {
                            "correct_positions": {"type": "integer"},
                            "correct_pegs": {"type": "integer"}
                        }
                    },
                    "history": {"type": "array"}
                }
            },
            "returns": {
                "type": "object",
                "properties": {
                    "correct_positions": {"type": "array"},
                    "correct_colors_wrong_position": {"type": "array"},
                    "impossible_colors": {"type": "array"},
                    "constraints": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    }
}

STRATEGIST_CARD = {
    "agent_id": "strategist",
    "agent_name": "Strategist",
    "agent_type": "strategist",
    "paradigm": "base",
    "version": "1.0",
    "description": "Proposes high-level strategy for the next guess",
    "role": "strategist",
    "constraints_owned": ["Strategy coherence", "Game phase identification"],
    "can_communicate": True,
    "team_members": ["analyzer", "proposer", "validator", "boss"],
    "discovery_tags": ["strategy", "planning", "phase"],
    "capabilities": {
        "propose_strategy": {
            "description": "Propose strategy for next guess",
            "parameters": {
                "type": "object",
                "properties": {
                    "guess_history": {"type": "array"},
                    "difficulty": {"type": "string"}
                }
            },
            "returns": {
                "type": "object",
                "properties": {
                    "phase": {"type": "string"},
                    "strategy": {"type": "string"},
                    "confidence": {"type": "number"}
                }
            }
        }
    }
}

PROPOSER_CARD = {
    "agent_id": "proposer",
    "agent_name": "Proposer",
    "agent_type": "proposer",
    "paradigm": "base",
    "version": "1.0",
    "description": "Generates guesses that respect all constraints",
    "role": "proposer",
    "constraints_owned": ["Constraint-respecting guess generation", "Position locking"],
    "can_communicate": True,
    "team_members": ["analyzer", "strategist", "validator", "boss"],
    "discovery_tags": ["generation", "proposal", "guess"],
    "capabilities": {
        "propose_guess": {
            "description": "Generate guess respecting constraints",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy": {"type": "string"},
                    "constraints": {"type": "string"},
                    "available_colors": {"type": "array"},
                    "num_pegs": {"type": "integer"},
                    "previous_guesses": {"type": "array"}
                }
            },
            "returns": {
                "type": "object",
                "properties": {
                    "proposed_guess": {"type": "array"},
                    "reasoning": {"type": "string"}
                }
            }
        }
    }
}

VALIDATOR_CARD = {
    "agent_id": "validator",
    "agent_name": "Validator",
    "agent_type": "validator",
    "paradigm": "base",
    "version": "1.0",
    "description": "Validates guesses against hard and soft constraints",
    "role": "validator",
    "constraints_owned": ["Hard constraint enforcement", "Soft constraint validation"],
    "can_communicate": True,
    "team_members": ["analyzer", "strategist", "proposer", "boss"],
    "discovery_tags": ["validation", "constraint", "quality"],
    "capabilities": {
        "validate_guess": {
            "description": "Validate guess against constraints",
            "parameters": {
                "type": "object",
                "properties": {
                    "guess": {"type": "array"},
                    "available_colors": {"type": "array"},
                    "expected_length": {"type": "integer"},
                    "constraints": {"type": "object"}
                }
            },
            "returns": {
                "type": "object",
                "properties": {
                    "valid": {"type": "boolean"},
                    "hard_violations": {"type": "array"},
                    "soft_warnings": {"type": "array"}
                }
            }
        }
    }
}

LOGGER_CARD = {
    "agent_id": "logger",
    "agent_name": "Logger",
    "agent_type": "logger",
    "paradigm": "base",
    "version": "1.0",
    "description": "Logs all inter-agent communication and events",
    "role": "logger",
    "constraints_owned": ["Audit trail maintenance", "Message recording"],
    "can_communicate": True,
    "team_members": ["analyzer", "strategist", "proposer", "validator", "boss"],
    "discovery_tags": ["logging", "audit", "communication"],
    "capabilities": {
        "log_message": {
            "description": "Log a message or event",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_type": {"type": "string"},
                    "sender": {"type": "string"},
                    "receiver": {"type": "string"},
                    "content": {"type": "object"}
                }
            },
            "returns": {
                "type": "object",
                "properties": {
                    "logged": {"type": "boolean"},
                    "message_id": {"type": "string"}
                }
            }
        },
        "get_logs": {
            "description": "Retrieve logs with filtering",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {"type": "string"},
                    "limit": {"type": "integer"}
                }
            },
            "returns": {
                "type": "array",
                "items": {"type": "object"}
            }
        }
    }
}

METRICS_CARD = {
    "agent_id": "metrics",
    "agent_name": "Metrics",
    "agent_type": "metrics",
    "paradigm": "base",
    "version": "1.0",
    "description": "Tracks and aggregates metrics across puzzle solving",
    "role": "metrics",
    "constraints_owned": ["Metrics aggregation", "Performance tracking"],
    "can_communicate": True,
    "team_members": ["analyzer", "strategist", "proposer", "validator", "boss"],
    "discovery_tags": ["metrics", "tracking", "performance"],
    "capabilities": {
        "record_metric": {
            "description": "Record a metric value",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string"},
                    "value": {"type": ["number", "integer", "string"]},
                    "tags": {"type": "object"}
                }
            },
            "returns": {
                "type": "object",
                "properties": {
                    "recorded": {"type": "boolean"}
                }
            }
        },
        "get_metrics": {
            "description": "Get aggregated metrics",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {"type": "string"}
                }
            },
            "returns": {
                "type": "object",
                "properties": {
                    "metrics": {"type": "object"}
                }
            }
        }
    }
}
