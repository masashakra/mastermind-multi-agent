# Agent Memory - Quick Reference

## What Changed?

Agents now have **persistent memory** of their own reasoning across rounds.

### Before
- Agent sees: guess_history + last_feedback
- Missing: "What did I think before? What strategy worked?"

### After  
- Agent sees: guess_history + **analysis_history** + last_feedback
- Memory shows: "Round 6: I guessed [y,b,g,b] and got 4p+3pos!"

---

## How It Works (Flow)

```
Round 6:
  1. Agent thinks + analyzes
  2. Agent guesses [y,b,g,b] 
  3. Gets result: 4p+3pos ✓✓✓ BREAKTHROUGH
  4. Orchestrator stores: {R6, guess, analysis, strategy, feedback}

Round 7:
  1. Orchestrator passes: analysis_history = [R5, R6 results]
  2. Agent reads: "R6: [y,b,g,b] → 4p+3pos" 
  3. Agent thinks: "We're 1 peg away! Build on this!"
  4. Agent guesses smarter permutation
  5. Should solve or get very close!
```

---

## Implementation Summary

### 3 Files Changed

**1. orchestrator.py**
```python
self.team_analysis_histories = {}  # Track per team
# Pass to agents
"analysis_history": self.team_analysis_histories[team_id]
# Store after each round
self.team_analysis_histories[team_id].append({...})
```

**2. team_agent.py**
```python
def solve_round(
    guess_history,
    analysis_history=None,  # NEW PARAM
    last_feedback=None,
    ...
)

# Build memory context
if analysis_history:
    for entry in analysis_history[-2:]:  # Last 2 rounds
        display: f"R{n}: {guess} → {pegs}p+{positions}pos"
```

**3. agent_server.py**
```python
result = agent.solve_round(
    analysis_history=payload.get("analysis_history", []),  # NEW
    ...
)
```

---

## Expected Results

### Hypothesis
- **Before Memory**: Round 7 resets, puzzle unsolved
- **After Memory**: Round 7 builds on R6 success, puzzle solved R8 or earlier

### Success Criteria
✅ Completes all 8 rounds without timeouts
✅ Shows improved strategy progression  
✅ Recognizes breakthrough moments (3p+3pos in R6 → builds in R7)
✅ Solves puzzle or gets closer than baseline

---

## Data Format

### What Gets Stored
```
Round 6 result:
{
  "round": 6,
  "guess": ['yellow', 'blue', 'green', 'black'],
  "analysis": "Found all 4 colors: yellow, blue, green, black",
  "strategy": "Now testing position combinations",
  "feedback": {
    "your_distance": 1,
    "your_rank": 1,
    "game_feedback": {"correct_pegs": 4, "correct_positions": 3}
  }
}
```

### What Agent Sees (R7)
```
Your History (Learn from These Results):
  R5: [red, blue, green, white] → 2p+1pos
  R6: [yellow, blue, green, black] → 4p+3pos
```

---

## Validation Checklist

- [ ] Test completes all 8 rounds without hanging
- [ ] Agent produces memory-aware guesses in R7+
- [ ] No timeout errors in LLM calls
- [ ] Analysis_history properly populated each round
- [ ] Guess accuracy improves or stays consistent

---

## Files to Check

```
src/paradigms/judge_mediated/
├── orchestrator.py        (lines 43, 89, 205-211)
├── agents/
│   ├── team_agent.py      (lines 70-77, 112-136, 173-178)
│   └── agent_server.py    (line 123)
```

---

## Quick Debug

If memory isn't working:

1. Check if `analysis_history` is being populated
   ```bash
   grep -n "team_analysis_histories\[" orchestrator.py
   ```

2. Check if agent receives it
   ```bash
   grep -n "analysis_history" agent_server.py
   ```

3. Check if agent uses it
   ```bash
   grep -n "analysis_history" team_agent.py
   ```

4. Monitor first few rounds for data flow
   ```bash
   grep "Your History" /tmp/agent_memory_test*.log
   ```

---

**Status**: ✅ Implemented and Testing  
**Puzzle**: MM_008 (easy)  
**Expected Time**: 2-3 minutes per test run (300 seconds)
