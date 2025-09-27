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
            "I'll format these citations for you",
            {"format_citations_tool": {
                "sources": [source.model_dump() for source in sample_sources[:1]],
                "citation_style": "APA",
                "include_bibliography": True
            }},
            "Citations formatted successfully"
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


# Abbreviated version for space - the full test would continue with all other test classes