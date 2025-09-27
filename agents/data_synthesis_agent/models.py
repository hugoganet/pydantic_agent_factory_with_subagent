"""
Pydantic models for Data Synthesis Agent.

Defines input and output models for research finding integration,
pattern analysis, and report generation.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ResearchSource(BaseModel):
    """Individual research source with metadata."""
    url: Optional[str] = None
    title: str
    author: Optional[str] = None
    publication_date: Optional[str] = None
    source_type: str = "web"  # "web", "document", "api", "database"


class ResearchFinding(BaseModel):
    """Research finding from upstream agents."""
    source_agent: str = Field(description="Agent that produced this finding")
    finding_id: str = Field(description="Unique identifier for this finding")
    content: str = Field(description="Main finding content")
    sources: List[ResearchSource] = Field(default_factory=list)
    confidence_level: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    key_insights: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class SynthesisRequirements(BaseModel):
    """Requirements for synthesis processing."""
    focus_areas: List[str] = Field(default_factory=list, description="Areas to emphasize")
    depth_level: Literal["brief", "standard", "comprehensive"] = "standard"
    include_methodology: bool = True
    include_gaps: bool = True
    include_recommendations: bool = False


class SynthesisRequest(BaseModel):
    """Request for data synthesis."""
    request_id: str = Field(description="Unique synthesis request identifier")
    research_findings: List[ResearchFinding] = Field(description="Findings to synthesize")
    synthesis_requirements: SynthesisRequirements = Field(default_factory=SynthesisRequirements)
    output_format: Literal["executive", "detailed", "technical"] = "executive"
    target_audience: Literal["executives", "researchers", "technical", "general"] = "executives"
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class KeyFinding(BaseModel):
    """Individual key finding in synthesized report."""
    finding_id: str
    title: str
    description: str
    supporting_sources: List[str] = Field(default_factory=list)
    confidence_level: float = Field(ge=0.0, le=1.0)
    significance: Literal["high", "medium", "low"] = "medium"
    cross_validation_status: Literal["validated", "conflicting", "insufficient"] = "insufficient"


class ResearchGap(BaseModel):
    """Identified gap in research coverage."""
    gap_id: str
    description: str
    impact_level: Literal["high", "medium", "low"] = "medium"
    suggested_research: Optional[str] = None


class ConfidenceAssessment(BaseModel):
    """Overall confidence assessment of synthesis."""
    overall_confidence: float = Field(ge=0.0, le=1.0)
    source_reliability: float = Field(ge=0.0, le=1.0)
    cross_validation_score: float = Field(ge=0.0, le=1.0)
    completeness_score: float = Field(ge=0.0, le=1.0)
    methodology_notes: str = ""


class Evidence(BaseModel):
    """Supporting evidence for findings."""
    evidence_id: str
    content: str
    source: ResearchSource
    relevance_score: float = Field(ge=0.0, le=1.0)
    validation_status: Literal["verified", "unverified", "conflicting"] = "unverified"


class ReportMetadata(BaseModel):
    """Metadata about the generated report."""
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    synthesis_duration_seconds: Optional[float] = None
    findings_processed: int = 0
    sources_analyzed: int = 0
    agent_version: str = "1.0.0"
    quality_score: Optional[float] = None


class SynthesizedReport(BaseModel):
    """Complete synthesized research report."""
    request_id: str
    executive_summary: str = Field(description="High-level overview and key takeaways")
    key_findings: List[KeyFinding] = Field(default_factory=list)
    detailed_analysis: str = Field(description="Comprehensive analysis section")
    supporting_evidence: List[Evidence] = Field(default_factory=list)
    gaps_identified: List[ResearchGap] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    confidence_assessment: ConfidenceAssessment = Field(default_factory=ConfidenceAssessment)
    metadata: ReportMetadata = Field(default_factory=ReportMetadata)


# Tool output models
class IntegrationResult(BaseModel):
    """Result of data integration tool."""
    success: bool = True
    integrated_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Result of pattern analysis tool."""
    success: bool = True
    analysis_results: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


class ReportResult(BaseModel):
    """Result of report generation tool."""
    success: bool = True
    synthesized_report: Dict[str, Any] = Field(default_factory=dict)
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)