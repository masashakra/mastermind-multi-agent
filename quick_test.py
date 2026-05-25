#!/usr/bin/env python3
"""Quick test of agent improvements with timeout handling."""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from game_engine import GameEngine
from agents.boss import BossAgent
from puzzle_generator import load_puzzles

puzzles = load_puzzles()
test_puzzles = {
    "easy": next(p for p in puzzles if p['difficulty'] == 'easy'),
    "medium": next(p for p in puzzles if p['difficulty'] == 'medium'),
}

results = {}

for difficulty, puzzle in test_puzzles.items():
    print(f"\n{'=' * 70}")
    print(f"Testing {difficulty.upper()}: {puzzle['puzzle_id']}")
    print(f"Secret: {puzzle['secret_code']}")
    print(f"{'=' * 70}")

    try:
        game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])
        boss = BossAgent(provider="kaggle")
        guess_history = []
        start_time = time.time()

        for round_num in range(1, 9):
            if game_engine.is_game_over():
                break

            print(f"\nRound {round_num}:", end=" ", flush=True)

            round_result = boss.orchestrate_round({
                "puzzle": puzzle,
                "guess_history": guess_history,
                "difficulty": puzzle["difficulty"]
            })

            guess = round_result.get("guess", [])
            feedback = game_engine.submit_guess(guess)

            print(f"{guess} → {feedback['feedback']}", flush=True)

            if not feedback.get("valid", False):
                print(f"  ✗ Invalid guess", flush=True)
                continue

            guess_history.append({
                "round": round_num,
                "guess": guess,
                "feedback": feedback.get("feedback", {})
            })

            if feedback.get("solved", False):
                elapsed = time.time() - start_time
                results[difficulty] = {
                    "success": True,
                    "guesses": round_num,
                    "time": elapsed
                }
                print(f"✓ SOLVED!", flush=True)
                break
        else:
            elapsed = time.time() - start_time
            results[difficulty] = {
                "success": False,
                "guesses": len(guess_history),
                "time": elapsed
            }
            print(f"\n✗ FAILED - Ran out of rounds", flush=True)

    except KeyboardInterrupt:
        print("\n✗ INTERRUPTED", flush=True)
        results[difficulty] = {"error": "interrupted"}
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)[:100]}", flush=True)
        results[difficulty] = {"error": str(e)[:100]}

print(f"\n{'=' * 70}")
print("SUMMARY")
print(f"{'=' * 70}")

for difficulty in ["easy", "medium"]:
    result = results.get(difficulty, {})
    if "error" in result:
        print(f"{difficulty.upper():8} ERROR: {result['error']}")
    else:
        status = "✓ SOLVED" if result.get("success") else "✗ FAILED"
        guesses = result.get("guesses", 0)
        time_taken = result.get("time", 0)
        print(f"{difficulty.upper():8} {status:12} Guesses: {guesses}/8  Time: {time_taken:.1f}s")
