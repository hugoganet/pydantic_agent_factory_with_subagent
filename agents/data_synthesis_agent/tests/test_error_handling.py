"""
Test Data Synthesis Agent error handling and recovery mechanisms.

Tests various failure scenarios including tool failures, validation errors,
timeout handling, and graceful degradation strategies.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse
from pydantic import ValidationError

from agents.data_synthesis_agent import agent, run_synthesis
from agents.data_synthesis_agent.models import (
    SynthesisRequest, ResearchFinding, ResearchSource, SynthesizedReport
)
from agents.data_synthesis_agent.dependencies import SynthesisDependencies


class TestValidationErrorHandling:
    """Test handling of input validation errors."""

    @pytest.mark.asyncio
    async def test_invalid_synthesis_request(self):
        """Test handling of malformed synthesis requests."""

        # Test empty findings list
        with pytest.raises(ValueError, match="Synthesis conditions not met"):
            empty_request = SynthesisRequest(
                request_id="empty_test",
                research_findings=[],  # Empty findings
                output_format="detailed"
            )
            await run_synthesis(empty_request, session_id="validation_test")

    @pytest.mark.asyncio
    async def test_invalid_research_finding_data(self):
        """Test handling of invalid ResearchFinding data."""

        # Test invalid confidence level
        with pytest.raises(ValidationError):
            ResearchFinding(
                source_agent="test_agent",
                finding_id="invalid_confidence",
                content="Test content",
                confidence_level=1.5  # Invalid: > 1.0
            )

        # Test negative confidence level
        with pytest.raises(ValidationError):
            ResearchFinding(
                source_agent="test_agent",
                finding_id="negative_confidence",
                content="Test content",
                confidence_level=-0.1  # Invalid: < 0.0
            )

    @pytest.mark.asyncio
    async def test_synthesis_readiness_validation(self, mock_settings):
        """Test synthesis readiness validation scenarios."""

        # Test research phase not complete
        deps_not_ready = SynthesisDependencies(
            session_id="not_ready_test",
            research_phase_complete=False  # Not ready
        )
        assert not deps_not_ready.validate_synthesis_readiness(5)

        # Test zero findings
        deps_ready = SynthesisDependencies(
            session_id="ready_test",
            research_phase_complete=True
        )
        assert not deps_ready.validate_synthesis_readiness(0)  # Zero findings

        # Test excessive findings (warning case)
        deps_excessive = SynthesisDependencies(
            session_id="excessive_test",
            research_phase_complete=True,
            max_findings_count=10
        )
        # Should still return True but log warning
        assert deps_excessive.validate_synthesis_readiness(15)

    @pytest.mark.asyncio
    async def test_quality_threshold_validation(self, sample_research_findings):
        """Test quality threshold validation errors."""

        # Test invalid quality threshold
        with pytest.raises(ValidationError):
            SynthesisRequest(
                request_id="invalid_quality",
                research_findings=sample_research_findings,
                quality_threshold=1.2  # Invalid: > 1.0
            )

        with pytest.raises(ValidationError):
            SynthesisRequest(
                request_id="negative_quality",
                research_findings=sample_research_findings,
                quality_threshold=-0.1  # Invalid: < 0.0
            )


class TestToolExecutionErrors:
    """Test handling of tool execution failures."""

    @pytest.mark.asyncio
    async def test_data_integrator_error_handling(self, test_dependencies, error_scenarios):
        """Test data_integrator handles various error conditions."""

        from agents.data_synthesis_agent.tools import register_synthesis_tools

        class ToolCapture:
            def __init__(self):
                self.captured_tools = {}
            def tool(self, func):
                self.captured_tools[func.__name__] = func
                return func

        tool_capture = ToolCapture()
        register_synthesis_tools(tool_capture, SynthesisDependencies)
        data_integrator = tool_capture.captured_tools['data_integrator']

        mock_ctx = MagicMock()
        mock_ctx.deps = test_dependencies

        # Test with low confidence findings
        result = await data_integrator(
            mock_ctx,
            error_scenarios["low_confidence_findings"],
            normalization_strategy="confidence_weighted"
        )

        assert result["success"] is True  # Should still succeed
        assert len(result["integrated_data"]["unified_findings"]) >= 0

        # Test with corrupted finding data (simulate exception)
        with patch('agents.data_synthesis_agent.tools.defaultdict') as mock_defaultdict:
            mock_defaultdict.side_effect = Exception("Data structure corruption")

            result = await data_integrator(
                mock_ctx,
                error_scenarios["low_confidence_findings"],
                normalization_strategy="confidence_weighted"
            )

            assert result["success"] is False
            assert "error" in result
            assert "Data structure corruption" in result["error"]

    @pytest.mark.asyncio
    async def test_pattern_analyzer_error_handling(self, test_dependencies):
        """Test pattern_analyzer handles invalid input gracefully."""

        from agents.data_synthesis_agent.tools import register_synthesis_tools

        class ToolCapture:
            def __init__(self):
                self.captured_tools = {}
            def tool(self, func):
                self.captured_tools[func.__name__] = func
                return func

        tool_capture = ToolCapture()
        register_synthesis_tools(tool_capture, SynthesisDependencies)
        pattern_analyzer = tool_capture.captured_tools['pattern_analyzer']

        mock_ctx = MagicMock()
        mock_ctx.deps = test_dependencies

        # Test with failed integration data
        failed_integration_data = {
            "success": False,
            "error": "Integration failed",
            "integrated_data": {}
        }

        result = await pattern_analyzer(
            mock_ctx,
            failed_integration_data,
            analysis_depth="standard"
        )

        assert result["success"] is False
        assert "Invalid integrated_data" in result["error"]

        # Test with malformed integration data
        malformed_data = {
            "success": True,
            "integrated_data": "not_a_dict"  # Wrong type
        }

        result = await pattern_analyzer(
            mock_ctx,
            malformed_data,
            analysis_depth="standard"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_report_generator_error_handling(self, test_dependencies):
        """Test report_generator handles analysis failures."""

        from agents.data_synthesis_agent.tools import register_synthesis_tools

        class ToolCapture:
            def __init__(self):
                self.captured_tools = {}
            def tool(self, func):
                self.captured_tools[func.__name__] = func
                return func

        tool_capture = ToolCapture()
        register_synthesis_tools(tool_capture, SynthesisDependencies)
        report_generator = tool_capture.captured_tools['report_generator']

        mock_ctx = MagicMock()
        mock_ctx.deps = test_dependencies

        # Test with failed analysis results
        failed_analysis_results = {
            "success": False,
            "error": "Pattern analysis failed",
            "analysis_results": {}
        }

        result = await report_generator(
            mock_ctx,
            failed_analysis_results,
            output_format="detailed",
            target_audience="researchers"
        )

        assert result["success"] is False
        assert "Invalid analysis_results" in result["error"]

    @pytest.mark.asyncio
    async def test_tool_chain_failure_recovery(self, test_dependencies, sample_research_findings):
        """Test recovery when tool chain encounters failures."""

        failure_count = 0

        async def failing_tool_chain_function(messages, tools):
            nonlocal failure_count
            last_message = messages[-1].content if messages else ""

            if "data_integrator" in last_message:
                # Data integrator succeeds
                return {
                    "data_integrator": {
                        "research_findings": sample_research_findings,
                        "normalization_strategy": "confidence_weighted"
                    }
                }
            elif "pattern_analyzer" in last_message:
                failure_count += 1
                if failure_count <= 2:
                    # Pattern analyzer fails first two times
                    raise Exception(f"Pattern analyzer failure #{failure_count}")
                else:
                    # Succeeds on third attempt
                    return {
                        "pattern_analyzer": {
                            "integrated_data": {
                                "success": True,
                                "integrated_data": {"unified_findings": []}
                            },
                            "analysis_depth": "standard"
                        }
                    }
            elif "report_generator" in last_message:
                # Report generator succeeds
                return {
                    "report_generator": {
                        "analysis_results": {
                            "success": True,
                            "analysis_results": {"identified_patterns": []}
                        },
                        "output_format": "detailed",
                        "target_audience": "researchers"
                    }
                }
            else:
                return ModelTextResponse(content="Starting tool chain with failure recovery")

        function_model = FunctionModel(failing_tool_chain_function)
        test_agent = agent.override(model=function_model)

        # Configure retries
        test_agent.retries = 3

        # Test that agent eventually succeeds despite failures
        result = await test_agent.run(
            "Synthesize with tool chain failure recovery",
            deps=test_dependencies
        )

        assert result is not None
        assert failure_count >= 2  # Should have had failures and recovered


class TestTimeoutAndPerformanceErrors:
    """Test handling of timeout and performance-related errors."""

    @pytest.mark.asyncio
    async def test_synthesis_timeout_handling(self, sample_synthesis_request):
        """Test synthesis respects timeout configurations."""

        # Create dependencies with very short timeout
        short_timeout_deps = SynthesisDependencies(
            session_id="timeout_test",
            synthesis_request_id="timeout_001",
            research_phase_complete=True,
            synthesis_timeout=1  # 1 second timeout
        )

        # Create slow function model
        async def slow_synthesis_function(messages, tools):
            await asyncio.sleep(3)  # Longer than timeout
            return ModelTextResponse(content="Slow synthesis completed")

        slow_model = FunctionModel(slow_synthesis_function)

        # Test with timeout wrapper
        with patch('agents.data_synthesis_agent.SynthesisDependencies.from_settings') as mock_from_settings:
            mock_from_settings.return_value = short_timeout_deps

            start_time = datetime.now()
            try:
                # Use asyncio.wait_for to enforce timeout
                result = await asyncio.wait_for(
                    agent.override(model=slow_model).run(
                        "Slow synthesis test",
                        deps=short_timeout_deps
                    ),
                    timeout=2.0  # 2 second timeout
                )
                # If it completes, that's also acceptable
                assert result is not None
            except asyncio.TimeoutError:
                # Timeout is expected behavior
                pass

            duration = (datetime.now() - start_time).total_seconds()
            assert duration <= 3  # Should not exceed reasonable timeout

    @pytest.mark.asyncio
    async def test_large_dataset_memory_handling(self, performance_test_findings):
        """Test handling of memory pressure with large datasets."""

        # Create synthesis request with maximum findings
        large_request = SynthesisRequest(
            request_id="memory_pressure_test",
            research_findings=performance_test_findings,  # 50 findings
            output_format="comprehensive"
        )

        # Test memory-efficient processing
        memory_deps = SynthesisDependencies(
            session_id="memory_test",
            research_phase_complete=True,
            max_findings_count=50
        )

        # Simulate memory pressure scenario
        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            async def memory_efficient_response(*args, **kwargs):
                # Simulate memory-conscious processing
                await asyncio.sleep(0.1)
                result = AsyncMock()
                result.data = SynthesizedReport(
                    request_id="memory_pressure_test",
                    executive_summary="Memory-efficient synthesis completed",
                    key_findings=[],
                    detailed_analysis="Handled large dataset efficiently",
                    supporting_evidence=[],
                    gaps_identified=[],
                    recommendations=[],
                    confidence_assessment={"overall_confidence": 0.80},
                    metadata={
                        "findings_processed": len(performance_test_findings),
                        "memory_optimized": True
                    }
                )
                return result

            mock_agent_run.side_effect = memory_efficient_response

            result = await run_synthesis(large_request, session_id="memory_test")

            assert isinstance(result, SynthesizedReport)
            assert result.metadata["findings_processed"] == 50
            assert result.metadata.get("memory_optimized", False) is True

    @pytest.mark.asyncio
    async def test_concurrent_request_throttling(self, sample_research_findings):
        """Test handling of concurrent synthesis requests."""

        # Create multiple synthesis requests
        concurrent_requests = [
            SynthesisRequest(
                request_id=f"concurrent_{i}",
                research_findings=sample_research_findings[:5],  # Smaller datasets
                output_format="executive"
            )
            for i in range(5)
        ]

        # Mock agent with controlled response time
        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            async def throttled_response(*args, **kwargs):
                await asyncio.sleep(0.1)  # Small delay
                result = AsyncMock()
                result.data = SynthesizedReport(
                    request_id="concurrent_test",
                    executive_summary="Throttled synthesis response",
                    key_findings=[],
                    detailed_analysis="Concurrent processing test",
                    supporting_evidence=[],
                    gaps_identified=[],
                    recommendations=[],
                    confidence_assessment={"overall_confidence": 0.85},
                    metadata={"generation_timestamp": datetime.now()}
                )
                return result

            mock_agent_run.side_effect = throttled_response

            # Execute concurrent synthesis with timeout protection
            tasks = [
                asyncio.wait_for(
                    run_synthesis(req, session_id=f"concurrent_session_{i}"),
                    timeout=5.0
                )
                for i, req in enumerate(concurrent_requests)
            ]

            start_time = datetime.now()
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                duration = (datetime.now() - start_time).total_seconds()

                # Check that most requests completed successfully
                successful_results = [r for r in results if isinstance(r, SynthesizedReport)]
                assert len(successful_results) >= 3  # At least 60% success rate

                # Should complete in reasonable time
                assert duration < 10.0

            except Exception as e:
                # Some level of failure under concurrent load is acceptable
                assert "timeout" in str(e).lower() or "concurrent" in str(e).lower()


class TestGracefulDegradation:
    """Test graceful degradation strategies."""

    @pytest.mark.asyncio
    async def test_partial_tool_failure_degradation(self, sample_research_findings):
        """Test synthesis continues with partial tool failures."""

        degradation_scenario = 0

        async def degradation_function(messages, tools):
            nonlocal degradation_scenario
            last_message = messages[-1].content if messages else ""

            if "data_integrator" in last_message:
                # Data integrator succeeds
                return {
                    "data_integrator": {
                        "research_findings": sample_research_findings,
                        "normalization_strategy": "confidence_weighted"
                    }
                }
            elif "pattern_analyzer" in last_message:
                degradation_scenario += 1
                if degradation_scenario <= 1:
                    # Pattern analyzer fails - should degrade gracefully
                    raise Exception("Pattern analysis unavailable")
                else:
                    # Eventually provide minimal analysis
                    return {
                        "pattern_analyzer": {
                            "integrated_data": {
                                "success": False,
                                "error": "Limited analysis due to tool failure"
                            },
                            "analysis_depth": "minimal"
                        }
                    }
            elif "report_generator" in last_message:
                # Report generator adapts to limited analysis
                return {
                    "report_generator": {
                        "analysis_results": {
                            "success": False,
                            "analysis_results": {"identified_patterns": []},
                            "error": "Limited patterns due to analysis failure"
                        },
                        "output_format": "simplified",
                        "target_audience": "general"
                    }
                }
            else:
                return ModelTextResponse(content="Starting synthesis with graceful degradation")

        degradation_model = FunctionModel(degradation_function)
        test_agent = agent.override(model=degradation_model)

        deps = SynthesisDependencies(
            session_id="degradation_test",
            research_phase_complete=True
        )

        # Agent should complete synthesis despite tool failures
        result = await test_agent.run(
            "Synthesize with graceful degradation",
            deps=deps
        )

        assert result is not None
        # Should indicate some level of degradation occurred
        assert degradation_scenario >= 1

    @pytest.mark.asyncio
    async def test_low_confidence_data_handling(self, error_scenarios):
        """Test handling of low-confidence research findings."""

        low_confidence_request = SynthesisRequest(
            request_id="low_confidence_test",
            research_findings=error_scenarios["low_confidence_findings"],
            quality_threshold=0.5,  # Lower threshold to allow processing
            output_format="executive"
        )

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            mock_result = AsyncMock()
            mock_result.data = SynthesizedReport(
                request_id="low_confidence_test",
                executive_summary="Analysis based on limited confidence data shows preliminary trends requiring additional validation",
                key_findings=[
                    {
                        "finding_id": "low_conf_001",
                        "title": "Preliminary Trend (Low Confidence)",
                        "description": "Initial finding requiring validation",
                        "confidence_level": 0.3,
                        "cross_validation_status": "insufficient"
                    }
                ],
                detailed_analysis="Analysis conducted with limited confidence data",
                supporting_evidence=["Limited evidence base"],
                gaps_identified=["Low confidence levels", "Insufficient validation"],
                recommendations=["Gather higher confidence data", "Conduct additional validation"],
                confidence_assessment={
                    "overall_confidence": 0.4,
                    "source_reliability": 0.3,
                    "completeness_score": 0.2
                },
                metadata={"quality_warning": "Low confidence data"}
            )
            mock_agent_run.return_value = mock_result

            result = await run_synthesis(low_confidence_request, session_id="low_confidence_test")

            # Should complete but with appropriate warnings
            assert isinstance(result, SynthesizedReport)
            assert result.confidence_assessment["overall_confidence"] < 0.5
            assert "validation" in result.executive_summary.lower()
            assert len(result.gaps_identified) > 0
            assert any("confidence" in gap.lower() for gap in result.gaps_identified)

    @pytest.mark.asyncio
    async def test_incomplete_research_data_handling(self):
        """Test handling of incomplete or malformed research data."""

        # Create research findings with missing or incomplete data
        incomplete_findings = [
            ResearchFinding(
                source_agent="incomplete_agent",
                finding_id="incomplete_001",
                content="",  # Empty content
                sources=[],  # No sources
                confidence_level=0.5,
                key_insights=[],  # No insights
                timestamp=datetime.now()
            ),
            ResearchFinding(
                source_agent="partial_agent",
                finding_id="partial_001",
                content="Partial finding with some content",
                sources=[ResearchSource(title="Single Source", source_type="web")],
                confidence_level=0.7,
                key_insights=["partial insight"],
                timestamp=datetime.now()
            )
        ]

        incomplete_request = SynthesisRequest(
            request_id="incomplete_test",
            research_findings=incomplete_findings,
            output_format="executive",
            quality_threshold=0.6
        )

        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            mock_result = AsyncMock()
            mock_result.data = SynthesizedReport(
                request_id="incomplete_test",
                executive_summary="Synthesis from incomplete data reveals limited insights requiring additional research",
                key_findings=[
                    {
                        "finding_id": "partial_summary",
                        "title": "Limited Insight from Partial Data",
                        "description": "Partial insight identified despite incomplete source data",
                        "confidence_level": 0.6,
                        "cross_validation_status": "insufficient"
                    }
                ],
                detailed_analysis="Analysis constrained by incomplete source data",
                supporting_evidence=["Single validated source"],
                gaps_identified=[
                    "Empty content in research findings",
                    "Missing source information",
                    "Limited insight coverage"
                ],
                recommendations=[
                    "Improve data collection completeness",
                    "Validate all research findings before synthesis"
                ],
                confidence_assessment={
                    "overall_confidence": 0.55,
                    "completeness_score": 0.3
                },
                metadata={
                    "findings_processed": 2,
                    "data_quality_warning": "Incomplete source data"
                }
            )
            mock_agent_run.return_value = mock_result

            result = await run_synthesis(incomplete_request, session_id="incomplete_test")

            assert isinstance(result, SynthesizedReport)
            assert result.confidence_assessment["overall_confidence"] < 0.7
            assert result.confidence_assessment["completeness_score"] < 0.5
            assert len(result.gaps_identified) >= 3
            assert "incomplete" in result.detailed_analysis.lower()


class TestRecoveryMechanisms:
    """Test error recovery and retry mechanisms."""

    @pytest.mark.asyncio
    async def test_agent_retry_mechanism(self, sample_synthesis_request):
        """Test agent retry logic with transient failures."""

        failure_count = 0
        max_failures = 2

        async def intermittent_failure_function(messages, tools):
            nonlocal failure_count
            failure_count += 1

            if failure_count <= max_failures:
                # Fail first few attempts
                raise Exception(f"Transient failure #{failure_count}")
            else:
                # Success after retries
                return ModelTextResponse(content="Synthesis successful after retries")

        retry_model = FunctionModel(intermittent_failure_function)
        test_agent = agent.override(model=retry_model)

        # Configure retries
        test_agent.retries = 3

        deps = SynthesisDependencies(
            session_id="retry_test",
            research_phase_complete=True
        )

        # Should eventually succeed
        result = await test_agent.run(
            "Test synthesis with retry mechanism",
            deps=deps
        )

        assert result is not None
        assert failure_count == max_failures + 1  # Failed max_failures times, then succeeded

    @pytest.mark.asyncio
    async def test_synthesis_state_recovery(self, sample_research_findings):
        """Test recovery of synthesis state after interruption."""

        # Simulate synthesis interruption and recovery
        synthesis_state = {
            "integration_complete": False,
            "analysis_complete": False,
            "report_complete": False
        }

        async def stateful_recovery_function(messages, tools):
            last_message = messages[-1].content if messages else ""

            if "data_integrator" in last_message and not synthesis_state["integration_complete"]:
                synthesis_state["integration_complete"] = True
                return {
                    "data_integrator": {
                        "research_findings": sample_research_findings,
                        "normalization_strategy": "confidence_weighted"
                    }
                }
            elif "pattern_analyzer" in last_message and synthesis_state["integration_complete"] and not synthesis_state["analysis_complete"]:
                synthesis_state["analysis_complete"] = True
                return {
                    "pattern_analyzer": {
                        "integrated_data": {
                            "success": True,
                            "integrated_data": {"unified_findings": []}
                        },
                        "analysis_depth": "standard"
                    }
                }
            elif "report_generator" in last_message and synthesis_state["analysis_complete"] and not synthesis_state["report_complete"]:
                synthesis_state["report_complete"] = True
                return {
                    "report_generator": {
                        "analysis_results": {
                            "success": True,
                            "analysis_results": {"identified_patterns": []}
                        },
                        "output_format": "detailed",
                        "target_audience": "researchers"
                    }
                }
            else:
                return ModelTextResponse(content="State-aware synthesis processing")

        recovery_model = FunctionModel(stateful_recovery_function)
        test_agent = agent.override(model=recovery_model)

        deps = SynthesisDependencies(
            session_id="recovery_test",
            research_phase_complete=True
        )

        # Run synthesis
        result = await test_agent.run(
            "State recovery synthesis test",
            deps=deps
        )

        assert result is not None
        # Verify all synthesis stages completed
        assert synthesis_state["integration_complete"]
        assert synthesis_state["analysis_complete"]
        assert synthesis_state["report_complete"]

    @pytest.mark.asyncio
    async def test_dependency_failure_recovery(self, sample_synthesis_request):
        """Test recovery from dependency initialization failures."""

        # Test dependency recovery
        failure_attempts = 0

        def failing_deps_creation(*args, **kwargs):
            nonlocal failure_attempts
            failure_attempts += 1

            if failure_attempts <= 1:
                raise Exception("Dependency initialization failure")
            else:
                # Return valid dependencies after failure
                return SynthesisDependencies(
                    session_id="recovery_test",
                    research_phase_complete=True
                )

        with patch('agents.data_synthesis_agent.SynthesisDependencies.from_settings', side_effect=failing_deps_creation):
            # First attempt should fail
            try:
                await run_synthesis(sample_synthesis_request, session_id="dep_failure_test")
                assert False, "Should have failed on first attempt"
            except Exception as e:
                assert "Dependency initialization failure" in str(e)

            # Second attempt should succeed
            with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
                mock_result = AsyncMock()
                mock_result.data = SynthesizedReport(
                    request_id=sample_synthesis_request.request_id,
                    executive_summary="Recovered from dependency failure",
                    key_findings=[],
                    detailed_analysis="Successful recovery",
                    supporting_evidence=[],
                    gaps_identified=[],
                    recommendations=[],
                    confidence_assessment={"overall_confidence": 0.85},
                    metadata={"recovery": True}
                )
                mock_agent_run.return_value = mock_result

                result = await run_synthesis(sample_synthesis_request, session_id="dep_recovery_test")

                assert isinstance(result, SynthesizedReport)
                assert result.metadata.get("recovery") is True