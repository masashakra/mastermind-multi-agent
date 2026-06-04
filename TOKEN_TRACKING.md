# Token Counting Implementation

## Summary

Added real token usage tracking to all LLM API calls. The system now captures actual input/output tokens from OpenAI, DeepSeek, and Groq APIs.

## Changes Made

### 1. **`src/base/base_agent.py`** — Token tracking in API calls

**Three providers updated:**

#### OpenAI (line ~345)
```python
if resp.status_code == 200:
    resp_json = resp.json()
    response = resp_json["choices"][0]["message"]["content"]

    # TRACK TOKEN USAGE
    if "usage" in resp_json:
        input_tokens = resp_json["usage"].get("prompt_tokens", 0)
        output_tokens = resp_json["usage"].get("completion_tokens", 0)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        print(f"[{self.name}] Tokens: input={input_tokens}, output={output_tokens}, cumulative_input={self.total_input_tokens}, cumulative_output={self.total_output_tokens}")
    break
```

#### DeepSeek (line ~400)
Same pattern for DeepSeek API responses.

#### Groq (line ~440)
Same pattern for Groq API responses.

### 2. **BaseAgent** — Initialize and retrieve token counts

**Line 150-151:** Token counters initialized to 0
```python
self.total_input_tokens = 0
self.total_output_tokens = 0
```

**Line 1165-1177:** New method to retrieve token usage
```python
def get_token_usage(self) -> Dict[str, int]:
    """Get cumulative token usage for this agent.
    
    Returns:
        Dictionary with input_tokens, output_tokens, and total
    """
    return {
        "input_tokens": self.total_input_tokens,
        "output_tokens": self.total_output_tokens,
        "total_tokens": self.total_input_tokens + self.total_output_tokens,
        "api_calls": self.call_count
    }
```

### 3. **`test_round_table_metrics.py`** — Capture tokens in metrics

Added token tracking to the test script:

```python
# Track token usage per round (delta from previous)
token_usage = analyzer.get_token_usage()
round_input = token_usage["input_tokens"] - prev_input_tokens
round_output = token_usage["output_tokens"] - prev_output_tokens

# Record the delta for this round
metrics.record_tokens(round_num, round_input, round_output)
print(f"Tokens (this round): {round_input} input, {round_output} output (cumulative: {token_usage['total_tokens']})")

prev_input_tokens = token_usage["input_tokens"]
prev_output_tokens = token_usage["output_tokens"]
```

## How It Works

### Per-Round Tracking

1. **Before round:** Record `prev_input_tokens` and `prev_output_tokens`
2. **After LLM call:** Agent's `total_input_tokens` and `total_output_tokens` are updated by API response
3. **Calculate delta:** `round_tokens = current_total - prev_total`
4. **Record in metrics:** `metrics.record_tokens(round_num, round_input, round_output)`

### Data Flow

```
OpenAI API Response
    ↓
resp.json()["usage"]["prompt_tokens"] → input_tokens
resp.json()["usage"]["completion_tokens"] → output_tokens
    ↓
agent.total_input_tokens += input_tokens
agent.total_output_tokens += output_tokens
    ↓
agent.get_token_usage()
    ↓
test calculates delta
    ↓
metrics.record_tokens(round, delta_input, delta_output)
    ↓
Session JSON includes per_round token data
    ↓
MetricsAggregator computes:
  - total_tokens
  - tokens_per_guess
  - avg token cost across paradigm
```

## Output

### Console Output (During Test)

```
Round 1:
  [AnalyzerAgent] Tokens: input=1800, output=500, cumulative_input=1800, cumulative_output=500
  ✅ Response: 1200 chars
  Tokens (this round): 1800 input, 500 output (cumulative: 2300)
```

### Session JSON

```json
{
  "token_usage": {
    "total_input": 8234,
    "total_output": 2156,
    "per_round": [
      {"round": 1, "input": 1800, "output": 500, "total": 2300},
      {"round": 2, "input": 1600, "output": 450, "total": 2050},
      {"round": 3, "input": 1700, "output": 480, "total": 2180}
    ]
  }
}
```

### Summary Output

```
======================================================================
ROUND-TABLE SUMMARY
======================================================================

...
Avg token cost: 9,234 (input: 7,100, output: 2,134)
Tokens per guess: 1,775
...
```

## How to Use in Tests

### Run with metrics collection:
```bash
cd /Users/masashakra/Desktop/game
python3 test_round_table_metrics.py
```

This will:
1. Solve 6 puzzles with round-table paradigm
2. Track tokens for each puzzle
3. Collect aggregate metrics
4. Generate summary with token costs
5. Save to `output/metrics/round_table_summary.json`

### Check token usage programmatically:

```python
from paradigms.round_table.agents.analyzer import AnalyzerAgent

analyzer = AnalyzerAgent()
# ... make some calls ...
usage = analyzer.get_token_usage()
print(f"Total tokens used: {usage['total_tokens']}")
print(f"API calls made: {usage['api_calls']}")
```

## What Gets Measured

| Metric | Source | Use |
|--------|--------|-----|
| `input_tokens` | API response `prompt_tokens` | Measure context length |
| `output_tokens` | API response `completion_tokens` | Measure response length |
| `total_tokens` | input + output | Total API cost |
| `tokens_per_guess` | total_tokens / avg_guesses | Efficiency metric |

## Supported Providers

✅ **OpenAI** (gpt-4-turbo, gpt-4-o)
✅ **DeepSeek** (deep-seek-r1)
✅ **Groq** (mixtral-8x7b, llama-3)
✅ **Ollama** (no token tracking - N/A)

## Important Notes

1. **Cumulative tracking:** Agent tracks cumulative totals across all calls
2. **Per-round delta:** Test calculates the delta to get per-round tokens
3. **No double-counting:** Metrics add per-round deltas, not cumulative values
4. **Real tokens:** These are actual tokens from API, not estimates
5. **Printed each call:** Each API call prints token usage for debugging

## Next Steps

After running the test, you'll have:
- Token counts per puzzle per round
- Aggregate token cost per paradigm
- Efficiency ratio (tokens/guess) for comparison
- Complete data for paper results section

Run the test to see real token numbers!
