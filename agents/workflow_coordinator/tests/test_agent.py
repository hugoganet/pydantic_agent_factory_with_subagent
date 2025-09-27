"""Tests for the Workflow Coordinator Agent."""

import pytest
from datetime import datetime
from pydantic_ai import TestModel
from pydantic_ai.models import FunctionModel

from ..agent import workflow_coordinator_agent
from ..models import (
    SystemStatus,
    CoordinationRequest,
    CoordinationReport,
    AgentMessage
)


class TestWorkflowCoordinatorAgent:
    """Test cases for the Workflow Coordinator Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that the agent initializes correctly."""
        assert workflow_coordinator_agent is not None
        assert workflow_coordinator_agent.system_prompt is not None

    @pytest.mark.asyncio
    async def test_get_system_status(self, mock_dependencies):
        """Test system status retrieval."""
        # Use TestModel for predictable responses
        test_agent = workflow_coordinator_agent.override(
            model=TestModel(
                custom_result_text="System is healthy with all agents operational"
            )
        )

        # Use the get_system_status tool directly
        result = await workflow_coordinator_agent.get_system_status.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})()
        )

        assert isinstance(result, SystemStatus)
        assert result.overall_health in ["healthy", "degraded", "critical"]
        assert isinstance(result.agent_statuses, dict)
        assert isinstance(result.system_metrics, dict)
        assert isinstance(result.alerts, list)

    @pytest.mark.asyncio
    async def test_coordinate_workflow_parallel(self, mock_dependencies, sample_coordination_request):
        """Test parallel workflow coordination."""
        sample_coordination_request.coordination_type = "parallel"

        # Use the coordinate_workflow tool directly
        result = await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=sample_coordination_request
        )

        assert isinstance(result, CoordinationReport)
        assert result.workflow_id == sample_coordination_request.workflow_id
        assert "type" in result.execution_summary
        assert result.execution_summary["type"] == "parallel"
        assert isinstance(result.agent_performance, list)
        assert isinstance(result.recommendations, list)

    @pytest.mark.asyncio
    async def test_coordinate_workflow_sequential(self, mock_dependencies, sample_coordination_request):
        """Test sequential workflow coordination."""
        sample_coordination_request.coordination_type = "sequential"

        result = await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=sample_coordination_request
        )

        assert isinstance(result, CoordinationReport)
        assert result.execution_summary["type"] == "sequential"

    @pytest.mark.asyncio
    async def test_coordinate_workflow_pipeline(self, mock_dependencies, sample_coordination_request):
        """Test pipeline workflow coordination."""
        sample_coordination_request.coordination_type = "pipeline"
        sample_coordination_request.dependencies = {
            "test-agent-2": ["test-agent-1"]
        }

        result = await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=sample_coordination_request
        )

        assert isinstance(result, CoordinationReport)
        assert result.execution_summary["type"] == "pipeline"

    @pytest.mark.asyncio
    async def test_handle_message_routing(self, mock_dependencies, sample_agent_message):
        """Test message routing functionality."""
        result = await workflow_coordinator_agent.handle_message_routing.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            message=sample_agent_message
        )

        assert isinstance(result, str)
        assert sample_agent_message.message_id in result
        # Should be queued since both sender and recipient exist in mock deps

    @pytest.mark.asyncio
    async def test_agent_run_with_test_model(self, mock_dependencies):
        """Test running the agent with TestModel."""
        test_agent = workflow_coordinator_agent.override(
            model=TestModel(
                custom_result_text="System status: All 3 monitored agents are healthy. "
                                  "Overall system health is good with no alerts."
            )
        )

        result = await test_agent.run(
            "Get the current system status",
            deps=mock_dependencies
        )

        assert result.data is not None
        assert isinstance(result.data, str)
        assert "system" in result.data.lower()

    @pytest.mark.asyncio
    async def test_agent_run_health_check(self, mock_dependencies):
        """Test agent health check query."""
        test_agent = workflow_coordinator_agent.override(
            model=TestModel(
                custom_result_text="Health check completed. Monitored agents: "
                                  "test-agent-1 (healthy), test-agent-2 (healthy), test-agent-3 (healthy)"
            )
        )

        result = await test_agent.run(
            "Check health of all research agents",
            deps=mock_dependencies
        )

        assert result.data is not None
        assert "health" in result.data.lower()

    @pytest.mark.asyncio
    async def test_agent_with_function_model(self, mock_dependencies):
        """Test agent behavior with custom function model."""
        def custom_response(messages):
            """Custom response function for testing."""
            last_message = messages[-1].content if messages else ""

            if "status" in last_message.lower():
                return "System Status: All agents operational, 0 alerts, system health: healthy"
            elif "health" in last_message.lower():
                return "Health Check: All 3 agents responding normally with good performance metrics"
            else:
                return "Coordinator ready to assist with workflow management"

        function_agent = workflow_coordinator_agent.override(
            model=FunctionModel(custom_response)
        )

        # Test system status query
        result = await function_agent.run(
            "What is the current system status?",
            deps=mock_dependencies
        )
        assert "System Status" in result.data

        # Test health check query
        result = await function_agent.run(
            "Perform health check on all agents",
            deps=mock_dependencies
        )
        assert "Health Check" in result.data

    @pytest.mark.asyncio
    async def test_error_handling_invalid_workflow_type(self, mock_dependencies):
        """Test error handling for invalid workflow coordination type."""
        invalid_request = CoordinationRequest(
            workflow_id="test-invalid-workflow",
            participating_agents=["test-agent-1"],
            coordination_type="invalid",  # Invalid type
            dependencies={},
            timeout_settings={},
            retry_policies={}
        )

        # This should handle the invalid type gracefully
        result = await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=invalid_request
        )

        assert isinstance(result, CoordinationReport)
        # Should still return a report, possibly with errors

    @pytest.mark.asyncio
    async def test_message_routing_invalid_agent(self, mock_dependencies):
        """Test message routing with invalid agent ID."""
        invalid_message = AgentMessage(
            sender_id="invalid-agent",
            recipient_id="test-agent-1",
            message_type="task",
            payload={"test": "data"},
            correlation_id="test-123"
        )

        result = await workflow_coordinator_agent.handle_message_routing.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            message=invalid_message
        )

        assert isinstance(result, str)
        assert "rejected" in result.lower() or "unknown" in result.lower()

    @pytest.mark.asyncio
    async def test_workflow_coordination_too_many_parallel_agents(self, mock_dependencies):
        """Test coordination with too many parallel agents."""
        overloaded_request = CoordinationRequest(
            workflow_id="test-overloaded",
            participating_agents=["agent-1", "agent-2", "agent-3", "agent-4", "agent-5", "agent-6"],  # More than max
            coordination_type="parallel",
            dependencies={},
            timeout_settings={},
            retry_policies={}
        )

        result = await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=overloaded_request
        )

        assert isinstance(result, CoordinationReport)
        # Should include warnings about too many parallel agents
        assert len(result.error_summary.get("warnings", [])) > 0 or len(result.recommendations) > 0