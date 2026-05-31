#!/usr/bin/env python3
"""Test improved agent prompts with Kaggle backend."""

import sys
import os
from pathlib import Path
import time
import json

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load Kaggle env
from kaggle_setup import load_kaggle_env
try:
    load_kaggle_env()
except Exception as e:
    print(f"ERROR: Could not load Kaggle setup: {e}")
    sys.exit(1)

from game_engine import GameEngine
from agents.strategist import StrategistAgent
from agents.analyzer import AnalyzerAgent
from agents.proposer import ProposerAgent
from agents.validator import ValidatorAgent
from puzzle_generator import load_puzzles

# Load one easy puzzle for testing
puzzles = load_puzzles()
test_puzzle = next((p for p in puzzles if p['difficulty'] == 'easy'), None)

if not test_puzzle:
    print("ERROR: No easy puzzle found")
    sys.exit(1)

print(f"\n{'=' * 70}")
print(f"Testing Improved Prompts (Literature-Informed)")
print(f"Provider: Kaggle Backend")
print(f"{'=' * 70}")
print(f"Puzzle: {test_puzzle['puzzle_id']}")
print(f"Secret Code: {test_puzzle['secret_code']}")
print(f"Difficulty: {test_puzzle['difficulty']}")
print(f"{'=' * 70}\n")

try:
    game_engine = GameEngine(test_puzzle["secret_code"], test_puzzle["difficulty"])

    # Initialize agents with Kaggle backend
    strategist = StrategistAgent(provider="kaggle")
    analyzer = AnalyzerAgent(provider="kaggle")
    proposer = ProposerAgent(provider="kaggle")
    validator = ValidatorAgent(provider="kaggle")

    guess_history = []
    start_time = time.time()
    available_colors = test_puzzle.get("colors", ["red", "blue", "green", "yellow", "white", "black"])

    for round_num in range(1, 9):
        if game_engine.is_game_over():
            break

        print(f"\n{'─' * 70}")
        print(f"ROUND {round_num}")
        print(f"{'─' * 70}")

        # Step 1: Strategist analyzes and proposes strategy
        print(f"\n[1/4] Strategist analyzing game state...", end=" ", flush=True)
        strategy_result = strategist.process(
            guess_history=guess_history,
            difficulty=test_puzzle["difficulty"]
        )
        print(f"✓")
        print(f"  Phase: {strategy_result.get('phase', 'unknown')}")
        print(f"  Strategy: {strategy_result.get('strategy', 'N/A')}")

        # Step 2: Analyzer extracts constraints
        if guess_history:
            last_guess_data = guess_history[-1]
            print(f"\n[2/4] Analyzer extracting constraints...", end=" ", flush=True)

            analyzer_result = analyzer.process(
                last_guess=last_guess_data["guess"],
                feedback=last_guess_data["feedback"],
                previous_guesses=guess_history[:-1] if len(guess_history) > 1 else []
            )
            print(f"✓")

            constraints_text = "\n".join(analyzer_result.get("constraints", []))
            print(f"  Constraints identified:")
            for constraint in analyzer_result.get("constraints", []):
                print(f"    - {constraint}")
        else:
            print(f"\n[2/4] Analyzer: First round, no constraints yet ✓")
            constraints_text = "None"

        # Step 3: Proposer generates guess
        print(f"\n[3/4] Proposer generating guess...", end=" ", flush=True)

        proposer_result = proposer.process(
            strategy=strategy_result.get("strategy", ""),
            constraints_text=constraints_text,
            available_colors=available_colors,
            num_pegs=len(test_puzzle["secret_code"])
        )
        print(f"✓")

        guess = proposer_result.get("proposed_guess", [])
        print(f"  Proposed: {guess}")

        # Step 4: Validator validates guess
        print(f"\n[4/4] Validator checking guess...", end=" ", flush=True)

        validation_result = validator.process(
            guess=guess,
            available_colors=available_colors,
            expected_length=len(test_puzzle["secret_code"]),
            previous_guesses=[g["guess"] for g in guess_history],
            use_llm=True
        )
        print(f"✓")

        if not validation_result.get("is_valid", False):
            print(f"\n  ✗ Validation failed: {validation_result.get('errors', ['Unknown error'])}")
            continue

        # Submit guess to game engine
        print(f"\n[SUBMIT] Submitting guess to game...", end=" ", flush=True)
        feedback = game_engine.submit_guess(guess)
        print(f"✓")

        feedback_data = feedback.get("feedback", {})
        print(f"  Feedback: {feedback_data.get('correct_pegs', 0)} colors, {feedback_data.get('correct_positions', 0)} positions")

        guess_history.append({
            "round": round_num,
            "guess": guess,
            "feedback": feedback_data
        })

        # Check if solved
        if feedback.get("solved", False):
            elapsed = time.time() - start_time
            print(f"\n{'=' * 70}")
            print(f"✓ PUZZLE SOLVED in {round_num} guesses!")
            print(f"Time: {elapsed:.1f}s")
            print(f"{'=' * 70}\n")
            break
    else:
        elapsed = time.time() - start_time
        print(f"\n{'=' * 70}")
        print(f"✗ PUZZLE NOT SOLVED - Ran out of rounds")
        print(f"Time: {elapsed:.1f}s")
        print(f"{'=' * 70}\n")

except KeyboardInterrupt:
    print("\n\n✗ Test interrupted by user")
    sys.exit(0)
except Exception as e:
    print(f"\n\n✗ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Print final summary
print(f"\nAgent Call Statistics:")
print(f"  Strategist: {strategist.call_count} calls")
print(f"  Analyzer: {analyzer.call_count} calls")
print(f"  Proposer: {proposer.call_count} calls")
print(f"  Validator: {validator.call_count} calls")
print(f"\nTotal LLM Calls: {strategist.call_count + analyzer.call_count + proposer.call_count + validator.call_count}")
