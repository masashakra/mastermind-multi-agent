# Improved Strategist Prompt (v2)

Based on academic research: minimal rules + worked examples for strategic planning

---

## Key Changes:
1. ✅ Minimal strategy definition (clear objectives)
2. ✅ 5 worked examples covering different puzzle states
3. ✅ Examples show what to do at each phase
4. ✅ Clear output format with actionable strategy

## Prompt Code:

```python
prompt = f"""You are the Strategist for a Mastermind puzzle solver.

STRATEGY PHASES:
1. EXPLORATION (Round 1): Test diverse colors to see what exists
2. CONSTRAINT BUILDING (Rounds 2-3): Test colors in different positions to find locked positions
3. REFINEMENT (Rounds 4+): Test remaining unknowns, close the gaps
4. CONFIRMATION (Final rounds): Fill in final details before high-confidence guess

WORKED EXAMPLES:

Example 1 - First round (EXPLORATION):
History: None yet
Task: "What's our first guess?"
→ Strategy: "Test 4 diverse common colors to see which ones exist in the code"
→ Why: First feedback tells us which colors are even relevant
→ Confidence: 0.5 (very uncertain, just gathering data)

Example 2 - One locked position found (CONSTRAINT BUILDING):
History:
- Round 1: [red, blue, green, yellow] → 2 colors, 0 positions
- Round 2: [white, blue, green, yellow] → 2 colors, 1 position
Analysis: Added white, now 1 position is locked (probably white at 0 or green at 2)
→ Strategy: "Test the 2 colors in different positions to find which is locked, try new color at unlocked position"
→ Why: We know at least 2 colors exist, 1 is locked; need to identify WHICH position
→ Confidence: 0.6 (narrowing down)

Example 3 - Multiple colors found, positions unknown (REFINEMENT):
History:
- Round 1: [red, blue, green, yellow] → 1 color, 0 positions
- Round 2: [white, blue, green, yellow] → 2 colors, 1 position
- Round 3: [white, yellow, green, yellow] → 2 colors, 1 position
Analysis: White and green are definitely in code. White likely locked at 0. Need to find position of green and 2 other colors.
→ Strategy: "Assume white locked at position 0. Test green and 2 new colors at positions 1-3"
→ Recommended guess: [white, black, purple, green] (white locked, trying new colors black+purple, testing green at position 3)
→ Why: We have 2 confirmed, need 2 more. This tests specific positions efficiently
→ Confidence: 0.7 (good constraints, need to fill gaps)

Example 4 - Found 3 colors, confirming positions (CONFIRMATION):
History: Last 3 rounds confirm:
- LOCKED: white at position 0
- MISPLACED: green (exists but not at 2)
- IMPOSSIBLE: red, blue, yellow
- Found colors: white, green, and one more (maybe black?)
→ Strategy: "Test black and orange at positions 1,2,3 to find the last color and green's position"
→ Recommended guess: [white, black, green, orange]
→ Why: This tests:
  * Position 1: is it black or something else?
  * Position 2: is green locked here or is it position 3?
  * Position 3: is it orange or another untested color?
→ Confidence: 0.8 (we know the major constraints, closing final details)

Example 5 - All 4 colors identified, final positioning (CONFIRMATION):
History: Confirmed:
- LOCKED: white at 0, black at 1
- FOUND: green and purple exist but positions unknown
→ Strategy: "We have all 4 colors. Just determine if green is at 2 or 3."
→ Recommended guess: [white, black, green, purple] or [white, black, purple, green]
→ Why: We know all colors exist. Just arranging them correctly.
→ Confidence: 0.95 (almost certain, final arrangement)

TASK:

Puzzle difficulty: {difficulty}
Pegs needed: 4
Colors available: 6 typical (red, blue, green, yellow, white, black)

FEEDBACK HISTORY:
{feedback_text}

Based on the history:
1. What phase are we in? (EXPLORATION, CONSTRAINT BUILDING, REFINEMENT, CONFIRMATION)
2. What have we learned so far?
3. What should we test next? (be specific about positions and colors)
4. Why will this strategy help us narrow the possibilities?

Output ONLY with valid JSON (no markdown):
{{
  "phase": "REFINEMENT",
  "analysis": "We know white and green exist. White likely locked at position 0. Need to find where green is and identify 2 more colors.",
  "strategy": "Test green and 2 new colors at positions 1-3. Assume white at 0.",
  "recommended_positions": {{
    "position_0": "white (locked, keep)",
    "position_1": "test new color (e.g., black)",
    "position_2": "test green (moved from position 2)",
    "position_3": "test another new color (e.g., purple)"
  }},
  "reasoning": "We have 2 confirmed colors (white, green). Need 2 more. This guess tests specific positions efficiently.",
  "confidence": 0.75
}}"""
```

---

## Differences from Original:

| Aspect | Original | Improved |
|--------|----------|----------|
| Strategy definition | Generic (5 questions) | Specific phases (EXPLORATION → CONFIRMATION) |
| Worked examples | 0 | 5 detailed examples covering all phases |
| Example coverage | N/A | Round 1, 1 locked, multiple colors, 3 colors, all 4 colors |
| Actionability | Vague ("continue with diverse colors") | Specific ("test black and orange at positions 1,2,3") |
| Confidence tracking | No | Yes (0.5 to 0.95 as certainty grows) |
| Position recommendations | No | Yes (recommended_positions dict) |

---

## Expected Improvement:
- Strategist gives **specific** guidance instead of vague recommendations
- Proposer knows **exactly which positions to test** and with which colors
- System doesn't get stuck retesting same colors
- Better handling of "find remaining colors" phase

---

## Note:
This prevents the problem from the test where the system got stuck after finding 2 colors and couldn't figure out how to find the remaining 2. Now the Strategist will explicitly say:
- "You have 2 colors, need 2 more"
- "Test position 1 with black, position 2 with purple, position 3 with orange"
- This gives the Proposer concrete guidance to follow
