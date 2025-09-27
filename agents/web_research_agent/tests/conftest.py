"""
Test configuration and fixtures for Web Research Agent.
Provides reusable fixtures for TestModel and FunctionModel testing.
"""

import pytest
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, MagicMock
import aiohttp

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import agent
from ..dependencies import WebResearchDependencies
from ..models import SearchRequest, WebSearchResults, WebSource, SourceMetadata


@pytest.fixture
def sample_search_request():
    """Sample search request for testing."""
    return SearchRequest(
        search_id="test-search-123",
        query="machine learning algorithms",
        search_engines=["brave"],
        max_results=10,
        quality_threshold=0.7,
        content_types=["article", "paper"]
    )


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for testing."""
    deps = Mock(spec=WebResearchDependencies)
    deps.brave_api_key = "test-brave-key"
    deps.google_search_api_key = "test-google-key"
    deps.google_search_engine_id = "test-cx"
    deps.bing_search_api_key = "test-bing-key"
    deps.max_results = 20
    deps.quality_threshold = 0.7
    deps.request_timeout = 30
    deps.rate_limit_delay = 0.1  # Fast for testing
    deps.max_parallel_requests = 5
    deps.max_content_length = 10000
    deps.user_agent = "TestAgent/1.0"
    deps.respect_robots_txt = False  # Skip for testing
    deps.session_id = "test-session"
    deps.workflow_context = {"test": True}
    deps.available_search_engines = ["brave", "google", "bing"]

    # Mock HTTP session
    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    deps.http_session = mock_session

    # Mock robots.txt check
    deps.can_scrape_url = Mock(return_value=True)

    # Mock cleanup
    deps.cleanup = AsyncMock()

    return deps


@pytest.fixture
def sample_search_results():
    """Sample search engine results for testing."""
    return {
        "brave": [
            {
                "title": "Introduction to Machine Learning",
                "url": "https://example.com/ml-intro",
                "description": "Comprehensive guide to ML algorithms",
                "age": "2024-01-15",
                "engine": "brave",
                "rank": 1
            },
            {
                "title": "Deep Learning Fundamentals",
                "url": "https://example.com/dl-fundamentals",
                "description": "Understanding neural networks and deep learning",
                "age": "2024-02-01",
                "engine": "brave",
                "rank": 2
            }
        ]
    }


@pytest.fixture
def sample_extracted_content():
    """Sample extracted content for testing."""
    return [
        {
            "url": "https://example.com/ml-intro",
            "success": True,
            "content": "Machine learning is a branch of artificial intelligence that focuses on building applications that can learn from data and improve their accuracy over time without being programmed to do so.",
            "metadata": {
                "title": "Introduction to Machine Learning",
                "author": "Dr. Jane Smith",
                "publish_date": "2024-01-15T10:00:00Z",
                "word_count": 150,
                "domain": "example.com",
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "content_type": "article",
                "language": "en"
            },
            "error": None
        },
        {
            "url": "https://example.com/dl-fundamentals",
            "success": True,
            "content": "Deep learning is a subset of machine learning that uses neural networks with multiple layers to model and understand complex patterns in data.",
            "metadata": {
                "title": "Deep Learning Fundamentals",
                "author": "Prof. John Doe",
                "publish_date": "2024-02-01T14:30:00Z",
                "word_count": 200,
                "domain": "example.com",
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "content_type": "article",
                "language": "en"
            },
            "error": None
        }
    ]


@pytest.fixture
def test_model():
    """Create TestModel for fast testing."""
    return TestModel()


@pytest.fixture
def test_agent(test_model):
    """Create agent with TestModel for testing."""
    return agent.override(model=test_model)


@pytest.fixture
def search_function_model():
    """Create FunctionModel for controlled search behavior."""
    call_count = 0

    async def search_function(messages, tools):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            # First call - analyze request
            return ModelTextResponse(
                content="I'll perform a comprehensive web search for your query."
            )
        elif call_count == 2:
            # Second call - execute search tool
            return {
                "search_and_extract": {
                    "query": "test query",
                    "search_engines": ["brave"],
                    "max_results": 10,
                    "quality_threshold": 0.7
                }
            }
        else:
            # Final response
            return ModelTextResponse(
                content="Web research completed successfully. Here are the results..."
            )

    return FunctionModel(search_function)


@pytest.fixture
def content_extraction_function_model():
    """Create FunctionModel for content extraction testing."""
    async def extraction_function(messages, tools):
        # Simulate content extraction workflow
        return {
            "extract_content_from_urls": {
                "urls": ["https://example.com/test"],
                "extract_metadata": True
            }
        }

    return FunctionModel(extraction_function)


@pytest.fixture
def quality_assessment_function_model():
    """Create FunctionModel for quality assessment testing."""
    async def quality_function(messages, tools):
        # Simulate quality assessment workflow
        return {
            "assess_web_content_quality": {
                "extracted_content": [{"url": "test", "content": "test content"}],
                "search_query": "test query",
                "quality_threshold": 0.7
            }
        }

    return FunctionModel(quality_function)


@pytest.fixture
def mock_http_responses():
    """Mock HTTP responses for different scenarios."""
    responses = {
        "brave_success": {
            "web": {
                "results": [
                    {
                        "title": "Test Result 1",
                        "url": "https://example.com/1",
                        "description": "Test description 1",
                        "age": "2024-01-01"
                    },
                    {
                        "title": "Test Result 2",
                        "url": "https://example.com/2",
                        "description": "Test description 2",
                        "age": "2024-01-02"
                    }
                ]
            }
        },
        "google_success": {
            "items": [
                {
                    "title": "Google Test Result",
                    "link": "https://google-example.com/test",
                    "snippet": "Google test description"
                }
            ]
        },
        "bing_success": {
            "webPages": {
                "value": [
                    {
                        "name": "Bing Test Result",
                        "url": "https://bing-example.com/test",
                        "snippet": "Bing test description",
                        "dateLastCrawled": "2024-01-01T10:00:00Z"
                    }
                ]
            }
        },
        "content_html": """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Article</title>
            <meta name="author" content="Test Author">
        </head>
        <body>
            <article>
                <h1>Test Article Title</h1>
                <p>This is a test article content for extraction testing.</p>
                <p>It contains multiple paragraphs to test content quality.</p>
            </article>
        </body>
        </html>
        """
    }
    return responses


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()