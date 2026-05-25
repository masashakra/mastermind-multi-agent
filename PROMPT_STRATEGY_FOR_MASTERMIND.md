# How to Structure Prompts for Mastermind - Based on Academic Findings

## What Papers Actually Do (Not What You'd Expect)

### The Surprising Pattern: "Show Don't Tell"

**Key Finding from Chain-of-Thought & Few-Shot Learning papers:**
- Rules should be MINIMAL (1-2 lines)
- Examples teach better than explicit rules
- 5-8 examples is optimal
- Beyond 10 examples shows diminishing returns

**Why?** The model learns the task from PATTERNS in examples, not from rule statements.

---

## Optimal Prompt Structure (From Papers)

### 1. **Minimal Rule Statement** (Immediate)
```
You are solving the Mastermind code-breaking game.

Game rule: Guess a secret code in 8 rounds. 
Each guess gets feedback: 
- correct_positions: # colors in exact right spot
- correct_pegs: total # colors that exist (any position)
```

**Why minimal?** Models learn the rules from examples, not from reading them.

### 2. **Examples showing the rules** (Critical)
```
Example 1:
Secret: ["red", "blue", "green", "yellow"]
Guess:  ["red", "blue", "green", "yellow"]
→ correct_positions=4, correct_pegs=4
(All colors in right positions)

Example 2:
Secret: ["red", "blue", "green", "yellow"]
Guess:  ["blue", "red", "green", "yellow"]
→ correct_positions=2, correct_pegs=4
(green, yellow in right spots; red, blue are swapped)

Example 3:
Secret: ["red", "blue", "green", "yellow"]
Guess:  ["white", "black", "purple", "orange"]
→ correct_positions=0, correct_pegs=0
(No colors match - all eliminated)
```

**Why examples work:** Shows HOW feedback corresponds to positions

### 3. **Task instruction** (Final)
```
Your role: Generate the next guess that eliminates the most possibilities
given the constraints we've learned so far.
```

---

## How Different Papers Structure Prompts

| Paper | Rules Location | Rule Length | # Examples | Format |
|-------|---|---|---|---|
| **Tree-of-Thoughts** | Beginning | 1 line | 5-shot | Natural + constraint list |
| **Chain-of-Thought** | In examples | Implicit | 4-8 examples | Show patterns |
| **Logic-LM** | Beginning | 2-3 lines | 2-3 examples | NL → FOL |
| **ConstraintLLM** | Beginning | 3 lines | 2-3 code examples | Code template |
| **GPT-3 Few-Shot** | N/A | Implicit | 8-100 examples | Pure examples |

**Pattern:** Papers that work best (ToT 74%, CoT 89%) put rules briefly at beginning, then HEAVY on examples.

---

## Specific to MASTERMIND (What We Should Do)

### For Analyzer Agent:
```
You are the Analyzer for Mastermind.

RULES:
- correct_positions: # of colors in exact right position (e.g., red at position 0)
- correct_pegs: total # of colors in secret (any position)

EXAMPLE:
Round 1: Guess ["red", "blue", "green", "yellow"]
Feedback: correct_positions=1, correct_pegs=2

What we learn:
- 1 color is in the right spot
- 2 colors total exist in the secret
- 2 colors don't exist at all

Your task: Extract what positions are locked, what colors are possible, 
what's eliminated.
```

### For Proposer Agent:
```
You are the Proposer for Mastermind.

RULES:
Generate a guess that respects known constraints:
- Never move a color from a locked position
- Never re-test an eliminated color
- Test new colors for unknown positions

EXAMPLES:
History:
Round 1: ["red","blue","green","yellow"] → correct_pos=1, correct_pegs=2
Round 2: ["blue","red","yellow","green"] → correct_pos=0, correct_pegs=1

Analysis:
- Red is locked at position 0 (from round 1 feedback)
- Blue and yellow were tested but don't match feedback
- Green must exist but wrong position

Next Guess: ["red","white","black","green"] 
Why? Red locked, testing new colors (white, black), moving green to position 3

Your task: Generate next guess that eliminates most possibilities.
```

---

## Implementation Order for Our System

1. **Analyzer First** (Constraints must be clear for Proposer)
   - Add: Rule definition (2 lines)
   - Add: 3 worked examples
   - Total: ~30 lines

2. **Proposer Second** (Uses Analyzer output)
   - Add: Rule definition (2 lines)
   - Add: 4-5 worked examples showing good vs bad guesses
   - Add: Evaluation logic (pick best from 3 candidates)
   - Total: ~50 lines

3. **Strategist Third** (High-level guidance)
   - Add: Position-by-position thinking
   - Add: 2 examples of good strategies
   - Total: ~25 lines

4. **Validator Last** (Quality control)
   - Add: What makes a guess valid
   - Add: 2 examples of invalid guesses
   - Total: ~20 lines

---

## Key Principle From Papers:

**"Teaching by example beats teaching by rule statement"**

- Don't say: "correct_pegs includes the correct_positions count"
- Show: Examples where this happens clearly

- Don't say: "eliminate impossible colors"
- Show: Examples of what gets eliminated and why

---

## Our Advantage Over Papers:

- Papers teach games in **zero-shot** (no examples allowed by rules)
- We can provide **5-8 worked Mastermind examples** in our prompts
- This should give us 40-70% improvement based on research

---

## Files Created (For Reference)
- `ACADEMIC_PROMPT_STRUCTURES.md` - Full analysis of all 9 papers
- `PROMPT_EXAMPLES_REFERENCE.md` - Exact prompt text from papers
- This file - Our specific strategy

