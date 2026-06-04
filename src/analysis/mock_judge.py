"""
Mock LLM Judge for testing without requiring API credentials.
Use this for development and testing before running with real Claude.
"""

import re
from typing import Dict, List


class MockRoleAdherenceJudge:
    """Mock judge that evaluates role adherence using heuristics."""

    def __init__(self):
        """Initialize mock judge."""
        self.evaluation_cache = {}

        # Define role-specific keywords and patterns for each agent
        self.role_patterns = {
            "analyzer": {
                "should_contain": [
                    "feedback",
                    "constraint",
                    "color",
                    "exclude",
                    "include",
                    "deduce",
                    "identify",
                    "pattern",
                    "deduction",
                    "excluded",
                ],
                "should_not_contain": ["guess", "propose", "strategy", "test next"],
            },
            "strategist": {
                "should_contain": [
                    "strategy",
                    "approach",
                    "priority",
                    "decision",
                    "explore",
                    "determine",
                    "focus",
                    "plan",
                ],
                "should_not_contain": ["guess", "validate", "feedback analysis"],
            },
            "proposer": {
                "should_contain": ["guess", "propose", "color", "sequence", "peg"],
                "should_not_contain": [
                    "analyze",
                    "strategy",
                    "validate",
                    "feedback",
                    "constraint",
                ],
            },
            "validator": {
                "should_contain": [
                    "validate",
                    "check",
                    "constraint",
                    "valid",
                    "violation",
                    "comply",
                ],
                "should_not_contain": ["analyze", "propose", "strategy"],
            },
            "boss": {
                "should_contain": [
                    "orchestrate",
                    "coordinate",
                    "discover",
                    "decide",
                    "contact",
                    "message",
                    "registry",
                ],
                "should_not_contain": ["analyze", "propose", "validate"],
            },
        }

    def evaluate_message(self, agent_name: str, message_content: str) -> Dict:
        """
        Evaluate whether a message is role-specific using heuristics.

        Args:
            agent_name: Name of the agent
            message_content: The message to evaluate

        Returns:
            Dict with evaluation results
        """
        cache_key = (agent_name.lower(), hash(message_content))
        if cache_key in self.evaluation_cache:
            return self.evaluation_cache[cache_key]

        agent_key = agent_name.lower().strip()
        patterns = self.role_patterns.get(agent_key, {})

        if not patterns:
            return {
                "is_role_specific": None,
                "confidence": 0.0,
                "reasoning": f"Unknown agent: {agent_name}",
                "violations": [],
            }

        # Convert message to lowercase for pattern matching
        msg_lower = message_content.lower()

        # Count keyword matches
        positive_matches = sum(
            1 for keyword in patterns.get("should_contain", [])
            if keyword in msg_lower
        )
        negative_matches = sum(
            1 for keyword in patterns.get("should_not_contain", [])
            if keyword in msg_lower
        )

        # Calculate confidence and role-specificity
        max_positive = len(patterns.get("should_contain", [])) or 1
        max_negative = len(patterns.get("should_not_contain", [])) or 1

        # Simple heuristic scoring
        positive_score = positive_matches / max_positive
        negative_score = negative_matches / max_negative

        # Is role-specific if more positive matches and fewer negative matches
        is_role_specific = positive_score > 0.3 and negative_matches == 0
        confidence = min(1.0, positive_score + (1.0 - negative_score)) / 2.0

        # Identify violations
        violations = []
        if negative_matches > 0:
            for keyword in patterns.get("should_not_contain", []):
                if keyword in msg_lower:
                    violations.append(f"Contains '{keyword}' (prohibited for {agent_name})")

        evaluation = {
            "is_role_specific": is_role_specific,
            "confidence": confidence,
            "reasoning": (
                f"Role-specific keywords: {positive_matches}/{max_positive} found. "
                f"Prohibited keywords: {negative_matches}/{max_negative} found."
            ),
            "violations": violations,
        }

        self.evaluation_cache[cache_key] = evaluation
        return evaluation

    def evaluate_messages(self, agent_name: str, messages: List[str]) -> Dict:
        """
        Evaluate a list of messages from an agent.

        Args:
            agent_name: Name of the agent
            messages: List of message contents

        Returns:
            Dict with aggregated results
        """
        evaluations = []
        role_specific_count = 0
        total_confidence = 0.0

        for msg in messages:
            eval_result = self.evaluate_message(agent_name, msg)
            evaluations.append(eval_result)

            if eval_result.get("is_role_specific"):
                role_specific_count += 1

            confidence = eval_result.get("confidence", 0.0)
            if confidence is not None:
                total_confidence += confidence

        total_messages = len(messages)
        role_adherence_pct = (
            (role_specific_count / total_messages * 100) if total_messages > 0 else 0.0
        )

        avg_confidence = (
            (total_confidence / total_messages) if total_messages > 0 else 0.0
        )

        return {
            "agent": agent_name,
            "total_messages": total_messages,
            "role_specific_count": role_specific_count,
            "role_adherence_pct": role_adherence_pct,
            "avg_confidence": avg_confidence,
            "evaluations": evaluations,
        }

    def evaluate_message_log(self, messages_by_agent: Dict[str, List[str]]) -> Dict:
        """
        Evaluate all messages from all agents.

        Args:
            messages_by_agent: Dict mapping agent names to lists of messages

        Returns:
            Dict with evaluation results
        """
        results_by_agent = {}

        for agent_name, messages in messages_by_agent.items():
            results_by_agent[agent_name] = self.evaluate_messages(agent_name, messages)

        # Calculate overall adherence
        total_role_specific = sum(
            r["role_specific_count"] for r in results_by_agent.values()
        )
        total_messages = sum(r["total_messages"] for r in results_by_agent.values())

        overall_adherence_pct = (
            (total_role_specific / total_messages * 100)
            if total_messages > 0
            else 0.0
        )

        return {
            "results_by_agent": results_by_agent,
            "overall_adherence_pct": overall_adherence_pct,
            "total_messages": total_messages,
        }
