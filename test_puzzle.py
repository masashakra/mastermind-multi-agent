#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
import asyncio
from paradigms.round_table.orchestrator import RoundTableOrchestrator
from puzzle_generator import load_puzzles

# Get puzzle from command line or default to MM_003
puzzle_id = sys.argv[1] if len(sys.argv) > 1 else "MM_003"

puzzles = load_puzzles()
puzzle = next((p for p in puzzles if p['puzzle_id'] == puzzle_id), None)

if not puzzle:
    print(f"Puzzle {puzzle_id} not found")
    sys.exit(1)

print(f"\n{'='*70}")
print(f"Testing: {puzzle_id}")
print(f"Difficulty: {puzzle['difficulty']}")
print(f"Secret: {puzzle['secret_code']}")
print(f"{'='*70}\n")

orchestrator = RoundTableOrchestrator(puzzle, provider='kaggle')
try:
    result = asyncio.run(orchestrator.run())
    print(f"\n✓ FINAL RESULT:")
    print(f"  Success: {result['success']}")
    print(f"  Guesses: {result['guesses']}")
    print(f"  Rounds: {result['rounds']}")
    print(f"  Time: {result['elapsed_time']:.1f}s")
except KeyboardInterrupt:
    print("\n⚠ Interrupted by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
