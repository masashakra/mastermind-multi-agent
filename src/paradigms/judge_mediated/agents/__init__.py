# Boss-Worker Agents Module

from paradigms.judge_mediated.agents.base_agent import BaseAgent
from paradigms.judge_mediated.agents.analyzer import AnalyzerAgent, AGENT_CARD as ANALYZER_CARD
from paradigms.judge_mediated.agents.strategist import StrategistAgent, AGENT_CARD as STRATEGIST_CARD
from paradigms.judge_mediated.agents.proposer import ProposerAgent, AGENT_CARD as PROPOSER_CARD
from paradigms.judge_mediated.agents.validator import ValidatorAgent, AGENT_CARD as VALIDATOR_CARD
from paradigms.judge_mediated.agents.logger import LoggerAgent, AGENT_CARD as LOGGER_CARD
from paradigms.judge_mediated.agents.metrics import MetricsAgent, AGENT_CARD as METRICS_CARD

__all__ = [
    "BaseAgent",
    "AnalyzerAgent",
    "StrategistAgent",
    "ProposerAgent",
    "ValidatorAgent",
    "LoggerAgent",
    "MetricsAgent",
    "ANALYZER_CARD",
    "STRATEGIST_CARD",
    "PROPOSER_CARD",
    "VALIDATOR_CARD",
    "LOGGER_CARD",
    "METRICS_CARD",
]
