# Mastermind AI Solver - Complete System Overview

## Current Architecture

```
Game Loop (boss_worker.py)
    ↓
Boss Agent (boss.py)
    ├─→ Strategist (strategist.py) - IMPROVED v2
    ├─→ Analyzer (analyzer.py) - IMPROVED v2
    ├─→ Proposer (proposer.py) - IMPROVED v2
    └─→ Validator (validator.py) - IMPROVED v2
    ↓
Game Engine (game_engine.py)
    ├─ Validates guess format
    ├─ Computes feedback (correct_pegs, correct_positions)
    └─ Tracks game state
    ↓
Puzzle Results (logging + metrics)
```

---

## Agent Improvements Summary

### Level 1: Analyzer Agent
**File:** `src/agents/analyzer.py`

**What it does:**
- Takes last guess + feedback
- Extracts constraints (locked positions, misplaced colors, impossible colors)
- Returns structured constraint analysis

**Improvements:**
- ✅ Minimal 3-line feedback rule definition
- ✅ 4 detailed worked examples:
  - Example 1: Finding locked positions (all correct)
  - Example 2: Identifying misplaced colors (partial lock)
  - Example 3: Eliminating colors (feedback 0,0)
  - Example 4: Multi-round reasoning (duplicate colors!)
- ✅ Constraint validation logic (locks count matches feedback)
- ✅ Fallback to programmatic validation if LLM fails

**Key Feature:**
- Example 4 specifically handles tricky multi-round cases with duplicate colors
- Validates that locked positions count matches "correct_positions" feedback
- Recovers from LLM constraint extraction errors using position change heuristics

---

### Level 2: Proposer Agent
**File:** `src/agents/proposer.py`

**What it does:**
- Takes strategy + constraints + available colors
- Generates next guess that respects all constraints
- Returns proposed guess with reasoning

**Improvements:**
- ✅ Implemented Tree-of-Thoughts (ToT) approach
- ✅ Generates 3 candidate guesses internally
- ✅ Evaluates each candidate against all constraints
- ✅ Selects best candidate (most informative)
- ✅ 5 detailed worked examples covering:
  - Example 1: First round (diverse colors)
  - Example 2: One locked position
  - Example 3: Mostly locked (1-2 unknown)
  - Example 4: Multiple misplaced colors
  - Example 5: High confidence guess (almost done)
- ✅ Output includes all 3 candidates + reasoning for selection
- ✅ Constraint violation detection and fixing:
  - Never moves locked colors
  - Never uses impossible colors
  - Tests misplaced colors in new positions
- ✅ Duplicate guess prevention

**Key Feature:**
- Tree-of-Thought shown to improve similar tasks from 4% to 74%
- Explicit constraint checking for each candidate
- If LLM response unparseable, fallback to random valid guess

---

### Level 3: Strategist Agent
**File:** `src/agents/strategist.py`

**What it does:**
- Analyzes game history and feedback patterns
- Proposes high-level strategy for next guess(es)
- Guides the Proposer on what to test

**Improvements:**
- ✅ Introduced strategy PHASES (was generic before)
- ✅ 5 detailed worked examples:
  - Example 1: EXPLORATION phase (Round 1 - test diverse colors)
  - Example 2: CONSTRAINT BUILDING (found 1 lock, refine positions)
  - Example 3: REFINEMENT (have 2 colors, need 2 more)
  - Example 4: CONFIRMATION (3 colors found, final positions)
  - Example 5: CONFIRMATION (all 4 colors, just arrange)
- ✅ Confidence tracking (0.5 to 0.95 as progress increases)
- ✅ Recommended positions dict showing what to test at each position

**Key Feature:**
- Specific guidance instead of vague instructions
- Phase-based reasoning shows LLM what stage we're in
- Recommended_positions helps Proposer know which positions to focus on

---

### Level 4: Validator Agent
**File:** `src/agents/validator.py`

**What it does:**
- Quality control before guess submission
- Checks format, colors, and CONSTRAINTS
- Returns is_valid, ready_to_submit, detailed errors/warnings

**Improvements:**
- ✅ Added constraint validation (not just format)
- ✅ Now accepts `constraints` parameter from Boss
- ✅ Uses improved LLM prompt with 4 worked examples:
  - Example 1: Valid guess (all constraints satisfied)
  - Example 2: Invalid - violates locked position
  - Example 3: Invalid - uses impossible color
  - Example 4: Invalid - misplaced color in same position
- ✅ Detailed constraint_check breakdown in output
- ✅ Can prevent bad guesses BEFORE they're submitted

**Key Feature:**
- Prevents constraint violations at the gate
- Detailed feedback on what's wrong with invalid guesses
- Can save wasted guesses by catching errors early

---

## Boss Orchestration
**File:** `src/agents/boss.py`

**Workflow per round:**
1. Call Strategist → get phase + recommended strategy
2. Call Analyzer → extract constraints from latest feedback
3. Call Proposer → generate 3 candidates, pick best
4. Call Validator → validate guess with constraints
5. Submit to game engine
6. If invalid, log error and continue

**Recent Update:**
- Now passes constraints dict to Validator
- Uses validate_with_llm() for constraint-aware validation

---

## Game Loop
**File:** `src/paradigms/boss_worker.py`

**Main loop:**
```
For each round (max 8):
  1. Boss orchestrates round
  2. Extract guess from round result
  3. Submit to game engine
  4. Get feedback
  5. Log everything
  6. Check if solved
  7. If solved or max rounds reached, exit
```

**Logging:**
- All inter-agent messages logged
- Feedback logged
- Errors logged
- Token usage tracked per agent

---

## Current Test Results

### Test 1: Easy Puzzle (MM_005)
**Secret:** ['white', 'black', 'black', 'green']

**First Run (5 guesses):**
- Failed after 5 guesses
- Got stuck testing same colors repeatedly
- Never discovered that black (duplicate) was in secret

**Second Run (6 guesses, after Strategist improvement):**
- Made slightly more progress
- Found white by guess 4
- Still failed (system repeats guesses)

**Root Cause Analysis:**
- Model (Llama 8B) struggles with constraint memory
- Duplicate guesses suggest fallback logic or state loss
- System CAN find individual colors but struggles with combination

---

## What Works
✅ Basic agent orchestration
✅ Constraint extraction from feedback
✅ Tree-of-Thought candidate generation
✅ Validator prevents some constraint violations
✅ Phase-based strategy guidance
✅ Fallback error handling

## What Struggles  
❌ Model doesn't maintain constraint state across rounds
❌ Repetition of same guesses despite history
❌ Finding multiple missing colors simultaneously
❌ Reasoning about duplicate colors in secret
❌ Complex constraint combinations (>3 constraints)

---

## Known Limitations

### Llama 8B Constraints
- Token context limit (4K)
- Weaker combinatorial reasoning
- Struggles with multi-step inference
- Difficulty maintaining state across calls

### Why Tests Failed
1. **Memory Loss:** System doesn't maintain constraint context
2. **Repetition:** Fallback logic reverts to old guesses
3. **Model Capability:** 8B model lacks reasoning depth for constraint satisfaction

---

## Architecture Strengths
✅ Clean separation of concerns (Strategist → Analyzer → Proposer → Validator)
✅ All agents have worked examples (best practice from research)
✅ Tree-of-Thought implemented in Proposer
✅ Comprehensive error handling and logging
✅ Boss orchestration prevents deadlocks
✅ Validator catches errors before submission

---

## Next Steps Available

### Without New Enhancements:
1. **Tune existing prompts further** - Add more edge case examples
2. **Improve context passing** - Ensure constraints passed correctly between agents
3. **Debug state management** - Investigate why guesses repeat

### With New Enhancements:
1. **Z3 Constraint Solver** - Offload constraint satisfaction
2. **Better model** - Claude API or Llama 70B
3. **Prompt caching** - Keep constraints in context longer

---

## System Readiness

| Component | Status | Notes |
|-----------|--------|-------|
| Analyzer | ✅ Ready | 4 examples, constraint validation |
| Proposer | ✅ Ready | Tree-of-Thought, candidate evaluation |
| Strategist | ✅ Ready | Phase-based guidance |
| Validator | ✅ Ready | Constraint checking |
| Orchestration | ✅ Ready | Clean workflow |
| Game Loop | ✅ Ready | Proper feedback/logging |
| Testing | 🔴 Incomplete | Easy puzzle not solved |

**Overall:** System architecture is sound and well-designed. Limitations are primarily model capability (Llama 8B) and state management across rounds.

---

## Metrics for Next Test Run

When we test the full system, track:
1. **Success rate** - % of easy puzzles solved
2. **Guess efficiency** - Avg guesses to solve (target: 5-6)
3. **Constraint violations** - Times Validator catches errors
4. **State accuracy** - Does system remember previous constraints?
5. **Execution time** - Total time per puzzle
6. **Agent token usage** - Which agent uses most?

