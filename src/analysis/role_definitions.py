"""
Role definitions for each agent in the Mastermind multi-agent system.
Used by LLM judge to evaluate role adherence.
"""

ROLE_DEFINITIONS = {
    "analyzer": {
        "name": "Analyzer",
        "primary_responsibility": "Extract and identify color constraints from puzzle feedback",
        "key_responsibilities": [
            "Analyze feedback scores (correct_pegs, correct_positions) to deduce which colors are in the solution",
            "Identify which colors are definitely NOT in the solution based on feedback patterns",
            "Track which colors have been tested and their outcomes",
            "Determine the complete set of available colors from feedback patterns",
            "Report constraints in structured format (included_colors, excluded_colors, color_positions)",
        ],
        "should_NOT_do": [
            "Propose specific guesses",
            "Make strategic decisions about which colors to test next",
            "Validate guesses for correctness",
            "Orchestrate the overall solving process",
            "Generate new color sequences without analysis basis",
        ],
        "expected_actions": [
            "Analyze guess feedback pairs",
            "Report identified constraints",
            "List included/excluded colors",
            "Provide reasoning about color deductions",
        ],
    },
    "strategist": {
        "name": "Strategist",
        "primary_responsibility": "Formulate and refine the solving strategy based on identified constraints",
        "key_responsibilities": [
            "Review constraints identified by Analyzer",
            "Decide which colors should be tested/prioritized next",
            "Develop approach to narrow down the solution space",
            "Plan the sequence of exploration based on constraints",
            "Consider probability and information gain of different color combinations",
        ],
        "should_NOT_do": [
            "Actually generate the guess sequences (that's Proposer's job)",
            "Analyze feedback directly (that's Analyzer's job)",
            "Validate guesses (that's Validator's job)",
            "Override agent decisions (that's Boss's job)",
        ],
        "expected_actions": [
            "Review constraint reports",
            "Decide exploration priorities",
            "Recommend colors to test",
            "Provide strategic reasoning",
            "Suggest next testing direction",
        ],
    },
    "proposer": {
        "name": "Proposer",
        "primary_responsibility": "Generate specific color guesses based on constraints and strategy",
        "key_responsibilities": [
            "Create concrete color sequences following the strategy",
            "Respect all identified constraints when generating guesses",
            "Ensure guesses have the correct number of pegs",
            "Use only available colors in the puzzle",
            "Vary guesses to test different color combinations effectively",
        ],
        "should_NOT_do": [
            "Analyze feedback (that's Analyzer's job)",
            "Make strategic decisions (that's Strategist's job)",
            "Validate guesses for correctness (that's Validator's job)",
            "Override previous constraints",
            "Ignore the number of pegs required",
        ],
        "expected_actions": [
            "Generate color sequences",
            "Validate guess format",
            "Respect constraints in proposals",
            "Provide next guess as list of colors",
        ],
    },
    "validator": {
        "name": "Validator",
        "primary_responsibility": "Validate guesses for consistency with constraints and previous feedback",
        "key_responsibilities": [
            "Check that proposed guesses respect all identified constraints",
            "Verify guesses are consistent with previous feedback",
            "Validate guess format (correct number of pegs, valid colors)",
            "Detect when a guess violates known constraints",
            "Provide feedback on guess validity",
        ],
        "should_NOT_do": [
            "Analyze puzzle feedback directly (use Analyzer's analysis)",
            "Propose guesses (that's Proposer's job)",
            "Make strategic decisions (that's Strategist's job)",
            "Ignore identified constraints",
        ],
        "expected_actions": [
            "Review proposed guesses",
            "Check constraint compliance",
            "Validate format",
            "Report validation results",
            "Flag violations",
        ],
    },
    "boss": {
        "name": "Boss",
        "primary_responsibility": "Orchestrate multi-agent collaboration and coordinate the puzzle-solving process",
        "key_responsibilities": [
            "Discover available worker agents from registry",
            "Decide which agent to contact at each step based on current state",
            "Monitor overall progress through the puzzle",
            "Handle conflicts when agents provide contradictory information",
            "Coordinate message passing between agents",
            "Make autonomous decisions using LLM reasoning when needed",
            "Manage game rounds and feedback submission",
        ],
        "should_NOT_do": [
            "Perform detailed color analysis (delegate to Analyzer)",
            "Make low-level strategic decisions (delegate to Strategist)",
            "Generate guesses directly (delegate to Proposer)",
            "Validate guesses manually (delegate to Validator)",
            "Override agent outputs without reasoning",
        ],
        "expected_actions": [
            "Discover worker URLs",
            "Make agent contact decisions",
            "Submit guesses to game",
            "Handle feedback",
            "Coordinate multi-round execution",
            "Make override decisions when needed with reasoning",
        ],
    },
}

def get_role_definition(agent_name: str) -> dict:
    """Get the role definition for an agent."""
    agent_key = agent_name.lower().strip()
    if agent_key not in ROLE_DEFINITIONS:
        raise ValueError(f"Unknown agent: {agent_name}. Available: {list(ROLE_DEFINITIONS.keys())}")
    return ROLE_DEFINITIONS[agent_key]

def get_all_roles() -> dict:
    """Get all role definitions."""
    return ROLE_DEFINITIONS.copy()
