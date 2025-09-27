"""
Integration tests for Query Strategy Agent.
Tests the complete agent workflow and tool integration.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from typing import Dict, Any

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import agent, analyze_research_strategy, quick_complexity_check, create_strategy_agent_with_deps
from ..dependencies import AgentDependencies


class TestAgentBasicFunctionality:
    """Test core agent functionality with TestModel."""

    @pytest.mark.asyncio
    async def test_agent_basic_response(self, test_agent, test_dependencies):
        """Test agent provides appropriate response."""
        result = await test_agent.run(
            "Analyze the complexity of machine learning research",
            deps=test_dependencies
        )

        assert result.data is not None
        assert isinstance(result.data, str)
        assert len(result.all_messages()) > 0

    @pytest.mark.asyncio
    async def test_agent_with_structured_prompt(self, test_agent, test_dependencies):
        """Test agent with structured analysis prompt."""
        prompt = """Please analyze this research query and provide comprehensive strategic recommendations:

        Research Query: What are the environmental impacts of electric vehicle battery production?

        Constraints: time_limit: 60, source_limit: 10, quality_threshold: 0.8

        Please provide:
        1. Detailed complexity analysis with scoring (1-10 scale)
        2. Recommended research strategy with clear reasoning
        3. Comprehensive risk assessment with mitigation strategies
        4. Realistic timeline and resource estimates
        5. Quality checkpoints and fallback options"""

        result = await test_agent.run(prompt, deps=test_dependencies)

        assert result.data is not None
        assert isinstance(result.data, str)
        assert len(result.data) > 100  # Should be comprehensive response

    @pytest.mark.asyncio
    async def test_agent_tool_registration(self, test_agent):
        """Test that all expected tools are registered."""
        # Get agent's tools
        tools = {tool.name for tool in test_agent.tools}

        expected_tools = {"analyze_complexity", "recommend_strategy", "assess_risks"}
        assert expected_tools.issubset(tools)

    @pytest.mark.asyncio
    async def test_agent_dependency_injection(self):
        """Test agent dependency injection."""
        custom_deps = AgentDependencies(
            workflow_id="test_workflow",
            orchestrator_session_id="test_session",
            debug=True
        )

        test_model = TestModel()
        test_agent = agent.override(model=test_model)

        result = await test_agent.run(
            "Test dependency injection",
            deps=custom_deps
        )

        assert result.data is not None


class TestAgentToolCalling:
    """Test agent tool calling behavior with FunctionModel."""

    @pytest.mark.asyncio
    async def test_complexity_analysis_tool_call(self, complexity_function_model, test_dependencies):
        """Test agent calls complexity analysis tool."""
        test_agent = agent.override(model=complexity_function_model)

        result = await test_agent.run(
            "Analyze the complexity of this research query about machine learning",
            deps=test_dependencies
        )

        # Check that tools were called
        messages = result.all_messages()
        tool_calls = [msg for msg in messages if hasattr(msg, 'tool_name') and msg.tool_name == 'analyze_complexity']
        assert len(tool_calls) > 0

    @pytest.mark.asyncio
    async def test_full_strategy_workflow(self, strategy_function_model, test_dependencies):
        """Test complete strategy workflow with tool calls."""
        test_agent = agent.override(model=strategy_function_model)

        result = await test_agent.run(
            "Provide comprehensive strategy analysis for artificial intelligence ethics research",
            deps=test_dependencies
        )

        # Verify workflow completion
        messages = result.all_messages()

        # Should call all three main tools
        tool_names = [getattr(msg, 'tool_name', None) for msg in messages if hasattr(msg, 'tool_name')]
        expected_tools = ['analyze_complexity', 'recommend_strategy', 'assess_risks']

        for tool in expected_tools:
            assert tool in tool_names, f"Expected tool {tool} not called"

    @pytest.mark.asyncio
    async def test_agent_with_historical_data(self, test_dependencies_with_history, complexity_function_model):
        """Test agent behavior with historical context."""
        test_agent = agent.override(model=complexity_function_model)

        result = await test_agent.run(
            "Analyze research strategy for quantum computing applications",
            deps=test_dependencies_with_history
        )

        assert result.data is not None

        # Historical data should be accessible in context
        assert test_dependencies_with_history.historical_strategies is not None
        assert len(test_dependencies_with_history.historical_strategies) > 0

    @pytest.mark.asyncio
    async def test_agent_caching_behavior(self, test_dependencies, complexity_function_model):
        """Test complexity score caching behavior."""
        test_agent = agent.override(model=complexity_function_model)
        test_dependencies.debug = True

        query = "Machine learning algorithm optimization"

        # First call should compute and cache
        result1 = await test_agent.run(f"Analyze: {query}", deps=test_dependencies)

        # Second call should use cache
        result2 = await test_agent.run(f"Analyze: {query}", deps=test_dependencies)

        # Both should succeed
        assert result1.data is not None
        assert result2.data is not None

        # Cache should have the complexity score
        cached_score = test_dependencies.get_cached_complexity(query)
        assert cached_score is not None


class TestConvenienceFunctions:
    """Test convenience functions for agent usage."""

    @pytest.mark.asyncio
    async def test_analyze_research_strategy_function(self):
        """Test analyze_research_strategy convenience function."""
        result = await analyze_research_strategy(
            "What are the implications of quantum computing for cybersecurity?",
            constraints={"time_limit": 60, "source_limit": 8},
            workflow_context={"session_id": "test_session"}
        )

        assert isinstance(result, dict)
        assert "success" in result
        if result["success"]:
            assert "strategy_analysis" in result
            assert "agent_context" in result

    @pytest.mark.asyncio
    async def test_quick_complexity_check_function(self, sample_queries):
        """Test quick complexity check function."""
        # Test with valid queries
        simple_score = await quick_complexity_check(sample_queries["simple"])
        complex_score = await quick_complexity_check(sample_queries["complex"])

        assert isinstance(simple_score, float)
        assert isinstance(complex_score, float)
        assert 1.0 <= simple_score <= 10.0
        assert 1.0 <= complex_score <= 10.0
        assert complex_score > simple_score

    @pytest.mark.asyncio
    async def test_quick_complexity_check_error_handling(self):
        """Test error handling in quick complexity check."""
        # Empty query should return default
        score = await quick_complexity_check("")
        assert score == 5.0

        # None query should return default
        score = await quick_complexity_check(None)
        assert score == 5.0

    def test_create_strategy_agent_with_deps(self):
        """Test agent creation with custom dependencies."""
        custom_agent, deps = create_strategy_agent_with_deps(
            workflow_id="custom_workflow",
            debug=True
        )

        assert custom_agent is not None
        assert isinstance(deps, AgentDependencies)
        assert deps.workflow_id == "custom_workflow"
        assert deps.debug is True


class TestAgentErrorHandling:
    """Test agent error handling and resilience."""

    @pytest.mark.asyncio
    async def test_agent_with_invalid_dependencies(self, test_agent):
        """Test agent behavior with invalid dependencies."""
        # Create dependencies with None values
        invalid_deps = AgentDependencies()

        # Should still work with defaults
        result = await test_agent.run(
            "Test with minimal dependencies",
            deps=invalid_deps
        )

        assert result.data is not None

    @pytest.mark.asyncio
    async def test_agent_retry_mechanism(self):
        """Test agent retry mechanism on failures."""
        # Create agent with retry settings
        custom_deps = AgentDependencies(max_retries=2, timeout=10)
        test_model = TestModel()
        test_agent = agent.override(model=test_model)

        # This should succeed despite retry configuration
        result = await test_agent.run(
            "Test retry mechanism",
            deps=custom_deps
        )

        assert result.data is not None

    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self):
        """Test agent timeout configuration."""
        timeout_deps = AgentDependencies(timeout=1)  # Very short timeout
        test_model = TestModel()
        test_agent = agent.override(model=test_model)

        # Should still complete for simple TestModel
        result = await test_agent.run(
            "Quick test",
            deps=timeout_deps
        )

        assert result.data is not None

    @pytest.mark.asyncio
    async def test_analyze_research_strategy_error_handling(self):
        """Test error handling in analyze_research_strategy function."""
        # Test with minimal parameters
        result = await analyze_research_strategy("")

        assert isinstance(result, dict)
        assert "success" in result
        # Empty query might still work with TestModel, check result structure

    @pytest.mark.asyncio
    async def test_agent_with_malformed_constraints(self, test_agent, test_dependencies):
        """Test agent behavior with malformed constraint data."""
        prompt = """Analyze this query with malformed constraints:

        Research Query: Test query
        Constraints: invalid_format
        """

        # Should handle gracefully
        result = await test_agent.run(prompt, deps=test_dependencies)
        assert result.data is not None


class TestAgentWorkflowIntegration:
    """Test agent integration with Research Orchestrator workflow."""

    @pytest.mark.asyncio
    async def test_workflow_context_handling(self, test_agent):
        """Test handling of workflow context from Research Orchestrator."""
        workflow_context = {
            "workflow_id": "research_workflow_001",
            "session_id": "session_123",
            "previous_queries": ["initial research query"],
            "time_budget": 300,
            "quality_requirements": "high"
        }

        deps = AgentDependencies(
            workflow_id=workflow_context["workflow_id"],
            orchestrator_session_id=workflow_context["session_id"],
            research_context=workflow_context
        )

        result = await test_agent.run(
            "Analyze strategy for multi-agent workflow coordination",
            deps=deps
        )

        assert result.data is not None

    @pytest.mark.asyncio
    async def test_agent_response_format(self, test_agent, test_dependencies):
        """Test that agent responses are in expected format for orchestrator."""
        result = await test_agent.run(
            "Provide strategy recommendation for complex interdisciplinary research",
            deps=test_dependencies
        )

        assert result.data is not None
        assert isinstance(result.data, str)

        # Response should contain strategy guidance
        response_lower = result.data.lower()
        strategy_indicators = ['strategy', 'recommend', 'complexity', 'approach', 'analysis']
        assert any(indicator in response_lower for indicator in strategy_indicators)

    @pytest.mark.asyncio
    async def test_agent_session_continuity(self, test_dependencies_with_history, test_agent):
        """Test session continuity with historical data."""
        session_id = "continuous_session_001"
        test_dependencies_with_history.orchestrator_session_id = session_id

        # First query
        result1 = await test_agent.run(
            "Analyze strategy for machine learning research",
            deps=test_dependencies_with_history
        )

        # Update historical context
        test_dependencies_with_history.update_historical_context({
            "query": "machine learning research",
            "strategy": "moderate_multisource",
            "success": True,
            "duration": 45
        })

        # Second query in same session
        result2 = await test_agent.run(
            "Analyze strategy for deep learning applications",
            deps=test_dependencies_with_history
        )

        assert result1.data is not None
        assert result2.data is not None
        assert len(test_dependencies_with_history.historical_strategies) > 0


class TestAgentPerformanceCharacteristics:
    """Test agent performance and response characteristics."""

    @pytest.mark.asyncio
    async def test_agent_response_time_basic(self, test_agent, test_dependencies):
        """Test basic response time characteristics."""
        start_time = asyncio.get_event_loop().time()

        result = await test_agent.run(
            "Quick complexity analysis for simple query",
            deps=test_dependencies
        )

        end_time = asyncio.get_event_loop().time()
        response_time = end_time - start_time

        assert result.data is not None
        # TestModel should be very fast
        assert response_time < 2.0

    @pytest.mark.asyncio
    async def test_agent_consistency(self, test_agent, test_dependencies):
        """Test response consistency for similar queries."""
        base_query = "Analyze machine learning research complexity"

        # Run same query multiple times
        results = []
        for i in range(3):
            result = await test_agent.run(f"{base_query} - iteration {i}", deps=test_dependencies)
            results.append(result.data)

        # All should succeed
        assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_agent_requests(self, test_dependencies):
        """Test agent handling of concurrent requests."""
        test_model = TestModel()
        test_agent = agent.override(model=test_model)

        # Create multiple concurrent requests
        tasks = []
        for i in range(3):
            task = test_agent.run(
                f"Concurrent analysis request {i}",
                deps=test_dependencies
            )
            tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(result.data is not None for result in results)

    @pytest.mark.asyncio
    async def test_agent_memory_efficiency(self, test_dependencies_with_history, test_agent):
        """Test agent memory efficiency with historical data."""
        # Add many historical entries
        for i in range(150):  # More than the 100-entry limit
            test_dependencies_with_history.update_historical_context({
                "query": f"test query {i}",
                "strategy": "test_strategy",
                "success": True,
                "duration": 30
            })

        # Should auto-trim to prevent memory bloat
        assert len(test_dependencies_with_history.historical_strategies) <= 100

        # Agent should still work normally
        result = await test_agent.run(
            "Test with large historical context",
            deps=test_dependencies_with_history
        )

        assert result.data is not None


class TestAgentSpecialScenarios:
    """Test agent behavior in special scenarios."""

    @pytest.mark.asyncio
    async def test_agent_with_empty_research_context(self, test_agent):
        """Test agent with minimal research context."""
        minimal_deps = AgentDependencies(
            workflow_id=None,
            orchestrator_session_id=None,
            research_context={}
        )

        result = await test_agent.run(
            "Analyze research strategy with minimal context",
            deps=minimal_deps
        )

        assert result.data is not None

    @pytest.mark.asyncio
    async def test_agent_debug_mode(self, test_agent):
        """Test agent behavior in debug mode."""
        debug_deps = AgentDependencies(debug=True)

        result = await test_agent.run(
            "Debug mode test analysis",
            deps=debug_deps
        )

        assert result.data is not None

    @pytest.mark.asyncio
    async def test_agent_with_extreme_thresholds(self, test_agent):
        """Test agent with extreme configuration thresholds."""
        extreme_deps = AgentDependencies(
            complexity_threshold_low=1.0,
            complexity_threshold_high=9.0,
            confidence_threshold=0.9
        )

        result = await test_agent.run(
            "Test with extreme threshold configuration",
            deps=extreme_deps
        )

        assert result.data is not None

    @pytest.mark.asyncio
    async def test_agent_boundary_conditions(self, test_agent, test_dependencies, sample_queries):
        """Test agent with boundary condition inputs."""
        boundary_tests = [
            sample_queries.get("very_long", "long query"),  # Very long input
            "a",  # Very short input
            "?" * 100,  # Repetitive input
            "Test query with special characters: @#$%^&*()",  # Special characters
        ]

        for test_input in boundary_tests:
            result = await test_agent.run(test_input, deps=test_dependencies)
            # Should handle gracefully, either succeeding or failing gracefully
            assert result is not None