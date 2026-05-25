# Prompt Engineering Improvements Log

**Goal:** Improve Llama 3.1 8B's ability to solve Mastermind puzzles through better prompts

**Current Status:** Agents generate valid guesses but don't reason about constraints effectively

---

## Phase 1: Foundation - Game Understanding

### Task: Ensure agents deeply understand Mastermind rules and logic

**What agents need to understand:**
1. Exact game mechanics (4-6 pegs, feedback meaning)
2. Constraint extraction (what "2 correct_pegs, 1 correct_position" means)
3. Elimination logic (which codes are now impossible)
4. Search strategy (how to systematically narrow down)

**Approach:**
- [ ] Create GAME_MECHANICS.md explaining Mastermind to LLMs
- [ ] Research other implementations (academic papers, open-source projects)
- [ ] Document what worked in other projects
- [ ] Apply best practices to our prompts

---

## Test Results Template

**Version:** [v1, v2, etc]
**Date:** [Date]
**Test Puzzle:** [Puzzle ID]
**Difficulty:** [easy/medium/hard]
**Secret:** [The code]

**Results:**
- Success: [Yes/No]
- Guesses: [Number]
- Time: [Seconds]
- Notes: [What worked/didn't work]

---

## Test Results - Easy Puzzle (MM_005)
**Secret:** ['white', 'black', 'black', 'green']  
**Config:** 4 pegs, 6 colors

### Baseline (Original Prompts)
- Success: ✗ FAILED
- Guesses: 0/8
- Time: ~142s  
- Notes: Agents generated no valid guesses (prompts didn't explain game rules)

### Version 1: Improved Prompts with Examples
**Changes:**
- Analyzer: Added 4 worked examples showing constraint extraction
- Proposer: Added Tree-of-Thoughts with 6 worked examples + 3 candidate generation
- Both: Minimal rule definitions (1-3 lines) per academic research

**Results:**
- Success: ✗ FAILED
- Guesses: 7/8
- Time: ~153s
- Notes: Agents repeated same guess after learning new information. Core issue: **multi-round constraint extraction was incorrect**

### Version 2: Analyzer with Position-Change Detection + Proposer Validation
**Changes:**
- Analyzer: Added validation to catch constraint extraction errors
  - Checks if locked_positions count matches correct_positions feedback
  - Uses position-change heuristic to identify newly-locked positions
- Proposer: Added validation layers
  - Checks locked position constraints and fixes violations
  - Detects and prevents duplicate consecutive guesses
  - Extracts locked positions from constraint text

**Results:**
- Success: ✗ FAILED
- Guesses: 8/8
- Time: ~167s
- Guess sequence: 
  1. ['red', 'blue', 'green', 'yellow'] → 1 peg
  2. ['black', 'blue', 'green', 'yellow'] → 2 pegs (found black!)
  3. ['red', 'blue', 'green', 'yellow'] → 1 peg (back to round 1!)
  4-8. Various partial changes, but no systematic improvement

**Root Cause Analysis:**
- ✓ Locked position constraint enforcement works
- ✓ Duplicate guess prevention works
- ✗ **Constraint extraction still fails on multi-round scenarios**
  - Example: After round 2 (2 pegs, 0 positions), analyzer incorrectly identifies which colors are in the secret
  - LLM guesses that red is misplaced, but feedback doesn't support this
  - With only aggregate feedback, can't uniquely determine color identity when multiple colors change

## Modifications Log

| Version | Date | Changes | Analyzer | Proposer | Results |
|---------|------|---------|----------|----------|---------|
| v0 | baseline | None | Generic prompt | Generic prompt | 0/8 guesses |
| v1 | Day 1 | Tree-of-Thoughts + Examples | 4 examples | 6 examples + 3 candidates | 7/8 (repeated guesses) |
| v1.1 | Day 1 | Position change detection | Validation logic | - | Partial fix (constraint count) |
| v2 | Day 1 | Full validation suite | + Multi-round example | + Locked constraint enforcement + Duplicate prevention | 8/8 (varied but ineffective) |

## Key Findings

### What Worked
1. **Explicit examples better than rules** - Adding worked examples improved reasoning
2. **Validation layers catch errors** - Can enforce constraints programmatically
3. **Position-change heuristic helps** - Identifying which positions actually changed reduces false positives
4. **Duplicate prevention** - Helps agents explore search space rather than repeating

### What Didn't Work
1. **LLM constraint extraction on ambiguous feedback** - When multiple colors change between rounds, LLM makes unsupported guesses
2. **Tree-of-Thought without logical grounding** - Generating 3 candidates is good, but if all violate logical constraints, selection is random
3. **Prompts alone insufficient for constraint satisfaction** - Even with great prompts, pure LLM approaches struggle with combinatorial reasoning

### Why Prompts Hit a Ceiling
- **Information ambiguity:** With only feedback counts (correct_pegs, correct_positions), multiple interpretations exist
- **Combinatorial explosion:** As guess history grows, reasoning about constraint combinations becomes intractable for LLMs
- **Logical inference required:** Pure LLM reasoning isn't strong enough; need symbolic constraint solver
- **Model capability limit:** Llama 3.1 8B doesn't have sufficient reasoning capability even with perfect prompts

## Recommended Next Steps

### Short-term (Prompt-only)
1. Add explicit ambiguity resolution in prompts
   - When feedback is ambiguous, generate all possible interpretations
   - Test each in a hypothetical next round
2. Implement constraint voting
   - Have multiple interpretations compete for best explanation of feedback
3. Add symbolic constraint representation
   - Force agents to output formal constraints that can be validated programmatically

### Medium-term (Hybrid)
1. **LLM + Constraint Solver approach**
   - Use LLM for initialization and hypothesis generation
   - Use symbolic solver (e.g., Z3, PySAT) for constraint checking
   - Have agents collaborate: LLM proposes, Solver validates/fixes
2. **Larger model** (if available)
   - Claude 3.5 Sonnet or Opus likely have better reasoning
   - Test with better models to see if reasoning improves

### Long-term (Architecture)
1. **Hybrid multi-agent system**
   - LLM agents for strategy and communication
   - Symbolic agents for constraint reasoning
   - Each uses strengths: LLM for intuition, Solver for logic
2. **Knowledge representation**
   - Represent constraints in first-order logic
   - Use formal methods for verification
3. **Search algorithm integration**
   - Implement minimax or MCTS for guess selection
   - Use LLM to generate candidate moves, algorithm to score them

