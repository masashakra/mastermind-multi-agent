# Message Logging System

## Overview

All paradigms use a **unified MessageLogger** system to log:
- ✅ A2A message sends/receives (all data exchanged)
- ✅ Agent conversations (LLM thinking, multi-turn)
- ✅ Routing decisions (why agents sent to whom)
- ✅ Errors and events
- ✅ Full timestamps for analysis

## How to Set Up Logging in a Paradigm

### 1. In Orchestrator `__init__`:

```python
from communication.message_logger import init_message_logger

def __init__(self, puzzle: Dict[str, Any], provider: str = "kaggle"):
    self.puzzle = puzzle
    self.provider = provider
    
    # Initialize message logger
    puzzle_id = puzzle.get("puzzle_id", "unknown")
    paradigm = self.paradigm  # e.g., "round_table", "boss_worker"
    log_file = f"logs/{puzzle_id}_{paradigm}_{provider}_messages.log"
    
    self.message_logger = init_message_logger(log_file)
```

### 2. In Agent's send A2A message:

```python
from communication.message_logger import get_message_logger

async def send_a2a_message(self, ...):
    # ... existing code ...
    
    logger = get_message_logger()
    logger.log_a2a_send(
        agent_name=self.name,
        message_id=request_msg.message_id,
        sender_id=request_msg.sender_id,
        receiver_id=request_msg.receiver_id,
        action=action,
        payload=payload,
        routing_decision=routing_decision,
    )
```

### 3. In Agent's conversation turns:

```python
from communication.message_logger import get_message_logger

def call_llm_conversation(self, system_prompt, user_message):
    # ... LLM call ...
    response = ...
    
    logger = get_message_logger()
    turn = len(self.conversation) // 2
    logger.log_conversation(
        agent_name=self.name,
        turn=turn,
        role="user",
        content=user_message[:500],
    )
    logger.log_conversation(
        agent_name=self.name,
        turn=turn,
        role="assistant",
        content=response[:500],
    )
```

## Log File Format

```
logs/
├── MM_002_round_table_openai_messages.log
├── MM_002_boss_worker_groq_messages.log
├── MM_003_round_table_deepseek_messages.log
└── ...
```

Each file is JSON:
```json
{
  "puzzle_run_log": {
    "start_time": 1234567890.5,
    "start_datetime": "2026-06-02T12:34:56",
    "total_entries": 145,
    "entries": [
      {
        "timestamp": 1234567890.5,
        "datetime_str": "2026-06-02T12:34:56",
        "event_type": "a2a_send",
        "agent_name": "Analyzer_RoundTable",
        "message_id": "abc123",
        "sender_id": "analyzer_round_table",
        "receiver_id": "strategist_round_table",
        "action": "strategy",
        "payload": {...},
        "status": "ok"
      },
      ...
    ]
  }
}
```

## Viewing Logs

```bash
# Summary view
python3 view_message_log.py logs/MM_002_round_table_openai_messages.log

# Full detailed view
python3 view_message_log.py logs/MM_002_round_table_openai_messages.log --full

# Filter by agent
python3 view_message_log.py logs/MM_002_round_table_openai_messages.log --agent Analyzer

# Filter by event type
python3 view_message_log.py logs/MM_002_round_table_openai_messages.log --type conversation
python3 view_message_log.py logs/MM_002_round_table_openai_messages.log --type a2a_send
```

## Event Types

| Type | Description | Logged Where |
|------|-------------|--------------|
| `a2a_send` | Agent sends A2A message to peer | `base_agent.send_a2a_message()` |
| `a2a_receive` | Agent receives A2A message | Agent handlers |
| `conversation` | LLM request/response turn | `base_agent.call_llm_conversation()` |
| `routing` | Agent's routing decision | Agent handlers |
| `error` | Error or exception | Throughout |

## Integration Checklist

For each paradigm:

- [ ] Orchestrator calls `init_message_logger(log_file)`
- [ ] Agents call `get_message_logger()` when sending A2A messages
- [ ] Agents log conversation turns in `call_llm_conversation()`
- [ ] Optional: Agent handlers log routing decisions

## Status

Currently integrated:
- ✅ `round_table` — Full logging (A2A, conversation, routing)
- ❌ `boss_worker` — TODO
- ❌ `direct_debate` — TODO
- ❌ `judge_mediated` — TODO
- ❌ `moderator_mediated` — TODO
- ❌ `direct_adversarial` — TODO
