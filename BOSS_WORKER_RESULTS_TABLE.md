# Boss-Worker: 30 Easy Puzzles Results

## Overview
**Paradigm**: Boss-Worker (DeepSeek LLM)  
**Difficulty**: Easy  
**Metric**: Rounds to solve × Guesses per round  

---

## Results Table

| Puzzle | Rounds | Guesses | Avg Guess/Round |
|--------|--------|---------|-----------------|
| MM_001 | 5 | 5 | 1.0 |
| MM_002 | 6 | 6 | 1.0 |
| MM_003 | 2 | 2 | 1.0 |
| MM_004 | 5 | 7 | 1.4 |
| MM_005 | 5 | 5 | 1.0 |
| MM_006 | 6 | 9 | 1.5 |
| MM_007 | 5 | 5 | 1.0 |
| MM_008 | 5 | 7 | 1.4 |
| MM_009 | 5 | 5 | 1.0 |
| MM_010 | 6 | 6 | 1.0 |
| MM_011 | 6 | 6 | 1.0 |
| MM_012 | 4 | 4 | 1.0 |
| MM_013 | 3 | 2 | 0.7 |
| MM_014 | 5 | 5 | 1.0 |
| MM_015 | 7 | 8 | 1.1 |
| MM_016 | 4 | 4 | 1.0 |
| MM_017 | 6 | 6 | 1.0 |
| MM_018 | 6 | 6 | 1.0 |
| MM_019 | 6 | 6 | 1.0 |
| MM_020 | 5 | 5 | 1.0 |
| MM_021 | 5 | 5 | 1.0 |
| MM_022 | 7 | 7 | 1.0 |
| MM_023 | 4 | 4 | 1.0 |
| MM_024 | 6 | 6 | 1.0 |
| MM_025 | 7 | 7 | 1.0 |
| MM_026 | 5 | 5 | 1.0 |
| MM_027 | 5 | 8 | 1.6 |
| MM_028 | 5 | 5 | 1.0 |
| MM_029 | 5 | 5 | 1.0 |
| MM_030 | 5 | 5 | 1.0 |

---

## Statistics

### Rounds Played

| Metric | Value |
|--------|-------|
| **Average** | 5.2 |
| **Median** | 5 |
| **Minimum** | 2 (MM_003) |
| **Maximum** | 7 (MM_015, MM_022, MM_025) |
| **Mode** | 5 |
| **Std Dev** | ~1.2 |

### Total Guesses

| Metric | Value |
|--------|-------|
| **Total** | 166 guesses across 30 puzzles |
| **Average** | 5.5 guesses per puzzle |
| **Median** | 5 guesses |
| **Minimum** | 2 (MM_003, MM_013) |
| **Maximum** | 9 (MM_006) |
| **Std Dev** | ~1.8 |

### Efficiency (Guesses per Round)

| Metric | Value |
|--------|-------|
| **Average ratio** | 1.06 guesses/round |
| **Min ratio** | 0.67 (MM_013: 2 guesses in 3 rounds) |
| **Max ratio** | 1.6 (MM_027: 8 guesses in 5 rounds) |
| **Most common** | 1.0 (23 puzzles) |

---

## Key Insights

### Easiest Puzzles (by round count)
1. **MM_003**: 2 rounds, 2 guesses ⭐ Fastest
2. **MM_013**: 3 rounds, 2 guesses
3. **MM_012, MM_016, MM_023**: 4 rounds each

### Hardest Puzzles (by round count)
1. **MM_015**: 7 rounds, 8 guesses
2. **MM_022**: 7 rounds, 7 guesses
3. **MM_025**: 7 rounds, 7 guesses

### Most Efficient
- **23 out of 30** puzzles had exactly 1 guess per round (perfect efficiency)
- Only **MM_013** had fewer guesses than rounds (0.67 ratio)
- **MM_027** had most guesses per round (1.6)

### Distribution of Difficulty

| Difficulty | Rounds | Count |
|------------|--------|-------|
| Very Easy | 2-3 | 3 puzzles |
| Easy | 4-5 | 16 puzzles |
| Medium | 6 | 8 puzzles |
| Hard | 7+ | 3 puzzles |

---

## Success Rate
✅ **100%** - All 30 puzzles solved successfully by boss-worker paradigm

---

## Notes

- **Round**: A round consists of game feedback + analyzer/strategist/proposer/validator passes
- **Guess**: A proposed_guess sent to the game engine (equals number of validate actions)
- **Efficiency**: Most puzzles used exactly 1 guess per round, indicating the strategist provides accurate next-guess recommendations
- **Outliers**:
  - MM_006 (9 guesses in 6 rounds): High exploration phase
  - MM_027 (8 guesses in 5 rounds): Multiple strategy refinements
  - MM_013 (2 guesses in 3 rounds): Efficient deduction (solver guessed early)

---

**Data Source**: Boss-worker logs (MM_001-MM_030)  
**Generated**: 2026-06-08  
**Format**: Each puzzle ran independently; logs parsed for Round markers in Boss conversations
