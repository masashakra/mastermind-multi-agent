#!/usr/bin/env python3
"""Test Moderator-Mediated paradigm on puzzles."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from paradigms.moderator_mediated import ModeratorMediatedOrchestrator
from puzzle_generator import load_puzzles

puzzles = load_puzzles()

test_puzzles = {
    "easy": next(p for p in puzzles if p['difficulty'] == 'easy'),
    "medium": next(p for p in puzzles if p['difficulty'] == 'medium'),
    "hard": next(p for p in puzzles if p['difficulty'] == 'hard')
}

print("=" * 70)
print("MODERATOR-MEDIATED PARADIGM TEST")
print("=" * 70)
print("Coopetition: 3 teams, Moderator synthesizes consensus")
print()

results = {}

for difficulty, puzzle in test_puzzles.items():
    print(f"\nTesting {difficulty.upper()} puzzle: {puzzle['puzzle_id']}")
    print(f"Config: {puzzle['pegs']} pegs, {puzzle['num_colors']} colors")
    print("-" * 70)

    try:
        orchestrator = ModeratorMediatedOrchestrator(puzzle, provider="kaggle")
        result = orchestrator.run()

        results[difficulty] = result

        status = "✓ SOLVED" if result['success'] else "✗ FAILED"
        print(f"Result: {status}")
        print(f"Guesses: {result['guesses']}/{result['rounds']}")
        print(f"Time: {result['elapsed_time']:.1f}s")
        print(f"Messages: {result['message_count']}")
        print(f"Tokens: {result['token_usage']['total']}")

        coop_stats = result.get('coopetition_stats', {})
        print(f"\nCoopetition Stats:")
        print(f"  Consensus rounds: {coop_stats.get('consensus_rounds', 0)}")
        print(f"  Vote rounds: {coop_stats.get('vote_rounds', 0)}")
        print(f"  Total rounds: {coop_stats.get('total_rounds', 0)}")

        if result['guess_history']:
            print(f"\nGuess history:")
            for i, g in enumerate(result['guess_history'], 1):
                fb = g.get('feedback', {})
                decision = g.get('decision', '?')
                print(f"  {i}. [{decision}] {g['guess']} → {fb.get('correct_pegs', 0)} pegs, {fb.get('correct_positions', 0)} pos")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        results[difficulty] = {"error": str(e)}

print("\n" + "=" * 70)
print("MODERATOR-MEDIATED SUMMARY")
print("=" * 70)

for difficulty in ["easy", "medium", "hard"]:
    result = results.get(difficulty, {})
    if "error" in result:
        status = "ERROR"
        guesses = "N/A"
        consensus = "N/A"
    else:
        status = "✓ SOLVED" if result.get('success') else "✗ FAILED"
        guesses = f"{result.get('guesses', 0)}/{result.get('rounds', 0)}"
        coop = result.get('coopetition_stats', {})
        consensus = f"{coop.get('consensus_rounds', 0)} consensus"

    print(f"{difficulty.upper():8} {status:12} Guesses: {guesses:6} {consensus}")

print("\nNote: Moderator-Mediated = 3 teams with centralized Moderator synthesis")
