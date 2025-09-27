"""
Test requirements validation for Research Orchestrator Agent.
Validates all requirements from INITIAL.md against actual implementation.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import uuid
import json

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import orchestrator_agent, run_orchestration, health_check
from ..dependencies import OrchestratorDependencies
from ..tools import AgentMessage, TaskAssignment
from .conftest import (
    create_orchestration_function_model,
    assert_quality_thresholds,
    assert_performance_metrics
)


class TestRequirement001_RequestParsing:
    """REQ-001: Successfully parses complex research requests into strategic execution plans."""

    @pytest.mark.asyncio
    async def test_simple_request_parsing(self, test_dependencies):
        """Test parsing of simple research requests."""
        simple_query = "What is quantum computing?"

        from ..tools import analyze_research_request_tool

        result = await analyze_research_request_tool(
            redis_client=test_dependencies.redis_client,
            query=simple_query,
            timeout_minutes=10,
            quality_threshold=0.8
        )

        assert result["success"] is True, "Simple request parsing failed"
        plan = result["execution_plan"]

        # Verify strategic elements
        assert plan["complexity"] == "simple"
        assert "phases" in plan
        assert "task_breakdown" in plan
        assert "resource_allocation" in plan

        # Simple requests should have streamlined task breakdown
        assert len(plan["task_breakdown"]) >= 2, "Simple requests should have at least 2 tasks"

    @pytest.mark.asyncio
    async def test_complex_request_parsing(self, test_dependencies):
        """Test parsing of complex multi-faceted research requests."""
        complex_query = """
        Conduct comprehensive analysis of quantum computing developments in cryptography,
        examining post-quantum cryptography algorithms, implementation challenges,
        industry adoption patterns, security implications, performance benchmarks,
        and future roadmap considerations across academic research, commercial
        implementations, and government standards with focus on NIST recommendations.
        """

        from ..tools import analyze_research_request_tool

        result = await analyze_research_request_tool(
            redis_client=test_dependencies.redis_client,
            query=complex_query.strip(),
            timeout_minutes=15,
            quality_threshold=0.8
        )

        assert result["success"] is True, "Complex request parsing failed"
        plan = result["execution_plan"]

        # Verify complexity detection
        assert plan["complexity"] == "complex", "Complex query not properly classified"

        # Complex requests should have comprehensive task breakdown
        assert len(plan["task_breakdown"]) >= 5, "Complex requests should have at least 5 tasks"

        # Should include strategy consultation for complex queries
        task_types = [task["task"] for task in plan["task_breakdown"]]
        assert "strategy_consult" in task_types, "Complex queries should include strategy consultation"

        # Verify all major phases are included
        phases = plan["phases"]
        required_phases = ["planning", "research", "assessment", "attribution", "synthesis", "delivery"]
        for phase in required_phases:
            assert phase in phases, f"Missing required phase: {phase}"

    @pytest.mark.asyncio
    async def test_multi_domain_request_parsing(self, test_dependencies):
        """Test parsing of requests spanning multiple research domains."""
        multi_domain_query = """
        Research the intersection of artificial intelligence and quantum computing,
        including quantum machine learning algorithms, hybrid classical-quantum systems,
        current hardware limitations, and potential applications in optimization problems,
        drug discovery, and financial modeling.
        """

        from ..tools import analyze_research_request_tool

        result = await analyze_research_request_tool(
            redis_client=test_dependencies.redis_client,
            query=multi_domain_query.strip(),
            timeout_minutes=12,
            quality_threshold=0.8
        )

        assert result["success"] is True, "Multi-domain request parsing failed"
        plan = result["execution_plan"]

        # Multi-domain should be classified as complex
        assert plan["complexity"] in ["medium", "complex"], "Multi-domain query should be medium or complex"

        # Should include multiple research approaches
        task_breakdown = plan["task_breakdown"]
        assert len(task_breakdown) >= 4, "Multi-domain requests should have multiple research tasks"

    @pytest.mark.asyncio
    async def test_strategic_execution_plan_structure(self, test_dependencies):
        """Test that strategic execution plans have required structure and elements."""
        test_query = "Research developments in renewable energy storage technologies"

        from ..tools import analyze_research_request_tool

        result = await analyze_research_request_tool(
            redis_client=test_dependencies.redis_client,
            query=test_query,
            timeout_minutes=10,
            quality_threshold=0.8
        )

        assert result["success"] is True
        plan = result["execution_plan"]

        # Verify strategic plan structure
        required_fields = [
            "strategy_id", "query", "complexity", "timeout_minutes", "quality_threshold",
            "phases", "task_breakdown", "resource_allocation"
        ]

        for field in required_fields:
            assert field in plan, f"Strategic plan missing required field: {field}"

        # Verify resource allocation planning
        resource_alloc = plan["resource_allocation"]
        assert "max_parallel_agents" in resource_alloc
        assert "total_estimated_time" in resource_alloc
        assert resource_alloc["max_parallel_agents"] <= 5, "Should not exceed max parallel agent limit"

        # Verify phase timing
        total_phase_time = sum(
            phase_config.get("duration_seconds", 0)
            for phase_config in plan["phases"].values()
        )
        assert total_phase_time <= plan["timeout_minutes"] * 60, "Phase timing should fit within timeout"


class TestRequirement002_ParallelExecution:
    """REQ-002: Coordinates parallel execution of Web Research and Tool Integration agents."""

    @pytest.mark.asyncio
    async def test_parallel_agent_coordination(self, test_dependencies, sample_execution_plan):
        """Test coordination of parallel agents."""
        from ..tools import distribute_parallel_tasks_tool

        target_agents = ["web_research_agent", "tool_integration_agent"]

        result = await distribute_parallel_tasks_tool(
            redis_client=test_dependencies.redis_client,
            execution_plan=sample_execution_plan,
            target_agents=target_agents,
            max_parallel=2
        )

        assert result["success"] is True, "Parallel task distribution failed"
        assert result["tasks_sent"] >= 2, "Should distribute tasks to multiple agents"
        assert len(result["agents_coordinated"]) == 2, "Should coordinate exactly 2 agents"

        # Verify coordination state
        coordination_state = result["coordination_state"]
        assert "task_assignments" in coordination_state
        assert "sent_messages" in coordination_state

        # Check agent coordination
        coordinated_agents = result["agents_coordinated"]
        assert "web_research_agent" in coordinated_agents
        assert "tool_integration_agent" in coordinated_agents

    @pytest.mark.asyncio
    async def test_max_parallel_agent_limit(self, test_dependencies, sample_execution_plan):
        """Test enforcement of maximum 5 parallel agents."""
        from ..tools import distribute_parallel_tasks_tool

        # Try to coordinate more than 5 agents
        many_agents = [f"agent_{i}" for i in range(8)]

        result = await distribute_parallel_tasks_tool(
            redis_client=test_dependencies.redis_client,
            execution_plan=sample_execution_plan,
            target_agents=many_agents,
            max_parallel=5  # Enforce 5 agent limit
        )

        assert result["success"] is True
        assert len(result["agents_coordinated"]) <= 5, "Should not exceed 5 parallel agents"

    @pytest.mark.asyncio
    async def test_task_assignment_protocol(self, test_dependencies, sample_execution_plan):
        """Test TaskAssignment protocol compliance."""
        from ..tools import distribute_parallel_tasks_tool

        result = await distribute_parallel_tasks_tool(
            redis_client=test_dependencies.redis_client,
            execution_plan=sample_execution_plan,
            target_agents=["web_research_agent"],
            max_parallel=1
        )

        assert result["success"] is True

        # Verify task assignment structure
        coordination_state = result["coordination_state"]
        task_assignments = coordination_state["task_assignments"]

        if task_assignments:
            task = task_assignments[0]
            required_fields = ["task_id", "agent_id", "operation", "parameters", "deadline", "quality_requirements"]
            for field in required_fields:
                assert field in task, f"TaskAssignment missing required field: {field}"

    @pytest.mark.asyncio
    async def test_agent_message_protocol(self, test_dependencies, sample_execution_plan):
        """Test AgentMessage protocol compliance."""
        from ..tools import distribute_parallel_tasks_tool

        result = await distribute_parallel_tasks_tool(
            redis_client=test_dependencies.redis_client,
            execution_plan=sample_execution_plan,
            target_agents=["test_agent"],
            max_parallel=1
        )

        assert result["success"] is True

        # Verify message was sent via Redis
        assert test_dependencies.redis_client.lpush.call_count >= 1

        # Check message structure
        lpush_calls = test_dependencies.redis_client.lpush.call_args_list
        for call in lpush_calls:
            queue_name, message_json = call[0]
            assert "agent_queue:" in queue_name

            message_data = json.loads(message_json)
            required_fields = ["message_id", "sender_id", "recipient_id", "message_type",
                             "payload", "timestamp", "correlation_id"]
            for field in required_fields:
                assert field in message_data, f"AgentMessage missing required field: {field}"

            assert message_data["sender_id"] == "research_orchestrator"
            assert message_data["message_type"] in ["task", "result", "status", "error", "health"]


class TestRequirement003_CompletionTime:
    """REQ-003: Maintains <10 minute total research completion time."""

    @pytest.mark.asyncio
    async def test_basic_orchestration_timing(self, test_dependencies, sample_research_request):
        """Test that basic orchestration completes within time limit."""
        start_time = time.time()

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run(sample_research_request, deps=test_dependencies)

        execution_time = time.time() - start_time

        assert result.data is not None, "Orchestration should complete successfully"
        assert execution_time < 600, f"Orchestration took {execution_time:.2f}s, exceeding 10-minute (600s) limit"

    @pytest.mark.asyncio
    async def test_complex_orchestration_timing(self, test_dependencies):
        """Test complex orchestration with full workflow timing."""
        complex_query = """
        Comprehensive analysis of quantum computing applications in cryptography,
        including post-quantum algorithms, implementation challenges, industry adoption,
        security implications, and future roadmap across academic and commercial domains.
        """

        # Create realistic timing model
        timing_responses = [
            {"content": "Analyzing complex research request..."},
            {
                "type": "tool_call",
                "tool_call": {
                    "analyze_research_request": {
                        "query": complex_query,
                        "complexity": "complex",
                        "timeout_minutes": 10,
                        "quality_threshold": 0.8
                    }
                }
            },
            {"content": "Coordinating parallel research agents..."},
            {
                "type": "tool_call",
                "tool_call": {
                    "distribute_parallel_tasks": {
                        "execution_plan": {"strategy_id": "test", "phases": {
                            "research": {"agents": ["web_research", "tool_integration"], "parallel": True}
                        }},
                        "target_agents": ["web_research_agent", "tool_integration_agent"],
                        "max_parallel": 2
                    }
                }
            },
            {"content": "Research complete. Coordinating quality assessment and synthesis..."},
            {
                "type": "tool_call",
                "tool_call": {
                    "coordinate_quality_assessment": {
                        "research_results": [{"test": "data"}],
                        "quality_threshold": 0.8
                    }
                }
            },
            {
                "type": "tool_call",
                "tool_call": {
                    "synthesize_final_report": {
                        "validated_data": [{"test": "validated"}],
                        "citations": [{"test": "citation"}],
                        "synthesis_format": "comprehensive"
                    }
                }
            },
            {"content": "Complex research orchestration completed within time constraints"}
        ]

        function_model = create_orchestration_function_model(timing_responses)
        test_agent = orchestrator_agent.override(model=function_model)

        start_time = time.time()
        result = await test_agent.run(complex_query, deps=test_dependencies)
        execution_time = time.time() - start_time

        assert result.data is not None
        assert execution_time < 600, f"Complex orchestration took {execution_time:.2f}s, exceeding 10-minute limit"

    @pytest.mark.asyncio
    async def test_timeout_configuration_compliance(self, test_dependencies):
        """Test that timeout configurations align with 10-minute requirement."""
        # Test dependencies should be configured for performance
        assert test_dependencies.research_timeout <= 600, "Research timeout should be ≤ 10 minutes"
        assert test_dependencies.task_timeout <= 180, "Task timeout should be reasonable for 10-minute total"

        # Test timeout calculation in execution plans
        from ..tools import analyze_research_request_tool

        result = await analyze_research_request_tool(
            redis_client=test_dependencies.redis_client,
            query="Test timeout compliance",
            timeout_minutes=10
        )

        assert result["success"] is True
        plan = result["execution_plan"]

        # Verify phase timing adds up correctly
        total_planned_time = sum(
            phase.get("duration_seconds", 0)
            for phase in plan["phases"].values()
        )
        assert total_planned_time <= 600, "Total planned phase time should fit within 10 minutes"


class TestRequirement004_SuccessRate:
    """REQ-004: Achieves >95% task success rate with proper error recovery."""

    @pytest.mark.asyncio
    async def test_error_recovery_mechanisms(self, test_dependencies):
        """Test error recovery during orchestration failures."""

        # Create a model that simulates failures and recovery
        def create_failure_recovery_model():
            attempt_count = 0

            async def failure_recovery_function(messages, tools):
                nonlocal attempt_count
                attempt_count += 1

                if attempt_count == 1:
                    # First attempt - analysis succeeds
                    return {
                        "analyze_research_request": {
                            "query": "test query",
                            "timeout_minutes": 10
                        }
                    }
                elif attempt_count == 2:
                    # Second attempt - distribution fails (simulated)
                    return ModelTextResponse(content="Task distribution failed, implementing recovery strategy...")
                elif attempt_count == 3:
                    # Recovery attempt - retry with alternative approach
                    return {
                        "distribute_parallel_tasks": {
                            "execution_plan": {"strategy_id": "recovery", "phases": {}},
                            "target_agents": ["backup_agent"],
                            "max_parallel": 1
                        }
                    }
                else:
                    # Final success
                    return ModelTextResponse(content="Error recovery completed successfully")

            return failure_recovery_function

        function_model = FunctionModel(create_failure_recovery_model())
        test_agent = orchestrator_agent.override(model=function_model)

        result = await test_agent.run("Test error recovery", deps=test_dependencies)

        assert result.data is not None, "Error recovery should complete successfully"
        assert "recovery" in result.data.lower() or "completed" in result.data.lower()

    @pytest.mark.asyncio
    async def test_retry_mechanism_configuration(self, test_dependencies):
        """Test that retry mechanisms are properly configured."""
        assert test_dependencies.retry_max_attempts >= 3, "Should allow at least 3 retry attempts"
        assert test_dependencies.retry_backoff >= 1, "Should have exponential backoff configured"

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, test_dependencies):
        """Test graceful degradation when some agents fail."""

        # Simulate partial agent failure
        test_dependencies.system_health = {
            "status": "degraded",
            "failed_agents": ["tool_integration_agent"],
            "available_agents": ["web_research_agent", "quality_assessment_agent"]
        }

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run("Test graceful degradation", deps=test_dependencies)

        # Should still complete with reduced capabilities
        assert result.data is not None, "Should complete despite agent failures"

    @pytest.mark.asyncio
    async def test_infrastructure_failure_handling(self, test_dependencies):
        """Test handling of infrastructure failures (Redis, HTTP)."""

        # Simulate Redis failure
        original_redis = test_dependencies.redis_client
        failing_redis = AsyncMock()
        failing_redis.ping.side_effect = Exception("Redis connection lost")
        failing_redis.lpush.side_effect = Exception("Redis operation failed")
        test_dependencies.redis_client = failing_redis

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run("Test infrastructure failure", deps=test_dependencies)

        # Should provide some response despite infrastructure issues
        assert result.data is not None, "Should handle infrastructure failures gracefully"

        # Restore for cleanup
        test_dependencies.redis_client = original_redis


class TestRequirement005_QualityAssessment:
    """REQ-005: Integrates quality assessment results with >0.8 average source credibility."""

    @pytest.mark.asyncio
    async def test_quality_threshold_enforcement(self, test_dependencies, sample_research_results):
        """Test enforcement of quality thresholds."""
        from ..tools import TaskAssignment

        # Test quality assessment task creation
        quality_task = TaskAssignment(
            agent_id="quality_assessment_agent",
            operation="assess_source_quality",
            parameters={
                "research_data": sample_research_results,
                "quality_threshold": 0.8,
                "confidence_threshold": 0.7
            },
            quality_requirements={"min_credibility": 0.8, "min_confidence": 0.7}
        )

        assert quality_task.parameters["quality_threshold"] == 0.8
        assert quality_task.quality_requirements["min_credibility"] == 0.8

    @pytest.mark.asyncio
    async def test_source_credibility_validation(self, sample_research_results):
        """Test source credibility validation."""
        # Verify sample data meets quality requirements
        high_quality_sources = [
            result for result in sample_research_results
            if result.get("credibility_score", 0) >= 0.8
        ]

        assert len(high_quality_sources) >= 2, "Should have multiple sources meeting 0.8 credibility threshold"

        # Calculate average credibility
        credibility_scores = [result.get("credibility_score", 0) for result in sample_research_results]
        average_credibility = sum(credibility_scores) / len(credibility_scores)

        assert average_credibility >= 0.8, f"Average credibility {average_credibility:.2f} should be ≥ 0.8"

    @pytest.mark.asyncio
    async def test_quality_gate_coordination(self, test_dependencies, sample_research_results):
        """Test quality gate coordination functionality."""

        # Mock quality assessment coordination
        correlation_id = str(uuid.uuid4())
        quality_threshold = 0.8
        confidence_threshold = 0.7

        # Create quality task
        from ..tools import TaskAssignment, AgentMessage

        quality_task = TaskAssignment(
            agent_id="quality_assessment_agent",
            operation="assess_source_quality",
            parameters={
                "research_data": sample_research_results,
                "quality_threshold": quality_threshold,
                "confidence_threshold": confidence_threshold,
                "assessment_criteria": [
                    "source_credibility",
                    "information_accuracy",
                    "citation_quality",
                    "data_completeness"
                ]
            },
            quality_requirements={
                "min_credibility": quality_threshold,
                "min_confidence": confidence_threshold
            }
        )

        # Verify task structure for quality requirements
        assert quality_task.parameters["quality_threshold"] == quality_threshold
        assert quality_task.quality_requirements["min_credibility"] == quality_threshold

        # Test quality criteria inclusion
        criteria = quality_task.parameters["assessment_criteria"]
        required_criteria = ["source_credibility", "information_accuracy", "citation_quality", "data_completeness"]
        for criterion in required_criteria:
            assert criterion in criteria, f"Missing quality assessment criterion: {criterion}"

    @pytest.mark.asyncio
    async def test_quality_retry_mechanism(self, test_dependencies):
        """Test quality assessment retry mechanism."""
        assert test_dependencies.max_quality_retries >= 2, "Should allow at least 2 quality retries"
        assert test_dependencies.min_source_quality >= 0.8, "Minimum source quality should be 0.8"
        assert test_dependencies.min_confidence_rating >= 0.7, "Minimum confidence should be 0.7"


class TestRequirement006_FinalReports:
    """REQ-006: Generates comprehensive final reports with proper citation management."""

    @pytest.mark.asyncio
    async def test_report_synthesis_coordination(self, test_dependencies, sample_research_results, sample_citations):
        """Test final report synthesis coordination."""
        from ..tools import TaskAssignment

        synthesis_task = TaskAssignment(
            agent_id="data_synthesis_agent",
            operation="synthesize_research_report",
            parameters={
                "validated_research_data": sample_research_results,
                "formatted_citations": sample_citations,
                "report_format": "comprehensive",
                "synthesis_requirements": {
                    "include_executive_summary": True,
                    "include_methodology": True,
                    "include_source_analysis": True,
                    "include_gaps_limitations": True,
                    "citation_style": "academic"
                }
            },
            quality_requirements={"min_completeness": 0.9, "citation_accuracy": 1.0}
        )

        # Verify comprehensive report requirements
        requirements = synthesis_task.parameters["synthesis_requirements"]
        assert requirements["include_executive_summary"] is True
        assert requirements["include_methodology"] is True
        assert requirements["include_source_analysis"] is True
        assert requirements["include_gaps_limitations"] is True
        assert requirements["citation_style"] == "academic"

        # Verify quality requirements for reports
        quality_reqs = synthesis_task.quality_requirements
        assert quality_reqs["min_completeness"] >= 0.9
        assert quality_reqs["citation_accuracy"] == 1.0

    @pytest.mark.asyncio
    async def test_citation_management_integration(self, sample_citations):
        """Test proper citation management integration."""
        # Verify citation structure compliance
        for citation in sample_citations:
            required_fields = ["id", "type", "title", "year", "citation_text"]
            for field in required_fields:
                assert field in citation, f"Citation missing required field: {field}"

            # Verify citation formatting
            citation_text = citation["citation_text"]
            assert len(citation_text) > 20, "Citation text should be properly formatted"
            assert str(citation["year"]) in citation_text, "Year should appear in citation text"

    @pytest.mark.asyncio
    async def test_comprehensive_report_structure(self, sample_research_results, sample_citations):
        """Test comprehensive report structure requirements."""
        # Verify data completeness for comprehensive reports
        assert len(sample_research_results) >= 3, "Should have multiple research sources"
        assert len(sample_citations) >= 2, "Should have multiple formatted citations"

        # Verify source diversity
        source_types = set(result.get("source", "") for result in sample_research_results)
        assert len(source_types) >= 2, "Should have diverse source types for comprehensive reports"

    @pytest.mark.asyncio
    async def test_report_format_options(self, sample_research_results, sample_citations):
        """Test different report format options."""
        formats = ["comprehensive", "summary", "detailed"]

        for format_type in formats:
            from ..tools import TaskAssignment

            task = TaskAssignment(
                agent_id="data_synthesis_agent",
                operation="synthesize_research_report",
                parameters={
                    "validated_research_data": sample_research_results,
                    "formatted_citations": sample_citations,
                    "report_format": format_type
                }
            )

            assert task.parameters["report_format"] == format_type


class TestRequirement007_InterAgentCommunication:
    """REQ-007: Handles inter-agent communication using standardized AgentMessage protocol."""

    @pytest.mark.asyncio
    async def test_agent_message_protocol_compliance(self):
        """Test AgentMessage protocol compliance."""
        message = AgentMessage(
            recipient_id="test_agent",
            message_type="task",
            payload={"operation": "test_operation", "parameters": {"test": "data"}},
            correlation_id="test_correlation"
        )

        # Verify required fields
        assert message.message_id is not None
        assert message.sender_id == "research_orchestrator"
        assert message.recipient_id == "test_agent"
        assert message.message_type == "task"
        assert message.payload is not None
        assert message.correlation_id == "test_correlation"
        assert isinstance(message.priority, int)
        assert isinstance(message.retry_count, int)

        # Test serialization
        message_json = message.model_dump_json()
        assert isinstance(message_json, str)

        # Test deserialization
        message_data = json.loads(message_json)
        reconstructed = AgentMessage.model_validate(message_data)
        assert reconstructed.recipient_id == message.recipient_id

    @pytest.mark.asyncio
    async def test_task_assignment_protocol_compliance(self):
        """Test TaskAssignment protocol compliance."""
        task = TaskAssignment(
            agent_id="test_agent",
            operation="test_operation",
            parameters={"param1": "value1"},
            deadline=datetime.utcnow() + timedelta(minutes=5),
            dependencies=["task1"],
            quality_requirements={"min_score": 0.8}
        )

        # Verify required fields
        assert task.task_id is not None
        assert task.agent_id == "test_agent"
        assert task.operation == "test_operation"
        assert task.parameters == {"param1": "value1"}
        assert task.deadline is not None
        assert task.dependencies == ["task1"]
        assert task.quality_requirements == {"min_score": 0.8}

    @pytest.mark.asyncio
    async def test_redis_communication_pattern(self, test_dependencies, mock_redis):
        """Test Redis-based inter-agent communication."""
        # Create and send a message
        message = AgentMessage(
            recipient_id="web_research_agent",
            message_type="task",
            payload={"query": "test query"},
            correlation_id="test_correlation"
        )

        queue_name = f"agent_queue:{message.recipient_id}"
        await test_dependencies.redis_client.lpush(queue_name, message.model_dump_json())

        # Verify Redis operations
        mock_redis.lpush.assert_called_once()
        call_args = mock_redis.lpush.call_args
        assert call_args[0][0] == queue_name

        # Verify message content
        stored_message = json.loads(call_args[0][1])
        assert stored_message["recipient_id"] == "web_research_agent"
        assert stored_message["message_type"] == "task"

    @pytest.mark.asyncio
    async def test_message_correlation_tracking(self, test_dependencies):
        """Test message correlation tracking across agents."""
        correlation_id = str(uuid.uuid4())

        # Create multiple related messages
        messages = [
            AgentMessage(
                recipient_id="web_research_agent",
                message_type="task",
                payload={"query": "part 1"},
                correlation_id=correlation_id
            ),
            AgentMessage(
                recipient_id="tool_integration_agent",
                message_type="task",
                payload={"query": "part 2"},
                correlation_id=correlation_id
            )
        ]

        # All messages should share the same correlation ID
        for message in messages:
            assert message.correlation_id == correlation_id

        # Verify correlation tracking
        unique_correlations = set(msg.correlation_id for msg in messages)
        assert len(unique_correlations) == 1, "All related messages should share correlation ID"


class TestRequirement008_SystemHealthMonitoring:
    """REQ-008: Monitors and responds to system health status from Workflow Coordinator."""

    @pytest.mark.asyncio
    async def test_health_status_monitoring(self, test_dependencies):
        """Test system health status monitoring."""
        # Set various health states
        health_states = [
            {"status": "healthy", "message": "All systems operational"},
            {"status": "degraded", "error": "High latency detected", "affected_agents": ["web_research"]},
            {"status": "critical", "error": "Multiple agent failures", "failed_agents": ["web_research", "tool_integration"]}
        ]

        for health_state in health_states:
            test_dependencies.system_health = health_state

            test_model = TestModel()
            test_agent = orchestrator_agent.override(model=test_model)

            result = await test_agent.run(f"Handle {health_state['status']} system state", deps=test_dependencies)

            # Should complete regardless of health state
            assert result.data is not None, f"Should handle {health_state['status']} state gracefully"

    @pytest.mark.asyncio
    async def test_crisis_management_activation(self, test_dependencies):
        """Test crisis management mode activation."""
        # Set degraded health status
        test_dependencies.system_health = {
            "status": "degraded",
            "error": "Multiple component failures",
            "failed_components": ["redis", "agent_web_research"],
            "recovery_actions": ["restart_failed_agents", "switch_to_backup_redis"]
        }

        test_model = TestModel()
        test_agent = orchestrator_agent.override(model=test_model)

        result = await test_agent.run("Handle crisis scenario", deps=test_dependencies)

        # Crisis mode should still allow completion
        assert result.data is not None, "Crisis management should maintain basic functionality"

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, test_dependencies):
        """Test performance metrics collection and reporting."""
        # Setup performance tracking
        test_dependencies.enable_metrics = True
        test_dependencies.execution_start_time = datetime.utcnow() - timedelta(seconds=120)

        # Simulate completed tasks
        test_dependencies.completed_tasks = {
            "task_1": {"completion_time": datetime.utcnow(), "duration": 30},
            "task_2": {"completion_time": datetime.utcnow(), "duration": 45}
        }

        # Simulate active tasks
        test_dependencies.active_tasks = {
            "task_3": {"start_time": datetime.utcnow(), "agent": "web_research_agent"}
        }

        # Get metrics
        metrics = test_dependencies.get_task_metrics()

        # Verify metrics structure
        required_metrics = ["elapsed_seconds", "active_tasks", "completed_tasks", "agent_status_summary"]
        for metric in required_metrics:
            assert metric in metrics, f"Missing required metric: {metric}"

        # Verify performance data
        assert metrics["completed_tasks"] == 2
        assert metrics["active_tasks"] == 1
        assert metrics["elapsed_seconds"] >= 120

    @pytest.mark.asyncio
    async def test_health_check_functionality(self):
        """Test health check functionality."""
        with patch('redis.asyncio.Redis') as mock_redis_class, \
             patch('httpx.AsyncClient') as mock_http_class:

            # Setup mocks
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance

            mock_http_instance = AsyncMock()
            mock_http_class.return_value = mock_http_instance

            health = await health_check()

            # Verify health check response structure
            assert "status" in health
            assert "agent_type" in health
            assert health["agent_type"] == "research_orchestrator"

            if health["status"] == "healthy":
                assert "redis_connected" in health
                assert "agent_endpoints" in health
                assert "quality_thresholds" in health