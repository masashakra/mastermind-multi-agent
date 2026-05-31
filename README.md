# Boss-Worker Multi-Agent Paradigm

A complete, production-ready multi-agent system for solving Mastermind puzzles using centralized hierarchical coordination.

## Quick Start

```bash
# Set up Kaggle GPU backend (or use Claude/Groq)
export KAGGLE_URL="https://flatware-urgent-everglade.ngrok-free.dev"
export KAGGLE_MODEL="llama3.1:8b"

# Run the system
python3 src/paradigms/boss_worker/orchestrator.py
```

## What It Does

A **Boss agent** coordinates 4 specialized worker agents to solve Mastermind puzzles:

1. **Analyzer** - Extracts constraints from game feedback
2. **Strategist** - Determines game phase and strategy
3. **Proposer** - Generates guesses respecting constraints
4. **Validator** - Checks guess validity before submission

## System Architecture

```
Mastermind Game Engine (8 rounds max)
    ↑ feedback
    ↓ guess
Boss Orchestrator (LangGraph state machine)
    ├─ boss_run_round
    ├─ submit_guess  
    └─ check_result
        ↓
Registry (agent discovery)
    ├─ Analyzer (8101)
    ├─ Strategist (8102)
    ├─ Proposer (8103)
    ├─ Validator (8104)
    ├─ Logger (8105)
    └─ Metrics (8106)
```

## Documentation

- **FINAL_STATUS.md** - Complete technical reference (architecture, testing, fixes)
- **QUICK_START.md** - How to run the system with different LLM backends

## Features

✅ **Centralized Coordination** - Boss orchestrates all workers  
✅ **Autonomous Agents** - Each agent makes LLM-based decisions  
✅ **Quality Gates** - Validator prevents invalid submissions  
✅ **Service Discovery** - Agents register with central registry  
✅ **HTTP A2A Protocol** - Agents communicate via standardized messages  
✅ **Multi-LLM Support** - Works with Groq, Claude, Kaggle, Ollama  
✅ **Error Handling** - Retries, rate limiting, graceful degradation  
✅ **Production Ready** - Tested, documented, clean codebase  

## LLM Backends

Choose any of these LLM providers:

```bash
# Kaggle GPU (recommended - unlimited, fast)
export KAGGLE_URL="https://your-ngrok-url.ngrok-free.dev"

# Groq (free tier, rate-limited)
export GROQ_API_KEY="gsk_..."

# Claude API (most reliable)
export ANTHROPIC_API_KEY="sk-ant-..."

# Ollama (local, GPU-intensive)
# (no setup needed, default)
```

## Expected Results

| Difficulty | Success Rate | Avg Rounds | Time |
|------------|--------------|-----------|------|
| Easy | ~85-90% | 5-6 | 1-2 min |
| Medium | ~70-75% | 6-7 | 2-3 min |
| Hard | ~50-60% | 7-8 | 2-3 min |

## File Structure

```
src/
├── base/              # Base agent infrastructure
├── communication/     # A2A protocol
├── paradigms/
│   └── boss_worker/   # Boss-Worker paradigm (main implementation)
│       ├── orchestrator.py
│       └── agents/
│           ├── boss.py
│           ├── analyzer.py
│           ├── strategist.py
│           ├── proposer.py
│           ├── validator.py
│           └── agent_server.py
├── registry/         # Agent discovery service
├── game_engine.py    # Mastermind rules
└── puzzle_generator.py  # Puzzle generation

output/
└── puzzles.json      # Test puzzles

FINAL_STATUS.md       # Technical reference
QUICK_START.md        # Getting started guide
```

## Status

✅ **Complete and tested**  
✅ **Production ready**  
✅ **Ready for research**  

## Getting Help

See QUICK_START.md for troubleshooting and detailed configuration.

---

**Version:** 1.0  
**Status:** Production Ready  
**Last Updated:** May 31, 2026
