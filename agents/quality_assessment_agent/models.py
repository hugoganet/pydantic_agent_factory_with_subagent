"""Data models for Quality Assessment Agent."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class ResearchSource(BaseModel):
    """Input model for research sources to be assessed."""
    source_id: str = Field(..., description="Unique identifier for the source")
    url: Optional[str] = Field(None, description="Source URL if available")
    title: str = Field(..., description="Title of the source")
    content: str = Field(..., description="Full text content of the source")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional source metadata")
    extraction_timestamp: datetime = Field(..., description="When the source was extracted")


class QualityAssessment(BaseModel):
    """Output model for quality assessment results."""
    source_id: str = Field(..., description="Source identifier")
    credibility_score: float = Field(..., ge=0.0, le=1.0, description="Overall credibility score (0.0-1.0)")
    bias_score: float = Field(..., ge=0.0, le=1.0, description="Bias detection score (0.0 = no bias, 1.0 = high bias)")
    freshness_score: float = Field(..., ge=0.0, le=1.0, description="Content freshness score (0.0-1.0)")
    authority_score: float = Field(..., ge=0.0, le=1.0, description="Domain/source authority score (0.0-1.0)")
    overall_quality: float = Field(..., ge=0.0, le=1.0, description="Overall quality composite score (0.0-1.0)")
    confidence_rating: float = Field(..., ge=0.0, le=1.0, description="Confidence in assessment (0.0-1.0)")
    flags: List[str] = Field(default_factory=list, description="Warning flags or quality issues")
    assessment_timestamp: datetime = Field(default_factory=datetime.now, description="When assessment was performed")

    # Detailed breakdown for transparency
    assessment_details: Dict[str, Any] = Field(default_factory=dict, description="Detailed assessment breakdown")


class AgentMessage(BaseModel):
    """Standard inter-agent communication format."""
    message_id: str = Field(..., description="Unique message identifier")
    sender_id: str = Field(..., description="Sending agent identifier")
    recipient_id: str = Field(..., description="Receiving agent identifier")
    message_type: str = Field(..., description="Message type: task, result, status, error, health")
    payload: Dict[str, Any] = Field(..., description="Message payload")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    correlation_id: str = Field(..., description="Correlation ID for request tracking")
    priority: int = Field(default=1, description="Message priority (1-10)")
    retry_count: int = Field(default=0, description="Number of retry attempts")


class DomainAnalysis(BaseModel):
    """Internal model for domain authority analysis."""
    domain: str = Field(..., description="Domain name")
    ssl_enabled: bool = Field(default=False, description="Whether SSL is enabled")
    domain_age_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Domain age score")
    reputation_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Domain reputation score")
    authority_indicators: List[str] = Field(default_factory=list, description="Authority indicators found")


class ContentAnalysis(BaseModel):
    """Internal model for content quality analysis."""
    word_count: int = Field(default=0, description="Word count of content")
    structure_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Content structure quality")
    citation_count: int = Field(default=0, description="Number of citations found")
    readability_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Content readability score")
    completeness_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Content completeness score")


class BiasAnalysis(BaseModel):
    """Internal model for bias detection analysis."""
    emotional_language_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Emotional language indicator")
    absolute_terms_count: int = Field(default=0, description="Count of absolute terms")
    perspective_diversity: float = Field(default=0.5, ge=0.0, le=1.0, description="Perspective diversity score")
    bias_indicators: List[str] = Field(default_factory=list, description="Specific bias indicators found")
    neutrality_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Overall neutrality score")