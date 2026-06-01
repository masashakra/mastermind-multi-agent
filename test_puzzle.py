#!/usr/bin/env python3
import sys, os
sys.path.insert(0, 'src')
import asyncio

# Load .env.groq if it exists
_env_file = os.path.join(os.path.dirname(__file__), '.env.groq')
if os.path.exists(_env_file):
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                if _v.strip() and 'your_key' not in _v:
                    os.environ.setdefault(_k.strip(), _v.strip())

from paradigms.round_table.orchestrator import RoundTableOrchestrator
from puzzle_generator import load_puzzles

# Get puzzle and provider from command line
puzzle_id = sys.argv[1] if len(sys.argv) > 1 else "MM_002"
provider  = sys.argv[2] if len(sys.argv) > 2 else "groq"

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

print(f"Provider: {provider}")
orchestrator = RoundTableOrchestrator(puzzle, provider=provider)
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
