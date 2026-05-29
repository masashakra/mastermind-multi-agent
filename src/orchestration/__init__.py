# Orchestration Layer - Separate from Communication Layer
# Uses LangGraph for workflow management
# Agents communicate through A2A protocol only

from .orchestrator import MastermindOrchestrator

__all__ = [
    "MastermindOrchestrator",
]
