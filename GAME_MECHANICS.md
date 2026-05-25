# Mastermind Game Mechanics - LLM Guide

This document explains Mastermind in a way designed for LLMs to understand and reason about constraints.

---

## The Game

**Objective:** Guess a secret code in 8 or fewer rounds.

**Code Format:** 4-6 color pegs in specific positions
- Example: `["red", "blue", "green", "yellow"]`

**Available Colors:** Varies by difficulty (6-10 colors)

---

## Feedback Mechanic (CRITICAL FOR UNDERSTANDING)

After each guess, you get TWO numbers:

### 1. `correct_positions` (Exact Matches)
**Definition:** How many pegs are the RIGHT COLOR in the RIGHT POSITION

**Example:**
```
Secret:  ["red", "blue", "green", "yellow"]
Guess:   ["red", "white", "green", "black"]
         ↑              ↑
       Match         Match
correct_positions = 2 (red at 0, green at 2)
```

### 2. `correct_pegs` (Color Matches, Any Position)
**Definition:** How many pegs are the RIGHT COLOR but WRONG or RIGHT position

**Key Point:** This includes the correct_positions count!

**Example:**
```
Secret:  ["red", "blue", "green", "yellow"]
Guess:   ["blue", "red", "yellow", "white"]
         
Breaking it down:
- Position 0: "blue" exists in secret (at pos 1) ✓ color exists
- Position 1: "red" exists in secret (at pos 0) ✓ color exists  
- Position 2: "yellow" exists in secret (at pos 3) ✓ color exists
- Position 3: "white" does NOT exist ✗

correct_pegs = 3 (blue + red + yellow)
correct_positions = 0 (none in right spots)
```

---

## Constraint Extraction Logic

### What Each Feedback Tells You

**If `correct_positions = 2, correct_pegs = 2`:**
- 2 pegs are in the EXACT right position
- 2 pegs are in the secret but WRONG positions (or duplicates of correct ones)
- 2 pegs are NOT in the secret at all

**If `correct_positions = 0, correct_pegs = 3`:**
- NO pegs are in the right position (all wrong positions)
- 3 colors ARE in the secret (just rearranged)
- 1+ color is NOT in the secret

**If `correct_positions = 0, correct_pegs = 0`:**
- NONE of the 4 colors exist in the secret
- All 4 colors are ELIMINATED

---

## Decision-Making Framework

### After Each Guess, Ask These Questions:

1. **Which positions are locked?**
   - A position is LOCKED if we find a color that scores correct_positions
   - Example: If position 0 gets a match, don't move that color from position 0

2. **Which colors are confirmed?**
   - Colors that appear in `correct_pegs` exist somewhere in secret
   - Mark where they CAN'T be (they scored wrong position there)

3. **Which colors are eliminated?**
   - Any color that appeared in a guess with `correct_pegs + correct_positions = 0`
   - This color is NOT in the secret at all

4. **What's uncertain?**
   - Positions without confirmed colors
   - Unknown if unknown colors exist

---

## Systematic Search Strategy

### Good Approach (Finds solution in ~5 guesses):

**Round 1:** Test 4 diverse colors to find which ones exist
- Guess: `["red", "blue", "green", "yellow"]`
- Learn: Which 0-4 colors are in the secret

**Rounds 2-4:** Test positions of confirmed colors + try new colors if needed
- Lock in colors as you find their positions
- Eliminate colors that score 0

**Rounds 5-6:** Fine-tune remaining uncertain positions
- You should be close to the answer now

**Round 7-8:** Final verification

### Bad Approach (Takes 8+ guesses):
- Random guessing without tracking constraints
- Not locking in confirmed positions
- Retesting eliminated colors
- Not being systematic

---

## Example: Complete Puzzle

```
Secret: ["white", "black", "black", "green"]  (4 pegs, 6 colors)

Round 1: Guess ["red", "blue", "yellow", "green"]
  Feedback: correct_positions=0, correct_pegs=1
  Analysis: "green" exists (wrong position), others don't
  
Round 2: Guess ["green", "red", "blue", "white"]
  Feedback: correct_positions=1, correct_pegs=1
  Analysis: "green" at position 0 is LOCKED! 
            "white" exists but not at position 3
            "red", "blue" are eliminated
  
Round 3: Guess ["green", "black", "white", "yellow"]
  Feedback: correct_positions=2, correct_pegs=2
  Analysis: "green" at 0 LOCKED ✓
            "black" at 1 LOCKED ✓
            "white" exists but not at position 2
            "yellow" eliminated
  
Round 4: Guess ["green", "black", "black", "white"]
  Feedback: correct_positions=4, correct_pegs=0
  Analysis: SOLVED! All positions correct.
```

---

## Key Insights for LLM Reasoning

1. **Feedback includes the correct_positions count in correct_pegs**
   - If correct_positions=2 and correct_pegs=3, there's 1 additional color that's in the secret but wrong position

2. **Locked positions are GOLD**
   - Once you find a color in the right position, DON'T move it
   - This shrinks the search space drastically

3. **Elimination is powerful**
   - Any color that appears in a guess returning (0,0) is GONE
   - Don't test it again

4. **The problem narrows quickly**
   - Round 1: Test diversity (find which colors exist)
   - Rounds 2-3: Lock in positions (narrow the space)
   - Rounds 4+: Fine-tune (should be obvious)

5. **Position-by-position thinking beats random**
   - For each position: "What colors should I test here?"
   - Not: "What random guess feels right?"

