# Web Research Agent - Dependency Configuration

## Overview
Comprehensive dependency configuration for the Web Research Agent that handles multi-engine web search, content extraction, and quality-based filtering. Designed for minimal complexity with essential functionality only.

## Core Configuration Philosophy
- **Essential Variables Only**: Focus on API keys and basic operational settings
- **Single LLM Provider**: OpenAI GPT-4o-mini for cost-effective content processing
- **Simple Dependency Injection**: Basic dataclass pattern for agent dependencies
- **Minimal Package Requirements**: Only necessary libraries for MVP functionality

## Environment Configuration

### Required Environment Variables

```bash
# LLM Configuration (REQUIRED)
LLM_PROVIDER=openai
LLM_API_KEY=your-openai-api-key
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1

# Search Engine APIs (REQUIRED - at least one)
BRAVE_API_KEY=your-brave-search-api-key
GOOGLE_SEARCH_API_KEY=your-google-search-api-key
GOOGLE_SEARCH_ENGINE_ID=your-custom-search-engine-id
BING_SEARCH_API_KEY=your-bing-search-api-key

# Web Research Configuration (OPTIONAL - defaults provided)
DEFAULT_MAX_RESULTS=20
DEFAULT_QUALITY_THRESHOLD=0.7
REQUEST_TIMEOUT=30
RATE_LIMIT_DELAY=1.0
MAX_PARALLEL_REQUESTS=10

# Application Settings (OPTIONAL)
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false
MAX_RETRIES=3
```

### Optional Environment Variables

```bash
# Advanced Configuration (for future enhancements)
CONTENT_CACHE_TTL=3600
MAX_CONTENT_LENGTH=50000
USER_AGENT=WebResearchAgent/1.0
RESPECT_ROBOTS_TXT=true
HEADLESS_BROWSER_ENABLED=false
```

## Python Dependencies

### Core Requirements (requirements.txt)

```txt
# Core Pydantic AI Framework
pydantic-ai>=0.1.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Environment Management
python-dotenv>=1.0.0

# LLM Provider
openai>=1.0.0

# HTTP and Web Scraping
aiohttp>=3.9.0
httpx>=0.25.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0

# Search Engine Integrations
google-api-python-client>=2.100.0
azure-cognitiveservices-search-websearch>=2.0.0

# Content Processing
html2text>=2020.1.16
newspaper3k>=0.2.8
trafilatura>=1.6.0

# Async and Utilities
asyncio-throttle>=1.0.2
aiofiles>=23.0.0
tenacity>=8.2.0

# Data Validation and Processing
validators>=0.22.0
dateutil>=2.8.2
chardet>=5.2.0

# Development and Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-aiohttp>=1.0.4
black>=23.0.0
ruff>=0.1.0

# Optional: For advanced content extraction
selenium>=4.15.0  # Only if headless browsing needed
```

## Configuration File Specifications

### settings.py - Environment Configuration

```python
"""
Configuration management for Web Research Agent.
Uses pydantic-settings with python-dotenv for environment variable handling.
"""

import os
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_api_key: str = Field(..., description="API key for LLM provider")
    llm_model: str = Field(default="gpt-4o-mini", description="Model name")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL for LLM API"
    )

    # Search Engine API Keys (at least one required)
    brave_api_key: Optional[str] = Field(None, description="Brave Search API key")
    google_search_api_key: Optional[str] = Field(None, description="Google Search API key")
    google_search_engine_id: Optional[str] = Field(None, description="Google Custom Search Engine ID")
    bing_search_api_key: Optional[str] = Field(None, description="Bing Search API key")

    # Web Research Configuration
    default_max_results: int = Field(default=20, ge=1, le=100, description="Default max results per search")
    default_quality_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Default quality threshold"
    )
    request_timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    rate_limit_delay: float = Field(default=1.0, ge=0.1, le=10.0, description="Rate limit delay between requests")
    max_parallel_requests: int = Field(default=10, ge=1, le=50, description="Maximum parallel requests")

    # Content Processing Configuration
    max_content_length: int = Field(default=50000, description="Maximum content length to extract")
    content_cache_ttl: int = Field(default=3600, description="Content cache TTL in seconds")
    user_agent: str = Field(
        default="WebResearchAgent/1.0 (+https://pydantic.ai)",
        description="User agent for web requests"
    )
    respect_robots_txt: bool = Field(default=True, description="Respect robots.txt files")

    # Application Configuration
    app_env: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")
    max_retries: int = Field(default=3, description="Max retry attempts")

    @field_validator("llm_api_key")
    @classmethod
    def validate_llm_key(cls, v):
        """Ensure LLM API key is not empty."""
        if not v or v.strip() == "":
            raise ValueError("LLM API key cannot be empty")
        return v

    def get_available_search_engines(self) -> List[str]:
        """Get list of available search engines based on API keys."""
        engines = []
        if self.brave_api_key:
            engines.append("brave")
        if self.google_search_api_key and self.google_search_engine_id:
            engines.append("google")
        if self.bing_search_api_key:
            engines.append("bing")

        if not engines:
            raise ValueError("At least one search engine API key must be provided")

        return engines

    @field_validator("app_env")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"app_env must be one of {valid_envs}")
        return v

def load_settings() -> Settings:
    """Load settings with proper error handling."""
    try:
        settings = Settings()
        # Validate that at least one search engine is available
        settings.get_available_search_engines()
        return settings
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "llm_api_key" in str(e).lower():
            error_msg += "\nMake sure to set LLM_API_KEY in your .env file"
        elif "search engine" in str(e).lower():
            error_msg += "\nMake sure to set at least one search engine API key"
        raise ValueError(error_msg) from e

# Global settings instance
settings = load_settings()
```

### providers.py - Model Provider Configuration

```python
"""
LLM provider configuration for Web Research Agent.
Supports OpenAI GPT-4o-mini for cost-effective content processing.
"""

from typing import Optional
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from .settings import settings

def get_llm_model(model_choice: Optional[str] = None) -> OpenAIModel:
    """
    Get configured LLM model for web research tasks.

    Args:
        model_choice: Optional override for model choice

    Returns:
        Configured OpenAI model instance
    """
    model_name = model_choice or settings.llm_model

    provider = OpenAIProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key
    )

    return OpenAIModel(model_name, provider=provider)

def get_content_processing_model() -> OpenAIModel:
    """
    Get model optimized for content processing tasks.
    Uses GPT-4o-mini for cost-effective text processing.
    """
    provider = OpenAIProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key
    )

    return OpenAIModel("gpt-4o-mini", provider=provider)
```

### dependencies.py - Agent Dependencies

```python
"""
Dependencies for Web Research Agent.
Manages HTTP sessions, API clients, and configuration.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import logging
import aiohttp
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)

@dataclass
class WebResearchDependencies:
    """
    Dependencies injected into Web Research Agent runtime context.

    Contains all external services, API keys, and configuration
    needed for multi-engine web search and content extraction.
    """

    # Search Engine API Keys
    brave_api_key: Optional[str] = None
    google_search_api_key: Optional[str] = None
    google_search_engine_id: Optional[str] = None
    bing_search_api_key: Optional[str] = None

    # Configuration
    max_results: int = 20
    quality_threshold: float = 0.7
    request_timeout: int = 30
    rate_limit_delay: float = 1.0
    max_parallel_requests: int = 10
    max_content_length: int = 50000
    user_agent: str = "WebResearchAgent/1.0"
    respect_robots_txt: bool = True

    # Runtime Context
    session_id: Optional[str] = None
    workflow_context: Optional[Dict[str, Any]] = None

    # HTTP Session Management (initialized lazily)
    _http_session: Optional[aiohttp.ClientSession] = field(default=None, init=False, repr=False)
    _search_engines_available: Optional[List[str]] = field(default=None, init=False, repr=False)
    _robots_cache: Dict[str, RobotFileParser] = field(default_factory=dict, init=False, repr=False)

    @property
    def http_session(self) -> aiohttp.ClientSession:
        """Lazy initialization of HTTP session with proper configuration."""
        if self._http_session is None or self._http_session.closed:
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            connector = aiohttp.TCPConnector(
                limit=self.max_parallel_requests,
                limit_per_host=5,
                enable_cleanup_closed=True
            )
            headers = {"User-Agent": self.user_agent}

            self._http_session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=headers
            )
            logger.info("HTTP session initialized")

        return self._http_session

    @property
    def available_search_engines(self) -> List[str]:
        """Get list of available search engines based on API keys."""
        if self._search_engines_available is None:
            engines = []
            if self.brave_api_key:
                engines.append("brave")
            if self.google_search_api_key and self.google_search_engine_id:
                engines.append("google")
            if self.bing_search_api_key:
                engines.append("bing")

            if not engines:
                raise ValueError("No search engine API keys available")

            self._search_engines_available = engines
            logger.info(f"Available search engines: {engines}")

        return self._search_engines_available

    def can_scrape_url(self, url: str) -> bool:
        """
        Check if URL can be scraped based on robots.txt.

        Args:
            url: URL to check

        Returns:
            True if URL can be scraped, False otherwise
        """
        if not self.respect_robots_txt:
            return True

        try:
            from urllib.parse import urljoin, urlparse

            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

            if robots_url not in self._robots_cache:
                rp = RobotFileParser()
                rp.set_url(robots_url)
                try:
                    rp.read()
                    self._robots_cache[robots_url] = rp
                except Exception as e:
                    logger.warning(f"Failed to read robots.txt for {robots_url}: {e}")
                    # If we can't read robots.txt, assume scraping is allowed
                    return True

            return self._robots_cache[robots_url].can_fetch(self.user_agent, url)

        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True  # Allow scraping if check fails

    async def cleanup(self):
        """Cleanup resources when done."""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
            logger.info("HTTP session closed")

    @classmethod
    def from_settings(cls, settings, **kwargs):
        """
        Create dependencies from settings with overrides.

        Args:
            settings: Settings instance
            **kwargs: Override values

        Returns:
            Configured WebResearchDependencies instance
        """
        return cls(
            brave_api_key=kwargs.get('brave_api_key', settings.brave_api_key),
            google_search_api_key=kwargs.get('google_search_api_key', settings.google_search_api_key),
            google_search_engine_id=kwargs.get('google_search_engine_id', settings.google_search_engine_id),
            bing_search_api_key=kwargs.get('bing_search_api_key', settings.bing_search_api_key),
            max_results=kwargs.get('max_results', settings.default_max_results),
            quality_threshold=kwargs.get('quality_threshold', settings.default_quality_threshold),
            request_timeout=kwargs.get('request_timeout', settings.request_timeout),
            rate_limit_delay=kwargs.get('rate_limit_delay', settings.rate_limit_delay),
            max_parallel_requests=kwargs.get('max_parallel_requests', settings.max_parallel_requests),
            max_content_length=kwargs.get('max_content_length', settings.max_content_length),
            user_agent=kwargs.get('user_agent', settings.user_agent),
            respect_robots_txt=kwargs.get('respect_robots_txt', settings.respect_robots_txt),
            **{k: v for k, v in kwargs.items()
               if k not in [
                   'brave_api_key', 'google_search_api_key', 'google_search_engine_id',
                   'bing_search_api_key', 'max_results', 'quality_threshold',
                   'request_timeout', 'rate_limit_delay', 'max_parallel_requests',
                   'max_content_length', 'user_agent', 'respect_robots_txt'
               ]}
        )
```

### agent.py - Agent Initialization

```python
"""
Web Research Agent - Multi-engine web search with content extraction.
"""

import logging
from typing import Optional
from pydantic_ai import Agent

from .providers import get_llm_model
from .dependencies import WebResearchDependencies
from .settings import settings

logger = logging.getLogger(__name__)

# System prompt will be provided by prompt-engineer subagent
SYSTEM_PROMPT = """
You are a specialized web research agent that executes multi-engine web searches,
extracts clean content from web sources, and filters results based on quality criteria.

Your core capabilities:
1. Execute searches across multiple search engines (Brave, Google, Bing)
2. Extract and clean meaningful text content from web pages
3. Assess content quality and filter results based on relevance thresholds

You work as part of a research engineering workflow, providing high-quality
web sources for further analysis and synthesis.
"""

# Initialize the agent
agent = Agent(
    get_llm_model(),
    deps_type=WebResearchDependencies,
    system_prompt=SYSTEM_PROMPT,
    retries=settings.max_retries
)

logger.info("Web Research Agent initialized")

# Tools will be registered by tool-integrator subagent
# from .tools import register_tools
# register_tools(agent, WebResearchDependencies)

# Convenience functions for agent usage
async def run_web_search(
    query: str,
    search_engines: Optional[list] = None,
    max_results: int = 20,
    quality_threshold: float = 0.7,
    session_id: Optional[str] = None,
    **dependency_overrides
) -> str:
    """
    Execute web research with automatic dependency injection.

    Args:
        query: Search query
        search_engines: List of search engines to use
        max_results: Maximum results per engine
        quality_threshold: Minimum quality score
        session_id: Optional session identifier
        **dependency_overrides: Override default dependencies

    Returns:
        Web search results as formatted string
    """
    deps = WebResearchDependencies.from_settings(
        settings,
        session_id=session_id,
        max_results=max_results,
        quality_threshold=quality_threshold,
        **dependency_overrides
    )

    try:
        # Format search request
        search_request = f"""
        Search Query: {query}
        Search Engines: {search_engines or deps.available_search_engines}
        Max Results: {max_results}
        Quality Threshold: {quality_threshold}
        """

        result = await agent.run(search_request, deps=deps)
        return result.data
    finally:
        await deps.cleanup()

def create_agent_with_deps(**dependency_overrides) -> tuple[Agent, WebResearchDependencies]:
    """
    Create agent instance with custom dependencies.

    Args:
        **dependency_overrides: Custom dependency values

    Returns:
        Tuple of (agent, dependencies)
    """
    deps = WebResearchDependencies.from_settings(settings, **dependency_overrides)
    return agent, deps
```

## Environment File Template

### .env.example

```bash
# ========================================
# Web Research Agent Configuration
# ========================================

# LLM Configuration (REQUIRED)
LLM_PROVIDER=openai
LLM_API_KEY=your-openai-api-key-here
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1

# Search Engine APIs (At least one REQUIRED)
# Brave Search (Recommended - generous rate limits)
BRAVE_API_KEY=your-brave-search-api-key

# Google Custom Search (Optional but recommended)
GOOGLE_SEARCH_API_KEY=your-google-search-api-key
GOOGLE_SEARCH_ENGINE_ID=your-custom-search-engine-id

# Bing Search (Optional)
BING_SEARCH_API_KEY=your-bing-search-api-key

# Web Research Configuration (OPTIONAL - defaults provided)
DEFAULT_MAX_RESULTS=20
DEFAULT_QUALITY_THRESHOLD=0.7
REQUEST_TIMEOUT=30
RATE_LIMIT_DELAY=1.0
MAX_PARALLEL_REQUESTS=10

# Content Processing Settings (OPTIONAL)
MAX_CONTENT_LENGTH=50000
CONTENT_CACHE_TTL=3600
USER_AGENT=WebResearchAgent/1.0
RESPECT_ROBOTS_TXT=true

# Application Settings (OPTIONAL)
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false
MAX_RETRIES=3

# Advanced Settings (for future features)
HEADLESS_BROWSER_ENABLED=false
CONTENT_SUMMARIZATION_ENABLED=false
```

## Security Considerations

### API Key Management
- All API keys stored in environment variables only
- Never log or expose API keys in application code
- Use different API keys for development/staging/production
- Implement key rotation support for production deployments
- Consider using cloud secret management (AWS Secrets Manager, etc.)

### Web Scraping Security
- Respect robots.txt files by default (configurable)
- Use appropriate rate limiting to avoid overwhelming servers
- Implement proper error handling for blocked or restricted content
- Use realistic User-Agent strings
- Consider IP rotation for large-scale scraping (production)

### Input Validation
- Validate all URLs before attempting to scrape
- Sanitize extracted content to prevent injection attacks
- Limit content length to prevent memory exhaustion
- Validate search queries to prevent API abuse

## Testing Configuration

### Test Dependencies (conftest.py)

```python
import pytest
from unittest.mock import Mock, AsyncMock
from pydantic_ai.models.test import TestModel

@pytest.fixture
def test_settings():
    """Mock settings for testing."""
    return Mock(
        llm_provider="openai",
        llm_api_key="test-key",
        llm_model="gpt-4o-mini",
        brave_api_key="test-brave-key",
        default_max_results=10,
        default_quality_threshold=0.7,
        request_timeout=30,
        debug=True
    )

@pytest.fixture
def test_dependencies():
    """Test dependencies with mock HTTP session."""
    from dependencies import WebResearchDependencies

    deps = WebResearchDependencies(
        brave_api_key="test-brave-key",
        google_search_api_key="test-google-key",
        google_search_engine_id="test-engine-id",
        max_results=10,
        quality_threshold=0.7,
        debug=True
    )

    # Mock HTTP session
    deps._http_session = AsyncMock()
    return deps

@pytest.fixture
def test_agent():
    """Test agent with TestModel."""
    from pydantic_ai import Agent
    from dependencies import WebResearchDependencies

    return Agent(
        TestModel(),
        deps_type=WebResearchDependencies,
        system_prompt="Test web research agent"
    )
```

## Performance Optimizations

### HTTP Connection Management
- Use connection pooling with aiohttp.ClientSession
- Configure appropriate connection limits (10 parallel max)
- Implement connection keep-alive for efficiency
- Use connection timeouts to prevent hanging requests

### Async Processing
- Process multiple search engines in parallel
- Batch content extraction requests
- Use async/await throughout for non-blocking I/O
- Implement proper error handling for concurrent operations

### Caching Strategy
- Cache robots.txt files to avoid repeated requests
- Consider caching extracted content (with TTL)
- Cache search results for repeated queries (optional)
- Use in-memory caching for session-scoped data

## Quality Assurance Checklist

Before deployment, verify:
- [ ] All required API keys validated on startup
- [ ] HTTP sessions properly managed and closed
- [ ] Rate limiting implemented for all APIs
- [ ] Error handling for network failures
- [ ] Content extraction works for major websites
- [ ] Quality filtering produces relevant results
- [ ] Robots.txt compliance working correctly
- [ ] Memory usage stays within reasonable bounds
- [ ] Parallel processing doesn't overwhelm APIs
- [ ] Security measures in place for web scraping

## Integration Notes

### Workflow Integration
- Receives SearchRequest messages from workflow orchestrator
- Sends WebSearchResults to Quality Assessment Agent
- Maintains session context for workflow tracking
- Supports parallel execution with other research agents

### Error Reporting
- Structured error messages for API failures
- Detailed logging for debugging content extraction issues
- Graceful degradation when search engines are unavailable
- Performance metrics for workflow optimization

### Monitoring Points
- API response times and success rates
- Content extraction success rates
- Quality score distributions
- Rate limiting events and delays
- Memory and CPU usage during parallel processing

This dependency configuration provides a solid foundation for the Web Research Agent while maintaining simplicity and focusing on essential functionality for the MVP implementation.