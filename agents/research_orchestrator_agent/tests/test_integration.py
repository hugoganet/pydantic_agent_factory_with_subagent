"""
Test inter-agent communication and integration for Research Orchestrator Agent.
Tests Redis communication patterns, agent coordination workflows, and system integration.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import uuid

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import orchestrator_agent, run_orchestration
from ..dependencies import OrchestratorDependencies
from ..tools import AgentMessage, TaskAssignment
from .conftest import create_orchestration_function_model


class TestRedisIntegration:
    """Test Redis integration for inter-agent messaging."""

    @pytest.mark.asyncio
    async def test_redis_connection_initialization(self, test_dependencies):
        """Test Redis connection setup and health check."""
        await test_dependencies.setup_infrastructure()

        assert test_dependencies.redis_client is not None

        # Test ping
        pong = await test_dependencies.redis_client.ping()
        assert pong is True

    @pytest.mark.asyncio
    async def test_agent_message_queuing(self, test_dependencies, mock_redis):
        """Test agent message queuing via Redis."""
        message = AgentMessage(
            recipient_id="web_research_agent",
            message_type="task",
            payload={"query": "test query"},
            correlation_id="test_correlation"
        )

        # Queue the message
        queue_name = f"agent_queue:{message.recipient_id}"
        await test_dependencies.redis_client.lpush(
            queue_name,
            message.model_dump_json()
        )

        # Verify message was queued
        mock_redis.lpush.assert_called_once()
        call_args = mock_redis.lpush.call_args
        assert call_args[0][0] == queue_name

        # Verify message structure
        queued_message = json.loads(call_args[0][1])
        assert queued_message["recipient_id"] == "web_research_agent"
        assert queued_message["message_type"] == "task"

    @pytest.mark.asyncio
    async def test_execution_plan_storage(self, test_dependencies, mock_redis, sample_execution_plan):
        """Test execution plan storage in Redis."""
        plan_id = sample_execution_plan["strategy_id"]
        plan_key = f"execution_plan:{plan_id}"

        # Store the plan
        await test_dependencies.redis_client.setex(
            plan_key,
            3600,  # 1 hour TTL
            json.dumps(sample_execution_plan, default=str)
        )

        # Verify storage
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == plan_key
        assert call_args[0][1] == 3600

    @pytest.mark.asyncio
    async def test_coordination_state_tracking(self, test_dependencies, mock_redis):
        """Test coordination state tracking in Redis."""
        correlation_id = str(uuid.uuid4())
        coordination_state = {
            "correlation_id": correlation_id,
            "execution_plan_id": "test_plan_123",
            "sent_messages": [
                {"message_id": "msg_1", "agent_id": "web_research", "status": "sent"},
                {"message_id": "msg_2", "agent_id": "tool_integration", "status": "sent"}
            ],
            "task_assignments": [],
            "status": "distributed",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Store coordination state
        state_key = f"coordination:{correlation_id}"
        await test_dependencies.redis_client.setex(
            state_key,
            3600,
            json.dumps(coordination_state, default=str)
        )

        # Verify storage
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == state_key

    @pytest.mark.asyncio
    async def test_redis_failure_recovery(self, test_dependencies):
        """Test graceful handling of Redis failures."""
        # Simulate Redis connection failure
        original_redis = test_dependencies.redis_client

        # Create a failing Redis mock
        failing_redis = AsyncMock()
        failing_redis.ping.side_effect = Exception("Redis connection lost")
        failing_redis.lpush.side_effect = Exception("Redis operation failed")

        test_dependencies.redis_client = failing_redis

        # Agent should handle Redis failures gracefully
        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run(
            "Test Redis failure handling",
            deps=test_dependencies
        )

        # Agent should still provide a response despite Redis issues
        assert result.data is not None

        # Restore original redis for cleanup
        test_dependencies.redis_client = original_redis


class TestAgentCoordinationWorkflow:
    """Test agent coordination workflows and task distribution."""

    @pytest.mark.asyncio
    async def test_parallel_agent_coordination(self, test_dependencies, sample_execution_plan):
        """Test coordination of parallel agents during research phase."""

        # Create function model that simulates full orchestration workflow
        orchestration_responses = [
            {"content": "Starting parallel agent coordination..."},
            {
                "type": "tool_call",
                "tool_call": {
                    "analyze_research_request": {
                        "query": "test research query",
                        "complexity": "medium",
                        "timeout_minutes": 10,
                        "quality_threshold": 0.8
                    }
                }
            },
            {"content": "Distributing tasks to parallel agents..."},
            {
                "type": "tool_call",
                "tool_call": {
                    "distribute_parallel_tasks": {
                        "execution_plan": sample_execution_plan,
                        "target_agents": ["web_research_agent", "tool_integration_agent"],
                        "max_parallel": 2
                    }
                }
            },
            {"content": "Coordinating quality assessment..."},
            {
                "type": "tool_call",
                "tool_call": {
                    "coordinate_quality_assessment": {
                        "research_results": [{"test": "result"}],
                        "quality_threshold": 0.8,
                        "confidence_threshold": 0.7
                    }
                }
            },
            {"content": "Orchestration workflow completed successfully"}
        ]

        function_model = create_orchestration_function_model(orchestration_responses)
        test_agent = orchestrator_agent.override(model=function_model)

        result = await test_agent.run(
            "Coordinate parallel research agents",
            deps=test_dependencies
        )

        assert result.data is not None
        assert "completed" in result.data.lower()

        # Verify phase progression
        messages = result.all_messages()
        tool_calls = [msg for msg in messages if msg.role == "tool-call"]

        # Should have calls to analyze, distribute, and coordinate
        tool_names = [call.tool_name for call in tool_calls]
        expected_tools = ["analyze_research_request", "distribute_parallel_tasks", "coordinate_quality_assessment"]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing expected tool call: {expected_tool}"

    @pytest.mark.asyncio
    async def test_sequential_workflow_phases(self, test_dependencies):
        """Test proper sequencing of workflow phases."""

        # Create a model that tracks phase transitions
        phase_tracker = []

        def track_phase_response():
            call_count = 0

            async def phase_function(messages, tools):
                nonlocal call_count

                if call_count == 0:
                    phase_tracker.append("analysis_start")
                    call_count += 1
                    return {
                        "analyze_research_request": {
                            "query": "test query",
                            "complexity": "simple",
                            "timeout_minutes": 10,
                            "quality_threshold": 0.8
                        }
                    }
                elif call_count == 1:
                    phase_tracker.append("distribution_start")
                    call_count += 1
                    return {
                        "distribute_parallel_tasks": {
                            "execution_plan": {"strategy_id": "test", "phases": {}},
                            "target_agents": ["test_agent"],
                            "max_parallel": 1
                        }
                    }
                elif call_count == 2:
                    phase_tracker.append("quality_start")
                    call_count += 1
                    return {
                        "coordinate_quality_assessment": {
                            "research_results": [{"test": "data"}],
                            "quality_threshold": 0.8,
                            "confidence_threshold": 0.7
                        }
                    }
                else:
                    phase_tracker.append("completion")
                    return ModelTextResponse(content="Workflow phases completed in sequence")

            return phase_function

        function_model = FunctionModel(track_phase_response())
        test_agent = orchestrator_agent.override(model=function_model)

        result = await test_agent.run(
            "Test sequential workflow phases",
            deps=test_dependencies
        )

        assert result.data is not None

        # Verify phases occurred in expected order
        assert len(phase_tracker) >= 3
        assert "analysis_start" in phase_tracker
        assert "distribution_start" in phase_tracker
        assert "quality_start" in phase_tracker

    @pytest.mark.asyncio
    async def test_task_dependency_management(self, test_dependencies):
        """Test handling of task dependencies across agents."""

        # Create execution plan with dependencies
        execution_plan_with_deps = {
            "strategy_id": str(uuid.uuid4()),
            "phases": {
                "research": {
                    "agents": ["web_research_agent", "tool_integration_agent"],
                    "parallel": True,
                    "duration_seconds": 180
                },
                "assessment": {
                    "agents": ["quality_assessment_agent"],
                    "parallel": False,
                    "duration_seconds": 60
                }
            }
        }

        dependencies = {
            "quality_assessment_agent": ["web_research_task", "tool_integration_task"]
        }

        # Test dependency-aware task distribution
        from ..tools import distribute_parallel_tasks_tool

        result = await distribute_parallel_tasks_tool(
            redis_client=test_dependencies.redis_client,
            execution_plan=execution_plan_with_deps,
            target_agents=["web_research_agent", "tool_integration_agent", "quality_assessment_agent"],
            max_parallel=3,
            dependencies=dependencies
        )

        assert result["success"] is True
        coordination_state = result["coordination_state"]

        # Verify dependencies were included in task assignments
        task_assignments = coordination_state.get("task_assignments", [])
        quality_tasks = [task for task in task_assignments if task.get("agent_id") == "quality_assessment_agent"]

        for quality_task in quality_tasks:
            assert "dependencies" in quality_task
            deps = quality_task["dependencies"]
            if deps:  # Only check if dependencies exist
                assert isinstance(deps, list)

    @pytest.mark.asyncio
    async def test_agent_health_monitoring(self, test_dependencies, mock_http_client):
        """Test agent health monitoring during coordination."""

        # Setup mock HTTP responses for agent health checks
        async def mock_health_response(url, **kwargs):
            response_mock = AsyncMock()
            if "web_research" in url:
                response_mock.json.return_value = {"status": "healthy", "agent_id": "web_research_agent"}
            elif "tool_integration" in url:
                response_mock.json.return_value = {"status": "degraded", "agent_id": "tool_integration_agent", "error": "High CPU usage"}
            else:
                response_mock.json.return_value = {"status": "healthy", "agent_id": "unknown_agent"}
            response_mock.status_code = 200
            return response_mock

        mock_http_client.get.side_effect = mock_health_response

        # Test health checking
        agent_endpoints = test_dependencies.agent_endpoints
        health_statuses = {}

        for agent_id, endpoint in agent_endpoints.items():
            try:
                response = await test_dependencies.http_client.get(f"{endpoint}/health")
                health_data = await response.json()
                health_statuses[agent_id] = health_data.get("status", "unknown")
            except Exception:
                health_statuses[agent_id] = "unreachable"

        # Should have collected health status for each agent
        assert len(health_statuses) > 0
        assert "web_research" in health_statuses or len(health_statuses) == len(agent_endpoints)

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, test_dependencies):
        """Test error recovery during agent coordination."""

        # Create a scenario where one agent fails
        def create_error_recovery_model():
            call_count = 0

            async def error_recovery_function(messages, tools):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First call succeeds
                    return {
                        "analyze_research_request": {
                            "query": "test query",
                            "timeout_minutes": 10,
                            "quality_threshold": 0.8
                        }
                    }
                elif call_count == 2:
                    # Second call fails (simulate agent failure)
                    return ModelTextResponse(content="Agent coordination failed, initiating recovery...")
                elif call_count == 3:
                    # Recovery attempt
                    return {
                        "distribute_parallel_tasks": {
                            "execution_plan": {"strategy_id": "recovery", "phases": {}},
                            "target_agents": ["backup_agent"],
                            "max_parallel": 1
                        }
                    }
                else:
                    return ModelTextResponse(content="Recovery completed with alternative agents")

            return error_recovery_function

        function_model = FunctionModel(create_error_recovery_model())
        test_agent = orchestrator_agent.override(model=function_model)

        result = await test_agent.run(
            "Test error recovery workflow",
            deps=test_dependencies
        )

        assert result.data is not None
        assert "recovery" in result.data.lower() or "completed" in result.data.lower()


class TestSystemHealthIntegration:
    """Test system health monitoring and crisis management."""

    @pytest.mark.asyncio
    async def test_crisis_mode_activation(self, test_dependencies):
        """Test activation of crisis management mode."""

        # Simulate degraded system health
        test_dependencies.system_health = {
            "status": "degraded",
            "error": "Multiple agent failures detected",
            "failed_agents": ["web_research_agent", "tool_integration_agent"],
            "timestamp": datetime.utcnow().isoformat()
        }

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run(
            "Handle system crisis",
            deps=test_dependencies
        )

        # Should complete despite crisis conditions
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_high_priority_mode(self, test_dependencies):
        """Test high-priority research mode handling."""

        # Set high priority level
        test_dependencies.priority_level = "high"

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run(
            "Urgent research request",
            deps=test_dependencies
        )

        assert result.data is not None

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, test_dependencies):
        """Test collection and tracking of performance metrics."""

        # Enable metrics collection
        test_dependencies.enable_metrics = True
        test_dependencies.execution_start_time = datetime.utcnow()

        # Simulate some task completion
        test_dependencies.completed_tasks["task_1"] = {
            "completion_time": datetime.utcnow(),
            "duration": 30
        }
        test_dependencies.active_tasks["task_2"] = {
            "start_time": datetime.utcnow(),
            "agent": "test_agent"
        }

        # Get metrics
        metrics = test_dependencies.get_task_metrics()

        assert "elapsed_seconds" in metrics
        assert "completed_tasks" in metrics
        assert "active_tasks" in metrics
        assert metrics["completed_tasks"] == 1
        assert metrics["active_tasks"] == 1


class TestWorkflowCoordinatorIntegration:
    """Test integration with Workflow Coordinator Agent."""

    @pytest.mark.asyncio
    async def test_system_health_reporting(self, test_dependencies, mock_http_client):
        """Test reporting system health to Workflow Coordinator."""

        # Mock successful health report
        async def mock_health_report(url, **kwargs):
            response_mock = AsyncMock()
            response_mock.json.return_value = {"status": "received", "timestamp": datetime.utcnow().isoformat()}
            response_mock.status_code = 200
            return response_mock

        mock_http_client.post.side_effect = mock_health_report

        # Simulate health reporting
        health_data = {
            "orchestrator_id": test_dependencies.session_id,
            "status": "healthy",
            "active_agents": len(test_dependencies.active_agents),
            "completed_tasks": len(test_dependencies.completed_tasks),
            "metrics": test_dependencies.get_task_metrics()
        }

        workflow_coordinator_endpoint = test_dependencies.agent_endpoints.get("workflow_coordinator")
        if workflow_coordinator_endpoint:
            response = await test_dependencies.http_client.post(
                f"{workflow_coordinator_endpoint}/health-report",
                json=health_data
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_performance_metrics_reporting(self, test_dependencies, mock_http_client):
        """Test performance metrics reporting to Workflow Coordinator."""

        # Setup some metrics
        test_dependencies.execution_start_time = datetime.utcnow() - timedelta(seconds=120)
        test_dependencies.completed_tasks = {
            "task_1": {"duration": 30},
            "task_2": {"duration": 45}
        }

        metrics = test_dependencies.get_task_metrics()
        assert metrics["elapsed_seconds"] >= 120
        assert metrics["completed_tasks"] == 2


class TestFullWorkflowIntegration:
    """Test complete workflow integration from request to final report."""

    @pytest.mark.asyncio
    async def test_complete_orchestration_workflow(self, test_dependencies, sample_research_request):
        """Test complete orchestration workflow end-to-end."""

        # Create comprehensive orchestration model
        complete_workflow_responses = [
            {"content": "Initiating comprehensive research orchestration workflow..."},

            # Phase 1: Analysis
            {
                "type": "tool_call",
                "tool_call": {
                    "analyze_research_request": {
                        "query": sample_research_request,
                        "complexity": "complex",
                        "timeout_minutes": 10,
                        "quality_threshold": 0.8
                    }
                }
            },
            {"content": "Strategic execution plan created. Proceeding to parallel research phase..."},

            # Phase 2: Parallel Research
            {
                "type": "tool_call",
                "tool_call": {
                    "distribute_parallel_tasks": {
                        "execution_plan": {
                            "strategy_id": "complete_workflow_test",
                            "phases": {
                                "research": {
                                    "agents": ["web_research_agent", "tool_integration_agent"],
                                    "parallel": True,
                                    "duration_seconds": 180
                                }
                            }
                        },
                        "target_agents": ["web_research_agent", "tool_integration_agent"],
                        "max_parallel": 2
                    }
                }
            },
            {"content": "Research agents coordinated. Awaiting results for quality assessment..."},

            # Phase 3: Quality Assessment
            {
                "type": "tool_call",
                "tool_call": {
                    "coordinate_quality_assessment": {
                        "research_results": [
                            {"source": "academic", "credibility_score": 0.92},
                            {"source": "industry", "credibility_score": 0.85}
                        ],
                        "quality_threshold": 0.8,
                        "confidence_threshold": 0.7
                    }
                }
            },
            {"content": "Quality assessment completed. Sources verified. Proceeding to final synthesis..."},

            # Phase 4: Final Synthesis
            {
                "type": "tool_call",
                "tool_call": {
                    "synthesize_final_report": {
                        "validated_data": [
                            {"source": "academic", "content": "validated research data"},
                            {"source": "industry", "content": "validated industry insights"}
                        ],
                        "citations": [
                            {"id": "ref_1", "citation_text": "Academic Source (2024)"}
                        ],
                        "synthesis_format": "comprehensive"
                    }
                }
            },

            {"content": "Comprehensive research report synthesized and delivered. Orchestration workflow completed successfully with all quality gates passed."}
        ]

        function_model = create_orchestration_function_model(complete_workflow_responses)
        test_agent = orchestrator_agent.override(model=function_model)

        # Execute complete workflow
        start_time = datetime.utcnow()
        result = await test_agent.run(sample_research_request, deps=test_dependencies)
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        # Verify completion
        assert result.data is not None
        assert "completed successfully" in result.data.lower()

        # Verify performance requirement (< 10 minutes)
        assert execution_time < 600, f"Workflow took {execution_time}s, exceeding 10-minute limit"

        # Verify all tool calls were made
        messages = result.all_messages()
        tool_calls = [msg for msg in messages if msg.role == "tool-call"]

        expected_tools = [
            "analyze_research_request",
            "distribute_parallel_tasks",
            "coordinate_quality_assessment",
            "synthesize_final_report"
        ]

        tool_names = [call.tool_name for call in tool_calls]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing expected tool call: {expected_tool}"

        # Verify workflow progression through phases
        text_responses = [msg.content for msg in messages if msg.role == "model-text-response"]
        workflow_content = " ".join(text_responses).lower()

        assert "analysis" in workflow_content or "strategic" in workflow_content
        assert "parallel" in workflow_content or "research" in workflow_content
        assert "quality" in workflow_content or "assessment" in workflow_content
        assert "synthesis" in workflow_content or "report" in workflow_content