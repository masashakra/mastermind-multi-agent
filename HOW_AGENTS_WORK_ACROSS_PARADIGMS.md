# How Agents Work Across Paradigms

**Key Insight:** The agents **don't know which paradigm they're in!**

---

## Quick Answer

The agents are **paradigm-agnostic**. They:
1. Take input (game state, feedback, constraints)
2. Process via LLM
3. Return output

They don't know or care which paradigm is using them.

**The paradigm knows about the agents, but not vice versa.**

---

## Why This Matters

This is elegant architecture:

```
Agent Job: "Think about the problem and give me your answer"
→ Agent doesn't care WHO is asking (Boss? Peer? Judge?)

Paradigm Job: "Organize agents in a specific pattern"
→ Paradigm doesn't care if agents are smart or dumb
→ Paradigm just coordinates communication
```

---

## Proof: What's Inside Agents

### Agent Initialization

**Strategist:**
```python
def __init__(self, provider: str = "ollama", comm_layer: Optional[A2ACommunicationLayer] = None):
    super().__init__(name="Strategist", provider=provider, comm_layer=comm_layer)
```

Parameters:
- ✓ `provider`: Which LLM to use (ollama, groq, claude)
- ✓ `comm_layer`: How to communicate with other agents (optional)
- ✗ No `paradigm` parameter
- ✗ No `paradigm` field stored

**Analyzer, Proposer, Validator:** Same pattern - no paradigm awareness.

### Agent Methods

**Strategist.propose_strategy():**
```python
def propose_strategy(self, 
                    guess_history: List[Dict[str, Any]], 
                    difficulty: str) -> Dict[str, Any]:
    """Propose strategy for next guess(es)."""
```

Input: Just game data (guess history, difficulty)  
Output: Just strategy analysis (phase, strategy, confidence)  
**Nowhere does it say "I'm in Boss-Worker paradigm"**

**Analyzer.analyze_feedback():**
```python
def analyze_feedback(self,
                    last_guess: List[str],
                    feedback: Dict[str, int],
                    previous_guesses: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Analyze feedback and extract constraints."""
```

Input: Just game data (guess, feedback)  
Output: Just constraints (locked, misplaced, impossible)  
**Nowhere does it say "I'm in Round-Table paradigm"**

Same pattern for Proposer and Validator.

---

## How Does This Work?

### Different Paradigms, Same Agents

**Boss-Worker:**
```python
class BossWorkerOrchestrator:
    def __init__(self, puzzle, provider):
        self.strategist = StrategistAgent(provider=provider)
        self.analyzer = AnalyzerAgent(provider=provider)
        self.proposer = ProposerAgent(provider=provider)
        self.validator = ValidatorAgent(provider=provider)
    
    def run(self):
        # Boss calls agents in sequence
        strategy = self.strategist.propose_strategy(guess_history, difficulty)
        analysis = self.analyzer.analyze_feedback(last_guess, feedback)
        proposal = self.proposer.propose_guess(strategy, constraints, colors, pegs)
        validation = self.validator.validate_guess(proposal, colors, length)
        return validation
```

**Round-Table:**
```python
class RoundTableOrchestrator:
    def __init__(self, puzzle, provider):
        self.strategist = StrategistAgent(provider=provider)
        self.analyzer = AnalyzerAgent(provider=provider)
        self.proposer = ProposerAgent(provider=provider)
        self.validator = ValidatorAgent(provider=provider)
    
    def run(self):
        # Agents call each other directly (different flow)
        analysis = self.analyzer.analyze_feedback(last_guess, feedback)
        strategy = self.strategist.propose_strategy(guess_history, difficulty)
        proposal = self.proposer.propose_guess(strategy, constraints, colors, pegs)
        validation = self.validator.validate_guess(proposal, colors, length)
        return validation
```

**The agents are instantiated the SAME way in both!**

What differs:
- **Boss-Worker:** Boss calls agents (centralized call chain)
- **Round-Table:** Agents call each other (direct pass-off)

The agents don't know about these differences!

---

## The Key Principle

### Separation of Concerns

```
AGENT'S JOB:
├─ Read input
├─ Think about it via LLM
└─ Return output

PARADIGM'S JOB:
├─ Create agents
├─ Decide call order
├─ Pass results between agents
└─ Handle feedback from game

NEITHER KNOWS ABOUT THE OTHER'S JOB
```

### Analogy: A Team of Experts

```
Imagine you have 4 experts:
1. Strategist (plans)
2. Analyzer (understands)
3. Proposer (generates ideas)
4. Validator (checks quality)

Different organizations:
- Boss-Worker: Boss gathers all experts, asks each in sequence
- Round-Table: Experts sit around table, pass notes to each other
- Judge-Mediated: Experts work separately, judge picks best

The EXPERTS don't change!
They don't care HOW they're organized!
They just do their job when asked.
```

---

## Concrete Example: How Boss-Worker Uses Agents

### Round 1 in Boss-Worker

```
BossWorkerOrchestrator.run()
├─ CALL Strategist.propose_strategy()
│  ├─ Strategist receives: guess_history=[], difficulty="easy"
│  ├─ Strategist thinks: "No data yet, test diverse colors"
│  ├─ Strategist returns: {phase: "EXPLORATION", strategy: "..."}
│  └─ Strategist has NO IDEA this is Boss-Worker
│
├─ CALL Analyzer.analyze_feedback()
│  ├─ Analyzer receives: last_guess=[], feedback={}
│  ├─ Analyzer thinks: "No feedback yet, no constraints"
│  ├─ Analyzer returns: {correct_positions: [], impossible_colors: []}
│  └─ Analyzer has NO IDEA this is Boss-Worker
│
├─ CALL Proposer.propose_guess()
│  ├─ Proposer receives: strategy="test diverse", constraints={}, colors=[...]
│  ├─ Proposer thinks: "No constraints, test 4 diverse colors"
│  ├─ Proposer returns: {proposed_guess: [red, white, black, orange]}
│  └─ Proposer has NO IDEA this is Boss-Worker
│
├─ CALL Validator.validate_guess()
│  ├─ Validator receives: guess=[red, white, black, orange], constraints={}
│  ├─ Validator thinks: "Format OK, colors valid, all good"
│  ├─ Validator returns: {is_valid: true}
│  └─ Validator has NO IDEA this is Boss-Worker
│
└─ Boss decides: "All good, submit guess"
```

Notice: Each agent only knows:
- Its own input
- Its own output
- NOT what paradigm it's in

---

## Concrete Example: Same Agents in Round-Table

### Round 1 in Round-Table

```
RoundTableOrchestrator.run()
├─ CALL Analyzer.analyze_feedback()
│  ├─ Analyzer receives: last_guess=[], feedback={}
│  ├─ Returns: {correct_positions: [], impossible_colors: []}
│  ├─ Now, Analyzer calls next agent? NO!
│  └─ Analyzer just returns result, doesn't know about Round-Table
│
├─ CALL Strategist.propose_strategy()
│  ├─ Strategist receives: guess_history=[], difficulty="easy"
│  ├─ Returns: {phase: "EXPLORATION", strategy: "..."}
│  └─ Same agent, same logic, same result!
│
├─ CALL Proposer.propose_guess()
│  ├─ Proposer receives: strategy="...", constraints={}, ...
│  ├─ Returns: {proposed_guess: [red, white, black, orange]}
│  └─ Same agent, same logic, same result!
│
├─ CALL Validator.validate_guess()
│  ├─ Validator receives: guess=[red, white, black, orange], ...
│  ├─ Returns: {is_valid: true}
│  └─ Same agent, same logic, same result!
│
└─ Orchestrator decides: "All good, submit guess"
```

**The agents don't change!** The orchestrator just calls them in a different sequence or pattern.

---

## How Agents Actually Stay Agnostic

### Agent Code Structure

```python
class StrategistAgent(BaseAgent):
    def __init__(self, provider: str = "ollama", 
                 comm_layer: Optional[A2ACommunicationLayer] = None):
        # Store: name, provider, communication layer
        # DON'T store: paradigm, orchestrator, anything about context
        
    def propose_strategy(self, guess_history, difficulty):
        # Takes only DATA, no paradigm info
        # Calls LLM with prompt
        # Returns JSON result
        # Doesn't care who asked or why
```

No agent has:
- ✗ `self.paradigm = "boss-worker"`
- ✗ `self.orchestrator = boss_instance`
- ✗ `self.context = {...paradigm_info...}`

They just have:
- ✓ `self.name = "Strategist"`
- ✓ `self.provider = "ollama"`
- ✓ `self.comm_layer = A2ACommunicationLayer`

---

## The Communication Layer: The Only "Awareness"

Wait, there's one thing: the **communication layer**.

Some paradigms (like Boss-Worker) use A2A protocol:

```python
class BossAgent(BaseAgent):
    def __init__(self, provider, comm_layer=None):
        if comm_layer is None:
            comm_layer = A2ACommunicationLayer()
        
        # Share communication layer with workers
        self.strategist = StrategistAgent(provider=provider, 
                                         comm_layer=self.comm_layer)
        self.analyzer = AnalyzerAgent(provider=provider,
                                     comm_layer=self.comm_layer)
```

**But even this doesn't tell agents the paradigm!**

The communication layer is just: "Here's how to send/receive messages"

It doesn't say: "You're in Boss-Worker" or "You're in Round-Table"

Other paradigms don't even use the communication layer:

```python
class RoundTableOrchestrator:
    def __init__(self, puzzle, provider):
        # No communication layer
        self.strategist = StrategistAgent(provider=provider)
        # comm_layer defaults to None
```

---

## Why This Design?

### Benefit 1: Reusability

Same agent code used in 6 paradigms:
```
Strategist.propose_strategy() 
├─ Used in Boss-Worker
├─ Used in Round-Table
├─ Used in Judge-Mediated
├─ Used in Direct Adversarial
├─ Used in Moderator-Mediated
└─ Used in Direct Debate
```

**If Strategist knew about paradigms, it would need 6x code or complex conditionals:**
```python
# BAD: Paradigm-aware agent
def propose_strategy(self, guess_history, difficulty, paradigm):
    if paradigm == "boss-worker":
        # Boss-worker logic
    elif paradigm == "round-table":
        # Round-table logic
    elif paradigm == "judge-mediated":
        # Judge-mediated logic
    # ...6 times!
```

### Benefit 2: Fair Comparison

Each paradigm gets the **exact same agent logic**:

```
If Strategist results differ in Boss-Worker vs Round-Table:
→ It's because PARADIGM affects results
→ NOT because agent behaves differently
```

### Benefit 3: Flexibility

Easy to:
- Add new paradigm: Just create new orchestrator, it uses existing agents
- Improve agent: Update agent code, all paradigms automatically benefit
- Test agent independently: Don't need paradigm to test agent logic

### Benefit 4: Clear Separation

```
Agents: "Here's my analysis"
Paradigm: "Thanks, I'll route this to the next agent"
Neither needs to know about the other
```

---

## How It Works: The Message Flow

### What Happens When Boss Calls Strategist

```python
# In boss.py
class BossAgent(BaseAgent):
    def orchestrate_round(self, game_state):
        # Boss is orchestrating the round
        # Boss decides to call Strategist
        
        strategy_result = self.strategist.propose_strategy(
            guess_history=game_state["guess_history"],
            difficulty=game_state["difficulty"]
        )
        
        # Strategist returns result
        # Strategist never knows it was called by a Boss
        # Strategist never knows this is part of orchestration
```

**Strategist only knows:**
- "Someone called me with this data"
- "I processed it with my LLM"
- "I'm returning this result"

**Strategist doesn't know:**
- Who called it (Boss? Orchestrator? Other agent?)
- What paradigm it's in
- What will happen with the result

---

## Summary: The Clean Architecture

```
┌─────────────────────────────────────┐
│     PARADIGM ORCHESTRATOR            │
│  (Boss-Worker, Round-Table, etc.)   │
│                                      │
│  ├─ Creates agents                   │
│  ├─ Calls agents in specific order  │
│  ├─ Routes results between agents   │
│  └─ Submits final guess to game     │
│                                      │
│  KNOWS: Agent.propose_strategy()    │
│         Agent.analyze_feedback()    │
│         But NOT about paradigm      │
│                                      │
└────────────┬────────────────────────┘
             │
             ├─ Calls: propose_strategy(guess_history, difficulty)
             │
      ┌──────────────────────────┐
      │  STRATEGIST AGENT         │
      │                           │
      │  ├─ Reads input          │
      │  ├─ Calls LLM            │
      │  └─ Returns output       │
      │                           │
      │  KNOWS: game data         │
      │  DOESN'T KNOW: paradigm   │
      └──────────────────────────┘
```

**This is why the same 4 agents work in 6 different paradigms!**

---

## Key Takeaway

**Agents are paradigm-agnostic tools.**

They take input, think, return output.

**Paradigms are orchestration patterns.**

They coordinate agents in different ways.

**Neither knows about the other - and that's the beauty of the architecture!**

---

**Created:** May 31, 2026  
**Purpose:** Explain why agents don't know which paradigm they're in
