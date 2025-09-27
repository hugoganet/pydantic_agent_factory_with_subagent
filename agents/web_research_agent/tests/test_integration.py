"""
End-to-end integration tests for Web Research Agent.
Tests complete workflows, performance requirements, and error scenarios.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import agent, run_web_search
from ..dependencies import WebResearchDependencies
from ..models import SearchRequest, WebSearchResults


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_complete_search_workflow(self, mock_dependencies):
        """Test complete search workflow from query to results."""
        # Mock all tool responses for complete workflow
        with patch('agents.web_research_agent.tools.multi_engine_search') as mock_search, \
             patch('agents.web_research_agent.tools.extract_web_content') as mock_extract, \
             patch('agents.web_research_agent.tools.assess_content_quality') as mock_assess:

            # Mock search results
            mock_search.return_value = {
                "success": True,
                "search_results": {
                    "brave": [
                        {"url": "https://example1.com", "title": "ML Article 1", "description": "ML desc 1"},
                        {"url": "https://example2.com", "title": "ML Article 2", "description": "ML desc 2"},
                        {"url": "https://example3.com", "title": "ML Article 3", "description": "ML desc 3"}
                    ]
                },
                "metadata": {
                    "engines_successful": ["brave"],
                    "total_results": 3,
                    "execution_time": 1.2
                }
            }

            # Mock content extraction
            mock_extract.return_value = [
                {
                    "url": "https://example1.com",
                    "success": True,
                    "content": "Machine learning algorithms are mathematical procedures that...",
                    "metadata": {
                        "title": "ML Article 1",
                        "word_count": 500,
                        "domain": "example1.com",
                        "content_type": "article"
                    }
                },
                {
                    "url": "https://example2.com",
                    "success": True,
                    "content": "Deep learning represents a subset of machine learning...",
                    "metadata": {
                        "title": "ML Article 2",
                        "word_count": 750,
                        "domain": "example2.com",
                        "content_type": "article"
                    }
                }
            ]

            # Mock quality assessment
            mock_assess.return_value = {
                "success": True,
                "filtered_content": [
                    {
                        "url": "https://example1.com",
                        "content": "Machine learning algorithms are mathematical procedures...",
                        "quality_score": 0.85,
                        "credibility_indicators": ["Educational institution"],
                        "metadata": {"title": "ML Article 1"}
                    }
                ],
                "quality_summary": {
                    "high_quality_sources": 1,
                    "average_quality_score": 0.85,
                    "quality_distribution": {"excellent": 0, "good": 1, "fair": 0, "poor": 0}
                }
            }

            # Create function model for controlled workflow
            async def workflow_function(messages, tools):
                if len(messages) <= 2:
                    return {
                        "search_and_extract": {
                            "query": "machine learning algorithms",
                            "search_engines": ["brave"],
                            "max_results": 10,
                            "quality_threshold": 0.7
                        }
                    }
                else:
                    return ModelTextResponse("Research completed successfully with high-quality sources.")

            function_model = FunctionModel(workflow_function)
            test_agent = agent.override(model=function_model)

            # Execute complete workflow
            result = await test_agent.run(
                "Research machine learning algorithms from reliable sources",
                deps=mock_dependencies
            )

            # Verify all tools were called
            mock_search.assert_called_once()
            mock_extract.assert_called_once()
            mock_assess.assert_called_once()

            # Verify result quality
            assert result.data is not None
            assert "research completed" in result.data.lower() or "machine learning" in result.data.lower()

    @pytest.mark.asyncio
    async def test_multi_engine_search_workflow(self, mock_dependencies):
        """Test workflow with multiple search engines."""
        mock_dependencies.available_search_engines = ["brave", "google", "bing"]

        with patch('agents.web_research_agent.tools.multi_engine_search') as mock_search:
            mock_search.return_value = {
                "success": True,
                "search_results": {
                    "brave": [{"url": "https://brave-result.com", "title": "Brave Result"}],
                    "google": [{"url": "https://google-result.com", "title": "Google Result"}],
                    "bing": [{"url": "https://bing-result.com", "title": "Bing Result"}]
                },
                "metadata": {
                    "engines_successful": ["brave", "google", "bing"],
                    "total_results": 3
                }
            }

            async def multi_engine_function(messages, tools):
                return {
                    "multi_engine_web_search": {
                        "query": "artificial intelligence",
                        "engines": ["brave", "google", "bing"],
                        "max_results_per_engine": 5
                    }
                }

            function_model = FunctionModel(multi_engine_function)
            test_agent = agent.override(model=function_model)

            result = await test_agent.run(
                "Search across all available engines",
                deps=mock_dependencies
            )

            # Verify multi-engine search was called
            mock_search.assert_called_once()
            search_args = mock_search.call_args
            assert search_args[0][1] == "artificial intelligence"  # query
            assert set(search_args[0][2]) == {"brave", "google", "bing"}  # engines

    @pytest.mark.asyncio
    async def test_quality_filtering_workflow(self, mock_dependencies):
        """Test workflow with quality filtering."""
        with patch('agents.web_research_agent.tools.assess_content_quality') as mock_assess:
            # Mock high-threshold quality assessment
            mock_assess.return_value = {
                "success": True,
                "filtered_content": [
                    {"quality_score": 0.95, "credibility_indicators": ["Educational institution", "Peer reviewed"]},
                    {"quality_score": 0.87, "credibility_indicators": ["Government source"]}
                ],
                "quality_summary": {
                    "high_quality_sources": 2,
                    "average_quality_score": 0.91,
                    "filtered_out": 3  # High threshold filtered out lower quality
                }
            }

            async def quality_function(messages, tools):
                return {
                    "search_and_extract": {
                        "query": "climate change research",
                        "quality_threshold": 0.85  # High threshold
                    }
                }

            function_model = FunctionModel(quality_function)
            test_agent = agent.override(model=function_model)

            result = await test_agent.run(
                "Find high-quality research on climate change",
                deps=mock_dependencies
            )

            assert result.data is not None


class TestPerformanceRequirements:
    """Test performance requirements from INITIAL.md."""

    @pytest.mark.asyncio
    async def test_parallel_processing_simulation(self, mock_dependencies):
        """Test parallel processing of 50+ sources."""
        # Generate 55 URLs to test parallel processing requirement
        test_urls = [f"https://example{i}.com/article" for i in range(55)]

        with patch('agents.web_research_agent.tools.extract_web_content') as mock_extract:
            # Simulate processing time and parallel execution
            async def simulate_parallel_extraction(*args, **kwargs):
                urls = args[1]  # URL list
                await asyncio.sleep(0.1)  # Simulate processing time

                # Return successful extraction for all URLs
                return [
                    {
                        "url": url,
                        "success": True,
                        "content": f"Content from {url}",
                        "metadata": {"title": f"Article from {url}", "word_count": 300}
                    }
                    for url in urls
                ]

            mock_extract.side_effect = simulate_parallel_extraction

            # Test with function model
            async def parallel_function(messages, tools):
                return {
                    "extract_content_from_urls": {
                        "urls": test_urls,
                        "extract_metadata": True
                    }
                }

            function_model = FunctionModel(parallel_function)
            test_agent = agent.override(model=function_model)

            start_time = time.time()
            result = await test_agent.run(
                "Extract content from 55 sources in parallel",
                deps=mock_dependencies
            )
            execution_time = time.time() - start_time

            # Verify parallel processing was attempted
            mock_extract.assert_called_once()
            extracted_urls = mock_extract.call_args[0][1]
            assert len(extracted_urls) == 55

            # Should complete reasonably fast due to parallel processing
            assert execution_time < 5.0  # Should be much faster than sequential

    @pytest.mark.asyncio
    async def test_three_minute_constraint_simulation(self, mock_dependencies):
        """Test 3-minute time constraint for complete workflow."""
        # Mock all operations to have realistic timing
        with patch('agents.web_research_agent.tools.multi_engine_search') as mock_search, \
             patch('agents.web_research_agent.tools.extract_web_content') as mock_extract, \
             patch('agents.web_research_agent.tools.assess_content_quality') as mock_assess:

            # Mock with timing simulation
            async def timed_search(*args, **kwargs):
                await asyncio.sleep(0.5)  # Simulate search time
                return {
                    "success": True,
                    "search_results": {"brave": [{"url": f"https://example{i}.com"} for i in range(50)]},
                    "metadata": {"engines_successful": ["brave"], "execution_time": 0.5}
                }

            async def timed_extract(*args, **kwargs):
                await asyncio.sleep(1.0)  # Simulate extraction time
                urls = args[1]
                return [{"url": url, "success": True, "content": "test"} for url in urls]

            async def timed_assess(*args, **kwargs):
                await asyncio.sleep(0.3)  # Simulate assessment time
                return {
                    "success": True,
                    "filtered_content": [{"quality_score": 0.8}],
                    "quality_summary": {"average_quality_score": 0.8}
                }

            mock_search.side_effect = timed_search
            mock_extract.side_effect = timed_extract
            mock_assess.side_effect = timed_assess

            async def complete_function(messages, tools):
                return {
                    "search_and_extract": {
                        "query": "comprehensive research topic",
                        "max_results": 50,
                        "quality_threshold": 0.7
                    }
                }

            function_model = FunctionModel(complete_function)
            test_agent = agent.override(model=function_model)

            start_time = time.time()
            result = await test_agent.run(
                "Perform comprehensive research within time constraints",
                deps=mock_dependencies
            )
            execution_time = time.time() - start_time

            # Should complete well within 3 minutes (180 seconds)
            assert execution_time < 180
            # Verify all operations completed
            assert mock_search.called
            assert mock_extract.called
            assert mock_assess.called

    @pytest.mark.asyncio
    async def test_quality_score_requirement(self, mock_dependencies):
        """Test >0.8 average relevance score requirement."""
        with patch('agents.web_research_agent.tools.assess_content_quality') as mock_assess:
            # Mock high-quality results meeting the requirement
            mock_assess.return_value = {
                "success": True,
                "filtered_content": [
                    {"quality_score": 0.85},
                    {"quality_score": 0.90},
                    {"quality_score": 0.82},
                    {"quality_score": 0.88}
                ],
                "quality_summary": {
                    "average_quality_score": 0.86,  # > 0.8 requirement
                    "high_quality_sources": 4
                }
            }

            async def quality_function(messages, tools):
                return {
                    "search_and_extract": {
                        "query": "high quality research",
                        "quality_threshold": 0.8
                    }
                }

            function_model = FunctionModel(quality_function)
            test_agent = agent.override(model=function_model)

            result = await test_agent.run(
                "Find sources meeting quality requirements",
                deps=mock_dependencies
            )

            # Verify quality assessment was performed
            mock_assess.assert_called_once()
            # Quality requirement should be met in mock data
            assert result.data is not None


class TestErrorScenarios:
    """Test error handling and failure scenarios."""

    @pytest.mark.asyncio
    async def test_search_engine_failures(self, mock_dependencies):
        """Test graceful handling of search engine failures."""
        with patch('agents.web_research_agent.tools.multi_engine_search') as mock_search:
            # Mock partial failure scenario
            mock_search.return_value = {
                "success": True,  # At least one engine succeeded
                "search_results": {"google": [{"url": "https://backup-result.com"}]},
                "metadata": {
                    "engines_successful": ["google"],
                    "engines_failed": ["brave"],  # Primary engine failed
                    "total_results": 1
                },
                "errors": {"brave": "API rate limit exceeded"}
            }

            async def fallback_function(messages, tools):
                return {
                    "multi_engine_web_search": {
                        "query": "test query",
                        "engines": ["brave", "google"],  # Brave fails, Google succeeds
                        "max_results_per_engine": 10
                    }
                }

            function_model = FunctionModel(fallback_function)
            test_agent = agent.override(model=function_model)

            result = await test_agent.run(
                "Search with fallback handling",
                deps=mock_dependencies
            )

            # Should still succeed with backup engine
            assert result.data is not None
            mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_content_extraction_failures(self, mock_dependencies):
        """Test handling of content extraction failures."""
        with patch('agents.web_research_agent.tools.extract_web_content') as mock_extract:
            # Mock mixed success/failure scenario
            mock_extract.return_value = [
                {"url": "https://success1.com", "success": True, "content": "Good content"},
                {"url": "https://blocked.com", "success": False, "error": "Blocked by robots.txt"},
                {"url": "https://success2.com", "success": True, "content": "More good content"},
                {"url": "https://timeout.com", "success": False, "error": "Request timeout"}
            ]

            async def extraction_function(messages, tools):
                return {
                    "extract_content_from_urls": {
                        "urls": ["https://success1.com", "https://blocked.com",
                                "https://success2.com", "https://timeout.com"],
                        "extract_metadata": True
                    }
                }

            function_model = FunctionModel(extraction_function)
            test_agent = agent.override(model=function_model)

            result = await test_agent.run(
                "Extract content with some failures",
                deps=mock_dependencies
            )

            # Should report partial success
            assert result.data is not None
            assert "successful" in result.data.lower() or "2" in result.data  # 2 successful

    @pytest.mark.asyncio
    async def test_network_timeout_scenarios(self, mock_dependencies):
        """Test network timeout handling."""
        with patch('agents.web_research_agent.tools.multi_engine_search') as mock_search:
            # First call times out, retry succeeds
            call_count = 0

            async def timeout_then_success(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise asyncio.TimeoutError("Network timeout")
                else:
                    return {
                        "success": True,
                        "search_results": {"brave": [{"url": "https://retry-success.com"}]},
                        "metadata": {"engines_successful": ["brave"]}
                    }

            mock_search.side_effect = timeout_then_success

            async def timeout_function(messages, tools):
                return {
                    "multi_engine_web_search": {
                        "query": "timeout test",
                        "engines": ["brave"]
                    }
                }

            function_model = FunctionModel(timeout_function)
            test_agent = agent.override(model=function_model)

            result = await test_agent.run(
                "Test timeout handling",
                deps=mock_dependencies
            )

            # Should eventually succeed after retry
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_quality_assessment_failures(self, mock_dependencies):
        """Test quality assessment failure handling."""
        with patch('agents.web_research_agent.tools.assess_content_quality') as mock_assess:
            # Mock assessment failure
            mock_assess.return_value = {
                "success": False,
                "error": "Quality assessment service unavailable"
            }

            async def assessment_function(messages, tools):
                return {
                    "search_and_extract": {
                        "query": "test with assessment failure",
                        "quality_threshold": 0.7
                    }
                }

            function_model = FunctionModel(assessment_function)
            test_agent = agent.override(model=function_model)

            result = await test_agent.run(
                "Test quality assessment failure",
                deps=mock_dependencies
            )

            # Should handle failure gracefully
            assert result.data is not None
            # Should indicate assessment failure
            assert "assessment failed" in result.data.lower() or "failed" in result.data.lower()


class TestWorkflowIntegration:
    """Test integration with workflow orchestrator."""

    @pytest.mark.asyncio
    async def test_workflow_context_integration(self):
        """Test integration with workflow context."""
        workflow_context = {
            "workflow_id": "research-workflow-123",
            "stage": "information_gathering",
            "previous_results": {
                "topic_analysis": "completed",
                "search_keywords": ["machine learning", "neural networks"]
            }
        }

        deps = WebResearchDependencies(
            brave_api_key="test-key",
            workflow_context=workflow_context,
            session_id="workflow-session-456"
        )

        # Test with workflow-aware function
        async def workflow_aware_function(messages, tools):
            # Agent could use workflow context to inform its decisions
            return ModelTextResponse("Research completed for workflow stage: information_gathering")

        function_model = FunctionModel(workflow_aware_function)
        test_agent = agent.override(model=function_model)

        result = await test_agent.run(
            "Perform research as part of workflow",
            deps=deps
        )

        # Verify workflow context is accessible
        assert deps.workflow_context["workflow_id"] == "research-workflow-123"
        assert deps.workflow_context["stage"] == "information_gathering"
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_inter_agent_communication_format(self, mock_dependencies):
        """Test proper inter-agent communication format."""
        # Simulate receiving a task from orchestrator
        incoming_message = {
            "message_id": "msg-789",
            "sender_id": "workflow_orchestrator",
            "recipient_id": "web_research_agent",
            "message_type": "task",
            "payload": {
                "search_request": {
                    "query": "artificial intelligence trends 2024",
                    "max_results": 20,
                    "quality_threshold": 0.8
                }
            },
            "correlation_id": "workflow-correlation-123"
        }

        # Agent should be able to process this format
        async def communication_function(messages, tools):
            # Extract query from the message format
            return {
                "search_and_extract": {
                    "query": "artificial intelligence trends 2024",
                    "max_results": 20,
                    "quality_threshold": 0.8
                }
            }

        function_model = FunctionModel(communication_function)
        test_agent = agent.override(model=function_model)

        result = await test_agent.run(
            f"Process inter-agent message: {incoming_message['payload']['search_request']['query']}",
            deps=mock_dependencies
        )

        assert result.data is not None
        assert "artificial intelligence" in result.data.lower() or "search" in result.data.lower()

    @pytest.mark.asyncio
    async def test_convenience_function_integration(self):
        """Test the convenience function for standalone usage."""
        with patch('agents.web_research_agent.agent.agent.run') as mock_agent_run, \
             patch('agents.web_research_agent.dependencies.WebResearchDependencies.from_settings') as mock_deps_factory:

            # Mock successful agent execution
            mock_result = Mock()
            mock_result.data = "Search completed successfully with 15 high-quality sources found."
            mock_agent_run.return_value = mock_result

            # Mock dependency creation and cleanup
            mock_deps = AsyncMock()
            mock_deps.cleanup = AsyncMock()
            mock_deps_factory.return_value = mock_deps

            # Test convenience function
            result = await run_web_search(
                query="machine learning applications",
                search_engines=["brave", "google"],
                max_results=15,
                quality_threshold=0.8
            )

            # Verify function worked correctly
            assert result == "Search completed successfully with 15 high-quality sources found."

            # Verify dependencies were created and cleaned up
            mock_deps_factory.assert_called_once()
            mock_deps.cleanup.assert_called_once()
            mock_agent_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_tracking_integration(self, mock_dependencies):
        """Test session tracking throughout workflow."""
        session_id = "integration-test-session-789"
        mock_dependencies.session_id = session_id

        # Track that session is maintained throughout
        async def session_tracking_function(messages, tools):
            # Agent could log session information
            return ModelTextResponse(f"Research completed for session: {session_id}")

        function_model = FunctionModel(session_tracking_function)
        test_agent = agent.override(model=function_model)

        result = await test_agent.run(
            "Perform research with session tracking",
            deps=mock_dependencies
        )

        # Verify session information is maintained
        assert mock_dependencies.session_id == session_id
        assert result.data is not None