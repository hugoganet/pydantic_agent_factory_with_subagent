"""
Pydantic models for Web Research Agent input and output structures.
Defines the data models used for search requests, content extraction, and results.
"""

from datetime import datetime
from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field


# Input Models
class DateRange(BaseModel):
    """Date range filter for search results."""
    start_date: Optional[datetime] = Field(default=None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(default=None, description="End date for filtering")


class SearchRequest(BaseModel):
    """Search request model with comprehensive configuration."""
    search_id: str = Field(..., description="Unique identifier for this search request")
    query: str = Field(..., description="Search query to execute")
    search_engines: List[Literal["brave", "google", "bing"]] = Field(
        default=["brave"], description="Search engines to use in order of preference"
    )
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum results per engine")
    quality_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum quality score for results"
    )
    content_types: List[str] = Field(
        default=["article", "paper", "report", "news"], description="Preferred content types"
    )
    date_range: Optional[DateRange] = Field(default=None, description="Optional date filtering")


class ContentExtraction(BaseModel):
    """Configuration for content extraction from specific URLs."""
    url: str = Field(..., description="URL to extract content from")
    extract_full_text: bool = Field(default=True, description="Extract full text content")
    extract_metadata: bool = Field(default=True, description="Extract metadata")
    extract_images: bool = Field(default=False, description="Extract image references")


# Output Models
class SourceMetadata(BaseModel):
    """Metadata for a web source."""
    domain: str = Field(..., description="Source domain")
    publish_date: Optional[datetime] = Field(default=None, description="Publication date if available")
    author: Optional[str] = Field(default=None, description="Author if available")
    word_count: int = Field(..., description="Word count of extracted content")
    content_type: str = Field(..., description="Detected content type")
    language: str = Field(default="en", description="Detected language")


class WebSource(BaseModel):
    """Individual web source with extracted content and quality metrics."""
    source_id: str = Field(..., description="Unique identifier for this source")
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Page title")
    content: str = Field(..., description="Extracted text content")
    metadata: SourceMetadata = Field(..., description="Source metadata")
    extraction_timestamp: datetime = Field(..., description="When content was extracted")
    credibility_indicators: List[str] = Field(
        default_factory=list, description="List of credibility indicators found"
    )
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Computed quality score")


class SearchMetadata(BaseModel):
    """Metadata about the search execution process."""
    engines_used: List[str] = Field(..., description="Search engines that were used")
    total_execution_time: float = Field(..., description="Total execution time in seconds")
    results_per_engine: Dict[str, int] = Field(..., description="Results count per engine")
    rate_limit_delays: Dict[str, float] = Field(..., description="Rate limit delays per engine")


class QualitySummary(BaseModel):
    """Summary of quality assessment for all sources."""
    average_quality_score: float = Field(..., description="Average quality score of all results")
    high_quality_count: int = Field(..., description="Number of high-quality sources (>0.8)")
    filtered_out_count: int = Field(..., description="Number of sources filtered out")
    credible_sources_count: int = Field(..., description="Number of sources with credibility indicators")


class WebSearchResults(BaseModel):
    """Complete web search results with all metadata."""
    search_id: str = Field(..., description="Unique identifier matching the request")
    query_used: str = Field(..., description="Actual query executed")
    total_results: int = Field(..., description="Total number of results found")
    sources: List[WebSource] = Field(..., description="List of web sources found")
    search_metadata: SearchMetadata = Field(..., description="Search execution metadata")
    quality_summary: QualitySummary = Field(..., description="Quality assessment summary")


# Inter-agent communication models (for workflow integration)
class AgentMessage(BaseModel):
    """Standard inter-agent communication format."""
    message_id: str = Field(..., description="Unique message identifier")
    sender_id: str = Field(..., description="Sending agent identifier")
    recipient_id: str = Field(..., description="Receiving agent identifier")
    message_type: Literal["task", "result", "status", "error", "health"] = Field(..., description="Message type")
    payload: Dict[str, Any] = Field(..., description="Message payload")
    timestamp: datetime = Field(..., description="Message timestamp")
    correlation_id: str = Field(..., description="Correlation identifier for request tracking")
    priority: int = Field(default=1, description="Message priority")
    retry_count: int = Field(default=0, description="Number of retries attempted")