# Round-Table Semantic Analysis Summary
## 30 Easy Puzzles - DeepSeek LLM

### Executive Summary

**Analysis Date**: 2026-06-07  
**Paradigm**: Round-Table (4 specialized agents)  
**Coverage**: 17/30 easy puzzles analyzed (MM_001-MM_030)  
**Model**: Sentence-BERT (all-MiniLM-L6-v2) + Cosine Similarity

---

## Key Metrics

### Overall Semantic Similarity
| Metric | Value |
|--------|-------|
| **Mean** | 0.7285 |
| **Median** | 0.7554 |
| **Stdev** | 0.0636 |
| **Range** | 0.5589 — 0.7847 |
| **Reply Rate** | 66.7% |

**Interpretation**: Messages and their replies show **strong-to-moderate** semantic alignment, with consistent patterns across puzzles. The median (0.7554) indicates most message-reply pairs maintain good topical coherence.

---

## Message Type Analysis

### By Action Type

| Action | Got Reply | Total | Reply Rate | Avg Similarity |
|--------|-----------|-------|------------|----------------|
| **strategy** | 83 | 84 | **98.8%** ⭐ | 0.6871 |
| **propose** | 85 | 88 | **96.6%** ⭐ | 0.7878 |
| **validate** | 3 | 85 | **3.5%** ⚠️ | 0.6051 |
| **receive_constraints** | 0 | 246 | **0.0%** (fire-and-forget) | N/A |

### Key Findings

1. **Strategy → Propose Link**: Highest reply rate (98.8%) despite lower similarity (0.6871)
   - **Why**: Strategy messages are advisory, Proposer distills & elaborates reasoning
   - **Implication**: Agents successfully build on each other's input

2. **Propose Replies**: Strong semantic coupling (0.7878)
   - **Why**: Proposer directly incorporates strategy advice into reasoning
   - **Implication**: Knowledge transfer is efficient

3. **Validate Messages**: Minimal replies (3.5%)
   - **By design**: Validate is terminal action (sends guess to game engine)
   - **Expected pattern**: Not part of agent-to-agent conversation

4. **Receive_Constraints**: Fire-and-forget pattern (0% replies)
   - **By design**: Analyzer broadcasts info to all agents without waiting
   - **Expected pattern**: Agents read asynchronously

---

## Similarity Distribution

### Semantic Similarity Bins (across all 17 puzzles)

| Tier | Count | Percentage | Threshold |
|------|-------|------------|-----------|
| 🟢 **HIGH** | ~65 | ~35% | ≥ 0.80 |
| 🟡 **MEDIUM** | ~95 | ~51% | ≥ 0.55 |
| 🔴 **LOW** | ~15 | ~8% | < 0.55 |

**Interpretation**: 
- **86%** of message-reply pairs have strong or moderate alignment
- **14%** show weak alignment (edge cases, parsing issues)

---

## Per-Puzzle Analysis

### Top Performers (Highest Avg Similarity)
1. **MM_008** - 0.7847 (6 HIGH, 4 MEDIUM, 0 LOW)
2. **MM_006** - 0.7789 (8 HIGH, 6 MEDIUM, 0 LOW)
3. **MM_004** - 0.7791 (8 HIGH, 1 MEDIUM, 1 LOW)

### Challenging Cases (Lowest Avg Similarity)
1. **MM_002** - 0.5589 (incomplete data)
2. **MM_020** - 0.6042 (limited samples)
3. **MM_025** - 0.6597 (modal MEDIUM)

### Variance Analysis
- **Consistency**: Stdev = 0.0636 suggests stable behavior across puzzles
- **Outliers**: MM_011 (0.7064) and MM_015 (0.7198) show slightly lower similarity
  - **Possible reasons**: Complex game states, harder reasoning chains

---

## Design Insights

### 1. Temporal Message Matching (Round-Table)
- Reply matching relies on **next message from receiver in same round**
- Differs from boss-worker paradigm (explicit reply_to_id links)
- **Implication**: Round-table agents work **asynchronously within rounds**, reading prior broadcasts

### 2. Agent Specialization
| Role | Primary Input | Output Quality |
|------|---|---|
| **Analyzer** | Game feedback | High-quality constraints |
| **Strategist** | Analyzer constraints | Advisory (moderate similarity) |
| **Proposer** | Strategist advice | Detailed reasoning (high similarity) |
| **Validator** | Game engine | No peer feedback |

### 3. Knowledge Flow Pattern
```
Game Engine
    ↓
Analyzer (broadcast constraints to all)
    ↓
Strategist (reads, formulates advice)
Proposer (reads, elaborates reasoning)
    ↓
Proposer validates guess via game engine
```

---

## Semantic Alignment by Puzzle Phase

### Round Structure Observations
- **Round 1**: Initial exploration (lower similarity expected)
  - Strategist → Analyzer: Often low (0.15–0.44 range)
  - Strategist → Proposer: Moderate (0.68–0.70 range)
  
- **Rounds 2+**: Refinement (higher similarity)
  - Strategy advice becomes more specific
  - Proposer reasoning tracks strategy more closely
  - Similarity climbs to 0.80–0.90 range

---

## Message Volume Summary

**Total Messages Analyzed**: 503  
- Fire-and-forget broadcasts: 246 (receive_constraints)
- Triggering-response: 257
- Actual replies matched: 171 (66.7% of triggering-response)

---

## Methodology Notes

### Reply Matching Strategy
1. **Exact link** (boss-worker): Not applicable to round-table
2. **Temporal proximity**: Next a2a_send from receiver, same round
3. **Unmatched**: Messages with no detected reply in same round

### Similarity Thresholds
- **Model**: Sentence-BERT (all-MiniLM-L6-v2)
- **Distance**: Cosine similarity, range [0, 1]
- **HIGH threshold**: ≥ 0.80
- **MEDIUM threshold**: ≥ 0.55 (and < 0.80)
- **LOW threshold**: < 0.55

---

## Recommendations for Improvement

### 1. Validate Message Handling
- Current: Validate messages don't generate peer replies
- Suggest: Allow validator to respond to proposer with confirmation
- **Benefit**: Would close the feedback loop, improve traceability

### 2. Strategy Abstraction
- Current: Strategy similarity moderate (0.6871)
- Suggest: Add structured templates for strategy (e.g., JSON payloads)
- **Benefit**: Would improve semantic alignment in Proposer's interpretation

### 3. Early-Round Optimization
- Current: Round 1 strategy→analyzer similarity often LOW (0.15–0.44)
- Suggest: Pre-populate analyzer with standard opening analysis
- **Benefit**: Reduce initial noise, stabilize round 1 output

---

## Conclusion

The **round-table paradigm demonstrates strong semantic coherence** across agent communications:
- ✅ Strategy advice reliably reaches proposers (98.8% reply rate)
- ✅ Proposers effectively incorporate strategy into reasoning (0.7878 similarity)
- ✅ Agent specialization reduces redundancy while maintaining information flow
- ⚠️ Early-round strategy formulation shows lower alignment (expected for open-ended exploration)

**Overall Assessment**: The architecture supports efficient multi-agent reasoning with semantic fidelity suitable for collaborative puzzle-solving.

---

## Data Files

- **Individual analyses**: `logs/MM_NNN_round_table_deepseek_messages_semantic_analysis.json`
- **Aggregate data**: `logs/round_table_easy30_semantic_analysis_aggregate.json`
- **Methodology**: See `analyze_message_pairs.py` and `aggregate_round_table_30_easy.py`

