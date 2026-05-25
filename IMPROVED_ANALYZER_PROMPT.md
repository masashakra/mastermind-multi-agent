# Improved Analyzer Prompt (v2)

Based on academic research: minimal rules + worked examples

---

## Key Changes:
1. ✅ Minimal rule definition (3 lines explaining feedback)
2. ✅ 4 worked examples showing constraint extraction
3. ✅ Examples show edge cases
4. ✅ Clear output format

## Prompt Code:

```python
prompt = f"""You are the Analyzer for a Mastermind puzzle solver.

FEEDBACK RULES (CRITICAL):
- correct_positions: count of colors in EXACT right position
- correct_pegs: TOTAL count of colors that exist in secret (any position)
  * This includes the correct_positions count!
  * Example: If 2 colors are in right spot AND 1 more color exists elsewhere, correct_pegs=3

WORKED EXAMPLES:

Example 1 - Finding locked positions:
Secret: ["red", "blue", "green", "yellow"]
Guess:  ["red", "blue", "green", "yellow"]
Feedback: correct_positions=4, correct_pegs=4
→ LOCKED: all positions (exactly correct)
→ IMPOSSIBLE: nothing
→ UNCERTAIN: nothing

Example 2 - Identifying misplaced colors:
Secret: ["red", "blue", "green", "yellow"]
Guess:  ["blue", "red", "green", "yellow"]
Feedback: correct_positions=2, correct_pegs=4
→ Analysis: Green (pos 2) is locked, Yellow (pos 3) is locked
→ LOCKED: [position 2 → green, position 3 → yellow]
→ MISPLACED: Red and Blue exist but wrong positions
→ IMPOSSIBLE: nothing yet

Example 3 - Eliminating colors:
Secret: ["red", "blue", "green", "yellow"]
Guess:  ["white", "black", "purple", "orange"]
Feedback: correct_positions=0, correct_pegs=0
→ All 4 colors are IMPOSSIBLE
→ Red, Blue, Green, Yellow must all be in the secret

Example 4 - Partial information (Round 2 with context):
Previous: ["red", "blue", "green", "yellow"] → pos=1, pegs=2
Current:  ["blue", "red", "white", "black"]
Feedback: correct_positions=0, correct_pegs=1
→ Only 1 color from this guess exists
→ Since Blue+Red exist from round 1, and only 1 of them scores here...
→ One must be in a position we just tested wrongly
→ White and Black are IMPOSSIBLE (no match)

YOUR TASK:
Analyze feedback from latest guess and extract constraints.

LAST GUESS: {last_guess}
FEEDBACK: {feedback['correct_pegs']} colors exist, {feedback['correct_positions']} in exact positions

PREVIOUS GUESSES:
{history_text if history_text else "None yet"}

Extract and output:
1. Locked positions (color + position confirmed correct)
2. Misplaced colors (exist but tested in wrong position)
3. Impossible colors (appeared in guess with zero feedback)
4. Constraint summaries
5. Estimate remaining possibilities

Respond ONLY with valid JSON (no markdown):
{{
  "correct_positions": [
    {{"position": 0, "color": "red"}},
    {{"position": 3, "color": "yellow"}}
  ],
  "correct_colors_wrong_position": ["blue", "green"],
  "impossible_colors": ["white", "black"],
  "constraints": [
    "Red locked at position 0",
    "Yellow locked at position 3",
    "Blue exists but not at position 1",
    "Green exists but not at position 2"
  ],
  "estimated_remaining": "~10-20 possible codes"
}}"""
```

---

## Differences from Original:

| Aspect | Original | Improved |
|--------|----------|----------|
| Rule explanation | Generic | Specific with example |
| Worked examples | 0 | 4 detailed examples |
| Edge case coverage | None | Example 3 (all eliminate) |
| Feedback explanation | In ANALYSIS RULES | In RULES section + examples |
| Example 4 | N/A | Multi-round context |

---

## Expected Improvement:
- Better constraint extraction
- Fewer misunderstandings about feedback
- Clearer logic for what's locked vs misplaced vs impossible

