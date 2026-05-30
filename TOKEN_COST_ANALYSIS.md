# Token Cost Analysis for Boss-Worker Testing

## Per-Round Token Estimate

### Breakdown by Agent Call

**Strategist Call**
- Input: ~600 tokens (game state, history, difficulty)
- Output: ~180 tokens (strategy response)
- **Subtotal: ~780 tokens**

**Analyzer Call**
- Input: ~700 tokens (last guess, feedback, previous history)
- Output: ~250 tokens (constraint analysis)
- **Subtotal: ~950 tokens**

**Proposer Call** (improved with stricter prompt)
- Input: ~1000 tokens (strategy, constraints, template, available colors)
- Output: ~220 tokens (proposed guess)
- **Subtotal: ~1220 tokens**

**Validator Call** (with hard validation first)
- Input: ~800 tokens (guess, constraints, rules)
- Output: ~150 tokens (validation result)
- **Subtotal: ~950 tokens**

### Total Per Round
**~3900 tokens per round** (rounded to 4000 for safety)

---

## Full Game Scenarios

| Scenario | Rounds | Tokens | Cost* |
|----------|--------|--------|-------|
| Quick test (3 rounds) | 3 | ~12,000 | ~$0.01-0.02 |
| Partial test (4 rounds) | 4 | ~16,000 | ~$0.02-0.03 |
| Full game (8 rounds) | 8 | ~32,000 | ~$0.04-0.06 |
| 3 puzzles, 5 rounds each | 15 | ~60,000 | ~$0.07-0.12 |
| Full test suite (3 puzzles, full 8 rounds) | 24 | ~96,000 | ~$0.11-0.18 |

*Cost estimates based on Groq's typical pricing:
- Input tokens: ~$0.00005 per token ($0.05 per 1M)
- Output tokens: ~$0.00015 per token ($0.15 per 1M)
- Actual rates vary; check current Groq pricing

---

## Money-Saving Recommendations

### Option 1: Smart Testing (Recommended)
```
✓ Test 1 puzzle with improved constraints
✓ Run up to 8 rounds maximum
✓ Expected cost: $0.04-0.06 per puzzle
✓ Total for 1 puzzle: ~$0.06
```

### Option 2: Multi-Puzzle Testing
```
✓ Test 3 different puzzles with 5-round limit each
✓ Expected cost: ~$0.07-0.12 per test
✓ Gives good coverage of the improvements
```

### Option 3: Limited Quick Tests (Cheapest)
```
✓ Test 1-2 puzzles with 3-round limit
✓ Expected cost: ~$0.02-0.04 total
✓ Verifies improvements work before full test
```

---

## Token Reduction Opportunities

If tokens are limited, we can reduce them by:

1. **Shorter Prompts** (-20-30% tokens)
   - Remove examples from Validator
   - Reduce context in Analyzer

2. **Max 3-Round Tests** (-60% tokens)
   - Quick validation of improvements
   - ~$0.01 per puzzle

3. **Single Puzzle Only** (-66% tokens)
   - Test improvements on one puzzle
   - ~$0.06 total

4. **Use Local Ollama** (FREE)
   - If you can run local model
   - No token cost
   - Slower but unlimited

---

## My Recommendation

Given the improvements we made (strong Proposer prompt + hard Validator checks), I recommend:

### **Test Plan: 1 Puzzle, Up to 8 Rounds**
- **Cost**: ~$0.04-0.06
- **Scope**: Enough to see if improvements work
- **Puzzle**: MM_004 (easier, ~4-5 rounds to solve)
- **Expected outcome**: Should solve in 5-6 rounds with improvements

This is the **best ROI** - low cost, good validation of the changes.

---

## If You Want to Minimize Cost

### **Ultra-Budget Test: 3 Rounds Max on 1 Puzzle**
- **Cost**: ~$0.012-0.018
- **Purpose**: Quick verification
- **Trade-off**: Won't see full solution, but shows if constraints are being respected

---

## What to Watch For

Once testing starts:
- ✓ Are locked positions staying locked across rounds?
- ✓ Does the guess improve with each round?
- ✓ Are constraints being respected or rejected?
- ✓ Token usage tracking (verify estimates)

---

## Summary

| Budget | Test Plan |
|--------|-----------|
| < $0.02 | 1 puzzle, 3 rounds max |
| $0.05-0.10 | 1 puzzle, full 8 rounds |
| $0.10-0.20 | 2-3 puzzles, varying lengths |

**My recommendation**: $0.06 budget for 1 puzzle, 8 rounds = best validation of improvements
