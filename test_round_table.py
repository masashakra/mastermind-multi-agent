#!/usr/bin/env python3
"""Test Round-Table paradigm on puzzles to compare with Boss-Worker."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from paradigms.round_table import RoundTableOrchestrator
from core.puzzle_generator import load_puzzles

# Load puzzles
puzzles = load_puzzles()

# Get first 3 puzzles (easy, medium, hard)
test_puzzles = {
    "easy": next(p for p in puzzles if p['difficulty'] == 'easy'),
    "medium": next(p for p in puzzles if p['difficulty'] == 'medium'),
    "hard": next(p for p in puzzles if p['difficulty'] == 'hard')
}

print("=" * 70)
print("ROUND-TABLE PARADIGM TEST")
print("=" * 70)
print()

results = {}

for difficulty, puzzle in test_puzzles.items():
    print(f"\nTesting {difficulty.upper()} puzzle: {puzzle['puzzle_id']}")
    print(f"Config: {puzzle['pegs']} pegs, {puzzle['num_colors']} colors")
    print("-" * 70)

    try:
        orchestrator = RoundTableOrchestrator(puzzle, provider="kaggle")
        result = orchestrator.run()

        results[difficulty] = result

        # Display result
        status = "✓ SOLVED" if result['success'] else "✗ FAILED"
        print(f"Result: {status}")
        print(f"Guesses: {result['guesses']}/{result['rounds']}")
        print(f"Time: {result['elapsed_time']:.1f}s")
        print(f"Messages: {result['message_count']}")
        print(f"Tokens: {result['token_usage']['total']}")

        # Show guess history
        if result['guess_history']:
            print(f"\nGuess history:")
            for i, g in enumerate(result['guess_history'], 1):
                fb = g.get('feedback', {})
                print(f"  {i}. {g['guess']} → {fb.get('correct_pegs', 0)} pegs, {fb.get('correct_positions', 0)} pos")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        results[difficulty] = {"error": str(e)}

# Summary
print("\n" + "=" * 70)
print("ROUND-TABLE SUMMARY")
print("=" * 70)

for difficulty in ["easy", "medium", "hard"]:
    result = results.get(difficulty, {})
    if "error" in result:
        status = "ERROR"
        guesses = "N/A"
    else:
        status = "✓ SOLVED" if result.get('success') else "✗ FAILED"
        guesses = f"{result.get('guesses', 0)}/{result.get('rounds', 0)}"

    print(f"{difficulty.upper():8} {status:12} Guesses: {guesses}")

print("\nNote: Round-Table uses peer-to-peer agent communication.")
print("Compare results with Boss-Worker paradigm.")
