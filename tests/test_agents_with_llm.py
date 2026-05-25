# Real LLM Integration Tests
# Tests agents with actual LLM calls (Ollama or Claude)
# NOTE: Requires Ollama running locally OR ANTHROPIC_API_KEY set for Claude
# Run with: python3 tests/test_agents_with_llm.py

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.strategist import StrategistAgent
from agents.analyzer import AnalyzerAgent
from agents.proposer import ProposerAgent
from agents.validator import ValidatorAgent


def test_strategist_with_llm():
    """Test Strategist with real LLM call."""
    print("\n[Strategist LLM Test]")

    try:
        strategist = StrategistAgent(provider="ollama")
        print(f"  Provider: {strategist.provider}")
        print(f"  Model: {strategist.model}")
        print(f"  LLM Type: {type(strategist.llm).__name__}")

        # Call with empty history (first round)
        result = strategist.propose_strategy([], "easy")

        print(f"  ✓ LLM call successful")
        print(f"  Result keys: {list(result.keys())}")

        if "strategy" in result:
            print(f"  Strategy (first 100 chars): {str(result['strategy'])[:100]}...")
            return True
        else:
            print(f"  ✗ Missing 'strategy' key in result")
            return False

    except Exception as e:
        print(f"  ✗ Error: {e}")
        print(f"  Note: Ensure Ollama is running locally or Claude API is configured")
        return False


def test_analyzer_with_llm():
    """Test Analyzer with real LLM call."""
    print("\n[Analyzer LLM Test]")

    try:
        analyzer = AnalyzerAgent(provider="ollama")
        print(f"  Provider: {analyzer.provider}")
        print(f"  Model: {analyzer.model}")

        # Call with feedback
        result = analyzer.analyze_feedback(
            last_guess=["red", "blue", "green", "yellow"],
            feedback={"correct_pegs": 2, "correct_positions": 1}
        )

        print(f"  ✓ LLM call successful")
        print(f"  Result keys: {list(result.keys())}")

        if "constraints" in result:
            print(f"  Constraints: {result['constraints']}")
            return True
        else:
            print(f"  ✗ Missing 'constraints' key")
            return False

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_proposer_with_llm():
    """Test Proposer with real LLM call."""
    print("\n[Proposer LLM Test]")

    try:
        proposer = ProposerAgent(provider="ollama")
        print(f"  Provider: {proposer.provider}")
        print(f"  Model: {proposer.model}")

        # Call with strategy and constraints
        result = proposer.propose_guess(
            strategy="Test new colors",
            constraints_text="Red is in code but not position 0\nBlue locked at position 1",
            available_colors=["red", "blue", "green", "yellow", "white", "black"],
            num_pegs=4
        )

        print(f"  ✓ LLM call successful")
        print(f"  Result keys: {list(result.keys())}")

        if "proposed_guess" in result:
            guess = result["proposed_guess"]
            print(f"  Proposed guess: {guess}")
            print(f"  Guess length: {len(guess)}")
            if len(guess) == 4 and all(c in ["red", "blue", "green", "yellow", "white", "black"] for c in guess):
                print(f"  ✓ Valid guess format")
                return True
            else:
                print(f"  ✗ Invalid guess format")
                return False
        else:
            print(f"  ✗ Missing 'proposed_guess' key")
            return False

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_validator_with_llm():
    """Test Validator with LLM-based validation."""
    print("\n[Validator LLM Test]")

    try:
        validator = ValidatorAgent(provider="ollama")
        print(f"  Provider: {validator.provider}")
        print(f"  Model: {validator.model}")

        # Test with valid guess
        result = validator.validate_guess(
            guess=["red", "blue", "green", "yellow"],
            available_colors=["red", "blue", "green", "yellow", "white", "black"],
            expected_length=4
        )

        print(f"  ✓ Validation successful")
        print(f"  Result keys: {list(result.keys())}")
        print(f"  Is valid: {result.get('is_valid')}")
        print(f"  Ready to submit: {result.get('ready_to_submit')}")

        return result.get("is_valid", False)

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_agent_pipeline_with_llm():
    """Test complete agent pipeline with LLM calls."""
    print("\n[Complete Pipeline LLM Test]")

    try:
        strategist = StrategistAgent(provider="ollama")
        analyzer = AnalyzerAgent(provider="ollama")
        proposer = ProposerAgent(provider="ollama")
        validator = ValidatorAgent(provider="ollama")

        print("  Initialized all 4 agents ✓")

        # Round 1: No history
        print("\n  Round 1 (no history):")
        strategy = strategist.propose_strategy([], "easy")
        print(f"    - Strategist: {list(strategy.keys())}")

        analysis = analyzer.analyze_feedback(
            ["red", "blue", "green", "yellow"],
            {"correct_pegs": 2, "correct_positions": 1}
        )
        print(f"    - Analyzer: {list(analysis.keys())}")

        proposal = proposer.propose_guess(
            strategy.get("strategy", ""),
            str(analysis.get("constraints", [])),
            ["red", "blue", "green", "yellow", "white", "black"],
            4
        )
        print(f"    - Proposer: {list(proposal.keys())}")

        validation = validator.validate_guess(
            proposal.get("proposed_guess", []),
            ["red", "blue", "green", "yellow", "white", "black"],
            4
        )
        print(f"    - Validator: {list(validation.keys())}")

        print(f"\n  ✓ Complete pipeline executed successfully")
        return True

    except Exception as e:
        print(f"  ✗ Error in pipeline: {e}")
        return False


def main():
    """Run all LLM tests."""
    print("="*60)
    print("AGENT LLM INTEGRATION TESTS")
    print("="*60)
    print("\nNOTE: These tests require Ollama running locally")
    print("      Start Ollama with: ollama serve")
    print("      OR set ANTHROPIC_API_KEY for Claude API")

    results = {
        "Strategist": test_strategist_with_llm(),
        "Analyzer": test_analyzer_with_llm(),
        "Proposer": test_proposer_with_llm(),
        "Validator": test_validator_with_llm(),
        "Pipeline": test_agent_pipeline_with_llm()
    }

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name}: {status}")

    print(f"\nTotal: {passed}/{total} tests {'✓ PASSED' if passed == total else '✗ SOME FAILED'}")

    if passed < total:
        print("\nIf tests failed, check:")
        print("  1. Is Ollama running? (ollama serve)")
        print("  2. Is Ollama model available? (ollama pull mistral)")
        print("  3. Or set ANTHROPIC_API_KEY for Claude API")

    print("="*60 + "\n")


if __name__ == "__main__":
    main()
