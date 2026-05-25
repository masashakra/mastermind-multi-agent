#!/usr/bin/env python3
"""Comprehensive test suite: Run all 5 paradigms on same puzzle set.

This test allows direct comparison of:
  - Boss-Worker: Hierarchical
  - Round-Table: Peer-to-peer
  - Competition: Multiple analyses
  - Coopetition: Hybrid (cooperation + competition + feedback)
  - Experiment: Iterative refinement

Run this to determine which paradigm performs best.
"""

import sys
from pathlib import Path
import json
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kaggle_setup import load_kaggle_env
load_kaggle_env()

from paradigms.boss_worker import BossWorkerOrchestrator
from paradigms.round_table import RoundTableOrchestrator
from paradigms.judge_mediated import JudgeMediatedOrchestrator
from paradigms.direct_adversarial import DirectAdversarialOrchestrator
from paradigms.moderator_mediated import ModeratorMediatedOrchestrator
from paradigms.direct_debate import DirectDebateOrchestrator
from puzzle_generator import load_puzzles

# Load puzzles
puzzles = load_puzzles()

# Select test puzzles - get one of each difficulty
test_puzzles = {
    "easy": next(p for p in puzzles if p['difficulty'] == 'easy'),
    "medium": next(p for p in puzzles if p['difficulty'] == 'medium'),
    "hard": next(p for p in puzzles if p['difficulty'] == 'hard')
}

# Paradigm orchestrators
PARADIGMS = {
    "boss_worker": BossWorkerOrchestrator,
    "round_table": RoundTableOrchestrator,
    "judge_mediated": JudgeMediatedOrchestrator,
    "direct_adversarial": DirectAdversarialOrchestrator,
    "moderator_mediated": ModeratorMediatedOrchestrator,
    "direct_debate": DirectDebateOrchestrator,
}

print("=" * 90)
print("COMPREHENSIVE PARADIGM COMPARISON TEST")
print("=" * 90)
print(f"Testing {len(PARADIGMS)} paradigms on {len(test_puzzles)} puzzles")
print()

# Results storage
all_results = {}
summary_stats = defaultdict(lambda: {
    "solved": 0,
    "total": 0,
    "total_guesses": 0,
    "total_time": 0,
    "total_tokens": 0,
    "runs": []
})

# Test each paradigm
for paradigm_name, orchestrator_class in PARADIGMS.items():
    print("\n" + "=" * 90)
    print(f"TESTING PARADIGM: {paradigm_name.upper().replace('_', '-')}")
    print("=" * 90)

    paradigm_results = {}

    for difficulty, puzzle in test_puzzles.items():
        print(f"\n  Testing {difficulty.upper()}: {puzzle['puzzle_id']}")
        print(f"  Config: {puzzle['pegs']} pegs, {puzzle['num_colors']} colors")
        print("  " + "-" * 85)

        try:
            orchestrator = orchestrator_class(puzzle, provider="kaggle")
            result = orchestrator.run()

            paradigm_results[difficulty] = result

            # Extract key metrics
            success = result.get('success', False)
            guesses = result.get('guesses', 0)
            tokens = result.get('token_usage', {}).get('total', 0)
            elapsed = result.get('elapsed_time', 0)

            # Update summary stats
            summary_stats[paradigm_name]["total"] += 1
            if success:
                summary_stats[paradigm_name]["solved"] += 1
            summary_stats[paradigm_name]["total_guesses"] += guesses
            summary_stats[paradigm_name]["total_time"] += elapsed
            summary_stats[paradigm_name]["total_tokens"] += tokens
            summary_stats[paradigm_name]["runs"].append({
                "difficulty": difficulty,
                "success": success,
                "guesses": guesses,
                "tokens": tokens,
                "time": elapsed
            })

            # Print result
            status = "✓ SOLVED" if success else "✗ FAILED"
            print(f"    Result: {status}")
            print(f"    Guesses: {guesses}")
            print(f"    Time: {elapsed:.1f}s")
            print(f"    Tokens: {tokens}")

        except Exception as e:
            print(f"    ✗ Error: {e}")
            paradigm_results[difficulty] = {"error": str(e)}
            summary_stats[paradigm_name]["total"] += 1

    all_results[paradigm_name] = paradigm_results

# Print comprehensive summary
print("\n\n" + "=" * 90)
print("SUMMARY COMPARISON TABLE")
print("=" * 90)
print()

# Header
print(f"{'Paradigm':<20} {'Success':<12} {'Avg Guesses':<14} {'Avg Tokens':<14} {'Avg Time':<12}")
print("-" * 90)

# Calculate and display stats for each paradigm
paradigm_stats = {}
for paradigm_name in PARADIGMS.keys():
    stats = summary_stats[paradigm_name]

    solved = stats["solved"]
    total = stats["total"]
    success_rate = f"{solved}/{total}"

    avg_guesses = stats["total_guesses"] / max(1, total) if total > 0 else 0
    avg_tokens = stats["total_tokens"] / max(1, total) if total > 0 else 0
    avg_time = stats["total_time"] / max(1, total) if total > 0 else 0

    paradigm_stats[paradigm_name] = {
        "success_rate": f"{success_rate} ({100*solved/max(1,total):.0f}%)",
        "avg_guesses": avg_guesses,
        "avg_tokens": avg_tokens,
        "avg_time": avg_time,
    }

    print(f"{paradigm_name:<20} {success_rate:<12} {avg_guesses:<14.2f} {avg_tokens:<14.0f} {avg_time:<12.1f}")

print()

# Detailed breakdown by difficulty
print("=" * 90)
print("BREAKDOWN BY DIFFICULTY")
print("=" * 90)

for difficulty in ["easy", "medium", "hard"]:
    print(f"\n{difficulty.upper()} Puzzles:")
    print(f"  {'Paradigm':<20} {'Status':<12} {'Guesses':<10} {'Tokens':<10}")
    print("  " + "-" * 85)

    for paradigm_name in PARADIGMS.keys():
        result = all_results.get(paradigm_name, {}).get(difficulty, {})

        if "error" in result:
            print(f"  {paradigm_name:<20} {'ERROR':<12} {'N/A':<10} {'N/A':<10}")
        else:
            status = "✓ SOLVED" if result.get('success') else "✗ FAILED"
            guesses = result.get('guesses', 'N/A')
            tokens = result.get('token_usage', {}).get('total', 'N/A')
            print(f"  {paradigm_name:<20} {status:<12} {str(guesses):<10} {str(tokens):<10}")

# Ranking
print("\n" + "=" * 90)
print("PARADIGM RANKINGS")
print("=" * 90)

# Rank by success rate
print("\nBy Success Rate:")
ranked = sorted(paradigm_stats.items(), key=lambda x: x[1]['success_rate'].split('(')[1].rstrip('%)')
                , reverse=True)
for i, (name, stats) in enumerate(ranked, 1):
    print(f"  {i}. {name:<20} {stats['success_rate']}")

# Rank by efficiency (tokens per successful guess)
print("\nBy Token Efficiency (tokens / guesses):")
efficiency = {}
for paradigm_name, stats in summary_stats.items():
    if stats["total_guesses"] > 0:
        efficiency[paradigm_name] = stats["total_tokens"] / stats["total_guesses"]
    else:
        efficiency[paradigm_name] = float('inf')

ranked = sorted(efficiency.items(), key=lambda x: x[1])
for i, (name, eff) in enumerate(ranked, 1):
    print(f"  {i}. {name:<20} {eff:.0f} tokens/guess")

# Rank by speed
print("\nBy Speed (avg time per puzzle):")
speed = {name: stats["avg_time"] for name, stats in paradigm_stats.items()}
ranked = sorted(speed.items(), key=lambda x: x[1])
for i, (name, t) in enumerate(ranked, 1):
    print(f"  {i}. {name:<20} {t:.1f}s")

# Overall winner
print("\n" + "=" * 90)
print("OVERALL ASSESSMENT")
print("=" * 90)

best_success = max(paradigm_stats.items(),
                   key=lambda x: float(x[1]['success_rate'].split('(')[1].rstrip('%)')))
best_efficiency = min(efficiency.items(), key=lambda x: x[1] if x[1] != float('inf') else float('inf'))
best_speed = min(speed.items(), key=lambda x: x[1])

print(f"\nBest Success Rate:      {best_success[0]} ({best_success[1]['success_rate']})")
print(f"Best Token Efficiency:  {best_efficiency[0]} ({best_efficiency[1]:.0f} tokens/guess)")
print(f"Fastest:                {best_speed[0]} ({best_speed[1]:.1f}s)")

print("\n" + "=" * 90)
print("PARADIGM DESCRIPTIONS")
print("=" * 90)

descriptions = {
    "boss_worker": "Hierarchical: Central boss coordinates all agents",
    "round_table": "Peer-to-peer: Agents call each other directly without boss",
    "competition": "Multiple analyses: 3 proposers compete, shared analysis redundant",
    "coopetition": "Hybrid: Shared analysis + competing proposals + shared learning",
    "experiment": "Iterative: Analysis → Critique → Proposal → Validation loop",
}

for paradigm, description in descriptions.items():
    print(f"\n{paradigm.upper().replace('_', '-')}:")
    print(f"  {description}")

print("\n" + "=" * 90)
print("CONCLUSION")
print("=" * 90)
print("""
Based on empirical testing:

1. **Best Overall Performer**: See rankings above
2. **Most Efficient**: Uses fewest tokens per guess
3. **Fastest**: Completes puzzles quickest
4. **Best for Production**: Balance of success, efficiency, and speed

Next Steps:
  1. Implement optimizations to winning paradigm
  2. Test on full 30-puzzle set for validation
  3. Consider hybrid approaches if needed
  4. Profile and optimize token usage
  5. Deploy winning paradigm to production
""")

print("\nTest completed at:", Path(__file__).name)
