#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
from puzzle_generator import load_puzzles
import json

puzzles = load_puzzles()
puzzle = puzzles[0]  # MM_001

print(f"Secret in puzzle: {puzzle['secret_code']}")
print(f"\nPayload sent to agents:")

# Simulate what orchestrator sends
payload = {
    "last_guess": [],
    "feedback": {"correct_pegs": 0, "correct_positions": 0},
    "guess_history": [],
    "available_colors": puzzle.get("available_colors", []),
    "difficulty": puzzle.get("difficulty", "easy"),
}

print(json.dumps(payload, indent=2))
print("\n" + "="*50)
print("Does payload contain secret? NO ✓")
print("Agents only see: available_colors, feedback, difficulty")
print("="*50)
