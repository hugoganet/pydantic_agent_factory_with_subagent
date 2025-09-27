"""
Data Synthesis Agent - Research Integration and Report Generation.

This agent synthesizes research findings from multiple upstream agents
into comprehensive, audience-appropriate reports.
"""

from .agent import agent, run_synthesis, create_synthesis_agent_with_deps, health_check
from .models import (
    SynthesisRequest, SynthesizedReport, ResearchFinding,
    KeyFinding, ResearchGap, ConfidenceAssessment, Evidence,
    SynthesisRequirements, ReportMetadata
)
from .dependencies import SynthesisDependencies
from .settings import settings

__all__ = [
    # Main agent interface
    "agent",
    "run_synthesis",
    "create_synthesis_agent_with_deps",
    "health_check",

    # Data models
    "SynthesisRequest",
    "SynthesizedReport",
    "ResearchFinding",
    "KeyFinding",
    "ResearchGap",
    "ConfidenceAssessment",
    "Evidence",
    "SynthesisRequirements",
    "ReportMetadata",

    # Dependencies and configuration
    "SynthesisDependencies",
    "settings"
]

__version__ = "1.0.0"
__author__ = "Research Engineering Workflow"
__description__ = "Data synthesis agent for multi-source research integration"