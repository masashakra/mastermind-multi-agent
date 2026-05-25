# Puzzle Generator
# Generates 30 puzzles (10 easy, 10 medium, 10 hard) with secret codes
# Secret codes never shown to agents - stored for game engine only
# Shuffled to avoid difficulty bias - same puzzles used for all 6 paradigms

import random
import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path


def generate_puzzles(n_easy: int = 10, n_medium: int = 10, n_hard: int = 10) -> List[Dict[str, Any]]:
    """Generate puzzle database with random secret codes.

    Args:
        n_easy: Number of 4-peg easy puzzles
        n_medium: Number of 5-peg medium puzzles
        n_hard: Number of 6-peg hard puzzles

    Returns:
        List of puzzle dictionaries with secret codes
    """
    puzzles = []
    puzzle_id = 1

    configs = {
        "easy": {
            "pegs": 4,
            "colors": ["red", "blue", "green", "yellow", "white", "black"],
        },
        "medium": {
            "pegs": 5,
            "colors": ["red", "blue", "green", "yellow", "white", "black", "purple", "orange"],
        },
        "hard": {
            "pegs": 6,
            "colors": ["red", "blue", "green", "yellow", "white", "black", "purple", "orange", "pink", "brown"],
        }
    }

    for difficulty, count in [("easy", n_easy), ("medium", n_medium), ("hard", n_hard)]:
        cfg = configs[difficulty]
        for _ in range(count):
            secret_code = [random.choice(cfg["colors"]) for _ in range(cfg["pegs"])]

            puzzles.append({
                "puzzle_id": f"MM_{puzzle_id:03d}",
                "difficulty": difficulty,
                "pegs": cfg["pegs"],
                "num_colors": len(cfg["colors"]),
                "available_colors": cfg["colors"],
                "secret_code": secret_code,
                "created_at": datetime.now().isoformat(),
            })
            puzzle_id += 1

    random.shuffle(puzzles)
    return puzzles


def save_puzzles(puzzles: List[Dict[str, Any]], output_path: str = "output/puzzles.json") -> None:
    """Save puzzles to JSON file.

    Args:
        puzzles: List of puzzle dictionaries
        output_path: Where to save the file
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(puzzles, f, indent=2)
    print(f"✓ Generated {len(puzzles)} puzzles and saved to {output_path}")


def load_puzzles(puzzle_path: str = "output/puzzles.json") -> List[Dict[str, Any]]:
    """Load puzzles from JSON file.

    Args:
        puzzle_path: Path to puzzles.json

    Returns:
        List of puzzle dictionaries
    """
    with open(puzzle_path) as f:
        return json.load(f)


if __name__ == "__main__":
    puzzles = generate_puzzles(n_easy=10, n_medium=10, n_hard=10)
    save_puzzles(puzzles)
