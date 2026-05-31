# System Architecture Explained

**Purpose:** Understand why the system is designed this way and how everything works  
**Audience:** Developers, thesis writers, system researchers  
**Date:** May 31, 2026

---

## Quick Summary

**The Big Idea:**
- **4 Fixed Workers:** Strategist, Analyzer, Proposer, Validator (always the same)
- **6 Paradigms:** Different ways of organizing these 4 workers
- **Same Agents, Different Communication:** Each paradigm routes messages differently but uses the same agent logic

**Why?** This lets you compare how *communication patterns* affect performance, not just how *agents* perform.

---

## Part 1: Why All Paradigms Have the Same 4 Agents

### The Research Question

> "How does the **organizational structure** and **communication pattern** affect multi-agent problem solving?"

To answer this, we need to isolate variables:

```
Fixed: Agent logic (each agent's reasoning)
Variable: How agents communicate (paradigm)
```

If we changed agents between paradigms, we couldn't tell if differences came from:
- Better agent design? OR
- Better communication?

### The Solution: Standardized Agents

All 6 paradigms use the same 4 agents:

1. **Strategist** — Analyzes game state, proposes strategy
2. **Analyzer** — Extracts constraints from feedback
3. **Proposer** — Generates next guess respecting constraints
4. **Validator** — Checks guess is valid before submission

**These 4 agents are constant across all paradigms.**

What changes is **how they communicate and coordinate**.

### The 6 Paradigms (Different Communication)

| Paradigm | Structure | Communication | Who Decides |
|----------|-----------|---|---|
| **Boss-Worker** | Centralized | Boss coordinates all agents | Boss |
| **Round-Table** | Peer-to-peer | Agents call each other sequentially | Collective |
| **Judge-Mediated** | Centralized | Judge evaluates competing proposals | Judge |
| **Direct Adversarial** | Peer-to-peer | Agents debate without judge | Self-resolved |
| **Moderator-Mediated** | Centralized | Moderator synthesizes proposals | Moderator |
| **Direct Debate** | Peer-to-peer | Agents negotiate without moderator | Consensus |

**Same agents, 6 different communication patterns.**

### Why This Matters

By keeping agents constant and varying communication:

```
Boss-Worker Performance = Agent Quality + Boss Coordination
Round-Table Performance = Agent Quality + Peer Coordination

Difference = Coordination Impact (isolated variable)
```

This lets you measure: **Does centralization help or hurt?**

---

## Part 2: What Each File Does

### Core System Files

#### `game_engine.py`
**What it is:** The Mastermind game referee

**What it does:**
- Stores secret code (the answer)
- Receives guesses from agents
- Returns feedback: `{correct_pegs, correct_positions, solved}`
- Tracks rounds remaining (max 8)

**Why separate?** Prevents agents from cheating; provides objective truth

**Used by:** Every paradigm (all need to submit guesses)

**Example:**
```python
game = GameEngine(["red", "blue", "green", "yellow"], "easy")
feedback = game.submit_guess(["red", "white", "black", "orange"])
# Returns: {
#   "correct_pegs": 1,           # Red is in code
#   "correct_positions": 1,       # One color in right spot
#   "solved": False,
#   "valid": True
# }
```

---

#### `puzzle_generator.py`
**What it is:** Creates test puzzles

**What it does:**
- Loads/generates Mastermind puzzles with known solutions
- Provides difficulty levels: easy (4 colors), medium (5), hard (6)
- Returns puzzle metadata (ID, colors, difficulty)

**Why separate?** Enables reproducible testing across paradigms

**Used by:** Every paradigm (all need puzzles to solve)

**Example:**
```python
puzzles = load_puzzles()
# Returns: [
#   {
#     "puzzle_id": "MM_001",
#     "secret_code": ["red", "blue", "green", "yellow"],
#     "colors": ["red", "blue", "green", "yellow", "white", "black"],
#     "difficulty": "easy"
#   },
#   ...
# ]
```

---

### Agent Files (The 4 Fixed Workers)

#### `agents/base_agent.py`
**What it is:** Parent class for all agents

**What it does:**
- Handles LLM communication (Groq, Kaggle, Ollama, Claude)
- Parses JSON responses
- Manages API calls and error handling
- Provides communication layer support

**Why separate?** All agents share the same LLM interface; don't repeat code

**Used by:** Every agent (Strategist, Analyzer, Proposer, Validator)

---

#### `agents/strategist.py`
**What it is:** Strategic planner

**What it does:**
- Analyzes game state and history
- Identifies which phase we're in (EXPLORATION, CONSTRAINT_BUILDING, REFINEMENT, CONFIRMATION)
- Proposes next strategy

**Input:** Guess history + feedback  
**Output:** Strategy JSON  
**Why separate?** Strategy planning is a distinct role; can be improved independently

**Used in all paradigms** (all need strategy)

**Improvement (from papers):**
- 4-step Chain-of-Thought reasoning
- Worked example showing reasoning
- Confidence scoring

---

#### `agents/analyzer.py`
**What it is:** Constraint extractor

**What it does:**
- Receives latest feedback
- Identifies which colors are locked (confirmed correct)
- Identifies which colors are misplaced (exist, wrong position)
- Identifies which colors are impossible (don't exist)

**Input:** Last guess + feedback  
**Output:** Constraints JSON  
**Why separate?** Constraint analysis is complex; benefits from dedicated focus

**Used in all paradigms** (all need constraints)

**Improvement (from papers):**
- 5-step constraint extraction logic
- Worked example with full reasoning
- Confidence scoring

---

#### `agents/proposer.py`
**What it is:** Guess generator

**What it does:**
- Takes strategy + constraints
- Generates a guess that respects constraints
- Ensures locked positions stay locked
- Ensures impossible colors aren't used

**Input:** Strategy + Constraints + Available colors  
**Output:** Proposed guess + Justification  
**Why separate?** Guess generation is technical; benefits from dedicated role

**Used in all paradigms** (all need guesses)

**Improvement (from papers):**
- 5-step constraint-respecting reasoning
- Validation checklist before output
- Worked example

---

#### `agents/validator.py`
**What it is:** Quality control / error preventer

**What it does:**
- Checks guess meets format requirements (4 colors, valid colors)
- Checks locked positions are preserved
- Checks impossible colors aren't used
- **Prevents invalid guesses from being submitted**

**Input:** Proposed guess + constraints  
**Output:** Validation JSON (is_valid, errors, warnings)  
**Why separate?** Validation is critical; catches errors from other agents

**Used in all paradigms** (all need validation)

**Improvement (from papers):**
- 6-step validation process (hard + soft checks)
- 4 detailed worked examples
- Confidence scoring

---

### Communication Files

#### `communication/protocol.py`
**What it is:** Standardized message format (A2A Protocol)

**What it does:**
- Defines A2AMessage structure (sender, receiver, action, payload)
- Implements A2ACommunicationLayer for message routing
- Tracks message history and correlation IDs
- Enables request-response pairs

**Why separate?** Communication should be abstracted; can be swapped out

**Used by:** Boss-Worker paradigm (centralized, needs A2A)

**Example message:**
```python
A2AMessage(
    message_id="msg-123",
    sender_id="boss",
    receiver_id="strategist",
    message_type="request",
    action="propose_strategy",
    payload={"guess_history": [...], "difficulty": "easy"},
    correlation_id="req-456"  # Links request to response
)
```

---

#### `communication/agent_card.py`
**What it is:** Agent capability advertisement

**What it does:**
- Describes what each agent can do
- Lists inputs/outputs they accept
- Provides discovery tags

**Why separate?** Enables dynamic agent discovery and capability matching

**Not heavily used** in current paradigms but part of full A2A spec

---

#### `communication/agent_discovery.py`
**What it is:** Agent lookup service

**What it does:**
- Maintains registry of available agents
- Supports capability-based lookup
- Enables dynamic agent selection

**Why separate?** Supports scalability and dynamic systems

**Not heavily used** in current paradigms but part of full A2A spec

---

#### `communication_logger.py`
**What it is:** Message recorder

**What it does:**
- Logs all messages between agents
- Records sender, receiver, message type, content
- Enables analysis of communication patterns
- Tracks token usage per message

**Why separate?** Logging is a cross-cutting concern; shouldn't be in agent code

**Used by:** All paradigms (all log messages)

---

### Paradigm Files (The 6 Communication Patterns)

#### `paradigms/boss_worker.py`
**What it is:** Centralized collaboration

**Structure:**
```
     BOSS
    / | \ \
   /  |  \ \
  S   A   P  V  (Strategist, Analyzer, Proposer, Validator)
```

**How it works:**
1. Boss sends strategy request to Strategist
2. Strategist responds
3. Boss sends analysis request to Analyzer
4. Analyzer responds
5. Boss sends proposal request to Proposer (with strategy + constraints)
6. Proposer responds
7. Boss sends validation request to Validator
8. Validator approves or rejects
9. Boss submits approved guess to GameEngine

**Communication:** Boss → Agent → Boss → Agent → ...

**Characteristics:**
- Centralized coordination
- All decisions go through Boss
- High transparency (Boss sees everything)
- Potential bottleneck at Boss
- Clear control flow

---

#### `paradigms/round_table.py`
**What it is:** Peer-to-peer collaboration

**Structure:**
```
Analyzer → Strategist → Proposer → Validator
   ↑                                    ↓
   ←─────────────────────────────────→
    (results flow, no Boss in middle)
```

**How it works:**
1. Analyzer receives last feedback, extracts constraints
2. Analyzer passes constraints to Strategist
3. Strategist proposes strategy, passes to Proposer
4. Proposer generates guess with strategy + constraints
5. Proposer passes to Validator
6. Validator approves/rejects, passes back

**Communication:** Agent → Agent → Agent → ...

**Characteristics:**
- Peer-to-peer (no coordinator)
- Agents call each other directly
- Sequential but less hierarchy
- Agents have equal status
- More direct communication

---

#### `paradigms/judge_mediated.py`
**What it is:** Competitive evaluation with judge

**Structure:**
```
     JUDGE
    / | \ \
   /  |  \ \
  S   A   P  V (Multiple proposals generated)
```

**How it works:**
1. Multiple agents propose solutions independently
2. Judge evaluates all proposals
3. Judge selects best guess
4. Guess submitted

**Communication:** Judge → Agents → Judge → Select

**Characteristics:**
- Competitive (agents compete)
- Centralized judge
- Agents work independently
- Judge makes final decision
- Tests robustness of proposals

---

#### `paradigms/direct_adversarial.py`
**What it is:** Competitive without judge

**Structure:**
```
Proposals compete directly
- Agent A proposes guess X
- Agent B proposes guess Y
- Conflict resolution without judge
```

**How it works:**
1. Agents independently propose solutions
2. Agents debate/compete without central judge
3. Best proposal wins through reasoning
4. Guess submitted

**Communication:** Agent ↔ Agent (debate)

**Characteristics:**
- Competitive (no judge)
- Peer-to-peer conflict resolution
- Agents must convince each other
- Tests persuasiveness of reasoning

---

#### `paradigms/moderator_mediated.py`
**What it is:** Cooperative synthesis with moderator

**Structure:**
```
     MODERATOR
    / | \ \
   /  |  \ \
  S   A   P  V (Proposals synthesized)
```

**How it works:**
1. All agents propose solutions
2. Moderator synthesizes best elements from each
3. Combined solution submitted

**Communication:** Moderator ↔ Agents ↔ Moderator

**Characteristics:**
- Cooperative (agents help synthesize)
- Centralized moderator
- Agents contribute ideas
- Moderator combines best parts
- Tests collaborative synthesis

---

#### `paradigms/direct_debate.py`
**What it is:** Cooperative negotiation without moderator

**Structure:**
```
Agents negotiate directly
- Agent A: "Try red"
- Agent B: "No, try blue"
- Consensus without moderator
```

**How it works:**
1. Agents propose independently
2. Agents negotiate without moderator
3. Consensus reached through discussion
4. Final guess submitted

**Communication:** Agent ↔ Agent (negotiation)

**Characteristics:**
- Cooperative (shared goal)
- Peer-to-peer (no moderator)
- Agents must reach consensus
- Tests collaborative reasoning

---

### Orchestration Files

#### `orchestration/langgraph_orchestrator.py`
**What it is:** Game flow manager

**What it does:**
- Manages round-by-round game flow
- Coordinates game state
- Handles round limits (max 8)
- Returns results

**Why separate?** Game orchestration is separate from agent orchestration

**Used by:** All paradigms (all need round management)

---

#### `orchestration/orchestrator.py`
**What it is:** Experiment runner

**What it does:**
- Runs multiple puzzles with multiple paradigms
- Collects results
- Compares performance across paradigms

**Why separate?** Enables comparative analysis

**Used by:** Experiment runners (not used in individual paradigm tests)

---

### Evaluation Files

#### `checkpoint.py`
**What it is:** Progress saver

**What it does:**
- Saves game state at checkpoints
- Enables resuming interrupted games

**Why separate?** Checkpointing is orthogonal to game logic

---

#### `communication_logger.py`
**What it is:** Message recorder (see above)

---

### Setup Files

#### `kaggle_setup.py`
**What it is:** Environment configuration

**What it does:**
- Loads .env file with API keys
- Sets up Kaggle backend

**Why separate?** Configuration shouldn't be in game code

---

## Part 3: How the System Works (Data Flow)

### High-Level Flow

```
1. Create Puzzle (game_engine.py)
   ↓
2. Create Paradigm Orchestrator (e.g., boss_worker.py)
   ↓
3. Initialize Agents (strategist, analyzer, proposer, validator)
   ↓
4. For each round (1-8):
   a. Paradigm routes through agents
   b. Each agent processes via LLM (base_agent.py)
   c. Communication logged (communication_logger.py)
   d. Final guess submitted to GameEngine
   e. Feedback received and used in next round
   ↓
5. Game ends when solved or rounds exhausted
   ↓
6. Results returned and logged
```

---

### Detailed Round Flow (Boss-Worker Example)

```
ROUND START
├─ Boss receives game state
│  └─ Guess history, current feedback
│
├─ STEP 1: Strategist
│  ├─ Boss sends request: "propose_strategy"
│  ├─ Strategist processes via LLM
│  │  ├─ Reads input (game state)
│  │  ├─ Applies 4-step CoT reasoning
│  │  ├─ Outputs strategy JSON
│  │  └─ Includes confidence score
│  └─ Boss receives response: strategy
│
├─ STEP 2: Analyzer  
│  ├─ Boss sends request: "analyze_feedback"
│  ├─ Analyzer processes via LLM
│  │  ├─ Reads input (last guess + feedback)
│  │  ├─ Applies 5-step constraint extraction
│  │  ├─ Outputs constraints JSON
│  │  └─ Includes confidence score
│  └─ Boss receives response: constraints
│
├─ STEP 3: Proposer
│  ├─ Boss sends request: "propose_guess"
│  │  └─ Includes: strategy + constraints + available colors
│  ├─ Proposer processes via LLM
│  │  ├─ Reads input (strategy + constraints)
│  │  ├─ Applies 5-step constraint-respecting reasoning
│  │  ├─ Outputs proposed guess + justification
│  │  └─ Includes confidence score
│  └─ Boss receives response: proposed guess
│
├─ STEP 4: Validator
│  ├─ Boss sends request: "validate_guess"
│  │  └─ Includes: proposed guess + constraints
│  ├─ Validator processes via LLM
│  │  ├─ Reads input (guess + constraints)
│  │  ├─ Applies 6-step validation (hard + soft)
│  │  ├─ Outputs validation result
│  │  └─ Includes confidence score
│  └─ Boss receives response: is_valid?
│
├─ STEP 5: Decision
│  ├─ If valid: use guess
│  └─ If invalid: retry from Proposer (max 2 retries)
│
├─ STEP 6: Submit Guess
│  ├─ Boss submits guess to GameEngine
│  ├─ GameEngine returns feedback
│  └─ Boss logs communication
│
├─ STEP 7: Update History
│  ├─ Add guess + feedback to history
│  └─ Prepare for next round
│
└─ ROUND END
   └─ Check: solved? or rounds exhausted?
```

---

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│         External: Puzzle Generator                   │
│  (provides secret code and puzzle metadata)          │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────┐
│         GameEngine (Referee)                         │
│  ├─ Stores secret code                              │
│  ├─ Receives guesses                                │
│  ├─ Returns feedback: {correct_pegs, correct_pos}  │
│  └─ Tracks rounds                                   │
└────────┬──────────────────────────────┬─────────────┘
         │                              │
         ↓ Feedback                     ↓ Guess
    ┌─────────────────────────────────────────────┐
    │   Paradigm Orchestrator                     │
    │   (e.g., BossWorkerOrchestrator)           │
    │                                             │
    │   ├─ Manages rounds                         │
    │   ├─ Routes through agents                  │
    │   └─ Logs all communication                 │
    │                                             │
    │   ┌──────────────────────────────────────┐ │
    │   │         BOSS AGENT                   │ │
    │   │                                      │ │
    │   ├─ Strategist → (strategy)             │ │
    │   ├─ Analyzer → (constraints)            │ │
    │   ├─ Proposer → (guess)                  │ │
    │   ├─ Validator → (is_valid?)             │ │
    │   └─ Submit approved guess                │ │
    │   └──────────────────────────────────────┘ │
    │                                             │
    └─────────────────────────────────────────────┘
         │
         ↓ Results (success, guesses, rounds, messages)
    ┌─────────────────────────────────────────────┐
    │   Communication Logger                      │
    │   (records all messages for analysis)       │
    └─────────────────────────────────────────────┘
```

---

## Part 4: Message Flow Within a Round

### Boss-Worker Message Flow

```
Agent Input → LLM Call → JSON Output → Boss Receives → Next Agent

EXAMPLE:

Strategist:
  Input: {
    "guess_history": [{guess: [...], feedback: {...}}],
    "difficulty": "easy"
  }
  ↓ (sent to LLM via call_llm)
  LLM Response: "Let me think step by step...
                 Step 1: We found 2 colors...
                 Step 2: We're in constraint building phase...
                 Step 3: We should test new positions...
                 Strategy: Keep red and blue, vary positions"
  ↓ (parsed from LLM response)
  Output: {
    "phase": "CONSTRAINT_BUILDING",
    "analysis": "Found 2 colors, 1 locked",
    "strategy": "Keep red and blue, vary positions",
    "reasoning_steps": [step1, step2, step3],
    "confidence": 0.85
  }
  ↓ (sent to Boss)
  Boss uses this for Analyzer input

Analyzer:
  Input: {
    "last_guess": ["red", "blue", "green", "yellow"],
    "feedback": {"correct_pegs": 2, "correct_positions": 1},
    "previous_guesses": [...]
  }
  ↓ (sent to LLM)
  LLM Response: "Step 1: 2 colors exist...
                 Step 2: 1 position locked...
                 Step 3: Misplaced = 2-1 = 1...
                 Constraints: Position ?, Red locked, Blue misplaced"
  ↓ (parsed)
  Output: {
    "correct_positions": [{"position": 0, "color": "red"}],
    "correct_colors_wrong_position": ["blue"],
    "impossible_colors": ["green", "yellow"],
    "constraints": ["Position 0: red (LOCKED)", ...],
    "confidence": 0.8
  }
  ↓ (sent to Boss)
  Boss uses this for Proposer input

[continues for Proposer and Validator]
```

---

## Part 5: Why This Architecture

### Design Principles

1. **Separation of Concerns**
   - Each file has one responsibility
   - game_engine.py: Just the game rules
   - agents/: Just the reasoning
   - paradigms/: Just the communication pattern
   - communication/: Just the messaging

2. **Reusability**
   - Same 4 agents used in 6 paradigms
   - Same GameEngine used by all paradigms
   - Same communication_logger used by all

3. **Comparability**
   - Fixed agents + variable communication
   - Enables measuring impact of communication patterns
   - Can isolate which design choice helps

4. **Extensibility**
   - New paradigms? Create new paradigms/ file
   - New agents? Create new agents/ file
   - New LLM? Update base_agent.py

### How Files Relate

```
game_engine.py (the game)
    ↓ used by
paradigms/*.py (communication patterns)
    ↓ use
agents/*.py (4 fixed workers)
    ↓ use
agents/base_agent.py (LLM interface)
    ↓ logs
communication_logger.py (message recorder)
    ↓ uses
communication/*.py (message format)
```

---

## Part 6: A Concrete Example

### Boss-Worker Solving "Easy" Puzzle

```
PUZZLE: MM_001
Secret Code: [red, blue, green, yellow]
Difficulty: easy
Available Colors: [red, blue, green, yellow, white, black]
Max Rounds: 8

─────────────────────────────────────────────

ROUND 1: First Guess

Boss: "Strategist, what's your strategy?"
Strategist: "We know nothing, test diverse colors"

Boss: "Analyzer, extract constraints"
Analyzer: "No constraints yet, first guess"

Boss: "Proposer, generate first guess"
Proposer: "Guess: [red, white, black, orange]
           (Testing red, and 3 completely new colors)"

Boss: "Validator, is this valid?"
Validator: "✓ Valid - 4 colors, all available"

Boss submits to GameEngine: [red, white, black, orange]
GameEngine feedback: {correct_pegs: 1, correct_positions: 0}

ANALYSIS: Red is in the code but wrong position

─────────────────────────────────────────────

ROUND 2: Constraint-Building

Boss: "Strategist, update strategy"
Strategist: "We found red exists (wrong position).
             Now test other positions for red,
             and find other colors that exist"

Boss: "Analyzer, extract constraints"
Analyzer: "Locked: none
           Misplaced: [red (not at position 0)]
           Impossible: [white, black, orange]"

Boss: "Proposer, generate next guess"
Proposer: "Guess: [blue, red, green, yellow]
           (Testing red in position 1,
            and three likely colors)"

Boss: "Validator, is this valid?"
Validator: "✓ Valid - respects constraints,
            red moved to new position"

Boss submits: [blue, red, green, yellow]
GameEngine feedback: {correct_pegs: 4, correct_positions: 2}

ANALYSIS: 4 colors are in code! 2 already locked!

─────────────────────────────────────────────

ROUND 3: Refinement

Boss: "Strategist, update strategy"
Strategist: "All 4 colors found! Now lock positions.
             Currently: position 0=blue, position 1=red
             Need to find: positions 2 and 3"

Boss: "Analyzer, extract constraints"
Analyzer: "Locked: [position 0: blue, position 1: red]
           Misplaced: [green (not at 2), yellow (not at 3)]
           Impossible: []"

Boss: "Proposer, generate next guess"
Proposer: "Guess: [blue, red, yellow, green]
           (Keep positions 0,1 locked,
            swap positions 2,3 for misplaced colors)"

Boss: "Validator, is this valid?"
Validator: "✓ Valid - locked positions preserved,
            misplaced colors moved"

Boss submits: [blue, red, yellow, green]
GameEngine feedback: {correct_pegs: 4, correct_positions: 4}

ANALYSIS: SOLVED! All 4 positions correct!

─────────────────────────────────────────────

RESULTS:
Success: ✓ YES
Guesses: 3
Rounds: 3
Messages: 12 (3 rounds × 4 agents)
Strategy: Boss-Worker (centralized coordination)
```

---

## Part 7: Key Takeaways

### Why Same Agents?

✓ **Isolates variables:** Can measure communication impact without agent differences  
✓ **Fair comparison:** Each paradigm gets identical reasoning capability  
✓ **Identifies best structure:** Shows which communication pattern works best  

### Why Multiple Paradigms?

✓ **Tests different organizational patterns:** Centralized vs. peer-to-peer  
✓ **Tests collaboration types:** Cooperation vs. competition vs. coopetition  
✓ **Comprehensive evaluation:** Measures impact of communication design  

### File Organization Philosophy

✓ **Separation:** Each file has one clear purpose  
✓ **Reusability:** Files used by multiple paradigms where appropriate  
✓ **Extensibility:** Easy to add new paradigms or agents  
✓ **Clarity:** File structure reflects conceptual structure  

---

## Part 8: Quick Reference: What File for What Task?

| Task | File |
|------|------|
| Add a new puzzle difficulty | `puzzle_generator.py` |
| Change game rules (feedback logic) | `game_engine.py` |
| Improve Strategist reasoning | `agents/strategist.py` |
| Improve Analyzer constraints | `agents/analyzer.py` |
| Improve Proposer guess generation | `agents/proposer.py` |
| Improve Validator checking | `agents/validator.py` |
| Change LLM provider or add retry logic | `agents/base_agent.py` |
| Create a new paradigm | Create `paradigms/new_paradigm.py` |
| Track new metrics | `communication_logger.py` |
| Change message format | `communication/protocol.py` |
| Run experiment comparing paradigms | `orchestration/orchestrator.py` |

---

## Part 9: Summary

### The System in One Paragraph

The system uses **4 fixed worker agents** (Strategist, Analyzer, Proposer, Validator) that solve Mastermind puzzles together. Each agent has one clear role in the reasoning process. The system tests **6 different communication paradigms** (different ways to organize these agents) to see which organizational structure works best for collaborative problem-solving. The GameEngine provides the objective truth (secret code, feedback), and the Paradigm Orchestrators manage how agents are routed through each round. The Communication Logger records all interactions for analysis.

### Why This Design?

✓ **Focused research:** Isolates the impact of communication patterns  
✓ **Fair comparison:** All paradigms get identical agent capability  
✓ **Clear architecture:** Each file has one clear purpose  
✓ **Extensible:** Easy to add new paradigms or improve agents  
✓ **Analyzable:** All communication logged and traceable  

---

**Created:** May 31, 2026  
**Purpose:** System architecture explanation for developers and thesis writers
