"""
Test integration scenarios for Citation Management Agent.
Validates workflow integration, AgentMessage protocol, and multi-agent coordination.
"""

import pytest
import asyncio
import json
from typing import List, Dict, Any
from datetime import date, datetime
from unittest.mock import Mock, AsyncMock, patch

from ..agent import agent, process_citation_request, run_citation_agent
from ..models import (
    CitationRequest,
    CitationResponse,
    SourceToCite,
    FormattedCitation,
    CitationValidation,
    CitationDependencies,
    AgentMessage
)


class TestWorkflowIntegration:
    """Test integration with research engineering workflow."""

    @pytest.mark.asyncio
    async def test_agent_message_protocol_compliance(self, test_dependencies):
        """Test agent complies with AgentMessage protocol from workflow architecture."""
        # Create a workflow message from Quality Assessment Agent
        agent_message = AgentMessage(
            sender_id="quality_assessment_agent",
            recipient_id="citation_management_agent",
            message_type="citation_request",
            payload={
                "sources": [
                    {
                        "source_id": "qa_source_1",
                        "title": "Validated Research Paper",
                        "authors": ["Researcher, Lead", "Scientist, Senior"],
                        "publication_date": "2023-05-15",
                        "url": "https://journal.example.com/validated-paper",
                        "source_type": "journal",
                        "additional_metadata": {
                            "quality_score": 0.95,
                            "credibility_rating": "high",
                            "peer_reviewed": True
                        }
                    }
                ],
                "citation_style": "APA",
                "include_bibliography": True,
                "request_id": "qa_citation_001"
            },
            timestamp="2023-09-27T10:00:00Z",
            correlation_id="workflow_research_session_001",
            priority=2
        )

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            # Mock agent response
            mock_response = AsyncMock()
            mock_response.data = CitationResponse(
                request_id="qa_citation_001",
                citations=[
                    FormattedCitation(
                        source_id="qa_source_1",
                        citation_key="researcher2023",
                        inline_citation="(Researcher & Scientist, 2023)",
                        full_citation="Researcher, L., & Scientist, S. (2023). Validated Research Paper.",
                        citation_style="APA",
                        validation_status="valid"
                    )
                ],
                bibliography=["Researcher, L., & Scientist, S. (2023). Validated Research Paper."],
                citation_map={"qa_source_1": "researcher2023"},
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

            # Process the workflow message
            citation_request = CitationRequest(**agent_message.payload)
            result = await process_citation_request(citation_request, test_dependencies)

            assert isinstance(result, CitationResponse)
            assert result.request_id == agent_message.payload["request_id"]
            assert result.style_used == agent_message.payload["citation_style"]

    @pytest.mark.asyncio
    async def test_data_synthesis_integration(self, test_dependencies):
        """Test integration with Data Synthesis Agent workflow."""
        # Simulate sources from multiple research agents
        multi_agent_sources = [
            # From Web Research Agent
            SourceToCite(
                source_id="web_src_1",
                title="Online AI Research Trends",
                authors=["WebAuthor, First"],
                publication_date=date(2023, 6, 1),
                url="https://aitrends.com/research",
                source_type="web",
                additional_metadata={"source_agent": "web_research_agent"}
            ),
            # From Tool Integration Agent (internal document)
            SourceToCite(
                source_id="internal_doc_1",
                title="Internal AI Strategy Document",
                authors=["Strategy, Team"],
                publication_date=date(2023, 3, 15),
                source_type="report",
                additional_metadata={
                    "source_agent": "tool_integration_agent",
                    "document_type": "internal_strategy",
                    "access_level": "restricted"
                }
            ),
            # From Quality Assessment Agent (verified source)
            SourceToCite(
                source_id="verified_journal_1",
                title="Peer-Reviewed AI Ethics Study",
                authors=["Ethics, Professor", "Review, Peer"],
                publication_date=date(2023, 4, 20),
                source_type="journal",
                additional_metadata={
                    "source_agent": "quality_assessment_agent",
                    "quality_score": 0.92,
                    "verification_status": "verified"
                }
            )
        ]

        citation_request = CitationRequest(
            request_id="synthesis_citation_001",
            sources=multi_agent_sources,
            citation_style="Chicago",
            include_bibliography=True,
            sort_alphabetically=True
        )

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            mock_response = AsyncMock()
            mock_response.data = CitationResponse(
                request_id="synthesis_citation_001",
                citations=[
                    FormattedCitation(
                        source_id="web_src_1",
                        citation_key="webauthor2023",
                        inline_citation="(WebAuthor, 2023)",
                        full_citation='WebAuthor, First. "Online AI Research Trends." 2023.',
                        citation_style="Chicago",
                        validation_status="valid"
                    ),
                    FormattedCitation(
                        source_id="internal_doc_1",
                        citation_key="strategy2023",
                        inline_citation="(Strategy, 2023)",
                        full_citation='Strategy, Team. "Internal AI Strategy Document." 2023.',
                        citation_style="Chicago",
                        validation_status="valid"
                    ),
                    FormattedCitation(
                        source_id="verified_journal_1",
                        citation_key="ethics2023",
                        inline_citation="(Ethics, 2023)",
                        full_citation='Ethics, Professor, and Peer Review. "Peer-Reviewed AI Ethics Study." 2023.',
                        citation_style="Chicago",
                        validation_status="valid"
                    )
                ],
                bibliography=[
                    'Ethics, Professor, and Peer Review. "Peer-Reviewed AI Ethics Study." 2023.',
                    'Strategy, Team. "Internal AI Strategy Document." 2023.',
                    'WebAuthor, First. "Online AI Research Trends." 2023.'
                ],
                citation_map={
                    "web_src_1": "webauthor2023",
                    "internal_doc_1": "strategy2023",
                    "verified_journal_1": "ethics2023"
                },
                style_used="Chicago",
                validation_results=CitationValidation(
                    total_sources=3,
                    valid_citations=3,
                    warnings=[],
                    errors=[],
                    missing_fields={},
                    duplicate_sources=[]
                )
            )
            mock_run.return_value = mock_response

            result = await process_citation_request(citation_request, test_dependencies)

            # Verify proper citation handling for multi-agent sources
            assert len(result.citations) == 3
            assert len(result.bibliography) == 3
            assert result.style_used == "Chicago"

            # Verify bibliography is sorted alphabetically
            bibliography = result.bibliography
            for i in range(len(bibliography) - 1):
                assert bibliography[i].lower() <= bibliography[i + 1].lower()

    @pytest.mark.asyncio
    async def test_research_orchestrator_coordination(self, test_dependencies):
        """Test coordination with Research Orchestrator Agent."""
        # Simulate batch processing request from orchestrator
        orchestrator_message = AgentMessage(
            sender_id="research_orchestrator_agent",
            recipient_id="citation_management_agent",
            message_type="batch_citation_request",
            payload={
                "batch_id": "orchestrator_batch_001",
                "priority": "high",
                "deadline": "2023-09-27T12:00:00Z",
                "requests": [
                    {
                        "request_id": "batch_req_1",
                        "sources": [
                            {
                                "source_id": "batch_src_1",
                                "title": "AI Research Paper 1",
                                "authors": ["Author1, First"],
                                "source_type": "journal"
                            }
                        ],
                        "citation_style": "APA"
                    },
                    {
                        "request_id": "batch_req_2",
                        "sources": [
                            {
                                "source_id": "batch_src_2",
                                "title": "AI Research Paper 2",
                                "authors": ["Author2, Second"],
                                "source_type": "journal"
                            }
                        ],
                        "citation_style": "MLA"
                    }
                ]
            },
            correlation_id="orchestrator_coordination_001"
        )

        # Process batch requests
        results = []
        for req_data in orchestrator_message.payload["requests"]:
            citation_request = CitationRequest(
                request_id=req_data["request_id"],
                sources=[SourceToCite(**src) for src in req_data["sources"]],
                citation_style=req_data["citation_style"],
                include_bibliography=True,
                sort_alphabetically=True
            )

            with patch('agents.citation_management.agent.agent.run') as mock_run:
                mock_response = AsyncMock()
                mock_response.data = CitationResponse(
                    request_id=req_data["request_id"],
                    citations=[],
                    bibliography=[],
                    citation_map={},
                    style_used=req_data["citation_style"],
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
                results.append(result)

        # Verify all requests processed successfully
        assert len(results) == 2
        assert results[0].request_id == "batch_req_1"
        assert results[1].request_id == "batch_req_2"
        assert results[0].style_used == "APA"
        assert results[1].style_used == "MLA"


class TestConcurrentProcessing:
    """Test concurrent request handling and performance."""

    @pytest.mark.asyncio
    async def test_concurrent_citation_requests(self, sample_sources, test_dependencies):
        """Test agent handles concurrent citation requests properly."""
        # Create multiple concurrent requests
        requests = []
        for i in range(5):
            request = CitationRequest(
                request_id=f"concurrent_req_{i}",
                sources=sample_sources[i:i+1],  # One source per request
                citation_style="APA",
                include_bibliography=True,
                sort_alphabetically=True
            )
            requests.append(request)

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            mock_response = AsyncMock()
            mock_response.data = CitationResponse(
                request_id="test_request",
                citations=[],
                bibliography=[],
                citation_map={},
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

            # Process all requests concurrently
            tasks = [
                process_citation_request(req, test_dependencies)
                for req in requests
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should complete successfully
            assert len(results) == 5
            for result in results:
                assert not isinstance(result, Exception)
                assert isinstance(result, CitationResponse)

    @pytest.mark.asyncio
    async def test_high_volume_processing(self, large_source_dataset, test_dependencies):
        """Test agent performance with high-volume requests."""
        import time

        # Create large citation request
        citation_request = CitationRequest(
            request_id="high_volume_test",
            sources=large_source_dataset[:100],  # 100 sources
            citation_style="APA",
            include_bibliography=True,
            sort_alphabetically=True
        )

        start_time = time.time()

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            mock_response = AsyncMock()
            mock_response.data = CitationResponse(
                request_id="high_volume_test",
                citations=[],
                bibliography=[],
                citation_map={},
                style_used="APA",
                validation_results=CitationValidation(
                    total_sources=100,
                    valid_citations=100,
                    warnings=[],
                    errors=[],
                    missing_fields={},
                    duplicate_sources=[]
                )
            )
            mock_run.return_value = mock_response

            result = await process_citation_request(citation_request, test_dependencies)
            processing_time = time.time() - start_time

            # Should meet performance requirement: 100+ citations within 1 minute
            assert processing_time < 60.0  # 1 minute limit
            assert isinstance(result, CitationResponse)
            assert result.validation_results.total_sources == 100


class TestErrorHandlingIntegration:
    """Test error handling in integration scenarios."""

    @pytest.mark.asyncio
    async def test_partial_failure_handling(self, test_dependencies):
        """Test handling when some sources fail to process."""
        mixed_sources = [
            # Valid source
            SourceToCite(
                source_id="valid_src",
                title="Valid Research Paper",
                authors=["Valid, Author"],
                source_type="journal"
            ),
            # Problematic source (empty title)
            SourceToCite(
                source_id="problem_src",
                title="",  # Empty title
                authors=[],  # No authors
                source_type="web"
            )
        ]

        citation_request = CitationRequest(
            request_id="partial_failure_test",
            sources=mixed_sources,
            citation_style="APA",
            include_bibliography=True,
            sort_alphabetically=True
        )

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            # Mock partial success response
            mock_response = AsyncMock()
            mock_response.data = CitationResponse(
                request_id="partial_failure_test",
                citations=[
                    FormattedCitation(
                        source_id="valid_src",
                        citation_key="valid2023",
                        inline_citation="(Valid, 2023)",
                        full_citation="Valid, Author. (2023). Valid Research Paper.",
                        citation_style="APA",
                        validation_status="valid"
                    ),
                    FormattedCitation(
                        source_id="problem_src",
                        citation_key="error_key",
                        inline_citation="(Error)",
                        full_citation="Error formatting citation",
                        citation_style="APA",
                        validation_status="error"
                    )
                ],
                bibliography=["Valid, Author. (2023). Valid Research Paper."],
                citation_map={"valid_src": "valid2023"},
                style_used="APA",
                validation_results=CitationValidation(
                    total_sources=2,
                    valid_citations=1,
                    warnings=["problem_src: Missing required information"],
                    errors=["problem_src: Failed to format citation"],
                    missing_fields={"problem_src": ["title", "authors"]},
                    duplicate_sources=[]
                )
            )
            mock_run.return_value = mock_response

            result = await process_citation_request(citation_request, test_dependencies)

            # Should handle partial failures gracefully
            assert isinstance(result, CitationResponse)
            assert result.validation_results.total_sources == 2
            assert result.validation_results.valid_citations == 1
            assert len(result.validation_results.errors) > 0
            assert len(result.validation_results.warnings) > 0

    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self, citation_request, test_dependencies):
        """Test handling of agent timeouts."""
        # Set short timeout
        test_dependencies.timeout = 1  # 1 second

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            # Mock timeout
            mock_run.side_effect = asyncio.TimeoutError("Agent timed out")

            result = await process_citation_request(citation_request, test_dependencies)

            # Should return error response
            assert isinstance(result, CitationResponse)
            assert len(result.citations) == 0
            assert len(result.validation_results.errors) > 0
            assert "timeout" in result.validation_results.errors[0].lower() or "timed out" in result.validation_results.errors[0].lower()

    @pytest.mark.asyncio
    async def test_invalid_message_format_handling(self, test_dependencies):
        """Test handling of invalid workflow messages."""
        # Invalid AgentMessage
        invalid_message = {
            "invalid_field": "invalid_value",
            "missing_required_fields": True
        }

        # Should handle gracefully without crashing
        try:
            # This would be how invalid messages might be processed
            result = await run_citation_agent(
                sources=[],  # Empty sources
                citation_style="APA",
                request_id="invalid_test"
            )
            assert isinstance(result, CitationResponse)
        except Exception as e:
            # If exception occurs, it should be handled gracefully
            assert "validation" in str(e).lower() or "invalid" in str(e).lower()


class TestDataConsistency:
    """Test data consistency across integration scenarios."""

    @pytest.mark.asyncio
    async def test_citation_key_consistency(self, test_dependencies):
        """Test citation keys remain consistent across requests."""
        source = SourceToCite(
            source_id="consistency_test",
            title="Consistency Test Paper",
            authors=["Consistent, Author"],
            publication_date=date(2023, 1, 1),
            source_type="journal"
        )

        # Process same source twice
        citation_request1 = CitationRequest(
            request_id="consistency_req_1",
            sources=[source],
            citation_style="APA"
        )

        citation_request2 = CitationRequest(
            request_id="consistency_req_2",
            sources=[source],
            citation_style="APA"
        )

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            mock_response1 = AsyncMock()
            mock_response1.data = CitationResponse(
                request_id="consistency_req_1",
                citations=[
                    FormattedCitation(
                        source_id="consistency_test",
                        citation_key="consistent2023_consisten",
                        inline_citation="(Consistent, 2023)",
                        full_citation="Consistent, Author. (2023). Consistency Test Paper.",
                        citation_style="APA",
                        validation_status="valid"
                    )
                ],
                bibliography=[],
                citation_map={"consistency_test": "consistent2023_consisten"},
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

            mock_response2 = AsyncMock()
            mock_response2.data = CitationResponse(
                request_id="consistency_req_2",
                citations=[
                    FormattedCitation(
                        source_id="consistency_test",
                        citation_key="consistent2023_consisten",  # Same key
                        inline_citation="(Consistent, 2023)",
                        full_citation="Consistent, Author. (2023). Consistency Test Paper.",
                        citation_style="APA",
                        validation_status="valid"
                    )
                ],
                bibliography=[],
                citation_map={"consistency_test": "consistent2023_consisten"},
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

            mock_run.side_effect = [mock_response1, mock_response2]

            result1 = await process_citation_request(citation_request1, test_dependencies)
            result2 = await process_citation_request(citation_request2, test_dependencies)

            # Citation keys should be consistent
            key1 = result1.citation_map["consistency_test"]
            key2 = result2.citation_map["consistency_test"]
            assert key1 == key2

    @pytest.mark.asyncio
    async def test_style_consistency_across_requests(self, sample_sources, test_dependencies):
        """Test citation style consistency within and across requests."""
        for style in ["APA", "MLA", "Chicago", "IEEE", "Harvard"]:
            citation_request = CitationRequest(
                request_id=f"style_consistency_{style}",
                sources=sample_sources[:2],
                citation_style=style
            )

            with patch('agents.citation_management.agent.agent.run') as mock_run:
                mock_response = AsyncMock()
                mock_response.data = CitationResponse(
                    request_id=f"style_consistency_{style}",
                    citations=[
                        FormattedCitation(
                            source_id="src_1",
                            citation_key="test_key_1",
                            inline_citation="(Test, 2023)",
                            full_citation="Test citation 1",
                            citation_style=style,
                            validation_status="valid"
                        ),
                        FormattedCitation(
                            source_id="src_2",
                            citation_key="test_key_2",
                            inline_citation="(Test, 2023)",
                            full_citation="Test citation 2",
                            citation_style=style,
                            validation_status="valid"
                        )
                    ],
                    bibliography=[],
                    citation_map={},
                    style_used=style,
                    validation_results=CitationValidation(
                        total_sources=2,
                        valid_citations=2,
                        warnings=[],
                        errors=[],
                        missing_fields={},
                        duplicate_sources=[]
                    )
                )
                mock_run.return_value = mock_response

                result = await process_citation_request(citation_request, test_dependencies)

                # All citations should use the same style
                assert result.style_used == style
                for citation in result.citations:
                    assert citation.citation_style == style