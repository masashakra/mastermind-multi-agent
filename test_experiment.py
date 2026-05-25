#!/usr/bin/env python3
"""Test Experiment paradigm on puzzles - the iterative refinement approach."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from paradigms.experiment import ExperimentOrchestrator
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
print("EXPERIMENT PARADIGM TEST")
print("=" * 70)
print("Iterative refinement: analysis → critique → proposal → validation loop")
print()

results = {}

for difficulty, puzzle in test_puzzles.items():
    print(f"\nTesting {difficulty.upper()} puzzle: {puzzle['puzzle_id']}")
    print(f"Config: {puzzle['pegs']} pegs, {puzzle['num_colors']} colors")
    print("-" * 70)

    try:
        orchestrator = ExperimentOrchestrator(puzzle, provider="kaggle")
        result = orchestrator.run()

        results[difficulty] = result

        # Display result
        status = "✓ SOLVED" if result['success'] else "✗ FAILED"
        print(f"Result: {status}")
        print(f"Guesses: {result['guesses']}/{result['rounds']}")
        print(f"Time: {result['elapsed_time']:.1f}s")
        print(f"Messages: {result['message_count']}")
        print(f"Tokens: {result['token_usage']['total']}")

        # Experiment stats
        exp_stats = result.get('experiment_stats', {})
        print(f"\nExperiment Stats (Iterative Refinement):")
        print(f"  Total refinement iterations: {exp_stats.get('total_refinements', 0)}")
        print(f"  Rounds with refinement:      {exp_stats.get('rounds_with_refinement', 0)}")
        print(f"  Rounds without refinement:   {exp_stats.get('rounds_without_refinement', 0)}")
        print(f"  Avg refinements per round:   {exp_stats.get('avg_refinements_per_round', 0):.2f}")

        # Show refinement iterations by round
        if exp_stats.get('refinement_iterations'):
            print(f"\nRefinement history:")
            for r in exp_stats.get('refinement_iterations', []):
                print(f"  Round {r['round']}: {r['iterations']} iteration(s)")

        # Show guess history with refinement count
        if result['guess_history']:
            print(f"\nGuess history (refinement count noted):")
            for i, g in enumerate(result['guess_history'], 1):
                fb = g.get('feedback', {})
                ref = g.get('refinement_iterations', 0)
                ref_str = f"[R{ref}]" if ref > 0 else "[R0]"
                print(f"  {i}. {ref_str} {g['guess']} → {fb.get('correct_pegs', 0)} pegs, {fb.get('correct_positions', 0)} pos")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        results[difficulty] = {"error": str(e)}

# Summary
print("\n" + "=" * 70)
print("EXPERIMENT SUMMARY")
print("=" * 70)

for difficulty in ["easy", "medium", "hard"]:
    result = results.get(difficulty, {})
    if "error" in result:
        status = "ERROR"
        guesses = "N/A"
        refinements = "N/A"
    else:
        status = "✓ SOLVED" if result.get('success') else "✗ FAILED"
        guesses = f"{result.get('guesses', 0)}/{result.get('rounds', 0)}"
        exp = result.get('experiment_stats', {})
        refinements = f"{exp.get('total_refinements', 0)} total"

    print(f"{difficulty.upper():8} {status:12} Guesses: {guesses:6} Refinements: {refinements}")

print("\nNote: Experiment paradigm uses iterative refinement with validation loop.")
print("Strategy: Analysis → Critique → Proposal → Validation (with one refinement iteration if needed)")
print("Compare with Boss-Worker, Round-Table, Competition, and Coopetition paradigms.")
