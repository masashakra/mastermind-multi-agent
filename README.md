# Mastermind Multi-Agent System

**Bachelor Thesis: Interactions of Agents in Multi-Agent Environment**

**Author:** Masa ElShakra  
**Supervisor:** Dr. Mervat Abuelkheir  
**Deadline:** May 24, 2026 (10 days)  
**Status:** Phase 1 (Infrastructure) ✓ Complete

---

## 🎯 Project Overview

This system evaluates how **6 different interaction paradigms** affect multi-agent performance on **Mastermind puzzle-solving**. Same puzzles, different coordination strategies → measure which paradigm excels.

### Key Numbers
- **30 puzzles** (10 easy, 10 medium, 10 hard)
- **6 paradigms** (2 collaboration, 2 competition, 2 coopetition)
- **180 experimental runs** (30 puzzles × 6 paradigms)
- **9 metrics** (task success, communication efficiency, coordination quality)

---

## ⚙️ Setup & Configuration

### LLM Backend (Required)

This system uses an LLM for agent reasoning. Configure your backend:

**Option 1: Kaggle Backend (Primary)**
```bash
# Copy to your project root:
cp kaggle_setup/.env .env

# Or manually create .env with:
export KAGGLE_URL=https://flatware-urgent-everglade.ngrok-free.dev
export KAGGLE_MODEL=llama3.1:8b
```

Then load in your code:
```python
from src.kaggle_setup import load_kaggle_env
load_kaggle_env()

from src.paradigms.boss_worker import BossWorkerOrchestrator
orchestrator = BossWorkerOrchestrator(puzzle, provider="kaggle")
result = orchestrator.run()
```

**Option 2: Local Ollama (Fallback)**
```bash
ollama serve          # Terminal 1
ollama pull mistral   # Terminal 2 (one-time)
```

Then use: `provider="ollama"`

### Quick Test
```bash
python3 test_kaggle.py
```

---

## 📁 Project Structure

```
game/
├── README.md                   # This file
├── PHASE1_SUMMARY.md          # ✓ Phase 1 completion report
├── PHASE2_SUMMARY.md          # ✓ Phase 2 completion report
├── PHASE3_SUMMARY.md          # ✓ Phase 3 completion report
├── LLM_VERIFICATION.md        # ✓ LLM backend verification
├── test_kaggle.py             # Quick Kaggle backend test
├── main.py                     # Main experiment runner (Day 9)
├── kaggle_setup/
│   └── .env                    # Kaggle backend configuration
├── output/
│   ├── puzzles.json           # ✓ 30 generated puzzles (run once)
│   ├── checkpoint.json        # Progress tracking (auto-generated)
│   ├── sessions/              # Detailed logs per puzzle-paradigm
│   ├── metrics/               # Aggregated results
│   └── logs/                  # Debug logs
├── src/
│   ├── __init__.py
│   ├── game_engine.py         # ✓ Mastermind game logic
│   ├── puzzle_generator.py    # ✓ Generate puzzles
│   ├── communication_logger.py # ✓ Log inter-agent messages
│   ├── checkpoint.py          # ✓ Save-and-resume system
│   ├── kaggle_setup.py        # ✓ Load Kaggle backend config
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py      # ✓ Base class (Day 3)
│   │   ├── strategist.py      # ✓ Strategy proposer (Day 3)
│   │   ├── analyzer.py        # ✓ Constraint extractor (Day 3)
│   │   ├── proposer.py        # ✓ Guess generator (Day 4)
│   │   ├── validator.py       # ✓ Quality control (Day 4)
│   │   └── boss.py            # ✓ Orchestrator (Day 5)
│   ├── paradigms/
│   │   ├── __init__.py
│   │   ├── boss_worker.py     # ✓ Collaboration, centralized (Day 5)
│   │   ├── round_table.py     # Collaboration, peer-to-peer (Day 6)
│   │   ├── judge_mediated.py  # Competition, centralized (Day 7)
│   │   ├── direct_adversarial.py # Competition, peer-to-peer (Day 7)
│   │   ├── moderator_mediated.py # Coopetition, centralized (Day 8)
│   │   └── direct_debate.py   # Coopetition, peer-to-peer (Day 8)
│   └── evaluation/
│       ├── __init__.py
│       └── metrics.py         # Compute all 9 metrics (Day 10)
└── tests/
    ├── test_game_engine.py    # ✓ Game engine tests
    ├── test_agents.py         # ✓ Agent tests (Days 3-4)
    ├── test_agents_with_llm.py # LLM integration tests
    ├── test_boss_worker.py    # ✓ Boss-Worker paradigm tests
    └── test_paradigms.py      # Paradigm tests (Day 8)
```

---

## 📋 What's Implemented (Phase 1: Infrastructure)

### ✓ Game Engine (`src/game_engine.py`)
**8-round Mastermind puzzle solver**

- `GameEngine(secret_code, difficulty)`: Initialize with secret code
- `submit_guess(guess)`: Get feedback (correct_pegs, correct_positions)
- `is_game_over()`: Check win condition or round limit
- `get_state()`: Retrieve game state

**Feedback explanation:**
- `correct_pegs`: # of colors that exist in secret (any position)
- `correct_positions`: # of colors in correct position

**Example:**
```python
from src.game_engine import GameEngine

secret = ["red", "blue", "green", "yellow"]
game = GameEngine(secret, "easy")

result = game.submit_guess(["red", "blue", "green", "yellow"])
# → {"solved": True, "correct_pegs": 4, "correct_positions": 4}
```

### ✓ Puzzle Generator (`src/puzzle_generator.py`)
**Generate 30 puzzles once, reuse for all paradigms**

- `generate_puzzles(n_easy, n_medium, n_hard)`: Generate with random codes
- `save_puzzles(puzzles, output_path)`: Save to JSON
- `load_puzzles(puzzle_path)`: Load for experiments

**Usage:**
```bash
python src/puzzle_generator.py
# Output: ✓ Generated 30 puzzles and saved to output/puzzles.json
```

**Output format:**
```json
{
  "puzzle_id": "MM_001",
  "difficulty": "easy",
  "pegs": 4,
  "num_colors": 6,
  "available_colors": ["red", "blue", "green", "yellow", "white", "black"],
  "secret_code": ["red", "blue", "green", "yellow"],
  "created_at": "2026-05-14T20:14:00"
}
```

### ✓ Communication Logger (`src/communication_logger.py`)
**Log all inter-agent messages for analysis**

- `CommunicationLogger(puzzle_id, paradigm)`: Initialize per puzzle-paradigm
- `log_message(message)`: Record message (immediate write for robustness)
- `get_all_messages()`: Retrieve messages
- `get_messages_by_type(msg_type)`: Filter by message type
- `get_messages_by_round(round_num)`: Filter by round
- `summary()`: Get message statistics

**Output format (JSONL):**
```json
{
  "timestamp": 1715683200.123,
  "round_number": 1,
  "sender": "strategist",
  "receiver": "boss",
  "message_type": "strategy_proposal",
  "content": {...},
  "puzzle_id": "MM_001",
  "paradigm": "boss-worker"
}
```

### ✓ Checkpoint System (`src/checkpoint.py`)
**Save-and-resume: crash at puzzle 15/30 → resume from 16**

- `load_checkpoint()`: Get completed puzzles
- `save_checkpoint(puzzle_id)`: Mark puzzle done
- `is_completed(puzzle_id)`: Check if already done
- `get_completion_status()`: Get stats
- `reset_checkpoint()`: Clear (use with caution!)

**Usage in main loop:**
```python
completed = load_checkpoint()
for puzzle in puzzles:
    if is_completed(puzzle["puzzle_id"]):
        continue  # Already done
    run_puzzle(puzzle)
    save_checkpoint(puzzle["puzzle_id"])
```

### ✓ Tests
**Game Engine Tests (`tests/test_game_engine.py`)** - 9 test cases
- Perfect guess (solved)
- All colors correct, wrong positions
- Mixed feedback
- No matches
- Wrong length validation
- Max rounds termination
- Solution termination
- Duplicate color counting
- Game state retrieval

Run tests:
```bash
python3 tests/test_game_engine.py
```

---

## 🤖 Agents (Phase 2: Days 3-4) ✓ COMPLETE

### ✓ Base Agent (`src/agents/base_agent.py`)
**Abstract base class for all agents**

Features:
- LLM provider abstraction (Kaggle for primary, Ollama for dev, Claude for production)
- JSON response parsing (direct, markdown, error recovery)
- Call tracking and token counting
- Error handling and fallbacks

Supported providers:
- `"kaggle"`: Llama 3.1 8B via ngrok (recommended)
- `"ollama"`: Local Ollama (fallback)
- `"claude"`: Claude API (if configured)

```python
from src.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, provider="kaggle"):
        super().__init__(name="MyAgent", provider=provider)
    
    def process(self, **kwargs):
        # Implement specific logic
        pass

# Usage:
agent = MyAgent(provider="kaggle")
```

### ✓ Strategist Agent (`src/agents/strategist.py`)
**Proposes high-level guessing strategy**

Role: Strategic planning based on feedback patterns

Input: Guess history + feedback  
Output: JSON with analysis, strategy, reasoning, confidence

```python
from src.agents.strategist import StrategistAgent

strategist = StrategistAgent()
strategy = strategist.propose_strategy(
    guess_history=[
        {
            "round": 1,
            "guess": ["red", "blue", "green", "yellow"],
            "feedback": {"correct_pegs": 2, "correct_positions": 1}
        }
    ],
    difficulty="easy"
)
# → {"analysis": "...", "strategy": "...", "reasoning": "...", "confidence": 0.85}
```

### ✓ Analyzer Agent (`src/agents/analyzer.py`)
**Interprets feedback and extracts constraints**

Role: Information processing and constraint extraction

Input: Latest guess + feedback  
Output: JSON with locked positions, colors, constraints, estimates

```python
from src.agents.analyzer import AnalyzerAgent

analyzer = AnalyzerAgent()
analysis = analyzer.analyze_feedback(
    last_guess=["red", "blue", "green", "yellow"],
    feedback={"correct_pegs": 2, "correct_positions": 1}
)
# → {"correct_positions": [...], "correct_colors_wrong_position": [...], ...}
```

### ✓ Proposer Agent (`src/agents/proposer.py`)
**Generates concrete guess from strategy and constraints**

Role: Execution - translates strategy into specific action

Input: Strategy + constraints + available colors + num_pegs  
Output: JSON with proposed guess and justification

```python
from src.agents.proposer import ProposerAgent

proposer = ProposerAgent()
proposal = proposer.propose_guess(
    strategy="Test new colors in positions 3-4",
    constraints_text="Red locked at position 0",
    available_colors=["red", "blue", "green", "yellow", "white", "black"],
    num_pegs=4
)
# → {"proposed_guess": ["red", "blue", "green", "yellow"], "justification": "..."}
```

### ✓ Validator Agent (`src/agents/validator.py`)
**Quality control before guess submission**

Role: Error prevention and validation

Input: Proposed guess + available colors + expected length  
Output: JSON with validation result

```python
from src.agents.validator import ValidatorAgent

validator = ValidatorAgent()
validation = validator.validate_guess(
    guess=["red", "blue", "green", "yellow"],
    available_colors=["red", "blue", "green", "yellow", "white", "black"],
    expected_length=4,
    previous_guesses=[["white", "white", "white", "white"]]
)
# → {"is_valid": True, "ready_to_submit": True, "errors": [], "warnings": []}
```

### ✓ Agent Tests (`tests/test_agents.py`)
**18 comprehensive test cases**

Run tests:
```bash
python3 tests/test_agents.py
```

Test coverage:
- Base agent JSON parsing (direct, markdown, error cases)
- Strategist feedback formatting
- Analyzer None input handling
- Proposer initialization and tracking
- Validator validation logic (5 test cases)
- Agent integration and workflow

All 18 tests passing ✓

---

## 🎯 Paradigms (Phase 3+: Days 5-8)

### ✓ Boss-Worker Paradigm (Day 5) - COMPLETE

**Type:** Collaboration + Centralized

**Structure:**
- 1 Boss (central coordinator)
- 4 Workers (Strategist, Analyzer, Proposer, Validator)
- Sequential execution
- Full message transparency

**Boss Agent (`src/agents/boss.py`) - 180 lines**

Orchestrates all worker agents:
```python
from src.agents.boss import BossAgent

boss = BossAgent()
round_result = boss.orchestrate_round({
    "puzzle": puzzle,
    "guess_history": previous_guesses,
    "difficulty": "easy"
})
# Returns: {guess, strategy, analysis, proposal, validation, messages}
```

**Boss-Worker Orchestrator (`src/paradigms/boss_worker.py`) - 210 lines**

Complete paradigm implementation:
```python
from src.paradigms.boss_worker import BossWorkerOrchestrator

orchestrator = BossWorkerOrchestrator(puzzle)
result = orchestrator.run()
# Returns: {success, guesses, rounds, elapsed_time, messages, tokens, ...}
```

**Workflow per Round:**
1. Boss asks Strategist: "What's our strategy?"
2. Boss asks Analyzer: "What constraints can we extract?"
3. Boss asks Proposer: "Generate a guess"
4. Boss asks Validator: "Is it valid?"
5. Submit guess to game engine
6. Log all messages
7. Check if solved or max rounds reached

**Tests: 13 passing ✓**
- Boss agent tests (4)
- Orchestrator tests (4)
- Workflow tests (2)
- Paradigm property tests (3)

### Remaining Paradigms (Days 6-8)

| Day | Paradigm | Type | Structure | Status |
|-----|----------|------|-----------|--------|
| 6 | Round-Table | Collab | Peer-to-Peer | → Next |
| 7a | Judge-Mediated | Comp | Centralized | Pending |
| 7b | Direct Adversarial | Comp | Peer-to-Peer | Pending |
| 8a | Moderator-Mediated | Coop | Centralized | Pending |
| 8b | Direct Debate | Coop | Peer-to-Peer | Pending |

All 5 remaining paradigms follow same architecture:
- Same 4 agents (Strategist, Analyzer, Proposer, Validator)
- Same GameEngine
- Different orchestration/coordination logic
- Different message routing
- Same logging infrastructure

---

## 🚀 Quick Start

### 1. Setup Environment (One-time)
```bash
cd /Users/masashakra/Desktop/game
python3 -m pip install langchain-ollama anthropic python-dotenv pandas matplotlib
```

### 2. Generate Puzzles (One-time)
```bash
python3 src/puzzle_generator.py
```

Output:
```
✓ Generated 30 puzzles and saved to output/puzzles.json
```

### 3. Run All Tests
```bash
python3 tests/test_game_engine.py    # 9 tests for game engine
python3 tests/test_agents.py         # 18 tests for agents
```

### 4. Progress Timeline

| Phase | Days | Status | Tasks |
|-------|------|--------|-------|
| **Infrastructure** | 1-2 | ✓ Complete | Game Engine, Puzzles, Logging, Checkpoint |
| **Agents** | 3-4 | ✓ Complete | 4 agents + tests (28 tests total) |
| **Boss-Worker** | 5 | **✓ Complete** | Boss Agent + paradigm orchestrator (13 tests) |
| **Round-Table** | 6 | → Next | Peer collaboration paradigm |
| **Competition** | 7 | Pending | Judge-Mediated + Direct Adversarial |
| **Coopetition** | 8 | Pending | Moderator-Mediated + Direct Debate |
| **Experiment** | 9 | Pending | Run all 180 puzzles |
| **Analysis** | 10 | Pending | Metrics + Results |

---

## 📊 Metrics (9 Total)

### Task Success (3 metrics)
- **Success Rate (%)**: (solved / total) × 100
- **Avg Guesses**: sum(guesses) / count(solved)
- **Failure Rate (%)**: (unsolved / total) × 100

### Communication Efficiency (3 metrics)
- **Token Cost**: sum(input + output tokens)
- **Message Count**: Count A2A messages
- **Wasted Comm Rate (%)**: (wasted / total) × 100

### Coordination Quality (3 metrics)
- **Role Adherence (%)**: (on-role / total) × 100
- **Convergence Speed (rounds)**: Round # when stable
- **Coordination Score (1-5)**: (Comm Flow + Coord Strategy) / 2

---

## 🎮 Game Rules Reminder

**Mastermind** (4/5/6 pegs):
1. Secret code generated randomly
2. Agent proposes guess
3. Feedback returned:
   - `correct_pegs`: # colors in code (any position)
   - `correct_positions`: # colors in correct position
4. Agent analyzes, proposes next guess
5. Repeat until solved (≤8 rounds) or failure

**Example:**
- Secret: [Red, Blue, Green, Yellow]
- Guess 1: [Red, Blue, Green, Yellow] → 4 pegs, 4 positions ✓ **SOLVED**
- Secret: [Red, Blue, Green, Yellow]
- Guess 2: [Yellow, Green, Blue, Red] → 4 pegs, 0 positions
- Secret: [Red, Blue, Green, Yellow]
- Guess 3: [Red, Red, Red, Red] → 1 peg, 1 position

---

## 📝 File Summaries

Each source file includes a header comment explaining its purpose:

```python
# File Name
# One-line description
# Implementation details
# Key functions/classes
```

Example:
```python
# Game Engine
# Core game logic: feedback computation, guess validation
# Tracks secret code, validates guesses, returns feedback
# Implements 8-round max, detects win condition
```

---

## 🔧 Configuration

Currently using:
- **Local LLM**: Ollama (Mistral 7B) - free, fast for development
- **Final LLM**: Claude API - for thesis results
- **Framework**: LangChain + LangGraph
- **Storage**: JSON files → SQLite (upgrade later if needed)
- **Logging**: JSON Lines format (structured, queryable)

To switch to Claude API later, update agent base class.

---

## 📚 Academic Foundation

This project is grounded in multi-agent systems research:

- **MastermindEval** (Golde et al., 2025) - Game mechanics & difficulty progression
- **Multi-Agent Collaboration Mechanisms** (Tran et al., 2025) - Paradigm taxonomy
- **The Orchestration of Multi-Agent Systems** (Adimulam et al., 2026) - Agent architecture
- **A2A Protocol** (Linux Foundation) - Communication standard

See full specification for citations and academic justifications.

---

## ⚠️ Important Notes

1. **Puzzles are one-time generated**: Run `python src/puzzle_generator.py` once, then all paradigms use the same 30 puzzles. This ensures fair comparison.

2. **Secret codes are hidden**: Game engine stores secret code, never shown to agents. Same puzzle across paradigms → isolate paradigm effects.

3. **Save-and-resume**: If experiment crashes at puzzle 15, checkpoint system allows resuming from puzzle 16. No data loss.

4. **Sequential execution OK for 10-day deadline**: Competition/coopetition paradigms with 3 teams run sequentially (not truly parallel), but still siloed during solving. Results nearly identical to true parallel, code is much simpler.

5. **No streaming needed**: Streaming doesn't reduce token cost. Keep LLM calls simple (blocking) for clarity.

---

## 🎓 Thesis Integration

Results go directly into **Chapter 4: Results**:
- Success rates by paradigm
- Token cost comparison
- Message count analysis
- Coordination quality findings
- Key insights

---

## 📞 Questions?

Refer to full specification document for:
- Complete paradigm workflows
- Agent prompt templates
- Detailed metric formulas
- Q&A with justifications
- 10-day timeline

---

**Status:** Infrastructure Phase ✓ Complete  
**Next:** Phase 2 (Agents, Days 3-4)  
**Timeline:** 10 days to completion ⏱️

