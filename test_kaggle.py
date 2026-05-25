#!/usr/bin/env python3
"""
Quick test of Kaggle backend.
Run with: python3 test_kaggle.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env

print("=" * 60)
print("KAGGLE BACKEND TEST")
print("=" * 60)

try:
    load_kaggle_env()
    print("\n✓ Kaggle environment loaded")
except Exception as e:
    print(f"\n✗ Failed to load Kaggle env: {e}")
    sys.exit(1)

try:
    from agents.strategist import StrategistAgent
    agent = StrategistAgent(provider="kaggle")
    print(f"✓ Strategist agent initialized with Kaggle backend")
    print(f"  Provider: {agent.provider}")
    print(f"  Model: {agent.model}")
except Exception as e:
    print(f"✗ Failed to initialize agent: {e}")
    sys.exit(1)

try:
    print("\n[Testing LLM call...]")
    result = agent.propose_strategy([], "easy")
    print(f"✓ LLM call successful!")
    print(f"  Keys in response: {list(result.keys())}")
    if "strategy" in result:
        strategy_preview = str(result["strategy"])[:100]
        print(f"  Strategy: {strategy_preview}...")
    else:
        print(f"  ✗ No 'strategy' key in response")
except Exception as e:
    print(f"✗ LLM call failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ KAGGLE BACKEND WORKING")
print("=" * 60)
