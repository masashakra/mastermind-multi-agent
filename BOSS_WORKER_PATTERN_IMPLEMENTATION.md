# Boss-Worker Pattern Applied to Judge-Mediated Memory

## What We Changed

Implemented the **Boss-Worker paradigm's constraint extraction pattern** in judge-mediated agents.

### Before (Generic Memory)
```
Round N Agent receives:
  - guess_history: [all previous guesses]
  - analysis_history: [summary of past results]
  
Agent must INFER constraints from numbers
"OK, 3 pegs, 1 position... which colors? ???"
```

### After (Structured Constraints - Boss-Worker Style)
```
Round N Agent receives:
  - guess_history: [all previous guesses]
  - constraint_history: [
      {
        "round": 5,
        "colors_in": ["red", "blue"],     ← EXPLICIT!
        "colors_out": ["green"],           ← EXPLICIT!
        "locked_positions": {"0": "red"},  ← EXPLICIT!
      }
    ]
  
Agent can see FACTS directly
"I know red is at position 0, blue is in, green is out. Let me build on that!"
```

---

## Implementation Details

### 1. TeamAgent.solve_round() - Single LLM Call

**Old Approach** (3-step prompt):
```
STEP 1: ANALYZE
STEP 2: STRATEGIZE  
STEP 3: GUESS
```

**New Approach** (JSON structured output):
```python
prompt = """
Extract constraints and propose guess.

Respond with JSON:
{
  "colors_in": [...],
  "colors_out": [...],
  "locked_positions": {...},
  "guess": ["c1", "c2", "c3", "c4"]
}
"""
```

**Why single call?**
- More reliable parsing
- Forces DeepSeek to think before responding
- Structured format easier to validate

### 2. Orchestrator.py - Store Constraints

**Old:**
```python
self.team_analysis_histories[team_id].append({
  "round": N,
  "guess": [...],
  "analysis": "text",
  "feedback": {...}
})
```

**New (Boss-Worker style):**
```python
constraints = team_result.get("constraints", {})
if constraints:
  constraints["round"] = round_num
  self.team_constraint_histories[team_id].append(constraints)
```

### 3. Agent Server - Pass Constraints

**Old:**
```python
agent.solve_round(
  analysis_history=payload.get("analysis_history", [])
)
```

**New:**
```python
agent.solve_round(
  constraint_history=payload.get("constraint_history", [])
)
```

---

## Why This Works Better

### Pattern Flow (Like Boss-Worker!)

```
Round 1:
  Agent extracts: colors_in=[], colors_out=[], locked={}
  ↓
Round 2:
  Agent sees: colors_in=[red, blue], colors_out=[green]
  Agent KNOWS these facts, builds on them
  ↓
Round 3:
  Agent sees: colors_in=[red, blue], locked={0: red}
  Agent can now say: "Red is locked, blue must be in pos 1, 2, or 3"
  ↓
Result: Agents follow logic, not random guesses
```

### Explicit Facts > Implicit Inference

**Old (DeepSeek struggles):**
```
"You got 3 pegs + 1 position before... 
 Now got 2 pegs + 0 positions...
 Maybe try [red, red, red, red]?"
```
← DeepSeek doesn't INFER constraints well

**New (DeepSeek can use):**
```
"FACTS: colors IN = [red, blue, green, yellow]
        colors OUT = [white, black]
        locked = {0: red}
 
 TASK: Test permutations with these constraints
 Guess: [red, blue, green, yellow]"
```
← DeepSeek follows explicit rules better

---

## JSON Response Format

Agent now returns:
```json
{
  "colors_in": ["red", "blue", "green"],
  "colors_out": ["yellow", "white"],
  "locked_positions": {"0": "red", "2": "green"},
  "misplaced_colors": [
    {"color": "blue", "wrong_positions": [0, 2]}
  ],
  "reasoning": "Red locked at 0, green at 2, blue in 1 or 3",
  "guess": ["red", "blue", "green", "yellow"]
}
```

This structured output:
1. Gets stored in constraint_history
2. Gets shown to next round agent in explicit form
3. Guides agent's next reasoning

---

## Testing

Running on MM_008 puzzle with:
- **DeepSeek R1** (only available LLM)
- **3 teams** parallel
- **8 rounds** max
- **Boss-Worker constraint extraction**

### Expected Improvements
1. ✅ Agents see explicit constraints (not just numbers)
2. ✅ Next round builds on previous findings
3. ✅ Reduces random guessing (follows rules)
4. ✅ Closer to solution (hopefully!)

### Test Status
- Started: After basic memory implementation
- Config: constraint_history instead of analysis_history
- Running: Now

---

## Fallback Logic

If JSON parsing fails:
```python
# Fallback 1: Use colors_in from last round
if colors_in:
  guess = colors_in[:num_pegs]

# Fallback 2: Use available colors
else:
  guess = available_colors[:num_pegs]
```

Ensures we always return a valid guess even if LLM response is malformed.

---

## Why This Matches Boss-Worker

### Boss-Worker Pipeline
```
Analyzer extracts:
  {colors_in, colors_out, locked_positions}
    ↓ (passes structured data)
Strategist builds strategy:
  "Test these positions with locked colors"
    ↓ (passes strategy)
Proposer generates guess:
  [red, blue, green, yellow]
```

### Judge-Mediated with Constraints
```
Round N Agent extracts:
  {colors_in, colors_out, locked_positions}
    ↓ (stored for next round)
Round N+1 Agent sees facts:
  "RED IN, BLUE IN, GREEN OUT, locked at 0"
    ↓ (builds strategy on facts)
Round N+1 Agent proposes:
  [red, blue, ?, ?]
```

**Same logical pipeline!** Just distributed across rounds instead of agents.

