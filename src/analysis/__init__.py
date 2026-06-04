"""
Analysis module for multi-agent puzzle solving evaluation.

Provides tools for:
- Role adherence analysis (evaluating whether agents stay in their roles)
- Message tracing and parsing (extracting A2A messages from logs)
- Judge system (LLM-based evaluation of role compliance)
"""

from .role_definitions import get_role_definition, get_all_roles
from .role_adherence_judge import RoleAdherenceJudge, print_role_adherence_report
from .message_log_parser import MessageLogParser, extract_message_text_for_analysis, A2AMessage
from .analyze_role_adherence import RoleAdherenceAnalyzer

__all__ = [
    "get_role_definition",
    "get_all_roles",
    "RoleAdherenceJudge",
    "print_role_adherence_report",
    "MessageLogParser",
    "extract_message_text_for_analysis",
    "A2AMessage",
    "RoleAdherenceAnalyzer",
]
