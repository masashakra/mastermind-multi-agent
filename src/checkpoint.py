# Checkpoint System
# Tracks which puzzles have been completed across all paradigms
# Enables save-and-resume: if crash at puzzle 15/30, resume from 16 instead of restarting
# Saves checkpoint after each puzzle completes all 6 paradigms

import json
from pathlib import Path
from typing import Set, Dict, Any


CHECKPOINT_FILE = Path("output/checkpoint.json")


def load_checkpoint() -> Dict[str, Any]:
    """Load checkpoint state with completed puzzles.

    Returns:
        Dictionary with "completed" (set of puzzle IDs) and metadata
    """
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
            return data
    return {"completed": [], "last_updated": None, "total_completed": 0}


def save_checkpoint(puzzle_id: str, metrics: Dict[str, Any] = None) -> None:
    """Save checkpoint after puzzle completes.

    Args:
        puzzle_id: Puzzle that was completed
        metrics: Optional metrics dictionary to store
    """
    checkpoint = load_checkpoint()

    if puzzle_id not in checkpoint["completed"]:
        checkpoint["completed"].append(puzzle_id)
        checkpoint["total_completed"] = len(checkpoint["completed"])
        checkpoint["last_updated"] = Path(CHECKPOINT_FILE).stat().st_mtime if CHECKPOINT_FILE.exists() else None

    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2)


def is_completed(puzzle_id: str) -> bool:
    """Check if puzzle has been completed.

    Args:
        puzzle_id: Puzzle to check

    Returns:
        True if puzzle was completed, False otherwise
    """
    checkpoint = load_checkpoint()
    return puzzle_id in checkpoint.get("completed", [])


def get_completion_status() -> Dict[str, Any]:
    """Get overall completion status.

    Returns:
        Dictionary with completion stats
    """
    checkpoint = load_checkpoint()
    return {
        "total_completed": checkpoint.get("total_completed", 0),
        "completed_puzzles": checkpoint.get("completed", []),
        "last_updated": checkpoint.get("last_updated", None)
    }


def reset_checkpoint() -> None:
    """Reset checkpoint (use with caution!)."""
    CHECKPOINT_FILE.unlink(missing_ok=True)
    print("✓ Checkpoint reset")
