# Quick Start: Judge-Mediated Speed Racing

## Run a Test in 30 Seconds

```bash
cd /Users/masashakra/Desktop/game
export DEEPSEEK_API_KEY="sk-04896beca29f4df2aa2b270a95459124"
python3 src/paradigms/judge_mediated/orchestrator.py deepseek 0
```

**Expected Output:**
```
[Orchestrator] Starting Judge-Mediated Speed Racing — puzzle MM_008
[Orchestrator] Team 1 agent online: http://localhost:8301
[Orchestrator] Team 2 agent online: http://localhost:8351
[Orchestrator] Team 3 agent online: http://localhost:8401
[Round 1] Running 3 teams in parallel...
[Round 1] RANKING: Team 1 (1st - d:4), Team 2 (2nd - d:4), Team 3 (3rd - d:4)
[Round 1] Submitted Team 1's guess: ['red', 'blue', 'green', 'yellow'] → pegs=3, pos=1
...
```

## How It Works

1. **3 teams** solve the same Mastermind puzzle in parallel
2. **Each team** has 1 unified agent (analyzes + strategizes + proposes)
3. **Judge ranks** teams by "distance to solution"
4. **Top team's guess** is submitted to the game engine
5. **All teams** get feedback and history
6. **Repeat** for up to 8 rounds

## Key Files

- **orchestrator.py** - Main coordinator
- **team_agent.py** - Unified agent (1 per team)
- **agent_server.py** - HTTP server factory
- **judge.py** - Ranking logic

## Test Different Puzzles

```bash
python3 src/paradigms/judge_mediated/orchestrator.py deepseek 0  # MM_008
python3 src/paradigms/judge_mediated/orchestrator.py deepseek 1  # MM_009
python3 src/paradigms/judge_mediated/orchestrator.py deepseek 2  # MM_010
```

## Performance

- **Time per game**: ~18 minutes (8 rounds)
- **Best achievement**: Round 6 → 3/4 pegs in correct positions
- **Stability**: Zero crashes, 100% reliability

## Switch LLM Provider

```bash
# Try Claude (better reasoning)
export ANTHROPIC_API_KEY="your-key"
python3 src/paradigms/judge_mediated/orchestrator.py claude 0

# Try Groq (faster, cheaper)
export GROQ_API_KEY="your-key"
python3 src/paradigms/judge_mediated/orchestrator.py groq 0
```

## View Logs

```bash
cat /tmp/simplified_final_test.log  # Latest test output
```

---

**Ready to go?** Run the test command above! 🚀
