# Phase 3 Action Plan: Performance Optimization

## Current Status
✅ Phase 1: Hardcoded fallback → Ensures first guess tests all colors  
✅ Phase 2: Color inconsistency detection → Generates hypotheses for wrong colors  
⏳ Phase 3: LLM Performance Optimization → NEEDED to enable full puzzle solving

## The Bottleneck: LLM Slowness

### What's Happening
```
Round 1: 5-10 seconds (initial analysis)
Round 2: 10-15 seconds
Round 3: 15-20 seconds
Round 4: 30-60 seconds (DeepSeek timeout!)
Round 5+: Timeout
```

### Root Cause
- **Current Model**: DeepSeek R1 (reasoning model, thorough but slow)
- **Prompt Size**: Growing with conversation history (adding context from all prior rounds)
- **Token Count**: Each round's prompt includes full history → ~1000-2000 tokens
- **Inference Time**: R1 takes 30-60 seconds for complex reasoning

### Why Phase 2 Helps (But Isn't Enough)
Phase 2 generates hypotheses CORRECTLY, but:
- Still uses slow LLM for strategy generation
- Hypotheses are generated during analysis (slow)
- Proposer waits for full analysis before generating guess
- Overall time per round still 30-60 seconds

## Solution Strategy

### Option 1: Faster Model (Quick Win)
**Action**: Switch from DeepSeek R1 to faster alternative
- DeepSeek API: `deepseek-chat` (vs `deepseek-reasoner`)
- Anthropic: `claude-3-5-sonnet` (faster than opus)
- Groq: `mixtral-8x7b` (very fast, less accurate)

**Effort**: 30 minutes  
**Tradeoff**: May lose some accuracy on complex reasoning  
**Recommendation**: Try this first

### Option 2: Context Optimization (Moderate Effort)
**Action**: Reduce prompt size in later rounds
- Round 1-2: Full history (setup phase)
- Round 3-4: Last 2 rounds only (focused phase)
- Round 5+: Last 1 round only (solving phase)

**Effort**: 1-2 hours  
**Tradeoff**: May lose context for complex deductions  
**Recommendation**: Do after Option 1

### Option 3: Hypothesis Caching (Advanced)
**Action**: Cache hypothesis generation results
- Once hypotheses generated, reuse across multiple attempts
- Don't re-call LLM for same inconsistency pattern
- Parallel hypothesis testing across teams

**Effort**: 2-3 hours  
**Tradeoff**: Complex state management  
**Recommendation**: Do last, only if needed

## Recommended Implementation Order

### Step 1: Switch to Faster Model (Phase 3a)
**Files to modify**:
- `src/base/base_agent.py` - Add model selection parameter
- `src/paradigms/judge_mediated/agents/analyzer_strategist.py` - Use faster model
- `src/paradigms/judge_mediated/agents/proposer_agent.py` - Use faster model

**Time**: 30 minutes  
**Expected Impact**: Round time down to 5-10 seconds (3-4x faster)

```python
# In base_agent.py __init__
if provider == "deepseek":
    model = "deepseek-chat"  # Fast version (was "deepseek-reasoner")
elif provider == "anthropic":
    model = "claude-3-5-sonnet"  # Fast version
```

### Step 2: Context Window Optimization (Phase 3b)
**Files to modify**:
- `src/paradigms/judge_mediated/agents/analyzer_strategist.py` - Lines 194-220 (history building)
- `src/paradigms/judge_mediated/agents/proposer_agent.py` - Lines 130-135 (history building)

**Time**: 1-2 hours  
**Expected Impact**: Further 30-50% faster (depends on rounds completed)

```python
# In analyze_and_strategize()
# Round 1-2: Use full history ([-3:] = last 3 entries)
# Round 3-4: Use limited history ([-2:] = last 2 entries)
# Round 5+: Use minimal history ([-1:] = last 1 entry)

if round_num <= 2:
    entries_to_use = self.analysis_history[-3:]
elif round_num <= 4:
    entries_to_use = self.analysis_history[-2:]
else:
    entries_to_use = self.analysis_history[-1:]
```

### Step 3: Hypothesis Caching (Optional)
**Files to modify**:
- `src/paradigms/judge_mediated/agents/analyzer_strategist.py` - Add cache
- `src/paradigms/judge_mediated/agents/proposer_agent.py` - Use cache

**Time**: 2-3 hours  
**Expected Impact**: 20-30% faster if multiple rounds test same hypotheses

---

## Testing Plan

### Test 1: Verify Phase 3a Works
```bash
cd /Users/masashakra/Desktop/game

# Run with faster model
python3 -c "
from src.paradigms.judge_mediated.orchestrator_2agents import TwoAgentOrchestrator
from puzzle_generator import load_puzzles
puzzles = load_puzzles()
puzzle = next(p for p in puzzles if p['puzzle_id'] == 'MM_008')
orchestrator = TwoAgentOrchestrator(puzzle, provider='deepseek')
result = orchestrator.run()
print(f'Success: {result[\"success\"]}')
print(f'Rounds: {result[\"winning_round\"]}')
"
```

### Test 2: Measure Time Improvement
```bash
# Before: ~120 seconds timeout, incomplete
# After Phase 3a: Expect ~15-30 seconds per puzzle
# After Phase 3b: Expect ~10-20 seconds per puzzle
```

### Test 3: Run on Full Easy Set
```bash
python3 -c "
from src.paradigms.judge_mediated.orchestrator_2agents import TwoAgentOrchestrator
from puzzle_generator import load_puzzles

puzzles = load_puzzles()
easy = [p for p in puzzles if p['difficulty'] == 'easy']

results = []
for puzzle in easy:
    try:
        orch = TwoAgentOrchestrator(puzzle, provider='deepseek')
        result = orch.run()
        results.append({
            'puzzle': puzzle['puzzle_id'],
            'success': result['success'],
            'rounds': result.get('winning_round', 8)
        })
    except:
        results.append({'puzzle': puzzle['puzzle_id'], 'success': False, 'rounds': 8})

successes = sum(1 for r in results if r['success'])
print(f'Success rate: {successes}/{len(results)} ({100*successes//len(results)}%)')
for r in results:
    print(f\"  {r['puzzle']}: {'✅' if r['success'] else '❌'} ({r['rounds']} rounds)\")
"
```

---

## Expected Outcomes

### Phase 3a: Faster Model
- **Success Rate**: 60-70% → 70-80%
- **Time**: 120 seconds → 20-40 seconds per puzzle
- **Effort**: Minimal code change

### Phase 3b: Context Optimization
- **Success Rate**: 70-80% → 75-85%
- **Time**: 20-40 seconds → 10-20 seconds per puzzle
- **Effort**: Moderate code change

### Phase 3c: Hypothesis Caching (Optional)
- **Success Rate**: 75-85% → 80-90%+
- **Time**: 10-20 seconds → 5-15 seconds per puzzle
- **Effort**: Significant code change

---

## Decision Matrix: Which to Implement?

| Approach | Effort | Benefit | Risk | Recommendation |
|----------|--------|---------|------|---|
| **3a: Faster Model** | 30 min | ⭐⭐⭐ | Low | ✅ DO NOW |
| **3b: Context Optimization** | 1-2 hrs | ⭐⭐ | Medium | ✅ DO IF NEEDED |
| **3c: Hypothesis Caching** | 2-3 hrs | ⭐ | High | ❌ SKIP (complex) |

---

## Implementation Checklist

### Before Starting
- [ ] Ensure Phase 1+2 tests still pass
- [ ] Document current baseline (time, success rate)
- [ ] Back up working code to branch

### Phase 3a: Faster Model
- [ ] Modify `base_agent.py` to select faster model
- [ ] Update `analyzer_strategist.py` provider setup
- [ ] Update `proposer_agent.py` provider setup
- [ ] Test with single puzzle (MM_008)
- [ ] Measure time improvement
- [ ] Commit changes

### Phase 3b: Context Optimization (Optional)
- [ ] Add round-number-aware history limiting
- [ ] Implement in analyzer_strategist.py
- [ ] Implement in proposer_agent.py
- [ ] Test with full easy set
- [ ] Measure additional improvement
- [ ] Commit changes

### Phase 3c: Hypothesis Caching (Optional)
- [ ] Add hypothesis cache dict to analyzer
- [ ] Implement cache lookup logic
- [ ] Test with repeated inconsistencies
- [ ] Commit changes

---

## Questions for User

1. **Preference**: Faster model (less accurate) or slower model (more accurate)?
   - Recommendation: Faster is fine; Phase 2 makes up for accuracy loss

2. **Target Success Rate**: 70% (quick fix) or 80%+ (full optimization)?
   - Recommendation: 70% is acceptable; 80%+ requires all 3 phases

3. **Time Budget**: 30 minutes (Phase 3a only) or 3+ hours (full optimization)?
   - Recommendation: 30 minutes gives you 2x speedup

---

## Success Criteria

✅ **Phase 3a Complete** when:
- Round time <10 seconds (down from 30-60 seconds)
- MM_008 solves within 6 rounds (before timeout at 8)
- Easy puzzle success rate ≥70%

✅ **Phase 3b Complete** when:
- Round time <5 seconds
- MM_008 solves within 4-5 rounds
- Easy puzzle success rate ≥80%

✅ **All Complete** when:
- Success rate ≥80% on easy puzzles
- Average solve time <30 seconds total
- Consistent results across multiple runs

---

## Next Command

Ready to proceed? Run this:

```bash
# 1. Backup current working version
cd /Users/masashakra/Desktop/game
git add -A && git commit -m "Phase 1+2 complete: Hardcoded fallback + Color hypothesis detection"

# 2. Create Phase 3 branch
git checkout -b phase-3-optimization

# 3. Implement Phase 3a (faster model)
# Edit src/base/base_agent.py to use faster model
# Edit analyzer_strategist.py and proposer_agent.py

# 4. Test
python3 test_judge_mediated_fix.py

# 5. If successful, merge back to main
git checkout main
git merge phase-3-optimization
```

