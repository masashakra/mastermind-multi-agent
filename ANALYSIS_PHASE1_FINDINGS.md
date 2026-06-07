# Judge-Mediated Phase 1 Findings & Phase 2 Plan

## Executive Summary

**Phase 1 Status**: ✅ PARTIALLY SUCCESSFUL
- Hardcoded initial guess (Fix #1) implemented correctly
- Color recovery mechanism (Fix #2) implemented but insufficient
- **New Issue Discovered**: Analyzer has flawed color identification logic

**Expected Impact**: 20% → 80% success rate (if all issues fixed)

---

## Test Results Analysis

### Test Setup
- Puzzle: MM_008
- Secret Code: `['yellow', 'blue', 'red', 'black']`
- Available Colors: `['red', 'blue', 'green', 'yellow', 'white', 'black']`
- Configuration: 2-agent judge_mediated with DeepSeek R1

### Round 1 Behavior (✅ Working as Expected)

**Initial Guess (Hardcoded - Fix #1)**
```
Team 1: ['red', 'blue', 'green', 'yellow']  ← Tests first 4 available colors
Team 2: ['red', 'blue', 'green', 'yellow']  ← Same hardcoded guess
```

**Feedback Received**
```
Team 1: 3P/1L (3 colors correct, 1 position locked)
Team 2: 3P/1L (same)
```

**Expected Interpretation**
- 3 of the 4 tested colors are in the puzzle
- 1 of the 4 is NOT in the puzzle
- The 4th color in the puzzle is one of the untested colors [white, black]

**Actual Analyzer Interpretation (❌ WRONG)**
- All 4 tested colors are in the puzzle: `colors_in = ['red', 'blue', 'green', 'yellow']`
- Locked position: blue at position 1
- No recognition that green is wrong and black is missing

### Why This Causes Failure

With incorrect `colors_in = ['red', 'blue', 'green', 'yellow']`:
1. Proposer can only permute these 4 colors
2. One of them (green) is always wrong
3. No way to discover that the 4th color should be black
4. System loops through permutations of wrong color set
5. Never solves puzzle (timeout after 8 rounds)

### Root Cause: Naive Color Identification

The `AnalyzerStrategistAgent` uses this logic:

```python
# In analyzer_strategist.py, line ~180
if feedback.get("correct_pegs", 0) > 0:
    # Assume ALL colors in guess with positive feedback are IN the puzzle
    colors_in = list(set(guess))  # ← THIS IS THE BUG!
```

This logic fails when:
- Total colors available > num_pegs (in this case 6 > 4)
- Initial guess doesn't contain all actual puzzle colors
- Feedback is incomplete (3P instead of 4P on 4-color guess)

**Why direct_debate works**: It has separate Solver and Analyzer agents that use different strategies and can fallback gracefully to hypothesis generation when color ID is uncertain.

---

## Phase 1 Fixes: Impact Assessment

### Fix #1: Hardcoded Initial Guess ✅
**Status**: Working correctly
**Code Location**: `proposer_agent.py`, lines 89-101
**Impact**:
- ✅ Guarantees Round 1 always tests first 4 colors
- ✅ Provides immediate feedback on which colors are in puzzle
- ⚠️ Only works if first 4 available colors overlap with actual puzzle colors
- ❌ Fails if puzzle uses colors from positions [0,1,2,4] instead of [0,1,2,3]

**Improvement Needed**: Randomize color order in available_colors OR test all colors systematically

### Fix #2: Color Recovery Mechanism ✅ (Partially)
**Status**: Implemented but insufficient
**Code Location**: `proposer_agent.py`, lines 112-128
**Logic**:
```python
if round_num >= 2 and len(colors_in) < num_pegs:
    # Force test of untested colors
```

**Problem**: 
- Only triggers when `len(colors_in) < 4`
- In this test, colors_in = 4 (but wrong), so doesn't trigger
- Condition is too simple

**Needed Enhancement**: Detect when feedback doesn't match color count
- If we tested 4 colors and got 3P feedback: 1 color is wrong!
- Trigger recovery when: `max_feedback_seen < num_pegs` OR color consistency check fails

---

## Core Algorithm Problem: Feedback → Colors Inference

### Current (Broken) Logic
```
Tested: ['red', 'blue', 'green', 'yellow']
Feedback: 3P/1L
Conclusion: colors_in = ['red', 'blue', 'green', 'yellow']  ❌ WRONG
```

### Better Logic Needed
```
Tested: ['red', 'blue', 'green', 'yellow'] (4 colors)
Feedback: 3P/1L (only 3 colors correct!)
Conclusion: Exactly 1 of these 4 is wrong
            Unknown which one, need more data
            
Solution: In next round, test replacement hypothesis
          Try ['red', 'blue', 'green', 'white'] instead
          If we get 4P: green was wrong, white is correct
          If we get 3P again: try other color combinations
```

### Mathematical Framework

Given:
- `tested_colors = ['red', 'blue', 'green', 'yellow']` (4 colors)
- `feedback = 3P/1L` (3 correct, 1 position locked)

Possible scenarios:
1. Red is wrong → colors are [blue, green, yellow, X]
2. Blue is wrong → colors are [red, green, yellow, X]
3. Green is wrong → colors are [red, blue, yellow, X]  ← **CORRECT**
4. Yellow is wrong → colors are [red, blue, green, X]

Where X ∈ [white, black] (untested colors)

The current system incorrectly assumes scenario (all 4 are in), but should create hypotheses for scenarios 1-4.

---

## Phase 2 Plan: Enhanced Color Identification

### Phase 2a: Feedback Consistency Checker
**File**: `analyzer_strategist.py` (ADD method)

```python
def _check_color_consistency(self, guesses, feedbacks):
    """Detect when color identification contradicts feedback."""
    
    for guess, feedback in zip(guesses, feedbacks):
        pegs = feedback.get("correct_pegs", 0)
        
        # If feedback < num_tested, one color is wrong!
        if pegs < len(set(guess)):  # < 4 correct out of 4 tested
            return {
                "is_consistent": False,
                "issue": "feedback_count_mismatch",
                "tested": len(set(guess)),
                "correct": pegs,
                "missing_colors": len(set(guess)) - pegs
            }
    
    return {"is_consistent": True}
```

### Phase 2b: Hypothesis Generation
**File**: `analyzer_strategist.py` (ADD method)

```python
def _generate_color_hypotheses(self, guess, feedback, available_colors):
    """Generate alternative color sets when feedback is inconsistent."""
    
    pegs = feedback["correct_pegs"]
    
    if pegs < len(set(guess)):
        # One color in guess is wrong
        wrong_color_candidates = list(set(guess))
        untested = [c for c in available_colors if c not in guess]
        
        hypotheses = []
        for wrong_color in wrong_color_candidates:
            for replacement in untested:
                hypothesis = [
                    replacement if c == wrong_color else c
                    for c in guess
                ]
                hypotheses.append({
                    "assumption": f"{wrong_color} is wrong, {replacement} is in puzzle",
                    "colors": list(set(hypothesis))
                })
        
        return hypotheses
    
    return None
```

### Phase 2c: Hypothesis Testing Strategy
**File**: `proposer_agent.py` (ENHANCE propose_guess)

```python
def propose_guess(self, strategy, available_colors, num_pegs=4, round_num=1):
    # ... existing code ...
    
    # NEW: Check if we should test a hypothesis
    hypotheses = strategy.get("color_hypotheses", [])
    if hypotheses and round_num >= 2:
        hypothesis_to_test = hypotheses[0]  # Test most likely first
        print(f"Testing hypothesis: {hypothesis_to_test['assumption']}")
        
        guess = hypothesis_to_test["colors"][:num_pegs]
        return {"guess": guess, "reasoning": f"Hypothesis test: {hypothesis_to_test['assumption']}"}
    
    # ... rest of existing code ...
```

### Phase 2d: Enhanced Color Recovery (FIX #2 Improvement)
**File**: `proposer_agent.py` (IMPROVE lines 112-128)

```python
# CURRENT (insufficient)
if round_num >= 2 and len(colors_in) < num_pegs:
    untested_colors = [c for c in available_colors if c not in colors_in]
    if untested_colors:
        # Force new color test
        ...

# PROPOSED (enhanced)
if round_num >= 2:
    # Check for inconsistency: is max feedback < expected?
    max_feedback_seen = strategy.get("max_pegs_feedback", 0)
    
    if max_feedback_seen < num_pegs and len(colors_in) == num_pegs:
        # Feedback says < 4 colors correct, but we identified 4 colors!
        # One of our identified colors is WRONG
        print(f"⚠️ FEEDBACK INCONSISTENCY: Max {max_feedback_seen}P out of {num_pegs}")
        print(f"    But colors_in has {len(colors_in)} colors - one is WRONG!")
        
        # Force test of untested colors
        untested = [c for c in available_colors if c not in colors_in]
        if untested:
            recovery_guess = colors_in[:num_pegs-1] + [untested[0]]
            return {"guess": recovery_guess, "reasoning": "Color hypothesis test"}
```

---

## Phase 2e: Proposer Memory Enhancement
**File**: `proposer_agent.py` (ADD tracking)

```python
def __init__(self, ...):
    # ... existing code ...
    self.color_hypotheses_tested = []  # Track what we've tested
    self.feedback_anomalies = []       # Track when feedback is inconsistent
```

---

## Implementation Sequence

### Step 1: Add Consistency Checker (analyzer_strategist.py)
- Add `_check_color_consistency()` method
- Call it after analyzing each round's feedback
- Return anomaly info in strategy

### Step 2: Add Hypothesis Generator (analyzer_strategist.py)
- Add `_generate_color_hypotheses()` method
- Generate alternatives when inconsistency detected
- Include in strategy payload

### Step 3: Improve Color Recovery (proposer_agent.py)
- Enhance the color recovery trigger condition
- Check for feedback < expected, not just color_count
- Test hypothesis colors in recovery mode

### Step 4: Test Integrated Solution
- Run test_judge_mediated_fix.py again
- Expected: Should solve within 5-6 rounds instead of timeout

### Step 5: Verify on Multiple Puzzles
- Test on MM_008 (current failure case)
- Test on MM_EASY_* puzzles (regression)
- Verify success rate improves to 80%+

---

## Success Criteria for Phase 2

| Metric | Target | Measurement |
|--------|--------|-------------|
| MM_008 Success | ✅ Solve | Within 6 rounds |
| Easy Puzzles | 80%+ | 4-5 out of 5 |
| Avg Rounds | ≤ 5 | Mean rounds to solve |
| No Timeouts | 100% | All tests complete |

---

## Files to Modify

1. **analyzer_strategist.py**
   - Add `_check_color_consistency()` at line ~300
   - Add `_generate_color_hypotheses()` at line ~320
   - Call them from `analyze_and_strategize()` method
   - Include results in returned strategy

2. **proposer_agent.py**
   - Enhance color recovery trigger (line 114)
   - Add `feedback_anomalies` tracking to `__init__`
   - Support hypothesis testing in `propose_guess()`

3. **test_judge_mediated_fix.py**
   - No changes needed (already set up correctly)

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Hypotheses too broad | Medium | Limit to top 2-3 most likely hypotheses |
| Increased LLM calls | Medium | Cache hypothesis results, reuse across rounds |
| Edge case failures | Low | Comprehensive unit tests for consistency checker |
| Timeout on complex puzzles | Low | Phase 3 will optimize LLM speed |

---

## Timeline Estimate

- **Phase 2a-c (Implement)**: 30-45 minutes
- **Phase 2d-e (Integrate)**: 15-20 minutes  
- **Testing & Verification**: 30 minutes
- **Total Phase 2**: ~2 hours

Expected completion: Within current session

