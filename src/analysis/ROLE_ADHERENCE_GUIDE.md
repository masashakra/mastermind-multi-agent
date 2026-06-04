# Role Adherence Analysis - Complete Guide

## Overview

The Role Adherence Analysis system evaluates whether multi-agent puzzle-solving interactions stay true to defined roles. It uses an LLM judge to determine if each agent's messages are appropriate for their assigned responsibilities.

## What is Role Adherence?

**Role Adherence (%)** = Proportion of an agent's messages that align with its defined role and responsibilities.

**Example:**
- Analyzer has 10 messages
- 8 messages properly analyze feedback and identify constraints
- 2 messages incorrectly propose guesses (outside their role)
- Role Adherence = 8/10 = 80%

## System Architecture

### 1. Role Definitions (`role_definitions.py`)

Each agent has a detailed role card:

```python
{
    "name": "Analyzer",
    "primary_responsibility": "Extract color constraints from feedback",
    "key_responsibilities": [
        "Analyze feedback scores",
        "Identify excluded colors",
        "Track tested colors",
        # ... etc
    ],
    "should_NOT_do": [
        "Propose specific guesses",
        "Make strategic decisions",
        # ... etc
    ]
}
```

### 2. Judge System

#### Mock Judge (Heuristic-Based)
- **Default mode** - Works without API keys
- Uses keyword matching to evaluate role-specificity
- Fast, deterministic, good for development
- Location: `mock_judge.py`

#### LLM Judge (Claude-Based)
- Uses Claude to deeply evaluate role adherence
- Set `use_mock=False` in RoleAdherenceJudge
- Requires Anthropic or DeepSeek API key
- More accurate but slower

### 3. Message Log Parser (`message_log_parser.py`)

Extracts messages from puzzle run logs:

```python
parser = MessageLogParser("puzzle_run.log")
messages = parser.parse()

# Get messages by agent
messages_by_agent = parser.get_messages_by_agent()
# Returns: {"analyzer": [msg1, msg2, ...], "boss": [...], ...}
```

Supports multiple log formats:
- JSON puzzle_run_log format (default)
- A2A message format
- Text-based logs

### 4. Main Analyzer (`analyze_role_adherence.py`)

Orchestrates the complete analysis workflow:

```python
analyzer = RoleAdherenceAnalyzer("puzzle_run.log")
results = analyzer.analyze_and_save("report.json")
```

## Usage

### Quick Start

#### 1. Test with Sample Messages
```bash
python test_role_adherence.py
```

Output:
- Agent role definitions
- Sample test messages evaluated for each agent
- Suggestions for analyzing actual logs

#### 2. Analyze a Puzzle Run Log
```bash
python test_role_adherence.py puzzle_run.log
```

Output:
- Parses 51+ messages from the log
- Evaluates each agent's role adherence
- Generates role_adherence_report.json
- Displays violations by agent and message

#### 3. Programmatic Usage
```python
from analysis import RoleAdherenceAnalyzer, RoleAdherenceJudge, get_all_roles

# View role definitions
roles = get_all_roles()
for agent_name, role_def in roles.items():
    print(f"{agent_name}: {role_def['primary_responsibility']}")

# Analyze a log
analyzer = RoleAdherenceAnalyzer("puzzle_run.log")
results = analyzer.analyze_and_save()

# Access results
evaluation = results["evaluation_results"]
print(f"Overall adherence: {evaluation['overall_adherence_pct']:.1f}%")

for agent_name, agent_results in evaluation["results_by_agent"].items():
    adherence = agent_results['role_adherence_pct']
    messages = agent_results['total_messages']
    print(f"{agent_name}: {adherence:.1f}% ({messages} messages)")
```

## Output Format

### Console Report
```
======================================================================
ROLE ADHERENCE EVALUATION REPORT
======================================================================

📊 Overall Role Adherence: 3.9%
📈 Total Messages Evaluated: 51

----------------------------------------------------------------------
Agent: ANALYZER
----------------------------------------------------------------------
  Role Adherence: 0.0%
  Messages: 0/5
  Confidence: 0.49

  ⚠️  Messages with violations: 5
    Message 1: ["Contains 'guess' (prohibited for analyzer)"]
    ...
```

### JSON Report (`role_adherence_report.json`)

```json
{
  "evaluation_results": {
    "results_by_agent": {
      "analyzer": {
        "agent": "analyzer",
        "total_messages": 5,
        "role_specific_count": 0,
        "role_adherence_pct": 0.0,
        "avg_confidence": 0.49,
        "evaluations": [...]
      },
      ...
    },
    "overall_adherence_pct": 3.9,
    "total_messages": 51
  },
  "analysis_summary": "...",
  "detailed_messages": {...}
}
```

## Interpretation Guide

### Role Adherence Ranges

| Score | Interpretation | Action |
|-------|-----------------|--------|
| 90-100% | Excellent | Agent stays in role well |
| 70-90% | Good | Minor off-role messages |
| 50-70% | Fair | Some role violations |
| 30-50% | Poor | Frequent off-role behavior |
| 0-30% | Very Poor | Agent regularly exceeds scope |

### Violation Types

**Analyzer violations:**
- Mentioning specific guesses (should delegate to Proposer)
- Making strategy decisions (should delegate to Strategist)
- Validating guesses (should delegate to Validator)

**Strategist violations:**
- Directly analyzing feedback (should delegate to Analyzer)
- Generating concrete guesses (should delegate to Proposer)
- Validating guesses (should delegate to Validator)

**Proposer violations:**
- Analyzing constraints (should use Analyzer's analysis)
- Making strategy decisions (should use Strategist's guidance)
- Validating for correctness (should delegate to Validator)

**Validator violations:**
- Proposing new guesses (should delegate to Proposer)
- Analyzing original feedback (should delegate to Analyzer)
- Making strategy changes (should inform Strategist)

**Boss violations:**
- Performing detailed analysis (should delegate)
- Generating guesses directly (should delegate)
- Validating guesses manually (should delegate)

## Customization

### Modify Role Definitions

Edit `role_definitions.py`:

```python
ROLE_DEFINITIONS["analyzer"]["key_responsibilities"] = [
    # Add new responsibilities
    "Your custom responsibility",
]

ROLE_DEFINITIONS["analyzer"]["should_NOT_do"] = [
    # Add new prohibitions
    "Your custom prohibition",
]
```

### Custom Judge Patterns

Edit `mock_judge.py` role_patterns:

```python
self.role_patterns = {
    "analyzer": {
        "should_contain": [
            "feedback",
            "constraint",
            # Add custom keywords
        ],
        "should_not_contain": [
            "guess",
            # Add custom prohibited keywords
        ],
    },
}
```

### Switch to LLM Judge

```python
judge = RoleAdherenceJudge(use_mock=False)  # Uses Claude/DeepSeek

# Or with specific configuration
judge = RoleAdherenceJudge(
    model="claude-opus-4-1-20250805",
    use_mock=False
)
```

## Data Collection Integration

Use role adherence metrics as part of comprehensive analysis:

1. **Role Adherence (%)**
   - Does each agent stay in its role?
   - Are responsibilities properly separated?

2. **Consistency Metrics**
   - Do constraints remain consistent across rounds?
   - Are contradictions resolved?

3. **Communication Patterns**
   - Who communicates with whom?
   - What's the message frequency by type?

4. **Quality Metrics**
   - How quickly is the puzzle solved?
   - How many violations before success?

5. **Agent Performance**
   - Accuracy of analysis
   - Quality of strategy
   - Correctness of guesses
   - Validation effectiveness

## Common Scenarios

### Scenario 1: Analyzer is Making Strategic Decisions

**Problem:** Role Adherence = 40%

**Investigation:**
- Check for phrases like "we should test", "let's try next"
- These indicate strategy-making (Strategist's job)

**Fix:**
- Update Analyzer's prompt to only report constraints
- Remove decision-making language from Analyzer outputs

### Scenario 2: Boss is Performing Detailed Analysis

**Problem:** Boss messages contain constraint analysis details

**Investigation:**
- Look for constraint identification in Boss messages
- Should only see delegation and orchestration

**Fix:**
- Have Boss only query agents, never analyze directly
- Ensure Boss requests come with agent-provided data

### Scenario 3: Role Adherence Improving Over Time

**Tracking:**
```python
# Run analysis on logs from different time periods
for puzzle in puzzles:
    analyzer = RoleAdherenceAnalyzer(puzzle.log_file)
    results = analyzer.analyze_and_save()
    adherence = results["evaluation_results"]["overall_adherence_pct"]
    print(f"Puzzle {puzzle.id}: {adherence:.1f}%")
```

## Troubleshooting

### No messages parsed
- Check log file format
- Ensure log is in JSON format with conversation entries
- Verify agent_name fields exist

### All violations detected
- Mock judge heuristics might be too strict
- Review role_patterns for false positives
- Consider switching to LLM judge for better accuracy

### API errors
- Mock judge will automatically fallback from API failures
- Check DEEPSEEK_API_KEY or ANTHROPIC_API_KEY environment variable
- Ensure API credentials are valid

## Files

```
src/analysis/
├── role_definitions.py          # Agent role cards
├── role_adherence_judge.py      # Judge class (uses mock or LLM)
├── mock_judge.py                # Heuristic-based evaluator
├── message_log_parser.py        # Extracts messages from logs
├── analyze_role_adherence.py    # Main orchestrator
├── __init__.py                  # Module exports
└── README.md                    # Quick reference

test_role_adherence.py            # Standalone test script
role_adherence_report.json        # Generated report (output)
```

## Next Steps

1. **Run baseline analysis** on current puzzle runs
2. **Identify main violation patterns** by agent
3. **Update agent prompts** to improve role adherence
4. **Re-run analysis** to measure improvement
5. **Integrate metrics** into comprehensive test reporting
6. **Monitor trends** across multiple puzzle runs

## Questions?

For detailed role requirements, check:
- `src/analysis/role_definitions.py` - Role definitions
- `src/analysis/README.md` - Module overview
- Agent implementations in `src/paradigms/boss_worker/agents/`
