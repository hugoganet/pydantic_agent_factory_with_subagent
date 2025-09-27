"""
Test configuration for Citation Management Agent.
Provides fixtures and test utilities for all test modules.
"""

import pytest
import asyncio
from typing import List, Dict, Any
from datetime import date
from unittest.mock import Mock, AsyncMock
from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel

from ..models import (
    CitationRequest,
    CitationResponse,
    SourceToCite,
    FormattedCitation,
    CitationValidation,
    CitationDependencies
)
from ..agent import agent


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_dependencies():
    """Create test dependencies for agent execution."""
    return CitationDependencies(
        session_id="test_session",
        batch_size=10,
        duplicate_threshold=0.85,
        validate_citations=True,
        max_retries=1,
        timeout=5,
        debug=True
    )


@pytest.fixture
def sample_sources():
    """Create sample sources for testing."""
    return [
        SourceToCite(
            source_id="src_1",
            title="The Impact of AI on Research Methodology",
            authors=["Smith, John A.", "Doe, Jane B."],
            publication_date=date(2023, 3, 15),
            url="https://example.com/ai-research-methodology",
            source_type="journal",
            additional_metadata={
                "journal_name": "Journal of AI Research",
                "volume": "10",
                "issue": "2",
                "pages": "123-145",
                "doi": "10.1000/182"
            }
        ),
        SourceToCite(
            source_id="src_2",
            title="Machine Learning in Academic Writing",
            authors=["Brown, Alice C."],
            publication_date=date(2023, 1, 10),
            url="https://example.com/ml-academic-writing",
            source_type="web",
            additional_metadata={"accessed_date": "2023-09-27"}
        ),
        SourceToCite(
            source_id="src_3",
            title="Deep Learning Fundamentals",
            authors=["Wilson, Robert", "Davis, Sarah"],
            publication_date=date(2022, 12, 5),
            source_type="book",
            additional_metadata={
                "publisher": "Academic Press",
                "isbn": "978-0123456789",
                "edition": "3rd"
            }
        ),
        # Duplicate source for testing
        SourceToCite(
            source_id="src_4",
            title="The Impact of AI on Research Methodology",  # Same title as src_1
            authors=["Smith, John A.", "Doe, Jane B."],  # Same authors
            publication_date=date(2023, 3, 15),
            url="https://example.com/ai-research-methodology",  # Same URL
            source_type="journal",
            additional_metadata={
                "journal_name": "Journal of AI Research",
                "volume": "10",
                "issue": "2",
                "pages": "123-145"
            }
        )
    ]


@pytest.fixture
def incomplete_sources():
    """Create sources with missing information for validation testing."""
    return [
        SourceToCite(
            source_id="incomplete_1",
            title="Incomplete Source Example",
            authors=[],  # Missing authors
            publication_date=None,  # Missing date
            source_type="web",
            additional_metadata={}
        ),
        SourceToCite(
            source_id="incomplete_2",
            title="",  # Missing title
            authors=["Unknown Author"],
            publication_date=date(2023, 1, 1),
            source_type="journal",
            additional_metadata={}
        )
    ]


@pytest.fixture
def citation_request(sample_sources):
    """Create a standard citation request for testing."""
    return CitationRequest(
        request_id="test_request_001",
        sources=sample_sources,
        citation_style="APA",
        include_bibliography=True,
        sort_alphabetically=True
    )


@pytest.fixture
def test_model():
    """Create TestModel for fast testing without API calls."""
    return TestModel()


@pytest.fixture
def test_agent(test_model):
    """Create agent with TestModel for testing."""
    return agent.override(model=test_model)


@pytest.fixture
def formatted_citations():
    """Create sample formatted citations for testing."""
    return [
        FormattedCitation(
            source_id="src_1",
            citation_key="smith2023_src_1",
            inline_citation="(Smith & Doe, 2023)",
            full_citation="Smith, J. A., & Doe, J. B. (2023). The Impact of AI on Research Methodology. Journal of AI Research, 10(2), 123-145.",
            citation_style="APA",
            validation_status="valid"
        ),
        FormattedCitation(
            source_id="src_2",
            citation_key="brown2023_src_2",
            inline_citation="(Brown, 2023)",
            full_citation="Brown, A. C. (2023). Machine Learning in Academic Writing. Retrieved from https://example.com/ml-academic-writing",
            citation_style="APA",
            validation_status="valid"
        )
    ]


@pytest.fixture
def mock_llm_responses():
    """Create mock LLM responses for function model testing."""
    def create_citation_response_function():
        call_count = 0

        async def citation_function(messages, tools):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call - analyze request
                return "I'll process the citation request by detecting duplicates, formatting citations, and validating them."
            elif call_count == 2:
                # Tool call - detect duplicates
                return {
                    "detect_duplicates_tool": {
                        "sources": [
                            {
                                "source_id": "src_1",
                                "title": "The Impact of AI on Research",
                                "authors": ["Smith, John"],
                                "source_type": "journal"
                            }
                        ],
                        "similarity_threshold": 0.85
                    }
                }
            elif call_count == 3:
                # Tool call - format citations
                return {
                    "format_citations_tool": {
                        "sources": [
                            {
                                "source_id": "src_1",
                                "title": "The Impact of AI on Research",
                                "authors": ["Smith, John"],
                                "source_type": "journal"
                            }
                        ],
                        "citation_style": "APA",
                        "include_bibliography": True
                    }
                }
            elif call_count == 4:
                # Tool call - validate citations
                return {
                    "validate_citations_tool": {
                        "citations": [
                            {
                                "source_id": "src_1",
                                "citation_key": "smith2023",
                                "inline_citation": "(Smith, 2023)",
                                "full_citation": "Smith, J. (2023). The Impact of AI on Research.",
                                "citation_style": "APA",
                                "validation_status": "valid"
                            }
                        ]
                    }
                }
            else:
                # Final response with CitationResponse
                return """{
                    "request_id": "test_request",
                    "citations": [
                        {
                            "source_id": "src_1",
                            "citation_key": "smith2023",
                            "inline_citation": "(Smith, 2023)",
                            "full_citation": "Smith, J. (2023). The Impact of AI on Research.",
                            "citation_style": "APA",
                            "validation_status": "valid"
                        }
                    ],
                    "bibliography": ["Smith, J. (2023). The Impact of AI on Research."],
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
                }"""

        return citation_function

    return create_citation_response_function


@pytest.fixture
def function_model_agent(mock_llm_responses):
    """Create agent with FunctionModel for controlled behavior testing."""
    function_model = FunctionModel(mock_llm_responses())
    return agent.override(model=function_model)


# Performance testing fixtures
@pytest.fixture
def large_source_dataset():
    """Create large dataset for performance testing."""
    sources = []
    for i in range(150):  # Above the 100+ requirement
        sources.append(
            SourceToCite(
                source_id=f"perf_src_{i:03d}",
                title=f"Performance Test Source {i}",
                authors=[f"Author{i % 10}, Test"],
                publication_date=date(2023, 1, (i % 28) + 1),
                url=f"https://example.com/source-{i}",
                source_type="journal" if i % 2 == 0 else "web",
                additional_metadata={"test_data": True}
            )
        )
    return sources


@pytest.fixture
def duplicate_heavy_dataset():
    """Create dataset with many duplicates for duplicate detection testing."""
    sources = []
    # Create 20 unique sources
    for i in range(20):
        sources.append(
            SourceToCite(
                source_id=f"unique_{i}",
                title=f"Unique Source {i}",
                authors=[f"Author{i}, Unique"],
                publication_date=date(2023, 1, 1),
                source_type="journal",
                additional_metadata={}
            )
        )

    # Create 30 duplicates (varying similarity levels)
    for i in range(30):
        original_idx = i % 20
        sources.append(
            SourceToCite(
                source_id=f"duplicate_{i}",
                title=f"Unique Source {original_idx}",  # Exact match
                authors=[f"Author{original_idx}, Unique"],  # Exact match
                publication_date=date(2023, 1, 1),
                source_type="journal",
                additional_metadata={"duplicate": True}
            )
        )

    return sources


# Helper functions for tests
def assert_citation_format(citation: FormattedCitation, style: str):
    """Assert that citation follows format requirements for given style."""
    assert citation.citation_style.upper() == style.upper()
    assert citation.inline_citation is not None
    assert citation.full_citation is not None
    assert citation.citation_key is not None
    assert citation.source_id is not None

    if style.upper() == "APA":
        assert "(" in citation.inline_citation
        assert ")" in citation.inline_citation
    elif style.upper() == "MLA":
        assert "(" in citation.inline_citation
        assert ")" in citation.inline_citation
    # Add more style-specific assertions as needed


def assert_bibliography_sorted(bibliography: List[str]):
    """Assert that bibliography is sorted alphabetically."""
    if len(bibliography) <= 1:
        return True

    for i in range(len(bibliography) - 1):
        current = bibliography[i].lower()
        next_item = bibliography[i + 1].lower()
        assert current <= next_item, f"Bibliography not sorted: '{bibliography[i]}' should come after '{bibliography[i + 1]}'"


def calculate_duplicate_accuracy(detected_duplicates: List[Dict], expected_duplicates: List[Dict]) -> float:
    """Calculate accuracy of duplicate detection."""
    if not expected_duplicates:
        return 1.0 if not detected_duplicates else 0.0

    # Simplified accuracy calculation for testing
    detected_ids = set()
    for dup in detected_duplicates:
        detected_ids.update(dup.get("duplicate_source_ids", []))

    expected_ids = set()
    for dup in expected_duplicates:
        expected_ids.update(dup.get("duplicate_source_ids", []))

    if not expected_ids:
        return 1.0

    intersection = detected_ids.intersection(expected_ids)
    return len(intersection) / len(expected_ids)