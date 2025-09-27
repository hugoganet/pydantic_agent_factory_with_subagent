"""
Test Pydantic models for Web Research Agent.
Validates input/output model structure, validation, and serialization.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any
import uuid

from pydantic import ValidationError

from ..models import (
    DateRange, SearchRequest, ContentExtraction, SourceMetadata,
    WebSource, SearchMetadata, QualitySummary, WebSearchResults,
    AgentMessage
)


class TestInputModels:
    """Test input model validation and structure."""

    def test_date_range_model(self):
        """Test DateRange model validation."""
        # Valid date range
        date_range = DateRange(
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 12, 31, tzinfo=timezone.utc)
        )
        assert date_range.start_date is not None
        assert date_range.end_date is not None

        # Optional fields
        empty_range = DateRange()
        assert empty_range.start_date is None
        assert empty_range.end_date is None

    def test_search_request_model_valid(self):
        """Test SearchRequest model with valid data."""
        request = SearchRequest(
            search_id="test-search-123",
            query="machine learning algorithms",
            search_engines=["brave", "google"],
            max_results=20,
            quality_threshold=0.8,
            content_types=["article", "paper"],
            date_range=DateRange(
                start_date=datetime(2024, 1, 1, tzinfo=timezone.utc)
            )
        )

        assert request.search_id == "test-search-123"
        assert request.query == "machine learning algorithms"
        assert request.search_engines == ["brave", "google"]
        assert request.max_results == 20
        assert request.quality_threshold == 0.8
        assert request.date_range is not None

    def test_search_request_defaults(self):
        """Test SearchRequest model with default values."""
        request = SearchRequest(
            search_id="test",
            query="test query"
        )

        assert request.search_engines == ["brave"]  # Default
        assert request.max_results == 20  # Default
        assert request.quality_threshold == 0.7  # Default
        assert request.content_types == ["article", "paper", "report", "news"]  # Default
        assert request.date_range is None  # Default

    def test_search_request_validation_errors(self):
        """Test SearchRequest validation constraints."""
        # Missing required fields
        with pytest.raises(ValidationError):
            SearchRequest()

        # Invalid search engine
        with pytest.raises(ValidationError):
            SearchRequest(
                search_id="test",
                query="test",
                search_engines=["invalid_engine"]
            )

        # Max results out of range
        with pytest.raises(ValidationError):
            SearchRequest(
                search_id="test",
                query="test",
                max_results=150  # > 100
            )

        # Quality threshold out of range
        with pytest.raises(ValidationError):
            SearchRequest(
                search_id="test",
                query="test",
                quality_threshold=1.5  # > 1.0
            )

    def test_content_extraction_model(self):
        """Test ContentExtraction model validation."""
        extraction = ContentExtraction(
            url="https://example.com/article",
            extract_full_text=True,
            extract_metadata=True,
            extract_images=False
        )

        assert extraction.url == "https://example.com/article"
        assert extraction.extract_full_text is True
        assert extraction.extract_metadata is True
        assert extraction.extract_images is False

        # Test defaults
        minimal_extraction = ContentExtraction(
            url="https://example.com"
        )
        assert minimal_extraction.extract_full_text is True  # Default
        assert minimal_extraction.extract_metadata is True  # Default
        assert minimal_extraction.extract_images is False  # Default


class TestOutputModels:
    """Test output model validation and structure."""

    def test_source_metadata_model(self):
        """Test SourceMetadata model validation."""
        metadata = SourceMetadata(
            domain="example.com",
            publish_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            author="Dr. Jane Smith",
            word_count=1500,
            content_type="article",
            language="en"
        )

        assert metadata.domain == "example.com"
        assert metadata.author == "Dr. Jane Smith"
        assert metadata.word_count == 1500
        assert metadata.content_type == "article"
        assert metadata.language == "en"

    def test_web_source_model(self):
        """Test WebSource model validation."""
        metadata = SourceMetadata(
            domain="example.com",
            word_count=1000,
            content_type="article"
        )

        source = WebSource(
            source_id="src-123",
            url="https://example.com/article",
            title="Test Article",
            content="This is the extracted content...",
            metadata=metadata,
            extraction_timestamp=datetime.now(timezone.utc),
            credibility_indicators=["Educational institution", "Author identified"],
            quality_score=0.85
        )

        assert source.source_id == "src-123"
        assert source.quality_score == 0.85
        assert len(source.credibility_indicators) == 2

        # Test quality score validation
        with pytest.raises(ValidationError):
            WebSource(
                source_id="test",
                url="test",
                title="test",
                content="test",
                metadata=metadata,
                extraction_timestamp=datetime.now(timezone.utc),
                quality_score=1.5  # Invalid: > 1.0
            )

    def test_search_metadata_model(self):
        """Test SearchMetadata model validation."""
        metadata = SearchMetadata(
            engines_used=["brave", "google"],
            total_execution_time=2.5,
            results_per_engine={"brave": 15, "google": 10},
            rate_limit_delays={"brave": 0.5, "google": 1.0}
        )

        assert metadata.engines_used == ["brave", "google"]
        assert metadata.total_execution_time == 2.5
        assert metadata.results_per_engine["brave"] == 15
        assert metadata.rate_limit_delays["google"] == 1.0

    def test_quality_summary_model(self):
        """Test QualitySummary model validation."""
        summary = QualitySummary(
            average_quality_score=0.75,
            high_quality_count=8,
            filtered_out_count=5,
            credible_sources_count=12
        )

        assert summary.average_quality_score == 0.75
        assert summary.high_quality_count == 8
        assert summary.filtered_out_count == 5
        assert summary.credible_sources_count == 12

    def test_web_search_results_complete_model(self):
        """Test complete WebSearchResults model."""
        # Create component models
        metadata = SourceMetadata(
            domain="example.com",
            word_count=1000,
            content_type="article"
        )

        sources = [
            WebSource(
                source_id="src-1",
                url="https://example.com/1",
                title="Article 1",
                content="Content 1",
                metadata=metadata,
                extraction_timestamp=datetime.now(timezone.utc),
                quality_score=0.8
            ),
            WebSource(
                source_id="src-2",
                url="https://example.com/2",
                title="Article 2",
                content="Content 2",
                metadata=metadata,
                extraction_timestamp=datetime.now(timezone.utc),
                quality_score=0.9
            )
        ]

        search_metadata = SearchMetadata(
            engines_used=["brave"],
            total_execution_time=3.0,
            results_per_engine={"brave": 2},
            rate_limit_delays={"brave": 0.5}
        )

        quality_summary = QualitySummary(
            average_quality_score=0.85,
            high_quality_count=2,
            filtered_out_count=0,
            credible_sources_count=2
        )

        # Create complete results
        results = WebSearchResults(
            search_id="search-456",
            query_used="machine learning",
            total_results=2,
            sources=sources,
            search_metadata=search_metadata,
            quality_summary=quality_summary
        )

        assert results.search_id == "search-456"
        assert results.query_used == "machine learning"
        assert results.total_results == 2
        assert len(results.sources) == 2
        assert results.search_metadata.engines_used == ["brave"]
        assert results.quality_summary.average_quality_score == 0.85


class TestAgentMessage:
    """Test inter-agent communication model."""

    def test_agent_message_model(self):
        """Test AgentMessage model validation."""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id="web_research_agent",
            recipient_id="quality_assessment_agent",
            message_type="result",
            payload={
                "search_results": "...",
                "status": "completed",
                "source_count": 25
            },
            timestamp=datetime.now(timezone.utc),
            correlation_id="workflow-789",
            priority=1,
            retry_count=0
        )

        assert message.sender_id == "web_research_agent"
        assert message.message_type == "result"
        assert message.payload["source_count"] == 25
        assert message.priority == 1

    def test_agent_message_types(self):
        """Test AgentMessage type validation."""
        valid_types = ["task", "result", "status", "error", "health"]

        for msg_type in valid_types:
            message = AgentMessage(
                message_id="test",
                sender_id="test",
                recipient_id="test",
                message_type=msg_type,
                payload={},
                timestamp=datetime.now(timezone.utc),
                correlation_id="test"
            )
            assert message.message_type == msg_type

        # Invalid type
        with pytest.raises(ValidationError):
            AgentMessage(
                message_id="test",
                sender_id="test",
                recipient_id="test",
                message_type="invalid_type",
                payload={},
                timestamp=datetime.now(timezone.utc),
                correlation_id="test"
            )

    def test_agent_message_defaults(self):
        """Test AgentMessage default values."""
        message = AgentMessage(
            message_id="test",
            sender_id="test",
            recipient_id="test",
            message_type="task",
            payload={},
            timestamp=datetime.now(timezone.utc),
            correlation_id="test"
        )

        assert message.priority == 1  # Default
        assert message.retry_count == 0  # Default


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_search_request_serialization(self):
        """Test SearchRequest JSON serialization."""
        request = SearchRequest(
            search_id="test-123",
            query="artificial intelligence",
            search_engines=["brave", "google"],
            max_results=15,
            quality_threshold=0.75
        )

        # Test to dict
        data = request.model_dump()
        assert data["search_id"] == "test-123"
        assert data["search_engines"] == ["brave", "google"]

        # Test from dict
        new_request = SearchRequest.model_validate(data)
        assert new_request.search_id == request.search_id
        assert new_request.query == request.query

    def test_web_search_results_serialization(self):
        """Test WebSearchResults complete serialization."""
        # Create minimal but valid results
        metadata = SourceMetadata(
            domain="test.com",
            word_count=100,
            content_type="article"
        )

        source = WebSource(
            source_id="test-src",
            url="https://test.com",
            title="Test",
            content="Test content",
            metadata=metadata,
            extraction_timestamp=datetime.now(timezone.utc),
            quality_score=0.7
        )

        search_meta = SearchMetadata(
            engines_used=["brave"],
            total_execution_time=1.0,
            results_per_engine={"brave": 1},
            rate_limit_delays={"brave": 0.5}
        )

        quality = QualitySummary(
            average_quality_score=0.7,
            high_quality_count=1,
            filtered_out_count=0,
            credible_sources_count=1
        )

        results = WebSearchResults(
            search_id="test",
            query_used="test",
            total_results=1,
            sources=[source],
            search_metadata=search_meta,
            quality_summary=quality
        )

        # Test serialization
        data = results.model_dump()
        assert data["search_id"] == "test"
        assert len(data["sources"]) == 1

        # Test deserialization
        new_results = WebSearchResults.model_validate(data)
        assert new_results.search_id == results.search_id
        assert len(new_results.sources) == 1
        assert new_results.sources[0].quality_score == 0.7


class TestModelEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_lists_and_optional_fields(self):
        """Test models with empty lists and optional fields."""
        # WebSource with empty credibility indicators
        metadata = SourceMetadata(
            domain="test.com",
            word_count=0,  # Edge case: zero words
            content_type="webpage"
        )

        source = WebSource(
            source_id="empty-test",
            url="https://empty.com",
            title="",  # Edge case: empty title
            content="",  # Edge case: empty content
            metadata=metadata,
            extraction_timestamp=datetime.now(timezone.utc),
            credibility_indicators=[],  # Empty list
            quality_score=0.0  # Minimum score
        )

        assert source.quality_score == 0.0
        assert len(source.credibility_indicators) == 0
        assert source.title == ""

    def test_boundary_values(self):
        """Test boundary values for numeric fields."""
        # Test minimum quality score
        request_min = SearchRequest(
            search_id="min-test",
            query="test",
            max_results=1,  # Minimum
            quality_threshold=0.0  # Minimum
        )
        assert request_min.max_results == 1
        assert request_min.quality_threshold == 0.0

        # Test maximum quality score
        request_max = SearchRequest(
            search_id="max-test",
            query="test",
            max_results=100,  # Maximum
            quality_threshold=1.0  # Maximum
        )
        assert request_max.max_results == 100
        assert request_max.quality_threshold == 1.0

    def test_unicode_and_special_characters(self):
        """Test models with unicode and special characters."""
        request = SearchRequest(
            search_id="unicode-test",
            query="人工智能 machine learning 🤖"
        )
        assert "🤖" in request.query

        # Test with special characters in metadata
        metadata = SourceMetadata(
            domain="test.com",
            author="Dr. José García-Rodríguez",
            word_count=100,
            content_type="artículo"
        )
        assert "García" in metadata.author
        assert "artículo" == metadata.content_type