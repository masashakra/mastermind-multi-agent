# Direct Debate with Judge Feedback

A competitive paradigm where two autonomous teams race to solve the puzzle, but a **judge evaluates their proposals and selects the stronger one** each round.

Built with **LangGraph** state management (matching boss_worker structure).

## Architecture (LangGraph Workflow)

```
┌──────────────────────────────────────────────────────────────┐
│  START                                                        │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ↓
        ┌─────────────────────────┐
        │ collect_proposals       │
        │ (Both teams propose)    │
        └────────────┬────────────┘
                     │
                     ↓
        ┌─────────────────────────┐
        │ judge_decision          │
        │ (Judge selects better)  │
        └────────────┬────────────┘
                     │
            ┌────────┴────────┐
            │                 │
         Valid?            Invalid?
            │                 │
            ↓                 ↓
    ┌──────────────┐   ┌─────────────┐
    │submit_guess  │   │check_result │
    └──────┬───────┘   └─────────────┘
           │                 │
           └────────┬────────┘
                    ↓
        ┌─────────────────────────┐
        │ check_result            │
        │ (More rounds? Solved?)  │
        └────────────┬────────────┘
                     │
            ┌────────┴────────┐
            │                 │
         Loop            Game Over
            │                 │
            ↓                 ↓
    collect_proposals      END
```

## LangGraph State (TypedDict)

```python
class DebateJudgeState(TypedDict):
    round_number:      int
    guess_history:     List[Dict]
    last_guess:        List[str]
    last_feedback:     Dict
    last_selected_team: str
    proposals:         List[Dict]
    judge_decision:    Dict
    solved:            bool
    game_over:         bool
    submit_this_round: bool
    round_result:      Dict
```

## Nodes & Flow

| Node | Input | Output | Purpose |
|------|-------|--------|---------|
| `collect_proposals` | State | proposals | Request proposals from both teams |
| `judge_decision` | proposals + history | judge_decision, last_guess | Judge evaluates and selects |
| `submit_guess` | last_guess | guess_history, last_feedback | Submit to game engine |
| `check_result` | feedback | round_number, game_over | Advance round; check end condition |

## Key Differences from Other Paradigms

| Paradigm | Competition | Judge Role |
|----------|-------------|-----------|
| **Direct Debate** | Direct - first to solve wins | None |
| **Judge-Mediated** | Independent racing - leaderboard | Provides ranking/analysis |
| **Direct Debate Judge Feedback** | ✨ NEW - judge-selected guesses | **Actively selects best proposal** |
| **Coopetition Centralized** | Collaborative with voting | Mediates negotiation |

## Judge Decision Process

The judge uses a **3-turn multi-turn analysis** (if LLM available):

1. **Turn 1**: Objective evaluation
   - Strategy quality of each proposal (0-100)
   - Strengths and weaknesses
   - Initial lean (A/B/equal)

2. **Turn 2**: Weighted comparison
   - Confidence score × 40%
   - Strategy quality × 60%
   - Combined weighted score

3. **Turn 3**: Final decision
   - Commit to choice with reasoning
   - Ensure defensibility

**Fallback (No LLM)**: Simple heuristic - higher confidence + slight diversity bonus

## Running the Paradigm

```python
from paradigms.direct_debate_judge_feedback.orchestrator import DirectDebateJudgeFeedbackOrchestrator
from puzzle_generator import load_puzzles

puzzles = load_puzzles()
puzzle = puzzles[0]

orchestrator = DirectDebateJudgeFeedbackOrchestrator(
    puzzle, 
    provider="deepseek",  # or "groq", "claude", etc.
    num_teams=2
)
result = orchestrator.run()

print(f"Winner: {result['winner']}")
print(f"Rounds: {result['total_rounds']}")
print(f"Solved: {result['success']}")
```

Or from CLI:
```bash
python src/paradigms/direct_debate_judge_feedback/orchestrator.py
```

## Output

Results include:

- **Winner**: Which team had the selected guess that solved it
- **Leaderboard**: Order of teams that solved (typically just winner)
- **Total Rounds**: How many judge selections it took
- **All Guesses**: Complete history of judge-selected guesses and feedback
- **Submission History**: Which team proposed each selected guess
- **Logs**: Per-team message logs merged into main log

## Customization

### Changing Judge Provider
The paradigm respects the provider argument - it initializes the judge with the same LLM provider as teams.

### Disabling LLM Judge (Heuristic Mode)
Judge automatically falls back to heuristic if LLM unavailable (caught via exception).

### Changing Team Count
Set `num_teams` > 2 in orchestrator init (untested - likely needs adaptation).

### Adjusting Judge Confidence Weights
Edit `_evaluate_with_llm()` in [judge.py](agents/judge.py) - change the 0.4 and 0.6 weights in Turn 2.

## Files

- **orchestrator.py**: Main orchestration logic (game loop, judge calls)
- **agents/judge.py**: Judge agent with multi-turn evaluation
- **agents/agent_server.py**: Team agents serving proposals
- **README.md**: This file

## Notes

- Teams can see shared history (last 5 guesses + feedback)
- Teams learn from ALL guesses, not just their own
- Judge selection provides a "quality filter" - teams learn what's valued
- First team to have their proposal selected AND be correct wins
- Max 16 rounds (configurable via MAX_ROUNDS)
