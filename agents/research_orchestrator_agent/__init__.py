"""
Research Orchestrator Agent

Master coordinator for the Research Engineering Workflow system.
Orchestrates 7 specialized agents to deliver comprehensive research reports.
"""

from .agent import orchestrator_agent, run_orchestration, health_check
from .dependencies import OrchestratorDependencies
from .settings import settings

__version__ = "1.0.0"
__author__ = "Research Engineering Workflow Team"

__all__ = [
    "orchestrator_agent",
    "run_orchestration",
    "health_check",
    "OrchestratorDependencies",
    "settings"
]