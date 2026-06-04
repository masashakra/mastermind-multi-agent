# Logging Specification - Complete Data Capture

## Purpose

When you run 30 puzzles × 6 paradigms = 180 puzzle-solving sessions, each session generates a comprehensive JSON log. This document specifies exactly what's logged and what analysis can be derived from it.

---

## What Gets Logged

### Session Object Structure

```json
{
  // ============ METADATA ============
  "puzzle_id": "MM_001",
  "paradigm": "round_table",
  "difficulty": "easy",
  "provider": "openai",
  "timestamp_start": "2026-06-02T10:30:00.123456",
  "timestamp_end": "2026-06-02T10:32:15.654321",

  // ============ PUZZLE DETAILS (for verification & analysis) ============
  "puzzle_metadata": {
    "secret_code": ["red", "blue", "green", "yellow"],
    "available_colors": ["red", "blue", "green", "yellow", "white", "black"],
    "pegs": 4
  },

  // ============ RESULTS ============
  "result": {
    "success": true,
    "guesses": 5,
    "rounds": 5,
    "termination_reason": "solution_found"
  },

  // ============ RESOURCE USAGE ============
  "token_usage": {
    "total_input": 8234,
    "total_output": 2156,
    "per_round": [
      {"round": 1, "input": 1800, "output": 500, "total": 2300},
      {"round": 2, "input": 1600, "output": 450, "total": 2050},
      // ... up to round N
    ]
  },

  // ============ PER-ROUND DATA ============
  "round_data": {
    "1": {
      "guess": ["red", "blue", "green", "yellow"],
      "feedback": {"correct_pegs": 2, "correct_positions": 1},
      "response_chars": 1200,
      "model": "gpt-4-turbo"
    },
    "2": {
      "guess": ["white", "black", "red", "blue"],
      "feedback": {"correct_pegs": 3, "correct_positions": 2},
      "response_chars": 1850,
      "model": "gpt-4-turbo"
    }
    // ... more rounds
  },

  // ============ INTER-AGENT MESSAGES (for coordination quality) ============
  "messages": [
    {
      "timestamp": "2026-06-02T10:30:05.123456",
      "round": 1,
      "sender": "strategist",
      "receiver": "boss",
      "message_type": "strategy_proposal",
      "content": {
        "analysis": "No previous feedback yet...",
        "strategy": "Try diverse color distribution...",
        "reasoning": "..."
      }
    },
    {
      "timestamp": "2026-06-02T10:30:06.234567",
      "round": 1,
      "sender": "boss",
      "receiver": "analyzer",
      "message_type": "analysis_request",
      "content": {
        "request": "Analyze the feedback constraints..."
      }
    },
    // ... more messages from all agents
  ],

  // ============ CONSTRAINT EXTRACTION (for analysis quality) ============
  "constraints_extracted": [
    {
      "round": 1,
      "analysis": {
        "impossible": ["white"],
        "confirmed": ["red", "blue"],
        "locked_positions": [
          {"position": 0, "color": "red"},
          {"position": 2, "color": "green"}
        ]
      },
      "timestamp": "2026-06-02T10:30:07.345678"
    },
    // ... more constraints
  ],

  // ============ AGENT PERFORMANCE (for role adherence & coordination) ============
  "agent_performance": {
    "analyzer": {
      "rounds": {
        "1": {
          "response_length": 1200,
          "parse_success": true,
          "constraints_found": 3
        },
        // ... per-round
      }
    },
    "strategist": {
      "rounds": {
        // ... similar structure
      }
    }
    // ... other agents
  }
}
```

---

## What Analysis Can Be Done

### 1. Task Success Metrics (Automated)

**From:** `result`, `puzzle_metadata`

```python
# Success rate
success_count = sum(1 for s in sessions if s["result"]["success"])
success_rate = success_count / len(sessions) * 100

# Avg guesses (for solved puzzles)
solved = [s for s in sessions if s["result"]["success"]]
avg_guesses = sum(s["result"]["guesses"] for s in solved) / len(solved)

# Failure rate
failure_rate = 100 - success_rate

# Verification
for session in sessions:
    if session["result"]["success"]:
        final_guess = session["round_data"][str(session["result"]["rounds"])]["guess"]
        secret = session["puzzle_metadata"]["secret_code"]
        assert final_guess == secret  # ✓ Verify solution is correct
```

### 2. Communication Efficiency Metrics (Automated)

**From:** `token_usage`, `messages`

```python
# Token cost
total_tokens = session["token_usage"]["total_input"] + session["token_usage"]["total_output"]
tokens_per_guess = total_tokens / session["result"]["guesses"]

# Message count
msg_count = len(session["messages"])
msgs_per_round = msg_count / session["result"]["rounds"]

# Message breakdown
msg_types = {}
for msg in session["messages"]:
    msg_type = msg["message_type"]
    msg_types[msg_type] = msg_types.get(msg_type, 0) + 1
# e.g., {"strategy_proposal": 5, "analysis": 5, "validation": 5}
```

### 3. Wasted Communication Rate (LLM-Judge)

**From:** `messages`, `puzzle_metadata`, `result`

```python
# Call Claude API with all messages to classify:
# - PRODUCTIVE: Advances task, provides actionable info
# - NEUTRAL: Acknowledged but non-essential
# - WASTED: Redundant, off-topic, contradictory

prompt = f"""
Puzzle: {session['puzzle_metadata']['secret_code']}
Result: Solved in {session['result']['guesses']} guesses

Messages (for classification):
{json.dumps(session['messages'][:10])}

Classify each message as PRODUCTIVE / NEUTRAL / WASTED.
"""

# Response gives wasted_rate, productive_rate, etc.
```

### 4. Role Adherence (LLM-Judge)

**From:** `messages`, agent roles

```python
# For each message, evaluate if sender adhered to their role

# Strategist should: propose strategies, analyze patterns
# Analyzer should: extract constraints, interpret feedback
# Proposer should: generate guesses
# Validator should: check validity

prompt = f"""
Agent roles:
- Strategist: Propose strategies
- Analyzer: Extract constraints
- Proposer: Generate guesses
- Validator: Check validity

For each message from {sender}, is it on-role?

Messages: {json.dumps(session['messages'])}
"""

# Response gives adherence per agent
```

### 5. Convergence Speed (Semantic Analysis)

**From:** `messages` (strategist proposals), `constraints_extracted`

```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer("all-MiniLM-L6-v2")

# Extract Strategist proposals by round
strategies = {}
for msg in session["messages"]:
    if msg["sender"] == "strategist" and msg["message_type"] == "strategy_proposal":
        round_num = msg["round"]
        strategies[round_num] = msg["content"]["strategy"]

# Compute semantic similarity between consecutive rounds
# When similarity > 0.85, strategy has converged
for i in range(1, len(strategies)):
    prev_embedding = model.encode(strategies[i-1])
    curr_embedding = model.encode(strategies[i])
    similarity = cosine_similarity([prev_embedding], [curr_embedding])[0][0]
    if similarity > 0.85:
        convergence_round = i
        break
```

### 6. Coordination Score (LLM-Judge)

**From:** `messages`, `result`, `puzzle_metadata`

```python
# Holistic evaluation of coordination quality on 1-5 scale

prompt = f"""
Paradigm: {session['paradigm']}
Success: {session['result']['success']}
Guesses: {session['result']['guesses']}

Messages: {json.dumps(session['messages'])}

Evaluate on two dimensions (1-5 each):

1. COMMUNICATION FLOW
   - Clarity and coherence of information sharing
   - Appropriate requests/responses
   - Building on prior information

2. COORDINATION STRATEGY
   - Clear role definition and adherence
   - Logical task sequencing
   - Appropriate workload distribution

Rate both dimensions and provide overall score.
"""

# Response gives communication_flow (1-5), coordination_strategy (1-5)
```

---

## Data Completeness Checklist

### ✅ Currently Logged

- [x] Puzzle ID, paradigm, difficulty
- [x] Provider (openai, deepseek, groq)
- [x] Timestamps (start, end)
- [x] Secret code (for verification)
- [x] Available colors (for analysis)
- [x] Success/failure status
- [x] Guess count and rounds
- [x] Token usage (total + per-round)
- [x] All inter-agent messages with:
  - [x] Timestamp
  - [x] Sender and receiver
  - [x] Message type
  - [x] Full content
- [x] Per-round guess and feedback
- [x] Response character length
- [x] LLM model used
- [x] Extracted constraints per round
- [x] Agent performance tracking

### ✅ Ready for Analysis

- [x] **Task success metrics** — No additional logging needed
- [x] **Communication metrics** — No additional logging needed
- [x] **Convergence speed** — Have message content ✓
- [x] **Wasted comm rate** — Have full messages ✓
- [x] **Role adherence** — Have messages + sender ✓
- [x] **Coordination score** — Have all data ✓

---

## How to Run Tests and Capture Data

### Single Paradigm (6-10 puzzles)

```bash
python3 test_round_table_metrics.py
```

Output:
- `output/sessions/MM_001_round_table.json`
- `output/sessions/MM_002_round_table.json`
- ... (one per puzzle)
- `output/metrics/round_table_summary.json`

### All 30 Puzzles for One Paradigm

Create a loop test script:

```python
def test_paradigm_all_puzzles(paradigm: str):
    puzzles = load_puzzles()  # All 30 puzzles
    
    for puzzle in puzzles:
        metrics = solve_puzzle_with_metrics(puzzle["puzzle_id"], paradigm)
        metrics.save()  # Auto-saves to output/sessions/
```

### All 6 Paradigms × 30 Puzzles = 180 Sessions

Once you have all 180 sessions in `output/sessions/`, you can:

```python
# Load all sessions
import glob, json

sessions = {}
for json_file in glob.glob("output/sessions/*.json"):
    with open(json_file) as f:
        session = json.load(f)
        paradigm = session["paradigm"]
        if paradigm not in sessions:
            sessions[paradigm] = []
        sessions[paradigm].append(session)

# Compute all 9 metrics from the logs
for paradigm, paradigm_sessions in sessions.items():
    # Success rate
    success_rate = compute_success_rate(paradigm_sessions)
    
    # Avg guesses
    avg_guesses = compute_avg_guesses(paradigm_sessions)
    
    # Token cost
    avg_tokens = compute_avg_tokens(paradigm_sessions)
    
    # Message count
    avg_messages = compute_avg_messages(paradigm_sessions)
    
    # Wasted comm rate (LLM-Judge)
    wasted_rate = evaluate_wasted_comm_with_judge(paradigm_sessions)
    
    # Role adherence (LLM-Judge)
    role_adherence = evaluate_role_adherence_with_judge(paradigm_sessions)
    
    # Convergence speed (Embeddings)
    convergence = compute_convergence_speed(paradigm_sessions)
    
    # Coordination score (LLM-Judge)
    coord_score = evaluate_coordination_with_judge(paradigm_sessions)

    print(f"\n{paradigm} Results:")
    print(f"  Success: {success_rate:.1f}%")
    print(f"  Avg guesses: {avg_guesses:.1f}")
    print(f"  Tokens/guess: {avg_tokens:.0f}")
    print(f"  Wasted comm: {wasted_rate:.1f}%")
    print(f"  Role adherence: {role_adherence:.1f}%")
    print(f"  Convergence: Round {convergence}")
    print(f"  Coordination: {coord_score:.2f}/5.0")
```

---

## Key Insights

### Why This Structure?

1. **Puzzle metadata stored** — Can verify solutions after-the-fact
2. **All messages captured** — Can evaluate coordination quality with LLM-Judge
3. **Per-round details** — Can analyze strategy evolution
4. **Token tracking** — Can measure communication cost
5. **Agent performance** — Can assess role adherence per-agent

### What's NOT Logged (and why)

- Full LLM conversation history per agent — Too large, can reconstruct from messages
- Raw API responses — Would be redundant (we extract what we need)
- Agent reasoning chains — Already captured in message content

### Future Extension

If you need more detail later:
- Save agent conversation history separately per puzzle
- Track constraint evolution (diff per round)
- Log decision reasoning from agents

---

## Testing Your Logs

After running first few puzzles, verify the logs are complete:

```python
import json

with open("output/sessions/MM_001_round_table.json") as f:
    session = json.load(f)

# Checklist
assert session["puzzle_metadata"]["secret_code"] is not None
assert len(session["messages"]) > 0
assert session["token_usage"]["total_input"] > 0
assert len(session["round_data"]) == session["result"]["rounds"]
assert session["result"]["success"] in [True, False]
assert session["constraints_extracted"] is not None

print("✅ All data present!")
```

---

## Next Steps

1. **Run test:** `python3 test_round_table_metrics.py`
2. **Verify logs:** Check `output/sessions/*.json` has all fields
3. **Repeat for other paradigms** with similar test scripts
4. **Collect all 180 sessions**
5. **Run analysis** to compute all 9 metrics
6. **Generate report** with results

You're ready to capture everything! 🚀
