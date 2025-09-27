# Web Research Agent - Tool Specifications

## Tool Architecture Overview

The Web Research Agent requires **3 essential tools** to fulfill its core responsibilities:

1. **multi_engine_search** - Execute searches across multiple search engines with intelligent fallback
2. **extract_web_content** - Extract and clean content from web sources with metadata
3. **assess_content_quality** - Evaluate source credibility and relevance using quality metrics

## Tool 1: Multi-Engine Search

### Purpose
Execute searches across Brave, Google, and Bing APIs with intelligent fallback handling and rate limiting.

### Tool Specification
```python
@agent.tool
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
```

### Implementation Requirements

#### Search Engine Integration
```python
# Brave Search API integration
async def search_brave(api_key: str, query: str, count: int) -> List[Dict]:
    """Search using Brave Search API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key},
            params={
                "q": query,
                "count": min(count, 20),  # Brave limit
                "offset": 0,
                "country": "US",
                "search_lang": "en",
                "ui_lang": "en-US"
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("web", {}).get("results", [])

# Google Custom Search integration
async def search_google(api_key: str, engine_id: str, query: str, count: int) -> List[Dict]:
    """Search using Google Custom Search API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": api_key,
                "cx": engine_id,
                "q": query,
                "num": min(count, 10),  # Google limit per request
                "start": 1,
                "gl": "US",
                "hl": "en"
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("items", [])

# Bing Search API integration
async def search_bing(api_key: str, query: str, count: int) -> List[Dict]:
    """Search using Bing Search API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.bing.microsoft.com/v7.0/search",
            headers={"Ocp-Apim-Subscription-Key": api_key},
            params={
                "q": query,
                "count": min(count, 50),  # Bing limit
                "offset": 0,
                "mkt": "en-US",
                "responseFilter": "Webpages"
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("webPages", {}).get("value", [])
```

#### Rate Limiting & Error Handling
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError))
)
async def execute_search_with_retry(
    search_func: Callable,
    *args,
    **kwargs
) -> List[Dict]:
    """Execute search with retry logic and rate limiting."""
    await asyncio.sleep(ctx.deps.rate_limit_delay)  # Rate limiting
    return await search_func(*args, **kwargs)
```

#### Response Format
```python
{
    "success": True,
    "search_results": {
        "brave": [
            {
                "title": "Page Title",
                "url": "https://example.com/page",
                "description": "Page description",
                "age": "2024-01-15T10:30:00Z",
                "engine": "brave",
                "rank": 1
            }
        ],
        "google": [...],
        "bing": [...]
    },
    "metadata": {
        "engines_attempted": ["brave", "google", "bing"],
        "engines_successful": ["brave", "google"],
        "engines_failed": ["bing"],
        "total_results": 45,
        "execution_time": 2.3,
        "rate_limit_delays": {"brave": 1.0, "google": 1.2}
    },
    "errors": {
        "bing": "API key invalid or expired"
    }
}
```

## Tool 2: Web Content Extraction

### Purpose
Extract clean, readable text content from URLs with metadata preservation and robust error handling.

### Tool Specification
```python
@agent.tool
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
```

### Implementation Requirements

#### Content Extraction Engine
```python
import newspaper
import requests_html
from bs4 import BeautifulSoup
from readability import Document
import asyncio
from urllib.robotparser import RobotFileParser

async def extract_single_url(
    session: requests_html.AsyncHTMLSession,
    url: str,
    extract_metadata: bool,
    respect_robots: bool
) -> Dict[str, Any]:
    """Extract content from a single URL."""
    try:
        # Check robots.txt if requested
        if respect_robots and not await check_robots_txt(url):
            return {
                "url": url,
                "success": False,
                "error": "Robots.txt disallows access",
                "content": "",
                "metadata": {}
            }

        # Fetch page content
        response = await session.get(url, timeout=30)
        response.html.render(timeout=20, wait=2)  # Handle JavaScript

        # Extract clean text using multiple methods
        content_methods = [
            extract_with_newspaper,
            extract_with_readability,
            extract_with_beautifulsoup
        ]

        best_content = ""
        metadata = {}

        for method in content_methods:
            try:
                content, meta = await method(response.html.html, url)
                if len(content) > len(best_content):
                    best_content = content
                    if extract_metadata:
                        metadata.update(meta)
                break
            except Exception as e:
                logger.debug(f"Content extraction method failed for {url}: {e}")
                continue

        return {
            "url": url,
            "success": True,
            "content": best_content,
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "publish_date": metadata.get("publish_date"),
                "word_count": len(best_content.split()),
                "domain": urlparse(url).netloc,
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "content_type": detect_content_type(best_content),
                "language": detect_language(best_content)
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

async def check_robots_txt(url: str) -> bool:
    """Check if robots.txt allows access to the URL."""
    try:
        rp = RobotFileParser()
        robots_url = urljoin(url, "/robots.txt")
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch("*", url)
    except Exception:
        return True  # Allow if robots.txt check fails

# Content extraction methods
async def extract_with_newspaper(html: str, url: str) -> Tuple[str, Dict]:
    """Extract content using newspaper3k library."""
    article = newspaper.Article(url)
    article.set_html(html)
    article.parse()

    return article.text, {
        "title": article.title,
        "author": ", ".join(article.authors),
        "publish_date": article.publish_date.isoformat() if article.publish_date else None
    }

async def extract_with_readability(html: str, url: str) -> Tuple[str, Dict]:
    """Extract content using readability library."""
    doc = Document(html, url=url)
    soup = BeautifulSoup(doc.content(), 'html.parser')

    return soup.get_text(separator=' ', strip=True), {
        "title": doc.title()
    }

async def extract_with_beautifulsoup(html: str, url: str) -> Tuple[str, Dict]:
    """Fallback extraction using BeautifulSoup."""
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

    title = soup.find('title')
    return best_content, {
        "title": title.get_text().strip() if title else ""
    }
```

#### Parallel Processing
```python
async def process_urls_in_batches(
    urls: List[str],
    batch_size: int = 10,
    max_concurrent: int = 5
) -> List[Dict[str, Any]]:
    """Process URLs in parallel batches to manage resource usage."""
    semaphore = asyncio.Semaphore(max_concurrent)
    session = requests_html.AsyncHTMLSession()

    async def process_with_semaphore(url: str) -> Dict[str, Any]:
        async with semaphore:
            return await extract_single_url(session, url, True, True)

    results = []
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[process_with_semaphore(url) for url in batch],
            return_exceptions=True
        )
        results.extend(batch_results)

    await session.close()
    return results
```

#### Response Format
```python
[
    {
        "url": "https://example.com/article",
        "success": True,
        "content": "Clean extracted text content...",
        "metadata": {
            "title": "Article Title",
            "author": "John Doe",
            "publish_date": "2024-01-15T10:30:00Z",
            "word_count": 850,
            "domain": "example.com",
            "extraction_timestamp": "2024-09-26T14:30:00Z",
            "content_type": "article",
            "language": "en"
        },
        "error": None
    },
    {
        "url": "https://blocked-site.com",
        "success": False,
        "content": "",
        "metadata": {},
        "error": "Robots.txt disallows access"
    }
]
```

## Tool 3: Content Quality Assessment

### Purpose
Evaluate extracted content for relevance, credibility, and quality using configurable scoring metrics.

### Tool Specification
```python
@agent.tool
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
```

### Implementation Requirements

#### Quality Scoring Algorithm
```python
import re
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

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
        keyword_overlap = len(query_words.intersection(content_words)) / len(query_words)

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
    avg_sentence_length = np.mean([len(s.split()) for s in sentences if s.strip()])

    if 5 <= avg_sentence_length <= 30:
        length_score = 1.0
    elif 3 <= avg_sentence_length <= 40:
        length_score = 0.7
    else:
        length_score = 0.4

    # Check for repetitive content
    unique_sentences = len(set(s.strip().lower() for s in sentences if s.strip()))
    repetition_score = min(unique_sentences / len(sentences), 1.0)

    return (length_score * 0.6) + (repetition_score * 0.4)
```

#### Filtering and Ranking
```python
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
```

#### Response Format
```python
{
    "success": True,
    "filtered_content": [
        {
            "url": "https://example.com/article",
            "content": "Clean extracted text...",
            "metadata": {...},
            "quality_score": 0.85,
            "credibility_indicators": [
                "Educational institution",
                "Author identified",
                "Publication date available"
            ],
            "relevance_score": 0.92,
            "content_quality_score": 0.78,
            "credibility_score": 0.85,
            "freshness_score": 0.95
        }
    ],
    "quality_summary": {
        "total_sources": 25,
        "high_quality_sources": 18,
        "filtered_out": 7,
        "average_quality_score": 0.73,
        "quality_distribution": {
            "excellent": 5,
            "good": 13,
            "fair": 4,
            "poor": 3
        }
    },
    "assessment_metadata": {
        "quality_threshold_used": 0.7,
        "search_query": "machine learning algorithms",
        "assessment_timestamp": "2024-09-26T14:35:00Z",
        "processing_time": 1.2
    }
}
```

## Error Handling Strategies

### Network and API Errors
```python
class WebResearchError(Exception):
    """Base exception for web research tool errors."""
    pass

class SearchEngineError(WebResearchError):
    """Exception for search engine API failures."""
    pass

class ContentExtractionError(WebResearchError):
    """Exception for content extraction failures."""
    pass

async def handle_search_engine_failure(
    engine: str,
    error: Exception,
    fallback_engines: List[str]
) -> Dict[str, Any]:
    """Handle search engine failures with fallback logic."""
    logger.error(f"Search engine {engine} failed: {error}")

    if fallback_engines:
        logger.info(f"Attempting fallback to: {fallback_engines}")
        return {"fallback_attempted": True, "next_engines": fallback_engines}
    else:
        return {"fallback_attempted": False, "error": str(error)}

async def handle_extraction_failure(
    url: str,
    error: Exception,
    retry_count: int = 0
) -> Dict[str, Any]:
    """Handle content extraction failures with retry logic."""
    if retry_count < 2:  # Allow up to 2 retries
        logger.warning(f"Extraction failed for {url}, retrying ({retry_count + 1}/2): {error}")
        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
        return {"should_retry": True, "retry_count": retry_count + 1}
    else:
        logger.error(f"Extraction failed permanently for {url}: {error}")
        return {"should_retry": False, "error": str(error)}
```

### Rate Limiting and Throttling
```python
from asyncio import Semaphore
from time import time

class RateLimiter:
    """Rate limiter for API requests."""

    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.semaphore = Semaphore(max_requests)

    async def acquire(self):
        """Acquire permission to make a request."""
        await self.semaphore.acquire()
        current_time = time()

        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests
                        if current_time - req_time < self.time_window]

        # Add current request
        self.requests.append(current_time)

        # Calculate delay if needed
        if len(self.requests) >= self.max_requests:
            oldest_request = min(self.requests)
            delay = self.time_window - (current_time - oldest_request)
            if delay > 0:
                await asyncio.sleep(delay)

    def release(self):
        """Release semaphore after request completion."""
        self.semaphore.release()
```

## Integration Requirements

### Dependencies
```python
# Required Python packages for tools.py
httpx>=0.24.0          # HTTP client for API requests
newspaper3k>=0.2.8     # Content extraction
beautifulsoup4>=4.12.0 # HTML parsing
readability>=0.3.0     # Content extraction
requests-html>=0.10.0  # JavaScript rendering
scikit-learn>=1.3.0    # TF-IDF for relevance scoring
numpy>=1.24.0          # Numerical operations
tenacity>=8.2.0        # Retry mechanisms
langdetect>=1.0.9      # Language detection
```

### Environment Variables Required
```bash
# Search Engine APIs (all tools)
BRAVE_API_KEY=your-brave-search-api-key
GOOGLE_SEARCH_API_KEY=your-google-search-api-key
GOOGLE_SEARCH_ENGINE_ID=your-custom-search-engine-id
BING_SEARCH_API_KEY=your-bing-search-api-key

# Rate Limiting Configuration
DEFAULT_MAX_RESULTS=20
DEFAULT_QUALITY_THRESHOLD=0.7
REQUEST_TIMEOUT=30
RATE_LIMIT_DELAY=1.0
MAX_CONCURRENT_EXTRACTIONS=10
EXTRACTION_BATCH_SIZE=5
```

### Tool Registration Pattern
```python
def register_web_research_tools(agent, deps_type):
    """Register all web research tools with the agent."""

    # Tool 1: Multi-engine search
    @agent.tool
    async def multi_engine_search(
        ctx: RunContext[deps_type],
        query: str,
        engines: List[Literal["brave", "google", "bing"]] = ["brave"],
        max_results_per_engine: int = 20
    ) -> Dict[str, Any]:
        # Implementation here
        pass

    # Tool 2: Content extraction
    @agent.tool
    async def extract_web_content(
        ctx: RunContext[deps_type],
        urls: List[str],
        extract_metadata: bool = True,
        respect_robots: bool = True
    ) -> List[Dict[str, Any]]:
        # Implementation here
        pass

    # Tool 3: Quality assessment
    @agent.tool
    async def assess_content_quality(
        ctx: RunContext[deps_type],
        extracted_content: List[Dict[str, Any]],
        search_query: str,
        quality_threshold: float = 0.7
    ) -> Dict[str, Any]:
        # Implementation here
        pass

    logger.info(f"Registered {len(agent.tools)} web research tools")
```

## Performance Optimization

### Parallel Processing Strategy
- **Search Engines**: Query all engines simultaneously with asyncio.gather()
- **Content Extraction**: Process URLs in parallel batches (max 10 concurrent)
- **Quality Assessment**: Batch process content with vectorized operations

### Caching Strategy
- **Search Results**: Cache results for identical queries (TTL: 1 hour)
- **Extracted Content**: Cache extracted content by URL (TTL: 24 hours)
- **Quality Scores**: Cache quality assessments (TTL: 6 hours)

### Resource Management
- **Connection Pooling**: Reuse HTTP connections for efficiency
- **Memory Management**: Process large content batches in chunks
- **Timeout Handling**: Aggressive timeouts to prevent hanging requests

## Security Considerations

### API Key Management
- Store all API keys in environment variables only
- Never log API keys or include in error messages
- Validate API key format before making requests

### Web Scraping Ethics
- Always check robots.txt before scraping
- Use appropriate user agent strings
- Implement conservative rate limiting
- Respect website terms of service

### Content Validation
- Sanitize extracted content before processing
- Validate URLs before accessing
- Check content size limits to prevent memory issues

---

**Tool Specifications Complete**: 2024-09-26

**Implementation Notes**:
- These tools are designed to work together as a pipeline: search → extract → assess
- All tools include comprehensive error handling and retry mechanisms
- Performance optimizations support the 3-minute processing requirement for 50+ sources
- Quality assessment uses configurable thresholds for flexible filtering
- Tools respect web scraping ethics and API rate limits