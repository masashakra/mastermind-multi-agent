"""
LLM Judge for evaluating agent role adherence.
Uses DeepSeek R1 via OpenAI-compatible API — no mock fallback.
"""

import json
import os
import re
import requests
from typing import Dict, List

from .role_definitions import get_role_definition


class RoleAdherenceJudge:
    """Evaluates whether each agent message aligns with its defined role."""

    def __init__(self):
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not set. Add it to .env.groq")
        self.api_key   = api_key
        self.base_url  = "https://api.deepseek.com"
        self.model     = "deepseek-chat"   # cheaper than R1 for classification
        self.cache     = {}

    def _call_llm(self, prompt: str) -> str:
        """Call DeepSeek API and return response text."""
        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400,
                "temperature": 0.0,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def evaluate_message(self, agent_name: str, message_content: str) -> Dict:
        """
        Evaluate whether a single message is on-role for the given agent.

        Returns:
            {
                "is_role_specific": bool,
                "confidence": float,
                "reasoning": str,
                "violations": List[str]
            }
        """
        cache_key = (agent_name.lower(), hash(message_content))
        if cache_key in self.cache:
            return self.cache[cache_key]

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

Evaluate whether this message is appropriate and role-specific for this agent.

Respond in JSON only:
{{
    "is_role_specific": true or false,
    "confidence": 0.0 to 1.0,
    "reasoning": "one sentence explanation",
    "violations": ["list any specific should_NOT_do items violated, or empty list"]
}}"""

        try:
            response_text = self._call_llm(prompt)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response_text)
        except Exception as e:
            result = {
                "is_role_specific": None,
                "confidence": 0.0,
                "reasoning": f"Parse error: {e}",
                "violations": [],
            }

        self.cache[cache_key] = result
        return result

    def evaluate_messages(self, agent_name: str, messages: List[str]) -> Dict:
        """Evaluate all messages from one agent."""
        evaluations = []
        on_role = 0
        total_confidence = 0.0

        for i, msg in enumerate(messages):
            print(f"    [{i+1}/{len(messages)}] evaluating {agent_name}...", end="\r")
            result = self.evaluate_message(agent_name, msg)
            evaluations.append(result)
            if result.get("is_role_specific"):
                on_role += 1
            total_confidence += result.get("confidence") or 0.0

        n = len(messages)
        return {
            "agent":              agent_name,
            "total_messages":     n,
            "role_specific_count": on_role,
            "role_adherence_pct": round(on_role / n * 100, 1) if n else 0.0,
            "avg_confidence":     round(total_confidence / n, 3) if n else 0.0,
            "evaluations":        evaluations,
        }

    def evaluate_message_log(self, messages_by_agent: Dict[str, List[str]]) -> Dict:
        """Evaluate all agents from a parsed log."""
        results = {}
        for agent_name, messages in messages_by_agent.items():
            print(f"\n  Evaluating {agent_name.upper()} ({len(messages)} messages)...")
            results[agent_name] = self.evaluate_messages(agent_name, messages)

        total_on_role = sum(r["role_specific_count"] for r in results.values())
        total_msgs    = sum(r["total_messages"] for r in results.values())

        return {
            "results_by_agent":    results,
            "overall_adherence_pct": round(total_on_role / total_msgs * 100, 1) if total_msgs else 0.0,
            "total_messages":      total_msgs,
        }


def print_role_adherence_report(evaluation_result: Dict) -> str:
    lines = ["\n" + "="*70, "ROLE ADHERENCE EVALUATION REPORT", "="*70]
    lines.append(f"\n  Overall Role Adherence : {evaluation_result['overall_adherence_pct']:.1f}%")
    lines.append(f"  Total Messages         : {evaluation_result['total_messages']}\n")

    for agent, res in evaluation_result["results_by_agent"].items():
        lines.append("-"*70)
        lines.append(f"  {agent.upper()}")
        lines.append(f"    Adherence  : {res['role_adherence_pct']:.1f}%  "
                     f"({res['role_specific_count']}/{res['total_messages']} on-role)")
        lines.append(f"    Confidence : {res['avg_confidence']:.2f}")

        violations = [(i, e["violations"]) for i, e in enumerate(res["evaluations"])
                      if e.get("violations")]
        if violations:
            lines.append(f"    Violations : {len(violations)} message(s)")
            for idx, v in violations[:3]:
                lines.append(f"      msg {idx+1}: {v}")

    lines.append("\n" + "="*70)
    return "\n".join(lines)
