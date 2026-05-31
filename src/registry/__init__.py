# Registry module - central agent discovery and management

from registry.registry import (
    AgentRegistry,
    RegisteredAgent,
    get_global_registry,
    reset_global_registry
)

__all__ = [
    "AgentRegistry",
    "RegisteredAgent",
    "get_global_registry",
    "reset_global_registry",
]
