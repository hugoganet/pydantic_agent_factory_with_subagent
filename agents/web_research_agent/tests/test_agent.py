"""
Test core agent functionality using TestModel and FunctionModel.
Validates the main agent behavior and tool integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import agent, run_web_search, create_agent_with_deps
from ..dependencies import WebResearchDependencies


class TestWebResearchAgent:
    """Test suite for the main Web Research Agent functionality."""

    @pytest.mark.asyncio
    async def test_agent_basic_response(self, test_agent, mock_dependencies):
        """Test agent provides appropriate response with TestModel."""
        result = await test_agent.run(
            "Search for information about machine learning",
            deps=mock_dependencies
        )

        assert result.data is not None
        assert isinstance(result.data, str)
        assert len(result.all_messages()) > 0

    @pytest.mark.asyncio
    async def test_agent_tool_calling_with_function_model(self, mock_dependencies):
        """Test agent calls appropriate tools using FunctionModel."""
        call_sequence = []

        async def controlled_function(messages, tools):
            call_sequence.append(len(messages))

            if len(call_sequence) == 1:
                # First call - agent analyzes request
                return ModelTextResponse(
                    content="I'll perform a comprehensive web search for your query."
                )
            elif len(call_sequence) == 2:
                # Second call - agent uses search tool
                return {
                    "search_and_extract": {
                        "query": "machine learning algorithms",
                        "search_engines": ["brave"],
                        "max_results": 10,
                        "quality_threshold": 0.7
                    }
                }
            else:
                # Final response
                return ModelTextResponse(
                    content="Web research completed. Found relevant sources on machine learning."
                )

        function_model = FunctionModel(controlled_function)
        test_agent = agent.override(model=function_model)

        result = await test_agent.run(
            "Search for machine learning algorithms",
            deps=mock_dependencies
        )

        # Verify the tool was called
        assert len(call_sequence) >= 2
        assert "machine learning" in result.data.lower()

    @pytest.mark.asyncio
    async def test_agent_multi_tool_workflow(self, mock_dependencies):
        """Test complete workflow using multiple tools."""
        workflow_steps = []

        async def workflow_function(messages, tools):
            step_count = len(workflow_steps)
            workflow_steps.append(step_count + 1)

            if step_count == 0:
                return ModelTextResponse("Starting web research...")
            elif step_count == 1:
                return {"multi_engine_web_search": {"query": "test", "engines": ["brave"]}}
            elif step_count == 2:
                return {"extract_content_from_urls": {"urls": ["https://example.com"]}}
            elif step_count == 3:
                return {"assess_web_content_quality": {"extracted_content": [], "search_query": "test"}}
            else:
                return ModelTextResponse("Research complete with quality assessment.")

        function_model = FunctionModel(workflow_function)
        test_agent = agent.override(model=function_model)

        result = await test_agent.run(
            "Perform comprehensive research on artificial intelligence",
            deps=mock_dependencies
        )

        # Verify workflow steps were executed
        assert len(workflow_steps) >= 4
        assert "research" in result.data.lower()

    @pytest.mark.asyncio
    async def test_agent_error_handling(self, mock_dependencies):
        """Test agent handles errors gracefully."""
        async def error_function(messages, tools):
            # Simulate a tool that fails
            return {"search_and_extract": {"invalid": "parameters"}}

        function_model = FunctionModel(error_function)
        test_agent = agent.override(model=function_model)

        # This should not raise an exception
        result = await test_agent.run(
            "Search for something that will fail",
            deps=mock_dependencies
        )

        # Agent should handle the error and provide some response
        assert result.data is not None
        assert isinstance(result.data, str)

    @pytest.mark.asyncio
    async def test_run_web_search_convenience_function(self):
        """Test the convenience function for running web searches."""
        with patch('agents.web_research_agent.agent.agent.run') as mock_run:
            mock_run.return_value = Mock(data="Search completed successfully")

            with patch('agents.web_research_agent.dependencies.WebResearchDependencies.from_settings') as mock_deps:
                mock_dep_instance = AsyncMock()
                mock_dep_instance.cleanup = AsyncMock()
                mock_deps.return_value = mock_dep_instance

                result = await run_web_search(
                    "test query",
                    search_engines=["brave"],
                    max_results=5
                )

                assert result == "Search completed successfully"
                mock_deps.assert_called_once()
                mock_dep_instance.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_agent_with_deps(self):
        """Test agent creation with custom dependencies."""
        with patch('agents.web_research_agent.agent.WebResearchDependencies.from_settings') as mock_deps:
            mock_dep_instance = Mock()
            mock_deps.return_value = mock_dep_instance

            test_agent, deps = create_agent_with_deps(
                brave_api_key="custom-key",
                max_results=15
            )

            assert test_agent is not None
            assert deps == mock_dep_instance
            mock_deps.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_with_different_search_engines(self, mock_dependencies):
        """Test agent works with different search engine configurations."""
        async def engine_function(messages, tools):
            if len(messages) <= 2:
                return {"multi_engine_web_search": {
                    "query": "test",
                    "engines": ["google", "bing"],
                    "max_results_per_engine": 5
                }}
            else:
                return ModelTextResponse("Search completed with multiple engines.")

        function_model = FunctionModel(engine_function)
        test_agent = agent.override(model=function_model)

        # Configure dependencies for multiple engines
        mock_dependencies.available_search_engines = ["google", "bing"]

        result = await test_agent.run(
            "Search using Google and Bing",
            deps=mock_dependencies
        )

        assert "search" in result.data.lower()

    @pytest.mark.asyncio
    async def test_agent_quality_threshold_handling(self, mock_dependencies):
        """Test agent handles different quality thresholds."""
        async def quality_function(messages, tools):
            if "high quality" in str(messages):
                return {"search_and_extract": {
                    "query": "test",
                    "quality_threshold": 0.9
                }}
            else:
                return ModelTextResponse("Quality assessment completed.")

        function_model = FunctionModel(quality_function)
        test_agent = agent.override(model=function_model)

        result = await test_agent.run(
            "Find high quality sources about machine learning",
            deps=mock_dependencies
        )

        assert result.data is not None

    @pytest.mark.asyncio
    async def test_agent_parallel_processing_simulation(self, mock_dependencies):
        """Test agent can handle parallel processing requests."""
        async def parallel_function(messages, tools):
            return {"extract_content_from_urls": {
                "urls": [f"https://example{i}.com" for i in range(10)],
                "extract_metadata": True
            }}

        function_model = FunctionModel(parallel_function)
        test_agent = agent.override(model=function_model)

        result = await test_agent.run(
            "Extract content from multiple sources in parallel",
            deps=mock_dependencies
        )

        assert result.data is not None

    @pytest.mark.asyncio
    async def test_agent_workflow_context_integration(self, mock_dependencies):
        """Test agent integrates with workflow context."""
        # Set workflow context
        mock_dependencies.workflow_context = {
            "workflow_id": "test-workflow-123",
            "stage": "information_gathering",
            "priority": "high"
        }

        async def context_aware_function(messages, tools):
            return ModelTextResponse("Research completed within workflow context.")

        function_model = FunctionModel(context_aware_function)
        test_agent = agent.override(model=function_model)

        result = await test_agent.run(
            "Perform research as part of workflow",
            deps=mock_dependencies
        )

        assert "workflow" in result.data.lower() or "research" in result.data.lower()

    @pytest.mark.asyncio
    async def test_agent_session_tracking(self, mock_dependencies):
        """Test agent tracks session information."""
        mock_dependencies.session_id = "unique-session-456"

        test_agent_instance = agent.override(model=TestModel())

        result = await test_agent_instance.run(
            "Track this research session",
            deps=mock_dependencies
        )

        # Verify session is accessible in dependencies
        assert mock_dependencies.session_id == "unique-session-456"
        assert result.data is not None


class TestAgentToolIntegration:
    """Test integration between agent and tools."""

    @pytest.mark.asyncio
    async def test_search_and_extract_tool_integration(self, mock_dependencies):
        """Test the main search_and_extract tool integration."""
        with patch('agents.web_research_agent.tools.multi_engine_search') as mock_search, \
             patch('agents.web_research_agent.tools.extract_web_content') as mock_extract, \
             patch('agents.web_research_agent.tools.assess_content_quality') as mock_assess:

            # Mock successful tool responses
            mock_search.return_value = {
                "success": True,
                "search_results": {"brave": [{"url": "https://example.com", "title": "Test"}]},
                "metadata": {"engines_successful": ["brave"], "execution_time": 1.5}
            }

            mock_extract.return_value = [{
                "success": True,
                "url": "https://example.com",
                "content": "Test content",
                "metadata": {"title": "Test", "word_count": 50}
            }]

            mock_assess.return_value = {
                "success": True,
                "filtered_content": [{"quality_score": 0.8}],
                "quality_summary": {
                    "high_quality_sources": 1,
                    "average_quality_score": 0.8,
                    "quality_distribution": {"excellent": 0, "good": 1, "fair": 0, "poor": 0}
                }
            }

            # Test direct tool call
            from ..agent import search_and_extract
            result = await search_and_extract(
                Mock(deps=mock_dependencies),
                query="test query",
                search_engines=["brave"],
                max_results=10,
                quality_threshold=0.7
            )

            # Verify tools were called
            mock_search.assert_called_once()
            mock_extract.assert_called_once()
            mock_assess.assert_called_once()

            # Verify result format
            assert isinstance(result, str)
            assert "search" in result.lower() or "results" in result.lower()

    @pytest.mark.asyncio
    async def test_individual_tool_calls(self, mock_dependencies):
        """Test individual tool calls work correctly."""
        # Test multi_engine_web_search tool
        with patch('agents.web_research_agent.tools.multi_engine_search') as mock_search:
            mock_search.return_value = {
                "success": True,
                "search_results": {"brave": [{"title": "Test", "url": "test.com", "description": "desc"}]},
                "metadata": {}
            }

            from ..agent import multi_engine_web_search
            result = await multi_engine_web_search(
                Mock(deps=mock_dependencies),
                query="test",
                engines=["brave"],
                max_results_per_engine=10
            )

            assert isinstance(result, str)
            assert "test" in result.lower()

        # Test extract_content_from_urls tool
        with patch('agents.web_research_agent.tools.extract_web_content') as mock_extract:
            mock_extract.return_value = [{
                "success": True,
                "metadata": {"title": "Test Title", "domain": "example.com", "word_count": 100},
                "content": "Test content for extraction"
            }]

            from ..agent import extract_content_from_urls
            result = await extract_content_from_urls(
                Mock(deps=mock_dependencies),
                urls=["https://example.com"],
                extract_metadata=True
            )

            assert isinstance(result, str)
            assert "extraction" in result.lower()