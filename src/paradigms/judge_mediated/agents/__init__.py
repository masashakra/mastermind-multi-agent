# Judge-Mediated Paradigm Agents Module (Simplified - 1 Agent Per Team)

from paradigms.judge_mediated.agents.base_agent import BaseAgent
from paradigms.judge_mediated.agents.team_agent import TeamAgent, AGENT_CARD as TEAM_AGENT_CARD
from paradigms.judge_mediated.agents.judge import JudgeAgent, AGENT_CARD as JUDGE_CARD
from paradigms.judge_mediated.agents.logger import LoggerAgent
from paradigms.judge_mediated.agents.metrics import MetricsAgent, AGENT_CARD as METRICS_CARD

__all__ = [
    "BaseAgent",
    "TeamAgent",
    "JudgeAgent",
    "LoggerAgent",
    "MetricsAgent",
    "TEAM_AGENT_CARD",
    "JUDGE_CARD",
    "METRICS_CARD",
]
