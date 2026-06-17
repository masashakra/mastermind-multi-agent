"""
Agent Role and Paradigm Definitions

Provides explicit role awareness for agents in multi-agent systems.
Based on Adimulam et al. (2026) recommendation that agents should
explicitly state their role and constraints for better coordination
(30-50% improvement in coordination quality).
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional


class AgentRole(Enum):
    """Explicit agent roles in the multi-agent system"""

    BOSS = "boss"
    STRATEGIST = "strategist"
    ANALYZER = "analyzer"
    PROPOSER = "proposer"
    VALIDATOR = "validator"

    def __str__(self) -> str:
        return self.value.upper()

    def get_description(self) -> str:
        """Get human-readable description of the role"""
        descriptions = {
            "boss": "Orchestrates team communication and coordinates worker agents via A2A protocol",
            "strategist": "Analyzes game state and proposes strategies for the next guess",
            "analyzer": "Extracts constraints from feedback and identifies locked positions",
            "proposer": "Generates guesses that respect all constraints",
            "validator": "Validates guesses against hard and soft constraints"
        }
        return descriptions.get(self.value, "Unknown role")


class ParadigmType(Enum):
    """Explicit paradigm types for multi-agent coordination"""

    BOSS_WORKER = "boss_worker"
    DIRECT_DEBATE = "direct_debate"
    DIRECT_DEBATE_JUDGE_FEEDBACK = "direct_debate_judge_feedback"
    ROUND_TABLE = "round_table"

    def __str__(self) -> str:
        return self.value

    def get_description(self) -> str:
        """Get human-readable description of the paradigm"""
        descriptions = {
            "boss_worker": "Centralized Boss orchestrates all workers via A2A protocol",
            "direct_debate": "Agents debate and discuss solutions directly",
            "direct_debate_judge_feedback": "Judge evaluates and selects between debating agent proposals (with strict constraints)",
            "round_table": "Peer agents call each other directly without a Boss coordinator",
        }
        return descriptions.get(self.value, "Unknown paradigm")

    def enables_communication(self) -> bool:
        """Return whether this paradigm enables direct agent-to-agent communication"""
        # Paradigms with A2A communication
        communicating = {
            ParadigmType.BOSS_WORKER,
            ParadigmType.DIRECT_DEBATE_JUDGE_FEEDBACK,
        }
        return self in communicating


@dataclass
class RoleContext:
    """
    Complete role context for an agent

    This provides agents with explicit knowledge of:
    - What role they have in the system
    - Which paradigm they're operating in
    - Which other agents are on their team
    - Whether they can communicate directly with other agents
    - What constraints they are responsible for enforcing

    Based on Adimulam et al. (2026) recommendation for explicit
    role and constraint awareness (30-50% coordination improvement).
    """

    agent_id: str  # e.g., "strategist", "analyzer"
    role: AgentRole  # e.g., AgentRole.STRATEGIST
    paradigm: ParadigmType  # e.g., ParadigmType.BOSS_WORKER
    team_members: List[str]  # e.g., ["boss", "analyzer", "proposer", "validator"]
    can_communicate: bool  # Whether agent can send A2A requests
    constraints_owned: List[str]  # Constraints this agent is responsible for

    def get_system_prompt(self) -> str:
        """
        Generate system context prompt for agent initialization.

        This is prepended to all agent prompts to give explicit role context.
        Agents can then reference their role, team, and constraints in reasoning.

        Benefit: Per Adimulam et al., explicit role statements improve
        coordination quality by 30-50%.
        """
        comm_status = "ENABLED" if self.can_communicate else "DISABLED"
        team_str = ", ".join(self.team_members)

        if self.constraints_owned:
            constraints_str = "\n  • ".join(self.constraints_owned)
        else:
            constraints_str = "None"

        return f"""
================================================================================
YOU ARE THE {self.role.value.upper()} AGENT IN A MULTI-AGENT SYSTEM
================================================================================

YOUR IDENTITY AND ROLE:
  • Agent ID: {self.agent_id}
  • Role: {self.role.get_description()}
  • Paradigm: {self.paradigm.get_description()}

YOUR TEAM AND COMMUNICATION:
  • Team Members: {team_str}
  • Communication Status: {comm_status}
{f'  • You CAN send direct A2A requests to: {team_str}' if self.can_communicate else '  • You CANNOT send direct A2A requests (Orchestrator coordinates instead)'}

YOUR CONSTRAINTS AND RESPONSIBILITIES:
  As the {self.role.value.upper()}, you are explicitly responsible for:
  • {constraints_str}

WHAT THIS MEANS FOR YOUR REASONING:
  1. Acknowledge your role clearly: "As the {self.role.value.upper()}, I..."
  2. State what constraints you enforce: "I will ensure..."
  3. Mention coordination with team: "I coordinate with {self.team_members[0]}..."
  4. Remember your paradigm context: "In {self.paradigm.value}, ..."

RESEARCH BASIS:
  Explicit role awareness and constraint statements improve multi-agent
  coordination by 30-50% (Adimulam et al., 2026). Your role context helps
  the system achieve this improvement.

================================================================================
"""

    def validate_communication(self, receiver_id: str) -> bool:
        """
        Validate whether this agent can communicate with a given receiver.

        Returns True if:
        1. Agent has communication enabled for this paradigm
        2. Receiver is in the agent's team members list
        """
        return self.can_communicate and receiver_id in self.team_members
