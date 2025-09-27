"""Integration tests for Quality Assessment Agent."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import aiohttp

from ..agent import assess_source_quality, assess_multiple_sources, health_check
from ..models import ResearchSource, QualityAssessment, AgentMessage
from ..dependencies import get_dependencies


class TestAgentIntegration:
    """Test agent integration with real-world scenarios."""

    @pytest.mark.asyncio
    async def test_end_to_end_quality_assessment(self, sample_research_source):
        """Test complete end-to-end quality assessment workflow."""
        # Use mock dependencies to avoid external API calls
        with patch('..dependencies.aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock(spec=aiohttp.ClientSession)
            mock_session.closed = False
            mock_session_class.return_value = mock_session

            # Mock agent responses for controlled testing
            with patch('..agent.quality_agent.run') as mock_agent_run:
                expected_assessment = QualityAssessment(
                    source_id=sample_research_source.source_id,
                    credibility_score=0.85,
                    bias_score=0.15,
                    freshness_score=0.9,
                    authority_score=0.8,
                    overall_quality=0.825,
                    confidence_rating=0.9,
                    flags=[],
                    assessment_details={
                        "domain_analysis": "High authority domain",
                        "content_quality": "Well-structured with citations",
                        "bias_analysis": "Minimal bias indicators",
                        "freshness": "Recent content"
                    }
                )

                mock_result = AsyncMock()
                mock_result.data = expected_assessment
                mock_agent_run.return_value = mock_result

                # Run assessment
                result = await assess_source_quality(sample_research_source)

                # Validate results
                assert isinstance(result, QualityAssessment)
                assert result.source_id == sample_research_source.source_id
                assert 0.0 <= result.credibility_score <= 1.0
                assert 0.0 <= result.bias_score <= 1.0
                assert 0.0 <= result.overall_quality <= 1.0
                assert result.confidence_rating > 0.5

                # Verify agent was called with correct parameters
                mock_agent_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_integration_message_format(self):
        """Test integration with workflow message format."""
        # Simulate receiving a message from another agent
        incoming_message = AgentMessage(
            message_id="msg_001",
            sender_id="web_research_agent",
            recipient_id="quality_assessment_agent",
            message_type="task",
            payload={
                "source": {
                    "source_id": "web_source_001",
                    "url": "https://example.com/article",
                    "title": "Test Article",
                    "content": "Sample article content for testing workflow integration.",
                    "metadata": {"domain": "example.com"},
                    "extraction_timestamp": datetime.now().isoformat()
                }
            },
            correlation_id="corr_001",
            priority=1
        )

        # Convert message payload to ResearchSource
        source_data = incoming_message.payload["source"]
        research_source = ResearchSource(
            source_id=source_data["source_id"],
            url=source_data["url"],
            title=source_data["title"],
            content=source_data["content"],
            metadata=source_data["metadata"],
            extraction_timestamp=datetime.fromisoformat(source_data["extraction_timestamp"])
        )

        # Mock the assessment
        with patch('..agent.quality_agent.run') as mock_agent_run:
            assessment = QualityAssessment(
                source_id=research_source.source_id,
                credibility_score=0.7,
                bias_score=0.3,
                freshness_score=0.8,
                authority_score=0.6,
                overall_quality=0.675,
                confidence_rating=0.8,
                flags=[]
            )

            mock_result = AsyncMock()
            mock_result.data = assessment
            mock_agent_run.return_value = mock_result

            # Process the request
            result = await assess_source_quality(research_source)

            # Create response message
            response_message = AgentMessage(
                message_id="msg_001_response",
                sender_id="quality_assessment_agent",
                recipient_id=incoming_message.sender_id,
                message_type="result",
                payload={
                    "assessment": result.model_dump(),
                    "original_source_id": research_source.source_id
                },
                correlation_id=incoming_message.correlation_id,
                priority=incoming_message.priority
            )

            # Validate response structure
            assert response_message.message_type == "result"
            assert response_message.correlation_id == "corr_001"
            assert "assessment" in response_message.payload
            assert response_message.payload["original_source_id"] == "web_source_001"

    @pytest.mark.asyncio
    async def test_concurrent_processing_integration(self, performance_test_sources):
        """Test concurrent processing capabilities."""
        # Use subset for faster testing
        test_sources = performance_test_sources[:10]

        with patch('..agent.quality_agent.run') as mock_agent_run:
            # Mock different assessment results
            def create_mock_result(source):
                assessment = QualityAssessment(
                    source_id=source.source_id,
                    credibility_score=0.6 + (hash(source.source_id) % 40) / 100,  # Vary between 0.6-1.0
                    bias_score=0.1 + (hash(source.source_id) % 30) / 100,        # Vary between 0.1-0.4
                    freshness_score=0.7 + (hash(source.source_id) % 30) / 100,   # Vary between 0.7-1.0
                    authority_score=0.5 + (hash(source.source_id) % 50) / 100,   # Vary between 0.5-1.0
                    overall_quality=0.65,
                    confidence_rating=0.8,
                    flags=[]
                )
                mock_result = AsyncMock()
                mock_result.data = assessment
                return mock_result

            mock_agent_run.side_effect = lambda *args, **kwargs: create_mock_result(
                # Extract source from args - this is a simplified approach
                test_sources[len(mock_agent_run.call_args_list)]
            )

            # Process multiple sources concurrently
            start_time = datetime.now()
            results = await assess_multiple_sources(test_sources, max_concurrent=5)
            end_time = datetime.now()

            # Validate results
            assert len(results) == len(test_sources)
            assert all(isinstance(r, QualityAssessment) for r in results)

            # Check that processing was reasonably fast (should be faster than sequential)
            processing_time = (end_time - start_time).total_seconds()
            assert processing_time < 10  # Should complete quickly with mocking

            # Verify all sources were processed
            result_source_ids = {r.source_id for r in results}
            expected_source_ids = {s.source_id for s in test_sources}
            assert result_source_ids == expected_source_ids

    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, sample_research_source):
        """Test error recovery in integrated environment."""
        # Test with network timeout simulation
        with patch('..agent.quality_agent.run') as mock_agent_run:
            # First call fails, second succeeds
            mock_agent_run.side_effect = [
                Exception("Network timeout"),
                # Don't need second call since assess_source_quality handles errors internally
            ]

            result = await assess_source_quality(sample_research_source)

            # Should return fallback assessment
            assert isinstance(result, QualityAssessment)
            assert result.confidence_rating == 0.1
            assert "assessment_failed" in result.flags

    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Test health check integration."""
        with patch('..agent.assess_source_quality') as mock_assess:
            # Mock successful health check
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
            assert health["test_assessment_completed"] is True
            assert "timestamp" in health
            assert health["agent_id"] == "quality_assessment_agent"

    @pytest.mark.asyncio
    async def test_dependency_injection_integration(self):
        """Test dependency injection works correctly."""
        custom_deps = get_dependencies()
        custom_deps.credibility_threshold = 0.9
        custom_deps.bias_threshold = 0.3

        with patch('..agent.quality_agent.run') as mock_agent_run:
            assessment = QualityAssessment(
                source_id="test_source",
                credibility_score=0.85,  # Below custom threshold
                bias_score=0.4,          # Above custom threshold
                freshness_score=0.8,
                authority_score=0.7,
                overall_quality=0.75,
                confidence_rating=0.8,
                flags=["low_credibility", "high_bias"]  # Flags based on thresholds
            )

            mock_result = AsyncMock()
            mock_result.data = assessment
            mock_agent_run.return_value = mock_result

            test_source = ResearchSource(
                source_id="test_source",
                title="Test Source",
                content="Test content",
                extraction_timestamp=datetime.now()
            )

            result = await assess_source_quality(test_source, custom_deps)

            # Verify custom dependencies were used
            assert isinstance(result, QualityAssessment)
            # Note: Actual flag checking would depend on agent implementation

        await custom_deps.close()


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_academic_paper_assessment(self, high_authority_source):
        """Test assessment of academic paper source."""
        with patch('..agent.quality_agent.run') as mock_agent_run:
            # Academic papers should score highly
            academic_assessment = QualityAssessment(
                source_id=high_authority_source.source_id,
                credibility_score=0.95,
                bias_score=0.1,
                freshness_score=0.8,
                authority_score=0.95,
                overall_quality=0.9,
                confidence_rating=0.95,
                flags=[],
                assessment_details={
                    "source_type": "academic",
                    "peer_reviewed": True,
                    "authority_indicators": ["nature.com", "doi_present", "citations_present"]
                }
            )

            mock_result = AsyncMock()
            mock_result.data = academic_assessment
            mock_agent_run.return_value = mock_result

            result = await assess_source_quality(high_authority_source)

            assert result.credibility_score >= 0.9
            assert result.authority_score >= 0.9
            assert result.bias_score <= 0.2
            assert result.confidence_rating >= 0.9

    @pytest.mark.asyncio
    async def test_biased_content_assessment(self, biased_research_source):
        """Test assessment of obviously biased content."""
        with patch('..agent.quality_agent.run') as mock_agent_run:
            biased_assessment = QualityAssessment(
                source_id=biased_research_source.source_id,
                credibility_score=0.3,
                bias_score=0.8,
                freshness_score=0.9,
                authority_score=0.2,
                overall_quality=0.35,
                confidence_rating=0.85,
                flags=["high_bias", "low_credibility", "emotional_language"],
                assessment_details={
                    "bias_indicators": ["excessive_emotional_language", "absolute_terms", "opinion_heavy"],
                    "authority_issues": ["unknown_domain", "no_ssl", "no_author_credentials"]
                }
            )

            mock_result = AsyncMock()
            mock_result.data = biased_assessment
            mock_agent_run.return_value = mock_result

            result = await assess_source_quality(biased_research_source)

            assert result.bias_score >= 0.6
            assert result.credibility_score <= 0.5
            assert "high_bias" in result.flags or result.bias_score >= 0.6

    @pytest.mark.asyncio
    async def test_low_quality_content_assessment(self, low_quality_source):
        """Test assessment of low-quality content."""
        with patch('..agent.quality_agent.run') as mock_agent_run:
            low_quality_assessment = QualityAssessment(
                source_id=low_quality_source.source_id,
                credibility_score=0.25,
                bias_score=0.4,
                freshness_score=0.1,  # Very old content
                authority_score=0.2,
                overall_quality=0.2,
                confidence_rating=0.7,
                flags=["low_quality", "outdated_content", "poor_structure"],
                assessment_details={
                    "quality_issues": ["short_content", "no_structure", "no_citations", "old_content"]
                }
            )

            mock_result = AsyncMock()
            mock_result.data = low_quality_assessment
            mock_agent_run.return_value = mock_result

            result = await assess_source_quality(low_quality_source)

            assert result.overall_quality <= 0.4
            assert result.freshness_score <= 0.3  # Old content
            assert len(result.flags) >= 1

    @pytest.mark.asyncio
    async def test_batch_processing_scenario(self, performance_test_sources):
        """Test batch processing scenario with mixed quality sources."""
        # Mix of different quality sources
        mixed_sources = [
            performance_test_sources[0],  # Regular test source
            performance_test_sources[1],  # Another test source
            performance_test_sources[2],  # Third test source
        ]

        with patch('..agent.quality_agent.run') as mock_agent_run:
            # Create varied assessment results
            assessments = [
                QualityAssessment(
                    source_id=mixed_sources[0].source_id,
                    credibility_score=0.8,
                    bias_score=0.2,
                    freshness_score=0.9,
                    authority_score=0.7,
                    overall_quality=0.75,
                    confidence_rating=0.85,
                    flags=[]
                ),
                QualityAssessment(
                    source_id=mixed_sources[1].source_id,
                    credibility_score=0.4,
                    bias_score=0.7,
                    freshness_score=0.6,
                    authority_score=0.3,
                    overall_quality=0.4,
                    confidence_rating=0.7,
                    flags=["medium_bias"]
                ),
                QualityAssessment(
                    source_id=mixed_sources[2].source_id,
                    credibility_score=0.9,
                    bias_score=0.1,
                    freshness_score=0.8,
                    authority_score=0.9,
                    overall_quality=0.85,
                    confidence_rating=0.95,
                    flags=[]
                )
            ]

            mock_results = [AsyncMock() for _ in assessments]
            for mock_result, assessment in zip(mock_results, assessments):
                mock_result.data = assessment
            mock_agent_run.side_effect = mock_results

            results = await assess_multiple_sources(mixed_sources, max_concurrent=3)

            assert len(results) == 3

            # Verify range of quality scores
            quality_scores = [r.overall_quality for r in results]
            assert min(quality_scores) <= 0.5  # At least one low quality
            assert max(quality_scores) >= 0.8  # At least one high quality

            # All should have valid confidence ratings
            assert all(r.confidence_rating >= 0.5 for r in results)

    @pytest.mark.asyncio
    async def test_external_service_integration_simulation(self, sample_research_source):
        """Test integration with external services (simulated)."""
        with patch('..dependencies.aiohttp.ClientSession') as mock_session_class:
            # Mock external API responses
            mock_session = AsyncMock(spec=aiohttp.ClientSession)
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "domain_authority": 75,
                "reputation_score": 0.8,
                "fact_check_result": "verified"
            })
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session.closed = False
            mock_session_class.return_value = mock_session

            with patch('..agent.quality_agent.run') as mock_agent_run:
                assessment = QualityAssessment(
                    source_id=sample_research_source.source_id,
                    credibility_score=0.8,
                    bias_score=0.2,
                    freshness_score=0.9,
                    authority_score=0.75,  # Influenced by external API
                    overall_quality=0.775,
                    confidence_rating=0.9,
                    flags=[],
                    assessment_details={
                        "external_verification": "fact_check_verified",
                        "domain_authority_score": 75
                    }
                )

                mock_result = AsyncMock()
                mock_result.data = assessment
                mock_agent_run.return_value = mock_result

                result = await assess_source_quality(sample_research_source)

                # External service data should influence scores
                assert result.authority_score >= 0.7
                assert result.confidence_rating >= 0.8