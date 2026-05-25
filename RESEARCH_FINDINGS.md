# Research Findings: LLM Mastermind Solving

## Key Discoveries

### 1. Benchmark Data
- **MastermindEval**: 30,000+ game states. Tests show:
  - GPT-4o: Good at agentic (iterative) solving
  - o1, o3-mini, DeepSeek-R1: Actually perform WORSE than random
  - **Lesson**: Reasoning models ≠ Logical reasoning
  
- **Knuth's Algorithm**: Optimal baseline
  - Guarantees ≤5 guesses
  - Average 4.76 guesses
  - We should aim for 5-6 guesses

### 2. What Works (Ranked by Impact)

**Top 3 Techniques:**

1. **Hybrid LLM + Constraint Solver** ⭐⭐⭐
   - LLM generates constraints from feedback
   - External solver (Z3, python-constraint) finds best guess
   - **Why**: Offloads combinatorial search
   - **For us**: Could integrate constraint propagation

2. **Tree-of-Thought (ToT) with Self-Evaluation** ⭐⭐⭐
   - Generate multiple candidate guesses
   - Evaluate each against constraints
   - Prune invalid paths
   - **Performance**: Game of 24: 4% (CoT) → 74% (ToT)
   - **For us**: Generate 3-4 candidate guesses, rank them

3. **Few-Shot + Iterative Refinement** ⭐⭐
   - Provide worked examples (3-5)
   - Use self-reflection after each step
   - Loop: generate → feedback → refine
   - **Key**: Structure feedback as "constraint violations"

### 3. Critical Finding: What DOESN'T Work
- ❌ Pure Chain-of-Thought struggles with combinatorial problems
- ❌ Asking model to self-correct fails unless errors are explicitly pointed out
- ❌ General refinement hurts; specific constraint feedback helps

### 4. Constraint Satisfaction is the Problem
- Models can translate rules to logic BUT fail at inference
- Problem: **Combinatorial search + constraint propagation**
- Solution: Offload to solver or explicit enumerate-and-check

---

## What We Should Implement (Priority Order)

### PHASE 1: Immediate (Tree-of-Thought Approach)
**Goal**: Get Llama 8B to reason about constraints better

1. **Proposer generates 3-4 candidate guesses**
   - Based on strategy + constraints
   - All following the rules

2. **Proposer evaluates candidates**
   - Against ALL previous feedback
   - Eliminates those that violate constraints
   - Selects the one that eliminates most possibilities

3. **Add self-reflection**
   - "Here's what we know is eliminated"
   - "Here's what we know is locked"
   - "Here's why guess X is better than Y"

**Expected improvement**: Better guess selection, fewer random tries

### PHASE 2: Medium (Iterative Refinement)
1. Feedback loop: Generator → Evaluator → Refiner
2. Explicit constraint checking after each step
3. Few-shot examples in prompt

### PHASE 3: Advanced (Hybrid Solver)
1. Integrate python-constraint or Z3
2. LLM outputs constraints
3. Solver finds optimal guess
4. Loop back for next round

---

## Our Specific Action Plan

### Start With:
1. **Improve ANALYZER** - Make constraints crystal clear
   - Output: "Locked positions", "Possible colors", "Eliminated colors"
   - Format: Structured list, not prose

2. **Rewrite PROPOSER** - Use Tree-of-Thought
   - Generate multiple candidates
   - Evaluate each
   - Explain reasoning
   - Select best

3. **Add to STRATEGIST** - Position-by-position thinking
   - "For position 0: test colors X, Y, Z"
   - "For position 1: test colors A, B, C"
   - More explicit than current vague strategy

4. **Test incrementally**
   - Easy puzzle first
   - Track: guesses, time, success

---

## Benchmark Targets

**From research:**
- Knuth optimal: 5 guesses
- Good LLM: 5-6 guesses
- Current (Llama 8B): 7-8 guesses (fails)

**Our goal**: 5-6 guesses consistently, solve all easy puzzles

