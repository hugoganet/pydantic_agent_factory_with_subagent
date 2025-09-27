"""
Test configuration and fixtures for Data Synthesis Agent tests.
"""

import pytest
from datetime import datetime

from pydantic_ai import TestModel, FunctionModel

from ..models import (
    ResearchFinding, ResearchSource, SynthesisRequest,
    SynthesisRequirements, SynthesizedReport, KeyFinding
)
from ..dependencies import SynthesisDependencies


@pytest.fixture
def test_dependencies():
    """Test dependencies for synthesis operations."""
    return SynthesisDependencies(
        session_id="test-session",
        synthesis_request_id="test-request",
        research_phase_complete=True,
        max_findings_count=10,
        synthesis_timeout=30,
        debug_mode=True
    )


@pytest.fixture
def sample_research_source():
    """Sample research source for testing."""
    return ResearchSource(
        url="https://example.com/research",
        title="Test Research Article",
        author="Dr. Test Author",
        publication_date="2024-01-15",
        source_type="web"
    )


@pytest.fixture
def sample_research_finding(sample_research_source):
    """Sample research finding for testing."""
    return ResearchFinding(
        source_agent="web_research_agent",
        finding_id="test_finding_1",
        content="AI adoption is accelerating across industries.",
        sources=[sample_research_source],
        confidence_level=0.85,
        key_insights=["AI adoption increasing", "Industry-wide implementation"],
        metadata={"extraction_method": "automated"}
    )


@pytest.fixture
def multiple_research_findings(sample_research_source):
    """Multiple research findings for comprehensive testing."""
    return [
        ResearchFinding(
            source_agent="web_research_agent",
            finding_id="web_finding_1",
            content="AI technologies are transforming business operations.",
            sources=[sample_research_source],
            confidence_level=0.8,
            key_insights=["AI transformation", "Business operations"],
            metadata={"source_type": "web_search"}
        ),
        ResearchFinding(
            source_agent="tool_integration_agent",
            finding_id="tool_finding_1",
            content="Internal analysis shows AI implementation benefits.",
            sources=[sample_research_source],
            confidence_level=0.9,
            key_insights=["AI implementation", "Performance metrics"],
            metadata={"source_type": "internal_tool"}
        )
    ]


@pytest.fixture
def sample_synthesis_request(multiple_research_findings):
    """Sample synthesis request for testing."""
    return SynthesisRequest(
        request_id="test_synthesis_001",
        research_findings=multiple_research_findings,
        output_format="executive",
        target_audience="executives",
        quality_threshold=0.7
    )


@pytest.fixture
def mock_test_model():
    """TestModel for isolated agent testing."""
    return TestModel()


@pytest.fixture
def mock_function_model():
    """FunctionModel with synthesis responses."""
    def synthesis_response(messages):
        return {
            "executive_summary": "AI adoption is accelerating across industries.",
            "key_findings": [{
                "finding_id": "key_1",
                "title": "AI Adoption Acceleration",
                "description": "Multiple sources confirm increasing AI implementation",
                "confidence_level": 0.8,
                "cross_validation_status": "validated"
            }],
            "detailed_analysis": "Comprehensive analysis of AI trends.",
            "confidence_assessment": 0.8
        }

    return FunctionModel(synthesis_response)