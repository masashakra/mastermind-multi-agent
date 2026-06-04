# Fix for 500-Character Response Truncation Issue

## Problem Statement

The Mastermind solver was experiencing consistent response truncation from the OpenAI o3-mini API, returning only ~500-character responses regardless of prompt complexity. This caused JSON parsing failures and prevented the solver from analyzing complex game states.

## Root Cause Analysis

The truncation was NOT caused by:
- ❌ An API-enforced response size limit
- ❌ Client-side truncation in the requests/httpx libraries
- ❌ Logging truncation (though logging DID show 500-char output, that was intentional)

**The actual root cause:** The `reasoning_effort="medium"` parameter on OpenAI's o3-mini model allocates tokens for INTERNAL REASONING chains. This significantly reduces the token budget available for the actual response output.

### Token Allocation Evidence

When calling o3-mini WITH `reasoning_effort="medium"`:
```
Response: ~500 characters (truncated)
```

When calling o3-mini WITHOUT `reasoning_effort`:
```
Response: ~1100+ characters (complete)
```

**Direct API test results:**
```
Request with 623 chars: ❌ 500-char response (with reasoning_effort)
Request with 623 chars: ✅ 1168-char response (without reasoning_effort)
```

## Solution Implemented

### Change 1: Remove `reasoning_effort` for JSON Tasks

**File:** `src/base/base_agent.py` (lines 317-323)

```python
# BEFORE:
if "o3" in self.llm["model"]:
    request_json["reasoning_effort"] = "medium"

# AFTER:
if "o3" in self.llm["model"]:
    # REMOVED: reasoning_effort was causing response starvation
    # For structured JSON output, we need full tokens for the response
    pass
```

**Rationale:**
- For structured JSON output (constraint analysis), we don't need o3's internal reasoning chains
- We need all available tokens for the actual response content
- Removing this parameter allows the full response to be returned

### Change 2: Increase Conversation History Window

**File:** `src/base/base_agent.py` (line 300)

```python
# BEFORE:
messages.extend(self.conversation[-20:])  # last 20 messages max

# AFTER:
messages.extend(self.conversation[-50:])  # last 50 messages max (~25 turns)
```

**Rationale:**
- Larger window provides better context for constraint analysis
- 50 messages ≈ 25 turns, sufficient for Mastermind puzzles (max 8 rounds, usually < 8)
- Better context = better analysis = better guess quality

### Change 3: Add Debugging for Response Length Tracking

**File:** `src/base/base_agent.py` (lines 333-336)

```python
if len(response) < 1000:
    print(f"[{self.name}] ⚠️  ACTUAL API RESPONSE: {len(response)} chars")
    if len(response) < 300:
        print(f"[{self.name}]    Content: {response}")
```

**Purpose:**
- Track actual response lengths from the API
- Identify if truncation occurs
- Verify the fix is working

## Expected Impact

### Before Fix
- MM_002: Parse failures in Rounds 6-7, puzzle unsolved (0/8 success)
- OpenAI responses: ~500 characters, JSON incomplete
- Constraint analysis: Empty or failed (reason: incomplete JSON)

### After Fix
- Full responses returned from OpenAI API (~1100+ characters)
- Complete JSON parsing without truncation
- Better constraint analysis with more context
- Improved puzzle solve rate

## Verification

### Direct API Test
✅ Tested with OpenAI API directly - removing reasoning_effort increases response from ~500 to 1168 chars

### Code Changes
✅ reasoning_effort parameter removed from o3-mini requests
✅ Conversation history window increased from 20 to 50 messages
✅ Debug output added for response length tracking

### Testing
- MM_001: Testing with reasoning_effort removed
- MM_002: Pending verification after MM_001 passes

## Alternative Workarounds (If Needed)

If the fix doesn't fully resolve issues, alternative approaches:

1. **Split Analysis into Multiple Calls**
   - Instead of one comprehensive analysis per round
   - Make targeted analyses: impossible_colors, locked_positions, etc.

2. **Simplified JSON Format**
   - Reduce response requirements to essential fields only
   - Remove reasoning_steps array and detailed explanations

3. **Stream Response**
   - Use OpenAI streaming mode for complete response capture
   - Process streamed tokens as they arrive

4. **Use Different Model**
   - GPT-4 (no reasoning_effort parameter)
   - Claude API (reliable max_tokens support)

## Files Modified

- `src/base/base_agent.py`: Lines 300, 317-323, 333-336

## Key Insight

The "500-character limit" was NOT a hard API constraint. It was a side effect of the `reasoning_effort` parameter which allocates tokens for internal reasoning, starving the response generation stage. By removing this parameter for structured output tasks, we restore full token availability for actual responses.

This aligns with the user's insight: **"there has to be another way around that 500 char limit"** - the solution was to remove the parameter that was CAUSING the limit.
