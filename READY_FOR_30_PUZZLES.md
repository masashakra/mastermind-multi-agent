# ✅ Ready for 30-Puzzle Test Run

Everything needed to run 30 puzzles × 6 paradigms and collect complete metrics is in place.

---

## What's Ready

### 1. **Metrics Collection** ✅
- `src/metrics.py` — MetricsCollector and MetricsAggregator classes
- Captures: success, guesses, tokens, messages, constraints, agent performance
- Stores: puzzle metadata (secret, colors), timestamps, per-round details
- Output: JSON sessions + aggregate summary

### 2. **Token Tracking** ✅
- `src/base/base_agent.py` — Real OpenAI/DeepSeek/Groq token counting
- Tracks: `input_tokens`, `output_tokens` per API call
- Method: `agent.get_token_usage()` returns cumulative usage
- Test script: Calculates per-round delta (no double-counting)

### 3. **Logging Specification** ✅
- `LOGGING_SPECIFICATION.md` — Complete data capture spec
- Lists all fields logged and how to analyze them
- Shows example JSON structure
- Explains how to compute all 9 metrics from logs

### 4. **Log Validation** ✅
- `validate_logs.py` — Check that all required data is present
- Run after collecting logs: `python3 validate_logs.py output/sessions`
- Identifies missing fields, incomplete tracking
- Paradigm-by-paradigm summary

### 5. **Test Templates** ✅
- `test_round_table_metrics.py` — Complete round-table test with metrics
- Ready to adapt for other paradigms
- Auto-saves to `output/sessions/` and `output/metrics/`

---

## Exactly What Gets Logged

### ✅ Task Success Data
```json
"result": {
  "success": true/false,
  "guesses": 5,
  "rounds": 5,
  "termination_reason": "solution_found"
}
```
✓ Can compute: success rate, avg guesses, failure rate

### ✅ Puzzle Metadata
```json
"puzzle_metadata": {
  "secret_code": ["red", "blue", "green", "yellow"],
  "available_colors": [...],
  "pegs": 4
}
```
✓ Can verify: all solutions are correct

### ✅ Token Usage
```json
"token_usage": {
  "total_input": 8234,
  "total_output": 2156,
  "per_round": [
    {"round": 1, "input": 1800, "output": 500},
    {"round": 2, "input": 1600, "output": 450}
  ]
}
```
✓ Can compute: token cost, tokens/guess, efficiency

### ✅ Per-Round Details
```json
"round_data": {
  "1": {
    "guess": ["red", "blue", "green", "yellow"],
    "feedback": {"correct_pegs": 2, "correct_positions": 1},
    "response_chars": 1200,
    "model": "gpt-4-turbo"
  }
}
```
✓ Can analyze: guessing patterns, feedback progression

### ✅ Inter-Agent Messages (for LLM-Judge)
```json
"messages": [
  {
    "timestamp": "2026-06-02T10:30:05.123456",
    "round": 1,
    "sender": "strategist",
    "receiver": "boss",
    "message_type": "strategy_proposal",
    "content": {...}
  }
]
```
✓ Can compute: message count, wasted comm rate, role adherence, coordination score

### ✅ Extracted Constraints
```json
"constraints_extracted": [
  {
    "round": 1,
    "analysis": {
      "impossible": ["white"],
      "confirmed": ["red", "blue"],
      "locked_positions": [...]
    }
  }
]
```
✓ Can analyze: constraint quality, analysis progression

---

## Analysis Capabilities

### Automated (no extra work)
- ✅ Success Rate
- ✅ Avg Guesses
- ✅ Failure Rate
- ✅ Token Cost
- ✅ Tokens/Guess
- ✅ Message Count
- ✅ Constraint Completeness

### LLM-Judge (Claude API, ~$5-10 for all 180)
- ⏳ Wasted Comm Rate
- ⏳ Role Adherence
- ⏳ Coordination Score

### Embedding-based (local, free)
- ⏳ Convergence Speed

**You can run full paper analysis from the logs without re-running puzzles.**

---

## How to Use

### Step 1: Test One Paradigm (5 min)

```bash
cd /Users/masashakra/Desktop/game
python3 test_round_table_metrics.py
```

Output:
```
output/sessions/
  MM_001_round_table.json
  MM_002_round_table.json
  ...
output/metrics/
  round_table_summary.json
```

### Step 2: Validate Logs Are Complete

```bash
python3 validate_logs.py output/sessions
```

Expected output:
```
✅ MM_001_round_table
✅ MM_002_round_table
...
OVERALL: 6/6 valid (100%)
```

If any issues appear → Fix them before running all 30

### Step 3: Run All 30 Puzzles for One Paradigm

Create `test_all_puzzles.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from test_round_table_metrics import solve_puzzle_with_metrics
from puzzle_generator import load_puzzles

puzzles = load_puzzles()
for puzzle in puzzles:  # All 30
    metrics = solve_puzzle_with_metrics(
        puzzle["puzzle_id"],
        paradigm="round_table",
        provider="openai"
    )
    metrics.save()
    print(f"✅ {puzzle['puzzle_id']}")
```

Run:
```bash
python3 test_all_puzzles.py
```

Takes ~30-45 min per paradigm (depends on tokens, parallelization)

### Step 4: Repeat for Other 5 Paradigms

Copy and adapt `test_all_puzzles.py` for:
- `boss_worker`
- `judge_mediated`
- `round_table_request_response`
- (2 more paradigms)

### Step 5: Validate All 180 Sessions

```bash
python3 validate_logs.py output/sessions
```

Expected:
```
OVERALL: 180/180 valid (100%)
```

### Step 6: Analyze

Load all 180 and compute metrics (from LOGGING_SPECIFICATION.md):

```python
import glob, json
from metrics import MetricsAggregator

sessions_by_paradigm = {}
for json_file in glob.glob("output/sessions/*.json"):
    with open(json_file) as f:
        session = json.load(f)
        paradigm = session["paradigm"]
        if paradigm not in sessions_by_paradigm:
            sessions_by_paradigm[paradigm] = []
        sessions_by_paradigm[paradigm].append(session)

# Compute all metrics per paradigm
results = {}
for paradigm, sessions in sessions_by_paradigm.items():
    agg = MetricsAggregator()
    for s in sessions:
        agg.add_session(s)
    results[paradigm] = agg.summary()

# Print results
for paradigm, summary in results.items():
    print(f"\n{paradigm}:")
    print(f"  Success: {summary['success_rate']:.1f}%")
    print(f"  Avg guesses: {summary['avg_guesses']['avg']:.1f}")
    print(f"  Tokens/guess: {summary['avg_tokens']['per_guess']:.0f}")
```

---

## What to Do Now

### ✅ Option A: Test Round-Table First (Recommended)

```bash
python3 test_round_table_metrics.py
python3 validate_logs.py output/sessions
```

**Expected:** 6 valid sessions in ~2 min, validates without errors

If this works → You're ready for full 30-puzzle run

### ✅ Option B: Run Full 30-Puzzle Test Immediately

1. Create `test_all_puzzles.py` (template above)
2. Run: `python3 test_all_puzzles.py`
3. Wait ~1 hour
4. Validate: `python3 validate_logs.py output/sessions`
5. Check results: `ls -la output/sessions/ | wc -l` (should be 30)

---

## Files You Now Have

```
game/
├── src/
│   ├── metrics.py                      ✨ NEW - Metrics collection
│   └── base/base_agent.py              ✨ UPDATED - Token tracking
├── test_round_table_metrics.py         ✨ NEW - Paradigm test template
├── validate_logs.py                    ✨ NEW - Log validation
├── TOKEN_TRACKING.md                   📖 Documentation
├── LOGGING_SPECIFICATION.md            📖 Complete logging spec
├── METRICS_USAGE.md                    📖 Metrics how-to
└── READY_FOR_30_PUZZLES.md             📖 This file

output/
├── sessions/                           📁 Auto-created (180 JSON files)
└── metrics/                            📁 Auto-created (summaries)
```

---

## Checklist Before Running

- [ ] `src/metrics.py` exists ✓
- [ ] `src/base/base_agent.py` has token tracking ✓
- [ ] `test_round_table_metrics.py` updated with puzzle metadata ✓
- [ ] `validate_logs.py` created ✓
- [ ] `LOGGING_SPECIFICATION.md` reviewed ✓
- [ ] Ready to test!

---

## Expected Output After 30 Puzzles

```
output/sessions/
├── MM_001_paradigm_1.json      (puzzle 1, paradigm 1)
├── MM_001_paradigm_2.json      (puzzle 1, paradigm 2)
├── ...
├── MM_030_paradigm_5.json      (puzzle 30, paradigm 5)
└── MM_030_paradigm_6.json      (puzzle 30, paradigm 6)
                                → 180 total files

output/metrics/
├── paradigm_1_summary.json
├── paradigm_2_summary.json
├── ...
└── paradigm_6_summary.json
                                → 6 summaries
```

Each session JSON has:
- Puzzle metadata (for verification)
- All messages (for LLM-Judge)
- Token usage (for efficiency)
- Per-round details (for analysis)
- Constraints (for quality assessment)
- **Everything needed for paper** ✅

---

## Next: Actual Run

You're **100% ready** to run puzzles and collect data.

**Recommended:** Test with `python3 test_round_table_metrics.py` first (2 min), validate it works, then scale to all 30 puzzles.

Want to proceed? 🚀
