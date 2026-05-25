#!/usr/bin/env python3
"""Debug what Llama/Kaggle is actually returning."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from agents.proposer import ProposerAgent

print("=" * 70)
print("DEBUGGING LLM RESPONSE FROM KAGGLE")
print("=" * 70)

proposer = ProposerAgent(provider="kaggle")

# Simple test
available_colors = ["red", "blue", "green", "yellow", "white", "black"]
strategy = "Test new color combinations focusing on position 0"
constraints = "No constraints yet - first round"
num_pegs = 4

print(f"\nCalling Proposer.propose_guess()...")
print(f"  Strategy: {strategy}")
print(f"  Constraints: {constraints}")
print(f"  Colors: {available_colors}")
print(f"  Pegs: {num_pegs}")

result = proposer.propose_guess(
    strategy=strategy,
    constraints_text=constraints,
    available_colors=available_colors,
    num_pegs=num_pegs
)

print(f"\nResult from Proposer:")
print(f"  Keys: {list(result.keys())}")
print(f"  proposed_guess: {result.get('proposed_guess')}")
print(f"  Has parse error? {result.get('parse_error')}")
print(f"  Has length_corrected? {result.get('length_corrected')}")
print(f"  Has invalid_colors_fixed? {result.get('invalid_colors_fixed')}")
print(f"\nFull result:")
import json
print(json.dumps(result, indent=2))
