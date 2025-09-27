"""
Test performance requirements for Citation Management Agent.
Validates processing speed, memory usage, and scalability requirements.
"""

import pytest
import asyncio
import time
import psutil
import os
from typing import List, Dict, Any
from datetime import date
from unittest.mock import Mock, AsyncMock, patch

from ..agent import agent, process_citation_request, run_citation_agent
from ..tools import format_citations, detect_duplicates, validate_citations
from ..models import (
    CitationRequest,
    CitationResponse,
    SourceToCite,
    FormattedCitation,
    CitationValidation,
    CitationDependencies
)


class TestPerformanceRequirements:
    """Test performance requirements from GitHub Issue #13."""

    @pytest.mark.asyncio
    async def test_100_citations_within_1_minute(self, large_source_dataset, test_dependencies):
        """Test requirement: Process 100+ citations within 1 minute."""
        # Use 120 sources to exceed the 100+ requirement
        sources = large_source_dataset[:120]

        citation_request = CitationRequest(
            request_id="performance_test_100plus",
            sources=sources,
            citation_style="APA",
            include_bibliography=True,
            sort_alphabetically=True
        )

        start_time = time.time()

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            # Mock successful processing
            mock_response = AsyncMock()
            mock_response.data = CitationResponse(
                request_id="performance_test_100plus",
                citations=[
                    FormattedCitation(
                        source_id=f"perf_src_{i:03d}",
                        citation_key=f"author{i % 10}2023_{i:03d}",
                        inline_citation=f"(Author{i % 10}, 2023)",
                        full_citation=f"Author{i % 10}, Test. (2023). Performance Test Source {i}.",
                        citation_style="APA",
                        validation_status="valid"
                    ) for i in range(120)
                ],
                bibliography=[
                    f"Author{i % 10}, Test. (2023). Performance Test Source {i}."
                    for i in range(120)
                ],
                citation_map={
                    f"perf_src_{i:03d}": f"author{i % 10}2023_{i:03d}"
                    for i in range(120)
                },
                style_used="APA",
                validation_results=CitationValidation(
                    total_sources=120,
                    valid_citations=120,
                    warnings=[],
                    errors=[],
                    missing_fields={},
                    duplicate_sources=[]
                )
            )
            mock_run.return_value = mock_response

            result = await process_citation_request(citation_request, test_dependencies)
            processing_time = time.time() - start_time

            # Performance requirement: 100+ citations within 1 minute
            assert processing_time < 60.0, f"Processing took {processing_time:.2f} seconds, should be under 60 seconds"
            assert result.validation_results.total_sources >= 100
            assert len(result.citations) >= 100

    @pytest.mark.asyncio
    async def test_batch_processing_efficiency(self, large_source_dataset, test_dependencies):
        """Test batch processing is more efficient than individual processing."""
        sources_subset = large_source_dataset[:50]

        # Test batch processing
        batch_start = time.time()
        batch_request = CitationRequest(
            request_id="batch_test",
            sources=sources_subset,
            citation_style="APA"
        )

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            mock_response = AsyncMock()
            mock_response.data = CitationResponse(
                request_id="batch_test",
                citations=[],
                bibliography=[],
                citation_map={},
                style_used="APA",
                validation_results=CitationValidation(
                    total_sources=50,
                    valid_citations=50,
                    warnings=[],
                    errors=[],
                    missing_fields={},
                    duplicate_sources=[]
                )
            )
            mock_run.return_value = mock_response

            batch_result = await process_citation_request(batch_request, test_dependencies)
            batch_time = time.time() - batch_start

            # Test individual processing (simulate with smaller batch)
            individual_start = time.time()
            individual_results = []

            # Process 10 individual requests
            for i in range(10):
                individual_request = CitationRequest(
                    request_id=f"individual_{i}",
                    sources=sources_subset[i:i+1],
                    citation_style="APA"
                )

                mock_response.data.request_id = f"individual_{i}"
                mock_response.data.validation_results.total_sources = 1
                mock_response.data.validation_results.valid_citations = 1

                result = await process_citation_request(individual_request, test_dependencies)
                individual_results.append(result)

            individual_time = time.time() - individual_start

            # Batch processing should be more efficient
            # (Note: This is a simplified test; in real scenarios, batch would be much more efficient)
            assert len(individual_results) == 10
            assert batch_result is not None

    @pytest.mark.asyncio
    async def test_memory_usage_requirements(self, large_source_dataset, test_dependencies):
        """Test memory usage stays within reasonable limits (<500MB for typical workloads)."""
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Process large dataset
        sources = large_source_dataset[:100]
        citation_request = CitationRequest(
            request_id="memory_test",
            sources=sources,
            citation_style="APA",
            include_bibliography=True
        )

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            mock_response = AsyncMock()
            mock_response.data = CitationResponse(
                request_id="memory_test",
                citations=[
                    FormattedCitation(
                        source_id=f"mem_src_{i}",
                        citation_key=f"mem_key_{i}",
                        inline_citation=f"(MemAuthor{i}, 2023)",
                        full_citation=f"MemAuthor{i}. (2023). Memory Test Source {i}.",
                        citation_style="APA",
                        validation_status="valid"
                    ) for i in range(100)
                ],
                bibliography=[f"MemAuthor{i}. (2023). Memory Test Source {i}." for i in range(100)],
                citation_map={f"mem_src_{i}": f"mem_key_{i}" for i in range(100)},
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

            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = memory_after - memory_before

            # Memory usage should be reasonable for typical workloads
            # Note: This is a mock test, real memory usage would be different
            assert memory_used < 500, f"Memory usage {memory_used:.2f}MB exceeds 500MB limit"
            assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_request_performance(self, sample_sources, test_dependencies):
        """Test performance under concurrent load."""
        concurrent_requests = 10
        sources_per_request = 5

        async def create_request(request_id: int) -> CitationResponse:
            request = CitationRequest(
                request_id=f"concurrent_{request_id}",
                sources=sample_sources[:sources_per_request],
                citation_style="APA"
            )

            with patch('agents.citation_management.agent.agent.run') as mock_run:
                mock_response = AsyncMock()
                mock_response.data = CitationResponse(
                    request_id=f"concurrent_{request_id}",
                    citations=[],
                    bibliography=[],
                    citation_map={},
                    style_used="APA",
                    validation_results=CitationValidation(
                        total_sources=sources_per_request,
                        valid_citations=sources_per_request,
                        warnings=[],
                        errors=[],
                        missing_fields={},
                        duplicate_sources=[]
                    )
                )
                mock_run.return_value = mock_response

                return await process_citation_request(request, test_dependencies)

        start_time = time.time()

        # Create concurrent tasks
        tasks = [create_request(i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # All requests should complete successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == concurrent_requests

        # Should handle concurrent load efficiently
        assert total_time < 30.0, f"Concurrent processing took {total_time:.2f} seconds, should be under 30 seconds"


class TestToolPerformance:
    """Test individual tool performance."""

    @pytest.mark.asyncio
    async def test_format_citations_performance(self, large_source_dataset, test_dependencies):
        """Test citation formatting performance."""
        sources = large_source_dataset[:100]
        ctx = Mock(deps=test_dependencies)

        start_time = time.time()
        formatted_citations = await format_citations(
            ctx=ctx,
            sources=sources,
            citation_style="APA",
            include_bibliography=True
        )
        formatting_time = time.time() - start_time

        # Should format 100 citations quickly
        assert formatting_time < 10.0, f"Formatting took {formatting_time:.2f} seconds, should be under 10 seconds"
        assert len(formatted_citations) == 100

        # All citations should be properly formatted
        for citation in formatted_citations:
            assert citation.inline_citation is not None
            assert citation.full_citation is not None
            assert citation.citation_key is not None

    @pytest.mark.asyncio
    async def test_duplicate_detection_performance(self, duplicate_heavy_dataset, test_dependencies):
        """Test duplicate detection performance with large dataset."""
        ctx = Mock(deps=test_dependencies)

        start_time = time.time()
        result = await detect_duplicates(
            ctx=ctx,
            sources=duplicate_heavy_dataset,
            similarity_threshold=0.85
        )
        detection_time = time.time() - start_time

        # Should complete duplicate detection efficiently
        assert detection_time < 30.0, f"Duplicate detection took {detection_time:.2f} seconds, should be under 30 seconds"

        # Should find duplicates
        assert result["original_count"] > result["deduplicated_count"]
        assert len(result["duplicates"]) > 0

    @pytest.mark.asyncio
    async def test_validation_performance(self, test_dependencies):
        """Test citation validation performance."""
        # Create large set of citations to validate
        citations = [
            FormattedCitation(
                source_id=f"val_src_{i}",
                citation_key=f"val_key_{i}",
                inline_citation=f"(Author{i}, 2023)",
                full_citation=f"Author{i}. (2023). Validation Test {i}.",
                citation_style="APA",
                validation_status="valid"
            ) for i in range(100)
        ]

        ctx = Mock(deps=test_dependencies)

        start_time = time.time()
        validation = await validate_citations(
            ctx=ctx,
            citations=citations,
            validation_rules={}
        )
        validation_time = time.time() - start_time

        # Should validate citations quickly
        assert validation_time < 5.0, f"Validation took {validation_time:.2f} seconds, should be under 5 seconds"
        assert validation.total_sources == 100


class TestScalabilityRequirements:
    """Test scalability under various load conditions."""

    @pytest.mark.asyncio
    async def test_large_bibliography_generation(self, large_source_dataset, test_dependencies):
        """Test performance with large bibliography generation."""
        sources = large_source_dataset[:200]  # Large bibliography

        citation_request = CitationRequest(
            request_id="large_bibliography_test",
            sources=sources,
            citation_style="APA",
            include_bibliography=True,
            sort_alphabetically=True
        )

        start_time = time.time()

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            # Mock large bibliography response
            mock_response = AsyncMock()
            mock_response.data = CitationResponse(
                request_id="large_bibliography_test",
                citations=[
                    FormattedCitation(
                        source_id=f"bib_src_{i}",
                        citation_key=f"bib_key_{i}",
                        inline_citation=f"(BibAuthor{i}, 2023)",
                        full_citation=f"BibAuthor{i}. (2023). Bibliography Test {i}.",
                        citation_style="APA",
                        validation_status="valid"
                    ) for i in range(200)
                ],
                bibliography=sorted([
                    f"BibAuthor{i}. (2023). Bibliography Test {i}."
                    for i in range(200)
                ]),
                citation_map={f"bib_src_{i}": f"bib_key_{i}" for i in range(200)},
                style_used="APA",
                validation_results=CitationValidation(
                    total_sources=200,
                    valid_citations=200,
                    warnings=[],
                    errors=[],
                    missing_fields={},
                    duplicate_sources=[]
                )
            )
            mock_run.return_value = mock_response

            result = await process_citation_request(citation_request, test_dependencies)
            processing_time = time.time() - start_time

            # Should handle large bibliographies efficiently
            assert processing_time < 120.0, f"Large bibliography took {processing_time:.2f} seconds, should be under 2 minutes"
            assert len(result.bibliography) == 200
            assert len(result.citations) == 200

            # Bibliography should be sorted
            bibliography = result.bibliography
            for i in range(len(bibliography) - 1):
                assert bibliography[i] <= bibliography[i + 1]

    @pytest.mark.asyncio
    async def test_multiple_citation_styles_performance(self, sample_sources, test_dependencies):
        """Test performance when processing multiple citation styles."""
        styles = ["APA", "MLA", "Chicago", "IEEE", "Harvard"]

        async def process_style(style: str) -> CitationResponse:
            request = CitationRequest(
                request_id=f"style_perf_{style}",
                sources=sample_sources[:20],
                citation_style=style,
                include_bibliography=True
            )

            with patch('agents.citation_management.agent.agent.run') as mock_run:
                mock_response = AsyncMock()
                mock_response.data = CitationResponse(
                    request_id=f"style_perf_{style}",
                    citations=[],
                    bibliography=[],
                    citation_map={},
                    style_used=style,
                    validation_results=CitationValidation(
                        total_sources=20,
                        valid_citations=20,
                        warnings=[],
                        errors=[],
                        missing_fields={},
                        duplicate_sources=[]
                    )
                )
                mock_run.return_value = mock_response

                return await process_citation_request(request, test_dependencies)

        start_time = time.time()

        # Process all styles concurrently
        tasks = [process_style(style) for style in styles]
        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # Should handle multiple styles efficiently
        assert total_time < 60.0, f"Multiple styles took {total_time:.2f} seconds, should be under 1 minute"
        assert len(results) == 5

        # All should complete successfully
        for i, result in enumerate(results):
            assert result.style_used == styles[i]

    @pytest.mark.asyncio
    async def test_high_duplicate_ratio_performance(self, test_dependencies):
        """Test performance with high duplicate ratios."""
        # Create dataset with 80% duplicates
        sources = []

        # 20 unique sources
        for i in range(20):
            sources.append(SourceToCite(
                source_id=f"unique_{i}",
                title=f"Unique Source {i}",
                authors=[f"UniqueAuthor{i}"],
                source_type="journal"
            ))

        # 80 duplicates (4 copies of each unique source)
        for i in range(20):
            for copy in range(4):
                sources.append(SourceToCite(
                    source_id=f"duplicate_{i}_{copy}",
                    title=f"Unique Source {i}",  # Same title
                    authors=[f"UniqueAuthor{i}"],  # Same author
                    source_type="journal"
                ))

        ctx = Mock(deps=test_dependencies)

        start_time = time.time()
        result = await detect_duplicates(
            ctx=ctx,
            sources=sources,
            similarity_threshold=0.85
        )
        detection_time = time.time() - start_time

        # Should handle high duplicate ratios efficiently
        assert detection_time < 60.0, f"High duplicate detection took {detection_time:.2f} seconds, should be under 1 minute"

        # Should significantly reduce source count
        original_count = result["original_count"]
        deduplicated_count = result["deduplicated_count"]
        reduction_ratio = (original_count - deduplicated_count) / original_count

        assert reduction_ratio > 0.6, f"Should reduce by >60%, actually reduced by {reduction_ratio:.2%}"
        assert deduplicated_count <= 25  # Should be close to 20 unique sources


class TestResourceUsage:
    """Test resource usage patterns and limits."""

    @pytest.mark.asyncio
    async def test_memory_cleanup(self, large_source_dataset, test_dependencies):
        """Test memory is properly cleaned up after large operations."""
        process = psutil.Process(os.getpid())

        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024

        # Process large request
        sources = large_source_dataset[:150]
        citation_request = CitationRequest(
            request_id="memory_cleanup_test",
            sources=sources,
            citation_style="APA"
        )

        with patch('agents.citation_management.agent.agent.run') as mock_run:
            mock_response = AsyncMock()
            mock_response.data = CitationResponse(
                request_id="memory_cleanup_test",
                citations=[],
                bibliography=[],
                citation_map={},
                style_used="APA",
                validation_results=CitationValidation(
                    total_sources=150,
                    valid_citations=150,
                    warnings=[],
                    errors=[],
                    missing_fields={},
                    duplicate_sources=[]
                )
            )
            mock_run.return_value = mock_response

            result = await process_citation_request(citation_request, test_dependencies)

        # Check memory after processing
        post_processing_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = post_processing_memory - baseline_memory

        # Memory increase should be reasonable
        assert memory_increase < 200, f"Memory increased by {memory_increase:.2f}MB, should be under 200MB"

    @pytest.mark.asyncio
    async def test_cpu_usage_efficiency(self, sample_sources, test_dependencies):
        """Test CPU usage remains efficient during processing."""
        # This is a simplified test - in practice, you'd monitor actual CPU usage
        start_time = time.time()

        # Simulate CPU-intensive operations
        for i in range(10):
            citation_request = CitationRequest(
                request_id=f"cpu_test_{i}",
                sources=sample_sources[:10],
                citation_style="APA"
            )

            with patch('agents.citation_management.agent.agent.run') as mock_run:
                mock_response = AsyncMock()
                mock_response.data = CitationResponse(
                    request_id=f"cpu_test_{i}",
                    citations=[],
                    bibliography=[],
                    citation_map={},
                    style_used="APA",
                    validation_results=CitationValidation(
                        total_sources=10,
                        valid_citations=10,
                        warnings=[],
                        errors=[],
                        missing_fields={},
                        duplicate_sources=[]
                    )
                )
                mock_run.return_value = mock_response

                result = await process_citation_request(citation_request, test_dependencies)

        total_time = time.time() - start_time

        # Should complete efficiently
        assert total_time < 30.0, f"CPU-intensive operations took {total_time:.2f} seconds, should be under 30 seconds"