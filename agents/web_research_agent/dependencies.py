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