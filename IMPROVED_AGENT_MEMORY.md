# Judge-Mediated: Improved Memory Pattern (Boss-Worker Style)

## Problem with Current Approach

Current format is too concise:
```
R6: [y,b,g,b] → 4p+3pos
```

Agent has to **infer** the constraints, which DeepSeek R1 fails to do.

---

## Solution: Extract & Pass Explicit Constraints

### New Analysis_History Format

Instead of just storing results, **extract constraints during analysis**:

```python
analysis_history = [
    {
        "round": 6,
        "guess": ["yellow", "blue", "green", "black"],
        "analysis_structured": {
            "colors_in": ["yellow", "blue", "green", "black"],  # ← EXPLICIT!
            "colors_out": ["red", "white"],                      # ← EXPLICIT!
            "locked_positions": {
                0: "yellow",  # Position 0 definitely yellow
                2: "green",   # Position 2 definitely green
            },
            "unlocked_positions": [1, 3],
            "misplaced_colors": [
                {"color": "blue", "tried_in": [1, 2, 3], "locked_position": 1}
            ]
        },
        "full_analysis": "All 4 colors identified! Blue is in position 1, Green in position 2...",
        "result": {
            "correct_pegs": 4,
            "correct_positions": 3
        }
    }
]
```

### Where to Extract This

**In TeamAgent.solve_round():**

```python
# Step 1: Extract constraints (with guidance)
prompt_step1 = f"""
Extract STRUCTURED constraints from feedback history:

{guess_history_text}

For each guess, identify:
1. COLORS IN CODE: Which colors got correct_pegs?
2. COLORS OUT: Which colors never appeared in correct_pegs?
3. LOCKED POSITIONS: Which colors/positions are confirmed?
4. MISPLACED COLORS: Which colors are in code but wrong position?

Respond with JSON:
{{
  "colors_in": ["color1", "color2", ...],
  "colors_out": ["color1", ...],
  "locked_positions": {{"0": "color", "1": "color", ...}},
  "misplaced_colors": [{{"color": "blue", "wrong_positions": [0, 2]}}]
}}
"""

constraints = parse_json(self.call_llm(prompt_step1))

# Store this for next round
return {
    "guess": guess,
    "analysis_structured": constraints,  # ← NEW: Structured data!
    "full_analysis": analysis_text
}
```

---

## Updated Orchestrator Flow

### Current (Weak Memory)
```python
# Round N: Agent gets generic summary
agent.solve_round(
    analysis_history=[
        {"round": N-1, "guess": [...], "result": "..."}
    ]
)
```

### Improved (Boss-Worker Style)
```python
# Round N: Agent gets STRUCTURED constraints from previous rounds
agent.solve_round(
    analysis_history=[
        {
            "round": N-1,
            "constraints": {
                "colors_in": ["red", "blue"],
                "colors_out": ["green", "yellow"],
                "locked_positions": {"0": "red"},
            }
        }
    ],
    last_feedback={...}
)
```

---

## Updated TeamAgent Prompt

### Current (Weak)
```
IMPORTANT: Learn from your own thinking in previous rounds!
- Review what you thought in earlier rounds
```

### Improved (Boss-Worker Style)
```
CONSTRAINTS FROM PREVIOUS ROUNDS (Use these facts!):
  Round 5: Colors IN: [red, blue] | OUT: [green, white] | Locked: position 0 = red
  Round 6: Colors IN: [red, blue, yellow, black] | OUT: [green, white] | Locked: 0=yellow, 2=green

REQUIRED: Build on these confirmed facts!
  - DO place: red, blue, yellow, black (confirmed IN)
  - DO NOT place: green, white (confirmed OUT)
  - LOCK position 0 to: yellow
  - LOCK position 2 to: green
  - TEST position permutations for remaining slots

STRATEGY: You know [y, ?, g, b] with 3 positions locked.
Test these permutations:
  [y, b, g, ?] - is b in position 1?
  [y, ?, g, b] - is ? in position 1?
```

---

## Implementation: 3 Files to Change

### 1. TeamAgent (`team_agent.py`) - Extract Constraints

```python
def solve_round(self, guess_history, analysis_history=None, ...):
    """Step 1: Extract constraints from history"""
    
    # Build constraint extraction prompt
    if analysis_history:
        prompt_constraints = f"""
        Extract explicit constraints from this feedback history:
        
        {self._format_analysis_history(analysis_history)}
        
        Respond with ONLY JSON (no other text):
        {{
            "colors_in": ["color1", "color2"],
            "colors_out": ["color3"],
            "locked_positions": {{"0": "color1", "2": "color2"}},
            "misplaced": [{{"color": "blue", "wrong_at": [1, 3]}}]
        }}
        """
        
        constraints_json = self.call_llm(prompt_constraints)
        constraints = json.loads(constraints_json)
    else:
        constraints = {}
    
    """Step 2: Build next guess using constraints"""
    
    prompt_guess = f"""
    {constraint_text_from_structured_data(constraints)}
    
    Based on these constraints, propose next guess...
    """
    
    guess = self._parse_guess(self.call_llm(prompt_guess))
    
    return {
        "guess": guess,
        "analysis_structured": constraints,
        "analysis_text": "..."
    }
```

### 2. Orchestrator (`orchestrator.py`) - Store Structured Data

```python
# After getting agent results
for team_id in range(1, NUM_TEAMS + 1):
    team_result = team_results[team_id - 1]
    
    # Store full structured analysis (like boss-worker!)
    self.team_analysis_histories[team_id].append({
        "round": round_num,
        "guess": team_result.get("guess", []),
        "analysis_structured": team_result.get("analysis_structured", {}),  # ← NEW!
        "analysis_text": team_result.get("analysis", ""),
        "feedback": team_feedback,
    })
```

### 3. Agent Server (`agent_server.py`) - No Change Needed

Already passes analysis_history parameter ✓

---

## Comparison: Before vs After

### BEFORE (Current - DeepSeek struggles)
```
Round 6 sees:
  R5: [r,b,g,w] → 2p+1pos
  
Agent thinks: "Hmm, got 2 pegs. Maybe try different colors?"
Agent guesses: [y,y,y,y] ← Random!
```

### AFTER (Improved - Like boss-worker)
```
Round 6 sees:
  R5 CONSTRAINTS: 
    - colors_in: [red, blue]
    - colors_out: [green, white]
    - locked_positions: {0: red}
  
Agent thinks: "I KNOW red and blue are in! Red is at position 0!
             I need 2 more colors. Let me test [red, ?, ?, ?]"
Agent guesses: [red, yellow, black, purple] ← Logical!
```

---

## Why This Works (Like Boss-Worker)

**Boss-Worker Pipeline:**
```
Analyzer → (explicit constraints) → Strategist → (explicit strategy) → Proposer
```

**Judge-Mediated with Improved Memory:**
```
Round N Agent (extracts constraints) → (explicit constraints) → Round N+1 Agent
```

Same pattern! **Explicit structured data** instead of summaries.

---

## Expected Results

With this pattern:
1. ✅ Agent can clearly see what's confirmed IN/OUT
2. ✅ Agent can see locked positions explicitly
3. ✅ Agent builds logically on constraints
4. ✅ Even DeepSeek R1 will follow explicit rules better
5. ✅ No more random single-color guesses

---

## Implementation Priority

**Easy (do this first):**
1. Extract constraints to structured format in TeamAgent
2. Store in orchestrator
3. Update prompt to reference structured data

**Better (do next):**
1. Add constraint validation (eliminate impossible guesses)
2. Track constraint evolution across rounds
3. Log constraint confidence (how sure are we?)

**Advanced (optional):**
1. Use constraint satisfaction solver alongside LLM
2. Auto-generate permutations to test
3. Track strategy effectiveness across rounds

