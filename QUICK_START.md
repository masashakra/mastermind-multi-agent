# Quick Start Guide - Mastermind AI Solver

## Setup (First Time Only)

```bash
# Install dependencies
pip install z3-solver python-dotenv

# Load Kaggle environment
export KAGGLE_URL=https://flatware-urgent-everglade.ngrok-free.dev
export KAGGLE_MODEL=llama3.1:8b
```

---

## Run Tests

### Option 1: Test Boss-Worker Paradigm (Original)
```bash
python3 test_easy_puzzle.py           # Single easy puzzle
python3 test_boss_worker_kaggle.py    # Multiple puzzles (medium + hard)
```

### Option 2: Test Round-Table Paradigm (NEW)
```bash
python3 test_round_table.py           # Same puzzles, peer-to-peer agents
```

### Option 3: Compare Both (TODO - Create This)
```bash
python3 test_compare_paradigms.py     # Run both on same puzzles, show results
```

---

## Quick Results Interpretation

### If Test Shows "✓ SOLVED"
✅ Success! The system solved the puzzle in N guesses.

### If Test Shows "✗ FAILED"  
⚠️ System ran out of guesses (8 rounds). Shows:
- `Guesses used: X/8` - How many guesses attempted
- `Guess history` - What was tried and feedback received

### Compare Results
```
Boss-Worker:  [Results from test_boss_worker_kaggle.py]
Round-Table:  [Results from test_round_table.py]

Better paradigm = higher success rate, fewer guesses
```

---

## File Structure at a Glance

```
Game System (What to know):
├── 4 Agents (improved with prompts)
│   ├── Analyzer - Extract constraints
│   ├── Proposer - Generate guesses
│   ├── Strategist - Plan strategy
│   └── Validator - Check quality
│
├── 2 Paradigms (implemented)
│   ├── Boss-Worker - Hierarchical
│   └── Round-Table - Peer-to-peer
│
├── Tests (what to run)
│   ├── test_boss_worker_kaggle.py
│   ├── test_round_table.py
│   └── test_agent_reasoning.py (for debugging)
│
└── Docs (for understanding)
    ├── PARADIGM_ARCHITECTURE.md - How each paradigm works
    ├── SYSTEM_OVERVIEW.md - Full architecture
    └── TESTING_GUIDE.md - What to expect
```

---

## What Gets Tested

### Easy Puzzles (4 pegs, 6 colors)
- **Target:** 5-6 guesses
- **Baseline:** 0/10 currently (need fixes)

### Medium Puzzles (5 pegs, 8 colors)
- **Target:** 6-7 guesses
- **Status:** Not tested yet

### Hard Puzzles (6 pegs, 10 colors)
- **Target:** 7-8 guesses
- **Status:** Not tested yet

---

## Key Metrics to Watch

When tests run, look for:

1. **Success Rate** - % of puzzles solved
2. **Average Guesses** - Fewer is better (target 5-6 for easy)
3. **Token Usage** - Lower is cheaper
4. **Execution Time** - Faster is better
5. **Duplicates** - Should be 0 (no repeated guesses)
6. **Violations** - Should be 0 (no constraint breaks)

---

## Next Paradigms (To Implement)

### Competition (Day 6)
- Multiple agents propose guesses
- Pick best
- See if more perspectives help

### Coopetition (Day 7)
- Cooperation phase (extract constraints together)
- Competition phase (each proposes guess)
- Pick best
- Expected to be most efficient

### Experiment (Day 8)
- Try novel approaches
- Variants: Debate, Hierarchical, Vote, Expert-Novice

---

## Troubleshooting

### Test Hangs/Times Out
```
→ Kaggle API might be slow
→ Check internet connection
→ Try again (API sometimes flaky)
```

### Test Fails Immediately
```
→ Check KAGGLE_URL and KAGGLE_MODEL in .env
→ Verify Kaggle backend is running
→ Check logs for LLM error messages
```

### Duplicate Guesses in Output
```
→ Known issue - LLM state management
→ Shows agents aren't remembering previous guesses
→ Affects solver efficiency
```

### All Guesses Same (e.g., Always "red blue green yellow")
```
→ LLM fallback triggered
→ Proposer can't parse LLM response
→ Check agent output with test_agent_reasoning.py
```

---

## Understanding Test Output

```
======================================================================
Testing EASY puzzle: MM_005
Difficulty: easy
Config: 4 pegs, 6 colors
Secret: ['white', 'black', 'black', 'green']
======================================================================

Result: ✓ SOLVED or ✗ FAILED
Guesses used: 5/8                    ← Guesses attempted out of 8 max
Rounds: 5                            ← Rounds executed
Messages: 28                         ← Inter-agent communications
Time: 145.3s                        ← Total execution time

Guess history:
  1. ['red', 'blue', 'green', 'yellow'] → 1 peg, 0 pos
  2. ['white', 'blue', 'green', 'yellow'] → 2 pegs, 1 pos
  ...
  5. ['white', 'black', 'green', 'black'] → 4 pegs, 4 pos ✓
```

**Reading the feedback:**
- `1 peg, 0 pos` = 1 color exists (wrong position), 0 in right position
- `2 pegs, 1 pos` = 2 colors exist total, 1 in right position
- `4 pegs, 4 pos` = 4 colors exist total, 4 in right positions = SOLVED ✓

---

## Commands Summary

```bash
# Test individual paradigms
python3 test_easy_puzzle.py                    # Boss-Worker, 1 puzzle
python3 test_boss_worker_kaggle.py             # Boss-Worker, 3 puzzles
python3 test_round_table.py                    # Round-Table, 3 puzzles

# Debug agent reasoning
python3 test_agent_reasoning.py                # See what agents output
python3 test_round2_reasoning.py               # Deep dive Round 2
python3 test_round3_reasoning.py               # Deep dive Round 3

# Compare paradigms (TODO)
python3 test_compare_paradigms.py              # Side-by-side results
```

---

## What Works Now

✅ **Stable:**
- Game loop (no crashes)
- Agent orchestration (calls work)
- Constraint extraction (mostly correct)
- Guess proposal (generates valid colors)
- Validation (catches some errors)

⚠️ **Issues:**
- Duplicate guesses (agents repeat)
- Model reasoning (Llama 8B limited)
- State management (constraints lost)
- Success rate (0% on easy currently)

---

## Expected Next Steps (Your Decision)

**Option A: Debug Current System**
- Fix duplicate guesses
- Improve constraint memory
- Get easy puzzles solving
- THEN move to other paradigms

**Option B: Continue Building (Current Plan)**
- Test both Boss-Worker and Round-Table
- Build Competition paradigm
- Build Coopetition paradigm
- Let's see which paradigm works best
- THEN optimize

👉 **You chose Option B** - Build full system first, then enhance.

---

## Documentation Structure

For understanding different aspects:

**System Architecture:**
- `SYSTEM_OVERVIEW.md` - High-level overview
- `FILE_STRUCTURE.md` - Code organization

**Paradigms:**
- `PARADIGM_ARCHITECTURE.md` - How each paradigm works
- `MASTER_CHECKLIST.md` - Project status

**Implementation:**
- `IMPLEMENTATION_COMPLETE.md` - What's been done
- `TODAY_PROGRESS.md` - Today's work

**Testing:**
- `TESTING_GUIDE.md` - How to test
- `MASTERMIND_REASONING_GUIDE.md` - How agents should think

---

## Next Action

**Choose one:**

```bash
# A) Test Round-Table paradigm (see how it compares)
python3 test_round_table.py

# B) Implement Competition paradigm (next architecture)
# (Would need to create src/paradigms/competition.py)

# C) Run comprehensive comparison (need test_compare_paradigms.py)
python3 test_compare_paradigms.py
```

What would you like to do next?

