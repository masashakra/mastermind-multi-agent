# 🆓 Using Groq (Free!) Instead of OpenAI

**Cost:** $0-5 for full 30×6 test (vs $30-40 with OpenAI)  
**Setup time:** 5 minutes  
**Speed:** ⚡ Faster than OpenAI

---

## Why Groq?

| Feature | Groq | OpenAI | Ollama |
|---------|------|--------|--------|
| Cost | $0-5 | $30-40 | $0 |
| Speed | ⚡ 1-2 sec/puzzle | 🔹 3-5 sec/puzzle | ⏱️ 30+ sec/puzzle |
| Free tier | 9K tokens/day | No | Unlimited |
| Setup | 2 min | 5 min | 15+ min |
| Already in code | ✅ Yes | ✅ Yes | ✅ Yes |
| Token cost | ~$0.001/1K | ~$0.016/1K | N/A |

---

## Setup (5 minutes)

### Step 1: Sign Up
1. Go to **groq.com**
2. Click "Get Started" or "Sign Up"
3. Create free account (email + password)
4. Verify email
5. Accept terms

### Step 2: Get API Key
1. Log in to groq.com
2. Go to **API Keys** section
3. Click **Create API Key**
4. Copy the key
5. Save to `.env` file in your project:

```bash
# In /Users/masashakra/Desktop/game/.env
GROQ_API_KEY=your_key_here
```

### Step 3: Verify It Works
```bash
cd /Users/masashakra/Desktop/game

python3 << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if api_key:
    print(f"✅ API key loaded: {api_key[:10]}...")
else:
    print("❌ API key not found")
EOF
```

---

## Run Tests with Groq

### Test 1: Single Puzzle (Free)
```bash
python3 << 'EOF'
import sys
sys.path.insert(0, "src")
from test_round_table_metrics import solve_puzzle_with_metrics

# Test 1 puzzle with Groq
metrics = solve_puzzle_with_metrics(
    "MM_001",
    paradigm="round_table",
    provider="groq"  # <-- Use Groq!
)
metrics.save()
print("✅ Test complete! Check output/sessions/")
EOF
```

**Cost:** Free (within daily limit)  
**Time:** ~1 minute

### Test 2: All 30 Puzzles (1 paradigm)
```bash
python3 << 'EOF'
import sys
sys.path.insert(0, "src")
from test_round_table_metrics import solve_puzzle_with_metrics
from puzzle_generator import load_puzzles

paradigm = "round_table"
puzzles = load_puzzles()

print(f"Running {len(puzzles)} puzzles with {paradigm}...")
for puzzle in puzzles:
    metrics = solve_puzzle_with_metrics(
        puzzle["puzzle_id"],
        paradigm=paradigm,
        provider="groq"
    )
    metrics.save()
    print(f"✅ {puzzle['puzzle_id']}")

print(f"\n✅ All {len(puzzles)} puzzles completed!")
EOF
```

**Cost:** Free (uses ~278K tokens, within free tier)  
**Time:** ~30 minutes

### Test 3: Full 30×6 (180 puzzles)

**Option A: Completely Free (But Slow)**
- Run 9K tokens per day
- Spread over ~183 days
- Cost: $0

**Option B: Minimal Cost (~$5)**
1. Add small paid credits to Groq account (~$5)
2. Run all 180 puzzles back-to-back
3. Cost: ~$3-5 total
4. Time: ~3-4 hours

For Option B:
```bash
# Set up a loop to run all paradigms
for paradigm in round_table boss_worker judge_mediated paradigm_4 paradigm_5 paradigm_6; do
    python3 << 'EOF'
import sys
sys.path.insert(0, "src")
from test_round_table_metrics import solve_puzzle_with_metrics
from puzzle_generator import load_puzzles

paradigm = "$paradigm"
puzzles = load_puzzles()

for puzzle in puzzles:
    metrics = solve_puzzle_with_metrics(
        puzzle["puzzle_id"],
        paradigm=paradigm,
        provider="groq"
    )
    metrics.save()
    print(f"✅ {puzzle['puzzle_id']}_{paradigm}")
EOF
done
```

---

## Cost Comparison

### Scenario A: Run 1 Paradigm (30 puzzles)
```
Groq:     Free (9K tokens/day)
OpenAI:   ~$4.80
DeepSeek: ~$0.50
Ollama:   Free (slow: ~15 hours)
```

### Scenario B: Run Full 180 Puzzles
```
Groq:     $0 (spread over time) or $3-5 (this week)
OpenAI:   $24-30
DeepSeek: $2-3
Ollama:   Free (slow: ~90 hours)
```

---

## Groq Free Tier Details

**Daily limit:** 9,000 tokens per day  
**Monthly:** Up to 270,000 tokens (9K × 30 days)

**How to maximize:**
- Run puzzles right after midnight UTC
- Use multiple API keys (create multiple accounts)
- Spread tests over several days

**If you need more:**
- Add $5-10 credit
- Use "pay as you go" pricing
- Total cost for 180 puzzles: ~$3-5

---

## Alternative: Ollama (Completely Free)

If you want **zero cost** with no time limit:

```bash
# Install Ollama
brew install ollama

# Run Ollama server
ollama serve

# In another terminal, download a model
ollama pull mistral  # or llama2, neural-chat, etc

# Run tests
python3 << 'EOF'
import sys
sys.path.insert(0, "src")
from test_round_table_metrics import solve_puzzle_with_metrics

metrics = solve_puzzle_with_metrics(
    "MM_001",
    paradigm="round_table",
    provider="ollama"
)
EOF
```

**Cost:** $0  
**Speed:** Slower (30-60 sec per puzzle vs 1-2 sec with Groq)  
**Depends on:** Your computer's GPU

---

## Recommendation

**Best option: Groq with $5 credit**

Pros:
- ✅ Fast (1-2 sec per puzzle)
- ✅ Cheap (~$3-5 for everything)
- ✅ Quick setup (5 min)
- ✅ Can run all 180 this week
- ✅ Already in your code

How:
1. Sign up at groq.com (free)
2. Get API key
3. Add $5 credit (optional, for speed)
4. Run tests with `provider="groq"`
5. Get results in a few hours

---

## Files to Modify

### Update `.env`:
```bash
# .env
GROQ_API_KEY=your_groq_key_here
OPENAI_API_KEY=  # Optional, leave empty
```

### Update test scripts:
Change:
```python
provider="openai"
```

To:
```python
provider="groq"
```

---

## Verify Token Usage

After running, check actual costs:

```bash
python3 << 'EOF'
import json, glob

total_input = 0
total_output = 0
for f in glob.glob("output/sessions/*.json"):
    with open(f) as file:
        session = json.load(file)
        usage = session.get("token_usage", {})
        total_input += usage.get("total_input", 0)
        total_output += usage.get("total_output", 0)

total = total_input + total_output
groq_cost = (total / 1000) * 0.005  # Groq avg ~$0.005/1K

print(f"Total tokens used: {total:,}")
print(f"Groq cost: ${groq_cost:.2f}")
print(f"OpenAI cost: ${(total/1000) * 0.016:.2f}")
print(f"Savings with Groq: ${(total/1000) * 0.011:.2f}")
EOF
```

---

## TL;DR

1. Go to **groq.com** → Sign up (free, 2 min)
2. Get API key
3. Change `provider="openai"` → `provider="groq"`
4. Run tests
5. Cost: **$0-5** (vs $30-40 with OpenAI)
6. Speed: **Faster** (⚡ 1-2 sec vs 🔹 3-5 sec)

You're ready to go! 🚀
