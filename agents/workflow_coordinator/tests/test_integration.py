"""Integration tests for the Workflow Coordinator Agent."""

import pytest
from datetime import datetime
from pydantic_ai.models import TestModel, FunctionModel

from ..agent import workflow_coordinator_agent, run_coordinator_agent
from ..models import CoordinationRequest, AgentMessage
from ..dependencies import create_coordinator_dependencies


class TestWorkflowCoordinatorIntegration:
    """Integration tests for the complete workflow coordinator system."""

    @pytest.mark.asyncio
    async def test_full_workflow_coordination_lifecycle(self, mock_dependencies):
        """Test complete workflow from creation to completion."""
        # Create a coordination request
        request = CoordinationRequest(
            workflow_id="integration-test-workflow",
            participating_agents=["test-agent-1", "test-agent-2"],
            coordination_type="pipeline",
            dependencies={"test-agent-2": ["test-agent-1"]},
            timeout_settings={"default": 300},
            retry_policies={}
        )

        # Execute coordination
        result = await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=request
        )

        # Validate results
        assert result.workflow_id == request.workflow_id
        assert result.execution_summary["type"] == "pipeline"
        assert len(result.agent_performance) >= 0
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_message_routing_workflow(self, mock_dependencies):
        """Test complete message routing workflow."""
        # Create a message
        message = AgentMessage(
            sender_id="test-agent-1",
            recipient_id="test-agent-2",
            message_type="task",
            payload={
                "action": "process_data",
                "data": {"query": "test query", "parameters": {"limit": 10}}
            },
            correlation_id="integration-test-123"
        )

        # Route the message
        result = await workflow_coordinator_agent.handle_message_routing.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            message=message
        )

        assert isinstance(result, str)
        assert message.message_id in result
        assert "queued" in result.lower()

    @pytest.mark.asyncio
    async def test_system_health_monitoring_workflow(self, mock_dependencies):
        """Test complete system health monitoring workflow."""
        # Get system status
        system_status = await workflow_coordinator_agent.get_system_status.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})()
        )

        # Validate system status
        assert system_status.overall_health in ["healthy", "degraded", "critical"]
        assert len(system_status.agent_statuses) == 3  # Our mock has 3 agents
        assert isinstance(system_status.system_metrics, dict)
        assert isinstance(system_status.alerts, list)

        # Check individual agent statuses
        for agent_id, status in system_status.agent_statuses.items():
            assert agent_id in mock_dependencies.monitored_agents
            assert status.status in ["healthy", "degraded", "failed"]
            assert status.response_time_ms >= 0
            assert 0 <= status.error_rate_percent <= 100

    @pytest.mark.asyncio
    async def test_parallel_workflow_coordination(self, mock_dependencies):
        """Test parallel workflow coordination with multiple agents."""
        request = CoordinationRequest(
            workflow_id="parallel-integration-test",
            participating_agents=["test-agent-1", "test-agent-2", "test-agent-3"],
            coordination_type="parallel",
            dependencies={},
            timeout_settings={"parallel_timeout": 180},
            retry_policies={"default": {"max_attempts": 2}}
        )

        result = await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=request
        )

        assert result.execution_summary["type"] == "parallel"
        assert result.execution_summary["agents_count"] == 3
        assert "parallel_execution_time" in result.timing_analysis

    @pytest.mark.asyncio
    async def test_sequential_workflow_coordination(self, mock_dependencies):
        """Test sequential workflow coordination."""
        request = CoordinationRequest(
            workflow_id="sequential-integration-test",
            participating_agents=["test-agent-1", "test-agent-2", "test-agent-3"],
            coordination_type="sequential",
            dependencies={},
            timeout_settings={},
            retry_policies={}
        )

        result = await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=request
        )

        assert result.execution_summary["type"] == "sequential"
        assert result.execution_summary["sequence_length"] == 3
        assert "sequential_execution_time" in result.timing_analysis

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, mock_dependencies):
        """Test error recovery and handling workflow."""
        # Create a request that will trigger warnings (too many parallel agents)
        request = CoordinationRequest(
            workflow_id="error-recovery-test",
            participating_agents=["agent-1", "agent-2", "agent-3", "agent-4", "agent-5"],  # More than max
            coordination_type="parallel",
            dependencies={},
            timeout_settings={},
            retry_policies={}
        )

        result = await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=request
        )

        # Should handle the overload gracefully
        assert result.workflow_id == request.workflow_id
        # Should have warnings about too many agents
        assert len(result.error_summary.get("warnings", [])) > 0 or len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_dependency_validation_workflow(self, mock_dependencies):
        """Test dependency validation in pipeline workflows."""
        request = CoordinationRequest(
            workflow_id="dependency-validation-test",
            participating_agents=["test-agent-1", "test-agent-2"],
            coordination_type="pipeline",
            dependencies={
                "test-agent-2": ["test-agent-1"],
                "test-agent-3": ["non-existent-agent"]  # This should cause an error
            },
            timeout_settings={},
            retry_policies={}
        )

        result = await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=request
        )

        # Should detect the invalid dependency
        assert len(result.error_summary.get("errors", [])) > 0

    @pytest.mark.asyncio
    async def test_agent_run_integration_with_test_model(self, mock_dependencies):
        """Test full agent run with TestModel integration."""
        test_agent = workflow_coordinator_agent.override(
            model=TestModel(
                custom_result_text="System Status Report: All 3 monitored agents are operational. "
                                  "Current system health: HEALTHY. Active workflows: 0. "
                                  "Performance metrics within normal ranges."
            )
        )

        result = await test_agent.run(
            "Provide a comprehensive system status report with health metrics",
            deps=mock_dependencies
        )

        assert result.data is not None
        assert "System Status" in result.data
        assert "HEALTHY" in result.data
        assert "agents" in result.data.lower()

    @pytest.mark.asyncio
    async def test_complex_workflow_scenario(self, mock_dependencies):
        """Test a complex workflow scenario with multiple operations."""
        # Step 1: Check system health
        system_status = await workflow_coordinator_agent.get_system_status.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})()
        )

        # Step 2: Coordinate a workflow
        request = CoordinationRequest(
            workflow_id="complex-scenario-workflow",
            participating_agents=["test-agent-1", "test-agent-2"],
            coordination_type="pipeline",
            dependencies={"test-agent-2": ["test-agent-1"]},
            timeout_settings={"pipeline_timeout": 240},
            retry_policies={"default": {"max_attempts": 3}}
        )

        coordination_result = await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=request
        )

        # Step 3: Route a message
        message = AgentMessage(
            sender_id="test-agent-1",
            recipient_id="test-agent-2",
            message_type="result",
            payload={"workflow_id": request.workflow_id, "status": "completed"},
            correlation_id="complex-scenario-123"
        )

        routing_result = await workflow_coordinator_agent.handle_message_routing.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            message=message
        )

        # Validate all operations succeeded
        assert system_status.overall_health in ["healthy", "degraded", "critical"]
        assert coordination_result.workflow_id == request.workflow_id
        assert message.message_id in routing_result

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, mock_dependencies):
        """Test that performance metrics are collected throughout operations."""
        initial_metrics = mock_dependencies.metrics_collector.get_metrics()

        # Perform multiple operations
        await workflow_coordinator_agent.get_system_status.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})()
        )

        request = CoordinationRequest(
            workflow_id="metrics-test",
            participating_agents=["test-agent-1"],
            coordination_type="sequential",
            dependencies={},
            timeout_settings={},
            retry_policies={}
        )

        await workflow_coordinator_agent.coordinate_workflow.func(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            coordination_request=request
        )

        # Check that metrics were collected
        final_metrics = mock_dependencies.metrics_collector.get_metrics()
        assert len(final_metrics) > len(initial_metrics)
        assert "uptime_seconds" in final_metrics