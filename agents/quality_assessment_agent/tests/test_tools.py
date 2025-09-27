"""Test tool implementations for quality assessment."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from ..tools import (
    analyze_domain_authority,
    analyze_content_quality,
    analyze_bias_indicators,
    check_freshness
)
from ..models import DomainAnalysis, ContentAnalysis, BiasAnalysis


class TestDomainAuthorityTool:
    """Test domain authority analysis tool."""

    @pytest.mark.asyncio
    async def test_analyze_domain_authority_high_authority(self, test_dependencies):
        """Test domain authority analysis for high-authority domains."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Test high-authority academic domain
        result = await analyze_domain_authority(mock_ctx, "https://www.nature.com/article")

        assert isinstance(result, DomainAnalysis)
        assert result.domain == "www.nature.com"
        assert result.ssl_enabled is True
        assert result.reputation_score >= 0.8
        assert "high_authority_domain:nature.com" in result.authority_indicators
        assert "ssl_enabled" in result.authority_indicators

    @pytest.mark.asyncio
    async def test_analyze_domain_authority_government(self, test_dependencies):
        """Test domain authority analysis for government domains."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        result = await analyze_domain_authority(mock_ctx, "https://cdc.gov/health-info")

        assert isinstance(result, DomainAnalysis)
        assert result.domain == "cdc.gov"
        assert result.ssl_enabled is True
        assert result.reputation_score >= 0.9
        assert "government_domain" in result.authority_indicators
        assert result.domain_age_score >= 0.8

    @pytest.mark.asyncio
    async def test_analyze_domain_authority_educational(self, test_dependencies):
        """Test domain authority analysis for educational domains."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        result = await analyze_domain_authority(mock_ctx, "https://university.edu/research")

        assert isinstance(result, DomainAnalysis)
        assert result.domain == "university.edu"
        assert result.ssl_enabled is True
        assert result.reputation_score >= 0.8
        assert "educational_domain" in result.authority_indicators

    @pytest.mark.asyncio
    async def test_analyze_domain_authority_low_authority(self, test_dependencies):
        """Test domain authority analysis for low-authority domains."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        result = await analyze_domain_authority(mock_ctx, "http://random-blog.com/post")

        assert isinstance(result, DomainAnalysis)
        assert result.domain == "random-blog.com"
        assert result.ssl_enabled is False
        assert result.reputation_score <= 0.7
        # Should not have high authority indicators

    @pytest.mark.asyncio
    async def test_analyze_domain_authority_no_url(self, test_dependencies):
        """Test domain authority analysis with no URL provided."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        result = await analyze_domain_authority(mock_ctx, None)

        assert isinstance(result, DomainAnalysis)
        assert result.domain == "unknown"
        assert "no_url_provided" in result.authority_indicators

    @pytest.mark.asyncio
    async def test_analyze_domain_authority_invalid_url(self, test_dependencies):
        """Test domain authority analysis with invalid URL."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        result = await analyze_domain_authority(mock_ctx, "not-a-valid-url")

        assert isinstance(result, DomainAnalysis)
        # Should handle parsing errors gracefully


class TestContentQualityTool:
    """Test content quality analysis tool."""

    @pytest.mark.asyncio
    async def test_analyze_content_quality_high_quality(self, test_dependencies):
        """Test content quality analysis for high-quality content."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        high_quality_content = """
        # Research Study: Quality Assessment in Digital Content

        ## Abstract
        This comprehensive study examines the methodologies for assessing
        digital content quality across multiple domains.

        ## Introduction
        Quality assessment has become increasingly important in the digital age.
        According to previous research (Smith et al., 2023), systematic approaches
        to content evaluation are essential for maintaining information standards.

        ## Methodology
        We conducted a systematic analysis of content elements:
        - Structural components evaluation
        - Citation pattern analysis
        - Readability assessment
        - Completeness scoring

        ## Results
        Statistical analysis revealed significant correlations between content
        structure and perceived quality (p < 0.05). The findings demonstrate
        that well-organized content with proper citations enhances credibility.

        ## Discussion
        The results support established theories in information science and
        provide practical frameworks for automated quality assessment.

        ## Conclusion
        Based on extensive analysis, we conclude that systematic quality
        assessment can reliably identify high-quality content sources.

        ## References
        [1] Smith, J., Brown, A., & Wilson, C. (2023). Digital content standards.
        [2] Johnson, M. et al. (2022). Information quality metrics.
        [3] https://example.com/research-paper-url
        """

        result = await analyze_content_quality(
            mock_ctx,
            high_quality_content,
            "Research Study: Quality Assessment in Digital Content"
        )

        assert isinstance(result, ContentAnalysis)
        assert result.word_count > 100
        assert result.structure_score >= 0.8
        assert result.citation_count >= 3
        assert result.readability_score >= 0.6
        assert result.completeness_score >= 0.7

    @pytest.mark.asyncio
    async def test_analyze_content_quality_low_quality(self, test_dependencies):
        """Test content quality analysis for low-quality content."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        low_quality_content = "short text no structure"

        result = await analyze_content_quality(mock_ctx, low_quality_content, "")

        assert isinstance(result, ContentAnalysis)
        assert result.word_count < 10
        assert result.structure_score <= 0.3
        assert result.citation_count == 0
        assert result.completeness_score <= 0.5

    @pytest.mark.asyncio
    async def test_analyze_content_quality_structured_content(self, test_dependencies):
        """Test content quality analysis for well-structured content."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        structured_content = """
        ## Main Topic

        This article discusses important concepts with proper organization.

        ### Key Points
        - First important point with details
        - Second point with supporting evidence
        - Third point with references [1]

        ### Analysis
        According to research findings (Author, 2023), these concepts
        are well-established in the field.

        ### Conclusion
        The evidence supports the main hypothesis presented.

        References:
        [1] Important study citation
        """

        result = await analyze_content_quality(
            mock_ctx,
            structured_content,
            "Well-Structured Article Title"
        )

        assert isinstance(result, ContentAnalysis)
        assert result.structure_score >= 0.7
        assert result.citation_count >= 1
        # Should detect headings, lists, and proper structure

    @pytest.mark.asyncio
    async def test_analyze_content_quality_empty_content(self, test_dependencies):
        """Test content quality analysis with empty content."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        result = await analyze_content_quality(mock_ctx, "", "")

        assert isinstance(result, ContentAnalysis)
        assert result.word_count == 0
        assert result.structure_score == 0.0
        assert result.readability_score == 0.0


class TestBiasAnalysisTool:
    """Test bias detection analysis tool."""

    @pytest.mark.asyncio
    async def test_analyze_bias_indicators_neutral_content(self, test_dependencies):
        """Test bias analysis for neutral, factual content."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        neutral_content = """
        According to research studies, systematic analysis reveals consistent
        patterns in data collection. The methodology follows established
        protocols and evidence suggests reliable outcomes.

        Statistical analysis found significant correlations in the dataset.
        Further research might provide additional insights into these findings.
        """

        result = await analyze_bias_indicators(
            mock_ctx,
            neutral_content,
            "Objective Research Analysis"
        )

        assert isinstance(result, BiasAnalysis)
        assert result.emotional_language_score <= 0.3
        assert result.neutrality_score >= 0.6
        assert result.perspective_diversity >= 0.5
        # Should have minimal bias indicators

    @pytest.mark.asyncio
    async def test_analyze_bias_indicators_biased_content(self, test_dependencies):
        """Test bias analysis for obviously biased content."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        biased_content = """
        This is absolutely shocking and outrageous! Everyone knows that this
        incredible discovery will definitely change everything forever.

        I believe this is clearly the most important breakthrough ever made.
        Obviously, all previous research was completely wrong and stupid.
        Nothing else matters compared to this amazing revelation.

        The ridiculous establishment always tries to hide the truth, but
        this brilliant analysis exposes their terrible lies.
        """

        result = await analyze_bias_indicators(
            mock_ctx,
            biased_content,
            "SHOCKING: Incredible Discovery Changes Everything!"
        )

        assert isinstance(result, BiasAnalysis)
        assert result.emotional_language_score >= 0.5
        assert result.absolute_terms_count >= 5
        assert result.neutrality_score <= 0.5
        assert len(result.bias_indicators) >= 2

    @pytest.mark.asyncio
    async def test_analyze_bias_indicators_opinion_content(self, test_dependencies):
        """Test bias analysis for opinion-heavy content."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        opinion_content = """
        I think this approach might be effective based on my experience.
        In my opinion, the results seem to indicate positive outcomes.
        I believe further investigation could be beneficial.

        The analysis appears to support the hypothesis, though I feel
        more data would strengthen the conclusions.
        """

        result = await analyze_bias_indicators(
            mock_ctx,
            opinion_content,
            "Personal Analysis of Results"
        )

        assert isinstance(result, BiasAnalysis)
        assert "opinion_heavy_content" in result.bias_indicators
        assert result.perspective_diversity <= 0.5

    @pytest.mark.asyncio
    async def test_analyze_bias_indicators_fact_based_content(self, test_dependencies):
        """Test bias analysis for fact-based content."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        fact_content = """
        According to the National Science Foundation, research shows
        significant improvements in methodology. Studies indicate consistent
        patterns across multiple datasets.

        Data reveals correlation coefficients of r=0.78 (p<0.001).
        Evidence suggests that systematic approaches yield reliable results.
        Analysis found statistically significant differences between groups.
        """

        result = await analyze_bias_indicators(
            mock_ctx,
            fact_content,
            "Scientific Analysis Results"
        )

        assert isinstance(result, BiasAnalysis)
        assert result.perspective_diversity >= 0.7
        assert result.neutrality_score >= 0.6
        # Should not have opinion-heavy flag

    @pytest.mark.asyncio
    async def test_analyze_bias_indicators_error_handling(self, test_dependencies):
        """Test bias analysis error handling."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Simulate error by passing invalid data that could cause exceptions
        result = await analyze_bias_indicators(mock_ctx, None, None)

        assert isinstance(result, BiasAnalysis)
        # Should return default values when errors occur


class TestFreshnessTool:
    """Test content freshness analysis tool."""

    @pytest.mark.asyncio
    async def test_check_freshness_recent_content(self, test_dependencies):
        """Test freshness check for recent content."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Content extracted 2 days ago
        extraction_time = datetime.now() - timedelta(days=2)
        metadata = {
            "published_date": "2023-12-15",
            "last_modified": "2023-12-16"
        }

        result = await check_freshness(mock_ctx, extraction_time, metadata)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        assert result >= 0.8  # Should be high for recent content

    @pytest.mark.asyncio
    async def test_check_freshness_old_content(self, test_dependencies):
        """Test freshness check for old content."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Content extracted and published over 2 years ago
        extraction_time = datetime.now() - timedelta(days=800)
        metadata = {
            "published_date": "2020-01-01"
        }

        result = await check_freshness(mock_ctx, extraction_time, metadata)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        assert result <= 0.3  # Should be low for old content

    @pytest.mark.asyncio
    async def test_check_freshness_no_metadata(self, test_dependencies):
        """Test freshness check with no publication metadata."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Recent extraction but no publication date
        extraction_time = datetime.now() - timedelta(hours=6)
        metadata = {}

        result = await check_freshness(mock_ctx, extraction_time, metadata)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        # Should use extraction time and score highly for recent

    @pytest.mark.asyncio
    async def test_check_freshness_various_timeframes(self, test_dependencies):
        """Test freshness scoring across different timeframes."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        test_cases = [
            (timedelta(days=1), 1.0),      # 1 day: perfect score
            (timedelta(days=15), 0.9),     # 2 weeks: high score
            (timedelta(days=60), 0.8),     # 2 months: good score
            (timedelta(days=200), 0.6),    # 7 months: moderate score
            (timedelta(days=500), 0.4),    # 1.4 years: low score
            (timedelta(days=1000), 0.2)    # 2.7 years: very low score
        ]

        for age, expected_min_score in test_cases:
            extraction_time = datetime.now() - age
            metadata = {}

            result = await check_freshness(mock_ctx, extraction_time, metadata)

            assert isinstance(result, float)
            assert 0.0 <= result <= 1.0
            # Allow some tolerance in scoring
            assert result >= expected_min_score - 0.1

    @pytest.mark.asyncio
    async def test_check_freshness_date_parsing(self, test_dependencies):
        """Test freshness check with various date formats."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        extraction_time = datetime.now()

        date_formats = [
            "2023-12-15",
            "2023-12-15 14:30:00",
            "2023/12/15",
            "15/12/2023"
        ]

        for date_format in date_formats:
            metadata = {"published_date": date_format}

            result = await check_freshness(mock_ctx, extraction_time, metadata)

            assert isinstance(result, float)
            assert 0.0 <= result <= 1.0
            # Should successfully parse most common formats

    @pytest.mark.asyncio
    async def test_check_freshness_error_handling(self, test_dependencies):
        """Test freshness check error handling."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Test with invalid data that might cause errors
        extraction_time = "invalid_timestamp"
        metadata = {"published_date": "invalid_date"}

        result = await check_freshness(mock_ctx, extraction_time, metadata)

        assert isinstance(result, float)
        assert result == 0.5  # Should return default value on error


class TestToolIntegration:
    """Test tool integration with agent context."""

    @pytest.mark.asyncio
    async def test_tools_with_real_dependencies(self, test_dependencies):
        """Test tools work with actual dependencies."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Test each tool can be called without errors
        domain_result = await analyze_domain_authority(mock_ctx, "https://example.com")
        assert isinstance(domain_result, DomainAnalysis)

        content_result = await analyze_content_quality(mock_ctx, "Test content", "Test title")
        assert isinstance(content_result, ContentAnalysis)

        bias_result = await analyze_bias_indicators(mock_ctx, "Test content", "Test title")
        assert isinstance(bias_result, BiasAnalysis)

        freshness_result = await check_freshness(mock_ctx, datetime.now(), {})
        assert isinstance(freshness_result, float)

    @pytest.mark.asyncio
    async def test_tool_error_resilience(self, test_dependencies):
        """Test that tools handle errors gracefully."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Test tools with problematic inputs
        error_inputs = [
            (None, ""),
            ("", None),
            ("very long content " * 1000, "very long title " * 100),
        ]

        for content, title in error_inputs:
            # Tools should not raise exceptions
            try:
                domain_result = await analyze_domain_authority(mock_ctx, content)
                content_result = await analyze_content_quality(mock_ctx, content or "", title or "")
                bias_result = await analyze_bias_indicators(mock_ctx, content or "", title or "")

                # All should return valid results even with bad inputs
                assert isinstance(domain_result, DomainAnalysis)
                assert isinstance(content_result, ContentAnalysis)
                assert isinstance(bias_result, BiasAnalysis)

            except Exception as e:
                pytest.fail(f"Tool raised exception with inputs ({content}, {title}): {e}")

    @pytest.mark.asyncio
    async def test_tool_performance_boundaries(self, test_dependencies):
        """Test tool performance with edge cases."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Test with minimal content
        minimal_result = await analyze_content_quality(mock_ctx, "a", "b")
        assert isinstance(minimal_result, ContentAnalysis)
        assert minimal_result.word_count == 1

        # Test with very large content (should handle gracefully)
        large_content = "word " * 10000  # 10k words
        large_result = await analyze_content_quality(mock_ctx, large_content, "Large content test")
        assert isinstance(large_result, ContentAnalysis)
        assert large_result.word_count == 10000

        # Test with special characters and unicode
        special_content = "Test with émojis 🎉 and spéciàl characters üñíçødé"
        special_result = await analyze_content_quality(mock_ctx, special_content, "Special chars")
        assert isinstance(special_result, ContentAnalysis)
        assert special_result.word_count > 0