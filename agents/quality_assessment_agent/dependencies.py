"""Dependencies for Quality Assessment Agent."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import asyncio
import aiohttp
from datetime import datetime
from .settings import settings


@dataclass
class QualityAssessmentDependencies:
    """Dependencies for quality assessment operations."""

    # Configuration
    agent_id: str = settings.agent_id
    processing_timeout: int = settings.processing_timeout

    # External service configurations
    fact_check_api_key: Optional[str] = settings.fact_check_api_key

    # Scoring weights
    domain_authority_weight: float = settings.domain_authority_weight
    content_quality_weight: float = settings.content_quality_weight
    author_credentials_weight: float = settings.author_credentials_weight
    source_type_weight: float = settings.source_type_weight
    freshness_weight: float = settings.freshness_weight

    # Quality thresholds
    credibility_threshold: float = settings.credibility_threshold
    bias_threshold: float = settings.bias_threshold

    # Session for HTTP requests
    http_session: Optional[aiohttp.ClientSession] = None

    def __post_init__(self):
        """Initialize HTTP session if not provided."""
        if self.http_session is None:
            self.http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.processing_timeout)
            )

    async def close(self):
        """Clean up resources."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()


def get_dependencies() -> QualityAssessmentDependencies:
    """Create and return quality assessment dependencies."""
    return QualityAssessmentDependencies()