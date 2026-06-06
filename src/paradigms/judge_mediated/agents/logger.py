# Logger Agent for Judge-Mediated Paradigm
# Captures and logs all agent communications for debugging and analysis

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class LoggerAgent:
    """Logger Agent for Judge-Mediated Paradigm

    Captures all agent communications and messages for debugging and analysis.
    Stores messages in JSON format with timestamps.
    """

    def __init__(self, paradigm_name: str):
        """Initialize the logger agent.

        Args:
            paradigm_name: Name of the paradigm (e.g., "judge_mediated")
        """
        self.paradigm_name = paradigm_name
        self.logs: List[Dict[str, Any]] = []
        self.start_time = datetime.now()

    def log_message(self, message: Dict[str, Any]) -> None:
        """Log a message with timestamp.

        Args:
            message: Dictionary containing message details
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": (datetime.now() - self.start_time).total_seconds(),
            **message
        }
        self.logs.append(log_entry)

    def save_logs(self, filepath: Optional[str] = None) -> None:
        """Save logs to a JSON file.

        Args:
            filepath: Path to save logs to. If None, uses default paradigm directory.
        """
        if filepath is None:
            # Default: save to paradigm's logs directory
            logs_dir = Path(__file__).parent.parent / "logs" / "communication_logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            filepath = logs_dir / f"{self.paradigm_name}_messages.json"
        else:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(self.logs, f, indent=2)

    def get_logs(self) -> List[Dict[str, Any]]:
        """Get all logs.

        Returns:
            List of log entries
        """
        return self.logs

    def clear_logs(self) -> None:
        """Clear all logs."""
        self.logs = []

    def __len__(self) -> int:
        """Return the number of logged messages."""
        return len(self.logs)
