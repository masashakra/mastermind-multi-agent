# Role Adherence Analysis

## Overview

The Role Adherence Analysis system evaluates whether each agent in the multi-agent Mastermind puzzle-solving system stays true to its defined role and responsibilities. It uses an LLM judge (Claude) to assess whether each message is role-specific.

## Key Components

### 1. Role Definitions (`role_definitions.py`)

Defines the scope of responsibility for each agent:

- **Analyzer**: Extracts color constraints from feedback
- **Strategist**: Formulates solving strategy
- **Proposer**: Generates specific guesses
- **Validator**: Validates guesses against constraints
- **Boss**: Orchestrates multi-agent collaboration

Each role includes:
- Primary responsibility
- Key responsibilities (what they should do)
- Prohibited actions (what they should NOT do)
- Expected actions

### 2. Role Adherence Judge (`role_adherence_judge.py`)

Uses Claude to evaluate whether individual messages are role-specific.

**Main class**: `RoleAdherenceJudge`

```python
from analysis import RoleAdherenceJudge

judge = RoleAdherenceJudge()

# Evaluate a single message
result = judge.evaluate_message(
    agent_name="analyzer",
    message_content="Based on the feedback, red and blue are in the solution..."
)

# Returns:
# {
#     "is_role_specific": True/False,
#     "confidence": 0.0-1.0,
#     "reasoning": "explanation",
#     "violations": [list of violated "should_NOT_do" items]
# }
```

### 3. Message Log Parser (`message_log_parser.py`)

Extracts A2A messages from puzzle run logs.

**Main class**: `MessageLogParser`

```python
from analysis import MessageLogParser

parser = MessageLogParser("puzzle_run.log")
messages = parser.parse()

# Get messages by agent
messages_by_agent = parser.get_messages_by_agent()
# Returns: {"analyzer": [...], "strategist": [...], ...}

# Get specific agent's messages
analyzer_messages = parser.get_agent_messages("analyzer")

# Get messages for specific action
analyze_messages = parser.get_messages_for_action("analyze")
```

### 4. Main Analyzer (`analyze_role_adherence.py`)

Ties everything together to perform comprehensive role adherence analysis.

**Main class**: `RoleAdherenceAnalyzer`

```python
from analysis import RoleAdherenceAnalyzer

analyzer = RoleAdherenceAnalyzer("puzzle_run.log")
results = analyzer.analyze_and_save("role_adherence_report.json")
```

## Usage

### Quick Test with Sample Messages

```bash
python test_role_adherence.py
```

This will:
1. Print all agent role definitions
2. Test the judge with sample messages for each agent
3. Suggest how to analyze actual puzzle run logs

### Analyze a Puzzle Run Log

```bash
python test_role_adherence.py path/to/puzzle_run.log
```

This will:
1. Parse the log file for A2A messages
2. Evaluate role adherence for each message
3. Generate a detailed report
4. Save results to `role_adherence_report.json`

### Programmatic Usage

```python
from analysis import RoleAdherenceAnalyzer

# Analyze a puzzle run
analyzer = RoleAdherenceAnalyzer("puzzle_run.log")
results = analyzer.analyze_and_save("report.json")

# Access detailed results
evaluation = results["evaluation_results"]
print(f"Overall adherence: {evaluation['overall_adherence_pct']:.1f}%")

for agent_name, agent_results in evaluation["results_by_agent"].items():
    print(f"{agent_name}: {agent_results['role_adherence_pct']:.1f}%")
```

## Evaluation Metrics

### Role Adherence (%)

The proportion of an agent's messages that align with its defined role.

- **100%**: All messages are role-specific
- **80-100%**: Excellent role adherence
- **60-80%**: Good role adherence, some off-role messages
- **<60%**: Poor role adherence, many violations

### Confidence Score

The LLM judge's confidence in its evaluation (0.0-1.0):
- **0.8-1.0**: High confidence in evaluation
- **0.5-0.8**: Moderate confidence
- **<0.5**: Low confidence, ambiguous cases

### Violations

Specific "should_NOT_do" items from the role definition that the agent violated in a message.

## Example Output

```
======================================================================
ROLE ADHERENCE EVALUATION REPORT
======================================================================

📊 Overall Role Adherence: 87.3%
📈 Total Messages Evaluated: 156

----------------------------------------------------------------------
Agent: ANALYZER
----------------------------------------------------------------------
  Role Adherence: 92.1%
  Messages: 35/38
  Confidence: 0.91

  ⚠️  Messages with violations: 3
    Message 12: ['Override previous constraints without re-analysis']
    Message 24: ['Propose specific guesses']
    Message 38: ['Make strategic decisions']

----------------------------------------------------------------------
Agent: STRATEGIST
----------------------------------------------------------------------
  Role Adherence: 85.7%
  Messages: 30/35
  Confidence: 0.88
...
```

## Data Collection for Analysis

This tool helps with the comprehensive data collection plan by providing:

1. **Role Adherence Metrics**: Understanding how well agents stay in their roles
2. **Message Traceability**: Complete audit trail of all agent interactions
3. **Violation Detection**: Identifying when agents exceed their scope
4. **Confidence Assessment**: Quantifying analysis certainty

Use alongside other metrics like:
- Agent Communication Patterns
- Constraint Consistency
- Solution Quality
- Performance Efficiency
- Error Recovery

## Integration with Data Collection Plan

This analysis module is part of a larger data collection strategy. Before running full test suites, use this to:

1. **Validate agent design**: Do agents stay within their roles?
2. **Identify edge cases**: When do agents struggle to stay role-specific?
3. **Refine role definitions**: Are the role boundaries clear enough?
4. **Establish baselines**: What's the expected role adherence for each agent?

Then use these insights to improve agent behavior before full-scale testing.
