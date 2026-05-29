# Agent Discovery Service - A2A Agent Registration and Lookup
# Manages agent registry, discovery, and capability queries

from typing import Dict, List, Optional, Any
from .agent_card import AgentCard, AgentCapability


class AgentRegistry:
    """
    Agent Registry - Central registry for all agents in the A2A system.

    Handles:
    - Agent registration and deregistration
    - Agent discovery by various criteria
    - Capability queries
    - Agent metadata retrieval
    """

    def __init__(self):
        """Initialize the agent registry."""
        self.agents: Dict[str, AgentCard] = {}  # agent_id -> AgentCard
        self.agents_by_type: Dict[str, List[str]] = {}  # agent_type -> [agent_ids]
        self.agents_by_capability: Dict[str, List[str]] = {}  # action -> [agent_ids]
        self.agents_by_tag: Dict[str, List[str]] = {}  # tag -> [agent_ids]

    def register_agent(self, card: AgentCard) -> None:
        """Register an agent with its card.

        Args:
            card: AgentCard describing the agent

        Raises:
            ValueError: If agent_id already registered
        """
        if card.agent_id in self.agents:
            raise ValueError(f"Agent {card.agent_id} already registered")

        # Store agent card
        self.agents[card.agent_id] = card

        # Index by type
        if card.agent_type not in self.agents_by_type:
            self.agents_by_type[card.agent_type] = []
        self.agents_by_type[card.agent_type].append(card.agent_id)

        # Index by capability
        for capability in card.capabilities:
            if capability.action not in self.agents_by_capability:
                self.agents_by_capability[capability.action] = []
            self.agents_by_capability[capability.action].append(card.agent_id)

        # Index by discovery tags
        for tag in card.discovery_tags:
            if tag not in self.agents_by_tag:
                self.agents_by_tag[tag] = []
            self.agents_by_tag[tag].append(card.agent_id)

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent.

        Args:
            agent_id: Agent identifier
        """
        if agent_id not in self.agents:
            return

        card = self.agents.pop(agent_id)

        # Remove from type index
        if card.agent_type in self.agents_by_type:
            self.agents_by_type[card.agent_type].remove(agent_id)

        # Remove from capability index
        for capability in card.capabilities:
            if capability.action in self.agents_by_capability:
                self.agents_by_capability[capability.action].remove(agent_id)

        # Remove from tag index
        for tag in card.discovery_tags:
            if tag in self.agents_by_tag:
                self.agents_by_tag[tag].remove(agent_id)

    def get_agent(self, agent_id: str) -> Optional[AgentCard]:
        """Get agent card by agent ID.

        Args:
            agent_id: Unique agent identifier

        Returns:
            AgentCard or None if not found
        """
        return self.agents.get(agent_id)

    def get_agents_by_type(self, agent_type: str) -> List[AgentCard]:
        """Get all agents of a specific type.

        Args:
            agent_type: Agent type classification

        Returns:
            List of AgentCards
        """
        agent_ids = self.agents_by_type.get(agent_type, [])
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]

    def get_agents_by_capability(self, action: str) -> List[AgentCard]:
        """Get all agents that can perform a specific action.

        Args:
            action: Action name (e.g., "propose_strategy")

        Returns:
            List of AgentCards capable of the action
        """
        agent_ids = self.agents_by_capability.get(action, [])
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]

    def get_agents_by_tag(self, tag: str) -> List[AgentCard]:
        """Get all agents matching a discovery tag.

        Args:
            tag: Discovery tag

        Returns:
            List of AgentCards with that tag
        """
        agent_ids = self.agents_by_tag.get(tag, [])
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]

    def find_agent_for_action(self, action: str) -> Optional[AgentCard]:
        """Find an agent capable of performing an action.

        Args:
            action: Action name

        Returns:
            First AgentCard capable of the action, or None
        """
        agents = self.get_agents_by_capability(action)
        return agents[0] if agents else None

    def list_all_agents(self) -> List[AgentCard]:
        """Get all registered agents.

        Returns:
            List of all AgentCards
        """
        return list(self.agents.values())

    def get_registry_info(self) -> Dict[str, Any]:
        """Get information about the registry.

        Returns:
            Dict with registry statistics
        """
        return {
            "total_agents": len(self.agents),
            "agent_types": list(self.agents_by_type.keys()),
            "total_capabilities": len(self.agents_by_capability),
            "total_tags": len(self.agents_by_tag),
            "agents": {aid: card.agent_name for aid, card in self.agents.items()}
        }

    def validate_agent_can_perform(self, agent_id: str, action: str) -> bool:
        """Check if an agent can perform a specific action.

        Args:
            agent_id: Agent to check
            action: Action to perform

        Returns:
            True if agent can perform action
        """
        card = self.get_agent(agent_id)
        if not card:
            return False
        return card.has_capability(action)

    def get_agent_capability(self, agent_id: str, action: str) -> Optional[AgentCapability]:
        """Get capability details for an agent performing an action.

        Args:
            agent_id: Agent ID
            action: Action name

        Returns:
            AgentCapability or None
        """
        card = self.get_agent(agent_id)
        if not card:
            return None
        return card.get_capability(action)

    def clear(self) -> None:
        """Clear all registered agents."""
        self.agents.clear()
        self.agents_by_type.clear()
        self.agents_by_capability.clear()
        self.agents_by_tag.clear()


class AgentDiscovery:
    """
    Agent Discovery Service - Query interface for finding agents.

    Provides methods to discover agents by various criteria.
    """

    def __init__(self, registry: AgentRegistry):
        """Initialize discovery service with a registry.

        Args:
            registry: AgentRegistry instance
        """
        self.registry = registry

    def find_strategist(self) -> Optional[AgentCard]:
        """Find the strategist agent."""
        agents = self.registry.get_agents_by_tag("strategist")
        return agents[0] if agents else None

    def find_analyzer(self) -> Optional[AgentCard]:
        """Find the analyzer agent."""
        agents = self.registry.get_agents_by_tag("analyzer")
        return agents[0] if agents else None

    def find_proposer(self) -> Optional[AgentCard]:
        """Find the proposer agent."""
        agents = self.registry.get_agents_by_tag("proposer")
        return agents[0] if agents else None

    def find_validator(self) -> Optional[AgentCard]:
        """Find the validator agent."""
        agents = self.registry.get_agents_by_tag("validator")
        return agents[0] if agents else None

    def find_agent_for_strategy_proposal(self) -> Optional[AgentCard]:
        """Find an agent that can propose strategies."""
        return self.registry.find_agent_for_action("propose_strategy")

    def find_agent_for_feedback_analysis(self) -> Optional[AgentCard]:
        """Find an agent that can analyze feedback."""
        return self.registry.find_agent_for_action("analyze_feedback")

    def find_agent_for_guess_proposal(self) -> Optional[AgentCard]:
        """Find an agent that can propose guesses."""
        return self.registry.find_agent_for_action("propose_guess")

    def find_agent_for_validation(self) -> Optional[AgentCard]:
        """Find an agent that can validate guesses."""
        return self.registry.find_agent_for_action("validate_guess")

    def find_mastermind_agents(self) -> List[AgentCard]:
        """Find all mastermind-related agents."""
        return self.registry.get_agents_by_tag("mastermind")

    def get_available_actions(self) -> List[str]:
        """Get all available actions across all agents."""
        return list(self.registry.agents_by_capability.keys())

    def get_agent_capabilities(self, agent_id: str) -> List[str]:
        """Get all capabilities of an agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of action names the agent can perform
        """
        card = self.registry.get_agent(agent_id)
        if not card:
            return []
        return [cap.action for cap in card.capabilities]
