"""
Query Strategy Agent - Research approach optimization and strategy recommendation.

This agent provides strategic advisory services for the Research Engineering Multi-Agent Workflow,
analyzing research queries and recommending optimal execution strategies.
"""

from .agent import (
    agent,
    analyze_research_strategy,
    create_strategy_agent_with_deps,
    quick_complexity_check
)
from .dependencies import AgentDependencies
from .settings import settings, load_settings
from .providers import get_llm_model

__version__ = "1.0.0"
__author__ = "Research Engineering Workflow Team"

__all__ = [
    "agent",
    "analyze_research_strategy",
    "create_strategy_agent_with_deps",
    "quick_complexity_check",
    "AgentDependencies",
    "settings",
    "load_settings",
    "get_llm_model"
]