# Comprehensive Logging for Direct Debate with Judge Feedback

All events, decisions, and LLM interactions are logged to a structured JSON file.

## Log File Location
```
logs/{puzzle_id}_dd_judge_feedback_{provider}_{run_tag}_messages.log
```

Example: `logs/MM_008_dd_judge_feedback_deepseek_test_messages.log`

## What Gets Logged

### 1. Orchestrator Events

#### Initialization
- Registry startup
- Team agent startup
- Judge initialization
- Message logger initialization

#### Per-Round Events
- **proposal_request**: Teams requested to generate proposals
- **proposals_received**: Both team proposals received by Judge
- **guess_submission**: Judge-selected guess submitted to game engine
- **guess_feedback**: Game engine feedback received
- **guess_invalid**: Invalid guess rejected by game engine

### 2. Team Agent Events

#### Proposal Generation
- **proposal_request**: Proposal generation initiated (round, shared history length)
- **proposal_generated**: Proposal completed (guess, reasoning, strategy, confidence)
- **error**: Errors during proposal generation

#### LLM Interactions
- AnalyserStrategist LLM calls (strategy analysis)
- Solver LLM calls (guess generation)
- Conversation turns logged by BaseAgent

### 3. Judge Events

#### Decision Making
- **judge_decision**: Judge's final decision (selected team, guess, reasoning, confidence)
- **judge_error**: Judge evaluation errors

### 4. Game Engine Events

#### Guess Validation
- Correct pegs feedback
- Correct positions feedback
- Puzzle solved status
- Invalid guess errors

## Log Entry Structure

Each entry contains:
```json
{
  "timestamp": 1234567890.123,
  "datetime_str": "2025-06-07T15:30:45.123456",
  "event_type": "proposal_generated|guess_feedback|judge_decision|etc",
  "agent_name": "team_1|Judge|Orchestrator|etc",
  "status": "ok|error",
  "error": "error message if status=error",
  "metadata": {
    "round": 1,
    "guess": ["red", "blue", "green", "yellow"],
    "correct_pegs": 2,
    "correct_positions": 1,
    "selected_team": "team_1",
    "confidence": 85,
    "reasoning": "..."
  }
}
```

## Log Summary

After puzzle completion, run:
```python
logger = get_message_logger()
logger.print_summary()
```

Output shows:
- Total log entries
- Entries by event type
- Entries by agent
- Duration in seconds
- Log file path

## Enabling Full Message Logging

The message logger is **automatically initialized** in:
1. `orchestrator.py:__init__()` - Creates message logger
2. `agent_server.py:get_proposal()` - Logs proposal generation
3. LangGraph nodes - Log judge decisions, submissions, feedback

## Event Type Reference

| Event Type | Agent | Details |
|-----------|-------|---------|
| proposal_request | Team | Proposal generation requested |
| proposal_generated | Team | Proposal completed (guess, reasoning, strategy) |
| proposals_received | Judge | Both proposals received |
| judge_decision | Judge | Judge selected guess (reasoning, confidence) |
| guess_submission | Orchestrator | Guess submitted to game engine |
| guess_feedback | Orchestrator | Feedback from game engine (pegs, positions) |
| guess_invalid | Orchestrator | Invalid guess rejected |
| error | Various | Error occurred |

## Accessing Logs

### Python
```python
import json
with open("logs/MM_008_dd_judge_feedback_deepseek_test_messages.log") as f:
    log_data = json.load(f)
    entries = log_data["puzzle_run_log"]["entries"]
```

### Command Line
```bash
cat logs/MM_008_dd_judge_feedback_deepseek_test_messages.log | jq '.puzzle_run_log.entries[] | select(.event_type=="judge_decision")'
```

### Real-time Monitoring
Logs are written immediately after each entry, enabling real-time monitoring of puzzle solving progress.

## LLM Call Logging

All LLM calls are logged by BaseAgent including:
- Prompt sent to LLM
- LLM response
- Parsed result
- Token usage (if available)

This is handled by BaseAgent's conversation logger (parent class).

## Complete Example

```json
{
  "puzzle_run_log": {
    "start_time": 1717858245.123,
    "start_datetime": "2025-06-07T15:30:45.123456",
    "total_entries": 45,
    "entries": [
      {
        "timestamp": 1717858245.456,
        "datetime_str": "2025-06-07T15:30:45.456789",
        "event_type": "proposal_request",
        "agent_name": "team_1",
        "status": "ok",
        "metadata": {
          "round": 1,
          "shared_history_len": 0,
          "difficulty": "easy"
        }
      },
      {
        "timestamp": 1717858246.123,
        "datetime_str": "2025-06-07T15:30:46.123456",
        "event_type": "proposal_generated",
        "agent_name": "team_1",
        "status": "ok",
        "metadata": {
          "round": 1,
          "guess": ["red", "blue", "green", "yellow"],
          "confidence": 50,
          "strategy": "Start with exploratory guess of primary colors",
          "reasoning": "First round - use classic opening guess to gather info"
        }
      },
      {
        "timestamp": 1717858250.456,
        "datetime_str": "2025-06-07T15:30:50.456789",
        "event_type": "judge_decision",
        "agent_name": "Judge",
        "status": "ok",
        "metadata": {
          "round": 1,
          "selected_team": "team_1",
          "winning_guess": ["red", "blue", "green", "yellow"],
          "confidence": 60,
          "reasoning": "Team A's classic opening balances information gain with exploratory coverage"
        }
      }
    ]
  }
}
```

## Running with Logging Enabled

All logging is automatic - just run:

```python
from paradigms.direct_debate_judge_feedback.orchestrator import DirectDebateJudgeFeedbackOrchestrator

orchestrator = DirectDebateJudgeFeedbackOrchestrator(puzzle, provider="deepseek")
result = orchestrator.run()

# Logs automatically saved to logs/{puzzle_id}_dd_judge_feedback_{provider}_messages.log
```

No additional configuration needed!
