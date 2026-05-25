# Mastermind Reasoning Guide - How Agents Should Think

## Feedback Mechanics (Critical!)

### Definition
When you guess `[guess_color_0, guess_color_1, guess_color_2, guess_color_3]` against secret `[secret_color_0, secret_color_1, secret_color_2, secret_color_3]`:

**correct_positions:**
- Count of colors that match exactly at their position
- Range: 0 to 4 (for 4-peg puzzle)
- Example: If positions 0 and 2 match, correct_positions=2

**correct_pegs:**
- TOTAL count of colors that exist in the secret (any position)
- Includes the correct_positions count!
- Range: 0 to 4 (for 4-peg puzzle)
- Example: If 2 colors match position AND 1 other color exists, correct_pegs=3

### Key Insight
**correct_pegs ≥ correct_positions always!**
- correct_positions tells you what's in the right spot
- correct_pegs - correct_positions tells you what exists but wrong spot

---

## Working Example

**Secret Code:** `[white, black, black, green]` (note: black appears twice!)

### Round 1: Testing initial diversity
**Guess:** `[red, blue, green, yellow]`
**Feedback:** correct_pegs=1, correct_positions=0

**Reasoning:**
- Position 0: red ≠ white ✗
- Position 1: blue ≠ black ✗
- Position 2: green ≠ black ✗
- Position 3: yellow ≠ green ✗
- Colors that exist: green exists (but at position 2 in secret, not position 3 in guess)
- Conclusion: Only green exists, all others (red, blue, yellow) are impossible

**What agents learn:**
- ✅ Green definitely exists (was in guess, got feedback)
- ❌ Red, blue, yellow are impossible
- ❌ Black hasn't been tested yet!

### Round 2: Testing white
**Guess:** `[white, blue, green, yellow]`
**Feedback:** correct_pegs=2, correct_positions=1

**Reasoning:**
- Position 0: white = white ✓ (position match!)
- Position 1: blue ≠ black ✗
- Position 2: green ≠ black ✗
- Position 3: yellow ≠ green ✗
- Colors that exist: white (in position 0) + green (elsewhere)
- Conclusion: 2 colors exist, white is locked at position 0, green at wrong position (not 3)

**What agents learn:**
- ✅ White locked at position 0
- ✅ Green exists but not at position 2 or 3 (wait, feedback says 1 position correct, that's white at 0)
- Wait, let me recalculate:
  - Positions: white at 0 matches → correct_positions = 1
  - Colors: white (position 0) + green (wrong position) → correct_pegs = 2
  - Misplaced: green exists somewhere (positions 1 or 3)
- ❌ Blue, yellow still impossible

### Round 3: Testing positions for green
**Guess:** `[white, yellow, green, yellow]`
**Feedback:** correct_pegs=2, correct_positions=1

**Reasoning:**
- Changed blue→yellow at position 1, kept other positions same
- Feedback stayed same (2 pegs, 1 position)
- This means yellow at position 1 is NOT one of our 2 colors
- So our 2 colors are still: white (locked at 0) + green (somewhere else)
- Green could be at positions 1 or 3

### Round 4: Test if white is the issue
**Guess:** `[red, yellow, green, yellow]`
**Feedback:** correct_pegs=1, correct_positions=0

**Reasoning:**
- Changed white→red at position 0
- Feedback DROPPED from 2 to 1 color!
- This proves white IS one of the 2 colors
- Red is not in the secret (feedback dropped)
- So: white and green are our 2 colors
- Positions: white somewhere (not at 0 now, but was locked there), green somewhere

**The Problem:**
- This is WRONG inference! We tested white at position 0 before and it worked
- But agents might think: "white lost feedback when moved from position 0"
- Conclusion: white was locked at position 0
- So guess should go back to: [white at 0, ?, green somewhere, ?]

### Round 5: Test new colors (positions 1 and 2)
**Guess:** `[white, black, green, blue]`
**Feedback:** correct_pegs=?, correct_positions=?

**What should happen:**
- Position 0: white = white ✓ (locked still)
- Position 1: black = black ✓ (match! but wait, secret has black at positions 1 AND 2)
- Position 2: green ≠ black ✗
- Position 3: blue ≠ green ✗
- correct_positions: 2 (positions 0 and 1)
- correct_pegs: 3 (white, black at positions 0-1, plus another black? plus green?)

Wait, the secret is `[white, black, black, green]`. Let me count colors:
- white: appears once, guess has it at position 0 → 1 match
- black: appears twice in secret, guess has it at position 1 → guess black count = 1, min(1,2) = 1 match
- green: appears once in secret, guess has it at position 2 → 0 match (position 2 in guess is green, but secret has black)
- Total correct_pegs = white(1) + black(1) + green(0) = 2... but there's another black in secret!

Actually, let me recalculate the feedback for guess `[white, black, green, blue]`:
- Exact matches: position 0 (white) and position 1 (black) = 2 correct_positions
- Color count:
  - white: guess has 1, secret has 1 → min(1,1) = 1
  - black: guess has 1, secret has 2 → min(1,2) = 1
  - green: guess has 1, secret has 1 → min(1,1) = 1
  - blue: guess has 1, secret has 0 → min(1,0) = 0
  - Total = 1 + 1 + 1 + 0 = 3 correct_pegs

So feedback would be: correct_pegs=3, correct_positions=2

### Pattern Recognition
After rounds so far, agents should realize:
- Positions 0 and 1 are locked (white and black)
- We have 3 colors matching (white, black, green)
- Need to find what's at position 3
- Position 2 is unknown (guess had green but secret has black)

This is WHERE THE SYSTEM GETS STUCK!

The issue: **Black appears TWICE** - at positions 1 AND 2 in secret.
- Guess: `[white, black, green, blue]` gives us feedback about positions but not clearly about the duplicate black
- Agents need to realize: position 2 has a matching color (black) but not at the right position in this guess
- The color at position 2 IS black (which is in the secret), but agents test green there

---

## Key Reasoning Principles

### 1. Exact Positions First
Always identify which positions have locked colors:
- Move a color from position A to position B
- If feedback doesn't change, neither A nor B is locked
- If feedback changes, one of them is locked

### 2. Color Existence
Use feedback changes to identify if colors exist:
- Replace color A with color B everywhere
- If correct_pegs goes up → B exists
- If correct_pegs goes down → A exists
- If stays same → neither or both exist

### 3. Duplicate Colors
THE HARDEST CASE: Secret can have same color multiple times
- `[white, black, black, green]` has black twice
- Feedback count only tells you if COLOR exists, not HOW MANY
- To detect duplicates:
  - Test with one instance of color: `[white, black, ?, ?]` → 2 pegs
  - Test with zero instances: `[white, ?, ?, ?]` → ? pegs
  - Difference tells you if color appears multiple times

### 4. Position vs Color Confusion
Remember:
- correct_positions = exact matches (right color, right position)
- correct_pegs = color matches (right color, any position)
- Misplaced = in correct_pegs but not correct_positions
- Impossible = not in correct_pegs

### 5. Multi-Round Reasoning
Each round's feedback depends on ALL colors:
```
Round N feedback = f(guess_N, secret)

To infer what changed:
  feedback_N vs feedback_N-1 depends on:
  - What changed in guess (positions and colors)
  - What's in secret
  
Examples:
  [A,B,C,D] → 2 pegs
  [A,B,C,E] → 1 peg
  → D exists, E doesn't

  [A,B,C,D] → 2 pegs, 0 positions
  [A,C,B,D] → 2 pegs, 1 position
  → Either A, C, or B is locked somewhere
```

---

## Strategic Guide for Agents

### PHASE 1: Exploration (Round 1)
**Goal:** Find which colors exist

**Strategy:**
- Test 4 diverse colors
- Learn which ones get any feedback
- Eliminate those with zero feedback

**Example:**
```
Guess: [red, blue, green, yellow]
Feedback: 1 peg
→ One of red/blue/green/yellow exists
→ Three are impossible
```

### PHASE 2: Constraint Building (Rounds 2-3)
**Goal:** Find locked positions and remaining colors

**Strategy:**
- Move tested colors to different positions
- Introduce 1 new color to test if more exist
- Track feedback changes to identify locked positions

**Example:**
```
Round 1: [red, blue, green, yellow] → 1 peg
Round 2: [white, blue, green, yellow] → 2 pegs
→ White exists (feedback went up)
→ One of green/blue/yellow or white is locked

Round 3: [white, black, green, yellow] → ? pegs
→ Testing if black exists
→ Testing different position for blue
```

### PHASE 3: Refinement (Rounds 4-5)
**Goal:** Find exact positions and remaining colors

**Strategy:**
- Test new colors at unknown positions
- Move misplaced colors to try different positions
- Narrow down which of 4-6 colors are in secret

**Example:**
```
After Rounds 1-3 we know:
- Green and white exist
- 2 more colors unknown
- Positions unknown

Guess: [white, black, green, purple]
→ Tests if black/purple exist at specific positions
→ Narrows possibilities significantly
```

### PHASE 4: Confirmation (Rounds 6-8)
**Goal:** Find exact positions for all 4 colors

**Strategy:**
- All 4 colors identified
- Test different position arrangements
- Small search space remaining

**Example:**
```
Known: white, black, green, purple exist
Guess: [white, black, green, purple]
Guess: [white, green, black, purple]
Guess: [white, purple, green, black]
→ One of these should solve
```

---

## Common Mistakes (Why Tests Fail)

### ❌ Mistake 1: Forgetting Colors
Agents test colors but don't track what's impossible.

**Fix:**
- Analyzer must output impossible_colors list
- Proposer must never use colors from impossible list

### ❌ Mistake 2: Not Testing New Colors
After finding 2 colors, agents keep rearranging them instead of testing new ones.

**Fix:**
- Strategist must say "need to test new colors"
- Proposer must include new colors in guesses

### ❌ Mistake 3: Missing Duplicate Colors
Secret has same color twice, agents don't discover.

**Example:**
```
Secret: [white, black, black, green]
Guess 1: [red, blue, green, yellow] → 1 peg (green)
Guess 2: [white, black, green, yellow] → 2 pegs (white, green)
Guess 3: [white, black, green, blue] → ? pegs

Should be: 3 pegs (white, black found; green exists)
BUT agent might not test position 2 with black
→ Never realizes there are TWO blacks
```

**Fix:**
- Test colors in multiple positions
- If color doesn't match at position A, try position B
- Use feedback changes to detect duplicates

### ❌ Mistake 4: Repeating Same Guess
System gets confused about state and tests same guess twice.

**Fix:**
- Validator must check against guess_history
- Proposer must avoid previous guesses
- Add explicit "NEVER duplicate" constraint

### ❌ Mistake 5: Not Using Constraint Feedback
Analyzer extracts constraints but Proposer ignores them.

**Fix:**
- Pass constraints explicitly to Proposer
- Proposer must check each candidate against all constraints
- Validator must verify constraints before submission

---

## Debugging Checklist

When a puzzle fails, check:

□ **Analyzer Output:**
- [ ] Are locked positions correct count?
- [ ] Are misplaced colors actually misplaced?
- [ ] Are impossible colors truly impossible?
- [ ] Handles multi-round reasoning?

□ **Strategist Output:**
- [ ] Is phase correct for round number?
- [ ] Does strategy make sense given constraints?
- [ ] Are recommendations specific (not vague)?

□ **Proposer Output:**
- [ ] Are all 3 candidates valid?
- [ ] Do candidates respect constraints?
- [ ] Is selected candidate the best?
- [ ] Is guess different from previous?

□ **Validator Output:**
- [ ] Is guess valid format?
- [ ] Does it respect all constraints?
- [ ] Are errors/warnings appropriate?

□ **Game Loop:**
- [ ] Is feedback computed correctly?
- [ ] Is history passed to next round?
- [ ] Did game timeout at 8 rounds?

