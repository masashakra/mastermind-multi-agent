#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
import asyncio
from paradigms.round_table.orchestrator import RoundTableOrchestrator
from puzzle_generator import load_puzzles

puzzles = load_puzzles()
puzzle = next(p for p in puzzles if p['puzzle_id'] == 'MM_001')

orchestrator = RoundTableOrchestrator(puzzle, provider='kaggle')
try:
    result = asyncio.run(orchestrator.run())
    print(f"\nFinal result: {result}")
except KeyboardInterrupt:
    print("\nInterrupted")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
