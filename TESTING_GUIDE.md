# Testing Guide - Mastermind AI Solver

## Puzzle Configuration

### Easy Puzzles (10 total)
- **Pegs:** 4
- **Available Colors:** 6 (red, blue, green, yellow, white, black)
- **Possible Codes:** 6^4 = 1,296
- **Knuth Optimal:** ≤5 guesses
- **Our Target:** 5-6 guesses

### Medium Puzzles (10 total)
- **Pegs:** 5
- **Available Colors:** 8 (red, blue, green, yellow, white, black, purple, orange)
- **Possible Codes:** 8^5 = 32,768
- **Knuth Optimal:** ≤5 guesses
- **Our Target:** 6-7 guesses

### Hard Puzzles (10 total)
- **Pegs:** 6
- **Available Colors:** 10 (red, blue, green, yellow, white, black, purple, orange, pink, brown)
- **Possible Codes:** 10^6 = 1,000,000
- **Knuth Optimal:** ≤5 guesses
- **Our Target:** 7-8 guesses

---

## Test Files

### 1. **test_easy_puzzle.py** - Single Easy Puzzle
```bash
python3 test_easy_puzzle.py
```

**What it tests:**
- Single easy puzzle (first from puzzles.json)
- Full Boss-Worker orchestration
- All agents working together

**Output:**
- Puzzle config
- Secret code (only after test)
- Guess history with feedback
- Success/failure
- Execution time
- Message count

**Expected:**
- ✅ Solve in 5-6 guesses
- ✅ No duplicate guesses
- ✅ Valid color usage
- ✅ Time < 300s

---

### 2. **test_boss_worker_kaggle.py** - Multiple Puzzles
```bash
python3 test_boss_worker_kaggle.py
```

**What it tests:**
- 2 puzzles (medium + hard)
- Full end-to-end solving
- Time efficiency

**Output:**
- Per-puzzle results (guesses, time, success)
- Aggregate statistics
- Agent token usage

**Expected:**
- ✅ Easy: 100% success rate, 5-6 guesses
- ✅ Medium: 50%+ success rate, 6-7 guesses
- ✅ Hard: 20%+ success rate, 7-8 guesses

---

### 3. **Detailed Agent Tests** (For Debugging)

#### test_agent_reasoning.py - Agent Output Analysis
```bash
python3 test_agent_reasoning.py
```
Shows what each agent outputs for a given puzzle state.

#### test_round2_reasoning.py - Round 2 Specific
```bash
python3 test_round2_reasoning.py
```
Deep dive into Round 2 constraint extraction.

#### test_round3_reasoning.py - Round 3 Specific
```bash
python3 test_round3_reasoning.py
```
Deep dive into Round 3 strategy and proposing.

---

## Test Protocol

### Phase 1: Smoke Test (5 min)
```bash
python3 test_easy_puzzle.py
```
- Verify system doesn't crash
- Check basic orchestration
- Look for obvious errors

### Phase 2: Easy Puzzle Batch (15 min)
```python
# Modify test_easy_puzzle.py to run multiple easy puzzles
# Or create test_easy_batch.py

easy_puzzles = [p for p in load_puzzles() if p['difficulty'] == 'easy'][:5]
for puzzle in easy_puzzles:
    orchestrator = BossWorkerOrchestrator(puzzle, provider="kaggle")
    result = orchestrator.run()
    # Track: success, guesses, time
```

**Success Criteria:**
- ✅ 4/5 puzzles solved
- ✅ Avg 5.5 guesses per puzzle
- ✅ No crashes

### Phase 3: All Difficulties (30 min)
```python
# Run all 30 puzzles or representative sample

puzzles = load_puzzles()
results = {
    "easy": [],
    "medium": [],
    "hard": []
}

for puzzle in puzzles:
    orchestrator = BossWorkerOrchestrator(puzzle, provider="kaggle")
    result = orchestrator.run()
    results[puzzle['difficulty']].append(result)
```

**Success Criteria:**
- ✅ Easy: ≥80% success (8/10), avg ≤6 guesses
- ✅ Medium: ≥50% success (5/10), avg ≤7 guesses
- ✅ Hard: ≥20% success (2/10), avg ≤8 guesses

---

## Metrics to Track

### Per-Puzzle Metrics
```json
{
  "puzzle_id": "MM_001",
  "difficulty": "easy",
  "success": true,
  "guesses": 5,
  "rounds": 5,
  "time_seconds": 145.3,
  "valid_guesses": 5,
  "invalid_guesses": 0,
  "constraint_violations": 0,
  "duplicate_guesses": 0
}
```

### Aggregate Metrics
```json
{
  "difficulty": "easy",
  "total_puzzles": 10,
  "solved": 8,
  "success_rate": 0.80,
  "avg_guesses": 5.3,
  "avg_time": 127.5,
  "violations_per_puzzle": 0.2,
  "duplicates_per_puzzle": 0.1
}
```

### Agent Metrics
```json
{
  "agent": "proposer",
  "avg_response_time": 3.2,
  "total_tokens": 15847,
  "avg_tokens_per_call": 437,
  "error_rate": 0.0,
  "fallback_rate": 0.05
}
```

---

## Debugging Protocol

### Issue: Puzzle Not Solved
1. **Check guess history:** Did agents make valid guesses?
2. **Check constraint extraction:** Did Analyzer understand feedback?
3. **Check strategy:** Did Strategist give useful guidance?
4. **Check duplicates:** Are same guesses being repeated?

### Issue: Duplicate Guesses
1. Run test_agent_reasoning.py
2. Check Proposer output for each round
3. Look for state loss (constraints not passed correctly)

### Issue: Invalid Guesses
1. Check Validator output
2. Verify constraints dict is populated
3. Check if colors are valid for puzzle

### Issue: Slow Execution
1. Check token usage per agent
2. Look for excessive LLM calls
3. Check for Kaggle API timeouts

---

## Expected Behavior by Puzzle Difficulty

### Easy Puzzle Behavior (4 pegs, 6 colors)

**Round 1:**
```
Strategist: EXPLORATION - Test diverse colors
Proposer: Generate 4 diverse colors
→ Guess: [red, blue, green, yellow]
→ Feedback: 1-2 colors exist
```

**Rounds 2-3:**
```
Strategist: CONSTRAINT_BUILDING - Test positions
Analyzer: "1 color exists, position unknown"
Proposer: Rearrange to find position and new colors
→ Guess: [white, red, green, yellow]
→ Feedback: 2 colors exist, 1 locked
```

**Rounds 4-5:**
```
Strategist: REFINEMENT - Find remaining colors
Analyzer: "2 colors locked, 2 unknown"
Proposer: Test new colors at unknown positions
→ Guess: [white, black, green, blue]
→ Feedback: 4 colors, 4 locked → SOLVED ✓
```

**Success Pattern:**
- Guesses 1-2: Explore and find colors
- Guesses 3-4: Find positions and missing colors
- Guess 5-6: Confirm final arrangement

---

## What Success Looks Like

### ✅ Good Run (4 pegs, solved in 5)
```
Round 1: [red, blue, green, yellow] → 1 peg, 0 pos
Round 2: [white, blue, green, yellow] → 2 pegs, 1 pos
Round 3: [white, yellow, green, blue] → 2 pegs, 1 pos
Round 4: [white, black, purple, green] → 4 pegs, 3 pos
Round 5: [white, black, green, black] → 4 pegs, 4 pos ✓
```

### ❌ Bad Run (gets stuck)
```
Round 1: [red, blue, green, yellow] → 1 peg, 0 pos
Round 2: [red, blue, green, yellow] → 1 peg, 0 pos ← DUPLICATE!
Round 3: [red, white, green, yellow] → 2 pegs, 0 pos
Round 4: [red, blue, green, yellow] → 1 peg, 0 pos ← DUPLICATE AGAIN!
Round 5-8: Spinning, no progress
```

---

## Running the Full Test Suite

```bash
#!/bin/bash

echo "=== Mastermind AI Solver Test Suite ==="
echo

echo "1. Smoke Test (Easy Puzzle)"
python3 test_easy_puzzle.py
echo

echo "2. Agent Reasoning Test"
python3 test_agent_reasoning.py
echo

echo "3. Round-Specific Tests"
python3 test_round2_reasoning.py
python3 test_round3_reasoning.py
echo

echo "4. Full Boss-Worker Test"
python3 test_boss_worker_kaggle.py
echo

echo "=== Test Suite Complete ==="
```

---

## Acceptance Criteria for System

The system is working well when:

✅ **Easy Puzzles:**
- Solve 80%+ of easy puzzles
- Average 5-6 guesses
- No invalid guesses submitted
- Execution time < 250s per puzzle

✅ **Constraint Handling:**
- Analyzer correctly extracts locked positions
- Proposer respects all constraints
- Validator catches constraint violations
- Zero duplicate guesses in solution

✅ **Efficiency:**
- Each agent responds in <5s
- Total puzzle time <300s per easy puzzle
- Token usage reasonable (<20K per puzzle)

---

## Notes

- All tests use Kaggle backend (Llama 3.1 8B)
- Puzzles loaded from `output/puzzles.json`
- Timing includes LLM API calls (~3-5s per agent call)
- Each puzzle may timeout after 8 rounds
- Failed puzzles logged for debugging

