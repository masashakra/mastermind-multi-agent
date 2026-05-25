#!/usr/bin/env python3
"""Test Boss-Worker on a single EASY puzzle to verify basic functionality."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from paradigms.boss_worker import BossWorkerOrchestrator
from puzzle_generator import load_puzzles

puzzles = load_puzzles()

# Get first EASY puzzle (4 pegs, 6 colors)
easy_puzzle = next(p for p in puzzles if p['difficulty'] == 'easy')

print("=" * 70)
print(f"Testing EASY puzzle: {easy_puzzle['puzzle_id']}")
print(f"Difficulty: {easy_puzzle['difficulty']}")
print(f"Config: {easy_puzzle['pegs']} pegs, {easy_puzzle['num_colors']} colors")
print(f"Secret: {easy_puzzle['secret_code']}")
print("=" * 70)
print()

import time
start = time.time()

try:
    orchestrator = BossWorkerOrchestrator(easy_puzzle, provider="kaggle")
    result = orchestrator.run()

    elapsed = time.time() - start

    print(f"\n{'='*70}")
    print(f"Result: {'✓ SOLVED' if result['success'] else '✗ FAILED'}")
    print(f"{'='*70}")
    print(f"Guesses used: {result['guesses']}/{result['rounds']}")
    print(f"Rounds: {result['rounds']}")
    print(f"Messages: {result['message_count']}")
    print(f"Time: {elapsed:.1f}s")
    print(f"\nGuess history:")
    for i, guess in enumerate(result['guess_history'], 1):
        print(f"  {i}. {guess}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
