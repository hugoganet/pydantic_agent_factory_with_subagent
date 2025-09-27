"""Tests for Workflow Coordinator Agent tools."""

import pytest
from datetime import datetime, timedelta
from ..tools import check_agent_health, manage_workflow_state, route_agent_message
from ..models import AgentMessage


class TestCoordinatorTools:
    """Test cases for coordinator tools."""

    @pytest.mark.asyncio
    async def test_check_agent_health_single_agent(self, mock_dependencies):
        """Test health check for a single agent."""
        result = await check_agent_health(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            agent_id="test-agent-1"
        )

        assert isinstance(result, dict)
        assert "test-agent-1" in result
        assert result["test-agent-1"].agent_id == "test-agent-1"
        assert result["test-agent-1"].status in ["healthy", "degraded", "failed"]

    @pytest.mark.asyncio
    async def test_check_agent_health_all_agents(self, mock_dependencies):
        """Test health check for all agents."""
        result = await check_agent_health(
            ctx=type('MockContext', (), {'deps': mock_dependencies})()
        )

        assert isinstance(result, dict)
        assert len(result) == 3  # Should have all 3 mock agents

        for agent_id, health_status in result.items():
            assert agent_id in mock_dependencies.monitored_agents
            assert health_status.agent_id == agent_id
            assert health_status.status in ["healthy", "degraded", "failed"]
            assert health_status.response_time_ms >= 0
            assert 0 <= health_status.error_rate_percent <= 100

    @pytest.mark.asyncio
    async def test_check_agent_health_invalid_agent(self, mock_dependencies):
        """Test health check for invalid agent ID."""
        result = await check_agent_health(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            agent_id="invalid-agent-id"
        )

        assert isinstance(result, dict)
        assert len(result) == 0  # Should return empty dict for invalid agent

    @pytest.mark.asyncio
    async def test_manage_workflow_state_create(self, mock_dependencies):
        """Test workflow state creation."""
        workflow_id = "test-workflow-create"
        state_data = {
            "participating_agents": ["test-agent-1", "test-agent-2"],
            "coordination_type": "parallel"
        }

        result = await manage_workflow_state(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            workflow_id=workflow_id,
            action="create",
            state_data=state_data
        )

        assert result.workflow_id == workflow_id
        assert result.status == "pending"
        assert result.participating_agents == state_data["participating_agents"]
        assert result.current_phase == "initialization"
        assert result.progress_percent == 0.0

    @pytest.mark.asyncio
    async def test_manage_workflow_state_update(self, mock_dependencies):
        """Test workflow state update."""
        workflow_id = "test-workflow-update"

        # First create a workflow
        create_data = {"participating_agents": ["test-agent-1"]}
        await manage_workflow_state(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            workflow_id=workflow_id,
            action="create",
            state_data=create_data
        )

        # Then update it
        update_data = {
            "status": "running",
            "current_phase": "execution",
            "progress_percent": 50.0
        }

        result = await manage_workflow_state(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            workflow_id=workflow_id,
            action="update",
            state_data=update_data
        )

        assert result.workflow_id == workflow_id
        assert result.status == "running"
        assert result.current_phase == "execution"
        assert result.progress_percent == 50.0

    @pytest.mark.asyncio
    async def test_manage_workflow_state_get(self, mock_dependencies):
        """Test workflow state retrieval."""
        workflow_id = "test-workflow-get"

        # Create a workflow first
        create_data = {"participating_agents": ["test-agent-1"]}
        created = await manage_workflow_state(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            workflow_id=workflow_id,
            action="create",
            state_data=create_data
        )

        # Then retrieve it
        result = await manage_workflow_state(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            workflow_id=workflow_id,
            action="get"
        )

        assert result.workflow_id == workflow_id
        assert result.status == created.status
        assert result.participating_agents == created.participating_agents

    @pytest.mark.asyncio
    async def test_manage_workflow_state_delete(self, mock_dependencies):
        """Test workflow state deletion."""
        workflow_id = "test-workflow-delete"

        # Create a workflow first
        create_data = {"participating_agents": ["test-agent-1"]}
        await manage_workflow_state(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            workflow_id=workflow_id,
            action="create",
            state_data=create_data
        )

        # Then delete it
        result = await manage_workflow_state(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            workflow_id=workflow_id,
            action="delete"
        )

        assert result.workflow_id == workflow_id
        assert result.status == "deleted"

    @pytest.mark.asyncio
    async def test_manage_workflow_state_invalid_action(self, mock_dependencies):
        """Test workflow state management with invalid action."""
        result = await manage_workflow_state(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            workflow_id="test-invalid-action",
            action="invalid"
        )

        assert result.status == "failed"
        assert result.error_details is not None

    @pytest.mark.asyncio
    async def test_route_agent_message_valid(self, mock_dependencies, sample_agent_message):
        """Test routing valid agent message."""
        result = await route_agent_message(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            message=sample_agent_message,
            validate_dependencies=True
        )

        assert result.message_id == sample_agent_message.message_id
        assert result.routing_status == "queued"
        assert result.delivery_time_ms is not None
        assert result.delivery_time_ms >= 0

    @pytest.mark.asyncio
    async def test_route_agent_message_invalid_sender(self, mock_dependencies):
        """Test routing message with invalid sender."""
        invalid_message = AgentMessage(
            sender_id="invalid-sender",
            recipient_id="test-agent-1",
            message_type="task",
            payload={"test": "data"},
            correlation_id="test-123"
        )

        result = await route_agent_message(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            message=invalid_message,
            validate_dependencies=True
        )

        assert result.routing_status == "rejected"
        assert "Unknown sender agent" in result.error_message

    @pytest.mark.asyncio
    async def test_route_agent_message_invalid_recipient(self, mock_dependencies):
        """Test routing message with invalid recipient."""
        invalid_message = AgentMessage(
            sender_id="test-agent-1",
            recipient_id="invalid-recipient",
            message_type="task",
            payload={"test": "data"},
            correlation_id="test-123"
        )

        result = await route_agent_message(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            message=invalid_message,
            validate_dependencies=True
        )

        assert result.routing_status == "rejected"
        assert "Unknown recipient agent" in result.error_message

    @pytest.mark.asyncio
    async def test_route_agent_message_no_validation(self, mock_dependencies):
        """Test routing message without dependency validation."""
        invalid_message = AgentMessage(
            sender_id="unknown-sender",
            recipient_id="unknown-recipient",
            message_type="task",
            payload={"test": "data"},
            correlation_id="test-123"
        )

        result = await route_agent_message(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            message=invalid_message,
            validate_dependencies=False
        )

        # Should succeed without validation
        assert result.routing_status == "queued"

    @pytest.mark.asyncio
    async def test_route_agent_message_missing_ids(self, mock_dependencies):
        """Test routing message with missing sender/recipient IDs."""
        invalid_message = AgentMessage(
            sender_id="",
            recipient_id="test-agent-1",
            message_type="task",
            payload={"test": "data"},
            correlation_id="test-123"
        )

        result = await route_agent_message(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            message=invalid_message
        )

        assert result.routing_status == "rejected"
        assert "Missing sender_id or recipient_id" in result.error_message

    @pytest.mark.asyncio
    async def test_health_check_metrics_recording(self, mock_dependencies):
        """Test that health checks record metrics properly."""
        initial_metrics = mock_dependencies.metrics_collector.get_metrics()
        initial_count = len(initial_metrics)

        await check_agent_health(
            ctx=type('MockContext', (), {'deps': mock_dependencies})(),
            agent_id="test-agent-1"
        )

        updated_metrics = mock_dependencies.metrics_collector.get_metrics()

        # Should have recorded response time and error rate metrics
        assert len(updated_metrics) > initial_count
        assert any("test-agent-1" in key for key in updated_metrics.keys())