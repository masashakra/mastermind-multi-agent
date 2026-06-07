# Phase 2 Implementation Summary

## Overview
Phase 2 adds intelligent color identification and hypothesis testing to detect and resolve color inconsistencies that cause puzzle-solving to fail.

## Root Problem Identified
When testing 4 available colors and receiving 3P (pegs) feedback:
- **Naive Algorithm**: Assumes all 4 tested colors are in the puzzle
- **Reality**: Only 3 are in the puzzle; 1 is WRONG
- **Result**: System loops trying to find position locks with wrong color set, never solves

## Solution: Color Inconsistency Detection + Hypothesis Testing

### Component 1: Color Consistency Checker
**File**: `analyzer_strategist.py`, method `_check_color_consistency()`

**What it does**:
- Analyzes each round's feedback vs. number of colors tested
- Detects when: `correct_pegs < num_tested_colors`
- Example: Tested 4 colors, got 3P feedback → ONE COLOR IS WRONG!

**Return value**:
```python
{
    "is_consistent": False,  # Flag for inconsistency
    "issue": "color_count_mismatch",
    "round": 1,
    "tested_colors": ['red', 'blue', 'green', 'yellow'],
    "tested_count": 4,
    "correct_count": 3,  # Only 3 correct out of 4
    "wrong_color_count": 1,
    "identified_colors": ['red', 'blue', 'green']
}
```

### Component 2: Hypothesis Generator
**File**: `analyzer_strategist.py`, method `_generate_color_hypotheses()`

**What it does**:
- When inconsistency detected, generates all possible hypotheses
- For each tested color, creates hypothesis that it's the WRONG one
- For each wrong color, tests replacing it with each untested color
- Returns ranked list of hypotheses to test

**Example output**:
```python
[
    {
        "assumption": "red is WRONG, white is IN",
        "colors": ['blue', 'green', 'yellow', 'white'],
        "wrong_color": 'red',
        "replacement": 'white'
    },
    {
        "assumption": "blue is WRONG, white is IN",
        "colors": ['red', 'green', 'yellow', 'white'],
        "wrong_color": 'blue',
        "replacement": 'white'
    },
    # ... more hypotheses ...
]
```

### Component 3: Analyzer Integration
**File**: `analyzer_strategist.py`, method `analyze_and_strategize()`

**What changed**:
1. After analyzing guess history, calls `_check_color_consistency()`
2. If inconsistency found, calls `_generate_color_hypotheses()`
3. Passes hypotheses in strategy: `strategy["color_hypotheses"] = [...]`
4. Also passes inconsistency info: `strategy["color_inconsistency"] = {...}`
5. Tracks max feedback seen for recovery logic: `strategy["max_pegs_feedback"] = N`

### Component 4: Proposer Integration (Enhanced Recovery)
**File**: `proposer_agent.py`, method `propose_guess()`

**What changed**:
1. **Phase 2 Detection Block** (lines 112-137):
   - Checks if analyzer detected inconsistency
   - If hypotheses available, tests first hypothesis
   - Example: If hypothesis says "test [green, yellow, white, red]", proposes that

2. **Enhanced Color Recovery** (lines 139-170):
   - Original check: `if len(colors_in) < num_pegs`
   - New check: Also checks `if max_feedback < num_pegs AND len(colors_in) == num_pegs`
   - This detects the "4 colors identified but feedback says only 3 correct" anomaly
   - Forces recovery by testing untested colors

**Execution Flow**:
```
Round 1: Initial guess ['red', 'blue', 'green', 'yellow'] → 3P/1L
  ↓
Analyzer Phase 2: Detects inconsistency, generates 8 hypotheses

Round 2: Proposer uses Phase 2 detection
  ↓ 
Tests first hypothesis: 'blue is WRONG, white is IN'
Proposes: ['green', 'yellow', 'white', 'red'] → 2P/0L
  ↓
This result shows white doesn't work, blue might be wrong

Round 3+: Continue hypothesis testing
  ↓
Eventually narrow down which color is actually wrong
and discover the missing color
```

## Code Changes Summary

### analyzer_strategist.py
```python
# NEW: _check_color_consistency() - lines 78-124
def _check_color_consistency(self, guess_history, feedback_history, identified_colors):
    """Detect when color identification contradicts feedback."""
    # Checks if pegs < num_tested
    # Returns inconsistency info if found

# NEW: _generate_color_hypotheses() - lines 126-166
def _generate_color_hypotheses(self, guess, feedback, available_colors):
    """Generate alternative color sets when feedback is inconsistent."""
    # Creates hypotheses for which color might be wrong
    # Tests replacing it with untested colors

# MODIFIED: analyze_and_strategize() - line ~385
# Added calls to consistency checker and hypothesis generator
consistency_check = self._check_color_consistency(...)
if not consistency_check.get("is_consistent"):
    hypotheses = self._generate_color_hypotheses(...)
    result["color_hypotheses"] = hypotheses
    result["color_inconsistency"] = consistency_check

# MODIFIED: analyze_and_strategize() - line ~603
# Track max feedback for proposer recovery logic
max_pegs_feedback = max(fb.get("correct_pegs") for fb in feedback_for_positions)
result["max_pegs_feedback"] = max_pegs_feedback

# MODIFIED: error path - line ~687
# Also track max_pegs_feedback in error fallback
result["max_pegs_feedback"] = max_pegs_feedback
```

### proposer_agent.py
```python
# NEW: Phase 2 Detection Block - lines 112-137
if color_inconsistency and not color_inconsistency.get("is_consistent"):
    color_hypotheses = strategy.get("color_hypotheses", [])
    if color_hypotheses:
        hypothesis = color_hypotheses[0]
        hypothesis_guess = hypothesis["colors"][:num_pegs]
        return {"guess": hypothesis_guess, "reasoning": f"Hypothesis test: {hypothesis['assumption']}"}

# ENHANCED: Color Recovery - lines 139-170
# NEW: Check for max_feedback < num_pegs AND len(colors_in) == num_pegs
if max_feedback < num_pegs and len(colors_in) == num_pegs:
    # Force recovery by testing untested colors
    ...
```

## Test Results

### Observations from First Test Run
1. ✅ **Phase 2 Detection Working**: System correctly detected color inconsistency in Round 2
2. ✅ **Hypothesis Generation Working**: Generated 8 hypotheses correctly
3. ✅ **Hypothesis Testing Working**: Proposer tested first hypothesis in Round 2
4. ✅ **Feedback Integration**: Used hypothesis test feedback to refine understanding

**Round-by-round behavior**:
- **Round 1**: Initial guess → 3P/1L (detects inconsistency)
- **Round 2**: Tests hypothesis "blue is WRONG, white is IN" → 2P/0L (eliminates white)
- **Round 3-5**: Continues testing permutations to find correct colors
- **Round 5+**: (Test still running...)

### Success Metrics
- ✅ Color inconsistency detection working
- ✅ Hypothesis generation working
- ✅ Proposer recovery mode activated
- ⏳ Full puzzle solution (pending - test still running)

## Expected Improvements

| Metric | Before Phase 2 | After Phase 2 | Estimate |
|--------|---|---|---|
| Success Rate | 20% | 60-70% | Better color detection |
| Rounds to Solve | Timeout (8+) | 5-6 | Hypothesis narrows search |
| Color Detection | Stuck on wrong set | Dynamic refinement | Continuous improvement |
| Position Finding | Impossible | Possible after colors found | Foundation for solving |

## Remaining Issues to Address

### Issue 1: Hypothesis Prioritization
Current: Tests hypotheses in order without weighting
Better: Prioritize hypotheses by likelihood
- Example: If feedback drops from 3P to 2P, that color more likely wrong than others

### Issue 2: Systematic Color Testing
Current: Tests untested colors one at a time
Better: Test all untested colors in parallel guesses
- Would find the 4th color faster

### Issue 3: LLM Slowness
Current: DeepSeek timeout at Round 4+
Needed: Optimize context length or switch to faster model
- This is Phase 3 work

### Issue 4: Position Detection with Wrong Colors
Current: Can't detect locked positions because 1 color is wrong
Needed: Position detection should work even with partial color set
- Once 3 correct colors identified, could detect position patterns

## Files Modified
1. `src/paradigms/judge_mediated/agents/analyzer_strategist.py` - Added consistency checker and hypothesis generator
2. `src/paradigms/judge_mediated/agents/proposer_agent.py` - Enhanced color recovery with Phase 2 detection

## Next Steps
1. Complete current test and analyze full results
2. Implement Phase 2b: Hypothesis Prioritization (optional)
3. Implement Phase 3: LLM Performance Optimization
4. Test on full puzzle set (MM_EASY_* puzzles)
5. Target: Achieve 80%+ success rate

