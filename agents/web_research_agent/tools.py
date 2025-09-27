"""
Tools for Web Research Agent.
Implements multi-engine search, content extraction, and quality assessment tools.
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Literal, Callable
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import aiohttp
import numpy as np
from bs4 import BeautifulSoup
from pydantic_ai import RunContext
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .dependencies import WebResearchDependencies

logger = logging.getLogger(__name__)


# Custom exceptions
class WebResearchError(Exception):
    """Base exception for web research tool errors."""
    pass


class SearchEngineError(WebResearchError):
    """Exception for search engine API failures."""
    pass


class ContentExtractionError(WebResearchError):
    """Exception for content extraction failures."""
    pass


# Tool 1: Multi-Engine Search
async def multi_engine_search(
    ctx: RunContext[WebResearchDependencies],
    query: str,
    engines: List[Literal["brave", "google", "bing"]] = ["brave"],
    max_results_per_engine: int = 20
) -> Dict[str, Any]:
    """
    Execute web searches across multiple search engines with fallback handling.

    Args:
        query: Search query to execute
        engines: List of search engines to use in order of preference
        max_results_per_engine: Maximum results to retrieve per engine (1-100)

    Returns:
        Dictionary containing search results from all successful engines
    """
    logger.info(f"Executing multi-engine search for query: {query}")

    # Validate engines against available ones
    available_engines = ctx.deps.available_search_engines
    valid_engines = [e for e in engines if e in available_engines]

    if not valid_engines:
        raise SearchEngineError(f"None of the requested engines {engines} are available. Available: {available_engines}")

    start_time = time.time()
    search_results = {}
    metadata = {
        "engines_attempted": valid_engines,
        "engines_successful": [],
        "engines_failed": [],
        "total_results": 0,
        "rate_limit_delays": {}
    }
    errors = {}

    # Execute searches in parallel
    search_tasks = []
    for engine in valid_engines:
        if engine == "brave" and ctx.deps.brave_api_key:
            search_tasks.append(execute_brave_search(ctx, query, max_results_per_engine))
        elif engine == "google" and ctx.deps.google_search_api_key:
            search_tasks.append(execute_google_search(ctx, query, max_results_per_engine))
        elif engine == "bing" and ctx.deps.bing_search_api_key:
            search_tasks.append(execute_bing_search(ctx, query, max_results_per_engine))

    # Wait for all searches to complete
    search_responses = await asyncio.gather(*search_tasks, return_exceptions=True)

    # Process results
    for i, response in enumerate(search_responses):
        engine = valid_engines[i]

        if isinstance(response, Exception):
            metadata["engines_failed"].append(engine)
            errors[engine] = str(response)
            logger.error(f"Search failed for {engine}: {response}")
        else:
            search_results[engine] = response["results"]
            metadata["engines_successful"].append(engine)
            metadata["total_results"] += len(response["results"])
            metadata["rate_limit_delays"][engine] = response.get("delay", 0)
            logger.info(f"Search completed for {engine}: {len(response['results'])} results")

    execution_time = time.time() - start_time
    metadata["execution_time"] = execution_time

    return {
        "success": len(metadata["engines_successful"]) > 0,
        "search_results": search_results,
        "metadata": metadata,
        "errors": errors
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
)
async def execute_brave_search(
    ctx: RunContext[WebResearchDependencies],
    query: str,
    count: int
) -> Dict[str, Any]:
    """Search using Brave Search API."""
    await asyncio.sleep(ctx.deps.rate_limit_delay)

    async with ctx.deps.http_session.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"X-Subscription-Token": ctx.deps.brave_api_key},
        params={
            "q": query,
            "count": min(count, 20),  # Brave limit
            "offset": 0,
            "country": "US",
            "search_lang": "en",
            "ui_lang": "en-US"
        }
    ) as response:
        response.raise_for_status()
        data = await response.json()

        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "age": item.get("age"),
                "engine": "brave",
                "rank": len(results) + 1
            })

        return {
            "results": results,
            "delay": ctx.deps.rate_limit_delay
        }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
)
async def execute_google_search(
    ctx: RunContext[WebResearchDependencies],
    query: str,
    count: int
) -> Dict[str, Any]:
    """Search using Google Custom Search API."""
    await asyncio.sleep(ctx.deps.rate_limit_delay)

    async with ctx.deps.http_session.get(
        "https://www.googleapis.com/customsearch/v1",
        params={
            "key": ctx.deps.google_search_api_key,
            "cx": ctx.deps.google_search_engine_id,
            "q": query,
            "num": min(count, 10),  # Google limit per request
            "start": 1,
            "gl": "US",
            "hl": "en"
        }
    ) as response:
        response.raise_for_status()
        data = await response.json()

        results = []
        for item in data.get("items", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "description": item.get("snippet", ""),
                "age": None,
                "engine": "google",
                "rank": len(results) + 1
            })

        return {
            "results": results,
            "delay": ctx.deps.rate_limit_delay
        }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
)
async def execute_bing_search(
    ctx: RunContext[WebResearchDependencies],
    query: str,
    count: int
) -> Dict[str, Any]:
    """Search using Bing Search API."""
    await asyncio.sleep(ctx.deps.rate_limit_delay)

    async with ctx.deps.http_session.get(
        "https://api.bing.microsoft.com/v7.0/search",
        headers={"Ocp-Apim-Subscription-Key": ctx.deps.bing_search_api_key},
        params={
            "q": query,
            "count": min(count, 50),  # Bing limit
            "offset": 0,
            "mkt": "en-US",
            "responseFilter": "Webpages"
        }
    ) as response:
        response.raise_for_status()
        data = await response.json()

        results = []
        for item in data.get("webPages", {}).get("value", []):
            results.append({
                "title": item.get("name", ""),
                "url": item.get("url", ""),
                "description": item.get("snippet", ""),
                "age": item.get("dateLastCrawled"),
                "engine": "bing",
                "rank": len(results) + 1
            })

        return {
            "results": results,
            "delay": ctx.deps.rate_limit_delay
        }


# Tool 2: Web Content Extraction
async def extract_web_content(
    ctx: RunContext[WebResearchDependencies],
    urls: List[str],
    extract_metadata: bool = True,
    respect_robots: bool = True
) -> List[Dict[str, Any]]:
    """
    Extract clean text content from web sources with parallel processing.

    Args:
        urls: List of URLs to extract content from
        extract_metadata: Whether to extract metadata (title, author, date)
        respect_robots: Whether to check robots.txt before scraping

    Returns:
        List of extracted content with metadata for each successful URL
    """
    logger.info(f"Extracting content from {len(urls)} URLs")

    # Process URLs in parallel batches
    batch_size = 10
    max_concurrent = min(ctx.deps.max_parallel_requests, 10)
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_semaphore(url: str) -> Dict[str, Any]:
        async with semaphore:
            return await extract_single_url(ctx, url, extract_metadata, respect_robots)

    results = []
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[process_with_semaphore(url) for url in batch],
            return_exceptions=True
        )

        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Content extraction failed: {result}")
                results.append({
                    "url": "unknown",
                    "success": False,
                    "error": str(result),
                    "content": "",
                    "metadata": {}
                })
            else:
                results.append(result)

    successful_extractions = len([r for r in results if r.get("success", False)])
    logger.info(f"Content extraction completed: {successful_extractions}/{len(results)} successful")

    return results


async def extract_single_url(
    ctx: RunContext[WebResearchDependencies],
    url: str,
    extract_metadata: bool,
    respect_robots: bool
) -> Dict[str, Any]:
    """Extract content from a single URL."""
    try:
        # Check robots.txt if requested
        if respect_robots and ctx.deps.respect_robots_txt:
            if not ctx.deps.can_scrape_url(url):
                return {
                    "url": url,
                    "success": False,
                    "error": "Robots.txt disallows access",
                    "content": "",
                    "metadata": {}
                }

        # Fetch page content
        async with ctx.deps.http_session.get(url) as response:
            response.raise_for_status()
            html_content = await response.text()

        # Extract content using BeautifulSoup (simplified approach)
        content, metadata = extract_with_beautifulsoup(html_content, url)

        # Limit content length
        if len(content) > ctx.deps.max_content_length:
            content = content[:ctx.deps.max_content_length] + "... [truncated]"

        return {
            "url": url,
            "success": True,
            "content": content,
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "publish_date": metadata.get("publish_date"),
                "word_count": len(content.split()),
                "domain": urlparse(url).netloc,
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "content_type": detect_content_type(content),
                "language": "en"  # Simplified language detection
            },
            "error": None
        }

    except Exception as e:
        logger.error(f"Failed to extract content from {url}: {e}")
        return {
            "url": url,
            "success": False,
            "error": str(e),
            "content": "",
            "metadata": {}
        }


def extract_with_beautifulsoup(html: str, url: str) -> Tuple[str, Dict]:
    """Extract content using BeautifulSoup."""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove script and style elements
    for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
        script.decompose()

    # Extract text from main content areas
    content_selectors = [
        "article", "main", ".content", ".article-body",
        ".post-content", ".entry-content", "#content"
    ]

    best_content = ""
    for selector in content_selectors:
        elements = soup.select(selector)
        if elements:
            content = " ".join(elem.get_text(separator=' ', strip=True) for elem in elements)
            if len(content) > len(best_content):
                best_content = content

    if not best_content:
        best_content = soup.get_text(separator=' ', strip=True)

    # Extract metadata
    title_tag = soup.find('title')
    title = title_tag.get_text().strip() if title_tag else ""

    # Look for author meta tags
    author = ""
    author_selectors = ['meta[name="author"]', 'meta[property="article:author"]', '.author', '.byline']
    for selector in author_selectors:
        elem = soup.select_one(selector)
        if elem:
            author = elem.get('content', '') or elem.get_text().strip()
            break

    return best_content, {
        "title": title,
        "author": author
    }


def detect_content_type(content: str) -> str:
    """Detect content type based on content characteristics."""
    content_lower = content.lower()

    if any(keyword in content_lower for keyword in ['abstract', 'methodology', 'conclusion', 'references']):
        return "paper"
    elif any(keyword in content_lower for keyword in ['breaking', 'reported', 'according to']):
        return "news"
    elif len(content.split()) > 1000:
        return "article"
    else:
        return "webpage"


# Tool 3: Content Quality Assessment
async def assess_content_quality(
    ctx: RunContext[WebResearchDependencies],
    extracted_content: List[Dict[str, Any]],
    search_query: str,
    quality_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Assess the quality and relevance of extracted web content.

    Args:
        extracted_content: List of extracted content with metadata
        search_query: Original search query for relevance scoring
        quality_threshold: Minimum quality score to pass filtering

    Returns:
        Quality assessment results with scored and filtered content
    """
    logger.info(f"Assessing quality of {len(extracted_content)} content items")

    assessed_content = []

    for item in extracted_content:
        if not item.get("success", False) or not item.get("content"):
            continue

        content = item["content"]
        metadata = item.get("metadata", {})

        # Calculate quality score
        quality_score, indicators = await calculate_quality_score(content, metadata, search_query)

        assessed_item = {
            **item,
            "quality_score": quality_score,
            "credibility_indicators": indicators
        }
        assessed_content.append(assessed_item)

    # Filter and rank content
    result = await filter_and_rank_content(assessed_content, quality_threshold)

    logger.info(f"Quality assessment completed: {len(result['filtered_content'])}/{len(assessed_content)} passed threshold")

    return {
        "success": True,
        "filtered_content": result["filtered_content"],
        "quality_summary": result["quality_summary"],
        "assessment_metadata": {
            "quality_threshold_used": quality_threshold,
            "search_query": search_query,
            "assessment_timestamp": datetime.utcnow().isoformat(),
            "processing_time": 0.5  # Simplified timing
        }
    }


async def calculate_quality_score(
    content: str,
    metadata: Dict[str, Any],
    search_query: str
) -> Tuple[float, List[str]]:
    """Calculate comprehensive quality score for content."""

    scores = {}
    indicators = []

    # 1. Relevance Score (40% weight)
    relevance_score = calculate_relevance_score(content, search_query)
    scores['relevance'] = relevance_score * 0.4

    # 2. Content Quality Score (30% weight)
    content_quality = calculate_content_quality(content, metadata)
    scores['content_quality'] = content_quality * 0.3

    # 3. Source Credibility Score (20% weight)
    credibility_score, cred_indicators = calculate_credibility_score(metadata)
    scores['credibility'] = credibility_score * 0.2
    indicators.extend(cred_indicators)

    # 4. Freshness Score (10% weight)
    freshness_score = calculate_freshness_score(metadata)
    scores['freshness'] = freshness_score * 0.1

    total_score = sum(scores.values())

    return total_score, indicators


def calculate_relevance_score(content: str, search_query: str) -> float:
    """Calculate relevance score using TF-IDF similarity."""
    try:
        # Prepare texts for comparison
        texts = [search_query.lower(), content.lower()]

        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=1000
        )
        tfidf_matrix = vectorizer.fit_transform(texts)

        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

        # Boost score for exact keyword matches
        query_words = set(search_query.lower().split())
        content_words = set(content.lower().split())
        keyword_overlap = len(query_words.intersection(content_words)) / len(query_words) if query_words else 0

        # Combine similarity and keyword overlap
        final_score = (similarity * 0.7) + (keyword_overlap * 0.3)

        return min(final_score, 1.0)

    except Exception as e:
        logger.error(f"Relevance calculation failed: {e}")
        return 0.5  # Neutral score on failure


def calculate_content_quality(content: str, metadata: Dict[str, Any]) -> float:
    """Assess content quality based on structure and completeness."""
    quality_factors = []

    # Word count factor (optimal range: 300-3000 words)
    word_count = metadata.get('word_count', 0)
    if word_count < 100:
        word_factor = 0.2
    elif word_count < 300:
        word_factor = 0.6
    elif word_count <= 3000:
        word_factor = 1.0
    else:
        word_factor = 0.8
    quality_factors.append(word_factor)

    # Content structure (paragraphs, sentences)
    paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
    sentence_count = len(re.findall(r'[.!?]+', content))

    if paragraph_count >= 3 and sentence_count >= 5:
        structure_factor = 1.0
    elif paragraph_count >= 2 or sentence_count >= 3:
        structure_factor = 0.7
    else:
        structure_factor = 0.4
    quality_factors.append(structure_factor)

    # Language quality (basic grammar and coherence)
    coherence_score = assess_text_coherence(content)
    quality_factors.append(coherence_score)

    return np.mean(quality_factors)


def calculate_credibility_score(metadata: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Assess source credibility based on metadata."""
    credibility_score = 0.5  # Start with neutral
    indicators = []

    domain = metadata.get('domain', '')

    # Domain reputation (simplified scoring)
    if any(edu_domain in domain for edu_domain in ['.edu', '.ac.', 'university']):
        credibility_score += 0.3
        indicators.append("Educational institution")
    elif any(gov_domain in domain for gov_domain in ['.gov', '.mil']):
        credibility_score += 0.4
        indicators.append("Government source")
    elif any(org_domain in domain for org_domain in ['.org']):
        credibility_score += 0.2
        indicators.append("Non-profit organization")

    # Author information
    author = metadata.get('author', '')
    if author and len(author) > 2:
        credibility_score += 0.1
        indicators.append("Author identified")

    # Publication date
    if metadata.get('publish_date'):
        credibility_score += 0.1
        indicators.append("Publication date available")

    # Content type
    content_type = metadata.get('content_type', '')
    if content_type in ['article', 'paper', 'report']:
        credibility_score += 0.1
        indicators.append(f"Credible content type: {content_type}")

    return min(credibility_score, 1.0), indicators


def calculate_freshness_score(metadata: Dict[str, Any]) -> float:
    """Calculate freshness score based on publication date."""
    publish_date = metadata.get('publish_date')
    if not publish_date:
        return 0.5  # Neutral if no date

    try:
        pub_date = datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
        days_old = (datetime.now(timezone.utc) - pub_date).days

        if days_old <= 30:
            return 1.0
        elif days_old <= 90:
            return 0.8
        elif days_old <= 365:
            return 0.6
        elif days_old <= 1095:  # 3 years
            return 0.4
        else:
            return 0.2

    except Exception:
        return 0.5


def assess_text_coherence(text: str) -> float:
    """Basic text coherence assessment."""
    # Simple heuristics for text quality
    sentences = re.split(r'[.!?]+', text)

    if len(sentences) < 2:
        return 0.3

    # Check for reasonable sentence lengths
    sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
    if not sentence_lengths:
        return 0.3

    avg_sentence_length = np.mean(sentence_lengths)

    if 5 <= avg_sentence_length <= 30:
        length_score = 1.0
    elif 3 <= avg_sentence_length <= 40:
        length_score = 0.7
    else:
        length_score = 0.4

    # Check for repetitive content
    unique_sentences = len(set(s.strip().lower() for s in sentences if s.strip()))
    repetition_score = min(unique_sentences / len(sentences), 1.0) if sentences else 0

    return (length_score * 0.6) + (repetition_score * 0.4)


async def filter_and_rank_content(
    assessed_content: List[Dict[str, Any]],
    quality_threshold: float
) -> Dict[str, Any]:
    """Filter content by quality threshold and rank by score."""

    # Filter by quality threshold
    high_quality = [
        item for item in assessed_content
        if item.get('quality_score', 0) >= quality_threshold
    ]

    # Sort by quality score (descending)
    high_quality.sort(key=lambda x: x.get('quality_score', 0), reverse=True)

    # Generate summary statistics
    all_scores = [item.get('quality_score', 0) for item in assessed_content]

    return {
        "filtered_content": high_quality,
        "quality_summary": {
            "total_sources": len(assessed_content),
            "high_quality_sources": len(high_quality),
            "filtered_out": len(assessed_content) - len(high_quality),
            "average_quality_score": np.mean(all_scores) if all_scores else 0,
            "quality_distribution": {
                "excellent": len([s for s in all_scores if s >= 0.9]),
                "good": len([s for s in all_scores if 0.7 <= s < 0.9]),
                "fair": len([s for s in all_scores if 0.5 <= s < 0.7]),
                "poor": len([s for s in all_scores if s < 0.5])
            }
        }
    }