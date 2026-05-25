#!/usr/bin/env python3
"""Debug script to trace agent reasoning for one puzzle."""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from game_engine import GameEngine
from agents.strategist import StrategistAgent
from agents.analyzer import AnalyzerAgent
from agents.proposer import ProposerAgent
from agents.validator import ValidatorAgent
from puzzle_generator import load_puzzles

# Load easy puzzle for debugging
puzzles = load_puzzles()
puzzle = next(p for p in puzzles if p['difficulty'] == 'easy')

print("=" * 80)
print(f"DEBUGGING PUZZLE: {puzzle['puzzle_id']} (EASY)")
print(f"Config: {puzzle['pegs']} pegs, {puzzle['num_colors']} colors")
print(f"Available colors: {puzzle['available_colors']}")
print("=" * 80)

# Initialize agents
strategist = StrategistAgent(provider="kaggle")
analyzer = AnalyzerAgent(provider="kaggle")
proposer = ProposerAgent(provider="kaggle")
validator = ValidatorAgent(provider="kaggle")
game_engine = GameEngine(puzzle["secret_code"], puzzle["difficulty"])

guess_history = []

# ROUND 1
print("\n" + "=" * 80)
print("ROUND 1: EXPLORATION")
print("=" * 80)

strategy = strategist.propose_strategy(guess_history, puzzle["difficulty"])
print(f"\n1. STRATEGIST OUTPUT:")
print(f"   Phase: {strategy.get('phase')}")
print(f"   Strategy: {strategy.get('strategy')}")
print(f"   Confidence: {strategy.get('confidence')}")

proposal = proposer.propose_guess(
    strategy=strategy.get("strategy", ""),
    constraints_text="No constraints yet",
    available_colors=puzzle["available_colors"],
    num_pegs=puzzle["pegs"],
    previous_guesses=[]
)
print(f"\n2. PROPOSER OUTPUT:")
print(f"   Proposed guess: {proposal.get('proposed_guess')}")
print(f"   Justification: {proposal.get('justification')}")

# Submit guess
guess_1 = proposal.get('proposed_guess')
feedback_1 = game_engine.submit_guess(guess_1)
print(f"\n3. GAME ENGINE FEEDBACK:")
print(f"   Guess: {guess_1}")
print(f"   Feedback: {feedback_1.get('feedback')}")
print(f"   Solved: {feedback_1.get('solved')}")

# Add to history
guess_history.append({
    "round": 1,
    "guess": guess_1,
    "feedback": feedback_1.get("feedback", {})
})

# ROUND 2
print("\n" + "=" * 80)
print("ROUND 2: CONSTRAINT BUILDING")
print("=" * 80)

analysis = analyzer.analyze_feedback(
    guess_history[-1]["guess"],
    guess_history[-1]["feedback"],
    guess_history[:-1]
)
print(f"\n1. ANALYZER OUTPUT:")
print(f"   Locked positions: {analysis.get('correct_positions')}")
print(f"   Misplaced colors: {analysis.get('correct_colors_wrong_position')}")
print(f"   Impossible colors: {analysis.get('impossible_colors')}")
print(f"   Constraints:")
for constraint in analysis.get('constraints', []):
    print(f"     - {constraint}")

strategy = strategist.propose_strategy(guess_history, puzzle["difficulty"])
print(f"\n2. STRATEGIST OUTPUT (ROUND 2):")
print(f"   Phase: {strategy.get('phase')}")
print(f"   Analysis: {strategy.get('analysis')}")
print(f"   Strategy: {strategy.get('strategy')}")
print(f"   Confidence: {strategy.get('confidence')}")

constraints_text = "\n".join(analysis.get('constraints', [])) if analysis.get('constraints') else "No constraints"
proposal = proposer.propose_guess(
    strategy=strategy.get("strategy", ""),
    constraints_text=constraints_text,
    available_colors=puzzle["available_colors"],
    num_pegs=puzzle["pegs"],
    previous_guesses=[g["guess"] for g in guess_history]
)
print(f"\n3. PROPOSER OUTPUT (ROUND 2):")
print(f"   Proposed guess: {proposal.get('proposed_guess')}")
print(f"   Justification: {proposal.get('justification')}")

# Submit guess
guess_2 = proposal.get('proposed_guess')
feedback_2 = game_engine.submit_guess(guess_2)
print(f"\n4. GAME ENGINE FEEDBACK:")
print(f"   Guess: {guess_2}")
print(f"   Feedback: {feedback_2.get('feedback')}")
print(f"   Solved: {feedback_2.get('solved')}")

guess_history.append({
    "round": 2,
    "guess": guess_2,
    "feedback": feedback_2.get("feedback", {})
})

# ROUND 3
if not feedback_2.get('solved'):
    print("\n" + "=" * 80)
    print("ROUND 3: REFINEMENT")
    print("=" * 80)

    analysis = analyzer.analyze_feedback(
        guess_history[-1]["guess"],
        guess_history[-1]["feedback"],
        guess_history[:-1]
    )
    print(f"\n1. ANALYZER OUTPUT:")
    print(f"   Locked positions: {analysis.get('correct_positions')}")
    print(f"   Misplaced colors: {analysis.get('correct_colors_wrong_position')}")
    print(f"   Impossible colors: {analysis.get('impossible_colors')}")
    print(f"   Constraints:")
    for constraint in analysis.get('constraints', []):
        print(f"     - {constraint}")

    strategy = strategist.propose_strategy(guess_history, puzzle["difficulty"])
    print(f"\n2. STRATEGIST OUTPUT (ROUND 3):")
    print(f"   Phase: {strategy.get('phase')}")
    print(f"   Analysis: {strategy.get('analysis')}")
    print(f"   Strategy: {strategy.get('strategy')}")
    print(f"   Confidence: {strategy.get('confidence')}")

    constraints_text = "\n".join(analysis.get('constraints', [])) if analysis.get('constraints') else "No constraints"
    proposal = proposer.propose_guess(
        strategy=strategy.get("strategy", ""),
        constraints_text=constraints_text,
        available_colors=puzzle["available_colors"],
        num_pegs=puzzle["pegs"],
        previous_guesses=[g["guess"] for g in guess_history]
    )
    print(f"\n3. PROPOSER OUTPUT (ROUND 3):")
    print(f"   Proposed guess: {proposal.get('proposed_guess')}")
    print(f"   Justification: {proposal.get('justification')}")

    # Submit guess
    guess_3 = proposal.get('proposed_guess')
    feedback_3 = game_engine.submit_guess(guess_3)
    print(f"\n4. GAME ENGINE FEEDBACK:")
    print(f"   Guess: {guess_3}")
    print(f"   Feedback: {feedback_3.get('feedback')}")
    print(f"   Solved: {feedback_3.get('solved')}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Secret code: {puzzle['secret_code']}")
print(f"Total guesses: {len(guess_history)}")
for i, g in enumerate(guess_history, 1):
    print(f"  Round {i}: {g['guess']} → {g['feedback']}")
