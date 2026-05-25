# File Structure - Mastermind AI System

## Organization Philosophy
- **By Concern:** Agents separate from paradigms
- **Scalable:** Easy to add new paradigms
- **Clear:** Each file has one responsibility
- **Testable:** Each component independently testable

---

## Directory Structure

```
game/
│
├── src/
│   ├── agents/                    # Individual agents (reusable)
│   │   ├── __init__.py
│   │   ├── base_agent.py         # BaseAgent class (LLM calls, parsing)
│   │   ├── analyzer.py           # Constraint extraction
│   │   ├── proposer.py           # Guess generation (ToT)
│   │   ├── strategist.py         # Strategy planning
│   │   ├── validator.py          # Quality control
│   │   └── boss.py               # Boss-Worker orchestrator
│   │
│   ├── paradigms/                 # Different agent architectures
│   │   ├── __init__.py
│   │   ├── boss_worker.py        # Boss coordinates workers (DONE)
│   │   ├── round_table.py        # Peer-to-peer collaboration (TODO)
│   │   ├── competition.py        # Agents compete (TODO)
│   │   ├── coopetition.py        # Mix of coop + competition (TODO)
│   │   └── experiment.py         # Experimental approaches (TODO)
│   │
│   ├── core/                      # Core game logic
│   │   ├── __init__.py
│   │   ├── game_engine.py        # Feedback computation
│   │   ├── puzzle_generator.py   # Puzzle creation
│   │   ├── communication_logger.py # Inter-agent messaging
│   │   └── checkpoint.py         # State saving
│   │
│   ├── utils/                     # Utilities
│   │   ├── __init__.py
│   │   ├── kaggle_setup.py       # LLM backend config
│   │   └── metrics.py            # Metrics collection (TODO)
│   │
│   └── __init__.py
│
├── tests/                         # Test suite
│   ├── test_easy_puzzle.py       # Single easy puzzle
│   ├── test_boss_worker_kaggle.py # Multiple puzzles (Boss-Worker)
│   ├── test_round_table.py       # Round-Table tests (TODO)
│   ├── test_competition.py       # Competition tests (TODO)
│   ├── test_agent_reasoning.py   # Agent output analysis
│   ├── test_round2_reasoning.py  # Round 2 debugging
│   └── test_round3_reasoning.py  # Round 3 debugging
│
├── docs/                          # Documentation (CREATED TODAY)
│   ├── MASTER_CHECKLIST.md
│   ├── SYSTEM_OVERVIEW.md
│   ├── IMPLEMENTATION_COMPLETE.md
│   ├── TESTING_GUIDE.md
│   ├── MASTERMIND_REASONING_GUIDE.md
│   ├── RESEARCH_FINDINGS.md
│   ├── GAME_MECHANICS.md
│   ├── PROMPT_STRATEGY_FOR_MASTERMIND.md
│   ├── PROMPT_EXAMPLES_REFERENCE.md
│   ├── ACADEMIC_PROMPT_STRUCTURES.md
│   ├── FILE_STRUCTURE.md (this file)
│   └── PARADIGM_ARCHITECTURE.md (TODO)
│
├── prompts/                       # Prompt definitions (TODO - optional)
│   ├── analyzer_prompt.py        # Could move prompts here
│   ├── proposer_prompt.py
│   ├── strategist_prompt.py
│   └── validator_prompt.py
│
├── output/                        # Generated files
│   ├── puzzles.json              # Puzzle database
│   └── logs/                      # Execution logs
│
├── .env                           # Environment config
├── .claude/settings.json          # Claude Code settings
├── requirements.txt               # Python dependencies
└── README.md                      # Project overview
```

---

## Agent Files (`src/agents/`)

### `base_agent.py`
**Responsibility:** Base class for all agents
```python
class BaseAgent:
  - call_llm(prompt) → str
  - parse_json_response(response) → dict
  - get_stats() → dict
```

### `analyzer.py`
**Responsibility:** Extract constraints from feedback
```python
class AnalyzerAgent(BaseAgent):
  - analyze_feedback(guess, feedback, history)
  - process() [standard interface]
```

### `proposer.py`
**Responsibility:** Generate next guess (Tree-of-Thoughts)
```python
class ProposerAgent(BaseAgent):
  - propose_guess(strategy, constraints, colors, pegs, history)
  - process() [standard interface]
```

### `strategist.py`
**Responsibility:** Propose high-level strategy
```python
class StrategistAgent(BaseAgent):
  - propose_strategy(guess_history, difficulty)
  - process() [standard interface]
```

### `validator.py`
**Responsibility:** Quality control before submission
```python
class ValidatorAgent(BaseAgent):
  - validate_guess(guess, colors, length, history)
  - validate_with_llm(...) [constraint-aware]
  - process() [standard interface]
```

### `boss.py`
**Responsibility:** Boss-Worker orchestration (one paradigm)
```python
class BossAgent(BaseAgent):
  - orchestrate_round(game_state)
  - _ask_proposer_with_retry(...)
  - get_stats()
```

---

## Paradigm Files (`src/paradigms/`)

### `boss_worker.py` ✅ (DONE)
**Architecture:** One boss coordinates 4 workers
```
         Boss (orchestrator)
         /  |  \  \
    Strat Ana Prop Val
        ↓   ↓   ↓   ↓
    [All in sequence]
        ↓
    Game Engine
```

### `round_table.py` (TODO - Next)
**Architecture:** All agents equal, peer-to-peer discussion
```
    Strategist  Analyzer
        \      /
         \    /
      Proposer (hub?)
        /    \
       /      \
   Validator  (Others)
```

### `competition.py` (TODO)
**Architecture:** Agents propose competing guesses
```
Agent1: proposes guess A
Agent2: proposes guess B
Agent3: proposes guess C
→ Choose best based on some criterion
→ Submit and get feedback
```

### `coopetition.py` (TODO)
**Architecture:** Mix of cooperation and competition
```
Cooperation phase: Work together to extract constraints
Competition phase: Each proposes different guess
Evaluation: Pick best
```

### `experiment.py` (TODO)
**Architecture:** Experimental approaches
```
Novel combinations or approaches
Not yet defined
```

---

## Core Files (`src/core/`)

### `game_engine.py`
**Responsibility:** Mastermind game logic
```python
class GameEngine:
  - submit_guess(guess)
  - compute_feedback(guess, secret)
  - is_game_over()
  - get_stats()
```

### `puzzle_generator.py`
**Responsibility:** Generate puzzle database
```python
- generate_puzzles(n_easy, n_medium, n_hard)
- save_puzzles(puzzles, path)
- load_puzzles(path)
```

### `communication_logger.py`
**Responsibility:** Log all inter-agent communication
```python
class CommunicationLogger:
  - log_message(message_dict)
  - get_all_messages()
  - save_log()
```

### `checkpoint.py`
**Responsibility:** Save/restore game state
```python
- save_checkpoint(game_state, path)
- load_checkpoint(path)
```

---

## Utility Files (`src/utils/`)

### `kaggle_setup.py`
**Responsibility:** Kaggle backend configuration
```python
- load_kaggle_env()
- get_kaggle_client()
```

### `metrics.py` (TODO)
**Responsibility:** Collect and analyze metrics
```python
class MetricsCollector:
  - record_puzzle_result(puzzle_id, result)
  - get_success_rate()
  - get_average_guesses()
  - export_metrics()
```

---

## Test Files (`tests/`)

### `test_easy_puzzle.py`
**Purpose:** Test single easy puzzle
**Uses:** BossWorkerOrchestrator

### `test_boss_worker_kaggle.py`
**Purpose:** Test multiple puzzles with Boss-Worker
**Uses:** BossWorkerOrchestrator

### `test_round_table.py` (TODO)
**Purpose:** Test Round-Table paradigm
**Uses:** RoundTableOrchestrator

### `test_agent_reasoning.py`
**Purpose:** Analyze agent outputs for specific states
**Uses:** Individual agents

---

## Documentation Files (`docs/`)

### Reference
- `MASTER_CHECKLIST.md` - Project status
- `SYSTEM_OVERVIEW.md` - Architecture overview
- `FILE_STRUCTURE.md` (this file) - File organization

### Implementation
- `IMPLEMENTATION_COMPLETE.md` - What's been done
- `PARADIGM_ARCHITECTURE.md` (TODO) - How each paradigm works

### Guides
- `TESTING_GUIDE.md` - How to test
- `MASTERMIND_REASONING_GUIDE.md` - Agent reasoning
- `GAME_MECHANICS.md` - Game rules

### Research
- `RESEARCH_FINDINGS.md` - Academic research
- `PROMPT_STRATEGY_FOR_MASTERMIND.md` - Prompt strategy
- `PROMPT_EXAMPLES_REFERENCE.md` - Example prompts
- `ACADEMIC_PROMPT_STRUCTURES.md` - Paper analysis

---

## Import Structure (How files reference each other)

```
Paradigms import:
  paradigms/boss_worker.py
    ├── agents/boss.py
    ├── core/game_engine.py
    └── core/communication_logger.py

Tests import:
  tests/test_boss_worker_kaggle.py
    ├── paradigms/boss_worker.py
    └── core/puzzle_generator.py

Agents import:
  agents/base_agent.py
    └── utils/kaggle_setup.py
  
  agents/analyzer.py, proposer.py, strategist.py, validator.py
    └── base_agent.py
```

---

## What's Where

| Component | Location | Status |
|-----------|----------|--------|
| Boss-Worker paradigm | `src/paradigms/boss_worker.py` | ✅ Done |
| Round-Table paradigm | `src/paradigms/round_table.py` | ❌ TODO |
| Competition paradigm | `src/paradigms/competition.py` | ❌ TODO |
| All 4 agents | `src/agents/*.py` | ✅ Improved |
| Game logic | `src/core/game_engine.py` | ✅ Working |
| Puzzle generation | `src/core/puzzle_generator.py` | ✅ Working |
| Tests | `tests/*.py` | ⚠️ Partial |
| Documentation | `docs/*.md` | ✅ Complete |

---

## Adding a New Paradigm

To add Round-Table paradigm:

1. **Create file:** `src/paradigms/round_table.py`
2. **Define orchestrator:** `class RoundTableOrchestrator`
3. **Implement `run()` method:** Same interface as BossWorker
4. **Create test:** `tests/test_round_table.py`
5. **Update docs:** Document in PARADIGM_ARCHITECTURE.md

**Same imports needed:**
```python
from game_engine import GameEngine
from agents.analyzer import AnalyzerAgent
from agents.proposer import ProposerAgent
from agents.strategist import StrategistAgent
from agents.validator import ValidatorAgent
from communication_logger import CommunicationLogger
```

---

## Return Type Standard

All paradigms return same format:
```python
{
    "puzzle_id": str,
    "paradigm": str,
    "difficulty": str,
    "success": bool,
    "guesses": int,
    "rounds": int,
    "elapsed_time": float,
    "guess_history": [list of guesses with feedback],
    "message_count": int,
    "token_usage": {agent: tokens},
    "agent_stats": {agent: stats}
}
```

This allows easy comparison between paradigms.

---

## File Count Summary

- **Agent files:** 6 (base + 4 agents + boss)
- **Paradigm files:** 1 (boss_worker done) → 5 total planned
- **Core files:** 4
- **Utility files:** 2
- **Test files:** 5-7
- **Documentation:** 10+
- **Total Python files:** ~20
- **Total docs:** ~15

**Status:** Well-organized, ready to scale to 5 paradigms

