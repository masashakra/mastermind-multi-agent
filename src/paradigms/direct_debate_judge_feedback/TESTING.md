# Testing Guide: Direct Debate with Judge Feedback

## Quick Start

```python
from paradigms.direct_debate_judge_feedback.orchestrator import DirectDebateJudgeFeedbackOrchestrator
from puzzle_generator import load_puzzles

# Load puzzles
puzzles = load_puzzles()
easy_puzzles = [p for p in puzzles if p['difficulty'] == 'easy']
test_puzzle = easy_puzzles[0]

# Run paradigm
orchestrator = DirectDebateJudgeFeedbackOrchestrator(test_puzzle, provider="deepseek")
result = orchestrator.run()

# Check results
print(f"Winner: {result['winner']}")
print(f"Solved: {result['success']}")
print(f"Rounds: {result['total_rounds']}")
print(f"Time: {result['elapsed_time']:.1f}s")
```

## Configuration

### Parameters

| Parameter | Default | Options |
|-----------|---------|---------|
| puzzle | required | Any puzzle from load_puzzles() |
| provider | "deepseek" | "deepseek", "groq", "claude", "openai" |
| run_tag | "" | Any string for log file naming |

### Environment Variables Required

Set ONE of these:

```bash
# DeepSeek (cheapest)
export DEEPSEEK_API_KEY=sk_...

# Or OpenRouter (supports multiple models)
export OPENROUTER_API_KEY=sk_...

# Or Groq (fast)
export GROQ_API_KEY=gsk_...

# Or Claude/Anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

## Expected Behavior

### Per Round
1. **Collect Proposals** (1-2s)
   - Team A analyzes patterns + generates guess
   - Team B analyzes patterns + generates guess
   - Both proposals logged

2. **Judge Decision** (2-3s)
   - Judge evaluates both proposals
   - Multi-turn LLM analysis (3 turns)
   - Selects stronger guess
   - Decision logged with reasoning

3. **Submission** (instant)
   - Selected guess submitted to game engine
   - Feedback received
   - Feedback logged

### Total Runtime
- **8 rounds × ~5-6s per round = 40-48 seconds** (estimated)
- LLM provider speed varies (Groq faster, Claude smarter)

## What Gets Logged

✅ All of the following automatically logged to JSON:

- Proposal generation (both teams)
- Guess proposals (both teams)
- Judge evaluations (3-turn analysis)
- Judge decisions (selected team, reasoning)
- Guess submissions (to game engine)
- Feedback received (pegs, positions)
- Errors (if any)

### View Logs

```bash
# Find log file
ls -lt logs/*dd_judge_feedback* | head -1

# View summary
cat logs/MM_008_dd_judge_feedback_deepseek_test_messages.log | jq '.puzzle_run_log | {total_entries, start_datetime}'

# View all judge decisions
cat logs/MM_008_dd_judge_feedback_deepseek_test_messages.log | jq '.puzzle_run_log.entries[] | select(.event_type=="judge_decision")'

# View guess feedback
cat logs/MM_008_dd_judge_feedback_deepseek_test_messages.log | jq '.puzzle_run_log.entries[] | select(.event_type=="guess_feedback")'
```

## Testing Checklist

- [ ] Set LLM provider API key
- [ ] Load easy puzzle
- [ ] Create orchestrator instance
- [ ] Call orchestrator.run()
- [ ] Check result (winner, solved, rounds)
- [ ] Verify log file created
- [ ] View log entries
- [ ] Confirm all event types present

## Expected Results

### On Easy Puzzles
- **Success Rate**: 80-95% (depending on puzzle difficulty)
- **Avg Rounds**: 4-6 (out of 8 max)
- **Avg Time**: 30-45 seconds

### Sample Output
```
Winner          : team_1 🏆
Puzzle Solved   : YES ✅
Total Rounds    : 5
Elapsed Time    : 38.2s
Total LLM Calls : ~25 (5 per round)

Guess History (Judge-Selected):
  R1. team_1: ['red', 'blue', 'green', 'yellow'] → 2p 1pos
  R2. team_2: ['red', 'blue', 'green', 'white'] → 2p 1pos
  R3. team_1: ['red', 'blue', 'yellow', 'black'] → 2p 2pos
  R4. team_2: ['red', 'green', 'yellow', 'black'] → 3p 2pos
  R5. team_1: ['red', 'green', 'yellow', 'white'] → 4p 4pos ✅ SOLVED!
```

## Troubleshooting

### "No API Key Found"
- Set required API key for chosen provider
- Verify with: `echo $DEEPSEEK_API_KEY` (or equivalent)

### "LLM unavailable" Messages
- Judge falls back to heuristic mode (confidence-based)
- Team agents may fail - LLM provider connection issue
- Check API key validity and quota

### Slow Proposal Generation
- Normal - AnalyserStrategist + Solver each call LLM
- Groq is faster, Claude is slower but smarter
- Parallel proposal generation reduces wait

### Incorrect Guesses
- Judge uses multi-turn analysis (should be good)
- Some easy puzzles genuinely hard (4 colors × 4 positions = high entropy)
- Fallback heuristics may select less optimal guess

## Files to Review

- **orchestrator.py**: Main LangGraph workflow
- **agents/judge.py**: Judge evaluation logic
- **agents/agent_server.py**: Team proposal generation
- **LOGGING.md**: Comprehensive logging details
- **README.md**: Architecture overview

## Next Steps

1. Set API key for chosen provider
2. Run test on easy puzzle
3. Review log file (JSON format)
4. Run on multiple easy puzzles
5. Compare with other paradigms (boss_worker, direct_debate, etc.)

## Collecting Results

```python
import json

# Load log file
with open("logs/MM_008_dd_judge_feedback_deepseek_test_messages.log") as f:
    log = json.load(f)

# Extract metrics
entries = log["puzzle_run_log"]["entries"]
judge_decisions = [e for e in entries if e["event_type"] == "judge_decision"]
guess_feedbacks = [e for e in entries if e["event_type"] == "guess_feedback"]

print(f"Judge decisions made: {len(judge_decisions)}")
print(f"Guesses submitted: {len(guess_feedbacks)}")

# Find winning guess
for fb in guess_feedbacks:
    if fb["metadata"].get("correct_pegs") == 4:
        print(f"Solved in round {fb['metadata']['round']}: {fb['metadata']['guess']}")
        break
```

## Support

- Check LOGGING.md for detailed logging structure
- Check README.md for architecture
- Check orchestrator.py for flow logic
- Check judge.py for decision logic
