"""Performance tests for Quality Assessment Agent."""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from statistics import mean, median

from ..agent import assess_source_quality, assess_multiple_sources
from ..models import ResearchSource, QualityAssessment


class TestPerformanceRequirements:
    """Test performance requirements from INITIAL.md."""

    @pytest.mark.asyncio
    async def test_single_source_processing_time(self, sample_research_source):
        """Test that single source assessment completes within 30 seconds."""
        with patch('..agent.quality_agent.run') as mock_agent_run:
            # Simulate realistic processing time
            async def mock_run_with_delay(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate processing delay
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

            mock_agent_run.side_effect = mock_run_with_delay

            # Measure processing time
            start_time = time.time()
            result = await assess_source_quality(sample_research_source)
            end_time = time.time()

            processing_time = end_time - start_time

            # Should complete well within 30 seconds (requirement)
            assert processing_time < 30.0
            assert isinstance(result, QualityAssessment)
            print(f"Single source processing time: {processing_time:.3f} seconds")

    @pytest.mark.asyncio
    async def test_concurrent_processing_capacity(self, performance_test_sources):
        """Test concurrent processing of 10-20 sources."""
        # Test with 15 sources (within the 10-20 range requirement)
        test_sources = performance_test_sources[:15]

        with patch('..agent.quality_agent.run') as mock_agent_run:
            async def mock_assessment(*args, **kwargs):
                # Simulate realistic processing with variable delay
                await asyncio.sleep(0.05 + (time.time() % 0.1))  # 50-150ms delay
                source_id = args[0].split()[-1] if args else "unknown"
                assessment = QualityAssessment(
                    source_id=source_id,
                    credibility_score=0.6 + (time.time() % 0.4),
                    bias_score=0.1 + (time.time() % 0.3),
                    freshness_score=0.7 + (time.time() % 0.3),
                    authority_score=0.5 + (time.time() % 0.5),
                    overall_quality=0.65,
                    confidence_rating=0.8,
                    flags=[]
                )
                mock_result = AsyncMock()
                mock_result.data = assessment
                return mock_result

            mock_agent_run.side_effect = mock_assessment

            # Test concurrent processing
            start_time = time.time()
            results = await assess_multiple_sources(test_sources, max_concurrent=10)
            end_time = time.time()

            total_time = end_time - start_time

            # Validate results
            assert len(results) == len(test_sources)
            assert all(isinstance(r, QualityAssessment) for r in results)

            # Performance validation - should be faster than sequential processing
            # Sequential would be ~15 * 0.1s = 1.5s minimum, concurrent should be much faster
            assert total_time < 1.0  # Should complete in under 1 second with good concurrency

            # Verify throughput meets requirements (should handle 10-20 sources concurrently)
            throughput = len(test_sources) / total_time
            assert throughput >= 10  # Should process at least 10 sources per second

            print(f"Concurrent processing: {len(test_sources)} sources in {total_time:.3f}s (throughput: {throughput:.1f} sources/sec)")

    @pytest.mark.asyncio
    async def test_performance_with_varying_content_sizes(self):
        """Test performance with different content sizes."""
        # Create sources with varying content sizes
        content_sizes = [100, 1000, 5000, 10000, 50000]  # words
        test_sources = []

        for i, size in enumerate(content_sizes):
            content = "word " * size
            source = ResearchSource(
                source_id=f"size_test_{size}",
                url=f"https://example.com/article_{size}",
                title=f"Test Article {size} words",
                content=content,
                metadata={"word_count": size},
                extraction_timestamp=datetime.now()
            )
            test_sources.append(source)

        with patch('..agent.quality_agent.run') as mock_agent_run:
            processing_times = []

            async def mock_assessment_with_size_factor(*args, **kwargs):
                # Simulate processing time that scales slightly with content size
                content_factor = len(args[0]) / 10000 if args else 1  # Rough content size factor
                delay = 0.05 + min(content_factor * 0.01, 0.1)  # 50-150ms based on size
                await asyncio.sleep(delay)

                assessment = QualityAssessment(
                    source_id="test_source",
                    credibility_score=0.75,
                    bias_score=0.25,
                    freshness_score=0.8,
                    authority_score=0.7,
                    overall_quality=0.725,
                    confidence_rating=0.85,
                    flags=[]
                )
                mock_result = AsyncMock()
                mock_result.data = assessment
                return mock_result

            mock_agent_run.side_effect = mock_assessment_with_size_factor

            # Test each content size
            for source in test_sources:
                start_time = time.time()
                result = await assess_source_quality(source)
                end_time = time.time()

                processing_time = end_time - start_time
                processing_times.append(processing_time)

                # Each should still complete within reasonable time
                assert processing_time < 5.0
                assert isinstance(result, QualityAssessment)

            # Processing times should not increase dramatically with content size
            min_time = min(processing_times)
            max_time = max(processing_times)
            time_ratio = max_time / min_time

            # Even largest content should not take more than 3x longer than smallest
            assert time_ratio < 3.0

            print(f"Processing times by content size: {list(zip(content_sizes, processing_times))}")

    @pytest.mark.asyncio
    async def test_memory_efficiency_with_large_batch(self, performance_test_sources):
        """Test memory efficiency with large batch processing."""
        # Use larger batch to test memory efficiency
        large_batch = performance_test_sources  # All 20 sources

        with patch('..agent.quality_agent.run') as mock_agent_run:
            async def mock_assessment(*args, **kwargs):
                await asyncio.sleep(0.01)  # Minimal delay
                assessment = QualityAssessment(
                    source_id="batch_test",
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

            mock_agent_run.side_effect = mock_assessment

            # Process in batches to test memory efficiency
            batch_size = 5
            all_results = []

            start_time = time.time()
            for i in range(0, len(large_batch), batch_size):
                batch = large_batch[i:i + batch_size]
                batch_results = await assess_multiple_sources(batch, max_concurrent=5)
                all_results.extend(batch_results)

            end_time = time.time()
            total_time = end_time - start_time

            # Validate all results
            assert len(all_results) == len(large_batch)
            assert all(isinstance(r, QualityAssessment) for r in all_results)

            # Should complete efficiently
            throughput = len(large_batch) / total_time
            assert throughput >= 50  # Should handle high throughput in batches

            print(f"Batch processing: {len(large_batch)} sources in {total_time:.3f}s (throughput: {throughput:.1f} sources/sec)")

    @pytest.mark.asyncio
    async def test_performance_degradation_resilience(self, performance_test_sources):
        """Test performance resilience under adverse conditions."""
        test_sources = performance_test_sources[:10]

        with patch('..agent.quality_agent.run') as mock_agent_run:
            call_count = 0
            processing_times = []

            async def mock_assessment_with_degradation(*args, **kwargs):
                nonlocal call_count
                call_count += 1

                # Simulate increasing delay to test resilience
                if call_count <= 3:
                    delay = 0.05  # Normal processing
                elif call_count <= 6:
                    delay = 0.15  # Slower processing
                else:
                    delay = 0.1   # Recovery

                start = time.time()
                await asyncio.sleep(delay)
                end = time.time()
                processing_times.append(end - start)

                assessment = QualityAssessment(
                    source_id=f"resilience_test_{call_count}",
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

            mock_agent_run.side_effect = mock_assessment_with_degradation

            # Process sources and measure performance consistency
            results = await assess_multiple_sources(test_sources, max_concurrent=3)

            # Validate results
            assert len(results) == len(test_sources)
            assert all(isinstance(r, QualityAssessment) for r in results)

            # Performance should remain reasonable even with degradation
            avg_time = mean(processing_times)
            max_time = max(processing_times)

            assert avg_time < 0.3  # Average should be reasonable
            assert max_time < 0.5  # Even worst case should be acceptable

            print(f"Performance under degradation - Avg: {avg_time:.3f}s, Max: {max_time:.3f}s")

    @pytest.mark.asyncio
    async def test_timeout_handling_performance(self, sample_research_source):
        """Test performance when timeouts occur."""
        timeout_scenarios = [
            0.1,   # Fast response
            1.0,   # Moderate response
            5.0,   # Slow response
            30.0,  # At timeout limit
        ]

        for timeout in timeout_scenarios:
            with patch('..agent.quality_agent.run') as mock_agent_run:
                async def mock_with_timeout(*args, **kwargs):
                    if timeout >= 30.0:
                        # Simulate timeout by raising exception
                        raise asyncio.TimeoutError("Processing timeout")

                    await asyncio.sleep(min(timeout, 0.1))  # Cap actual sleep for testing
                    assessment = QualityAssessment(
                        source_id=sample_research_source.source_id,
                        credibility_score=0.7,
                        bias_score=0.3,
                        freshness_score=0.8,
                        authority_score=0.6,
                        overall_quality=0.675,
                        confidence_rating=0.8 if timeout < 30.0 else 0.1,
                        flags=[] if timeout < 30.0 else ["timeout_occurred"]
                    )
                    mock_result = AsyncMock()
                    mock_result.data = assessment
                    return mock_result

                mock_agent_run.side_effect = mock_with_timeout

                start_time = time.time()
                result = await assess_source_quality(sample_research_source)
                end_time = time.time()

                actual_time = end_time - start_time

                # Should handle timeouts gracefully
                assert isinstance(result, QualityAssessment)

                if timeout >= 30.0:
                    # Timeout case should return fallback quickly
                    assert actual_time < 1.0
                    assert result.confidence_rating <= 0.2
                else:
                    # Normal cases should complete reasonably
                    assert actual_time < timeout + 1.0

                print(f"Timeout scenario {timeout}s: completed in {actual_time:.3f}s")


class TestScalabilityMetrics:
    """Test scalability and performance metrics."""

    @pytest.mark.asyncio
    async def test_throughput_measurement(self, performance_test_sources):
        """Measure actual throughput capabilities."""
        batch_sizes = [1, 5, 10, 15, 20]
        throughput_results = {}

        for batch_size in batch_sizes:
            test_sources = performance_test_sources[:batch_size]

            with patch('..agent.quality_agent.run') as mock_agent_run:
                async def mock_assessment(*args, **kwargs):
                    await asyncio.sleep(0.02)  # Consistent 20ms processing time
                    assessment = QualityAssessment(
                        source_id="throughput_test",
                        credibility_score=0.75,
                        bias_score=0.25,
                        freshness_score=0.8,
                        authority_score=0.7,
                        overall_quality=0.725,
                        confidence_rating=0.85,
                        flags=[]
                    )
                    mock_result = AsyncMock()
                    mock_result.data = assessment
                    return mock_result

                mock_agent_run.side_effect = mock_assessment

                # Measure throughput
                start_time = time.time()
                results = await assess_multiple_sources(test_sources, max_concurrent=min(batch_size, 10))
                end_time = time.time()

                processing_time = end_time - start_time
                throughput = batch_size / processing_time

                throughput_results[batch_size] = {
                    'throughput': throughput,
                    'time': processing_time,
                    'sources': batch_size
                }

                assert len(results) == batch_size
                print(f"Batch size {batch_size}: {throughput:.1f} sources/sec ({processing_time:.3f}s)")

        # Analyze scalability
        # Throughput should increase with batch size up to concurrency limit
        throughputs = [result['throughput'] for result in throughput_results.values()]

        # Should achieve reasonable throughput even with single source
        assert throughput_results[1]['throughput'] >= 10

        # Should scale up to at least 30 sources/sec with larger batches
        max_throughput = max(throughputs)
        assert max_throughput >= 30

    @pytest.mark.asyncio
    async def test_latency_distribution(self, performance_test_sources):
        """Test latency distribution for performance consistency."""
        test_sources = performance_test_sources[:10]
        latencies = []

        with patch('..agent.quality_agent.run') as mock_agent_run:
            async def mock_assessment_with_jitter(*args, **kwargs):
                # Add realistic jitter to processing time
                import random
                base_delay = 0.05
                jitter = random.uniform(-0.02, 0.02)  # ±20ms jitter
                delay = max(0.01, base_delay + jitter)

                start = time.time()
                await asyncio.sleep(delay)
                end = time.time()
                latencies.append(end - start)

                assessment = QualityAssessment(
                    source_id="latency_test",
                    credibility_score=0.75,
                    bias_score=0.25,
                    freshness_score=0.8,
                    authority_score=0.7,
                    overall_quality=0.725,
                    confidence_rating=0.85,
                    flags=[]
                )
                mock_result = AsyncMock()
                mock_result.data = assessment
                return mock_result

            mock_agent_run.side_effect = mock_assessment_with_jitter

            # Process sources and collect latency data
            results = await assess_multiple_sources(test_sources, max_concurrent=5)

            assert len(results) == len(test_sources)
            assert len(latencies) >= len(test_sources)

            # Analyze latency distribution
            avg_latency = mean(latencies)
            median_latency = median(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)

            # Performance requirements
            assert avg_latency < 0.2      # Average under 200ms
            assert median_latency < 0.15  # Median under 150ms
            assert max_latency < 0.5      # No outliers over 500ms

            # Consistency check - no extreme outliers
            latency_range = max_latency - min_latency
            assert latency_range < 0.3    # Range should be reasonable

            print(f"Latency stats - Avg: {avg_latency:.3f}s, Median: {median_latency:.3f}s, Range: {latency_range:.3f}s")

    @pytest.mark.asyncio
    async def test_error_rate_under_load(self, performance_test_sources):
        """Test error rate under heavy load."""
        test_sources = performance_test_sources  # Use all 20 sources
        error_count = 0
        success_count = 0

        with patch('..agent.quality_agent.run') as mock_agent_run:
            async def mock_assessment_with_errors(*args, **kwargs):
                nonlocal error_count, success_count

                # Simulate occasional errors under load
                import random
                if random.random() < 0.05:  # 5% error rate simulation
                    error_count += 1
                    raise Exception("Simulated load-induced error")

                success_count += 1
                await asyncio.sleep(0.03)  # Slightly longer under load

                assessment = QualityAssessment(
                    source_id="load_test",
                    credibility_score=0.75,
                    bias_score=0.25,
                    freshness_score=0.8,
                    authority_score=0.7,
                    overall_quality=0.725,
                    confidence_rating=0.85,
                    flags=[]
                )
                mock_result = AsyncMock()
                mock_result.data = assessment
                return mock_result

            mock_agent_run.side_effect = mock_assessment_with_errors

            # Process under load
            results = await assess_multiple_sources(test_sources, max_concurrent=15)

            # Validate error handling
            assert len(results) == len(test_sources)  # Should handle all sources

            # Calculate actual error rate
            total_attempts = error_count + success_count
            actual_error_rate = error_count / total_attempts if total_attempts > 0 else 0

            # Error rate should be reasonable and handled gracefully
            assert actual_error_rate < 0.1  # Less than 10% error rate

            # All results should be valid (errors handled with fallback assessments)
            assert all(isinstance(r, QualityAssessment) for r in results)

            # Some results should be fallback assessments (low confidence)
            fallback_count = sum(1 for r in results if r.confidence_rating <= 0.2)

            print(f"Load test - Errors: {error_count}, Success: {success_count}, Error rate: {actual_error_rate:.1%}, Fallbacks: {fallback_count}")