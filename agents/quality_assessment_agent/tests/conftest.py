"""Test configuration and fixtures for Quality Assessment Agent."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse
import aiohttp

from ..models import ResearchSource, QualityAssessment
from ..dependencies import QualityAssessmentDependencies


@pytest.fixture
def test_model():
    """Provide TestModel for testing."""
    return TestModel()


@pytest.fixture
def test_dependencies():
    """Provide test dependencies."""
    # Mock HTTP session to avoid real network calls
    mock_session = Mock(spec=aiohttp.ClientSession)
    mock_session.closed = False
    mock_session.close = AsyncMock()

    return QualityAssessmentDependencies(
        agent_id="test_quality_agent",
        processing_timeout=10,
        fact_check_api_key="test_key",
        http_session=mock_session
    )


@pytest.fixture
def sample_research_source():
    """Provide a sample research source for testing."""
    return ResearchSource(
        source_id="test_source_001",
        url="https://example.com/article",
        title="Test Article Title: A Comprehensive Analysis",
        content="""
        This is a well-structured test article with multiple paragraphs.

        The article contains various elements that should be analyzed for quality.
        According to research studies, this type of content analysis is important
        for determining source credibility and bias indicators.

        ## Introduction

        The introduction provides context and background information.
        Research shows that structured content with proper headings and
        citations tends to be more reliable and credible.

        ## Methodology

        The methodology section explains the approach used:
        - Systematic analysis of content elements
        - Evaluation of structural components
        - Assessment of citation patterns

        ## Results

        Statistical analysis found significant correlations between content
        structure and perceived quality (p < 0.05). The findings suggest
        that well-organized content with proper citations enhances credibility.

        ## Conclusion

        Based on the evidence presented, we can conclude that content structure
        plays a crucial role in quality assessment. Further studies are needed
        to validate these findings across different domains.

        References:
        [1] Smith, J. et al. (2023). Content Quality Analysis. Journal of Information Science.
        [2] https://example.com/research-paper
        """,
        metadata={
            "published_date": "2023-10-15",
            "author": "Dr. Jane Smith",
            "domain": "example.com",
            "word_count": 200
        },
        extraction_timestamp=datetime.now() - timedelta(days=1)
    )


@pytest.fixture
def biased_research_source():
    """Provide a research source with obvious bias indicators."""
    return ResearchSource(
        source_id="biased_source_001",
        url="https://biased-site.com/opinion",
        title="SHOCKING: The Absolutely Terrible Truth About Everything!",
        content="""
        This is an absolutely outrageous article that everyone should read!
        The incredible findings will definitely shock you and completely
        change your perspective on everything.

        I believe this is the most important discovery ever made.
        Obviously, all previous research was totally wrong and stupid.
        Nothing else matters compared to this amazing revelation.

        The ridiculous establishment always tries to hide the truth,
        but this brilliant analysis exposes their lies. Everyone knows
        that the mainstream media never tells the truth about anything.

        In my opinion, this is clearly the only correct interpretation.
        All experts who disagree are obviously biased and completely
        ignorant of the facts.
        """,
        metadata={
            "published_date": "2024-01-01",
            "author": "Anonymous Blogger",
            "domain": "biased-site.com"
        },
        extraction_timestamp=datetime.now()
    )


@pytest.fixture
def low_quality_source():
    """Provide a low-quality research source."""
    return ResearchSource(
        source_id="low_quality_001",
        url="http://unreliable-news.com/breaking",
        title="breaking news",
        content="short low quality content no structure citations",
        metadata={},
        extraction_timestamp=datetime.now() - timedelta(days=1000)  # Old content
    )


@pytest.fixture
def high_authority_source():
    """Provide a high-authority research source."""
    return ResearchSource(
        source_id="authority_source_001",
        url="https://www.nature.com/articles/scientific-study",
        title="Peer-Reviewed Scientific Study on Quality Assessment",
        content="""
        Abstract: This comprehensive study examines methodologies for automated
        quality assessment of digital content sources. The research employs
        systematic analysis techniques to evaluate credibility indicators.

        Introduction: Quality assessment of information sources has become
        increasingly important in the digital age. According to previous
        studies (Johnson et al., 2022; Williams & Brown, 2023), standardized
        metrics for evaluating source credibility are essential.

        Methods: We conducted a systematic review of 500 digital sources,
        analyzing structural elements, citation patterns, and authority
        indicators. The methodology follows established protocols from
        the Information Science Research Foundation.

        Results: Statistical analysis revealed significant correlations
        between content structure and perceived credibility (r=0.78, p<0.001).
        Sources with proper citations scored 40% higher in quality metrics.

        Discussion: The findings support the hypothesis that systematic
        quality assessment can effectively identify credible sources.
        These results align with previous research in information retrieval
        and digital library science.

        Conclusion: Automated quality assessment systems can reliably
        identify high-quality sources when properly calibrated. Further
        research should focus on domain-specific adaptation of these methods.

        Acknowledgments: This research was supported by the National Science
        Foundation Grant #NSF-2023-001.

        References:
        [1] Johnson, A., Smith, B., & Lee, C. (2022). Digital source credibility.
        [2] Williams, D., & Brown, E. (2023). Information quality metrics.
        [3] Thompson, F. et al. (2021). Automated content analysis systems.
        """,
        metadata={
            "published_date": "2023-11-01",
            "author": "Dr. Sarah Johnson, Dr. Michael Chen",
            "journal": "Nature Scientific Reports",
            "doi": "10.1038/s41598-023-001",
            "peer_reviewed": True
        },
        extraction_timestamp=datetime.now() - timedelta(days=5)
    )


@pytest.fixture
def expected_quality_assessment():
    """Provide expected quality assessment structure."""
    return {
        "source_id": "test_source_001",
        "credibility_score": 0.8,
        "bias_score": 0.2,
        "freshness_score": 0.9,
        "authority_score": 0.7,
        "overall_quality": 0.75,
        "confidence_rating": 0.85,
        "flags": [],
        "assessment_details": {}
    }


@pytest.fixture
def quality_assessment_function_model():
    """Create FunctionModel that simulates quality assessment behavior."""

    async def assessment_function(messages, tools):
        """Simulate quality assessment agent responses."""

        # Check what tools are available
        available_tools = [tool.name for tool in tools or []]

        # First response - analyze request and use tools
        if len(messages) <= 2:
            return {
                "assess_domain_authority": {
                    "url": "https://example.com/article"
                }
            }

        # Second response - use content analysis tool
        elif len(messages) <= 4:
            return {
                "assess_content_quality": {
                    "content": "test content",
                    "title": "test title"
                }
            }

        # Third response - bias analysis
        elif len(messages) <= 6:
            return {
                "assess_bias_indicators": {
                    "content": "test content",
                    "title": "test title"
                }
            }

        # Fourth response - freshness check
        elif len(messages) <= 8:
            return {
                "assess_content_freshness": {
                    "extraction_timestamp": "2023-01-01T00:00:00",
                    "metadata": "{}"
                }
            }

        # Final response - return assessment
        else:
            return ModelTextResponse(
                content="Based on the comprehensive analysis using all available tools, "
                       "this source demonstrates good quality indicators with proper "
                       "structure and citations. The assessment is complete."
            )

    return FunctionModel(assessment_function)


@pytest.fixture
def error_function_model():
    """Create FunctionModel that simulates error conditions."""

    async def error_function(messages, tools):
        """Simulate various error conditions."""
        # Simulate API timeout or failure
        raise Exception("Simulated API timeout")

    return FunctionModel(error_function)


@pytest.fixture
async def mock_http_session():
    """Provide a mock HTTP session for testing external API calls."""
    session = Mock(spec=aiohttp.ClientSession)
    session.get = AsyncMock()
    session.post = AsyncMock()
    session.close = AsyncMock()
    session.closed = False
    return session


# Performance testing fixtures
@pytest.fixture
def performance_test_sources():
    """Provide multiple sources for performance testing."""
    sources = []

    for i in range(20):  # Create 20 test sources
        sources.append(ResearchSource(
            source_id=f"perf_test_{i:03d}",
            url=f"https://test-site-{i}.com/article",
            title=f"Test Article {i}: Performance Testing",
            content=f"This is test content for performance testing source {i}. " * 50,
            metadata={"test_index": i},
            extraction_timestamp=datetime.now() - timedelta(hours=i)
        ))

    return sources


# Validation test data
@pytest.fixture
def requirements_test_data():
    """Provide test data for validating against INITIAL.md requirements."""
    return {
        "credibility_test_cases": [
            {"domain": "wikipedia.org", "expected_min_score": 0.8},
            {"domain": "nature.com", "expected_min_score": 0.8},
            {"domain": "random-blog.com", "expected_max_score": 0.7},
        ],
        "bias_test_cases": [
            {
                "content": "This is neutral, factual content with evidence.",
                "expected_max_bias": 0.3
            },
            {
                "content": "This is absolutely terrible and everyone should be outraged!",
                "expected_min_bias": 0.6
            }
        ],
        "performance_requirements": {
            "max_processing_time": 30,  # seconds
            "min_credibility_precision": 0.85,
            "min_bias_detection_recall": 0.80,
            "max_concurrent_sources": 20
        }
    }