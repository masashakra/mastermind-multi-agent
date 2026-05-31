"""
A2A Contracts — Strict request/response schemas for each agent capability.

Ensures that all agent-to-agent calls conform to a strict contract:
  - Input payload validates against input_schema
  - Output payload validates against output_schema
  - Errors follow standard error codes

This enables:
  - Deterministic validation
  - Cross-agent interoperability
  - Debugging and error tracing
"""

from typing import Any, Dict


# ── Analyzer Contracts ────────────────────────────────────────────────────────

ANALYZER_ANALYZE_INPUT = {
    "type": "object",
    "required": ["last_guess", "feedback", "previous_guesses"],
    "properties": {
        "last_guess": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The last guess submitted",
        },
        "feedback": {
            "type": "object",
            "properties": {
                "correct_pegs": {"type": "integer", "minimum": 0},
                "correct_positions": {"type": "integer", "minimum": 0},
            },
            "description": "Feedback from game engine",
        },
        "previous_guesses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "round": {"type": "integer"},
                    "guess": {"type": "array", "items": {"type": "string"}},
                    "feedback": {"type": "object"},
                },
            },
            "description": "All previous guesses and feedback",
        },
    },
}

ANALYZER_ANALYZE_OUTPUT = {
    "type": "object",
    "required": ["analysis", "confidence", "constraints"],
    "properties": {
        "analysis": {"type": "string", "description": "Text explanation"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "constraints": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Identified constraints",
        },
        "correct_positions": {"type": "array", "items": {"type": "integer"}},
        "correct_colors_wrong_position": {"type": "array", "items": {"type": "string"}},
        "impossible_colors": {"type": "array", "items": {"type": "string"}},
    },
}


# ── Strategist Contracts ──────────────────────────────────────────────────────

STRATEGIST_STRATEGY_INPUT = {
    "type": "object",
    "required": ["guess_history", "difficulty"],
    "properties": {
        "guess_history": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "round": {"type": "integer"},
                    "guess": {"type": "array", "items": {"type": "string"}},
                    "feedback": {"type": "object"},
                },
            },
        },
        "difficulty": {
            "type": "string",
            "enum": ["easy", "medium", "hard"],
        },
    },
}

STRATEGIST_STRATEGY_OUTPUT = {
    "type": "object",
    "required": ["phase", "strategy", "confidence"],
    "properties": {
        "phase": {
            "type": "string",
            "enum": ["exploration", "constraint_building", "refinement", "confirmation"],
            "description": "Current game phase",
        },
        "strategy": {"type": "string", "description": "Strategy for this phase"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "guidance": {
            "type": "object",
            "properties": {
                "for_proposer": {"type": "string"},
                "focus_areas": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}


# ── Proposer Contracts ────────────────────────────────────────────────────────

PROPOSER_PROPOSE_INPUT = {
    "type": "object",
    "required": ["strategy", "constraints_text", "available_colors", "num_pegs"],
    "properties": {
        "strategy": {"type": "string"},
        "constraints_text": {"type": "string"},
        "available_colors": {
            "type": "array",
            "items": {"type": "string"},
        },
        "num_pegs": {"type": "integer", "minimum": 1},
        "previous_guesses": {
            "type": "array",
            "items": {"type": "array", "items": {"type": "string"}},
        },
    },
}

PROPOSER_PROPOSE_OUTPUT = {
    "type": "object",
    "required": ["proposed_guess", "reasoning", "confidence"],
    "properties": {
        "proposed_guess": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The proposed guess",
        },
        "reasoning": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "strategy_alignment": {"type": "string"},
        "expected_outcome": {"type": "string"},
    },
}


# ── Validator Contracts ───────────────────────────────────────────────────────

VALIDATOR_VALIDATE_INPUT = {
    "type": "object",
    "required": ["guess", "available_colors", "expected_length"],
    "properties": {
        "guess": {
            "type": "array",
            "items": {"type": "string"},
        },
        "available_colors": {
            "type": "array",
            "items": {"type": "string"},
        },
        "expected_length": {"type": "integer", "minimum": 1},
        "previous_guesses": {
            "type": "array",
            "items": {"type": "array", "items": {"type": "string"}},
        },
        "constraints": {
            "type": "object",
            "properties": {
                "correct_positions": {"type": "array"},
                "correct_colors_wrong_position": {"type": "array"},
                "impossible_colors": {"type": "array"},
            },
        },
    },
}

VALIDATOR_VALIDATE_OUTPUT = {
    "type": "object",
    "required": ["valid", "confidence"],
    "properties": {
        "valid": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "hard_violations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Constraint violations",
        },
        "soft_warnings": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Strategic concerns",
        },
        "reasoning": {"type": "string"},
        "strategic_assessment": {"type": "string"},
    },
}


# ── Logger Contracts ──────────────────────────────────────────────────────────

LOGGER_LOG_INPUT = {
    "type": "object",
    "required": ["message_type", "sender", "content"],
    "properties": {
        "message_type": {
            "type": "string",
            "enum": ["analysis", "strategy", "proposal", "validation", "feedback", "error", "metric"],
        },
        "sender": {"type": "string"},
        "receiver": {"type": "string"},
        "round": {"type": "integer"},
        "content": {"type": "object"},
    },
}

LOGGER_LOG_OUTPUT = {
    "type": "object",
    "required": ["logged"],
    "properties": {
        "logged": {"type": "boolean"},
        "log_id": {"type": "string"},
        "timestamp": {"type": "number"},
    },
}


# ── Metrics Contracts ─────────────────────────────────────────────────────────

METRICS_RECORD_INPUT = {
    "type": "object",
    "required": ["metric_name", "value"],
    "properties": {
        "metric_name": {"type": "string"},
        "value": {},  # Can be any type
        "tags": {
            "type": "object",
            "description": "Optional metadata",
        },
    },
}

METRICS_RECORD_OUTPUT = {
    "type": "object",
    "required": ["recorded"],
    "properties": {
        "recorded": {"type": "boolean"},
        "metric_name": {"type": "string"},
    },
}


# ── Contract Registry ─────────────────────────────────────────────────────────

AGENT_CONTRACTS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "analyzer": {
        "analyze": {
            "input": ANALYZER_ANALYZE_INPUT,
            "output": ANALYZER_ANALYZE_OUTPUT,
            "timeout": 30,
        },
    },
    "strategist": {
        "strategy": {
            "input": STRATEGIST_STRATEGY_INPUT,
            "output": STRATEGIST_STRATEGY_OUTPUT,
            "timeout": 30,
        },
    },
    "proposer": {
        "propose": {
            "input": PROPOSER_PROPOSE_INPUT,
            "output": PROPOSER_PROPOSE_OUTPUT,
            "timeout": 30,
        },
    },
    "validator": {
        "validate": {
            "input": VALIDATOR_VALIDATE_INPUT,
            "output": VALIDATOR_VALIDATE_OUTPUT,
            "timeout": 30,
        },
    },
    "logger": {
        "log": {
            "input": LOGGER_LOG_INPUT,
            "output": LOGGER_LOG_OUTPUT,
            "timeout": 10,
        },
    },
    "metrics": {
        "record": {
            "input": METRICS_RECORD_INPUT,
            "output": METRICS_RECORD_OUTPUT,
            "timeout": 10,
        },
    },
}


def get_contract(agent_type: str, action: str) -> Dict[str, Any]:
    """Get the contract for an agent capability."""
    if agent_type not in AGENT_CONTRACTS:
        return None
    return AGENT_CONTRACTS[agent_type].get(action)
