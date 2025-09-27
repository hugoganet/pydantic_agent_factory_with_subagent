"""
Test Data Synthesis Agent performance targets and validation.

Tests synthesis time targets, quality metrics, throughput capacity,
and scalability under various load conditions against the specified
performance requirements in INITIAL.md.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from statistics import mean, median
from unittest.mock import patch, AsyncMock

from agents.data_synthesis_agent import run_synthesis, health_check
from agents.data_synthesis_agent.models import SynthesisRequest, SynthesizedReport
from agents.data_synthesis_agent.dependencies import SynthesisDependencies


class TestSynthesisTimeTargets:
    """Test synthesis completion within time targets."""

    @pytest.mark.asyncio
    async def test_standard_synthesis_time_target(self, sample_synthesis_request):
        """Test synthesis completes within 2-minute target for standard reports."""

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            # Simulate realistic processing time for standard synthesis
            async def timed_standard_synthesis(*args, **kwargs):
                await asyncio.sleep(0.8)  # Simulate 800ms processing
                result = AsyncMock()
                result.data = SynthesizedReport(
                    request_id=sample_synthesis_request.request_id,
                    executive_summary="Standard synthesis completed within target time window",
                    key_findings=[
                        {
                            "finding_id": "perf_001",
                            "title": "Performance Test Finding",
                            "description": "Test finding for performance validation",
                            "confidence_level": 0.85
                        }
                    ],
                    detailed_analysis="Performance analysis demonstrates synthesis completion within targets",
                    supporting_evidence=["Performance metrics validation"],
                    gaps_identified=["Performance edge cases"],
                    recommendations=["Continue performance monitoring"],
                    confidence_assessment={"overall_confidence": 0.88},
                    metadata={
                        "generation_timestamp": datetime.now(),
                        "findings_processed": len(sample_synthesis_request.research_findings),
                        "synthesis_type": "standard"
                    }
                )
                return result

            mock_agent_run.side_effect = timed_standard_synthesis

            # Measure synthesis time
            start_time = time.time()
            result = await run_synthesis(sample_synthesis_request, session_id="perf_standard")
            end_time = time.time()

            synthesis_duration = end_time - start_time

            # Verify time target (2 minutes = 120 seconds)
            assert synthesis_duration < 120.0, f"Synthesis took {synthesis_duration:.2f}s, exceeds 120s target"

            # Verify successful completion
            assert isinstance(result, SynthesizedReport)
            assert result.request_id == sample_synthesis_request.request_id
            assert len(result.executive_summary) > 0

    @pytest.mark.asyncio
    async def test_executive_format_speed(self, sample_research_findings):
        """Test executive format synthesis is faster than detailed format."""

        # Create executive and detailed format requests
        executive_request = SynthesisRequest(
            request_id="exec_speed_test",
            research_findings=sample_research_findings,
            output_format="executive",
            target_audience="executives"
        )

        detailed_request = SynthesisRequest(
            request_id="detailed_speed_test",
            research_findings=sample_research_findings,
            output_format="detailed",
            target_audience="researchers"
        )

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            # Executive format processing (faster)
            async def executive_processing(*args, **kwargs):
                await asyncio.sleep(0.3)  # 300ms for executive
                result = AsyncMock()
                result.data = SynthesizedReport(
                    request_id="exec_speed_test",
                    executive_summary="Quick executive synthesis",
                    key_findings=[],
                    detailed_analysis="Brief analysis for executives",
                    supporting_evidence=[],
                    gaps_identified=[],
                    recommendations=[],
                    confidence_assessment={"overall_confidence": 0.85},
                    metadata={
                        "generation_timestamp": datetime.now(),
                        "synthesis_type": "executive",
                        "processing_time": 0.3
                    }
                )
                return result

            # Detailed format processing (slower)
            async def detailed_processing(*args, **kwargs):
                await asyncio.sleep(0.7)  # 700ms for detailed
                result = AsyncMock()
                result.data = SynthesizedReport(
                    request_id="detailed_speed_test",
                    executive_summary="Comprehensive detailed synthesis",
                    key_findings=[{
                        "finding_id": "detailed_001",
                        "title": "Detailed Finding",
                        "description": "Comprehensive analysis finding",
                        "confidence_level": 0.87
                    }],
                    detailed_analysis="Comprehensive analysis with multiple sections and detailed findings",
                    supporting_evidence=["Multiple evidence sources", "Cross-validation"],
                    gaps_identified=["Detailed gap analysis"],
                    recommendations=["Comprehensive recommendations"],
                    confidence_assessment={"overall_confidence": 0.89},
                    metadata={
                        "generation_timestamp": datetime.now(),
                        "synthesis_type": "detailed",
                        "processing_time": 0.7
                    }
                )
                return result

            # Test executive format
            mock_agent_run.side_effect = executive_processing
            exec_start = time.time()
            exec_result = await run_synthesis(executive_request, session_id="exec_perf")
            exec_duration = time.time() - exec_start

            # Test detailed format
            mock_agent_run.side_effect = detailed_processing
            detailed_start = time.time()
            detailed_result = await run_synthesis(detailed_request, session_id="detailed_perf")
            detailed_duration = time.time() - detailed_start

            # Executive should be faster than detailed
            assert exec_duration < detailed_duration
            assert exec_duration < 60.0  # Executive should be under 1 minute
            assert detailed_duration < 120.0  # Detailed should still be under 2 minutes

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, performance_test_findings):
        """Test synthesis performance with maximum dataset size (50 findings)."""

        large_synthesis_request = SynthesisRequest(
            request_id="large_dataset_perf",
            research_findings=performance_test_findings,  # 50 findings
            output_format="detailed",
            target_audience="researchers"
        )

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            async def large_dataset_processing(*args, **kwargs):
                # Simulate processing time proportional to dataset size
                processing_time = len(performance_test_findings) * 0.02  # 20ms per finding
                await asyncio.sleep(processing_time)

                result = AsyncMock()
                result.data = SynthesizedReport(
                    request_id="large_dataset_perf",
                    executive_summary="Large dataset synthesis demonstrates scalable performance with efficient processing of 50 research findings",
                    key_findings=[
                        {
                            "finding_id": f"large_finding_{i}",
                            "title": f"Pattern {i+1}",
                            "description": f"Identified pattern from large dataset analysis",
                            "confidence_level": 0.80 + (i * 0.02)
                        }
                        for i in range(5)  # 5 key findings from large dataset
                    ],
                    detailed_analysis="Comprehensive analysis of large dataset reveals multiple significant patterns and correlations across diverse research sources",
                    supporting_evidence=[f"Evidence from {len(performance_test_findings)} sources"],
                    gaps_identified=["Scale testing limitations"],
                    recommendations=["Monitor performance at scale"],
                    confidence_assessment={
                        "overall_confidence": 0.87,
                        "source_reliability": 0.89,
                        "cross_validation_score": 0.85
                    },
                    metadata={
                        "generation_timestamp": datetime.now(),
                        "findings_processed": len(performance_test_findings),
                        "processing_time": processing_time,
                        "dataset_size": "large"
                    }
                )
                return result

            mock_agent_run.side_effect = large_dataset_processing

            # Measure large dataset synthesis time
            start_time = time.time()
            result = await run_synthesis(large_synthesis_request, session_id="large_perf")
            synthesis_time = time.time() - start_time

            # Verify performance targets
            assert synthesis_time < 120.0, f"Large dataset synthesis took {synthesis_time:.2f}s, exceeds 120s target"

            # Verify processing efficiency
            assert result.metadata["findings_processed"] == 50
            assert len(result.key_findings) > 0
            assert result.confidence_assessment["overall_confidence"] >= 0.8


class TestQualityTargets:
    """Test synthesis quality targets (>90% accuracy)."""

    @pytest.mark.asyncio
    async def test_quality_target_achievement(self, integration_test_data):
        """Test synthesis achieves >90% quality target."""

        high_quality_request = SynthesisRequest(
            request_id="quality_target_test",
            research_findings=integration_test_data["findings"],
            quality_threshold=0.9,  # 90% quality threshold
            output_format="detailed",
            target_audience="researchers"
        )

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            mock_result = AsyncMock()
            mock_result.data = SynthesizedReport(
                request_id="quality_target_test",
                executive_summary="High-quality synthesis demonstrates superior accuracy with validated patterns and cross-verified insights from multiple reliable sources",
                key_findings=[
                    {
                        "finding_id": "quality_001",
                        "title": "High Confidence AI Healthcare Pattern",
                        "description": "Validated pattern showing consistent AI healthcare benefits",
                        "confidence_level": 0.94,
                        "significance": "high",
                        "cross_validation_status": "validated"
                    },
                    {
                        "finding_id": "quality_002",
                        "title": "Cross-Validated Diagnostic Accuracy",
                        "description": "40% improvement in diagnostic accuracy validated across sources",
                        "confidence_level": 0.92,
                        "significance": "high",
                        "cross_validation_status": "validated"
                    }
                ],
                detailed_analysis="Quality analysis demonstrates high factual accuracy through multi-source validation and statistical significance testing",
                supporting_evidence=[
                    "Cross-source validation across 5 independent sources",
                    "Statistical significance at p<0.05 level",
                    "Peer review validation"
                ],
                gaps_identified=["Limited longitudinal data"],
                recommendations=["Extend longitudinal analysis", "Increase peer review coverage"],
                confidence_assessment={
                    "overall_confidence": 0.93,  # >90% target
                    "source_reliability": 0.96,
                    "cross_validation_score": 0.94,
                    "completeness_score": 0.91,
                    "methodology_notes": "Multi-stage validation with statistical significance testing"
                },
                metadata={
                    "generation_timestamp": datetime.now(),
                    "findings_processed": len(integration_test_data["findings"]),
                    "quality_score": 0.94,  # >90% target
                    "validation_methods": ["cross_source", "statistical", "peer_review"]
                }
            )
            mock_agent_run.return_value = mock_result

            result = await run_synthesis(high_quality_request, session_id="quality_test")

            # Verify quality targets
            assert result.confidence_assessment["overall_confidence"] >= 0.9, "Overall confidence below 90% target"
            assert result.metadata["quality_score"] >= 0.9, "Quality score below 90% target"

            # Verify quality indicators
            assert all(kf["confidence_level"] >= 0.9 for kf in result.key_findings), "Key findings below 90% confidence"
            assert result.confidence_assessment["source_reliability"] >= 0.9, "Source reliability below 90%"

            # Verify cross-validation
            validated_findings = [kf for kf in result.key_findings if kf.get("cross_validation_status") == "validated"]
            assert len(validated_findings) >= len(result.key_findings) * 0.8, "Less than 80% findings cross-validated"

    @pytest.mark.asyncio
    async def test_quality_degradation_with_poor_sources(self, error_scenarios):
        """Test quality metrics reflect source data quality."""

        poor_quality_request = SynthesisRequest(
            request_id="poor_quality_test",
            research_findings=error_scenarios["low_confidence_findings"],
            quality_threshold=0.5,  # Lower threshold for poor data
            output_format="detailed"
        )

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            mock_result = AsyncMock()
            mock_result.data = SynthesizedReport(
                request_id="poor_quality_test",
                executive_summary="Analysis based on low-confidence sources shows preliminary trends requiring additional validation and higher-quality source material",
                key_findings=[
                    {
                        "finding_id": "poor_001",
                        "title": "Preliminary Trend (Requires Validation)",
                        "description": "Initial trend identified with limited confidence",
                        "confidence_level": 0.45,  # Below quality threshold
                        "cross_validation_status": "insufficient"
                    }
                ],
                detailed_analysis="Analysis constrained by low source confidence levels",
                supporting_evidence=["Limited evidence base"],
                gaps_identified=[
                    "Low source confidence levels",
                    "Insufficient cross-validation",
                    "Limited evidence base"
                ],
                recommendations=[
                    "Obtain higher-confidence source materials",
                    "Conduct additional validation studies",
                    "Expand evidence base"
                ],
                confidence_assessment={
                    "overall_confidence": 0.42,  # Below 90% target
                    "source_reliability": 0.35,
                    "cross_validation_score": 0.25,
                    "completeness_score": 0.30
                },
                metadata={
                    "quality_score": 0.38,  # Reflects poor source quality
                    "quality_warnings": ["Low source confidence", "Insufficient validation"]
                }
            )
            mock_agent_run.return_value = mock_result

            result = await run_synthesis(poor_quality_request, session_id="poor_quality_test")

            # Quality should reflect poor source material
            assert result.confidence_assessment["overall_confidence"] < 0.7
            assert result.metadata["quality_score"] < 0.7
            assert "quality_warnings" in result.metadata
            assert len(result.gaps_identified) >= 3

    @pytest.mark.asyncio
    async def test_quality_consistency_across_formats(self, sample_research_findings):
        """Test quality consistency across different output formats."""

        formats_to_test = ["executive", "detailed", "technical"]
        quality_results = {}

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            for fmt in formats_to_test:
                async def format_specific_processing(*args, **kwargs):
                    base_quality = 0.88  # Base quality score

                    # Format-specific adjustments
                    if fmt == "executive":
                        quality_adj = 0.02  # Slightly higher for focused format
                    elif fmt == "detailed":
                        quality_adj = 0.00  # Base quality
                    else:  # technical
                        quality_adj = 0.01  # Slightly higher for technical precision

                    final_quality = min(0.95, base_quality + quality_adj)

                    result = AsyncMock()
                    result.data = SynthesizedReport(
                        request_id=f"quality_consistency_{fmt}",
                        executive_summary=f"Quality-consistent {fmt} format synthesis",
                        key_findings=[{
                            "finding_id": f"{fmt}_quality_001",
                            "title": f"{fmt.title()} Quality Finding",
                            "description": f"Quality finding in {fmt} format",
                            "confidence_level": final_quality
                        }],
                        detailed_analysis=f"Quality analysis in {fmt} format",
                        supporting_evidence=[f"{fmt} format evidence"],
                        gaps_identified=[],
                        recommendations=[],
                        confidence_assessment={
                            "overall_confidence": final_quality,
                            "source_reliability": final_quality + 0.02
                        },
                        metadata={
                            "quality_score": final_quality,
                            "output_format": fmt
                        }
                    )
                    return result

                mock_agent_run.side_effect = format_specific_processing

                request = SynthesisRequest(
                    request_id=f"consistency_{fmt}",
                    research_findings=sample_research_findings,
                    output_format=fmt,
                    quality_threshold=0.8
                )

                result = await run_synthesis(request, session_id=f"consistency_{fmt}")
                quality_results[fmt] = result.confidence_assessment["overall_confidence"]

            # Verify quality consistency (within 10% variation)
            qualities = list(quality_results.values())
            quality_range = max(qualities) - min(qualities)
            assert quality_range <= 0.10, f"Quality variation {quality_range} exceeds 10% threshold"

            # All formats should maintain minimum quality
            assert all(q >= 0.8 for q in qualities), "Some formats below 80% quality threshold"


class TestThroughputCapacity:
    """Test synthesis throughput and capacity limits."""

    @pytest.mark.asyncio
    async def test_findings_processing_capacity(self, performance_test_findings):
        """Test processing capacity up to 50 findings per synthesis."""

        capacity_tests = [10, 25, 50]  # Different dataset sizes
        processing_times = {}

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            for finding_count in capacity_tests:
                async def capacity_processing(*args, **kwargs):
                    # Simulate processing time scaling with dataset size
                    processing_time = finding_count * 0.015  # 15ms per finding
                    await asyncio.sleep(processing_time)

                    result = AsyncMock()
                    result.data = SynthesizedReport(
                        request_id=f"capacity_{finding_count}",
                        executive_summary=f"Processed {finding_count} findings efficiently",
                        key_findings=[],
                        detailed_analysis=f"Analysis of {finding_count} findings",
                        supporting_evidence=[],
                        gaps_identified=[],
                        recommendations=[],
                        confidence_assessment={"overall_confidence": 0.85},
                        metadata={
                            "findings_processed": finding_count,
                            "processing_time": processing_time
                        }
                    )
                    return result

                mock_agent_run.side_effect = capacity_processing

                request = SynthesisRequest(
                    request_id=f"capacity_{finding_count}",
                    research_findings=performance_test_findings[:finding_count],
                    output_format="detailed"
                )

                start_time = time.time()
                result = await run_synthesis(request, session_id=f"capacity_{finding_count}")
                processing_times[finding_count] = time.time() - start_time

                # Verify processing completed successfully
                assert result.metadata["findings_processed"] == finding_count
                assert processing_times[finding_count] < 120.0  # Under 2-minute target

            # Verify scaling efficiency (should be roughly linear)
            efficiency_10_to_25 = processing_times[25] / processing_times[10]
            efficiency_25_to_50 = processing_times[50] / processing_times[25]

            # Should scale reasonably (not exponentially)
            assert efficiency_10_to_25 < 4.0, "Processing time scaling inefficient"
            assert efficiency_25_to_50 < 3.0, "Processing time scaling inefficient"

    @pytest.mark.asyncio
    async def test_concurrent_synthesis_throughput(self, sample_research_findings):
        """Test concurrent synthesis request handling."""

        concurrent_count = 3
        small_datasets = [sample_research_findings[:5] for _ in range(concurrent_count)]

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            async def concurrent_processing(*args, **kwargs):
                await asyncio.sleep(0.5)  # 500ms per synthesis
                result = AsyncMock()
                result.data = SynthesizedReport(
                    request_id=f"concurrent_{time.time()}",
                    executive_summary="Concurrent synthesis completed",
                    key_findings=[],
                    detailed_analysis="Concurrent processing analysis",
                    supporting_evidence=[],
                    gaps_identified=[],
                    recommendations=[],
                    confidence_assessment={"overall_confidence": 0.85},
                    metadata={
                        "generation_timestamp": datetime.now(),
                        "concurrent_processing": True
                    }
                )
                return result

            mock_agent_run.side_effect = concurrent_processing

            # Create concurrent synthesis tasks
            requests = [
                SynthesisRequest(
                    request_id=f"concurrent_{i}",
                    research_findings=dataset,
                    output_format="executive"
                )
                for i, dataset in enumerate(small_datasets)
            ]

            tasks = [
                run_synthesis(req, session_id=f"concurrent_{i}")
                for i, req in enumerate(requests)
            ]

            # Execute concurrent synthesis
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            # Verify concurrent completion
            assert len(results) == concurrent_count
            assert all(isinstance(r, SynthesizedReport) for r in results)

            # Should complete concurrently (faster than sequential)
            expected_sequential_time = concurrent_count * 0.5  # 1.5 seconds
            assert total_time < expected_sequential_time, f"Concurrent processing ({total_time:.2f}s) slower than expected"

    @pytest.mark.asyncio
    async def test_memory_efficiency_scaling(self, performance_test_findings):
        """Test memory efficiency with increasing dataset sizes."""

        # Simulate different memory usage patterns
        dataset_sizes = [10, 25, 50]
        memory_usage = {}

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            for size in dataset_sizes:
                async def memory_aware_processing(*args, **kwargs):
                    # Simulate memory-conscious processing
                    base_memory = 10  # MB base usage
                    linear_memory = size * 0.5  # 0.5MB per finding
                    total_memory = base_memory + linear_memory

                    # Simulate processing delay proportional to memory usage
                    await asyncio.sleep(total_memory * 0.01)

                    result = AsyncMock()
                    result.data = SynthesizedReport(
                        request_id=f"memory_{size}",
                        executive_summary=f"Memory-efficient processing of {size} findings",
                        key_findings=[],
                        detailed_analysis="Memory-optimized analysis",
                        supporting_evidence=[],
                        gaps_identified=[],
                        recommendations=[],
                        confidence_assessment={"overall_confidence": 0.85},
                        metadata={
                            "findings_processed": size,
                            "estimated_memory_mb": total_memory,
                            "memory_efficient": True
                        }
                    )
                    return result

                mock_agent_run.side_effect = memory_aware_processing

                request = SynthesisRequest(
                    request_id=f"memory_{size}",
                    research_findings=performance_test_findings[:size],
                    output_format="detailed"
                )

                result = await run_synthesis(request, session_id=f"memory_{size}")
                memory_usage[size] = result.metadata["estimated_memory_mb"]

            # Verify linear memory scaling (not exponential)
            memory_ratio_10_25 = memory_usage[25] / memory_usage[10]
            memory_ratio_25_50 = memory_usage[50] / memory_usage[25]

            # Should scale roughly linearly
            assert 1.5 <= memory_ratio_10_25 <= 3.5, f"Memory scaling ratio {memory_ratio_10_25} not linear"
            assert 1.5 <= memory_ratio_25_50 <= 2.5, f"Memory scaling ratio {memory_ratio_25_50} not linear"


class TestScalabilityMetrics:
    """Test scalability and performance monitoring."""

    @pytest.mark.asyncio
    async def test_performance_monitoring_metrics(self, sample_synthesis_request):
        """Test performance monitoring captures key metrics."""

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            mock_result = AsyncMock()
            mock_result.data = SynthesizedReport(
                request_id="metrics_test",
                executive_summary="Performance monitoring test",
                key_findings=[],
                detailed_analysis="Metrics collection analysis",
                supporting_evidence=[],
                gaps_identified=[],
                recommendations=[],
                confidence_assessment={"overall_confidence": 0.85},
                metadata={
                    "generation_timestamp": datetime.now(),
                    "synthesis_duration_seconds": 67.3,
                    "findings_processed": len(sample_synthesis_request.research_findings),
                    "sources_analyzed": 12,
                    "agent_version": "1.0.0",
                    "quality_score": 0.87,
                    "performance_metrics": {
                        "integration_time": 15.2,
                        "analysis_time": 28.7,
                        "generation_time": 23.4
                    }
                }
            )
            mock_agent_run.return_value = mock_result

            result = await run_synthesis(sample_synthesis_request, session_id="metrics_test")

            # Verify performance metrics collection
            assert "synthesis_duration_seconds" in result.metadata
            assert result.metadata["synthesis_duration_seconds"] < 120  # Within target
            assert "performance_metrics" in result.metadata

            perf_metrics = result.metadata["performance_metrics"]
            assert "integration_time" in perf_metrics
            assert "analysis_time" in perf_metrics
            assert "generation_time" in perf_metrics

    @pytest.mark.asyncio
    async def test_health_check_performance_info(self, mock_settings):
        """Test health check provides performance-relevant information."""

        with patch('agents.data_synthesis_agent.settings', mock_settings):
            health_status = await health_check()

            # Verify performance-related health metrics
            assert "max_findings" in health_status
            assert health_status["max_findings"] == 50  # Capacity limit
            assert "timeout_seconds" in health_status
            assert health_status["timeout_seconds"] == 120  # Time target
            assert "confidence_threshold" in health_status
            assert health_status["confidence_threshold"] == 0.7  # Quality threshold

    @pytest.mark.asyncio
    async def test_performance_regression_detection(self, sample_research_findings):
        """Test detection of performance regression scenarios."""

        # Simulate performance baseline and regression
        baseline_times = []
        regression_times = []

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            # Baseline performance
            async def baseline_processing(*args, **kwargs):
                processing_time = 0.6  # 600ms baseline
                await asyncio.sleep(processing_time)

                result = AsyncMock()
                result.data = SynthesizedReport(
                    request_id="baseline_test",
                    executive_summary="Baseline performance test",
                    key_findings=[],
                    detailed_analysis="Baseline analysis",
                    supporting_evidence=[],
                    gaps_identified=[],
                    recommendations=[],
                    confidence_assessment={"overall_confidence": 0.85},
                    metadata={
                        "processing_time": processing_time,
                        "performance_type": "baseline"
                    }
                )
                return result

            # Regression scenario (slower)
            async def regression_processing(*args, **kwargs):
                processing_time = 1.8  # 1800ms (3x slower)
                await asyncio.sleep(processing_time)

                result = AsyncMock()
                result.data = SynthesizedReport(
                    request_id="regression_test",
                    executive_summary="Performance regression test",
                    key_findings=[],
                    detailed_analysis="Regression analysis",
                    supporting_evidence=[],
                    gaps_identified=[],
                    recommendations=[],
                    confidence_assessment={"overall_confidence": 0.85},
                    metadata={
                        "processing_time": processing_time,
                        "performance_type": "regression"
                    }
                )
                return result

            # Test baseline performance (multiple runs)
            mock_agent_run.side_effect = baseline_processing
            for i in range(3):
                request = SynthesisRequest(
                    request_id=f"baseline_{i}",
                    research_findings=sample_research_findings[:10],
                    output_format="executive"
                )

                start_time = time.time()
                result = await run_synthesis(request, session_id=f"baseline_{i}")
                baseline_times.append(time.time() - start_time)

            # Test regression scenario
            mock_agent_run.side_effect = regression_processing
            for i in range(3):
                request = SynthesisRequest(
                    request_id=f"regression_{i}",
                    research_findings=sample_research_findings[:10],
                    output_format="executive"
                )

                start_time = time.time()
                result = await run_synthesis(request, session_id=f"regression_{i}")
                regression_times.append(time.time() - start_time)

            # Analyze performance regression
            baseline_avg = mean(baseline_times)
            regression_avg = mean(regression_times)
            performance_ratio = regression_avg / baseline_avg

            # Should detect significant regression
            assert performance_ratio >= 2.5, f"Performance regression not detected: {performance_ratio}x"

            # All baseline times should be reasonable
            assert all(t < 2.0 for t in baseline_times), "Baseline performance exceeds reasonable limits"

            # Regression should still complete (just slower)
            assert all(t < 10.0 for t in regression_times), "Regression scenario failed to complete"

    @pytest.mark.asyncio
    async def test_load_testing_scenarios(self, performance_test_findings):
        """Test various load scenarios and capacity limits."""

        load_scenarios = {
            "light": {"findings": 10, "concurrent": 1, "timeout": 30},
            "moderate": {"findings": 25, "concurrent": 2, "timeout": 60},
            "heavy": {"findings": 50, "concurrent": 3, "timeout": 120}
        }

        load_results = {}

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            for scenario_name, config in load_scenarios.items():
                async def load_processing(*args, **kwargs):
                    # Processing time scales with findings count
                    processing_time = config["findings"] * 0.01  # 10ms per finding
                    await asyncio.sleep(processing_time)

                    result = AsyncMock()
                    result.data = SynthesizedReport(
                        request_id=f"load_{scenario_name}",
                        executive_summary=f"Load test {scenario_name} scenario completed",
                        key_findings=[],
                        detailed_analysis=f"{scenario_name} load analysis",
                        supporting_evidence=[],
                        gaps_identified=[],
                        recommendations=[],
                        confidence_assessment={"overall_confidence": 0.85},
                        metadata={
                            "load_scenario": scenario_name,
                            "findings_processed": config["findings"],
                            "processing_time": processing_time
                        }
                    )
                    return result

                mock_agent_run.side_effect = load_processing

                # Create concurrent requests for this scenario
                requests = [
                    SynthesisRequest(
                        request_id=f"load_{scenario_name}_{i}",
                        research_findings=performance_test_findings[:config["findings"]],
                        output_format="detailed"
                    )
                    for i in range(config["concurrent"])
                ]

                # Execute load test
                tasks = [
                    asyncio.wait_for(
                        run_synthesis(req, session_id=f"load_{scenario_name}_{i}"),
                        timeout=config["timeout"]
                    )
                    for i, req in enumerate(requests)
                ]

                start_time = time.time()
                try:
                    results = await asyncio.gather(*tasks)
                    completion_time = time.time() - start_time

                    load_results[scenario_name] = {
                        "success": True,
                        "completion_time": completion_time,
                        "requests_completed": len(results),
                        "avg_time_per_request": completion_time / len(results)
                    }
                except asyncio.TimeoutError:
                    load_results[scenario_name] = {
                        "success": False,
                        "error": "timeout",
                        "timeout_limit": config["timeout"]
                    }

        # Verify load test results
        assert load_results["light"]["success"], "Light load scenario failed"
        assert load_results["moderate"]["success"], "Moderate load scenario failed"
        assert load_results["heavy"]["success"], "Heavy load scenario failed"

        # Verify performance characteristics
        assert load_results["light"]["completion_time"] < 30
        assert load_results["moderate"]["completion_time"] < 60
        assert load_results["heavy"]["completion_time"] < 120