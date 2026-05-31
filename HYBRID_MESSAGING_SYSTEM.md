# Hybrid Bidirectional/Unidirectional Messaging System

## 🎯 Overview

Implemented a **hybrid peer-to-peer messaging system** where agents can:
- **Fire-and-forget** (unidirectional) - send message and continue
- **Ask and wait** (bidirectional) - ask question and wait for reply

Agents **maintain persistent memory** of all sent/received messages and use that context in decision-making.

---

## ✨ Key Features

### 1. **Unidirectional Messaging** (Default)
```python
# Send message, don't wait for reply
await agent.send_a2a_message(
    receiver_type="strategist",
    action="strategy",
    payload=result,
    is_question=False  # Fire-and-forget
)
```

**Use case:** Normal peer-to-peer flow (Analyzer → Strategist → Proposer → Validator)

### 2. **Bidirectional Messaging** (Optional)
```python
# Ask a question and WAIT for reply
reply = await agent.send_a2a_message(
    receiver_type="validator",
    action="check_validity",
    payload={"guess": [...], "question": "Is this valid?"},
    is_question=True  # Wait for reply
)
```

**Use case:** When agent needs clarification before continuing

### 3. **Agent Memory System**

Each agent maintains:

```python
class AgentMemory:
    inbox: List[Dict]      # Messages received
    sent: List[Dict]       # Messages sent  
    deductions: Dict       # Learned facts/constraints
```

**Example memory state:**
```python
{
    "inbox": [
        {"from": "analyzer", "action": "analyze", "payload": {...}, "is_reply": False},
        {"from": "validator", "action": "check_validity", "payload": {"is_valid": True}, "is_reply": True}
    ],
    "sent": [
        {"to": "strategist", "action": "strategy", "payload": {...}, "is_question": False},
        {"to": "validator", "action": "check_validity", "payload": {...}, "is_question": True}
    ],
    "deductions": {
        "red_locked": True,
        "white_impossible": False
    }
}
```

### 4. **Memory-Aware Routing**

Agents use memory context when deciding where to send next:

```python
# Routing prompt includes recent messages
RECENT MESSAGES:
- YOU sent to strategist: strategy
- YOU received from analyzer: analyze

CRITICAL RULES:
✓ Send forward in normal flow
✗ DO NOT send back to who you just received from (avoid loops!)
✗ DO NOT send to yourself
```

---

## 📊 Implementation Details

### A2AMessage Extensions

Added two fields to A2AMessage:

```python
@dataclass
class A2AMessage:
    # ... existing fields ...
    is_question: bool = False    # If True, sender expects direct reply
    is_reply: bool = False       # If True, this is a direct reply (not forwarded)
```

### BaseAgent.send_a2a_message() Signature

```python
async def send_a2a_message(
    self,
    receiver_type: str,
    action: str,
    payload: Dict[str, Any],
    is_question: bool = False,  # NEW: wait for reply if True
    retries: int = 2,
) -> Dict[str, Any]
```

### Agent Handler Pattern

Each agent endpoint checks if incoming message is a question:

```python
@app.post("/analyze")
async def handle_analyze(request: Request):
    msg = A2AMessage.from_dict(await request.json())
    
    # Log received message
    agent.memory.receive_message(...)
    
    # If question, answer directly without forwarding
    if msg.is_question:
        result = agent.analyze_feedback(...)
        return A2AMessage.response(..., is_reply=True).to_dict()
    
    # Otherwise, process and forward
    result = agent.analyze_feedback(...)
    # Send to next peer (fire-and-forget)
    await agent.send_a2a_message(...)
```

---

## 🔄 Message Flow Example

### Round 1: Unidirectional Flow (Normal)

```
Orchestrator → Analyzer (is_question=False, fire-and-forget)
    │
    ├─→ Analyzer processes
    ├─→ Analyzer.memory.receive_message("orchestrator", ...)
    ├─→ LLM decides: "Send to strategist"
    ├─→ Analyzer.memory.send_message("strategist", ...)
    └─→ Analyzer → Strategist (is_question=False, fire-and-forget)
        │
        ├─→ Strategist processes
        ├─→ Strategist.memory.receive_message("analyzer", ...)
        ├─→ LLM decides: "Send to proposer"
        ├─→ Strategist.memory.send_message("proposer", ...)
        └─→ Strategist → Proposer (is_question=False, fire-and-forget)
            │
            └─→ [continues to Validator → Orchestrator]
```

### Round 2: Bidirectional Flow (If Needed)

```
Proposer: "Should I try RRBB?" (is_question=True)
    ↓ WAITS for reply
Validator: "Yes, valid ✓" (is_reply=True)
    ↑ Sends back
Proposer.memory.receive_message("validator", ..., is_reply=True)
Proposer: [continues with confidence]
```

---

## 🧠 Memory Context in Routing Decision

**Before:** Agents made routing decisions with no context
```
"Which peer should I send to?"
→ No memory of who I just received from
→ Could loop back to previous peer
```

**After:** Agents have full context
```
RECENT MESSAGES:
- YOU sent to strategist: strategy
- YOU received from analyzer: analyze

CRITICAL RULES:
✓ Send forward (analyzer→strategist→proposer→validator)
✗ Don't loop back to analyzer
✓ Send to strategist is NOT good because they just sent to you
```

---

## 🧪 Test Results

**Puzzle:** MM_001  
**Secret:** ['red', 'blue', 'green', 'yellow']

### Perfect Execution:

```
Analyzer → Strategist → Proposer → Validator → Orchestrator
                                      ✓ VALID GUESS
                                      
Guess: ['red', 'blue', 'green', 'yellow']
Feedback: 4 pegs, 4 positions ✓ SOLVED!

Success: True
Guesses: 1
Rounds: 1
Time: 35.2s
Errors: 0
```

---

## 💡 Use Cases

### Unidirectional (Fire-and-Forget)
- Normal message flow through peer chain
- One-way information passing
- No need to wait for response

### Bidirectional (Ask & Wait)
- Clarifying questions ("Is this valid?")
- Checking duplicates ("Has RRGG been tried?")
- Asking for recommendations ("What colors should I try?")
- Consensus-building ("Do you agree with this analysis?")

---

## 🎓 Architecture Benefits

✅ **Flexible Communication** - Switch between fire-and-forget and ask-and-wait  
✅ **Memory Awareness** - Agents learn from conversation history  
✅ **Loop Prevention** - Memory context prevents agents from sending back to sender  
✅ **Efficient** - Fire-and-forget is default, no unnecessary blocking  
✅ **Intelligent** - Agents can ask clarifying questions when unsure  
✅ **Auditable** - Full message history for debugging/analysis  

---

## 📝 Code Changes Summary

### Files Modified:

1. **src/communication/a2a_message.py**
   - Added `is_question: bool` field
   - Added `is_reply: bool` field
   - Updated `request()` and `response()` class methods

2. **src/base/base_agent.py**
   - Created `AgentMemory` class
   - Initialize `self.memory` in `__init__`
   - Updated `send_a2a_message()` to support `is_question` parameter
   - Added memory logging in send/receive operations
   - Enhanced routing prompt with memory context

3. **src/paradigms/round_table/agents/agent_server.py**
   - Updated all 4 agent handlers (analyzer, strategist, proposer, validator)
   - Added message logging to memory
   - Check `msg.is_question` and reply directly if true
   - Pass memory context to decision-making

---

## 🚀 Future Enhancements

Possible extensions (architecture supports them):

1. **Multiple agents asking same question**
   - Analyzer asks Validator for confirmation
   - Proposer also asks Validator about duplicates
   - Validator replies to both

2. **Consensus voting**
   - Proposer proposes multiple guesses
   - Validator checks all
   - Analyzer determines which is best

3. **Agent voting on decisions**
   - Proposer asks Strategist: "Should I try RRBB or RRWW?"
   - Strategist replies with recommendation
   - Proposer follows guidance

4. **Learning across rounds**
   - Memory persists across rounds
   - "I learned red is locked" - reuse in round 2
   - "RRGG failed before" - avoid in round 2

---

## ✅ Conclusion

Implemented a **production-ready hybrid messaging system** that enables:

- True peer-to-peer agent coordination
- Flexible unidirectional and bidirectional communication  
- Persistent agent memory for context-aware decision making
- Loop prevention through routing intelligence
- Foundation for advanced multi-agent collaboration patterns

**The system is ready for extended testing on harder puzzles where learning and bidirectional messaging will provide significant advantages.**
