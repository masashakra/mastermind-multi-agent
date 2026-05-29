# A2A Compliant Mastermind Solver - Architecture Guide

## Overview

Your system now implements a **fully compliant A2A (Agent-to-Agent) architecture** with proper separation of concerns between orchestration and communication.

---

## Architecture Layers

### Layer 1: LangGraph Orchestration (Game Level)
**File**: `src/orchestration/langgraph_orchestrator.py`

**Responsibility**: Manage game rounds, guess submission, and feedback

```python
LangGraphMastermindOrchestrator
├─ execute_game(puzzle)
│  ├─ Round 1: _ask_boss_for_guess() → _submit_guess_to_engine() → feedback
│  ├─ Round 2: _ask_boss_for_guess() → _submit_guess_to_engine() → feedback
│  └─ ... (repeat until solved or max rounds)
├─ Game state management
├─ Win/loss detection
└─ Feedback collection from game engine
```

**What it does**:
- Creates Boss agent
- Asks Boss for a guess (Boss handles A2A tasks internally)
- Submits guess to game engine (NOT A2A)
- Collects feedback from game engine
- Manages win/loss conditions
- Tracks game statistics

**What it does NOT do**:
- Handle A2A communication (Boss does that)
- Manage agent task assignment (Boss does that)
- Define agent capabilities (Agent Cards do that)

---

### Layer 2: Boss Agent (Task Orchestrator)
**File**: `src/agents/boss_a2a.py`

**Responsibility**: Send A2A tasks to workers, collect responses, assemble guess

```python
BossA2AAgent
├─ orchestrate_round(game_state)
│  ├─ send_request("propose_strategy") → Strategist [A2A]
│  ├─ send_request("analyze_feedback") → Analyzer [A2A]
│  ├─ send_request("propose_guess") → Proposer [A2A]
│  ├─ send_request("validate_guess") → Validator [A2A]
│  └─ return final guess to LangGraph
├─ A2A message tracking
└─ Result assembly from worker responses
```

**What it does**:
- Sends A2A task requests to each worker
- Receives A2A responses from each worker
- Assembles final guess from worker results
- Tracks A2A message history
- Returns guess for LangGraph to submit

**What it does NOT do**:
- Submit guess to game engine (LangGraph does that)
- Get feedback (LangGraph does that)
- Manage game rounds (LangGraph does that)
- Define workflow order (LangGraph does that)

---

### Layer 3: Communication Layer (A2A Protocol)
**Files**: 
- `src/communication/protocol.py` - Message format and routing
- `src/communication/agent_card.py` - Agent metadata
- `src/communication/agent_discovery.py` - Agent registry and discovery

**Responsibility**: Pure A2A message passing between agents

```python
A2ACommunicationLayer
├─ send_request(sender, receiver, action, payload) → A2AMessage
├─ send_response(sender, receiver, correlation_id, payload, status) → A2AMessage
├─ send_notification(sender, receiver, action, payload) → A2AMessage
├─ Message history tracking
├─ Message correlation (request ↔ response)
└─ Agent registry

AgentRegistry + AgentDiscovery
├─ Agent registration
├─ Capability-based discovery
├─ Tag-based discovery
└─ Agent metadata (cards)
```

**What it does**:
- Route A2A messages between agents
- Track message history
- Correlate requests with responses
- Manage agent registry
- Provide agent discovery by type/capability/tag

**What it does NOT do**:
- Define workflow (that's LangGraph's job)
- Submit to game engine (that's LangGraph's job)
- Execute agent logic (that's up to each agent)

---

### Layer 4: Worker Agents (LLM-Based)
**Files**:
- `src/agents/strategist.py`
- `src/agents/analyzer.py`
- `src/agents/proposer.py`
- `src/agents/validator.py`

**Responsibility**: Accept A2A tasks, perform work, return results

```
Worker Agent Lifecycle:
1. Receive A2A request from Boss
2. Execute LLM call (no heuristics)
3. Return result via A2A response
4. Go to step 1
```

**What they do**:
- Process A2A task requests
- Use LLM to generate results
- Return results via A2A protocol
- Track LLM statistics

**What they do NOT do**:
- Initiate work (Boss initiates via A2A)
- Manage game state
- Submit to game engine

---

## Data Flow - Single Round

```
Round N
└─ LangGraph: execute_game()
   ├─ Step 1: Ask Boss
   │  └─ Boss: orchestrate_round(game_state)
   │     ├─ Send A2A: "propose_strategy" → Strategist
   │     │  └─ Strategist LLM call
   │     │  └─ Receive A2A response
   │     ├─ Send A2A: "analyze_feedback" → Analyzer
   │     │  └─ Analyzer LLM call
   │     │  └─ Receive A2A response
   │     ├─ Send A2A: "propose_guess" → Proposer
   │     │  └─ Proposer LLM call
   │     │  └─ Receive A2A response
   │     ├─ Send A2A: "validate_guess" → Validator
   │     │  └─ Validator LLM call
   │     │  └─ Receive A2A response
   │     └─ return guess
   │
   ├─ Step 2: Submit to Engine
   │  └─ GameEngine.submit_guess(guess)
   │  └─ Receive feedback
   │
   ├─ Step 3: Check State
   │  ├─ if solved: return won
   │  └─ else: continue to Round N+1
```

---

## A2A Message Format

Every agent-to-agent communication uses standardized A2AMessage:

```python
A2AMessage {
    message_id: "uuid-123",           # Unique identifier
    sender_id: "strategist",          # Who sent it
    receiver_id: "boss",              # Who receives it
    message_type: "REQUEST",          # REQUEST|RESPONSE|NOTIFICATION|ERROR
    action: "propose_strategy",       # What to do
    payload: {...},                   # Data
    correlation_id: "uuid-123",       # Links request→response
    timestamp: 1234567890.0,          # When sent
    status: "success",                # success|error|pending
    metadata: {...}                   # Optional metadata
}
```

---

## Agent Discovery

Agents are discovered and registered:

```python
# By type
agents = discovery.get_agents_by_type("strategist")

# By capability
agents = discovery.get_agents_by_capability("propose_strategy")

# By tag
agents = discovery.get_agents_by_tag("mastermind")

# Find specific agent for action
agent = discovery.find_agent_for_strategy_proposal()
```

Each agent has an **Agent Card** with:
- Capabilities (what actions it can perform)
- Input/output schemas
- Discovery tags
- LLM provider and model
- Version and metadata

---

## Key Design Principles

### 1. Separation of Concerns
```
LangGraph:        GAME ORCHESTRATION (rounds, guess submission, feedback)
Boss:             TASK ORCHESTRATION (A2A task management)
Communication:    MESSAGE PASSING (A2A protocol)
Agents:           EXECUTION (LLM work)
```

### 2. Pure A2A for Agent Communication
- **A2A used for**: Agent ↔ Agent communication
- **A2A NOT used for**: Game engine calls, orchestration decisions

### 3. Stateless Agents
- Agents are stateless workers
- State is maintained by Boss (current round)
- State is maintained by LangGraph (game progress)

### 4. No Heuristics
- All decisions come from LLM calls
- No fallback logic
- No algorithmic shortcuts

---

## Example Usage

```python
from orchestration.langgraph_orchestrator import LangGraphMastermindOrchestrator
from puzzle_generator import load_puzzles

# Create orchestrator (creates Boss, creates Communication Layer)
orchestrator = LangGraphMastermindOrchestrator(provider="groq")

# Load puzzle
puzzles = load_puzzles("output/puzzles.json")
puzzle = puzzles[0]

# Execute game (LangGraph manages all rounds)
result = orchestrator.execute_game(puzzle)

# Result contains:
# {
#     "status": "won|lost|failed",
#     "puzzle_id": "MM_005",
#     "secret_code": [...],
#     "guesses_used": 5,
#     "max_guesses": 8,
#     "rounds_executed": 5,
#     "a2a_messages_total": 42,
#     "round_history": [...]
# }
```

---

## Testing the Architecture

### Test 1: Agent Discovery
```python
from communication.agent_discovery import AgentRegistry
from communication import STRATEGIST_CARD, ANALYZER_CARD, ...

registry = AgentRegistry()
registry.register_agent(STRATEGIST_CARD)
registry.register_agent(ANALYZER_CARD)
# ... etc

# Find agents
strategist = registry.get_agent("strategist")
agents_with_strategy = registry.get_agents_by_capability("propose_strategy")
```

### Test 2: A2A Protocol
```python
from communication.protocol import A2ACommunicationLayer

comm = A2ACommunicationLayer()

# Send request
request = comm.send_request(
    sender_id="boss",
    receiver_id="strategist",
    action="propose_strategy",
    payload={...}
)

# Send response
response = comm.send_response(
    sender_id="strategist",
    receiver_id="boss",
    correlation_id=request.message_id,
    payload={...},
    status="success"
)

# Check history
print(len(comm.message_history))  # All messages
print(comm.get_conversation("boss", "strategist"))  # Just these two
```

### Test 3: Boss Agent
```python
from communication.protocol import A2ACommunicationLayer
from agents.boss_a2a import BossA2AAgent

comm = A2ACommunicationLayer()
boss = BossA2AAgent(provider="groq", comm_layer=comm)

result = boss.orchestrate_round({
    "puzzle": puzzle,
    "guess_history": [],
    "difficulty": "easy"
})

print(result["guess"])  # The proposed guess
print(result["a2a_messages"])  # All A2A messages for this round
```

### Test 4: Full Game
```python
from orchestration.langgraph_orchestrator import LangGraphMastermindOrchestrator

orchestrator = LangGraphMastermindOrchestrator(provider="groq")
result = orchestrator.execute_game(puzzle)

print(f"Result: {result['status']}")
print(f"Guesses: {result['guesses_used']}/{result['max_guesses']}")
print(f"A2A Messages: {result['a2a_messages_total']}")
```

---

## Statistics Available

### Boss Agent Stats
```python
boss.get_stats()
# {
#     "agent_id": "boss",
#     "call_count": 12,  # LLM calls
#     "rounds_orchestrated": 3,
#     "total_a2a_messages": 24,  # 4 tasks × 2 A2A msgs each × 3 rounds
#     "provider": "groq"
# }
```

### Communication Layer Stats
```python
orchestrator.get_game_statistics()
# {
#     "total_a2a_messages": 24,
#     "comm_layer_stats": {
#         "agents_registered": 5,
#         "message_history_count": 24
#     }
# }
```

### Round History
```python
orchestrator.get_round_history()
# [
#     {
#         "round": 1,
#         "proposed_guess": [...],
#         "feedback": {...},
#         "is_solved": false
#     },
#     ...
# ]
```

---

## Summary

You now have a **fully A2A compliant system** where:

✅ **LangGraph** manages game rounds and guess submission  
✅ **Boss Agent** orchestrates A2A tasks to workers  
✅ **A2A Protocol** handles all agent-to-agent communication  
✅ **Worker Agents** execute LLM-based work  
✅ **Complete separation** between orchestration and communication  
✅ **Agent Discovery** for dynamic agent lookup  
✅ **Agent Cards** for capability definition  
✅ **Pure LLM** - no heuristics anywhere  

This is the architecture you specified: LangGraph initiates → Boss orchestrates → Workers execute via A2A.
