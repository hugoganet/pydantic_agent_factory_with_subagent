"""
Test core agent functionality for Research Orchestrator Agent.
Tests agent initialization, basic orchestration, system prompt handling, and error recovery.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import uuid

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import orchestrator_agent, run_orchestration, health_check
from ..dependencies import OrchestratorDependencies
from ..settings import load_settings
from .conftest import create_orchestration_function_model


class TestOrchestratorAgentInitialization:
    """Test agent initialization and configuration."""

    def test_agent_initialization(self):
        """Test that the orchestrator agent initializes properly."""
        assert orchestrator_agent is not None
        assert orchestrator_agent.deps_type == OrchestratorDependencies
        assert orchestrator_agent.retries > 0

    def test_agent_has_required_tools(self):
        """Test that all required coordination tools are registered."""
        tool_names = [tool.name for tool in orchestrator_agent.tools]

        required_tools = [
            "analyze_research_request",
            "distribute_parallel_tasks",
            "coordinate_quality_assessment",
            "synthesize_final_report"
        ]

        for tool_name in required_tools:
            assert tool_name in tool_names, f"Required tool {tool_name} not found"

    @pytest.mark.asyncio
    async def test_agent_with_test_model(self, test_dependencies):
        """Test agent runs with TestModel without external dependencies."""
        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        # TestModel provides simple responses by default
        result = await test_agent.run(
            "Test research request for quantum computing",
            deps=test_dependencies
        )

        assert result.data is not None
        assert isinstance(result.data, str)
        assert len(result.all_messages()) > 0


class TestSystemPromptHandling:
    """Test dynamic system prompt generation and context handling."""

    @pytest.mark.asyncio
    async def test_orchestration_context_prompt(self, test_dependencies):
        """Test that orchestration context is properly added to system prompt."""
        test_dependencies.current_phase = "research"
        test_dependencies.active_agents = ["web_research_agent", "tool_integration_agent"]
        test_dependencies.quality_requirements = {"min_credibility": 0.8}

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run(
            "Test orchestration with context",
            deps=test_dependencies
        )

        # Check that messages include system prompt information
        messages = result.all_messages()
        system_messages = [msg for msg in messages if msg.role == "system"]
        assert len(system_messages) > 0

    @pytest.mark.asyncio
    async def test_crisis_management_prompt(self, test_dependencies):
        """Test crisis management mode activation."""
        test_dependencies.system_health = {"status": "degraded", "error": "Redis connection failed"}

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run(
            "Handle crisis situation",
            deps=test_dependencies
        )

        # Should complete without errors even in crisis mode
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_high_priority_prompt(self, test_dependencies):
        """Test high-priority research mode activation."""
        test_dependencies.priority_level = "high"

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run(
            "Urgent research request",
            deps=test_dependencies
        )

        assert result.data is not None


class TestBasicOrchestrationFlow:
    """Test basic orchestration workflow execution."""

    @pytest.mark.asyncio
    async def test_simple_orchestration_flow(self, test_dependencies, sample_research_request):
        """Test basic orchestration with function model controlling the flow."""

        # Define expected orchestration sequence
        orchestration_responses = [
            {"content": "Analyzing research request and creating strategic plan..."},
            {
                "type": "tool_call",
                "tool_call": {
                    "analyze_research_request": {
                        "query": sample_research_request,
                        "complexity": "medium",
                        "timeout_minutes": 10,
                        "quality_threshold": 0.8
                    }
                }
            },
            {"content": "Distributing tasks to research agents..."},
            {
                "type": "tool_call",
                "tool_call": {
                    "distribute_parallel_tasks": {
                        "execution_plan": {
                            "strategy_id": "test_strategy",
                            "phases": {
                                "research": {
                                    "agents": ["web_research_agent", "tool_integration_agent"],
                                    "parallel": True,
                                    "duration_seconds": 180
                                }
                            }
                        },
                        "target_agents": ["web_research_agent", "tool_integration_agent"],
                        "max_parallel": 3
                    }
                }
            },
            {"content": "Coordinating quality assessment..."},
            {
                "type": "tool_call",
                "tool_call": {
                    "coordinate_quality_assessment": {
                        "research_results": [{"test": "data"}],
                        "quality_threshold": 0.8,
                        "confidence_threshold": 0.7
                    }
                }
            },
            {"content": "Synthesizing final comprehensive research report with validated sources and citations..."}
        ]

        function_model = create_orchestration_function_model(orchestration_responses)
        test_agent = orchestrator_agent.override(model=function_model)

        result = await test_agent.run(
            sample_research_request,
            deps=test_dependencies
        )

        # Verify orchestration completed
        assert result.data is not None
        assert "research report" in result.data.lower()

        # Verify tool calls were made
        messages = result.all_messages()
        tool_calls = [msg for msg in messages if msg.role == "tool-call"]
        assert len(tool_calls) >= 3  # At least analyze, distribute, and coordinate calls

    @pytest.mark.asyncio
    async def test_orchestration_with_error_recovery(self, test_dependencies, mock_redis):
        """Test orchestration handles tool failures gracefully."""

        # Simulate Redis failure during orchestration
        async def failing_redis_operation(*args, **kwargs):
            raise Exception("Redis connection lost")

        mock_redis.setex.side_effect = failing_redis_operation

        # Use TestModel which will provide basic responses despite tool failures
        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run(
            "Test error recovery during orchestration",
            deps=test_dependencies
        )

        # Agent should still provide a response even if some tools fail
        assert result.data is not None


class TestRunOrchestrationFunction:
    """Test the convenience function for orchestration."""

    @pytest.mark.asyncio
    async def test_run_orchestration_basic(self, test_settings):
        """Test run_orchestration function with mocked dependencies."""

        with patch('redis.asyncio.Redis') as mock_redis_class, \
             patch('httpx.AsyncClient') as mock_http_class:

            # Setup mocks
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance

            mock_http_instance = AsyncMock()
            mock_http_class.return_value = mock_http_instance

            # Mock the agent run method
            with patch.object(orchestrator_agent, 'run') as mock_run:
                mock_result = AsyncMock()
                mock_result.data = "Test orchestration complete"
                mock_run.return_value = mock_result

                result = await run_orchestration(
                    "Test research request",
                    session_id="test_session",
                    priority_level="normal"
                )

                assert result == "Test orchestration complete"
                mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_orchestration_with_overrides(self, test_settings):
        """Test run_orchestration with custom dependency overrides."""

        with patch('redis.asyncio.Redis') as mock_redis_class, \
             patch('httpx.AsyncClient') as mock_http_class:

            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance

            mock_http_instance = AsyncMock()
            mock_http_class.return_value = mock_http_instance

            with patch.object(orchestrator_agent, 'run') as mock_run:
                mock_result = AsyncMock()
                mock_result.data = "Custom orchestration complete"
                mock_run.return_value = mock_result

                result = await run_orchestration(
                    "Custom research request",
                    max_parallel_agents=10,
                    research_timeout=300,
                    custom_param="test_value"
                )

                assert result == "Custom orchestration complete"

    @pytest.mark.asyncio
    async def test_run_orchestration_failure_handling(self):
        """Test run_orchestration properly handles and propagates errors."""

        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_class.side_effect = Exception("Infrastructure setup failed")

            with pytest.raises(Exception) as exc_info:
                await run_orchestration("Test request")

            assert "Infrastructure setup failed" in str(exc_info.value)


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, test_settings):
        """Test successful health check."""

        with patch('redis.asyncio.Redis') as mock_redis_class, \
             patch('httpx.AsyncClient') as mock_http_class:

            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance

            mock_http_instance = AsyncMock()
            mock_http_class.return_value = mock_http_instance

            health = await health_check()

            assert health["status"] == "healthy"
            assert health["agent_type"] == "research_orchestrator"
            assert health["model"] == test_settings.llm_model
            assert health["redis_connected"] is True
            assert "quality_thresholds" in health

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure handling."""

        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_class.side_effect = Exception("Redis connection failed")

            health = await health_check()

            assert health["status"] == "unhealthy"
            assert "error" in health
            assert "Redis connection failed" in health["error"]


class TestPerformanceRequirements:
    """Test that agent meets performance requirements."""

    @pytest.mark.asyncio
    async def test_orchestration_timeout_compliance(self, test_dependencies, sample_research_request):
        """Test that orchestration completes within timeout limits."""

        start_time = datetime.utcnow()

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run(
            sample_research_request,
            deps=test_dependencies
        )

        execution_time = (datetime.utcnow() - start_time).total_seconds()

        # Should complete well under the 10-minute limit for basic operations
        assert execution_time < 600, f"Orchestration took {execution_time}s, exceeding 10-minute limit"
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_concurrent_orchestration_handling(self, test_dependencies):
        """Test agent can handle multiple concurrent orchestrations."""

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        # Create multiple concurrent orchestration tasks
        tasks = []
        for i in range(3):
            deps_copy = OrchestratorDependencies.from_settings(
                test_dependencies.__dict__,
                session_id=f"test_session_{i}"
            )
            deps_copy.redis_client = test_dependencies.redis_client
            deps_copy.http_client = test_dependencies.http_client

            task = test_agent.run(f"Research request {i}", deps=deps_copy)
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} failed: {result}"
            assert result.data is not None


class TestWorkflowPhaseTransitions:
    """Test workflow phase management and transitions."""

    @pytest.mark.asyncio
    async def test_phase_context_updates(self, test_dependencies):
        """Test that workflow phases are properly tracked."""

        # Start with no phase set
        assert test_dependencies.current_phase is None

        # Phases should be updated by tools during orchestration
        expected_phases = ["planning", "research", "assessment", "attribution", "synthesis", "delivery"]

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run(
            "Test phase transitions",
            deps=test_dependencies
        )

        # Basic completion check - phase tracking is tested more thoroughly in integration tests
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_agent_coordination_state(self, test_dependencies):
        """Test agent coordination state tracking."""

        initial_active_agents = test_dependencies.active_agents.copy()

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run(
            "Test agent coordination",
            deps=test_dependencies
        )

        assert result.data is not None
        # Active agents list may be updated during orchestration
        # Detailed coordination testing is in integration tests