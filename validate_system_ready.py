#!/usr/bin/env python3
"""
Validate system is ready for testing before spending tokens.
No LLM calls, no API usage - just verify structure and integration.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("\n" + "=" * 70)
print("SYSTEM READINESS VALIDATION")
print("Checking if system is ready for testing")
print("=" * 70 + "\n")

# Track results
checks = {
    "Core Components": [],
    "Game Engine": [],
    "Agents": [],
    "Communication": [],
    "Prompts": [],
}

# Check 1: Core Components
print("1. CORE COMPONENTS")
print("-" * 70)

try:
    from game_engine import GameEngine
    print("  ✓ GameEngine available")
    checks["Core Components"].append(True)
except Exception as e:
    print(f"  ✗ GameEngine: {e}")
    checks["Core Components"].append(False)

try:
    from puzzle_generator import load_puzzles
    puzzles = load_puzzles()
    print(f"  ✓ PuzzleGenerator available ({len(puzzles)} puzzles loaded)")
    checks["Core Components"].append(True)
except Exception as e:
    print(f"  ✗ PuzzleGenerator: {e}")
    checks["Core Components"].append(False)

# Check 2: Game Engine Functionality
print("\n2. GAME ENGINE FUNCTIONALITY")
print("-" * 70)

try:
    test_secret = ["red", "blue", "green", "yellow"]
    game = GameEngine(test_secret, "easy")
    print(f"  ✓ GameEngine instantiation works")

    # Test a guess
    feedback = game.submit_guess(["red", "white", "black", "orange"])
    assert "correct_pegs" in feedback.get("feedback", {})
    assert "correct_positions" in feedback.get("feedback", {})
    print(f"  ✓ Guess submission works")
    print(f"  ✓ Feedback format correct: {feedback['feedback']}")

    checks["Game Engine"].append(True)
    checks["Game Engine"].append(True)
except Exception as e:
    print(f"  ✗ GameEngine error: {e}")
    checks["Game Engine"].append(False)

# Check 3: Agent Loading (without LLM init)
print("\n3. AGENT STRUCTURE")
print("-" * 70)

try:
    from agents.strategist import StrategistAgent
    from agents.analyzer import AnalyzerAgent
    from agents.proposer import ProposerAgent
    from agents.validator import ValidatorAgent

    print("  ✓ All 4 agents importable")
    checks["Agents"].append(True)

    # Check agent methods exist
    assert hasattr(StrategistAgent, 'propose_strategy')
    assert hasattr(AnalyzerAgent, 'analyze_feedback')
    assert hasattr(ProposerAgent, 'propose_guess')
    assert hasattr(ValidatorAgent, 'validate_guess')

    print("  ✓ All agent methods present")
    checks["Agents"].append(True)

except Exception as e:
    print(f"  ✗ Agent loading error: {e}")
    checks["Agents"].append(False)

# Check 4: Communication Layer
print("\n4. COMMUNICATION LAYER")
print("-" * 70)

try:
    from communication.protocol import A2ACommunicationLayer, A2AMessage

    # Create a test communication layer
    comm = A2ACommunicationLayer()
    print("  ✓ A2ACommunicationLayer instantiable")

    # Check message structure
    import uuid
    test_msg = A2AMessage(
        message_id=str(uuid.uuid4()),
        sender_id="test_sender",
        receiver_id="test_receiver",
        message_type="request",
        action="test_action",
        payload={"test": "data"}
    )
    print("  ✓ A2AMessage structure correct")

    checks["Communication"].append(True)
    checks["Communication"].append(True)

except Exception as e:
    print(f"  ✗ Communication error: {e}")
    checks["Communication"].append(False)

# Check 5: Prompt Improvements
print("\n5. PROMPT IMPROVEMENTS")
print("-" * 70)

import inspect

prompt_checks = {
    "Strategist": ("Step 1", "reasoning_steps"),
    "Analyzer": ("Step 1", "Step 5", "confidence"),
    "Proposer": ("VALIDATION CHECKLIST", "Step 1"),
    "Validator": ("HARD CONSTRAINTS", "EXAMPLE 1", "confidence_score"),
}

for agent_name, search_terms in prompt_checks.items():
    try:
        if agent_name == "Strategist":
            method = StrategistAgent.propose_strategy
        elif agent_name == "Analyzer":
            method = AnalyzerAgent.analyze_feedback
        elif agent_name == "Proposer":
            method = ProposerAgent.propose_guess
        else:
            method = ValidatorAgent.validate_with_llm

        source = inspect.getsource(method)

        found_all = all(term in source for term in search_terms)
        if found_all:
            print(f"  ✓ {agent_name:12} has all improvements")
            checks["Prompts"].append(True)
        else:
            missing = [t for t in search_terms if t not in source]
            print(f"  ⚠ {agent_name:12} missing: {missing}")
            checks["Prompts"].append(False)
    except Exception as e:
        print(f"  ✗ {agent_name:12} error: {e}")
        checks["Prompts"].append(False)

# Summary
print("\n" + "=" * 70)
print("READINESS SUMMARY")
print("=" * 70 + "\n")

total_passed = sum(sum(1 for c in checks[k] if c) for k in checks)
total_checks = sum(len(checks[k]) for k in checks)

for category, results in checks.items():
    passed = sum(1 for c in results if c)
    total = len(results)
    status = "✓" if passed == total else "⚠" if passed > 0 else "✗"
    print(f"{status} {category:25} {passed}/{total}")

print(f"\n{'─' * 70}")
print(f"OVERALL: {total_passed}/{total_checks} checks passed")
print(f"{'─' * 70}\n")

if total_passed == total_checks:
    print("✓ SYSTEM READY FOR TESTING")
    print("\nNext steps:")
    print("  1. Set up LLM backend (Groq, Kaggle, or Ollama)")
    print("  2. Run: python3 test_improved_prompts.py")
    print("  3. Test on easy puzzle first")
    print("  4. Monitor token usage")
    print("  5. Expand to medium/hard puzzles")
    sys.exit(0)
else:
    print("⚠ SYSTEM HAS ISSUES")
    print(f"Fix {total_checks - total_passed} failing checks before testing")
    sys.exit(1)
