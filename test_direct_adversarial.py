#!/usr/bin/env python3
"""Test Direct Adversarial paradigm on puzzles."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from paradigms.direct_adversarial import DirectAdversarialOrchestrator
from puzzle_generator import load_puzzles

puzzles = load_puzzles()

test_puzzles = {
    "easy": next(p for p in puzzles if p['difficulty'] == 'easy'),
    "medium": next(p for p in puzzles if p['difficulty'] == 'medium'),
    "hard": next(p for p in puzzles if p['difficulty'] == 'hard')
}

print("=" * 70)
print("DIRECT ADVERSARIAL PARADIGM TEST")
print("=" * 70)
print("Competition: 3 teams compete, peer discussion (no judge)")
print()

results = {}

for difficulty, puzzle in test_puzzles.items():
    print(f"\nTesting {difficulty.upper()} puzzle: {puzzle['puzzle_id']}")
    print(f"Config: {puzzle['pegs']} pegs, {puzzle['num_colors']} colors")
    print("-" * 70)

    try:
        orchestrator = DirectAdversarialOrchestrator(puzzle, provider="kaggle")
        result = orchestrator.run()

        results[difficulty] = result

        status = "✓ SOLVED" if result['success'] else "✗ FAILED"
        print(f"Result: {status}")
        print(f"Guesses: {result['guesses']}/{result['rounds']}")
        print(f"Time: {result['elapsed_time']:.1f}s")
        print(f"Messages: {result['message_count']}")
        print(f"Tokens: {result['token_usage']['total']}")

        comp_stats = result.get('competition_stats', {})
        print(f"\nTeam Performance:")
        wins = comp_stats.get('team_wins', {})
        for team_id, win_count in wins.items():
            print(f"  Team {team_id}: {win_count} wins")

        if result['guess_history']:
            print(f"\nGuess history:")
            for i, g in enumerate(result['guess_history'], 1):
                fb = g.get('feedback', {})
                best_team = g.get('best_team', '?')
                print(f"  {i}. [Team {best_team}] {g['guess']} → {fb.get('correct_pegs', 0)} pegs, {fb.get('correct_positions', 0)} pos")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        results[difficulty] = {"error": str(e)}

print("\n" + "=" * 70)
print("DIRECT ADVERSARIAL SUMMARY")
print("=" * 70)

for difficulty in ["easy", "medium", "hard"]:
    result = results.get(difficulty, {})
    if "error" in result:
        status = "ERROR"
        guesses = "N/A"
    else:
        status = "✓ SOLVED" if result.get('success') else "✗ FAILED"
        guesses = f"{result.get('guesses', 0)}/{result.get('rounds', 0)}"

    print(f"{difficulty.upper():8} {status:12} Guesses: {guesses:6}")

print("\nNote: Direct Adversarial = 3 teams compete with peer discussion")
