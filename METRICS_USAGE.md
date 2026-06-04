# Metrics System - Quick Start

## Overview

The metrics system tracks performance across three dimensions:

1. **Task Success** — Solve rate, guesses, failure rate
2. **Communication** — Token usage, message count
3. **Coordination** — Response quality, constraints extracted

## Files

- `src/metrics.py` — Core metrics classes (MetricsCollector, MetricsAggregator)
- `test_round_table_metrics.py` — Test script for round-table paradigm with metrics

## Quick Start

### 1. Test Round-Table Paradigm

```bash
cd /Users/masashakra/Desktop/game
python3 test_round_table_metrics.py
```

This will:
- Solve 3 easy + 2 medium + 1 hard puzzle (~6 puzzles total)
- Collect detailed metrics for each
- Generate a summary report
- Save results to `output/sessions/` and `output/metrics/`

### 2. Example Output

```
======================================================================
ROUND-TABLE SUMMARY
======================================================================

Total puzzles: 6
Success rate: 83.3%
Avg guesses (solved): 5.2 (min: 4, max: 7)
Avg token cost: 9,234 (input: 7,100, output: 2,134)
Tokens per guess: 1,775
Avg messages: 8.5

By Difficulty:
  easy: 100% success, 3 puzzles
  medium: 100% success, 2 puzzles
  hard: 0% success, 1 puzzle

======================================================================
```

## Metrics Collected Per Puzzle

For each puzzle run, the system tracks:

```json
{
  "puzzle_id": "MM_001",
  "paradigm": "round_table",
  "difficulty": "easy",
  "result": {
    "success": true,
    "guesses": 5,
    "rounds": 5,
    "termination_reason": "solution_found"
  },
  "token_usage": {
    "total_input": 7100,
    "total_output": 2134,
    "per_round": [
      {"round": 1, "input": 1800, "output": 500, "total": 2300},
      {"round": 2, "input": 1600, "output": 450, "total": 2050}
    ]
  },
  "round_data": {
    "1": {
      "guess": ["red", "blue", "green", "yellow"],
      "feedback": {"correct_pegs": 2, "correct_positions": 1},
      "response_chars": 1200,
      "model": "gpt-4-turbo"
    }
  },
  "constraints": [
    {
      "round": 1,
      "analysis": {
        "impossible": ["white"],
        "confirmed": ["red", "blue"],
        "locked_positions": 1
      }
    }
  ]
}
```

## Using MetricsCollector in Custom Tests

```python
from metrics import MetricsCollector

# Initialize
metrics = MetricsCollector(
    puzzle_id="MM_001",
    paradigm="my_paradigm",
    difficulty="easy"
)

# During puzzle solving...

# Record a guess
metrics.record_guess(
    round_num=1,
    guess=["red", "blue", "green", "yellow"],
    feedback={"correct_pegs": 2, "correct_positions": 1}
)

# Record LLM response
metrics.record_response(
    round_num=1,
    response_chars=1200,
    model="gpt-4-turbo"
)

# Record token usage
metrics.record_tokens(
    round_num=1,
    input_tokens=1800,
    output_tokens=500
)

# Record constraints
metrics.record_constraints(
    round_num=1,
    analysis={
        "impossible": ["white"],
        "confirmed": ["red", "blue"],
        "locked_positions": 1
    }
)

# When puzzle is solved
metrics.mark_solved(reason="solution_found")

# Save to disk
filepath = metrics.save(output_dir="output/sessions")
print(f"Saved: {filepath}")
```

## Using MetricsAggregator for Summaries

```python
from metrics import MetricsAggregator
import json

# Load sessions from disk
agg = MetricsAggregator()
for json_file in Path("output/sessions").glob("*.json"):
    with open(json_file) as f:
        session = json.load(f)
        agg.add_session(session)

# Get summary
summary = agg.summary()
print(f"Success rate: {summary['success_rate']:.1f}%")
print(f"Avg guesses: {summary['avg_guesses']['avg']:.1f}")

# By difficulty
for difficulty, stats in summary['by_difficulty'].items():
    print(f"{difficulty}: {stats['success_rate']:.0f}% success")

# Save summary
agg.save_summary("round_table")
```

## Comparing Paradigms

Once you have metrics for multiple paradigms, compare them:

```python
from metrics import MetricsAggregator, print_metrics_table
import json

aggregators = {}

for paradigm in ["round_table", "boss_worker", "judge_mediated"]:
    agg = MetricsAggregator()
    for json_file in Path(f"output/sessions/{paradigm}").glob("*.json"):
        with open(json_file) as f:
            agg.add_session(json.load(f))
    aggregators[paradigm] = agg

# Print comparison table
print_metrics_table(aggregators)
```

Output:
```
====================================================================================================
PARADIGM COMPARISON - METRICS SUMMARY
====================================================================================================

Paradigm             Success %     Avg Guesses     Tokens/Guess       Messages  Samples
────────────────────────────────────────────────────────────────────────────────────────
round_table             83.3%             5.2              1775.0         8.5       6
boss_worker             90.0%             4.8              1450.0         4.2       6
judge_mediated          75.0%             6.1              2100.0        12.3       6
====================================================================================================
```

## Output Structure

```
output/
├── sessions/
│   ├── MM_001_round_table.json
│   ├── MM_002_round_table.json
│   └── ... (one JSON per puzzle per paradigm)
└── metrics/
    ├── round_table_summary.json
    ├── boss_worker_summary.json
    └── ... (one summary per paradigm)
```

## Next Steps

1. **Test Round-Table** — Run `test_round_table_metrics.py` to establish baseline
2. **Test Other Paradigms** — Create similar test scripts for other paradigms
3. **Compare Results** — Use aggregator to compare across paradigms
4. **Expand Metrics** — Add more sophisticated metrics (convergence, role adherence) using LLM-Judge

## Notes

- Metrics are saved automatically to `output/sessions/` and `output/metrics/`
- Each puzzle × paradigm combination creates one JSON session file
- Summaries aggregate all sessions for a paradigm
- Token counts require instrumentation in the LLM client (currently approximate)
- Response character counts are tracked from actual LLM responses

## Future Enhancements

The full metrics framework (METRICS_AND_EVALUATION_FRAMEWORK.md) includes:
- LLM-Judge evaluation for wasted communication, role adherence
- Embedding-based semantic analysis (convergence speed)
- Statistical significance testing
- Visualization and reporting

Start with this focused system, then expand as needed.
