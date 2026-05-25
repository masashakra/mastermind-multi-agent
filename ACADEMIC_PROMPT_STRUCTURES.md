# Academic Paper Prompt Structures: Game-Solving and Constraint Reasoning

A comprehensive analysis of how leading academic papers structure prompts for game-solving and constraint reasoning tasks.

---

## 1. TREE OF THOUGHTS (ToT) PAPER - Game of 24

**Paper**: Tree of Thoughts: Deliberate Problem Solving with Large Language Models  
**Authors**: Yao et al. (2023)  
**Citation**: arxiv 2305.10601  
**Code Repository**: https://github.com/princeton-nlp/tree-of-thought-llm

### Prompt Structure Overview

The ToT framework uses a **multi-phase prompting approach** for Game of 24:

#### Phase 1: Rule Explanation (Standard Prompt)
**Location**: Beginning  
**Rule Format**: Natural language  
**Length**: 1 line

```
"Use numbers and basic arithmetic operations (+ - * /) to obtain 24."
```

#### Phase 2: Chain-of-Thought Baseline (CoT Prompt)
**Location**: Before task  
**Rule Format**: Natural language + constraint  
**Length**: 2 lines

```
"Use numbers and basic arithmetic operations (+ - * /) to obtain 24. 
Each step, you are only allowed to choose two of the remaining numbers 
to obtain a new number."
```

#### Phase 3: Thought Generation (Propose Prompt)
**Location**: In prompts during tree search  
**Rule Format**: Structured format with examples  
**Length**: 5-shot examples + template

The **propose_prompt** generates possible next arithmetic steps from given numbers.

**Format Pattern**:
```
2 + 8 = 10 (left: 8 10 14)
```

Key features:
- Shows intermediate arithmetic operation
- Lists remaining available numbers in parentheses
- Uses consistent formatting for pattern matching

#### Phase 4: Thought Evaluation (Value Prompt)
**Location**: At each tree node during search  
**Rule Format**: Judgment categories  
**Length**: Short classification task

Evaluates candidate thoughts with judgments:
```
"sure" / "likely" / "impossible"
```

**Purpose**: 
- Promote correct partial solutions that can reach 24 within few lookahead trials
- Eliminate impossible partial solutions based on "too big/small" commonsense
- Keep uncertain solutions as "maybe"

#### Phase 5: Final Answer Validation (Value Last Step Prompt)
**Location**: At leaf nodes  
**Rule Format**: Formal validation criteria  
**Length**: Multi-part validation

Validates final answers by checking:
```
"use each input exactly once and no other numbers, and reach 24"
```

### Task Decomposition Strategy

**Thoughts broken into**: 3 intermediate equations  
**Candidates per step**: 3-5 proposals typical (tested with k=5)  
**Search strategy**: Breadth-first search (BFS)  
**Best candidates kept**: b=5 at each step

### Performance Results
- **Chain-of-Thought baseline**: 4% success rate (GPT-4)
- **Tree of Thoughts**: 74% success rate
- **Key insight**: Multiple reasoning paths with evaluation beats single linear reasoning

### All Prompts Location
Raw prompt file: `tot/prompts/game24.py` in the GitHub repository

---

## 2. MASTERMINDEVAL PAPER - Mastermind Game

**Paper**: MastermindEval: A Simple But Scalable Reasoning Benchmark  
**Citation**: arxiv 2503.05891  
**Code Repository**: https://github.com/flairNLP/mastermind  
**Hugging Face**: flair collection

### Mastermind Game Rules

**Game Mechanics**:
- Player 1 (Codemaker): Chooses a hidden code (sequence of colored pegs)
- Player 2 (Codebreaker): Must deduce the code from guesses
- Turns allowed: 8-12 attempts
- Feedback per guess: Black and white key pegs

**Feedback System**:
- **Black key peg**: Correct color AND correct position
- **White key peg**: Correct color but WRONG position
- Example: If key is `1234` and guess is `4256`:
  - 1 black peg (the "2" is correct)
  - 1 white peg (the "4" exists but wrong position)

### Three Evaluation Paradigms

#### 1. Agentic Evaluation
- Model autonomously plays the game
- Multi-turn interactive environment
- Model makes guesses and receives feedback iteratively

#### 2. Prompt-Based (Deductive) Evaluation
**Location of rules**: Beginning of prompt  
**Rule format**: Natural language game rules  
**Length**: Comprehensive rule explanation

Model is presented with:
- Pre-played game scenarios (history of guesses + feedback)
- Must deduce the last possible valid code from game history
- Challenge: Only ONE valid code remains given the constraints

#### 3. Multiple-Choice Evaluation
- Model identifies correct code from candidate options
- Simplified evaluation format
- Tests understanding without generation requirement

### Prompt Structure Pattern

The paper indicates the following structure (from documentation):
1. Game rules explained in natural language
2. Example game scenario with history
3. Feedback format explained (black/white pegs)
4. Task instruction (deduce code)
5. Model must reason through constraints

### Key Characteristics

- **Scalable**: Generates infinite puzzle instances
- **Interpretable**: Clear rule-based reasoning required
- **Constraint-heavy**: Pure deductive reasoning under constraints
- **Agentic capability test**: Can model play interactively?

---

## 3. LOGIC-LM PAPER - Logical Reasoning

**Paper**: Logic-LM: Empowering Large Language Models with Symbolic Solvers for Faithful Logical Reasoning  
**Citation**: arxiv 2305.12295  
**Code Repository**: https://github.com/teacherpeterpan/Logic-LLM

### Framework Overview

Logic-LM uses a **three-component prompt structure**:

#### Component 1: Natural Language Problem Statement
**Location**: Beginning  
**Format**: Original problem in natural language  
**Length**: Variable (domain-dependent)

#### Component 2: Symbolic Translation Request
**Location**: Middle - Primary task instruction  
**Rule format**: Formal specifications  
**Length**: Varies by target formalism

The framework translates problems into **FOUR symbolic formats**:
1. **LP** (Linear Programming)
2. **FOL** (First-Order Logic)
3. **CSP** (Constraint Satisfaction Problem)
4. **SAT** (Boolean Satisfiability)

**Example approach**:
- LLM receives: "Translate this problem to FOL formulation"
- LLM outputs: Formal logical expressions
- Solver validates and attempts to solve

#### Component 3: Self-Refinement Loop
**Location**: After symbolic solver feedback  
**Rule format**: Error-driven  
**Length**: Iterative (multiple attempts)

**Process**:
```
Input (Natural Language)
  ↓
LLM Translation
  ↓
Symbolic Solver (attempts inference)
  ↓
Solver Returns: [Error messages OR Solution]
  ↓
IF Error: LLM Refines using error feedback
  ↓
Repeat until solved or max attempts
```

### Key Insight: Neuro-Symbolic Integration

Rather than pure LLM reasoning, the framework leverages:
- **Neural component**: LLM for natural language understanding
- **Symbolic component**: Formal solver for guaranteed correctness
- **Feedback loop**: Solver error messages guide refinement

### Performance Results
- **39.2% improvement** over LLM alone with standard prompting
- **18.4% improvement** over LLM with chain-of-thought prompting
- Tested across 5 datasets in logical reasoning domains

### Prompt Structure Characteristics

| Aspect | Detail |
|--------|--------|
| Rules location | Beginning (problem statement) + during refinement (error messages) |
| Rule format | Natural language + formal logic specifications |
| Rule length | Problem-dependent; can be substantial for complex domains |
| Examples given | Often uses few-shot with domain examples |
| Key innovation | Error feedback from solver drives prompt refinement |

---

## 4. CHAIN-OF-THOUGHT (COT) PROMPTING - Few-Shot Examples

**Paper**: Chain-of-Thought Prompting Elicits Reasoning in Large Language Models  
**Authors**: Wei, Wang et al.  
**Citation**: arxiv 2201.11903

### Few-Shot Prompt Structure

#### Basic Pattern (2+ Examples)

**Location of rules**: Implicit in examples  
**Rule format**: Demonstration-based  
**Number of examples**: 8 for best performance; 2-5 is typical starting point

#### Example 1: Odd Number Sum Problem

```
Prompt:
"The odd numbers in this group add up to an even number: 4, 8, 9, 15, 12, 2, 1
A: Adding all the odd numbers (9, 15, 1) gives 25. The answer is False."

Question:
"The odd numbers in this group add up to an even number: 15, 32, 5, 13, 82, 7, 1
A:"
```

**Structure breakdown**:
1. Problem statement
2. Reasoning chain (identifying odd numbers, summing them)
3. Logical conclusion (check if sum is even)
4. Final answer

#### Example 2: Multi-Step Arithmetic (Zero-Shot CoT variant)

**Prompt structure**:
```
"Q: A juggler can juggle 16 balls. Another juggler can juggle 20 balls. 
If the first juggler uses reds and the second uses blues, and red balls 
cost $0.5 each and blue balls cost $0.6 each, what is the total cost 
for all the balls?

A: Let's think step by step."
```

**Key finding**: Simply adding **"Let's think step by step"** (zero-shot) produces comparable results to few-shot in many cases.

### Few-Shot Prompt Characteristics

| Aspect | Specification |
|--------|---------------|
| Minimum examples | 2 (though 8 is optimal) |
| Maximum useful examples | 5-10 (returns diminish after) |
| Example consistency | ALL examples must have identical structure |
| Format emphasis | Exact formatting is critical for steering output |
| Example placement | Place near end of prompt, just before task |
| Example freshness | Keep examples in active context window |

### What Makes Few-Shot Examples Effective

1. **Pattern recognition**: Models learn from example structures
2. **Format steering**: Consistent formatting across examples ensures consistent output
3. **Reasoning demonstration**: Shows step-by-step thinking process
4. **Implicit rule learning**: Rules emerge from pattern, not explicit statements

### Key Insight: LLMs are Pattern Followers

**Critical finding**: "Language models are pattern-followers more than rule-followers"
- **"Do it like this"** lands better than **"follow these 15 requirements"**
- Examples are more reliable than explicit rules
- Format consistency matters more than explicit instructions

---

## 5. CONSTRAINT SATISFACTION & NEURO-SYMBOLIC APPROACHES

### A. ConstraintLLM Framework

**Paper**: ConstraintLLM: A Neuro-Symbolic Framework for Industrial-Level Constraint Programming  
**Citation**: arxiv 2510.05774

#### Prompt Structure for CSP

**Role assignment**:
```
"You are a Python programming expert capable of using the pycsp3 library 
to solve Constraint Satisfaction Problems. Generate a syntactically and 
semantically correct constraint solving model."
```

**Three-component approach**:

1. **Problem Specification** (rules in natural language)
   - Problem description
   - Variables to define
   - Constraints to satisfy

2. **In-Context Examples** (few-shot demonstrations)
   - Example CSP in natural language
   - Corresponding pycsp3 code
   - Typically 2-5 examples

3. **Target Problem** (actual task)
   - Same format as examples
   - Model generates code to solve

#### Key Characteristics

- Rules are distributed between role statement and examples
- Format specified through programming language (Python/pycsp3)
- Verification step ensures generated code is syntactically correct
- Symbolic solver validates semantic correctness

### B. Constraint-Compliant Network Optimization

**Paper**: Constraint-Compliant Network Optimization through Large Language Models  
**Citation**: arxiv 2509.07492

#### Six-Component Prompt Structure

1. **Solution variable definition**: Specifies expected output format
2. **Constraint enforcement**: Preemptively filters infeasible options
3. **Linguistic constraints**: Narrow solution space within prompt
4. **Context specifications**: Domain-specific rules
5. **Format requirements**: Output structure
6. **Validation criteria**: How to check correctness

#### Constraint Introduction Strategy

**Location**: Multiple places (distributed throughout)
- Some in system prompt (general rules)
- Some in context (domain rules)
- Some implicit in examples
- Some explicit as output format requirements

**Purpose**: Create "lexical and syntactic constraints" within the prompt that preemptively filter the solution space

### C. RECAST: Complex Instruction Following with Constraints

**Paper**: RECAST: Expanding the Boundaries of LLMs' Complex Instruction Following with Multi-Constraint Data  
**Citation**: arxiv 2505.19030

#### Constraint Types in Prompts

Dataset synthesizes **19 constraint types**, including:
- Length constraints ("respond in <100 words")
- Content constraints ("must include X, Y, Z")
- Format constraints ("use JSON format")
- Negation constraints ("never mention X")
- Style constraints ("formal tone")
- Logical constraints ("if X then Y")

#### Evaluation Metric: Hard Constraint Satisfaction Rate (HSR)

Model must satisfy **ALL constraints simultaneously**  
Not partial credit - constraints are combined requirements

#### Prompt Pattern

```
Instructions: [Task description]
Constraints:
- [Constraint 1]
- [Constraint 2]
- ...
- [Constraint N]

Input: [Task content]
Output format: [Specification]
```

---

## 6. IN-CONTEXT LEARNING & FEW-SHOT FUNDAMENTALS

**Paper**: Language Models are Few-Shot Learners  
**Authors**: Brown et al. (GPT-3 paper)  
**Citation**: arxiv 2005.14165

### Few-Shot vs Zero-Shot vs One-Shot

#### Definition
Few-shot learning = Providing K demonstrations at inference time (no weight updates)

Typical range: **K = 10 to 100** examples (within context window limits)

#### Three Evaluation Modes

| Mode | Definition | Performance |
|------|-----------|-------------|
| Zero-shot | No demonstrations, only natural language instruction | Baseline |
| One-shot | Single demonstration example | Modest improvement |
| Few-shot | Multiple demonstrations (typically 8-100) | Significant improvement |

#### Key Finding: More Examples = Better Performance

- Performance improves with **number of examples** (K)
- Performance improves with **model size**
- Few-shot improvement is more dramatic with larger models
- Optimal K varies by task (typically 3-8 for most tasks)

#### Example Context Format

```
Task description in natural language

Example 1:
Input: [example input 1]
Output: [example output 1]

Example 2:
Input: [example input 2]
Output: [example output 2]

...

Example K:
Input: [example input K]
Output: [example output K]

[Test input - expecting output]
```

---

## 7. COMPARATIVE ANALYSIS: RULE PRESENTATION STRATEGIES

### Location of Rules

| Paper | Rules Beginning | Rules Middle | Rules in Context | Rules in Examples |
|-------|-----------------|--------------|-----------------|------------------|
| ToT (Game 24) | ✓ (standard) | ✓ (evaluate prompt) | ✓ (propose prompt) | ✓ (5-shot) |
| MastermindEval | ✓ | ✓ | ✓ | Optional |
| Logic-LM | ✓ (NL problem) | ✓ (translation request) | ✓ (feedback-driven) | ✓ |
| CoT | Implicit | — | — | ✓ (primary) |
| ConstraintLLM | ✓ (role definition) | — | ✓ (examples) | ✓ (2-5 shot) |
| Constraint Network | ✓ | ✓ | ✓ | ✓ |

### Rule Format Comparison

| Paper | Format | Formality |
|-------|--------|-----------|
| ToT | Natural language + structured format | Medium |
| MastermindEval | Natural language game rules | Low-Medium |
| Logic-LM | Natural language + formal logic | High |
| CoT | Demonstration-based (implicit rules) | Low |
| ConstraintLLM | Role-based + code format | High |
| Constraint Network | Distributed (multiple formats) | High |

### Rule Length Comparison

| Paper | Typical Length | Variation |
|-------|--------|-----------|
| ToT Game 24 | 1-2 lines (simple rules) | Varies with phase |
| CoT | Implicit, learned from examples | 2-5 shot examples |
| Logic-LM | Problem-dependent | Substantial for complex domains |
| ConstraintLLM | Brief role definition + examples | Examples 20+ lines typical |
| Constraint Network | 3-6 distinct constraint sections | Per-component length varies |

### Number of Examples

| Paper | Typical Examples | Range |
|-------|-----------------|-------|
| ToT | 1-shot or 5-shot | 1-5 |
| CoT | 8 optimal | 2-10 |
| GPT-3 (Few-shot) | 10-100 | 10-100 typical |
| ConstraintLLM | 2-5 | 1-5 |
| Game 24 proposals | 5-shot | 3-5 |

---

## 8. KEY PATTERNS & BEST PRACTICES

### What Works Across Papers

1. **Multi-phase prompting**: Start with rules, follow with examples, then with task-specific instructions
2. **Example freshness**: Place examples near the task (not at the beginning)
3. **Format consistency**: Identical structure across all examples
4. **Implicit vs explicit rules**: Examples teach better than explicit rules alone
5. **Task decomposition**: Break complex tasks into evaluable steps
6. **Feedback loops**: Use solver/validator output to refine responses (neuro-symbolic)

### Rule Presentation Findings

**Finding 1: Rules don't stand alone**
- Most papers combine rules with examples
- Pure rule lists are less effective than rule-demonstration combos

**Finding 2: Distribution works**
- Spreading rules across prompt is more effective than concentrating them
- General rules at start, specific rules near task
- Context-specific rules embedded in examples

**Finding 3: Format specification is critical**
- Exact output format matters more than stating rules
- Show format through examples, not just description

**Finding 4: Constraint languages vary by domain**
- Game rules: Natural language (simple, clear)
- Logic problems: First-order logic (formal)
- Programming tasks: Python/code format
- Reasoning tasks: Structured chains-of-thought

### Optimal Example Counts

- **Minimum**: 2-3 examples (shows pattern)
- **Typical effective**: 5-8 examples
- **Diminishing returns**: Beyond 10 examples
- **Over-prompting risk**: 15+ examples can degrade performance

---

## 9. REFERENCES & SOURCES

1. **Tree of Thoughts (ToT)**
   - Paper: https://arxiv.org/abs/2305.10601
   - Code: https://github.com/princeton-nlp/tree-of-thought-llm
   - Prompts location: `src/tot/prompts/game24.py`

2. **MastermindEval**
   - Paper: https://arxiv.org/abs/2503.05891
   - Code: https://github.com/flairNLP/mastermind
   - Hugging Face: https://huggingface.co/collections/flair/mastermindeval-67cb01daedbee142edd594ea

3. **Logic-LM**
   - Paper: https://arxiv.org/abs/2305.12295
   - Code: https://github.com/teacherpeterpan/Logic-LLM
   - ACL Anthology: https://aclanthology.org/2023.findings-emnlp.248/

4. **Chain-of-Thought Prompting**
   - Paper: https://arxiv.org/abs/2201.11903
   - Guide: https://www.promptingguide.ai/techniques/cot

5. **GPT-3 Few-Shot Learning**
   - Paper: https://arxiv.org/abs/2005.14165
   - Proceedings: https://proceedings.neurips.cc/paper/2020/file/1457c0d6bfcb4967418bfb8ac142f64a-Paper.pdf

6. **ConstraintLLM**
   - Paper: https://arxiv.org/abs/2510.05774

7. **Constraint-Compliant Network Optimization**
   - Paper: https://arxiv.org/abs/2509.07492

8. **RECAST: Complex Instruction Following**
   - Paper: https://arxiv.org/abs/2505.19030

9. **Prompt Engineering Guides**
   - Prompting Guide: https://www.promptingguide.ai/
   - Claude API Docs: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/

---

## 10. PRACTICAL IMPLEMENTATION GUIDELINES

### For Game-Solving Tasks (like Mastermind, Game of 24)

**Recommended structure**:
```
1. Rule explanation (1-2 sentences, natural language)
2. Format specification (show expected output format)
3. Examples (3-5 demonstrations with same format)
4. Evaluation criteria (how to judge correctness)
5. Task specification (the actual game instance)
```

### For Constraint Reasoning Tasks

**Recommended structure**:
```
1. Problem specification in natural language
2. Constraint list (clear enumeration)
3. Examples (show how constraints apply)
4. Output format specification
5. Validation criteria
6. Target problem
```

### For Logical Reasoning Tasks

**Recommended structure**:
```
1. Natural language problem
2. Translation instruction (to formal representation)
3. Example translations (2-3 shot)
4. Feedback on previous attempt (if iterative)
5. Refinement request (if needed)
```

---

**Document compiled**: May 15, 2026  
**Source**: Analysis of 9 major academic papers on game-solving and constraint reasoning with LLMs

