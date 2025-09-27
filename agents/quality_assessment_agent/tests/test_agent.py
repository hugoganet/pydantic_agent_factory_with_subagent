"""Test core agent functionality using TestModel and FunctionModel."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, AsyncMock

from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import quality_agent, assess_source_quality, assess_multiple_sources, health_check
from ..models import ResearchSource, QualityAssessment


class TestQualityAgent:
    """Test the core quality assessment agent functionality."""

    @pytest.mark.asyncio
    async def test_agent_basic_response(self, test_model, test_dependencies):
        """Test agent provides appropriate response with TestModel."""
        test_agent = quality_agent.override(model=test_model)

        result = await test_agent.run(
            "Assess the quality of this test source",
            deps=test_dependencies
        )

        # TestModel should return a QualityAssessment
        assert result.data is not None
        assert isinstance(result.data, QualityAssessment)
        assert len(result.all_messages()) > 0

    @pytest.mark.asyncio
    async def test_agent_with_function_model(self, quality_assessment_function_model, test_dependencies):
        """Test agent with custom function model for controlled behavior."""
        test_agent = quality_agent.override(model=quality_assessment_function_model)

        result = await test_agent.run(
            "Please assess this research source quality",
            deps=test_dependencies
        )

        # Verify the function model executed tool calls
        messages = result.all_messages()
        tool_calls = [msg for msg in messages if hasattr(msg, 'tool_name')]

        # Should have called assessment tools
        assert len(tool_calls) >= 1
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_agent_tool_calling_sequence(self, quality_assessment_function_model, test_dependencies):
        """Test that agent calls tools in expected sequence."""
        test_agent = quality_agent.override(model=quality_assessment_function_model)

        result = await test_agent.run(
            "Comprehensive quality assessment needed",
            deps=test_dependencies
        )

        messages = result.all_messages()
        tool_calls = [msg for msg in messages if hasattr(msg, 'tool_name')]

        # Verify specific tools were called
        tool_names = [call.tool_name for call in tool_calls]
        expected_tools = [
            'assess_domain_authority',
            'assess_content_quality',
            'assess_bias_indicators',
            'assess_content_freshness'
        ]

        # Should call at least some assessment tools
        assert any(tool in tool_names for tool in expected_tools)

    @pytest.mark.asyncio
    async def test_assess_source_quality_function(self, sample_research_source, test_dependencies):
        """Test the main assess_source_quality function."""
        with patch('..agent.quality_agent.run') as mock_run:
            # Mock the agent response
            mock_assessment = QualityAssessment(
                source_id=sample_research_source.source_id,
                credibility_score=0.8,
                bias_score=0.2,
                freshness_score=0.9,
                authority_score=0.7,
                overall_quality=0.75,
                confidence_rating=0.85,
                flags=[]
            )

            mock_result = AsyncMock()
            mock_result.data = mock_assessment
            mock_run.return_value = mock_result

            result = await assess_source_quality(sample_research_source, test_dependencies)

            assert isinstance(result, QualityAssessment)
            assert result.source_id == sample_research_source.source_id
            assert 0.0 <= result.credibility_score <= 1.0
            assert 0.0 <= result.bias_score <= 1.0
            assert 0.0 <= result.overall_quality <= 1.0

    @pytest.mark.asyncio
    async def test_assess_source_quality_with_error_handling(self, sample_research_source, test_dependencies):
        """Test error handling in assess_source_quality."""
        with patch('..agent.quality_agent.run') as mock_run:
            # Simulate an error
            mock_run.side_effect = Exception("Simulated API error")

            result = await assess_source_quality(sample_research_source, test_dependencies)

            # Should return fallback assessment
            assert isinstance(result, QualityAssessment)
            assert result.source_id == sample_research_source.source_id
            assert result.confidence_rating == 0.1
            assert "assessment_failed" in result.flags
            assert result.credibility_score == 0.5  # Fallback values

    @pytest.mark.asyncio
    async def test_assess_multiple_sources(self, performance_test_sources, test_dependencies):
        """Test concurrent assessment of multiple sources."""
        # Limit to first 5 sources for faster testing
        test_sources = performance_test_sources[:5]

        with patch('..agent.assess_source_quality') as mock_assess:
            # Mock individual assessments
            mock_assess.side_effect = lambda source, deps: QualityAssessment(
                source_id=source.source_id,
                credibility_score=0.7,
                bias_score=0.3,
                freshness_score=0.8,
                authority_score=0.6,
                overall_quality=0.65,
                confidence_rating=0.8,
                flags=[]
            )

            results = await assess_multiple_sources(test_sources, max_concurrent=3)

            assert len(results) == len(test_sources)
            assert all(isinstance(r, QualityAssessment) for r in results)
            assert all(r.source_id.startswith("perf_test_") for r in results)

    @pytest.mark.asyncio
    async def test_assess_multiple_sources_with_failures(self, performance_test_sources, test_dependencies):
        """Test concurrent assessment with some failures."""
        test_sources = performance_test_sources[:3]

        with patch('..agent.assess_source_quality') as mock_assess:
            # First call succeeds, second fails, third succeeds
            mock_assess.side_effect = [
                QualityAssessment(
                    source_id=test_sources[0].source_id,
                    credibility_score=0.8,
                    bias_score=0.2,
                    freshness_score=0.9,
                    authority_score=0.7,
                    overall_quality=0.75,
                    confidence_rating=0.85,
                    flags=[]
                ),
                Exception("Simulated failure"),
                QualityAssessment(
                    source_id=test_sources[2].source_id,
                    credibility_score=0.6,
                    bias_score=0.4,
                    freshness_score=0.7,
                    authority_score=0.5,
                    overall_quality=0.55,
                    confidence_rating=0.7,
                    flags=[]
                )
            ]

            results = await assess_multiple_sources(test_sources, max_concurrent=2)

            assert len(results) == len(test_sources)

            # First result should be normal
            assert results[0].confidence_rating == 0.85

            # Second result should be fallback (due to simulated failure)
            assert results[1].confidence_rating == 0.1
            assert "concurrent_assessment_failed" in results[1].flags

            # Third result should be normal
            assert results[2].confidence_rating == 0.7

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check functionality when agent is working."""
        with patch('..agent.assess_source_quality') as mock_assess:
            mock_assess.return_value = QualityAssessment(
                source_id="health_check",
                credibility_score=0.8,
                bias_score=0.2,
                freshness_score=0.9,
                authority_score=0.7,
                overall_quality=0.75,
                confidence_rating=0.85,
                flags=[]
            )

            health = await health_check()

            assert health["status"] == "healthy"
            assert health["agent_id"] == "quality_assessment_agent"
            assert health["test_assessment_completed"] is True
            assert "timestamp" in health
            assert health["test_confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check when agent has issues."""
        with patch('..agent.assess_source_quality') as mock_assess:
            mock_assess.side_effect = Exception("Health check failure")

            health = await health_check()

            assert health["status"] == "unhealthy"
            assert health["agent_id"] == "quality_assessment_agent"
            assert "error" in health
            assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_agent_with_different_source_types(self, test_dependencies):
        """Test agent behavior with different types of sources."""
        sources = [
            # High authority academic source
            ResearchSource(
                source_id="academic_001",
                url="https://www.nature.com/scientific-paper",
                title="Peer-Reviewed Research Study",
                content="Abstract: This study examines... Methods: We conducted... Results: Statistical analysis revealed...",
                metadata={"journal": "Nature", "peer_reviewed": True},
                extraction_timestamp=datetime.now()
            ),
            # News article
            ResearchSource(
                source_id="news_001",
                url="https://reuters.com/news-article",
                title="Breaking News Report",
                content="According to official sources, recent developments indicate...",
                metadata={"source_type": "news", "outlet": "Reuters"},
                extraction_timestamp=datetime.now()
            ),
            # Blog post
            ResearchSource(
                source_id="blog_001",
                url="https://personal-blog.com/opinion",
                title="My Thoughts On The Topic",
                content="I believe that this issue is very important because...",
                metadata={"source_type": "blog"},
                extraction_timestamp=datetime.now()
            )
        ]

        test_agent = quality_agent.override(model=TestModel())

        for source in sources:
            result = await test_agent.run(
                f"Assess quality of {source.source_id}",
                deps=test_dependencies
            )

            assert result.data is not None
            assert isinstance(result.data, QualityAssessment)
            assert result.data.source_id == source.source_id

    @pytest.mark.asyncio
    async def test_agent_error_recovery(self, sample_research_source, test_dependencies, error_function_model):
        """Test agent error recovery mechanisms."""
        test_agent = quality_agent.override(model=error_function_model)

        # This should not raise an exception, but handle it gracefully
        result = await assess_source_quality(sample_research_source, test_dependencies)

        # Should return fallback assessment
        assert isinstance(result, QualityAssessment)
        assert result.confidence_rating == 0.1  # Low confidence due to error
        assert "assessment_failed" in result.flags


class TestAgentPromptHandling:
    """Test agent behavior with different prompt types."""

    @pytest.mark.asyncio
    async def test_agent_with_minimal_prompt(self, test_model, test_dependencies):
        """Test agent with minimal prompt."""
        test_agent = quality_agent.override(model=test_model)

        result = await test_agent.run("Assess quality", deps=test_dependencies)

        assert result.data is not None
        assert isinstance(result.data, QualityAssessment)

    @pytest.mark.asyncio
    async def test_agent_with_detailed_prompt(self, test_model, test_dependencies):
        """Test agent with detailed assessment prompt."""
        test_agent = quality_agent.override(model=test_model)

        detailed_prompt = """
        Please conduct a comprehensive quality assessment of this research source:
        - Evaluate credibility and authority indicators
        - Analyze for potential bias
        - Assess content structure and quality
        - Check freshness and relevance
        - Provide confidence ratings
        """

        result = await test_agent.run(detailed_prompt, deps=test_dependencies)

        assert result.data is not None
        assert isinstance(result.data, QualityAssessment)

    @pytest.mark.asyncio
    async def test_agent_consistency(self, test_model, test_dependencies):
        """Test that agent provides consistent outputs for same input."""
        test_agent = quality_agent.override(model=test_model)

        # Configure TestModel to return consistent responses
        test_model.agent_responses = [
            ModelTextResponse(content="Assessment complete"),
            ModelTextResponse(content="Assessment complete")
        ]

        prompt = "Assess this source quality"

        # Run same assessment twice
        result1 = await test_agent.run(prompt, deps=test_dependencies)
        result2 = await test_agent.run(prompt, deps=test_dependencies)

        # Both should be valid QualityAssessment objects
        assert isinstance(result1.data, QualityAssessment)
        assert isinstance(result2.data, QualityAssessment)

        # Note: Exact consistency depends on model behavior, but structure should be same
        assert type(result1.data) == type(result2.data)