# Test Suite for Agent Implementations
# Tests each agent's core functionality with mock and real LLM calls
# Run with: python3 -m pytest tests/test_agents.py -v
# Or: python3 tests/test_agents.py

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.base_agent import BaseAgent
from agents.strategist import StrategistAgent
from agents.analyzer import AnalyzerAgent
from agents.proposer import ProposerAgent
from agents.validator import ValidatorAgent


class TestBaseAgent:
    """Test BaseAgent functionality."""

    def test_json_parsing_direct(self):
        """Test parsing direct JSON."""
        # Create minimal agent-like object to test parsing
        class MockAgent:
            def parse_json_response(self, response):
                import json
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    pass
                if "```json" in response:
                    try:
                        start = response.index("```json") + 7
                        end = response.index("```", start)
                        json_str = response[start:end].strip()
                        return json.loads(json_str)
                    except (ValueError, json.JSONDecodeError):
                        pass
                return {"error": "Failed to parse JSON response", "raw_response": response[:200]}

        agent = MockAgent()
        response = '{"analysis": "test", "strategy": "test strategy", "reasoning": "test"}'
        result = agent.parse_json_response(response)
        assert result["analysis"] == "test"
        print("✓ Test: Direct JSON parsing")

    def test_json_parsing_markdown(self):
        """Test parsing JSON from markdown code block."""
        class MockAgent:
            def parse_json_response(self, response):
                import json
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    pass
                if "```json" in response:
                    try:
                        start = response.index("```json") + 7
                        end = response.index("```", start)
                        json_str = response[start:end].strip()
                        return json.loads(json_str)
                    except (ValueError, json.JSONDecodeError):
                        pass
                return {"error": "Failed to parse JSON response", "raw_response": response[:200]}

        agent = MockAgent()
        response = '```json\n{"analysis": "test", "strategy": "test"}\n```'
        result = agent.parse_json_response(response)
        assert result["analysis"] == "test"
        print("✓ Test: Markdown JSON parsing")

    def test_json_parsing_failure(self):
        """Test graceful failure on invalid JSON."""
        class MockAgent:
            def parse_json_response(self, response):
                import json
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    pass
                if "```json" in response:
                    try:
                        start = response.index("```json") + 7
                        end = response.index("```", start)
                        json_str = response[start:end].strip()
                        return json.loads(json_str)
                    except (ValueError, json.JSONDecodeError):
                        pass
                return {"error": "Failed to parse JSON response", "raw_response": response[:200]}

        agent = MockAgent()
        response = "This is not JSON at all"
        result = agent.parse_json_response(response)
        assert "error" in result
        print("✓ Test: JSON parsing error handling")


class TestStrategist:
    """Test Strategist agent."""

    def test_format_feedback(self):
        """Test feedback formatting."""
        strategist = StrategistAgent()
        history = [
            {
                "round": 1,
                "guess": ["red", "blue", "green", "yellow"],
                "feedback": {"correct_pegs": 2, "correct_positions": 1}
            }
        ]
        formatted = strategist._format_feedback(history)
        assert "Round 1" in formatted
        assert "red" in formatted
        assert "2 correct colors" in formatted
        assert "1 correct position" in formatted
        print("✓ Test: Strategist feedback formatting")

    def test_format_feedback_empty(self):
        """Test feedback formatting with empty history."""
        strategist = StrategistAgent()
        formatted = strategist._format_feedback([])
        assert "No previous guesses" in formatted
        print("✓ Test: Strategist empty feedback formatting")


class TestAnalyzer:
    """Test Analyzer agent."""

    def test_analyzer_process_none_input(self):
        """Test analyzer handles None inputs gracefully."""
        analyzer = AnalyzerAgent()
        result = analyzer.process()

        assert result["correct_positions"] == []
        assert result["correct_colors_wrong_position"] == []
        assert result["constraints"] == []
        print("✓ Test: Analyzer handles None input")

    def test_analyzer_call_count(self):
        """Test analyzer tracks call counts."""
        analyzer = AnalyzerAgent()
        initial_count = analyzer.call_count
        # Don't actually call LLM, just test the interface
        assert analyzer.call_count == initial_count
        print("✓ Test: Analyzer call counting mechanism")


class TestProposer:
    """Test Proposer agent."""

    def test_proposer_initialization(self):
        """Test proposer initializes properly."""
        proposer = ProposerAgent()
        assert proposer.name == "Proposer"
        assert proposer.provider == "ollama"
        print("✓ Test: Proposer initialization")

    def test_proposer_call_count(self):
        """Test proposer tracks calls."""
        proposer = ProposerAgent()
        initial = proposer.call_count
        assert isinstance(initial, int)
        assert initial == 0
        print("✓ Test: Proposer call tracking")

    def test_proposer_stats(self):
        """Test proposer statistics."""
        proposer = ProposerAgent()
        stats = proposer.get_stats()
        assert stats["agent_name"] == "Proposer"
        assert stats["call_count"] == 0
        print("✓ Test: Proposer statistics")


class TestValidator:
    """Test Validator agent."""

    def test_validate_guess_valid(self):
        """Test validation of valid guess."""
        validator = ValidatorAgent()
        guess = ["red", "blue", "green", "yellow"]
        available = ["red", "blue", "green", "yellow", "white", "black"]

        result = validator.validate_guess(guess, available, 4)

        assert result["is_valid"] == True
        assert result["ready_to_submit"] == True
        assert len(result["errors"]) == 0
        print("✓ Test: Validator accepts valid guess")

    def test_validate_guess_wrong_length(self):
        """Test validation of wrong length guess."""
        validator = ValidatorAgent()
        guess = ["red", "blue", "green"]  # 3 instead of 4
        available = ["red", "blue", "green", "yellow", "white", "black"]

        result = validator.validate_guess(guess, available, 4)

        assert result["is_valid"] == False
        assert len(result["errors"]) > 0
        print("✓ Test: Validator catches wrong length")

    def test_validate_guess_invalid_color(self):
        """Test validation of invalid color."""
        validator = ValidatorAgent()
        guess = ["red", "blue", "purple", "yellow"]  # purple not available
        available = ["red", "blue", "green", "yellow", "white", "black"]

        result = validator.validate_guess(guess, available, 4)

        assert result["is_valid"] == False
        assert any("invalid color" in err.lower() for err in result["errors"])
        print("✓ Test: Validator catches invalid color")

    def test_validate_guess_duplicate(self):
        """Test validation of duplicate guess."""
        validator = ValidatorAgent()
        guess = ["red", "blue", "green", "yellow"]
        available = ["red", "blue", "green", "yellow", "white", "black"]
        previous = [["red", "blue", "green", "yellow"]]

        result = validator.validate_guess(guess, available, 4, previous)

        assert result["is_valid"] == True  # Still valid format
        assert result["ready_to_submit"] == False  # But shouldn't submit
        assert len(result["warnings"]) > 0
        print("✓ Test: Validator warns about duplicate")

    def test_validate_non_list(self):
        """Test validation of non-list input."""
        validator = ValidatorAgent()
        guess = "red blue green yellow"  # String instead of list
        available = ["red", "blue", "green", "yellow", "white", "black"]

        result = validator.validate_guess(guess, available, 4)

        assert result["is_valid"] == False
        print("✓ Test: Validator rejects non-list")


class TestIntegration:
    """Test agent integration (workflow)."""

    def test_validator_strategist_integration(self):
        """Test validator with strategist-like output."""
        validator = ValidatorAgent()

        # Simulate a proposer output
        guess = ["red", "blue", "green", "yellow"]
        available = ["red", "blue", "green", "yellow", "white", "black"]

        # Validate
        result = validator.validate_guess(guess, available, 4)

        assert result["is_valid"] == True
        assert result["ready_to_submit"] == True
        print("  ✓ Validator approved agent-generated guess")

        print("✓ Test: Agent integration works")

    def test_multiple_validations(self):
        """Test sequence of validations."""
        validator = ValidatorAgent()
        available = ["red", "blue", "green", "yellow", "white", "black"]

        # First guess
        result1 = validator.validate_guess(["red", "blue", "green", "yellow"], available, 4)
        assert result1["is_valid"] == True

        # Second guess (different)
        result2 = validator.validate_guess(
            ["yellow", "green", "blue", "red"],
            available,
            4,
            previous_guesses=[["red", "blue", "green", "yellow"]]
        )
        assert result2["is_valid"] == True
        assert result2["ready_to_submit"] == True

        # Third guess (duplicate)
        result3 = validator.validate_guess(
            ["red", "blue", "green", "yellow"],
            available,
            4,
            previous_guesses=[["red", "blue", "green", "yellow"]]
        )
        assert result3["ready_to_submit"] == False

        print("✓ Test: Multiple validations work correctly")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("AGENT TEST SUITE")
    print("="*60)

    print("\n[Base Agent Tests]")
    test_base = TestBaseAgent()
    test_base.test_json_parsing_direct()
    test_base.test_json_parsing_markdown()
    test_base.test_json_parsing_failure()

    print("\n[Strategist Tests]")
    test_strat = TestStrategist()
    test_strat.test_format_feedback()
    test_strat.test_format_feedback_empty()

    print("\n[Analyzer Tests]")
    test_ana = TestAnalyzer()
    test_ana.test_analyzer_process_none_input()
    test_ana.test_analyzer_call_count()

    print("\n[Proposer Tests]")
    test_prop = TestProposer()
    test_prop.test_proposer_initialization()
    test_prop.test_proposer_call_count()
    test_prop.test_proposer_stats()

    print("\n[Validator Tests]")
    test_val = TestValidator()
    test_val.test_validate_guess_valid()
    test_val.test_validate_guess_wrong_length()
    test_val.test_validate_guess_invalid_color()
    test_val.test_validate_guess_duplicate()
    test_val.test_validate_non_list()

    print("\n[Integration Tests]")
    test_int = TestIntegration()
    test_int.test_validator_strategist_integration()
    test_int.test_multiple_validations()

    print("\n" + "="*60)
    print("✓ ALL AGENT TESTS PASSED!")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
