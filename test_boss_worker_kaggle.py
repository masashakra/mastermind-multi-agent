#!/usr/bin/env python3
"""
Test Boss-Worker paradigm with Kaggle backend.
Run with: python3 test_boss_worker_kaggle.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env

print("=" * 70)
print("BOSS-WORKER PARADIGM TEST WITH KAGGLE BACKEND")
print("=" * 70)

try:
    load_kaggle_env()
    print("\n✓ Kaggle environment loaded")
except Exception as e:
    print(f"\n✗ Failed to load Kaggle env: {e}")
    sys.exit(1)

try:
    from paradigms.boss_worker import BossWorkerOrchestrator
    from puzzle_generator import load_puzzles
    print("✓ Imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

try:
    puzzles = load_puzzles()
    print(f"✓ Loaded {len(puzzles)} puzzles")
except Exception as e:
    print(f"✗ Failed to load puzzles: {e}")
    sys.exit(1)

# Test on first 2 puzzles (1 easy, potentially 1 medium)
test_puzzles = puzzles[:2]

print("\n" + "=" * 70)
print("TESTING BOSS-WORKER ON SAMPLE PUZZLES")
print("=" * 70)

results = []
for idx, puzzle in enumerate(test_puzzles, 1):
    print(f"\n[Test {idx}/{len(test_puzzles)}] Puzzle {puzzle['puzzle_id']} ({puzzle['difficulty']})")
    print(f"  Config: {puzzle['pegs']} pegs, {puzzle['num_colors']} colors")
    print(f"  Secret: {puzzle['secret_code']}")
    print("  Running...")

    try:
        orchestrator = BossWorkerOrchestrator(puzzle, provider="kaggle")
        result = orchestrator.run()

        print(f"  ✓ Completed")
        print(f"    Success: {result['success']}")
        print(f"    Guesses: {result['guesses']}")
        print(f"    Rounds: {result['rounds']}")
        print(f"    Time: {result['elapsed_time']:.2f}s")
        print(f"    Messages: {result['message_count']}")

        results.append({
            "puzzle_id": puzzle["puzzle_id"],
            "difficulty": puzzle["difficulty"],
            "success": result["success"],
            "guesses": result["guesses"],
            "rounds": result["rounds"],
            "time": result["elapsed_time"],
            "messages": result["message_count"]
        })

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            "puzzle_id": puzzle["puzzle_id"],
            "difficulty": puzzle["difficulty"],
            "error": str(e)
        })

# Summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)

for r in results:
    if "error" in r:
        print(f"\n❌ {r['puzzle_id']} ({r['difficulty']}): ERROR - {r['error']}")
    else:
        status = "✓ SOLVED" if r["success"] else "✗ FAILED"
        print(f"\n{status} {r['puzzle_id']} ({r['difficulty']})")
        print(f"    Guesses: {r['guesses']}, Time: {r['time']:.2f}s, Messages: {r['messages']}")

passed = sum(1 for r in results if "error" not in r and r.get("success", False))
total = len(results)

print(f"\n{'='*70}")
print(f"Results: {passed}/{total} puzzles solved")
print(f"{'='*70}\n")

if passed == total:
    print("✓ ALL TESTS PASSED - Ready for Phase 4")
    sys.exit(0)
else:
    print(f"⚠ {total - passed} test(s) failed or unsolved")
    sys.exit(1)
