"""
Tests for Data Synthesis Agent models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from ..models import (
    ResearchFinding, ResearchSource, SynthesisRequest,
    SynthesizedReport, KeyFinding, ConfidenceAssessment
)


class TestResearchSource:
    """Test ResearchSource model validation."""

    def test_valid_research_source(self):
        """Test creating a valid research source."""
        source = ResearchSource(
            url="https://example.com/article",
            title="Test Article",
            author="Test Author",
            source_type="web"
        )

        assert source.url == "https://example.com/article"
        assert source.title == "Test Article"
        assert source.source_type == "web"

    def test_minimal_research_source(self):
        """Test creating research source with minimal fields."""
        source = ResearchSource(title="Minimal Source")
        assert source.title == "Minimal Source"
        assert source.source_type == "web"  # Default value


class TestResearchFinding:
    """Test ResearchFinding model validation."""

    def test_valid_research_finding(self, sample_research_source):
        """Test creating a valid research finding."""
        finding = ResearchFinding(
            source_agent="web_research_agent",
            finding_id="test_finding",
            content="Test content for research finding.",
            sources=[sample_research_source],
            confidence_level=0.85,
            key_insights=["insight1", "insight2"]
        )

        assert finding.source_agent == "web_research_agent"
        assert finding.confidence_level == 0.85
        assert len(finding.key_insights) == 2

    def test_confidence_level_validation(self):
        """Test confidence level validation bounds."""
        # Valid confidence levels
        finding = ResearchFinding(
            source_agent="test_agent",
            finding_id="test",
            content="test content",
            confidence_level=0.5
        )
        assert finding.confidence_level == 0.5

        # Invalid confidence levels
        with pytest.raises(ValidationError):
            ResearchFinding(
                source_agent="test_agent",
                finding_id="test",
                content="test content",
                confidence_level=1.5
            )


class TestSynthesisRequest:
    """Test SynthesisRequest model validation."""

    def test_valid_synthesis_request(self, multiple_research_findings):
        """Test creating a valid synthesis request."""
        request = SynthesisRequest(
            request_id="test_request",
            research_findings=multiple_research_findings,
            output_format="executive",
            target_audience="executives"
        )

        assert request.request_id == "test_request"
        assert len(request.research_findings) == len(multiple_research_findings)
        assert request.output_format == "executive"

    def test_invalid_enum_values(self, multiple_research_findings):
        """Test validation of enum fields."""
        with pytest.raises(ValidationError):
            SynthesisRequest(
                request_id="test",
                research_findings=multiple_research_findings,
                output_format="invalid_format"
            )


class TestSynthesizedReport:
    """Test SynthesizedReport model validation."""

    def test_valid_synthesized_report(self):
        """Test creating a valid synthesized report."""
        key_finding = KeyFinding(
            finding_id="key_1",
            title="Test Finding",
            description="Test description",
            confidence_level=0.8
        )

        report = SynthesizedReport(
            request_id="test_report",
            executive_summary="Test summary.",
            key_findings=[key_finding],
            detailed_analysis="Test analysis."
        )

        assert report.request_id == "test_report"
        assert len(report.key_findings) == 1