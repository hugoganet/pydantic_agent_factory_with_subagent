"""
Citation Management Agent - Academic source attribution and reference formatting.

This agent provides comprehensive citation management capabilities including:
- Multi-style citation formatting (APA, MLA, Chicago, IEEE, Harvard)
- Duplicate source detection and merging
- Citation validation and completeness checking
- Bibliography generation with alphabetical sorting
- Integration with Research Engineering Workflow
"""

from .agent import agent, run_citation_agent, process_citation_request
from .models import (
    CitationRequest,
    CitationResponse,
    SourceToCite,
    FormattedCitation,
    CitationValidation,
    CitationDependencies,
    AgentMessage
)
from .settings import Settings, load_settings
from .providers import get_citation_model, get_llm_model

__version__ = "1.0.0"
__author__ = "Citation Management Agent"

__all__ = [
    # Main agent
    "agent",
    "run_citation_agent",
    "process_citation_request",

    # Models
    "CitationRequest",
    "CitationResponse",
    "SourceToCite",
    "FormattedCitation",
    "CitationValidation",
    "CitationDependencies",
    "AgentMessage",

    # Configuration
    "Settings",
    "load_settings",
    "get_citation_model",
    "get_llm_model",
]