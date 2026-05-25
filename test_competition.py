#!/usr/bin/env python3
"""Test Competition paradigm on puzzles to compare with Boss-Worker and Round-Table."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from paradigms.competition import CompetitionOrchestrator
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
print("COMPETITION PARADIGM TEST")
print("=" * 70)
print("Multiple proposers compete for best guess")
print()

results = {}

for difficulty, puzzle in test_puzzles.items():
    print(f"\nTesting {difficulty.upper()} puzzle: {puzzle['puzzle_id']}")
    print(f"Config: {puzzle['pegs']} pegs, {puzzle['num_colors']} colors")
    print("-" * 70)

    try:
        orchestrator = CompetitionOrchestrator(puzzle, provider="kaggle")
        result = orchestrator.run()

        results[difficulty] = result

        # Display result
        status = "✓ SOLVED" if result['success'] else "✗ FAILED"
        print(f"Result: {status}")
        print(f"Guesses: {result['guesses']}/{result['rounds']}")
        print(f"Time: {result['elapsed_time']:.1f}s")
        print(f"Messages: {result['message_count']}")
        print(f"Tokens: {result['token_usage']['total']}")

        # Competition stats
        comp_stats = result.get('competition_stats', {})
        print(f"\nCompetition Stats:")
        print(f"  Most effective proposer: {comp_stats.get('most_effective', 'unknown')}")
        wins = comp_stats.get('proposer_wins', {})
        for name, count in wins.items():
            rate = comp_stats.get('win_rates', {}).get(name, 0) * 100
            print(f"    {name.capitalize():12} {count} wins ({rate:.1f}%)")

        # Show guess history with winner
        if result['guess_history']:
            print(f"\nGuess history (winner noted):")
            for i, g in enumerate(result['guess_history'], 1):
                fb = g.get('feedback', {})
                winner = g.get('winner', '?')
                print(f"  {i}. [{winner[0].upper()}] {g['guess']} → {fb.get('correct_pegs', 0)} pegs, {fb.get('correct_positions', 0)} pos")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        results[difficulty] = {"error": str(e)}

# Summary
print("\n" + "=" * 70)
print("COMPETITION SUMMARY")
print("=" * 70)

for difficulty in ["easy", "medium", "hard"]:
    result = results.get(difficulty, {})
    if "error" in result:
        status = "ERROR"
        guesses = "N/A"
        proposer = "N/A"
    else:
        status = "✓ SOLVED" if result.get('success') else "✗ FAILED"
        guesses = f"{result.get('guesses', 0)}/{result.get('rounds', 0)}"
        comp = result.get('competition_stats', {})
        proposer = comp.get('most_effective', 'N/A')

    print(f"{difficulty.upper():8} {status:12} Guesses: {guesses:6} Best: {proposer.capitalize()}")

print("\nNote: Competition paradigm has 3 proposers compete per round.")
print("Compare results with Boss-Worker and Round-Table paradigms.")
print("Expected: More guesses (multiple proposers) but potentially better selection.")
