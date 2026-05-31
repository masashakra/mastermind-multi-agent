#!/usr/bin/env python3
"""
Validate improved prompt structure without requiring LLM backend.
Tests that prompts contain expected reasoning patterns from research papers.
"""

import sys
from pathlib import Path
import inspect

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.strategist import StrategistAgent
from agents.analyzer import AnalyzerAgent
from agents.proposer import ProposerAgent
from agents.validator import ValidatorAgent

print("\n" + "=" * 70)
print("PROMPT STRUCTURE VALIDATION")
print("Validating literature-informed improvements")
print("=" * 70 + "\n")

# Test data
test_guess_history = [
    {
        "round": 1,
        "guess": ["red", "blue", "green", "yellow"],
        "feedback": {"correct_pegs": 2, "correct_positions": 0}
    },
    {
        "round": 2,
        "guess": ["red", "green", "white", "black"],
        "feedback": {"correct_pegs": 2, "correct_positions": 1}
    }
]

test_last_guess = ["red", "green", "white", "black"]
test_feedback = {"correct_pegs": 2, "correct_positions": 1}
test_available_colors = ["red", "blue", "green", "yellow", "white", "black"]
test_num_pegs = 4

# Validation criteria from research papers
validation_criteria = {
    "Strategist": {
        "Chain-of-Thought": "Step 1",
        "Worked Example": "Reasoning",
        "Phase Identification": "EXPLORATION or CONSTRAINT_BUILDING or REFINEMENT or CONFIRMATION",
        "Reasoning Chain": "reasoning_steps",
    },
    "Analyzer": {
        "Chain-of-Thought": "Step 1",
        "Worked Example": "Last Guess",
        "Step-by-Step Logic": "Step 2",
        "Confidence Scoring": "confidence",
        "5-Step Process": "Step 5",
    },
    "Proposer": {
        "Chain-of-Thought": "Step 1",
        "Worked Example": "Constraints:",
        "Constraint Reasoning": "Step 2",
        "Validation Checklist": "VALIDATION CHECKLIST",
        "5-Step Process": "Step 5",
    },
    "Validator": {
        "Hard vs Soft Constraints": "HARD CONSTRAINTS",
        "Multiple Examples": "EXAMPLE 1",
        "6-Step Process": "Step 1",
        "Validation Steps": "Validation Steps:",
        "Confidence Scoring": "confidence_score",
    }
}

# Test each agent (read source code, don't initialize)
agents = {
    "Strategist": StrategistAgent,
    "Analyzer": AnalyzerAgent,
    "Proposer": ProposerAgent,
    "Validator": ValidatorAgent,
}

results = {}

for agent_name, agent_class in agents.items():
    print(f"\n{'─' * 70}")
    print(f"VALIDATING: {agent_name}")
    print(f"{'─' * 70}\n")

    # Get the agent's prompt by inspecting the method source
    if agent_name == "Strategist":
        method = agent_class.propose_strategy
    elif agent_name == "Analyzer":
        method = agent_class.analyze_feedback
    elif agent_name == "Proposer":
        method = agent_class.propose_guess
    elif agent_name == "Validator":
        method = agent_class.validate_with_llm

    # Get source code
    prompt_text = inspect.getsource(method)

    # Check each validation criterion
    criteria = validation_criteria[agent_name]
    passed = 0
    failed = 0

    for criterion, search_term in criteria.items():
        if search_term in prompt_text:
            print(f"  ✓ {criterion:30} Found: '{search_term}'")
            passed += 1
        else:
            print(f"  ✗ {criterion:30} MISSING: '{search_term}'")
            failed += 1

    results[agent_name] = {"passed": passed, "failed": failed, "total": len(criteria)}

    print(f"\n  Result: {passed}/{len(criteria)} criteria met")

# Summary
print(f"\n{'=' * 70}")
print("SUMMARY")
print(f"{'=' * 70}\n")

total_passed = sum(r["passed"] for r in results.values())
total_failed = sum(r["failed"] for r in results.values())
total_criteria = sum(r["total"] for r in results.values())

for agent_name, result in results.items():
    percentage = (result["passed"] / result["total"]) * 100
    status = "✓" if result["failed"] == 0 else "⚠"
    print(f"{status} {agent_name:15} {result['passed']}/{result['total']:2} ({percentage:5.1f}%)")

print(f"\n{'─' * 70}")
print(f"Overall: {total_passed}/{total_criteria} criteria ({(total_passed/total_criteria)*100:.1f}%)")
print(f"{'─' * 70}\n")

if total_failed == 0:
    print("✓ ALL PROMPTS VALIDATED SUCCESSFULLY")
    print("\nAll agents include literature-informed improvements:")
    print("  • Chain-of-Thought reasoning (Zhang et al., 2024)")
    print("  • Worked examples (Zhang et al., 2024)")
    print("  • Step-by-step constraint reasoning (Adimulam et al., 2026)")
    print("  • Explicit validation frameworks (MultiAgentBench, 2025)")
    print("\nReady for testing with live LLM backend.")
    sys.exit(0)
else:
    print(f"✗ {total_failed} criteria not met")
    print("Review the missing criteria above.")
    sys.exit(1)
