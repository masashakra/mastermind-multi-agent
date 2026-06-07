#!/usr/bin/env python3
"""
Aggregate and report on all boss-worker easy 30 semantic analyses.
"""

import json
from pathlib import Path
from statistics import mean, median, stdev

def load_analyses(logs_dir):
    """Load all semantic analysis JSON files."""
    analyses = {}
    # Get all semantic analysis files matching the pattern
    analysis_files = list(logs_dir.glob("MM_*_boss_worker_deepseek_messages_semantic_analysis.json"))
    print(f"Found {len(analysis_files)} analysis files")

    for f in sorted(analysis_files):
        # Extract puzzle_id like MM_001 from MM_001_boss_worker_deepseek_messages_semantic_analysis.json
        puzzle_id = "_".join(f.name.split("_")[:2])
        with open(f) as fp:
            analyses[puzzle_id] = json.load(fp)
    return analyses

def aggregate_stats(analyses):
    """Compute aggregate statistics across all puzzles."""

    avg_similarities = []
    reply_rates = []
    all_actions = {}

    for puzzle_id, data in sorted(analyses.items()):
        summary = data.get("summary", {})

        if summary.get("avg_similarity"):
            avg_similarities.append(summary["avg_similarity"])

        if "reply_rate_pct" in summary:
            reply_rates.append(summary["reply_rate_pct"])

        # Aggregate by action
        for action, stats in summary.get("by_action", {}).items():
            if action not in all_actions:
                all_actions[action] = {"total": 0, "got_reply": 0, "scores": []}
            all_actions[action]["total"] += stats.get("total", 0)
            all_actions[action]["got_reply"] += stats.get("got_reply", 0)
            if stats.get("avg_similarity"):
                all_actions[action]["scores"].append(stats["avg_similarity"])

    # Calculate action-level stats
    for action in all_actions:
        if all_actions[action]["scores"]:
            all_actions[action]["avg_similarity"] = round(
                sum(all_actions[action]["scores"]) / len(all_actions[action]["scores"]), 4
            )
        del all_actions[action]["scores"]

    return {
        "num_puzzles": len(analyses),
        "avg_similarity_across_puzzles": round(mean(avg_similarities), 4) if avg_similarities else None,
        "median_similarity": round(median(avg_similarities), 4) if avg_similarities else None,
        "stdev_similarity": round(stdev(avg_similarities), 4) if len(avg_similarities) > 1 else None,
        "min_similarity": round(min(avg_similarities), 4) if avg_similarities else None,
        "max_similarity": round(max(avg_similarities), 4) if avg_similarities else None,
        "avg_reply_rate": round(mean(reply_rates), 1) if reply_rates else None,
        "by_action": all_actions,
    }

def print_report(analyses, stats):
    """Print a comprehensive report."""

    print("\n" + "="*80)
    print("  BOSS-WORKER EASY 30: SEMANTIC ANALYSIS AGGREGATE REPORT")
    print("="*80)

    print(f"\nCOVERAGE:")
    print(f"  Analyzed puzzles: {stats['num_puzzles']}/30")

    if stats['num_puzzles'] == 0:
        print("  No analyses found yet.")
        return

    print(f"\nOVERALL SEMANTIC SIMILARITY:")
    print(f"  Mean:     {stats['avg_similarity_across_puzzles']:.4f}")
    print(f"  Median:   {stats['median_similarity']:.4f}")
    stdev_str = f"{stats['stdev_similarity']:.4f}" if stats['stdev_similarity'] is not None else "N/A"
    print(f"  Stdev:    {stdev_str}")
    print(f"  Range:    {stats['min_similarity']:.4f} — {stats['max_similarity']:.4f}")

    print(f"\nAVERAGE REPLY RATE: {stats['avg_reply_rate']:.1f}%")

    print(f"\nBY ACTION (across all puzzles):")
    for action in sorted(stats['by_action'].keys()):
        act = stats['by_action'][action]
        reply_pct = (act['got_reply'] / act['total'] * 100) if act['total'] > 0 else 0
        avg_sim = act.get('avg_similarity', 'N/A')
        print(f"  {action:<30} {act['got_reply']:3d}/{act['total']:3d} replies ({reply_pct:5.1f}%)  avg_sim={avg_sim}")

    # Per-puzzle summary
    print(f"\nPER-PUZZLE DETAILS:")
    print(f"\n  {'ID':<10} {'Replies':>20} {'Avg Sim':>12} {'Min':>8} {'Max':>8} {'HIGH':>6} {'MEDIUM':>6} {'LOW':>6}")
    print(f"  {'-'*80}")

    for puzzle_id, data in sorted(analyses.items()):
        summary = data.get("summary", {})
        dist = summary.get("distribution", {})
        replies_pct = summary.get("reply_rate_pct", 0)
        avg_sim = summary.get('avg_similarity')
        avg_sim_str = f"{avg_sim:.4f}" if avg_sim else "N/A"
        min_sim = summary.get('min_similarity')
        min_sim_str = f"{min_sim:.4f}" if min_sim else "N/A"
        max_sim = summary.get('max_similarity')
        max_sim_str = f"{max_sim:.4f}" if max_sim else "N/A"

        print(f"  {puzzle_id:<10} {summary.get('got_reply',0):3d}/{summary.get('triggers_response',0):3d} "
              f"({replies_pct:5.1f}%)  {avg_sim_str:>10s}  "
              f"{min_sim_str:>8s}  {max_sim_str:>8s}  "
              f"{dist.get('HIGH',0):6d}  {dist.get('MEDIUM',0):6d}  {dist.get('LOW',0):6d}")

    print("\n" + "="*80 + "\n")

def main():
    logs_dir = Path("logs")

    # Load all analyses
    analyses = load_analyses(logs_dir)

    if not analyses:
        print("No semantic analysis files found. Run analyze_message_pairs.py on boss worker logs first.")
        return

    # Compute aggregate stats
    stats = aggregate_stats(analyses)

    # Print report
    print_report(analyses, stats)

    # Save detailed JSON
    output = {
        "metadata": {
            "num_puzzles": len(analyses),
            "analysis_files": sorted(analyses.keys()),
        },
        "aggregate_statistics": stats,
        "puzzle_details": {
            pid: {
                "summary": data.get("summary", {}),
                "message_count": len(data.get("results", [])),
            }
            for pid, data in analyses.items()
        },
    }

    out_path = "logs/boss_worker_easy30_semantic_analysis_aggregate.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"✅ Detailed results saved to {out_path}")

if __name__ == "__main__":
    main()
