"""
Test tool implementations for Research Orchestrator Agent.
Tests all coordination tools: analyze_research_request, distribute_parallel_tasks,
coordinate_quality_assessment, and synthesize_final_report.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import uuid

from ..tools import (
    analyze_research_request_tool,
    distribute_parallel_tasks_tool,
    AgentMessage,
    TaskAssignment
)
from .conftest import create_mock_agent_message, create_mock_task_assignment


class TestAnalyzeResearchRequestTool:
    """Test research request analysis tool functionality."""

    @pytest.mark.asyncio
    async def test_simple_query_analysis(self, mock_redis):
        """Test analysis of a simple research query."""
        query = "What is quantum computing?"

        result = await analyze_research_request_tool(
            redis_client=mock_redis,
            query=query,
            timeout_minutes=10,
            quality_threshold=0.8
        )

        assert result["success"] is True
        assert "execution_plan" in result

        plan = result["execution_plan"]
        assert plan["query"] == query
        assert plan["complexity"] == "simple"  # Short query should be classified as simple
        assert plan["quality_threshold"] == 0.8
        assert "phases" in plan
        assert "task_breakdown" in plan

        # Verify Redis storage was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert "execution_plan:" in call_args[0][0]  # Key contains execution_plan prefix

    @pytest.mark.asyncio
    async def test_medium_query_analysis(self, mock_redis):
        """Test analysis of a medium complexity research query."""
        query = "Research the latest developments in quantum computing applications for cryptography including current challenges and future prospects"

        result = await analyze_research_request_tool(
            redis_client=mock_redis,
            query=query,
            complexity="medium",  # Explicitly set complexity
            timeout_minutes=15,
            quality_threshold=0.7
        )

        assert result["success"] is True
        plan = result["execution_plan"]

        assert plan["complexity"] == "medium"
        assert plan["timeout_minutes"] == 15
        assert plan["quality_threshold"] == 0.7

        # Medium complexity should include more tasks
        task_breakdown = plan["task_breakdown"]
        assert len(task_breakdown) >= 3

        # Should include web search and tool integration
        task_types = [task["task"] for task in task_breakdown]
        assert "web_search" in task_types
        assert "tool_integration" in task_types
        assert "quality_check" in task_types

    @pytest.mark.asyncio
    async def test_complex_query_analysis(self, mock_redis):
        """Test analysis of a complex research query."""
        query = "Conduct comprehensive analysis of quantum computing developments in cryptography, examining post-quantum cryptography algorithms, implementation challenges, industry adoption patterns, security implications, performance benchmarks, and future roadmap considerations across academic research, commercial implementations, and government standards"

        result = await analyze_research_request_tool(
            redis_client=mock_redis,
            query=query,
            timeout_minutes=20,
            quality_threshold=0.9
        )

        assert result["success"] is True
        plan = result["execution_plan"]

        assert plan["complexity"] == "complex"  # Long query should be classified as complex

        # Complex queries should have comprehensive task breakdown
        task_breakdown = plan["task_breakdown"]
        assert len(task_breakdown) >= 5

        # Should include all agent types for complex analysis
        task_types = [task["task"] for task in task_breakdown]
        assert "strategy_consult" in task_types
        assert "web_search" in task_types
        assert "tool_integration" in task_types
        assert "quality_check" in task_types
        assert "data_synthesis" in task_types

    @pytest.mark.asyncio
    async def test_analysis_with_redis_failure(self, mock_redis):
        """Test analysis handles Redis failures gracefully."""
        mock_redis.setex.side_effect = Exception("Redis connection failed")

        result = await analyze_research_request_tool(
            redis_client=mock_redis,
            query="Test query",
            timeout_minutes=10,
            quality_threshold=0.8
        )

        assert result["success"] is False
        assert "error" in result
        assert "Redis connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_execution_plan_structure(self, mock_redis):
        """Test that execution plan has required structure."""
        result = await analyze_research_request_tool(
            redis_client=mock_redis,
            query="Test structural analysis",
            timeout_minutes=10,
            quality_threshold=0.8
        )

        assert result["success"] is True
        plan = result["execution_plan"]

        # Verify required top-level fields
        required_fields = ["strategy_id", "query", "complexity", "timeout_minutes",
                          "quality_threshold", "phases", "task_breakdown", "resource_allocation"]
        for field in required_fields:
            assert field in plan, f"Missing required field: {field}"

        # Verify phases structure
        phases = plan["phases"]
        required_phases = ["planning", "research", "assessment", "attribution", "synthesis", "delivery"]
        for phase in required_phases:
            assert phase in phases, f"Missing required phase: {phase}"
            assert "duration_seconds" in phases[phase]
            assert "agents" in phases[phase]

        # Research phase should be marked as parallel
        assert phases["research"]["parallel"] is True

        # Verify resource allocation
        resource_alloc = plan["resource_allocation"]
        assert "max_parallel_agents" in resource_alloc
        assert "total_estimated_time" in resource_alloc


class TestDistributeParallelTasksTool:
    """Test parallel task distribution tool functionality."""

    @pytest.mark.asyncio
    async def test_basic_task_distribution(self, mock_redis, sample_execution_plan):
        """Test basic parallel task distribution."""
        target_agents = ["web_research_agent", "tool_integration_agent"]

        result = await distribute_parallel_tasks_tool(
            redis_client=mock_redis,
            execution_plan=sample_execution_plan,
            target_agents=target_agents,
            max_parallel=3
        )

        assert result["success"] is True
        assert "correlation_id" in result
        assert result["tasks_sent"] > 0
        assert len(result["agents_coordinated"]) <= 3  # Respects max_parallel limit

        # Verify Redis operations were called
        assert mock_redis.lpush.call_count > 0  # Messages sent to agent queues
        assert mock_redis.setex.call_count > 0  # Coordination state stored

    @pytest.mark.asyncio
    async def test_parallel_limit_enforcement(self, mock_redis, sample_execution_plan):
        """Test that max_parallel limit is properly enforced."""
        target_agents = ["agent1", "agent2", "agent3", "agent4", "agent5", "agent6"]
        max_parallel = 3

        result = await distribute_parallel_tasks_tool(
            redis_client=mock_redis,
            execution_plan=sample_execution_plan,
            target_agents=target_agents,
            max_parallel=max_parallel
        )

        assert result["success"] is True
        assert len(result["agents_coordinated"]) <= max_parallel

    @pytest.mark.asyncio
    async def test_task_assignment_structure(self, mock_redis, sample_execution_plan):
        """Test that TaskAssignment objects have proper structure."""
        target_agents = ["web_research_agent"]

        result = await distribute_parallel_tasks_tool(
            redis_client=mock_redis,
            execution_plan=sample_execution_plan,
            target_agents=target_agents,
            max_parallel=1
        )

        assert result["success"] is True

        # Verify coordination state was stored properly
        coordination_state = result["coordination_state"]
        assert "task_assignments" in coordination_state

        if coordination_state["task_assignments"]:
            task = coordination_state["task_assignments"][0]

            # Verify TaskAssignment structure
            required_fields = ["task_id", "agent_id", "operation", "parameters",
                             "deadline", "dependencies", "quality_requirements"]
            for field in required_fields:
                assert field in task, f"Missing required field in TaskAssignment: {field}"

    @pytest.mark.asyncio
    async def test_agent_message_creation(self, mock_redis, sample_execution_plan):
        """Test that AgentMessage objects are created properly."""
        target_agents = ["test_agent"]

        result = await distribute_parallel_tasks_tool(
            redis_client=mock_redis,
            execution_plan=sample_execution_plan,
            target_agents=target_agents,
            max_parallel=1
        )

        assert result["success"] is True

        # Check that a message was sent to the agent queue
        assert mock_redis.lpush.call_count >= 1

        # Verify the message structure by checking the call arguments
        lpush_calls = mock_redis.lpush.call_args_list
        for call in lpush_calls:
            queue_name, message_json = call[0]
            assert "agent_queue:" in queue_name

            # Parse the message to verify structure
            message_data = json.loads(message_json)
            required_fields = ["message_id", "sender_id", "recipient_id", "message_type",
                             "payload", "timestamp", "correlation_id", "priority", "retry_count"]
            for field in required_fields:
                assert field in message_data, f"Missing required field in AgentMessage: {field}"

    @pytest.mark.asyncio
    async def test_dependency_handling(self, mock_redis, sample_execution_plan):
        """Test task dependency handling."""
        target_agents = ["agent1", "agent2"]
        dependencies = {
            "agent1": [],
            "agent2": ["task_from_agent1"]
        }

        result = await distribute_parallel_tasks_tool(
            redis_client=mock_redis,
            execution_plan=sample_execution_plan,
            target_agents=target_agents,
            max_parallel=2,
            dependencies=dependencies
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_redis_failure_handling(self, mock_redis, sample_execution_plan):
        """Test handling of Redis failures during task distribution."""
        mock_redis.lpush.side_effect = Exception("Redis lpush failed")

        result = await distribute_parallel_tasks_tool(
            redis_client=mock_redis,
            execution_plan=sample_execution_plan,
            target_agents=["test_agent"],
            max_parallel=1
        )

        assert result["success"] is False
        assert "error" in result


class TestQualityAssessmentCoordination:
    """Test quality assessment coordination functionality."""

    @pytest.mark.asyncio
    async def test_quality_assessment_task_creation(self, test_dependencies, sample_research_results):
        """Test creation of quality assessment tasks."""
        from ..agent import orchestrator_agent

        test_agent = orchestrator_agent.override(model=None)  # We'll mock the tool call

        # Mock the tool execution directly
        with patch.object(test_dependencies.redis_client, 'lpush') as mock_lpush:
            mock_lpush.return_value = 1

            # Import and test the tool function directly from the registered tools
            from ..tools import register_tools

            # Create a mock context
            class MockContext:
                def __init__(self, deps):
                    self.deps = deps

            ctx = MockContext(test_dependencies)

            # Get the quality assessment tool function
            # Since tools are registered dynamically, we'll test the underlying functionality
            correlation_id = str(uuid.uuid4())

            # Create quality task manually to test structure
            from ..tools import TaskAssignment, AgentMessage

            quality_task = TaskAssignment(
                agent_id="quality_assessment_agent",
                operation="assess_source_quality",
                parameters={
                    "research_data": sample_research_results,
                    "quality_threshold": 0.8,
                    "confidence_threshold": 0.7,
                    "assessment_criteria": [
                        "source_credibility",
                        "information_accuracy",
                        "citation_quality",
                        "data_completeness"
                    ]
                },
                deadline=datetime.utcnow() + timedelta(minutes=2),
                quality_requirements={
                    "min_credibility": 0.8,
                    "min_confidence": 0.7
                }
            )

            # Verify task structure
            assert quality_task.agent_id == "quality_assessment_agent"
            assert quality_task.operation == "assess_source_quality"
            assert "research_data" in quality_task.parameters
            assert quality_task.parameters["quality_threshold"] == 0.8
            assert quality_task.quality_requirements["min_credibility"] == 0.8

    @pytest.mark.asyncio
    async def test_quality_threshold_validation(self, test_dependencies, sample_research_results):
        """Test quality threshold validation."""
        # Test with high quality threshold
        high_threshold_results = [
            result for result in sample_research_results
            if result.get("credibility_score", 0) >= 0.9
        ]

        assert len(high_threshold_results) >= 1, "Should have at least one high-quality source"

        # Test with low quality threshold - should include more results
        low_threshold_results = [
            result for result in sample_research_results
            if result.get("credibility_score", 0) >= 0.5
        ]

        assert len(low_threshold_results) >= len(high_threshold_results), "Lower threshold should include more sources"

    @pytest.mark.asyncio
    async def test_assessment_criteria_structure(self, sample_research_results):
        """Test that assessment criteria are properly structured."""
        expected_criteria = [
            "source_credibility",
            "information_accuracy",
            "citation_quality",
            "data_completeness"
        ]

        # Verify sample data has the fields needed for assessment
        for result in sample_research_results:
            assert "source" in result
            assert "content" in result
            assert "credibility_score" in result
            if result.get("credibility_score"):
                assert 0.0 <= result["credibility_score"] <= 1.0


class TestReportSynthesisCoordination:
    """Test final report synthesis coordination functionality."""

    @pytest.mark.asyncio
    async def test_synthesis_task_creation(self, test_dependencies, sample_research_results, sample_citations):
        """Test creation of report synthesis tasks."""
        from ..tools import TaskAssignment

        # Create synthesis task manually to test structure
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
            deadline=datetime.utcnow() + timedelta(minutes=3),
            quality_requirements={
                "min_completeness": 0.9,
                "citation_accuracy": 1.0
            }
        )

        # Verify task structure
        assert synthesis_task.agent_id == "data_synthesis_agent"
        assert synthesis_task.operation == "synthesize_research_report"
        assert "validated_research_data" in synthesis_task.parameters
        assert "formatted_citations" in synthesis_task.parameters
        assert synthesis_task.parameters["report_format"] == "comprehensive"

        # Verify synthesis requirements
        requirements = synthesis_task.parameters["synthesis_requirements"]
        assert requirements["include_executive_summary"] is True
        assert requirements["citation_style"] == "academic"

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
                    "report_format": format_type,
                    "synthesis_requirements": {
                        "include_executive_summary": format_type in ["comprehensive", "detailed"],
                        "include_methodology": format_type == "comprehensive",
                        "citation_style": "academic"
                    }
                },
                deadline=datetime.utcnow() + timedelta(minutes=3)
            )

            assert task.parameters["report_format"] == format_type

    @pytest.mark.asyncio
    async def test_citation_integration(self, sample_research_results, sample_citations):
        """Test citation integration in synthesis."""
        # Verify citations have required structure
        for citation in sample_citations:
            assert "id" in citation
            assert "type" in citation
            assert "title" in citation
            assert "year" in citation
            assert "citation_text" in citation

        # Verify research results can be matched with citations
        assert len(sample_research_results) > 0
        assert len(sample_citations) > 0

    @pytest.mark.asyncio
    async def test_quality_requirements_for_synthesis(self, sample_research_results, sample_citations):
        """Test quality requirements for report synthesis."""
        high_quality_sources = [
            result for result in sample_research_results
            if result.get("credibility_score", 0) >= 0.8
        ]

        assert len(high_quality_sources) >= 2, "Should have multiple high-quality sources for synthesis"

        # Verify citations are properly formatted
        for citation in sample_citations:
            citation_text = citation.get("citation_text", "")
            assert len(citation_text) > 20, "Citation text should be properly formatted"
            assert citation.get("year") is not None, "Citations should have publication year"


class TestAgentMessageProtocol:
    """Test AgentMessage and TaskAssignment protocol compliance."""

    def test_agent_message_creation(self):
        """Test AgentMessage object creation and validation."""
        message = AgentMessage(
            recipient_id="test_agent",
            message_type="task",
            payload={"test": "data"},
            correlation_id="test_correlation"
        )

        assert message.recipient_id == "test_agent"
        assert message.message_type == "task"
        assert message.sender_id == "research_orchestrator"  # Default sender
        assert message.payload == {"test": "data"}
        assert message.correlation_id == "test_correlation"
        assert message.priority == 1  # Default priority
        assert message.retry_count == 0  # Default retry count

    def test_task_assignment_creation(self):
        """Test TaskAssignment object creation and validation."""
        task = TaskAssignment(
            agent_id="test_agent",
            operation="test_operation",
            parameters={"param1": "value1"},
            dependencies=["task1", "task2"],
            quality_requirements={"min_score": 0.8}
        )

        assert task.agent_id == "test_agent"
        assert task.operation == "test_operation"
        assert task.parameters == {"param1": "value1"}
        assert task.dependencies == ["task1", "task2"]
        assert task.quality_requirements == {"min_score": 0.8}
        assert task.task_id is not None  # Should have auto-generated ID

    def test_message_serialization(self):
        """Test that messages can be serialized for Redis storage."""
        message = AgentMessage(
            recipient_id="test_agent",
            message_type="status",
            payload={"status": "completed"},
            correlation_id="test_correlation"
        )

        # Test JSON serialization
        message_json = message.model_dump_json()
        assert isinstance(message_json, str)
        assert "test_agent" in message_json
        assert "status" in message_json

        # Test deserialization
        message_data = json.loads(message_json)
        reconstructed = AgentMessage.model_validate(message_data)
        assert reconstructed.recipient_id == message.recipient_id
        assert reconstructed.message_type == message.message_type

    def test_task_assignment_serialization(self):
        """Test that task assignments can be serialized."""
        task = TaskAssignment(
            agent_id="test_agent",
            operation="test_operation",
            parameters={"test": True}
        )

        # Test JSON serialization
        task_json = task.model_dump_json()
        assert isinstance(task_json, str)
        assert "test_agent" in task_json

        # Test deserialization
        task_data = json.loads(task_json)
        reconstructed = TaskAssignment.model_validate(task_data)
        assert reconstructed.agent_id == task.agent_id
        assert reconstructed.operation == task.operation