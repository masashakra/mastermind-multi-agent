# Boss-Worker BaseAgent (inherits from src/base/)
# Can override methods for Boss-Worker specific behavior if needed

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from base.base_agent import BaseAgent as BaseAgentCore

# For Boss-Worker, we can use the core BaseAgent as-is
# But we keep this file for paradigm-specific customizations if needed
class BaseAgent(BaseAgentCore):
    """Boss-Worker specific BaseAgent

    Inherits from core BaseAgent with potential Boss-Worker overrides.
    """
    pass
