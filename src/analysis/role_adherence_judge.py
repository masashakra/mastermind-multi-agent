"""
LLM Judge for evaluating agent role adherence.
Determines whether each message aligns with the agent's defined role.
"""

import json
from typing import Dict, List, Tuple
import os
import anthropic

from .role_definitions import get_role_definition, get_all_roles


class RoleAdherenceJudge:
    """Judge that evaluates whether agent messages are role-specific."""

    def __init__(self, model: str = "deepseek-reasoner", use_mock: bool = True):
        """
        Initialize the judge with specified model.

        Args:
            model: Model to use (default: deepseek-reasoner)
            use_mock: If True, use mock judge (heuristics) with fast evaluation.
                     If False, attempt to use real LLM (requires API setup).
        """
        self.model = model
        self.evaluation_cache = {}
        self.use_mock = use_mock
        self.client = None

        # Initialize mock judge by default (fast, works without API key)
        if use_mock:
            from .mock_judge import MockRoleAdherenceJudge
            self.mock_judge = MockRoleAdherenceJudge()
        else:
            # Try to initialize LLM client
            try:
                api_key = os.environ.get("DEEPSEEK_API_KEY")
                if api_key:
                    self.client = anthropic.Anthropic(
                        api_key=api_key,
                        base_url="https://api.deepseek.com"
                    )
                else:
                    self.client = anthropic.Anthropic()
            except Exception as e:
                print(f"⚠️  Warning: Could not initialize LLM client ({str(e)})")
                print("   Falling back to mock judge (heuristic-based evaluation)")
                self.use_mock = True
                from .mock_judge import MockRoleAdherenceJudge
                self.mock_judge = MockRoleAdherenceJudge()

    def evaluate_message(self, agent_name: str, message_content: str) -> Dict:
        """
        Evaluate whether a message is role-specific.

        Args:
            agent_name: Name of the agent (analyzer, strategist, proposer, validator, boss)
            message_content: The actual message content to evaluate

        Returns:
            Dict with:
                - is_role_specific: bool
                - confidence: float (0-1)
                - reasoning: str
                - violations: List[str] (if any)
        """
        # Create cache key
        cache_key = (agent_name.lower(), hash(message_content))
        if cache_key in self.evaluation_cache:
            return self.evaluation_cache[cache_key]

        # Use mock judge if client is unavailable
        if self.use_mock or self.client is None:
            return self.mock_judge.evaluate_message(agent_name, message_content)

        role_def = get_role_definition(agent_name)

        prompt = f"""You are evaluating whether an agent's message aligns with its defined role in a multi-agent Mastermind puzzle-solving system.

AGENT: {role_def['name']}
PRIMARY RESPONSIBILITY: {role_def['primary_responsibility']}

KEY RESPONSIBILITIES:
{json.dumps(role_def['key_responsibilities'], indent=2)}

SHOULD NOT DO:
{json.dumps(role_def['should_NOT_do'], indent=2)}

EXPECTED ACTIONS:
{json.dumps(role_def['expected_actions'], indent=2)}

---

MESSAGE TO EVALUATE:
{message_content}

---

Based on the agent's role definition, evaluate whether this message is appropriate and role-specific.

Provide your evaluation in JSON format:
{{
    "is_role_specific": boolean,
    "confidence": float (0.0-1.0),
    "reasoning": "Brief explanation of your evaluation",
    "violations": [list of specific role violations if any, empty list if none]
}}

IMPORTANT:
- is_role_specific should be true if the message aligns with the agent's responsibilities
- is_role_specific should be false if the message goes outside the agent's scope or violates "should_NOT_do" items
- confidence should reflect how certain you are (1.0 = very certain, 0.5 = uncertain)
- violations should list specific "should_NOT_do" items violated, if any"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = response.content[0].text

            # Try to extract JSON from response
            try:
                # Find JSON in response (may be wrapped in markdown)
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    evaluation = json.loads(json_match.group())
                else:
                    evaluation = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback parsing
                evaluation = {
                    "is_role_specific": "role-specific" in response_text.lower() or "appropriate" in response_text.lower(),
                    "confidence": 0.5,
                    "reasoning": response_text,
                    "violations": [],
                }

            # Cache result
            self.evaluation_cache[cache_key] = evaluation
            return evaluation

        except Exception as e:
            return {
                "is_role_specific": None,
                "confidence": 0.0,
                "reasoning": f"Error during evaluation: {str(e)}",
                "violations": [],
            }

    def evaluate_messages(self, agent_name: str, messages: List[str]) -> Dict:
        """
        Evaluate a list of messages from an agent.

        Args:
            agent_name: Name of the agent
            messages: List of message contents

        Returns:
            Dict with:
                - agent: str
                - total_messages: int
                - role_specific_count: int
                - role_adherence_pct: float
                - evaluations: List[Dict] (detailed evaluation for each message)
                - avg_confidence: float
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
            (total_confidence / total_messages)
            if total_messages > 0
            else 0.0
        )

        return {
            "agent": agent_name,
            "total_messages": total_messages,
            "role_specific_count": role_specific_count,
            "role_adherence_pct": role_adherence_pct,
            "avg_confidence": avg_confidence,
            "evaluations": evaluations,
        }

    def evaluate_message_log(
        self, messages_by_agent: Dict[str, List[str]]
    ) -> Dict:
        """
        Evaluate all messages from all agents.

        Args:
            messages_by_agent: Dict mapping agent names to lists of messages

        Returns:
            Dict with:
                - results_by_agent: Dict[str, agent results]
                - overall_adherence_pct: float
                - summary: str
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
            (total_role_specific / total_messages * 100) if total_messages > 0 else 0.0
        )

        return {
            "results_by_agent": results_by_agent,
            "overall_adherence_pct": overall_adherence_pct,
            "total_messages": total_messages,
        }


def print_role_adherence_report(evaluation_result: Dict) -> str:
    """Print a formatted role adherence report."""
    report = []
    report.append("\n" + "=" * 70)
    report.append("ROLE ADHERENCE EVALUATION REPORT")
    report.append("=" * 70)

    # Overall stats
    report.append(
        f"\n📊 Overall Role Adherence: {evaluation_result['overall_adherence_pct']:.1f}%"
    )
    report.append(f"📈 Total Messages Evaluated: {evaluation_result['total_messages']}\n")

    # Per-agent results
    for agent_name, agent_results in evaluation_result["results_by_agent"].items():
        report.append("-" * 70)
        report.append(f"Agent: {agent_name.upper()}")
        report.append("-" * 70)
        report.append(
            f"  Role Adherence: {agent_results['role_adherence_pct']:.1f}%"
        )
        report.append(
            f"  Messages: {agent_results['role_specific_count']}/{agent_results['total_messages']}"
        )
        report.append(f"  Confidence: {agent_results['avg_confidence']:.2f}")

        # Show violations if any
        violations_by_msg = {}
        for i, eval_data in enumerate(agent_results["evaluations"]):
            if eval_data.get("violations"):
                violations_by_msg[i] = eval_data["violations"]

        if violations_by_msg:
            report.append(f"\n  ⚠️  Messages with violations: {len(violations_by_msg)}")
            for msg_idx, violations in violations_by_msg.items():
                report.append(f"    Message {msg_idx + 1}: {violations}")

    report.append("\n" + "=" * 70)
    return "\n".join(report)
