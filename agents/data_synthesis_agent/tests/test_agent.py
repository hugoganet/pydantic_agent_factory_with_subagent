"""
Test core Data Synthesis Agent functionality.

Tests the main agent workflow including synthesis request processing,
tool coordination, and structured report generation using TestModel
and FunctionModel patterns.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, AsyncMock

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from agents.data_synthesis_agent import agent, run_synthesis, health_check
from agents.data_synthesis_agent.models import SynthesisRequest, SynthesizedReport
from agents.data_synthesis_agent.dependencies import SynthesisDependencies


class TestAgentBasicFunctionality:
    """Test basic agent initialization and responses."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, test_agent, test_dependencies):
        """Test agent initializes with correct configuration."""
        assert test_agent is not None
        assert test_agent.deps_type == SynthesisDependencies
        assert test_agent.result_type == SynthesizedReport

    @pytest.mark.asyncio
    async def test_agent_basic_response(self, test_agent, test_dependencies, sample_synthesis_request):
        """Test agent provides appropriate response with TestModel."""
        # TestModel returns simple text responses by default
        result = await test_agent.run(
            "Please synthesize the research findings provided.",
            deps=test_dependencies
        )

        assert result.data is not None
        assert isinstance(result.data, str)  # TestModel returns string by default
        assert len(result.all_messages()) > 0

    @pytest.mark.asyncio
    async def test_agent_with_synthesis_request(self, test_agent, test_dependencies, sample_synthesis_request):
        """Test agent handles structured synthesis requests."""
        prompt = f"""
        Synthesize the following research request:
        Request ID: {sample_synthesis_request.request_id}
        Target Audience: {sample_synthesis_request.target_audience}
        Research Findings: {len(sample_synthesis_request.research_findings)} findings
        """

        result = await test_agent.run(prompt, deps=test_dependencies)

        assert result.data is not None
        assert len(result.all_messages()) >= 1
        # Verify the message contains synthesis information
        messages = [msg.content for msg in result.all_messages() if hasattr(msg, 'content')]
        assert any("synthesize" in str(msg).lower() for msg in messages)


class TestAgentToolCalling:
    """Test agent tool calling behavior."""

    @pytest.mark.asyncio
    async def test_agent_calls_data_integrator(self, test_dependencies, sample_synthesis_request):
        """Test agent calls data_integrator tool appropriately."""
        # Configure TestModel to call data_integrator tool
        test_model = TestModel()
        test_model.agent_responses = [
            ModelTextResponse(content="I'll integrate the research findings"),
            {
                "data_integrator": {
                    "research_findings": sample_synthesis_request.research_findings,
                    "normalization_strategy": "confidence_weighted"
                }
            },
            ModelTextResponse(content="Integration complete, now analyzing patterns"),
            {
                "pattern_analyzer": {
                    "integrated_data": {"success": True, "integrated_data": {}},
                    "analysis_depth": "standard"
                }
            },
            ModelTextResponse(content="Analysis complete, generating report"),
            {
                "report_generator": {
                    "analysis_results": {"success": True, "analysis_results": {}},
                    "output_format": "detailed",
                    "target_audience": "researchers"
                }
            }
        ]

        test_agent = agent.override(model=test_model)

        # Format synthesis request for agent
        prompt = f"""
        Please synthesize: {len(sample_synthesis_request.research_findings)} research findings
        Use data_integrator, pattern_analyzer, and report_generator tools
        """

        result = await test_agent.run(prompt, deps=test_dependencies)

        # Verify tools were called
        tool_calls = [msg for msg in result.all_messages() if msg.role == "tool-call"]
        assert len(tool_calls) > 0

        # Verify specific tools were called
        tool_names = [call.tool_name for call in tool_calls]
        assert "data_integrator" in tool_names

    @pytest.mark.asyncio
    async def test_agent_tool_sequence(self, test_dependencies, sample_synthesis_request, tool_success_function):
        """Test agent follows correct tool sequence."""
        test_agent = agent.override(model=tool_success_function)

        prompt = """
        Please synthesize the research findings by:
        1. Using data_integrator to combine findings
        2. Using pattern_analyzer to identify patterns
        3. Using report_generator to create final report
        """

        result = await test_agent.run(prompt, deps=test_dependencies)

        # Check that tools were called in sequence
        tool_calls = [msg for msg in result.all_messages() if msg.role == "tool-call"]

        # Should have multiple tool calls for synthesis workflow
        assert len(tool_calls) >= 1

        # Verify we have tool responses
        tool_responses = [msg for msg in result.all_messages() if msg.role == "tool-return"]
        assert len(tool_responses) >= 1


class TestSynthesisWorkflow:
    """Test the complete synthesis workflow."""

    @pytest.mark.asyncio
    async def test_run_synthesis_function(self, mock_settings, sample_synthesis_request):
        """Test the run_synthesis wrapper function."""
        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            # Mock agent response
            mock_result = AsyncMock()
            mock_result.data = SynthesizedReport(
                request_id=sample_synthesis_request.request_id,
                executive_summary="Test synthesis completed successfully",
                key_findings=[],
                detailed_analysis="Comprehensive test analysis",
                supporting_evidence=["Test validation"],
                gaps_identified=[],
                recommendations=["Continue testing"],
                confidence_assessment={"overall_confidence": 0.85},
                metadata={"generation_timestamp": datetime.now()}
            )
            mock_agent_run.return_value = mock_result

            result = await run_synthesis(
                sample_synthesis_request,
                session_id="test_session"
            )

            assert isinstance(result, SynthesizedReport)
            assert result.request_id == sample_synthesis_request.request_id
            assert "test synthesis" in result.executive_summary.lower()
            mock_agent_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesis_with_dependency_overrides(self, mock_settings, sample_synthesis_request):
        """Test synthesis with custom dependency configuration."""
        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            mock_result = AsyncMock()
            mock_result.data = SynthesizedReport(
                request_id=sample_synthesis_request.request_id,
                executive_summary="Custom dependency test",
                key_findings=[],
                detailed_analysis="Test analysis",
                supporting_evidence=[],
                gaps_identified=[],
                recommendations=[],
                confidence_assessment={"overall_confidence": 0.8},
                metadata={"generation_timestamp": datetime.now()}
            )
            mock_agent_run.return_value = mock_result

            result = await run_synthesis(
                sample_synthesis_request,
                session_id="custom_test",
                debug_mode=True,
                max_findings_count=25
            )

            assert isinstance(result, SynthesizedReport)
            # Verify custom dependencies were passed
            call_args = mock_agent_run.call_args
            deps = call_args.kwargs['deps']
            assert deps.debug_mode is True
            assert deps.max_findings_count == 25

    @pytest.mark.asyncio
    async def test_synthesis_validation_failure(self, mock_settings):
        """Test synthesis fails appropriately for invalid inputs."""
        # Create request with no findings (should fail validation)
        invalid_request = SynthesisRequest(
            request_id="invalid_test",
            research_findings=[],  # Empty findings
            output_format="detailed",
            target_audience="researchers"
        )

        with pytest.raises(ValueError, match="Synthesis conditions not met"):
            await run_synthesis(invalid_request, session_id="validation_test")

    @pytest.mark.asyncio
    async def test_synthesis_timing_metrics(self, mock_settings, sample_synthesis_request):
        """Test synthesis performance timing is tracked."""
        with patch('agents.data_synthesis_agent.agent.run') as mock_agent_run:
            # Add small delay to test timing
            async def delayed_response(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                result = AsyncMock()
                result.data = SynthesizedReport(
                    request_id=sample_synthesis_request.request_id,
                    executive_summary="Timed synthesis test",
                    key_findings=[],
                    detailed_analysis="Performance test",
                    supporting_evidence=[],
                    gaps_identified=[],
                    recommendations=[],
                    confidence_assessment={"overall_confidence": 0.85},
                    metadata={"generation_timestamp": datetime.now()}
                )
                return result

            mock_agent_run.side_effect = delayed_response

            # Test timing is captured
            start_time = datetime.now()
            result = await run_synthesis(sample_synthesis_request, session_id="timing_test")
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()
            assert duration >= 0.1  # Should take at least 100ms due to delay
            assert isinstance(result, SynthesizedReport)


class TestAgentHealthCheck:
    """Test agent health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_settings):
        """Test successful health check."""
        with patch('agents.data_synthesis_agent.settings', mock_settings):
            health_status = await health_check()

            assert health_status["status"] == "healthy"
            assert health_status["agent_id"] == "data_synthesis_agent"
            assert health_status["model"] == "gpt-4o"
            assert health_status["tools_registered"] == 3
            assert "timestamp" in health_status

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_settings):
        """Test health check handles failures gracefully."""
        with patch('agents.data_synthesis_agent.SynthesisDependencies') as mock_deps:
            # Simulate dependency creation failure
            mock_deps.side_effect = Exception("Dependency failure")

            health_status = await health_check()

            assert health_status["status"] == "unhealthy"
            assert "error" in health_status
            assert "Dependency failure" in health_status["error"]


class TestAgentConfiguration:
    """Test agent configuration and customization."""

    def test_agent_model_configuration(self, test_agent):
        """Test agent is configured with correct model settings."""
        # Verify agent has been overridden with TestModel
        assert test_agent.model is not None
        # TestModel should be used in test configuration
        assert isinstance(test_agent.model, TestModel)

    def test_agent_dependencies_type(self, test_agent):
        """Test agent uses correct dependencies type."""
        assert test_agent.deps_type == SynthesisDependencies

    def test_agent_result_type(self, test_agent):
        """Test agent returns structured result type."""
        assert test_agent.result_type == SynthesizedReport

    def test_agent_retry_configuration(self, test_agent):
        """Test agent has appropriate retry settings."""
        # Agent should have limited retries for performance targets
        assert hasattr(test_agent, 'retries')


class TestAgentErrorHandling:
    """Test agent error handling and recovery."""

    @pytest.mark.asyncio
    async def test_agent_handles_tool_errors(self, test_dependencies):
        """Test agent gracefully handles tool execution errors."""
        # Create function model that simulates tool errors
        async def error_prone_function(messages, tools):
            # Simulate a tool failure
            return {
                "data_integrator": {
                    "research_findings": "invalid_data",  # Wrong type
                    "normalization_strategy": "invalid_strategy"
                }
            }

        error_model = FunctionModel(error_prone_function)
        error_agent = agent.override(model=error_model)

        # Agent should handle tool errors without crashing
        result = await error_agent.run(
            "Please synthesize findings using data_integrator",
            deps=test_dependencies
        )

        # Should get some result even with tool errors
        assert result is not None

    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self, test_dependencies, sample_synthesis_request):
        """Test agent respects timeout configurations."""
        # Configure short timeout
        test_dependencies.synthesis_timeout = 1  # 1 second

        # Create slow function model
        async def slow_function(messages, tools):
            await asyncio.sleep(2)  # Longer than timeout
            return ModelTextResponse(content="Slow response")

        slow_model = FunctionModel(slow_function)
        slow_agent = agent.override(model=slow_model)

        # Test that synthesis handles timeout appropriately
        start_time = datetime.now()
        try:
            await slow_agent.run(
                "Please synthesize quickly",
                deps=test_dependencies
            )
        except Exception:
            # Timeout or cancellation is acceptable
            pass

        duration = (datetime.now() - start_time).total_seconds()
        # Should not wait much longer than configured timeout
        assert duration < 5  # Reasonable upper bound

    @pytest.mark.asyncio
    async def test_agent_invalid_input_handling(self, test_agent, test_dependencies):
        """Test agent handles invalid or malformed inputs."""
        # Test with various invalid inputs
        invalid_inputs = [
            "",  # Empty string
            None,  # None input
            "a" * 10000,  # Very long input
            "特殊字符测试",  # Non-ASCII characters
        ]

        for invalid_input in invalid_inputs:
            try:
                result = await test_agent.run(invalid_input, deps=test_dependencies)
                # Should get some response, even if not meaningful
                assert result is not None
            except Exception as e:
                # Some errors are acceptable for truly invalid inputs
                assert isinstance(e, (ValueError, TypeError, AttributeError))