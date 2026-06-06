# Coopetition Centralized BaseAgent

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent as BaseAgentCore


class BaseAgent(BaseAgentCore):
    """Coopetition Centralized specific BaseAgent.

    Inherits from core BaseAgent with potential coopetition-specific overrides.
    """
    pass
