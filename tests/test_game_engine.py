# Test Suite for Game Engine
# Validates feedback computation, guess validation, win condition detection
# Run with: python -m pytest tests/test_game_engine.py -v

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_engine import GameEngine


def test_perfect_guess():
    """Test when guess matches secret code exactly."""
    secret = ["red", "blue", "green", "yellow"]
    game = GameEngine(secret, "easy")

    result = game.submit_guess(["red", "blue", "green", "yellow"])

    assert result["valid"] == True
    assert result["solved"] == True
    assert result["feedback"]["correct_positions"] == 4
    assert result["feedback"]["correct_pegs"] == 4
    assert result["guess_number"] == 1
    print("✓ Test 1: Perfect guess")


def test_all_correct_color_wrong_position():
    """Test when all colors are correct but all in wrong positions."""
    secret = ["red", "blue", "green", "yellow"]
    game = GameEngine(secret, "easy")

    result = game.submit_guess(["yellow", "green", "blue", "red"])

    assert result["valid"] == True
    assert result["solved"] == False
    assert result["feedback"]["correct_pegs"] == 4
    assert result["feedback"]["correct_positions"] == 0
    print("✓ Test 2: All colors correct, all positions wrong")


def test_mixed_feedback():
    """Test mixed feedback: some positions correct, some colors only."""
    secret = ["red", "blue", "green", "yellow"]
    game = GameEngine(secret, "easy")

    result = game.submit_guess(["red", "red", "red", "red"])

    assert result["valid"] == True
    assert result["feedback"]["correct_pegs"] == 1  # Only red in code
    assert result["feedback"]["correct_positions"] == 1  # Position 0 matches
    print("✓ Test 3: Mixed correct pegs and positions")


def test_no_match():
    """Test when guess has no matching colors."""
    secret = ["red", "blue", "green", "yellow"]
    game = GameEngine(secret, "easy")

    result = game.submit_guess(["white", "white", "white", "white"])

    assert result["valid"] == True
    assert result["feedback"]["correct_pegs"] == 0
    assert result["feedback"]["correct_positions"] == 0
    print("✓ Test 4: No matching colors")


def test_wrong_length():
    """Test validation of guess length."""
    secret = ["red", "blue", "green", "yellow"]
    game = GameEngine(secret, "easy")

    result = game.submit_guess(["red", "blue", "green"])

    assert result["valid"] == False
    assert "Wrong number of pegs" in result["error"]
    print("✓ Test 5: Wrong guess length validation")


def test_game_over_by_rounds():
    """Test game termination after max rounds."""
    secret = ["red", "blue", "green", "yellow"]
    game = GameEngine(secret, "easy")

    for _ in range(8):
        game.submit_guess(["white", "white", "white", "white"])

    assert game.is_game_over() == True
    assert game.guess_count == 8
    print("✓ Test 6: Game over by max rounds")


def test_game_over_by_solution():
    """Test game termination when solved."""
    secret = ["red", "blue", "green", "yellow"]
    game = GameEngine(secret, "easy")

    game.submit_guess(["white", "white", "white", "white"])
    game.submit_guess(["red", "blue", "green", "yellow"])

    assert game.is_game_over() == True
    assert game.guess_count == 2
    print("✓ Test 7: Game over by solution")


def test_duplicate_colors():
    """Test feedback with duplicate colors in guess."""
    secret = ["red", "blue", "green", "yellow"]
    game = GameEngine(secret, "easy")

    # Guess has 2 reds, secret has only 1 red
    result = game.submit_guess(["red", "red", "blue", "green"])

    assert result["valid"] == True
    assert result["feedback"]["correct_pegs"] == 3  # red (1), blue, green
    assert result["feedback"]["correct_positions"] == 1  # red at 0 matches
    print("✓ Test 8: Duplicate color counting")


def test_game_state():
    """Test retrieving game state."""
    secret = ["red", "blue", "green", "yellow"]
    game = GameEngine(secret, "easy")

    game.submit_guess(["red", "blue", "green", "yellow"])
    state = game.get_state()

    assert state["guess_count"] == 1
    assert state["max_rounds"] == 8
    assert state["is_over"] == True
    assert len(state["guess_history"]) == 1
    print("✓ Test 9: Game state retrieval")


if __name__ == "__main__":
    test_perfect_guess()
    test_all_correct_color_wrong_position()
    test_mixed_feedback()
    test_no_match()
    test_wrong_length()
    test_game_over_by_rounds()
    test_game_over_by_solution()
    test_duplicate_colors()
    test_game_state()

    print("\n" + "="*50)
    print("✓ All game engine tests passed!")
    print("="*50)
