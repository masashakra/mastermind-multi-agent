# Boss-Worker Metrics Agent
# Full A2A agent for tracking metrics
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import List, Dict, Any, Optional, Union
import json
from datetime import datetime
from base.base_agent import BaseAgent
from base.agent_card import METRICS_CARD
from communication.protocol import A2ACommunicationLayer
from base.role import AgentRole, ParadigmType

AGENT_CARD = {
    **METRICS_CARD,
    "agent_id": "metrics_moderator_mediated",
    "paradigm": "moderator_mediated",
}

class MetricsAgent(BaseAgent):
    """Boss-Worker Metrics Agent

    Tracks and aggregates metrics via A2A protocol.
    Other agents call this agent to record metrics.
    """

    def __init__(self, paradigm_name: str = "moderator_mediated"):
        # Metrics doesn't need LLM
        self.name = "Metrics_BossWorker"
        self.agent_id = "metrics_moderator_mediated"
        self.paradigm = paradigm_name
        self.metrics: Dict[str, List[Union[int, float, str]]] = {}
        self.comm_layer = None
        self.role = AgentRole.VALIDATOR if not hasattr(AgentRole, 'METRICS') else None  # Fallback

    def record_metric(self, metric_name: str, value: Union[int, float, str],
                     tags: Optional[Dict[str, str]] = None) -> Dict[str, bool]:
        """Record a metric value

        Args:
            metric_name: Name of metric (e.g., "guesses_used", "rounds")
            value: Numeric or string value
            tags: Optional tags for categorization

        Returns:
            {"recorded": True}
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []

        self.metrics[metric_name].append(value)
        return {"recorded": True}

    def get_metrics(self, filter_name: Optional[str] = None) -> Dict[str, Any]:
        """Get aggregated metrics

        Args:
            filter_name: Optional filter for specific metric

        Returns:
            Aggregated metrics dictionary
        """
        if filter_name:
            values = self.metrics.get(filter_name, [])
            return {
                filter_name: {
                    "count": len(values),
                    "values": values,
                    "average": sum(v for v in values if isinstance(v, (int, float))) / len([v for v in values if isinstance(v, (int, float))]) if any(isinstance(v, (int, float)) for v in values) else None
                }
            }

        # Return all metrics
        result = {}
        for metric_name, values in self.metrics.items():
            numeric_values = [v for v in values if isinstance(v, (int, float))]
            result[metric_name] = {
                "count": len(values),
                "values": values,
                "average": sum(numeric_values) / len(numeric_values) if numeric_values else None
            }

        return result

    def save_metrics(self) -> bool:
        """Save metrics to file

        Returns:
            True if saved successfully
        """
        metrics_file = f"src/paradigms/{self.paradigm}/logs/metrics.json"
        try:
            import os
            os.makedirs(os.path.dirname(metrics_file), exist_ok=True)
            with open(metrics_file, 'w') as f:
                json.dump(self.get_metrics(), f, indent=2)
            return True
        except:
            return False
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process method for abstract base class compliance."""
        metric_name = state.get("metric_name", "")
        metric_value = state.get("metric_value", 0)
        return self.record_metric(metric_name, metric_value, state.get("tags"))
