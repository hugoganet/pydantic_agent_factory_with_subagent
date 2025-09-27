"""Error handling and resilience tests for Quality Assessment Agent."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import aiohttp

from ..agent import assess_source_quality, assess_multiple_sources, health_check
from ..models import ResearchSource, QualityAssessment
from ..dependencies import QualityAssessmentDependencies, get_dependencies
from ..tools import analyze_domain_authority, analyze_content_quality, analyze_bias_indicators, check_freshness


class TestAgentErrorHandling:
    """Test agent-level error handling and recovery."""

    @pytest.mark.asyncio
    async def test_agent_api_timeout_handling(self, sample_research_source):
        """Test handling of LLM API timeouts."""
        with patch('..agent.quality_agent.run') as mock_agent_run:
            # Simulate API timeout
            mock_agent_run.side_effect = asyncio.TimeoutError("API timeout")

            result = await assess_source_quality(sample_research_source)

            # Should return fallback assessment
            assert isinstance(result, QualityAssessment)
            assert result.source_id == sample_research_source.source_id
            assert result.confidence_rating == 0.1
            assert "assessment_failed" in result.flags

    @pytest.mark.asyncio
    async def test_agent_api_error_handling(self, sample_research_source):
        """Test handling of LLM API errors."""
        with patch('..agent.quality_agent.run') as mock_agent_run:
            # Simulate various API errors
            api_errors = [
                Exception("API rate limit exceeded"),
                ValueError("Invalid API key"),
                ConnectionError("Network connection failed"),
                Exception("Model temporarily unavailable")
            ]

            for error in api_errors:
                mock_agent_run.side_effect = error

                result = await assess_source_quality(sample_research_source)

                # Should handle all errors gracefully
                assert isinstance(result, QualityAssessment)
                assert result.confidence_rating == 0.1
                assert "assessment_failed" in result.flags
                assert result.credibility_score == 0.5  # Fallback values

    @pytest.mark.asyncio
    async def test_agent_invalid_response_handling(self, sample_research_source):
        """Test handling of invalid agent responses."""
        with patch('..agent.quality_agent.run') as mock_agent_run:
            # Mock invalid response structures
            invalid_responses = [
                Mock(data=None),
                Mock(data="invalid_string_instead_of_object"),
                Mock(data={"invalid": "structure"}),
            ]

            for invalid_response in invalid_responses:
                mock_agent_run.return_value = invalid_response

                result = await assess_source_quality(sample_research_source)

                # Should handle invalid responses gracefully
                assert isinstance(result, QualityAssessment)
                assert result.confidence_rating == 0.1

    @pytest.mark.asyncio
    async def test_concurrent_processing_partial_failures(self, performance_test_sources):
        """Test concurrent processing with partial failures."""
        test_sources = performance_test_sources[:5]

        with patch('..agent.quality_agent.run') as mock_agent_run:
            # Setup mixed success/failure pattern
            responses = []
            for i, source in enumerate(test_sources):
                if i % 2 == 0:
                    # Success case
                    assessment = QualityAssessment(
                        source_id=source.source_id,
                        credibility_score=0.8,
                        bias_score=0.2,
                        freshness_score=0.9,
                        authority_score=0.7,
                        overall_quality=0.75,
                        confidence_rating=0.85,
                        flags=[]
                    )
                    mock_result = AsyncMock()
                    mock_result.data = assessment
                    responses.append(mock_result)
                else:
                    # Failure case
                    responses.append(Exception(f"Simulated failure for source {i}"))

            mock_agent_run.side_effect = responses

            results = await assess_multiple_sources(test_sources, max_concurrent=3)

            # Should handle all sources despite partial failures
            assert len(results) == len(test_sources)
            assert all(isinstance(r, QualityAssessment) for r in results)

            # Check mix of successful and fallback assessments
            high_confidence = [r for r in results if r.confidence_rating > 0.5]
            low_confidence = [r for r in results if r.confidence_rating <= 0.2]

            assert len(high_confidence) >= 2  # Some successes
            assert len(low_confidence) >= 2   # Some fallbacks

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, performance_test_sources):
        """Test handling of memory pressure scenarios."""
        # Simulate large batch that might cause memory issues
        large_batch = performance_test_sources * 2  # 40 sources

        with patch('..agent.quality_agent.run') as mock_agent_run:
            call_count = 0

            async def mock_with_memory_pressure(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                # Simulate memory issues on every 10th call
                if call_count % 10 == 0:
                    raise MemoryError("Simulated memory pressure")

                assessment = QualityAssessment(
                    source_id=f"memory_test_{call_count}",
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
                return mock_result

            mock_agent_run.side_effect = mock_with_memory_pressure

            # Process in smaller batches to handle memory pressure
            batch_size = 10
            all_results = []

            for i in range(0, len(large_batch), batch_size):
                batch = large_batch[i:i + batch_size]
                try:
                    batch_results = await assess_multiple_sources(batch, max_concurrent=5)
                    all_results.extend(batch_results)
                except Exception as e:
                    # Should handle memory errors gracefully
                    pytest.fail(f"Batch processing failed under memory pressure: {e}")

            # Should complete all processing despite memory pressure
            assert len(all_results) == len(large_batch)

    @pytest.mark.asyncio
    async def test_dependency_failure_recovery(self, sample_research_source):
        """Test recovery from dependency failures."""
        # Test with dependency initialization failure
        with patch('..dependencies.get_dependencies') as mock_get_deps:
            mock_get_deps.side_effect = Exception("Dependency initialization failed")

            result = await assess_source_quality(sample_research_source)

            # Should still complete with fallback
            assert isinstance(result, QualityAssessment)
            assert result.confidence_rating == 0.1

    @pytest.mark.asyncio
    async def test_health_check_error_scenarios(self):
        """Test health check under various error conditions."""
        # Test health check with assessment failure
        with patch('..agent.assess_source_quality') as mock_assess:
            mock_assess.side_effect = Exception("Health check assessment failed")

            health = await health_check()

            assert health["status"] == "unhealthy"
            assert "error" in health
            assert health["agent_id"] == "quality_assessment_agent"

        # Test health check with dependency failure
        with patch('..dependencies.get_dependencies') as mock_get_deps:
            mock_get_deps.side_effect = Exception("Dependencies unavailable")

            health = await health_check()

            assert health["status"] == "unhealthy"
            assert "error" in health


class TestToolErrorHandling:
    """Test error handling in individual tools."""

    @pytest.mark.asyncio
    async def test_domain_authority_tool_errors(self, test_dependencies):
        """Test domain authority tool error handling."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Test with invalid URLs
        invalid_urls = [
            "not-a-url",
            "ftp://invalid-protocol.com",
            "://malformed-url",
            None,
            "",
            "javascript:alert('xss')",
        ]

        for invalid_url in invalid_urls:
            result = await analyze_domain_authority(mock_ctx, invalid_url)

            # Should handle all invalid URLs gracefully
            assert hasattr(result, 'domain')
            assert hasattr(result, 'reputation_score')
            # Should not raise exceptions

    @pytest.mark.asyncio
    async def test_content_quality_tool_errors(self, test_dependencies):
        """Test content quality tool error handling."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Test with problematic content
        problematic_inputs = [
            (None, None),
            ("", ""),
            ("\x00\x01\x02", "binary_data"),  # Binary data
            ("a" * 1000000, "huge_title" * 1000),  # Extremely large content
            ("unicode_test: éñ¿¡°", "título_con_acentos"),  # Unicode edge cases
        ]

        for content, title in problematic_inputs:
            try:
                result = await analyze_content_quality(mock_ctx, content or "", title or "")

                # Should return valid ContentAnalysis object
                assert hasattr(result, 'word_count')
                assert hasattr(result, 'structure_score')
                assert 0 <= result.structure_score <= 1

            except Exception as e:
                pytest.fail(f"Content quality tool failed with inputs ({content}, {title}): {e}")

    @pytest.mark.asyncio
    async def test_bias_analysis_tool_errors(self, test_dependencies):
        """Test bias analysis tool error handling."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Test with edge case content
        edge_cases = [
            ("", ""),  # Empty content
            ("a", "b"),  # Minimal content
            ("🎉" * 1000, "😀" * 100),  # Emoji-heavy content
            ("ALLCAPSTEXT", "ALLCAPSTITLE"),  # All caps
            ("mixed\nline\rbreaks\r\n", "title"),  # Mixed line endings
        ]

        for content, title in edge_cases:
            result = await analyze_bias_indicators(mock_ctx, content, title)

            # Should return valid BiasAnalysis object
            assert hasattr(result, 'emotional_language_score')
            assert hasattr(result, 'neutrality_score')
            assert 0 <= result.neutrality_score <= 1
            assert isinstance(result.bias_indicators, list)

    @pytest.mark.asyncio
    async def test_freshness_tool_errors(self, test_dependencies):
        """Test freshness assessment tool error handling."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Test with invalid timestamps and metadata
        invalid_inputs = [
            (None, {}),
            ("invalid_timestamp", {"published_date": "invalid_date"}),
            (datetime.now(), {"published_date": None}),
            (datetime.now(), {"published_date": "2023-13-45"}),  # Invalid date
            (datetime.now(), {"published_date": "not_a_date"}),
        ]

        for timestamp, metadata in invalid_inputs:
            result = await check_freshness(mock_ctx, timestamp, metadata)

            # Should return valid float score
            assert isinstance(result, float)
            assert 0.0 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_tool_timeout_handling(self, test_dependencies):
        """Test tool behavior under timeout conditions."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Simulate tools with various processing delays
        with patch('asyncio.sleep') as mock_sleep:
            # Test with normal delay
            mock_sleep.return_value = None

            result = await analyze_content_quality(mock_ctx, "test content", "test title")
            assert hasattr(result, 'word_count')

            # Test with timeout simulation
            mock_sleep.side_effect = asyncio.TimeoutError("Tool timeout")

            try:
                result = await analyze_content_quality(mock_ctx, "test content", "test title")
                # Should still complete with default values
                assert hasattr(result, 'word_count')
            except asyncio.TimeoutError:
                # If timeout propagates, that's also acceptable behavior
                pass


class TestExternalServiceErrorHandling:
    """Test error handling for external service interactions."""

    @pytest.mark.asyncio
    async def test_http_session_errors(self, test_dependencies):
        """Test handling of HTTP session errors."""
        # Mock HTTP session with various errors
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        test_dependencies.http_session = mock_session

        # Test connection errors
        mock_session.get.side_effect = aiohttp.ClientConnectionError("Connection failed")

        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Tools should handle connection errors gracefully
        result = await analyze_domain_authority(mock_ctx, "https://example.com")
        assert hasattr(result, 'domain')

    @pytest.mark.asyncio
    async def test_api_key_errors(self):
        """Test handling of invalid API keys."""
        # Test with invalid fact-check API key
        invalid_deps = QualityAssessmentDependencies(
            fact_check_api_key="invalid_key"
        )

        mock_ctx = Mock()
        mock_ctx.deps = invalid_deps

        # Should handle API key errors gracefully
        result = await analyze_domain_authority(mock_ctx, "https://example.com")
        assert hasattr(result, 'domain')

    @pytest.mark.asyncio
    async def test_service_unavailable_handling(self, test_dependencies):
        """Test handling of service unavailability."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_response = AsyncMock()
        mock_response.status = 503  # Service unavailable
        mock_session.get.return_value.__aenter__.return_value = mock_response

        test_dependencies.http_session = mock_session

        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Should handle service unavailability
        result = await analyze_domain_authority(mock_ctx, "https://example.com")
        assert hasattr(result, 'domain')

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, test_dependencies):
        """Test handling of malformed external API responses."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.side_effect = ValueError("Invalid JSON response")
        mock_session.get.return_value.__aenter__.return_value = mock_response

        test_dependencies.http_session = mock_session

        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Should handle malformed responses
        result = await analyze_domain_authority(mock_ctx, "https://example.com")
        assert hasattr(result, 'domain')


class TestDataValidationErrors:
    """Test handling of data validation errors."""

    @pytest.mark.asyncio
    async def test_invalid_research_source_handling(self):
        """Test handling of invalid ResearchSource data."""
        # Test with missing required fields
        invalid_sources = [
            # Missing source_id
            {
                "title": "Test Title",
                "content": "Test content",
                "extraction_timestamp": datetime.now()
            },
            # Invalid timestamp
            {
                "source_id": "test_001",
                "title": "Test Title",
                "content": "Test content",
                "extraction_timestamp": "invalid_timestamp"
            }
        ]

        for invalid_data in invalid_sources:
            try:
                # Should either create valid object or raise validation error
                if "source_id" in invalid_data:
                    source = ResearchSource(**invalid_data)
                    result = await assess_source_quality(source)
                    assert isinstance(result, QualityAssessment)
            except (ValueError, TypeError):
                # Validation errors are acceptable
                pass

    @pytest.mark.asyncio
    async def test_assessment_score_validation(self, sample_research_source):
        """Test validation of assessment scores."""
        with patch('..agent.quality_agent.run') as mock_agent_run:
            # Mock invalid assessment scores
            invalid_assessment = QualityAssessment(
                source_id=sample_research_source.source_id,
                credibility_score=1.5,  # Invalid: > 1.0
                bias_score=-0.1,        # Invalid: < 0.0
                freshness_score=2.0,    # Invalid: > 1.0
                authority_score=-1.0,   # Invalid: < 0.0
                overall_quality=1.1,    # Invalid: > 1.0
                confidence_rating=1.5,  # Invalid: > 1.0
                flags=[]
            )

            try:
                # Pydantic should validate scores
                assert 0.0 <= invalid_assessment.credibility_score <= 1.0
            except ValueError:
                # Validation error is expected behavior
                pass

    @pytest.mark.asyncio
    async def test_unicode_handling_errors(self, test_dependencies):
        """Test handling of Unicode and encoding errors."""
        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Test with various Unicode edge cases
        unicode_tests = [
            "Normal text with émojis 🎉 and accénts",
            "Mixed encoding: café naïve résumé",
            "Special characters: ™️ © ® ° ± ² ³",
            "Zero-width characters: \u200b\u200c\u200d",
            "Right-to-left: العربية עברית",
            "Surrogate pairs: 🌟💫⭐✨🎭🎪🎨🎬",
        ]

        for test_text in unicode_tests:
            try:
                result = await analyze_content_quality(mock_ctx, test_text, test_text[:20])
                assert hasattr(result, 'word_count')

                bias_result = await analyze_bias_indicators(mock_ctx, test_text, test_text[:20])
                assert hasattr(bias_result, 'neutrality_score')

            except UnicodeError as e:
                pytest.fail(f"Unicode handling failed for text '{test_text}': {e}")


class TestErrorRecoveryPatterns:
    """Test error recovery and resilience patterns."""

    @pytest.mark.asyncio
    async def test_retry_mechanism_simulation(self, sample_research_source):
        """Test retry-like behavior for transient failures."""
        with patch('..agent.quality_agent.run') as mock_agent_run:
            call_count = 0

            def mock_with_transient_failure(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First call fails
                    raise Exception("Transient failure")
                else:
                    # Subsequent calls succeed
                    assessment = QualityAssessment(
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
                    mock_result.data = assessment
                    return mock_result

            mock_agent_run.side_effect = mock_with_transient_failure

            # First call should return fallback due to failure
            result = await assess_source_quality(sample_research_source)
            assert result.confidence_rating == 0.1  # Fallback assessment

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, sample_research_source):
        """Test graceful degradation under various failure modes."""
        failure_modes = [
            "API timeout",
            "Rate limit exceeded",
            "Invalid response format",
            "Network connection error",
            "Authentication failure"
        ]

        for failure_mode in failure_modes:
            with patch('..agent.quality_agent.run') as mock_agent_run:
                mock_agent_run.side_effect = Exception(failure_mode)

                result = await assess_source_quality(sample_research_source)

                # Should always provide some assessment
                assert isinstance(result, QualityAssessment)
                assert result.source_id == sample_research_source.source_id

                # Degraded quality indicators
                assert result.confidence_rating <= 0.2
                assert "assessment_failed" in result.flags

                # Should provide reasonable fallback scores
                assert 0.0 <= result.credibility_score <= 1.0
                assert 0.0 <= result.overall_quality <= 1.0

    @pytest.mark.asyncio
    async def test_cascading_failure_prevention(self, performance_test_sources):
        """Test prevention of cascading failures in batch processing."""
        test_sources = performance_test_sources[:8]

        with patch('..agent.quality_agent.run') as mock_agent_run:
            call_count = 0

            def mock_with_cascading_risk(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                # Simulate cascading failure pattern
                if call_count <= 3:
                    # First few calls succeed
                    assessment = QualityAssessment(
                        source_id=f"cascade_test_{call_count}",
                        credibility_score=0.8,
                        bias_score=0.2,
                        freshness_score=0.9,
                        authority_score=0.7,
                        overall_quality=0.75,
                        confidence_rating=0.85,
                        flags=[]
                    )
                    mock_result = AsyncMock()
                    mock_result.data = assessment
                    return mock_result
                elif call_count <= 6:
                    # Middle calls fail (could trigger cascade)
                    raise Exception(f"Failure {call_count}")
                else:
                    # Later calls should still work (cascade prevented)
                    assessment = QualityAssessment(
                        source_id=f"cascade_test_{call_count}",
                        credibility_score=0.7,
                        bias_score=0.3,
                        freshness_score=0.8,
                        authority_score=0.6,
                        overall_quality=0.65,
                        confidence_rating=0.8,
                        flags=[]
                    )
                    mock_result = AsyncMock()
                    mock_result.data = assessment
                    return mock_result

            mock_agent_run.side_effect = mock_with_cascading_risk

            results = await assess_multiple_sources(test_sources, max_concurrent=4)

            # Should complete all assessments despite failures
            assert len(results) == len(test_sources)
            assert all(isinstance(r, QualityAssessment) for r in results)

            # Should have both successful and fallback assessments
            successful = [r for r in results if r.confidence_rating > 0.5]
            fallbacks = [r for r in results if r.confidence_rating <= 0.2]

            assert len(successful) >= 2  # Some succeeded
            assert len(fallbacks) >= 2   # Some failed gracefully