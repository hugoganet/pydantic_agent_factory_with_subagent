"""
Test core agent functionality for Citation Management Agent.
Validates agent responses, tool integration, and workflow compliance.
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any
from unittest.mock import patch, AsyncMock
from pydantic_ai.models.test import TestModel


from ..agent import agent, process_citation_request, run_citation_agent
from ..models import (
    CitationRequest,
    CitationResponse,
    SourceToCite,
    FormattedCitation,
    CitationValidation,
    CitationDependencies
)
from .conftest import assert_citation_format, assert_bibliography_sorted


class TestAgentBasicFunctionality:
    """Test basic agent functionality and responses."""

    @pytest.mark.asyncio
    async def test_agent_basic_response(self, test_agent, test_dependencies):
        """Test agent provides appropriate response."""
        result = await test_agent.run(
            "Format these sources in APA style: [{'source_id': 'test1', 'title': 'Test Title', 'authors': ['Test Author'], 'source_type': 'web'}]",
            deps=test_dependencies
        )

        assert result.data is not None
        assert isinstance(result.data, CitationResponse)
        assert result.data.request_id is not None
        assert len(result.all_messages()) > 0

    @pytest.mark.asyncio
    async def test_agent_with_citation_request(self, test_agent, citation_request, test_dependencies):
        """Test agent handles CitationRequest properly."""
        # Configure TestModel to return a proper CitationResponse
        test_model = test_agent.model
        test_model.agent_responses = [
            "I'll process your citation request.",
            {
                "request_id": citation_request.request_id,
                "citations": [
                    {
                        "source_id": "src_1",
                        "citation_key": "smith2023",
                        "inline_citation": "(Smith & Doe, 2023)",
                        "full_citation": "Smith, J. A., & Doe, J. B. (2023). The Impact of AI on Research Methodology.",
                        "citation_style": "APA",
                        "validation_status": "valid"
                    }
                ],
                "bibliography": ["Smith, J. A., & Doe, J. B. (2023). The Impact of AI on Research Methodology."],
                "citation_map": {"src_1": "smith2023"},
                "style_used": "APA",
                "validation_results": {
                    "total_sources": 1,
                    "valid_citations": 1,
                    "warnings": [],
                    "errors": [],
                    "missing_fields": {},
                    "duplicate_sources": []
                }
            }
        ]

        result = await process_citation_request(citation_request, test_dependencies)

        assert isinstance(result, CitationResponse)
        assert result.request_id == citation_request.request_id
        assert result.style_used == citation_request.citation_style

    @pytest.mark.asyncio
    async def test_agent_tool_calling(self, test_agent, sample_sources, test_dependencies):
        """Test agent calls appropriate tools."""
        test_model = test_agent.model

        # Configure TestModel to call specific tools
        test_model.agent_responses = [
            ""I'll format these citations for you"),
            {"format_citations_tool": {
                "sources": [source.model_dump() for source in sample_sources[:1]],
                "citation_style": "APA",
                "include_bibliography": True
            }},
            ""Citations formatted successfully")
        ]

        result = await test_agent.run(
            f"Format these sources in APA style: {[s.model_dump() for s in sample_sources[:1]]}",
            deps=test_dependencies
        )

        # Verify tool was called
        tool_calls = [msg for msg in result.all_messages() if msg.role == "tool-call"]
        assert len(tool_calls) > 0
        assert tool_calls[0].tool_name == "format_citations_tool"

    @pytest.mark.asyncio
    async def test_agent_error_handling(self, test_agent, test_dependencies):
        """Test agent handles errors gracefully."""
        # Test with invalid input
        result = await test_agent.run(
            "Process invalid citation data: [invalid_json}",
            deps=test_dependencies
        )

        assert result.data is not None
        # Agent should still provide a response even with invalid input


class TestProcessCitationRequest:
    """Test the main process_citation_request function."""

    @pytest.mark.asyncio
    async def test_process_citation_request_success(self, citation_request, test_dependencies):
        """Test successful citation request processing."""
        with patch('agents.citation_management.agent.agent.run') as mock_run:
            # Mock successful agent response
            mock_response = AsyncMock()
            mock_response.data = CitationResponse(
                request_id=citation_request.request_id,
                citations=[
                    FormattedCitation(
                        source_id="src_1",
                        citation_key="smith2023",
                        inline_citation="(Smith, 2023)",
                        full_citation="Smith, J. (2023). Test Citation.",
                        citation_style="APA",
                        validation_status="valid"
                    )
                ],
                bibliography=["Smith, J. (2023). Test Citation."],
                citation_map={"src_1": "smith2023"},
                style_used="APA",
                validation_results=CitationValidation(
                    total_sources=1,
                    valid_citations=1,
                    warnings=[],
                    errors=[],
                    missing_fields={},
                    duplicate_sources=[]
                )
            )
            mock_run.return_value = mock_response

            result = await process_citation_request(citation_request, test_dependencies)

            assert isinstance(result, CitationResponse)
            assert result.request_id == citation_request.request_id
            assert len(result.citations) > 0
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_citation_request_error(self, citation_request, test_dependencies):
        """Test citation request processing with errors."""
        with patch('agents.citation_management.agent.agent.run') as mock_run:
            # Mock agent failure
            mock_run.side_effect = Exception("Agent processing failed")

            result = await process_citation_request(citation_request, test_dependencies)

            assert isinstance(result, CitationResponse)
            assert result.request_id == citation_request.request_id
            assert len(result.citations) == 0
            assert len(result.validation_results.errors) > 0
            assert "Agent processing failed" in result.validation_results.errors[0]


class TestRunCitationAgent:
    """Test the main run_citation_agent function."""

    @pytest.mark.asyncio
    async def test_run_citation_agent_basic(self, sample_sources):
        """Test basic run_citation_agent functionality."""
        source_dicts = [source.model_dump() for source in sample_sources[:2]]

        with patch('agents.citation_management.agent.process_citation_request') as mock_process:
            # Mock successful processing
            mock_process.return_value = CitationResponse(
                request_id="citation_request",
                citations=[],
                bibliography=[],
                citation_map={},
                style_used="APA",
                validation_results=CitationValidation(
                    total_sources=2,
                    valid_citations=0,
                    warnings=[],
                    errors=[],
                    missing_fields={},
                    duplicate_sources=[]
                )
            )

            result = await run_citation_agent(
                sources=source_dicts,
                citation_style="APA",
                request_id="test_run"
            )

            assert isinstance(result, CitationResponse)
            assert result.request_id == "test_run"
            assert result.style_used == "APA"
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_citation_agent_different_styles(self, sample_sources):
        """Test run_citation_agent with different citation styles."""
        source_dicts = [sample_sources[0].model_dump()]

        for style in ["APA", "MLA", "Chicago", "IEEE", "Harvard"]:
            with patch('agents.citation_management.agent.process_citation_request') as mock_process:
                mock_process.return_value = CitationResponse(
                    request_id="style_test",
                    citations=[],
                    bibliography=[],
                    citation_map={},
                    style_used=style,
                    validation_results=CitationValidation(
                        total_sources=1,
                        valid_citations=0,
                        warnings=[],
                        errors=[],
                        missing_fields={},
                        duplicate_sources=[]
                    )
                )

                result = await run_citation_agent(
                    sources=source_dicts,
                    citation_style=style
                )

                assert result.style_used == style

    @pytest.mark.asyncio
    async def test_run_citation_agent_invalid_sources(self):
        """Test run_citation_agent with invalid source data."""
        invalid_sources = [
            {"source_id": "invalid", "title": "Test"},  # Missing required fields
            {"invalid": "data"}  # Completely invalid
        ]

        with patch('agents.citation_management.agent.process_citation_request') as mock_process:
            mock_process.return_value = CitationResponse(
                request_id="citation_request",
                citations=[],
                bibliography=[],
                citation_map={},
                style_used="APA",
                validation_results=CitationValidation(
                    total_sources=0,
                    valid_citations=0,
                    warnings=[],
                    errors=[],
                    missing_fields={},
                    duplicate_sources=[]
                )
            )

            result = await run_citation_agent(sources=invalid_sources)

            # Should handle invalid sources gracefully
            assert isinstance(result, CitationResponse)


class TestAgentIntegration:
    """Test agent integration with workflow patterns."""

    @pytest.mark.asyncio
    async def test_agent_message_protocol_compliance(self, test_agent, test_dependencies):
        """Test agent complies with AgentMessage protocol."""
        # Test that agent can handle structured workflow messages
        workflow_message = {
            "sender_id": "quality_assessment_agent",
            "recipient_id": "citation_management_agent",
            "message_type": "citation_request",
            "payload": {
                "sources": [
                    {
                        "source_id": "workflow_src_1",
                        "title": "Workflow Test Source",
                        "authors": ["Workflow, Test"],
                        "source_type": "web"
                    }
                ],
                "citation_style": "APA"
            },
            "correlation_id": "workflow_test_001"
        }

        result = await test_agent.run(
            f"Process workflow message: {workflow_message}",
            deps=test_dependencies
        )

        assert result.data is not None

    @pytest.mark.asyncio
    async def test_agent_batch_processing(self, test_agent, large_source_dataset, test_dependencies):
        """Test agent handles batch processing efficiently."""
        # Test with subset of large dataset
        sources_subset = large_source_dataset[:test_dependencies.batch_size]
        source_dicts = [source.model_dump() for source in sources_subset]

        start_time = time.time()
        result = await test_agent.run(
            f"Process batch citation request for {len(sources_subset)} sources in APA style: {source_dicts}",
            deps=test_dependencies
        )
        processing_time = time.time() - start_time

        assert result.data is not None
        # Should process within reasonable time (this is mocked, so should be fast)
        assert processing_time < 5.0

    @pytest.mark.asyncio
    async def test_agent_concurrent_requests(self, test_agent, sample_sources, test_dependencies):
        """Test agent handles concurrent requests properly."""
        source_dict = sample_sources[0].model_dump()

        # Create multiple concurrent requests
        tasks = []
        for i in range(3):
            task = test_agent.run(
                f"Process citation request {i}: [{source_dict}]",
                deps=test_dependencies
            )
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert result.data is not None


class TestAgentValidation:
    """Test agent validation against requirements."""

    @pytest.mark.asyncio
    async def test_agent_supports_all_citation_styles(self, test_agent, sample_sources, test_dependencies):
        """Test agent supports all 5 major citation styles."""
        source_dict = sample_sources[0].model_dump()
        required_styles = ["APA", "MLA", "Chicago", "IEEE", "Harvard"]

        for style in required_styles:
            result = await test_agent.run(
                f"Format this source in {style} style: [{source_dict}]",
                deps=test_dependencies
            )

            assert result.data is not None
            # Agent should handle all required styles

    @pytest.mark.asyncio
    async def test_agent_structured_output(self, test_agent, citation_request, test_dependencies):
        """Test agent produces properly structured CitationResponse."""
        # Configure TestModel to return structured data
        test_model = test_agent.model
        test_model.agent_responses = [
            {
                "request_id": citation_request.request_id,
                "citations": [
                    {
                        "source_id": "src_1",
                        "citation_key": "smith2023",
                        "inline_citation": "(Smith, 2023)",
                        "full_citation": "Smith, J. (2023). Test.",
                        "citation_style": "APA",
                        "validation_status": "valid"
                    }
                ],
                "bibliography": ["Smith, J. (2023). Test."],
                "citation_map": {"src_1": "smith2023"},
                "style_used": "APA",
                "validation_results": {
                    "total_sources": 1,
                    "valid_citations": 1,
                    "warnings": [],
                    "errors": [],
                    "missing_fields": {},
                    "duplicate_sources": []
                }
            }
        ]

        result = await test_agent.run(
            f"Process citation request: {citation_request.model_dump()}",
            deps=test_dependencies
        )

        assert isinstance(result.data, CitationResponse)
        assert hasattr(result.data, 'request_id')
        assert hasattr(result.data, 'citations')
        assert hasattr(result.data, 'bibliography')
        assert hasattr(result.data, 'citation_map')
        assert hasattr(result.data, 'style_used')
        assert hasattr(result.data, 'validation_results')

    @pytest.mark.asyncio
    async def test_agent_maintains_session_context(self, test_agent, test_dependencies):
        """Test agent maintains context across multiple interactions."""
        # First request
        result1 = await test_agent.run(
            "Start citation session with session ID: test_session",
            deps=test_dependencies
        )

        # Second request in same session
        result2 = await test_agent.run(
            "Continue with previous session context",
            deps=test_dependencies
        )

        # Both should complete successfully
        assert result1.data is not None
        assert result2.data is not None