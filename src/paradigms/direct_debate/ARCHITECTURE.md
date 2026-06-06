# 2v2 Direct Debate Architecture

## Overview
Autonomous peer-to-peer multi-agent system where **2 teams** compete head-to-head solving Mastermind puzzles.

Each team has **2 specialized agents** with distinct roles:

### Agent Roles

#### **Solver Agent** 
- **Responsibility**: Generate guesses based on strategy
- **Does NOT**: Debate, communicate with other teams
- **Inputs**: 
  - Guess history
  - Feedback from orchestrator
  - Strategy from team's Analyser-Strategist
- **Outputs**: Next guess

#### **Analyser-Strategist Agent**
- **Responsibility**: Analyze patterns, develop strategy, debate with other teams
- **Does NOT**: Generate guesses (delegates to Solver)
- **Inputs**:
  - Guess history + feedback
  - Public leaderboard (visible to all teams)
  - Peer debate messages from other teams' analysers
- **Outputs**: Strategy guidance for Solver

## System Architecture

```
┌─ ORCHESTRATOR ──────────────────────────────────┐
│  • Game validation (shared Mastermind engine)   │
│  • Public leaderboard (feedback scores only)    │
│  • Determines winner                            │
└─────────────────────────────────────────────────┘

┌─ TEAM 1 ────────────────────────────────────────┐
│                                                 │
│  ┌─ Analyser-Strategist (Port 8302) ──────┐   │
│  │ • Analyzes feedback patterns            │   │
│  │ • Develops strategy                     │   │
│  │ • Debates with Team 2's analyser        │   │
│  │ • Instructs Solver                      │   │
│  └─────────────────────────────────────────┘   │
│                      │ (HTTP A2A)              │
│  ┌─ Solver (Port 8301) ────────────────────┐   │
│  │ • Generates guesses                     │   │
│  │ • Submits to orchestrator               │   │
│  │ • Reports feedback to analyser          │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘

┌─ TEAM 2 ────────────────────────────────────────┐
│                                                 │
│  ┌─ Analyser-Strategist (Port 8304) ──────┐   │
│  │ • Analyzes feedback patterns            │   │
│  │ • Develops strategy                     │   │
│  │ • Debates with Team 1's analyser        │   │
│  │ • Instructs Solver                      │   │
│  └─────────────────────────────────────────┘   │
│                      │ (HTTP A2A)              │
│  ┌─ Solver (Port 8303) ────────────────────┐   │
│  │ • Generates guesses                     │   │
│  │ • Submits to orchestrator               │   │
│  │ • Reports feedback to analyser          │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Communication Flow

### Internal Team Communication (HTTP A2A)
- **Analyser → Solver**: Strategy guidance
- **Solver → Orchestrator**: Submit guess
- **Orchestrator → Solver**: Feedback
- **Analyser ← Solver**: Feedback for reflection

### Inter-Team Communication (HTTP A2A)
- **Analyser-Strategist ↔ Analyser-Strategist**: Debate messages
- Only analysers communicate with other teams
- Solvers never communicate with opponents

## Puzzle Solving Loop (Per Round)

```
Analyser-Strategist:
  1. analyze_and_strategize()
     - Analyze guess history + feedback
     - Check public leaderboard
     - Develop strategy
  2. Send strategy to Solver

Solver:
  3. solve_round()
     - Generate guess based on strategy
     - Return guess
  4. Submit guess to orchestrator
  5. Receive feedback

Analyser-Strategist:
  6. reflect_on_round()
     - Update learned_hypotheses
     - Update color_analysis
     - Update position_analysis
  7. Discover peers & debate
     - Get other teams' analysers from registry
     - Send debate message to each
     - Receive peer messages

Loop repeats until puzzle solved or max rounds reached
```

## Key Features

### 1. **Shared Game State**
- One Mastermind puzzle shared between teams
- Orchestrator validates all guesses
- First team to solve wins

### 2. **Public Leaderboard**
- All teams see feedback scores (pegs + positions)
- Guesses remain **private** (not visible to opponents)
- Competitive context without revealing strategy

### 3. **Agent Specialization**
- **Solver**: Lightweight, focused on guess generation
- **Analyser-Strategist**: Heavy reasoning, pattern analysis, debate

### 4. **Learned Hypotheses**
- Both agents track learned patterns:
  - `learned_hypotheses`: Hypotheses about code (e.g., "colors at position X", "colors NOT in code")
  - `color_analysis`: Which colors appear in correct feedback
  - `position_analysis`: Position constraints

### 5. **Debate System**
- Analysers engage in competitive debate
- LLM-driven responses to peer strategies
- Competitive intelligence for improving strategy

## Files

| File | Role |
|------|------|
| `orchestrator.py` | Game orchestrator, leaderboard, winner determination |
| `solver.py` | Solver agent class |
| `analyser_strategist.py` | Analyser-Strategist agent class |
| `agent_server.py` | FastAPI servers for both agent types |
| `team_agent.py` | **DEPRECATED** (replaced by solver + analyser_strategist) |

## HTTP Endpoints

### Solver (8301, 8303)
- `GET /health` → Liveness check
- `GET /.well-known/agent.json` → Agent card
- `POST /solve_round` → Generate guess (A2A message)

### Analyser-Strategist (8302, 8304)
- `GET /health` → Liveness check
- `GET /.well-known/agent.json` → Agent card
- `POST /analyze` → Develop strategy (A2A message)
- `POST /debate` → Respond to debate (A2A message)
- `POST /receive_message` → Receive peer messages
- `POST /start_puzzle` → Begin autonomous loop

### Orchestrator (dynamic port)
- `POST /submit_guess` → Submit & validate guess
  - Input: `{"team_id": "team_1", "guess": [...]}`
  - Output: `{"valid": true, "feedback": {...}, "public_leaderboard": [...]}`

## Initialization Sequence

1. Orchestrator starts registry server
2. Orchestrator starts HTTP server (for guess validation)
3. For each team (team_1, team_2):
   - Start Solver agent HTTP server
   - Wait for Solver health check
   - Start Analyser-Strategist HTTP server
   - Wait for Analyser-Strategist health check
4. Orchestrator notifies analysers to begin puzzle
5. Analyser runs autonomous loop for each round

## Configuration

- **Teams**: 2 (configurable via `num_teams` parameter)
- **Provider**: DeepSeek R1 (default), configurable
- **Timeout**: 30 minutes for entire puzzle
- **Max Rounds**: 16 per puzzle
- **Available Colors**: 6 (red, yellow, blue, green, white, black)
- **Pegs**: 4 per code

## Testing

```bash
export DEEPSEEK_API_KEY="sk-..."
python3 src/paradigms/direct_debate/orchestrator.py
```

Expected output:
```
[Orchestrator] Teams online: ['team_1', 'team_2']
[Orchestrator] Starting puzzle execution...
[team_1] Round 1
[team_1] Proposed: [...]
[team_2] Round 1
[team_2] Proposed: [...]
```

## Future Enhancements

1. **Shared internal state**: Instead of HTTP, agents could share Python objects within same process
2. **Hierarchical debate**: Analysers debate independently, then vote on next guess
3. **Memory persistence**: Save learned_hypotheses across puzzles
4. **Multi-puzzle tournaments**: Run multiple puzzles, track cumulative score
