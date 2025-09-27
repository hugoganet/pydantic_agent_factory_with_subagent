"""
Web Research Agent - Multi-engine web search with content extraction.
A Pydantic AI agent for comprehensive web research tasks.
"""

from .agent import agent, run_web_search, create_agent_with_deps
from .dependencies import WebResearchDependencies
from .models import (
    SearchRequest,
    WebSearchResults,
    WebSource,
    ContentExtraction,
    AgentMessage
)
from .settings import settings

__version__ = "1.0.0"
__author__ = "Pydantic AI Agent Factory"

__all__ = [
    "agent",
    "run_web_search",
    "create_agent_with_deps",
    "WebResearchDependencies",
    "SearchRequest",
    "WebSearchResults",
    "WebSource",
    "ContentExtraction",
    "AgentMessage",
    "settings"
]