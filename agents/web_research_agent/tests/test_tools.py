"""
Test individual tool implementations for Web Research Agent.
Validates search engines, content extraction, and quality assessment.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import aiohttp

from ..tools import (
    multi_engine_search, extract_web_content, assess_content_quality,
    execute_brave_search, execute_google_search, execute_bing_search,
    extract_single_url, calculate_quality_score, calculate_relevance_score,
    SearchEngineError, ContentExtractionError
)


class TestMultiEngineSearch:
    """Test multi-engine search functionality."""

    @pytest.mark.asyncio
    async def test_multi_engine_search_success(self, mock_dependencies):
        """Test successful multi-engine search."""
        # Mock successful search responses
        with patch('agents.web_research_agent.tools.execute_brave_search') as mock_brave:
            mock_brave.return_value = {
                "results": [
                    {"title": "Test 1", "url": "https://example.com/1", "description": "Desc 1", "rank": 1},
                    {"title": "Test 2", "url": "https://example.com/2", "description": "Desc 2", "rank": 2}
                ],
                "delay": 0.1
            }

            result = await multi_engine_search(
                Mock(deps=mock_dependencies),
                query="test query",
                engines=["brave"],
                max_results_per_engine=10
            )

            assert result["success"] is True
            assert "brave" in result["search_results"]
            assert len(result["search_results"]["brave"]) == 2
            assert result["metadata"]["engines_successful"] == ["brave"]
            assert result["metadata"]["total_results"] == 2

    @pytest.mark.asyncio
    async def test_multi_engine_search_fallback(self, mock_dependencies):
        """Test search engine fallback handling."""
        with patch('agents.web_research_agent.tools.execute_brave_search') as mock_brave, \
             patch('agents.web_research_agent.tools.execute_google_search') as mock_google:

            # Brave fails, Google succeeds
            mock_brave.side_effect = Exception("Brave API error")
            mock_google.return_value = {
                "results": [{"title": "Google Result", "url": "https://google-example.com", "description": "Google desc", "rank": 1}],
                "delay": 0.1
            }

            result = await multi_engine_search(
                Mock(deps=mock_dependencies),
                query="test query",
                engines=["brave", "google"],
                max_results_per_engine=10
            )

            assert result["success"] is True  # Google succeeded
            assert "google" in result["search_results"]
            assert "brave" in result["metadata"]["engines_failed"]
            assert "google" in result["metadata"]["engines_successful"]

    @pytest.mark.asyncio
    async def test_multi_engine_search_no_engines_available(self, mock_dependencies):
        """Test error when no search engines are available."""
        mock_dependencies.available_search_engines = []

        with pytest.raises(SearchEngineError):
            await multi_engine_search(
                Mock(deps=mock_dependencies),
                query="test query",
                engines=["brave"],
                max_results_per_engine=10
            )

    @pytest.mark.asyncio
    async def test_execute_brave_search(self, mock_dependencies):
        """Test Brave search API integration."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Brave Result",
                        "url": "https://brave-example.com",
                        "description": "Brave description",
                        "age": "2024-01-01"
                    }
                ]
            }
        }

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_dependencies.http_session = mock_session

        result = await execute_brave_search(
            Mock(deps=mock_dependencies),
            query="test",
            count=10
        )

        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Brave Result"
        assert result["results"][0]["engine"] == "brave"

    @pytest.mark.asyncio
    async def test_execute_google_search(self, mock_dependencies):
        """Test Google Custom Search API integration."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "title": "Google Result",
                    "link": "https://google-example.com",
                    "snippet": "Google snippet"
                }
            ]
        }

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_dependencies.http_session = mock_session

        result = await execute_google_search(
            Mock(deps=mock_dependencies),
            query="test",
            count=10
        )

        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Google Result"
        assert result["results"][0]["engine"] == "google"

    @pytest.mark.asyncio
    async def test_execute_bing_search(self, mock_dependencies):
        """Test Bing Search API integration."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "webPages": {
                "value": [
                    {
                        "name": "Bing Result",
                        "url": "https://bing-example.com",
                        "snippet": "Bing snippet",
                        "dateLastCrawled": "2024-01-01T10:00:00Z"
                    }
                ]
            }
        }

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_dependencies.http_session = mock_session

        result = await execute_bing_search(
            Mock(deps=mock_dependencies),
            query="test",
            count=10
        )

        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Bing Result"
        assert result["results"][0]["engine"] == "bing"


class TestContentExtraction:
    """Test web content extraction functionality."""

    @pytest.mark.asyncio
    async def test_extract_web_content_success(self, mock_dependencies):
        """Test successful content extraction."""
        with patch('agents.web_research_agent.tools.extract_single_url') as mock_extract:
            mock_extract.return_value = {
                "url": "https://example.com",
                "success": True,
                "content": "Test article content about machine learning algorithms.",
                "metadata": {
                    "title": "ML Article",
                    "author": "Test Author",
                    "word_count": 8,
                    "domain": "example.com",
                    "content_type": "article"
                },
                "error": None
            }

            result = await extract_web_content(
                Mock(deps=mock_dependencies),
                urls=["https://example.com"],
                extract_metadata=True,
                respect_robots=False
            )

            assert len(result) == 1
            assert result[0]["success"] is True
            assert result[0]["content"] == "Test article content about machine learning algorithms."
            assert result[0]["metadata"]["title"] == "ML Article"

    @pytest.mark.asyncio
    async def test_extract_single_url_success(self, mock_dependencies, mock_http_responses):
        """Test single URL content extraction."""
        mock_response = AsyncMock()
        mock_response.text.return_value = mock_http_responses["content_html"]

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_dependencies.http_session = mock_session
        mock_dependencies.max_content_length = 10000

        result = await extract_single_url(
            Mock(deps=mock_dependencies),
            url="https://example.com/test",
            extract_metadata=True,
            respect_robots=False
        )

        assert result["success"] is True
        assert "test article content" in result["content"].lower()
        assert result["metadata"]["title"] == "Test Article"
        assert result["metadata"]["domain"] == "example.com"

    @pytest.mark.asyncio
    async def test_extract_single_url_robots_blocked(self, mock_dependencies):
        """Test robots.txt blocking content extraction."""
        mock_dependencies.respect_robots_txt = True
        mock_dependencies.can_scrape_url.return_value = False

        result = await extract_single_url(
            Mock(deps=mock_dependencies),
            url="https://blocked-example.com/test",
            extract_metadata=True,
            respect_robots=True
        )

        assert result["success"] is False
        assert "robots.txt disallows" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_extract_web_content_parallel_processing(self, mock_dependencies):
        """Test parallel processing of multiple URLs."""
        urls = [f"https://example{i}.com" for i in range(20)]
        mock_dependencies.max_parallel_requests = 5

        with patch('agents.web_research_agent.tools.extract_single_url') as mock_extract:
            # Mock successful extraction for all URLs
            async def mock_extract_func(*args, **kwargs):
                await asyncio.sleep(0.01)  # Simulate processing time
                return {
                    "url": args[1],
                    "success": True,
                    "content": f"Content from {args[1]}",
                    "metadata": {"title": f"Title for {args[1]}", "word_count": 50},
                    "error": None
                }

            mock_extract.side_effect = mock_extract_func

            result = await extract_web_content(
                Mock(deps=mock_dependencies),
                urls=urls,
                extract_metadata=True
            )

            assert len(result) == 20
            successful = [r for r in result if r.get("success", False)]
            assert len(successful) == 20

    @pytest.mark.asyncio
    async def test_extract_content_error_handling(self, mock_dependencies):
        """Test error handling during content extraction."""
        with patch('agents.web_research_agent.tools.extract_single_url') as mock_extract:
            # Mix of successful and failed extractions
            async def mixed_extract_func(*args, **kwargs):
                url = args[1]
                if "fail" in url:
                    raise Exception("Network error")
                return {
                    "url": url,
                    "success": True,
                    "content": "Success content",
                    "metadata": {},
                    "error": None
                }

            mock_extract.side_effect = mixed_extract_func

            urls = ["https://success1.com", "https://fail1.com", "https://success2.com"]
            result = await extract_web_content(
                Mock(deps=mock_dependencies),
                urls=urls
            )

            assert len(result) == 3
            successful = [r for r in result if r.get("success", False)]
            failed = [r for r in result if not r.get("success", False)]
            assert len(successful) == 2
            assert len(failed) == 1


class TestQualityAssessment:
    """Test content quality assessment functionality."""

    @pytest.mark.asyncio
    async def test_assess_content_quality_success(self, sample_extracted_content):
        """Test successful quality assessment."""
        result = await assess_content_quality(
            Mock(deps=Mock()),
            extracted_content=sample_extracted_content,
            search_query="machine learning algorithms",
            quality_threshold=0.5
        )

        assert result["success"] is True
        assert len(result["filtered_content"]) >= 0
        assert "quality_summary" in result
        assert "assessment_metadata" in result

    def test_calculate_relevance_score(self):
        """Test relevance score calculation."""
        content = "Machine learning algorithms are important for data science and artificial intelligence applications."
        query = "machine learning algorithms"

        score = calculate_relevance_score(content, query)

        assert 0.0 <= score <= 1.0
        assert score > 0.3  # Should have good relevance

        # Test with unrelated content
        unrelated_content = "Cooking recipes for Italian pasta dishes."
        low_score = calculate_relevance_score(unrelated_content, query)
        assert low_score < score  # Should be less relevant

    @pytest.mark.asyncio
    async def test_calculate_quality_score(self):
        """Test comprehensive quality score calculation."""
        content = """
        Machine learning is a branch of artificial intelligence that focuses on building applications
        that can learn from data and improve their accuracy over time without being programmed to do so.
        This field has revolutionized many industries by enabling computers to perform tasks that
        traditionally required human intelligence.

        The core concept behind machine learning involves algorithms that can identify patterns in data
        and make predictions or decisions based on those patterns. There are several types of machine
        learning, including supervised learning, unsupervised learning, and reinforcement learning.
        """

        metadata = {
            "word_count": 200,
            "domain": "example.edu",
            "author": "Dr. Jane Smith",
            "publish_date": "2024-01-15T10:00:00Z",
            "content_type": "article"
        }

        score, indicators = await calculate_quality_score(
            content, metadata, "machine learning algorithms"
        )

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be decent quality
        assert len(indicators) > 0
        assert "Educational institution" in indicators

    @pytest.mark.asyncio
    async def test_quality_filtering_by_threshold(self, sample_extracted_content):
        """Test content filtering by quality threshold."""
        # Test with high threshold
        high_threshold_result = await assess_content_quality(
            Mock(deps=Mock()),
            extracted_content=sample_extracted_content,
            search_query="machine learning",
            quality_threshold=0.9
        )

        # Test with low threshold
        low_threshold_result = await assess_content_quality(
            Mock(deps=Mock()),
            extracted_content=sample_extracted_content,
            search_query="machine learning",
            quality_threshold=0.1
        )

        # Low threshold should include more content
        assert len(low_threshold_result["filtered_content"]) >= len(high_threshold_result["filtered_content"])

    @pytest.mark.asyncio
    async def test_quality_summary_statistics(self, sample_extracted_content):
        """Test quality summary statistics generation."""
        result = await assess_content_quality(
            Mock(deps=Mock()),
            extracted_content=sample_extracted_content,
            search_query="machine learning",
            quality_threshold=0.5
        )

        summary = result["quality_summary"]
        assert "total_sources" in summary
        assert "high_quality_sources" in summary
        assert "average_quality_score" in summary
        assert "quality_distribution" in summary

        # Check distribution categories
        dist = summary["quality_distribution"]
        assert all(key in dist for key in ["excellent", "good", "fair", "poor"])
        assert all(isinstance(count, int) for count in dist.values())

    @pytest.mark.asyncio
    async def test_empty_content_handling(self):
        """Test handling of empty or invalid content."""
        empty_content = [
            {"success": False, "content": "", "metadata": {}},
            {"success": True, "content": "", "metadata": {}}  # Empty but successful
        ]

        result = await assess_content_quality(
            Mock(deps=Mock()),
            extracted_content=empty_content,
            search_query="test",
            quality_threshold=0.5
        )

        assert result["success"] is True
        assert len(result["filtered_content"]) == 0  # No valid content to assess

    def test_content_type_detection(self):
        """Test content type detection functionality."""
        from ..tools import detect_content_type

        # Test academic paper
        paper_content = "Abstract: This paper presents a methodology for analyzing data. Conclusion: The results show significant improvement."
        assert detect_content_type(paper_content) == "paper"

        # Test news article
        news_content = "Breaking news: According to reports, the incident was reported this morning."
        assert detect_content_type(news_content) == "news"

        # Test long article
        long_content = "This is a comprehensive article. " * 200  # 1000+ words
        assert detect_content_type(long_content) == "article"

        # Test short webpage
        short_content = "This is a brief webpage description."
        assert detect_content_type(short_content) == "webpage"


class TestToolErrorHandling:
    """Test error handling across all tools."""

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, mock_dependencies):
        """Test handling of network timeouts."""
        with patch('agents.web_research_agent.tools.execute_brave_search') as mock_brave:
            mock_brave.side_effect = asyncio.TimeoutError("Request timeout")

            result = await multi_engine_search(
                Mock(deps=mock_dependencies),
                query="test query",
                engines=["brave"],
                max_results_per_engine=10
            )

            assert result["success"] is False
            assert "brave" in result["metadata"]["engines_failed"]

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, mock_dependencies):
        """Test rate limiting behavior."""
        mock_dependencies.rate_limit_delay = 0.1  # Fast for testing

        with patch('agents.web_research_agent.tools.execute_brave_search') as mock_brave:
            mock_brave.return_value = {"results": [], "delay": 0.1}

            start_time = asyncio.get_event_loop().time()
            await multi_engine_search(
                Mock(deps=mock_dependencies),
                query="test",
                engines=["brave"],
                max_results_per_engine=5
            )
            end_time = asyncio.get_event_loop().time()

            # Should have waited for rate limit delay
            assert end_time - start_time >= 0.1

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, mock_dependencies):
        """Test handling of malformed API responses."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {"invalid": "structure"}  # Missing expected fields

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_dependencies.http_session = mock_session

        # Should not raise exception, should handle gracefully
        result = await execute_brave_search(
            Mock(deps=mock_dependencies),
            query="test",
            count=10
        )

        # Should return empty results for malformed response
        assert len(result["results"]) == 0