# Boss-Worker Logger Agent
# Full A2A agent for logging all inter-agent communication
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from base.base_agent import BaseAgent
from base.agent_card import LOGGER_CARD
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType

AGENT_CARD = {
    **LOGGER_CARD,
    "agent_id": "logger_direct_adversarial",
    "paradigm": "direct_adversarial",
}

class LoggerAgent(BaseAgent):
    """Boss-Worker Logger Agent

    Logs all inter-agent communication via A2A protocol.
    Other agents call this agent to record messages.
    """

    def __init__(self, paradigm_name: str = "direct_adversarial"):
        # Logger doesn't need LLM
        self.name = "Logger_BossWorker"
        self.agent_id = "logger_direct_adversarial"
        self.paradigm = paradigm_name
        self.logs: List[Dict[str, Any]] = []
        self.comm_layer = None
        self.role = AgentRole.LOGGER if hasattr(AgentRole, 'LOGGER') else None

    def log_message(self, message_data: Dict[str, Any]) -> Dict[str, bool]:
        """Log a message or event

        Args:
            message_data: Message to log with timestamp, sender, etc.

        Returns:
            {"logged": True, "message_id": str}
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message_id": f"msg_{len(self.logs)}",
            **message_data
        }
        self.logs.append(log_entry)

        # Also write to file
        log_file = f"src/paradigms/{self.paradigm}/logs/communication_logs/{log_entry['message_id']}.json"
        try:
            # Create directory if needed
            import os
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'w') as f:
                json.dump(log_entry, f, indent=2)
        except:
            pass  # Silently fail if can't write

        return {"logged": True, "message_id": log_entry["message_id"]}

    def get_logs(self, filter_type: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """Retrieve logs with optional filtering

        Args:
            filter_type: Optional filter (e.g., "strategy", "analysis")
            limit: Max logs to return

        Returns:
            {"logs": [...]}
        """
        logs = self.logs
        if filter_type:
            logs = [l for l in logs if l.get("message_type") == filter_type]

        return {"logs": logs[-limit:]}
