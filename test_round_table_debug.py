#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
import asyncio
import signal
from paradigms.round_table.orchestrator import RoundTableOrchestrator
from puzzle_generator import load_puzzles

def timeout_handler(signum, frame):
    print("\n❌ TIMEOUT - Program took too long!")
    import traceback
    traceback.print_stack(frame)
    sys.exit(1)

# Set 90 second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(90)

puzzles = load_puzzles()
puzzle = next(p for p in puzzles if p['puzzle_id'] == 'MM_001')

orchestrator = RoundTableOrchestrator(puzzle, provider='kaggle')
try:
    result = asyncio.run(orchestrator.run())
    print(f"\n✓ Complete! Result: {result}")
except KeyboardInterrupt:
    print("\n⚠ Interrupted by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    signal.alarm(0)  # Cancel the alarm
