# Paradigm Architecture - 5 Approaches to Agent Collaboration

## Overview

We're implementing 5 different ways agents can work together to solve Mastermind puzzles. Each paradigm tests a different collaboration model.

---

## Paradigm 1: Boss-Worker ✅ (IMPLEMENTED)

### Architecture
```
           Boss Agent (Orchestrator)
           /      |      |      \
    Strategist Analyzer Proposer Validator
           \      |      |      /
           Sequential Chain
```

### Characteristics
- **Structure:** Hierarchical (one boss, four workers)
- **Communication:** Boss calls each agent in sequence
- **Decision Making:** Boss collects results, passes to next agent
- **Coordination:** Centralized (Boss controls flow)
- **Overhead:** Boss must track all state

### Workflow
1. Boss calls Strategist
2. Boss takes result, calls Analyzer
3. Boss takes result, calls Proposer
4. Boss takes result, calls Validator
5. Validator returns, Boss submits guess

### Pros
- ✅ Centralized control (predictable)
- ✅ Easy to debug (all decisions in one place)
- ✅ Can add explicit checks between steps

### Cons
- ❌ Boss becomes bottleneck
- ❌ Agents less autonomous
- ❌ More overhead (Boss must track context)

### File
`src/paradigms/boss_worker.py`

### Test
`test_boss_worker_kaggle.py`

---

## Paradigm 2: Round-Table 🔄 (IMPLEMENTED TODAY)

### Architecture
```
    Analyzer ←→ Strategist
        ↓           ↓
    Constraints  Strategy
        ↓           ↓
    Proposer ←→ Validator
    (generates)  (approves)
```

### Characteristics
- **Structure:** Peer-to-peer (all equal status)
- **Communication:** Agents call each other directly
- **Decision Making:** Sequential but without boss
- **Coordination:** Distributed (each agent responsible)
- **Overhead:** Less (no central coordinator)

### Workflow
1. Analyzer analyzes feedback, sends constraints to Strategist
2. Strategist receives constraints, proposes strategy, sends to Proposer
3. Proposer receives strategy, generates guess, sends to Validator
4. Validator receives guess, validates, returns result
5. Any agent can submit guess

### Pros
- ✅ More autonomous agents
- ✅ Less overhead (no Boss)
- ✅ Natural information flow (constraint → strategy → proposal)
- ✅ Easier to understand agent responsibilities

### Cons
- ❌ Sequential (agents must wait for each other)
- ⚠️ Harder to control flow
- ⚠️ Debugging spread across multiple agents

### File
`src/paradigms/round_table.py`

### Test
`test_round_table.py`

---

## Paradigm 3: Competition (TODO)

### Proposed Architecture
```
  Proposer1     Proposer2     Proposer3
   ↓ guess      ↓ guess       ↓ guess
   
   Evaluator (picks best)
        ↓
   Selected Guess
```

### Characteristics
- **Structure:** Multiple agents compete
- **Communication:** Parallel (all propose simultaneously)
- **Decision Making:** Winner-take-all or consensus
- **Coordination:** Evaluator ranks proposals
- **Overhead:** Higher (multiple proposals)

### Workflow (Proposed)
1. All agents (Analyzer, Strategist, Proposer) analyze feedback independently
2. Each generates their own guess based on their analysis
3. Evaluator receives all guesses
4. Evaluator ranks by quality/informativeness
5. Best guess submitted
6. Feedback shared with all agents

### Pros
- ✅ Different perspectives (may find better guesses)
- ✅ Parallel processing (faster?)
- ✅ Builds robustness (doesn't rely on one path)

### Cons
- ❌ Multiple redundant analyses
- ❌ Higher token usage
- ❌ Choosing between proposals is hard

### Use Case
When one agent might miss something, multiple perspectives help.

---

## Paradigm 4: Coopetition (TODO)

### Proposed Architecture
```
Phase 1: COOPERATION
  Analyzer + Strategist collaborate
       ↓
  Shared constraint/strategy

Phase 2: COMPETITION
  Proposer1, Proposer2 each propose guess
       ↓
  Evaluator picks best

Phase 3: FEEDBACK SHARE
  All agents learn from feedback
```

### Characteristics
- **Structure:** Phases (coop → competition → feedback)
- **Communication:** Hybrid (group then individual then group)
- **Decision Making:** Collaborative then competitive then collaborative
- **Coordination:** Multiple evaluation points
- **Overhead:** Medium (some redundancy but less than pure competition)

### Workflow (Proposed)
1. **Cooperation Phase:** Analyzer and Strategist work together
   - Analyzer: extract constraints
   - Strategist: plan based on constraints
   - Output: shared analysis

2. **Competition Phase:** Two Proposers generate guesses independently
   - Proposer1: "I'll test this way"
   - Proposer2: "I'll test that way"
   - Output: two candidate guesses

3. **Evaluation Phase:** Pick best guess based on criteria
   - Informativeness (which eliminates more possibilities?)
   - Safety (which respects all constraints?)
   - Output: selected guess

4. **Feedback Share:** All agents learn
   - All agents see feedback
   - Prepares for next round

### Pros
- ✅ Balances cooperation and competition
- ✅ Shared analysis (efficient)
- ✅ Multiple proposals (robust)
- ✅ Good token/result ratio

### Cons
- ❌ More complex coordination
- ❌ Harder to debug (multi-phase)

### Use Case
When you want multiple perspectives but don't want to duplicate work.

---

## Paradigm 5: Experiment (TODO)

### Proposed Variants

#### 5a: Debate/Discussion
```
Analyzer proposes interpretation
Strategist critiques
Proposer refines based on critique
Validator approves

Rounds of discussion until consensus
```

#### 5b: Hierarchical (Different hierarchy than Boss-Worker)
```
Strategist (high level)
  ↓
Analyzer (medium)
  ↓  
Proposer (low level)
  ↓
Validator (final check)
```

#### 5c: Majority Vote
```
All agents propose independently
Vote on best approach
Implement majority choice
```

#### 5d: Expert-Novice
```
Expert agent (Strategist) guides
Novice agent (Proposer) implements
Veteran agent (Analyzer) validates historical knowledge
Watchdog agent (Validator) ensures quality
```

### Characteristics
- **Structure:** Experimental/exploratory
- **Communication:** TBD per variant
- **Decision Making:** TBD per variant
- **Coordination:** TBD per variant
- **Overhead:** Variable

### Purpose
Testing novel approaches, finding what works best.

---

## Comparison Table

| Aspect | Boss-Worker | Round-Table | Competition | Coopetition | Experiment |
|--------|-------------|------------|-------------|-------------|-----------|
| Structure | Hierarchical | Peer-to-peer | Competitive | Hybrid | Flexible |
| Coordination | Centralized | Distributed | Central evaluator | Phased | Variable |
| Overhead | High | Low | Very High | Medium | Variable |
| Parallelism | Sequential | Sequential | Parallel | Phased | Variable |
| Token Usage | Medium | Medium | High | Medium-High | Variable |
| Autonomy | Low | High | Medium | Medium | High |
| Debuggability | High | Medium | Low | Medium | Low |
| Expected Performance | Good | Good? | Better? | Better? | Unknown |

---

## Expected Outcomes

### Hypothesis
- **Boss-Worker:** Good baseline, predictable
- **Round-Table:** Similar to Boss-Worker, but more elegant
- **Competition:** Better guesses (multiple perspectives)
- **Coopetition:** Best balance (cooperation + competition)
- **Experiment:** May find novel solutions

### How We'll Test
1. Run all 30 puzzles through each paradigm
2. Measure:
   - Success rate
   - Average guesses
   - Token usage
   - Execution time
3. Compare results
4. Identify best paradigm(s)

---

## Implementation Status

| Paradigm | Status | File | Test |
|----------|--------|------|------|
| Boss-Worker | ✅ Done | `src/paradigms/boss_worker.py` | `test_boss_worker_kaggle.py` |
| Round-Table | ✅ Done | `src/paradigms/round_table.py` | `test_round_table.py` |
| Competition | ❌ TODO | `src/paradigms/competition.py` | `test_competition.py` |
| Coopetition | ❌ TODO | `src/paradigms/coopetition.py` | `test_coopetition.py` |
| Experiment | ❌ TODO | `src/paradigms/experiment.py` | `test_experiment.py` |

---

## Next Steps

1. **Test Boss-Worker fully** (baseline)
2. **Test Round-Table** (compare to baseline)
3. **Implement Competition** (ambitious/exploration)
4. **Implement Coopetition** (balanced approach)
5. **Experiment with variants** (find best)
6. **Analyze results** (which paradigm wins?)
7. **Optimize winner** (enhancements)

---

## Running Paradigm Comparison

Eventually, we'll have a master test that runs all paradigms:

```bash
# Test all paradigms on same puzzle set
python3 test_all_paradigms.py

# Output:
# Boss-Worker:    8/10 solved, avg 5.5 guesses
# Round-Table:    8/10 solved, avg 5.4 guesses
# Competition:    9/10 solved, avg 5.2 guesses
# Coopetition:    9/10 solved, avg 5.1 guesses
# Experiment-A:   7/10 solved, avg 6.0 guesses
```

Then choose the best!

