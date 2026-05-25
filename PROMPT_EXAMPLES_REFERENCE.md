# Exact Prompt Examples from Academic Papers

Quick reference guide with exact prompt text from the papers.

---

## 1. TREE OF THOUGHTS - GAME OF 24

### From: https://github.com/princeton-nlp/tree-of-thought-llm/blob/master/src/tot/prompts/game24.py

#### Prompt 1: Standard Prompt (Basic Rule Statement)
```
Use numbers and basic arithmetic operations (+ - * /) to obtain 24.
```

#### Prompt 2: Chain-of-Thought Prompt (Rule + Constraint)
```
Use numbers and basic arithmetic operations (+ - * /) to obtain 24.
Each step, you are only allowed to choose two of the remaining numbers to obtain a new number.
```

#### Prompt 3: Propose Prompt (5-Shot Example + Format)
Structure: Shows 5 examples of intermediate steps, then instructs model to generate next steps.

Example format:
```
Input: 4 5 6 10

Examples of intermediate steps:
4 + 5 = 9 (left: 6 9 10)
6 * 10 = 60 (left: 4 5 60)
5 - 4 = 1 (left: 1 6 10)
4 * 5 = 20 (left: 6 10 20)
10 - 6 = 4 (left: 4 4 5)

Now generate 5 possible next steps for input: [numbers]
```

#### Prompt 4: Value Prompt (Thought Evaluation)
```
Evaluate whether the following numbers can reach 24 as:
sure/maybe/impossible

[Numbers]: [Evaluation]
```

#### Prompt 5: Value Last Step Prompt (Final Validation)
```
Evaluate whether the following equation uses each input exactly once 
and no other numbers, and reaches 24:
[Equation] = 24
```

---

## 2. CHAIN-OF-THOUGHT PROMPTING

### From: Wei et al. "Chain-of-Thought Prompting Elicits Reasoning"

#### Prompt Example 1: Odd Number Sum (Few-Shot with CoT)

```
Q: The odd numbers in this group add up to an even number: 4, 8, 9, 15, 12, 2, 1
A: Adding all the odd numbers (9, 15, 1) gives 25. The answer is False.

Q: The odd numbers in this group add up to an even number: 15, 32, 5, 13, 82, 7, 1
A: Adding all the odd numbers (15, 5, 13, 7, 1) gives 41. The answer is False.

Q: The odd numbers in this group add up to an even number: 2, 4, 16, 9
A: Adding all the odd numbers (9) gives 9. The answer is False.

Q: The odd numbers in this group add up to an even number: 4, 8, 9, 15, 12, 2, 1
A:
```

#### Prompt Example 2: Zero-Shot Chain-of-Thought (No Examples)

```
Q: A juggler can juggle 16 balls. Another juggler can juggle 20 balls. 
If the first juggler uses reds and the second uses blues, and red balls 
cost $0.5 each and blue balls cost $0.6 each, what is the total cost 
for all the balls?

A: Let's think step by step.
```

#### Key observation:
The zero-shot prompt with "Let's think step by step" appended often performs as well as 
multi-shot prompts, though few-shot with explicit reasoning chains is most reliable.

---

## 3. LOGIC-LM FRAMEWORK

### Three-Component Structure (from arxiv 2305.12295)

#### Component 1: Natural Language Problem (Beginning)
```
Problem statement in natural language.
(Example: "All people who work in the bakery are bakers. 
All bakers who work in the bakery bake. Explain why this is consistent.")
```

#### Component 2: Translation Instruction (Middle)
```
Translate the above problem into First-Order Logic (FOL):

[Provide variables and logical expressions]
```

OR

```
Translate the above problem into Constraint Satisfaction Problem (CSP) format:

Variables: [list]
Domain: [values per variable]
Constraints: [list constraints]
```

#### Component 3: Self-Refinement Loop (Error-driven)
```
Previous translation:
[LLM's previous output]

Solver error:
[Error message from symbolic solver]

Please revise your translation to fix the error:
```

---

## 4. GPT-3 FEW-SHOT LEARNING

### From: Brown et al. "Language Models are Few-Shot Learners"

#### Example 1: Translation Task (Few-Shot Format)

```
Q: What is the French word for pen?
A: stylo

Q: What is the French word for book?
A: livre

Q: What is the French word for dog?
A: chien

Q: What is the French word for cat?
A:
```

#### Example 2: Sentiment Analysis (Few-Shot)

```
This movie was amazing! Sentiment: positive

The acting was terrible. Sentiment: negative

It was just okay. Sentiment: neutral

This film is incredible and moving! Sentiment:
```

#### Key finding:
Few-shot learning provides K examples (typically 8-100) before the test case.
Performance improves with more examples, though diminishing returns kick in beyond 10.

---

## 5. CONSTRAINTLLM FRAMEWORK

### From: ConstraintLLM (arxiv 2510.05774)

#### Prompt Structure Template

```
You are a Python programming expert capable of using the pycsp3 library 
to solve Constraint Satisfaction Problems. Generate a syntactically and 
semantically correct constraint solving model.

Problem:
[Natural language problem description]

Variables to define:
[List of variables and their domains]

Constraints to satisfy:
[List of constraints]

Example 1:
Problem: [example problem]
Code:
```python
[pycsp3 code solution]
```

Example 2:
Problem: [example problem]
Code:
```python
[pycsp3 code solution]
```

Now solve this problem:
Problem: [target problem]
Code:
```python
[GENERATE THIS]
```
```

---

## 6. MASTERMINDEVAL BENCHMARK

### Mastermind Game Rules (from documentation)

#### Rule Explanation
```
Mastermind is a code-breaking game:

1. The Codemaker chooses a secret code of 4 colored pegs
2. The Codebreaker tries to guess the code within 10 attempts
3. After each guess, the Codemaker provides feedback:
   - Black peg: correct color in correct position
   - White peg: correct color in wrong position
   - No peg: color not in the code

Example:
Secret code: 1 2 3 4
Guess 1: 4 2 5 6
Feedback: 1 black (the 2), 1 white (the 4)
```

#### Prompt-Based Evaluation Template
```
Game History:
Guess 1: 1 2 3 4 → Feedback: 0 black, 0 white
Guess 2: 5 6 7 8 → Feedback: 1 black, 0 white
Guess 3: 5 1 2 3 → Feedback: 0 black, 2 white
Guess 4: 5 2 1 3 → Feedback: 2 black, 0 white

What is the secret code? (Given the above constraints, only one code is possible)
```

---

## 7. CONSTRAINT-COMPLIANT NETWORK OPTIMIZATION

### Six-Component Prompt Structure (from arxiv 2509.07492)

```
TASK: [Task description]

SOLUTION VARIABLES:
- Variable 1: [format specification]
- Variable 2: [format specification]

CONSTRAINTS:
1. [Constraint 1 in natural language]
2. [Constraint 2 in natural language]
3. [Constraint 3 in natural language]

DOMAIN RULES:
[Domain-specific rules and context]

OUTPUT FORMAT:
[Exact format specification with example]

VALIDATION CRITERIA:
[How correctness will be evaluated]

Now generate a solution for:
[Specific problem instance]
```

---

## 8. RECAST: MULTI-CONSTRAINT INSTRUCTION FOLLOWING

### Multi-Constraint Prompt Template (from arxiv 2505.19030)

```
INSTRUCTIONS:
[Primary task description]

CONSTRAINTS:
- Constraint Type 1: [specific requirement]
- Constraint Type 2: [specific requirement]
- Constraint Type 3: [specific requirement]
- Constraint Type 4: [specific requirement]

INPUT:
[Content to process]

OUTPUT FORMAT:
[Specification of expected output format]

EXAMPLE:
Input: [example input]
Output: [example output that satisfies ALL constraints]

Now complete the task:
[Actual task input]
```

Example constraint types:
- Length: "Your response must be between 100-150 words"
- Content: "Must include definitions for X, Y, and Z"
- Format: "Use JSON format with keys: name, description, score"
- Negation: "Never mention competitors"
- Style: "Use formal professional tone"
- Logical: "If mentioning cost, also mention benefits"

---

## 9. PROMPTING GUIDE - PRACTICAL EXAMPLES

### From: https://www.promptingguide.ai/techniques/cot

#### Basic Few-Shot CoT Example

```
Problem: 4, 8, 9, 15, 12, 2, 1 (which are odd and sum to even?)
Answer: Adding the odd numbers (9, 15, 1) gives 25. The answer is False.

Problem: 15, 32, 5, 13, 82, 7, 1 (which are odd and sum to even?)
Answer: Adding the odd numbers (15, 5, 13, 7, 1) gives 41. The answer is False.

Problem: 2, 4, 16, 9 (which are odd and sum to even?)
Answer:
```

---

## 10. PATTERN SUMMARY: WHAT'S CONSISTENT ACROSS ALL EXAMPLES

### Across all academic papers, successful prompts follow this pattern:

1. **Rule Statement** (1-3 sentences)
   - Concise, clear objective
   - Constraint explanation if needed

2. **Format Specification**
   - Show exact output format
   - May use examples to illustrate

3. **Few-Shot Examples** (2-8 typical)
   - Same structure/format as target
   - Include reasoning steps if task is complex
   - Placed immediately before target task

4. **Task Specification**
   - The actual problem to solve
   - Same format as examples
   - Clear input/output boundaries

5. **Optional: Evaluation Criteria**
   - How correctness will be assessed
   - Especially important for complex tasks

### Critical Insight:
**Format > Rules. Show > Tell.**
- Examples matter more than explicit rule statements
- Consistent formatting across all examples is critical
- Placing examples near the task (not at prompt start) improves performance

---

**Reference compiled**: May 15, 2026  
**Based on**: 9 academic papers on game-solving and constraint reasoning with LLMs

