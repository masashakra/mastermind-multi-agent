# Round-Table Semantic Analysis Report

## Overview
This analysis examines message-reply semantic similarity across all round-table paradigm runs with DeepSeek LLM on the game (30 easy puzzles).

## Methodology

### Data Collection
- **Paradigm**: Round-Table (multi-agent collaborative puzzle-solving)
- **Agent roles**: Analyzer, Strategist, Proposer, Validator
- **Message types**:
  - `receive_constraints`: Fire-and-forget broadcasts (no reply expected)
  - `strategy`: Strategist advises on approach
  - `propose`: Proposer suggests guesses
  - `validate`: Proposer submits final guess (no direct replies observed)

### Semantic Matching Strategy
1. **Priority 1**: Exact match via reply_to_id (used in Boss-Worker, not applicable here)
2. **Priority 2**: Temporal matching - next a2a_send from receiver in same round

### Similarity Metrics
- **Model**: Sentence-BERT (all-MiniLM-L6-v2) embedding + cosine similarity
- **Thresholds**:
  - 🟢 **HIGH** (≥0.80): Strong semantic alignment
  - 🟡 **MEDIUM** (≥0.55): Partial alignment
  - 🔴 **LOW** (<0.55): Weak alignment
  - 🔵 **FIRE_AND_FORGET**: No reply expected
  - ⚫ **NO_REPLY_FOUND**: Expected reply but not detected

## Expected Patterns

### Key Observations
1. **Fire-and-forget messages** should be ~50% of all messages (receive_constraints)
2. **Reply rate** for triggering-response messages typically 60-70%
3. **Strategy→Propose similarity** often HIGH (shared puzzle context)
4. **Analyze→Strategy similarity** often MEDIUM/HIGH (builds on analysis)
5. **Validate messages** don't get replies (terminal action)

### Design Insight
The round-table paradigm's reply patterns differ from boss-worker:
- Messages are **broadcast-like** (not point-to-point like boss-worker)
- Reply matching relies on **temporal proximity** within rounds
- Some replies may be **implicit** (agent reads prior broadcast)

## Output Files
- Individual analyses: `logs/MM_NNN_round_table_deepseek_messages_semantic_analysis.json`
- Aggregate report: `logs/round_table_semantic_analysis_aggregate.json`
- Summary statistics: Printed to console

## Next Steps
1. Complete all individual semantic analyses
2. Generate aggregate statistics
3. Compare with boss-worker results for paradigm insights
