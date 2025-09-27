"""
Pydantic models for Citation Management Agent.
Defines input/output models from GitHub Issue #13.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import date
from dataclasses import dataclass


# Input Models (from GitHub Issue #13)
class SourceToCite(BaseModel):
    """Source metadata for citation formatting."""
    source_id: str
    title: str
    authors: List[str]
    publication_date: Optional[date] = None
    url: Optional[str] = None
    source_type: Literal["web", "journal", "book", "report", "other"]
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)


class CitationRequest(BaseModel):
    """Request for citation formatting."""
    request_id: str
    sources: List[SourceToCite]
    citation_style: Literal["APA", "MLA", "Chicago", "IEEE", "Harvard"]
    include_bibliography: bool = True
    sort_alphabetically: bool = True


# Output Models (from GitHub Issue #13)
class FormattedCitation(BaseModel):
    """Formatted citation with validation status."""
    source_id: str
    citation_key: str
    inline_citation: str
    full_citation: str
    citation_style: str
    validation_status: Literal["valid", "warning", "error"]


class CitationValidation(BaseModel):
    """Citation validation results."""
    total_sources: int
    valid_citations: int
    warnings: List[str]
    errors: List[str]
    missing_fields: Dict[str, List[str]] = Field(default_factory=dict)  # source_id -> missing_fields
    duplicate_sources: List[Dict[str, str]] = Field(default_factory=list)  # detected duplicates


class CitationResponse(BaseModel):
    """Complete citation response."""
    request_id: str
    citations: List[FormattedCitation]
    bibliography: List[str]
    citation_map: Dict[str, str] = Field(default_factory=dict)  # source_id -> citation_key
    style_used: str
    validation_results: CitationValidation


# Dependencies
@dataclass
class CitationDependencies:
    """Dependencies for Citation Management Agent execution."""
    session_id: Optional[str] = None
    batch_size: int = 50
    duplicate_threshold: float = 0.85
    validate_citations: bool = True
    max_retries: int = 3
    timeout: int = 30
    debug: bool = False

    # Citation style validation rules (built-in)
    _style_requirements: Dict[str, List[str]] = None

    def __post_init__(self):
        if self._style_requirements is None:
            self._style_requirements = {
                "APA": ["authors", "publication_date", "title"],
                "MLA": ["authors", "title", "publication_date"],
                "Chicago": ["authors", "title", "publication_date"],
                "IEEE": ["authors", "title", "publication_date"],
                "Harvard": ["authors", "publication_date", "title"]
            }

    def get_required_fields(self, style: str) -> List[str]:
        """Get required fields for citation style."""
        return self._style_requirements.get(style.upper(), ["authors", "title"])


# Agent Message Protocol (for workflow integration)
class AgentMessage(BaseModel):
    """Standard inter-agent communication format."""
    sender_id: str
    recipient_id: str
    message_type: str  # "citation_request", "citation_response"
    payload: Dict[str, Any]
    timestamp: Optional[str] = None
    correlation_id: Optional[str] = None
    priority: int = 1