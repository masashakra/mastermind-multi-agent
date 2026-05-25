#!/usr/bin/env python3
"""Test to see agent reasoning after round 2 (when we found 2 pegs)"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from agents.analyzer import AnalyzerAgent
from agents.proposer import ProposerAgent
from agents.strategist import StrategistAgent

# After round 2: guess = ['black', 'blue', 'green', 'yellow'], feedback = 2 pegs, 0 positions
# Secret: ['white', 'black', 'black', 'green']

guess_history = [
    {
        "round": 1,
        "guess": ['red', 'blue', 'green', 'yellow'],
        "feedback": {'correct_pegs': 1, 'correct_positions': 0}
    },
    {
        "round": 2,
        "guess": ['black', 'blue', 'green', 'yellow'],
        "feedback": {'correct_pegs': 2, 'correct_positions': 0}
    }
]

available_colors = ["red", "blue", "green", "yellow", "white", "black"]
num_pegs = 4

print("=" * 70)
print("Testing Agent Reasoning for Mastermind Round 3 (after round 2)")
print("=" * 70)
print("\nGuess History:")
for g in guess_history:
    print(f"  {g['guess']} → pegs={g['feedback']['correct_pegs']}, pos={g['feedback']['correct_positions']}")

# Step 1: Strategist
print("\n" + "=" * 70)
print("STEP 1: STRATEGIST")
print("=" * 70)
strategist = StrategistAgent(provider="kaggle")
strategy_result = strategist.propose_strategy(guess_history, "easy")
print(f"\nStrategy: {strategy_result.get('strategy', 'N/A')}")
print(f"Reasoning: {strategy_result.get('reasoning', 'N/A')}")

# Step 2: Analyzer
print("\n" + "=" * 70)
print("STEP 2: ANALYZER (analyzing round 2 feedback)")
print("=" * 70)
analyzer = AnalyzerAgent(provider="kaggle")
last_guess = guess_history[-1]
analysis = analyzer.analyze_feedback(
    last_guess.get("guess", []),
    last_guess.get("feedback", {}),
    guess_history[:-1]
)
print(f"\nLocked Positions: {analysis.get('correct_positions', [])}")
print(f"Misplaced Colors: {analysis.get('correct_colors_wrong_position', [])}")
print(f"Impossible Colors: {analysis.get('impossible_colors', [])}")
print(f"Constraints:")
for c in analysis.get('constraints', []):
    print(f"  - {c}")
print(f"Estimated Remaining: {analysis.get('estimated_remaining', 'N/A')}")

# Step 3: Proposer
print("\n" + "=" * 70)
print("STEP 3: PROPOSER (proposing round 3 guess)")
print("=" * 70)
constraints_text = "\n".join(analysis.get('constraints', [])) if analysis.get('constraints') else "No constraints yet"
proposer = ProposerAgent(provider="kaggle")
proposal = proposer.propose_guess(
    strategy=strategy_result.get("strategy", ""),
    constraints_text=constraints_text,
    available_colors=available_colors,
    num_pegs=num_pegs,
    previous_guesses=[g.get("guess", []) for g in guess_history]
)
print(f"\nProposed Guess: {proposal.get('proposed_guess', [])}")
print(f"Justification: {proposal.get('justification', 'N/A')}")
print(f"Expected Outcome: {proposal.get('expected_outcome', 'N/A')}")
if 'duplicate_guess_fixed' in proposal:
    print(f"\n✓ Duplicate guess fixed: {proposal.get('fix_reason')}")
if 'locked_violations_fixed' in proposal:
    print(f"\n⚠️  Locked violations fixed: {proposal.get('locked_violations_fixed')}")
