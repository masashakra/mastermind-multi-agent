# Central Agent Registry
# Implements A2A protocol for agent discovery
# Manages agent lifecycle and capability registration
# Used by all paradigms

import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from communication.protocol import A2ACommunicationLayer, A2AMessage
from base.agent_card import AgentCard


@dataclass
class RegisteredAgent:
    """Agent registration record"""
    agent_id: str
    agent_name: str
    agent_type: str
    paradigm: str
    agent_card: Dict[str, Any]
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.now().isoformat())
    capabilities: List[str] = field(default_factory=list)
    discovery_tags: List[str] = field(default_factory=list)


class AgentRegistry:
    """Central registry for agent discovery and management

    Implements A2A protocol for agent registration and discovery.
    All paradigms query this registry to find agents.

    Features:
    - Agent registration with metadata
    - Capability-based discovery
    - Agent type filtering
    - Paradigm filtering
    - Direct ID lookup
    - A2A protocol compliance
    """

    def __init__(self, comm_layer: Optional[A2ACommunicationLayer] = None):
        """Initialize registry

        Args:
            comm_layer: Optional A2ACommunicationLayer for remote queries
        """
        self.agents: Dict[str, RegisteredAgent] = {}
        self.agent_index: Dict[str, List[str]] = {
            # agent_type -> [agent_ids]
        }
        self.capability_index: Dict[str, List[str]] = {
            # capability -> [agent_ids]
        }
        self.paradigm_index: Dict[str, List[str]] = {
            # paradigm -> [agent_ids]
        }
        self.comm_layer = comm_layer

    def register_agent(self, agent_card: Dict[str, Any]) -> bool:
        """Register an agent with its card

        Args:
            agent_card: Agent card (OpenAPI format)

        Returns:
            True if registered successfully
        """
        agent_id = agent_card.get("agent_id")
        agent_type = agent_card.get("agent_type")
        agent_name = agent_card.get("agent_name")
        paradigm = agent_card.get("paradigm")
        capabilities = list(agent_card.get("capabilities", {}).keys())
        discovery_tags = agent_card.get("discovery_tags", [])

        if not agent_id:
            return False

        # Create registration record
        reg = RegisteredAgent(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            paradigm=paradigm,
            agent_card=agent_card,
            capabilities=capabilities,
            discovery_tags=discovery_tags
        )

        # Store agent
        self.agents[agent_id] = reg

        # Update indexes
        if agent_type not in self.agent_index:
            self.agent_index[agent_type] = []
        self.agent_index[agent_type].append(agent_id)

        for capability in capabilities:
            if capability not in self.capability_index:
                self.capability_index[capability] = []
            if agent_id not in self.capability_index[capability]:
                self.capability_index[capability].append(agent_id)

        if paradigm not in self.paradigm_index:
            self.paradigm_index[paradigm] = []
        if agent_id not in self.paradigm_index[paradigm]:
            self.paradigm_index[paradigm].append(agent_id)

        return True

    def find_agent_by_id(self, agent_id: str) -> Optional[RegisteredAgent]:
        """Find agent by exact ID

        Args:
            agent_id: Agent identifier

        Returns:
            RegisteredAgent or None
        """
        return self.agents.get(agent_id)

    def find_agents_by_type(self, agent_type: str) -> List[RegisteredAgent]:
        """Find all agents of a specific type

        Args:
            agent_type: e.g., "analyzer", "strategist", "logger"

        Returns:
            List of matching agents
        """
        agent_ids = self.agent_index.get(agent_type, [])
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]

    def find_agents_by_capability(self, capability: str) -> List[RegisteredAgent]:
        """Find all agents with a specific capability

        Args:
            capability: e.g., "analyze_feedback", "propose_guess"

        Returns:
            List of agents that support the capability
        """
        agent_ids = self.capability_index.get(capability, [])
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]

    def find_agents_by_paradigm(self, paradigm: str) -> List[RegisteredAgent]:
        """Find all agents in a specific paradigm

        Args:
            paradigm: e.g., "boss_worker", "round_table"

        Returns:
            List of agents in the paradigm
        """
        agent_ids = self.paradigm_index.get(paradigm, [])
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]

    def find_agents_by_tags(self, tags: List[str]) -> List[RegisteredAgent]:
        """Find agents matching any of the discovery tags

        Args:
            tags: List of discovery tags

        Returns:
            Agents matching any tag
        """
        matching = []
        for agent in self.agents.values():
            if any(tag in agent.discovery_tags for tag in tags):
                matching.append(agent)
        return matching

    def get_analyzer_agents(self, paradigm: Optional[str] = None) -> List[RegisteredAgent]:
        """Get analyzer agents (convenience method)"""
        agents = self.find_agents_by_type("analyzer")
        if paradigm:
            agents = [a for a in agents if a.paradigm == paradigm]
        return agents

    def get_strategist_agents(self, paradigm: Optional[str] = None) -> List[RegisteredAgent]:
        """Get strategist agents"""
        agents = self.find_agents_by_type("strategist")
        if paradigm:
            agents = [a for a in agents if a.paradigm == paradigm]
        return agents

    def get_proposer_agents(self, paradigm: Optional[str] = None) -> List[RegisteredAgent]:
        """Get proposer agents"""
        agents = self.find_agents_by_type("proposer")
        if paradigm:
            agents = [a for a in agents if a.paradigm == paradigm]
        return agents

    def get_validator_agents(self, paradigm: Optional[str] = None) -> List[RegisteredAgent]:
        """Get validator agents"""
        agents = self.find_agents_by_type("validator")
        if paradigm:
            agents = [a for a in agents if a.paradigm == paradigm]
        return agents

    def get_logger_agents(self, paradigm: Optional[str] = None) -> List[RegisteredAgent]:
        """Get logger agents"""
        agents = self.find_agents_by_type("logger")
        if paradigm:
            agents = [a for a in agents if a.paradigm == paradigm]
        return agents

    def get_metrics_agents(self, paradigm: Optional[str] = None) -> List[RegisteredAgent]:
        """Get metrics agents"""
        agents = self.find_agents_by_type("metrics")
        if paradigm:
            agents = [a for a in agents if a.paradigm == paradigm]
        return agents

    def heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat (mark as active)

        Args:
            agent_id: Agent identifier

        Returns:
            True if updated
        """
        if agent_id in self.agents:
            self.agents[agent_id].last_heartbeat = datetime.now().isoformat()
            return True
        return False

    def get_active_agents(self, timeout_seconds: int = 300) -> List[RegisteredAgent]:
        """Get agents that have had recent heartbeat

        Args:
            timeout_seconds: Consider agent active if heartbeat within this time

        Returns:
            List of active agents
        """
        cutoff = datetime.now().timestamp() - timeout_seconds
        active = []
        for agent in self.agents.values():
            try:
                hb_time = datetime.fromisoformat(agent.last_heartbeat).timestamp()
                if hb_time > cutoff:
                    active.append(agent)
            except:
                pass
        return active

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent

        Args:
            agent_id: Agent to remove

        Returns:
            True if unregistered
        """
        if agent_id not in self.agents:
            return False

        agent = self.agents[agent_id]

        # Remove from indexes
        if agent.agent_type in self.agent_index:
            self.agent_index[agent.agent_type] = [
                aid for aid in self.agent_index[agent.agent_type]
                if aid != agent_id
            ]

        for capability in agent.capabilities:
            if capability in self.capability_index:
                self.capability_index[capability] = [
                    aid for aid in self.capability_index[capability]
                    if aid != agent_id
                ]

        if agent.paradigm in self.paradigm_index:
            self.paradigm_index[agent.paradigm] = [
                aid for aid in self.paradigm_index[agent.paradigm]
                if aid != agent_id
            ]

        # Remove agent
        del self.agents[agent_id]
        return True

    def get_summary(self) -> Dict[str, Any]:
        """Get registry summary

        Returns:
            Dictionary with counts and agent list
        """
        return {
            "total_agents": len(self.agents),
            "agents_by_type": {
                agent_type: len(agents)
                for agent_type, agents in self.agent_index.items()
            },
            "agents_by_paradigm": {
                paradigm: len(agents)
                for paradigm, agents in self.paradigm_index.items()
            },
            "capabilities": list(self.capability_index.keys()),
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "agent_name": a.agent_name,
                    "agent_type": a.agent_type,
                    "paradigm": a.paradigm,
                    "capabilities": a.capabilities
                }
                for a in self.agents.values()
            ]
        }

    def to_json(self) -> str:
        """Serialize registry to JSON"""
        return json.dumps(self.get_summary(), indent=2)


# Global registry instance (shared across paradigms)
_global_registry: Optional[AgentRegistry] = None


def get_global_registry(comm_layer: Optional[A2ACommunicationLayer] = None) -> AgentRegistry:
    """Get or create global registry

    Args:
        comm_layer: Optional communication layer

    Returns:
        Global AgentRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry(comm_layer)
    return _global_registry


def reset_global_registry() -> None:
    """Reset global registry (for testing)"""
    global _global_registry
    _global_registry = None
