#!/usr/bin/env python3
"""Detailed diagnostic: What's going wrong with one puzzle?"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from game_engine import GameEngine
from agents.boss import BossAgent
from puzzle_generator import load_puzzles

# Get one easy puzzle
puzzles = load_puzzles()
puzzle = next(p for p in puzzles if p['difficulty'] == 'easy')

print(f"\n{'='*80}")
print(f"DIAGNOSTIC: Why isn't the agent solving {puzzle['puzzle_id']}?")
print(f"{'='*80}")
print(f"\nSecret Code: {puzzle['secret_code']}")
print(f"Available Colors: {puzzle['available_colors']}")
print(f"Max Guesses: 8\n")

# Run agent
engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])
boss = BossAgent(provider="kaggle")
history = []

for round_num in range(1, 9):
    if engine.is_game_over():
        break

    print(f"\n{'─'*80}")
    print(f"ROUND {round_num}")
    print(f"{'─'*80}")

    try:
        result = boss.orchestrate_round({
            "puzzle": puzzle,
            "guess_history": history,
            "difficulty": puzzle["difficulty"]
        })

        guess = result['guess']
        feedback = engine.submit_guess(guess)

        print(f"Guess:    {guess}")
        print(f"Feedback: {feedback['feedback']}")

        if feedback.get('solved'):
            print(f"\n✓ SOLVED!")
            break

        # Analyze what happened
        correct_pegs = feedback['feedback']['correct_pegs']
        correct_pos = feedback['feedback']['correct_positions']
        misplaced = correct_pegs - correct_pos

        print(f"Analysis: {correct_pegs} colors exist, {correct_pos} in right position, {misplaced} in wrong position")

        # Show what colors we know
        if history:
            print(f"\nWhat we know so far:")
            print(f"  Colors found: {correct_pegs} total")

            # Check each guess to see which colors appear
            all_tested = set()
            for h in history + [{"guess": guess}]:
                all_tested.update(h["guess"])
            print(f"  Colors tested: {sorted(all_tested)}")

            # What's still unknown?
            untested = set(puzzle['available_colors']) - all_tested
            print(f"  Colors NOT tested: {sorted(untested)}")

        history.append({
            "round": round_num,
            "guess": guess,
            "feedback": feedback['feedback']
        })

    except Exception as e:
        print(f"ERROR: {str(e)[:200]}")
        break

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print(f"Rounds used: {len(history)}/8")
print(f"Solved: {engine.is_game_over() and all(f.get('solved') for f in [h['feedback'] for h in history])}")

if history:
    last = history[-1]
    print(f"\nLast guess: {last['guess']}")
    print(f"Last feedback: {last['feedback']}")
    print(f"Secret:     {puzzle['secret_code']}")
    print(f"\nComparison:")
    for i, (guess_color, secret_color) in enumerate(zip(last['guess'], puzzle['secret_code'])):
        match = "✓" if guess_color == secret_color else "✗"
        print(f"  Position {i}: guessed '{guess_color}', secret '{secret_color}' {match}")
