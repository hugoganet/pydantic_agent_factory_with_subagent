"""
Research Orchestrator Agent - Model Providers

OpenAI GPT-4o model configuration optimized for complex coordination tasks
and multi-agent workflow orchestration.
"""

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from typing import Optional
import httpx
import logging

from .settings import settings

logger = logging.getLogger(__name__)


def get_orchestrator_model() -> OpenAIModel:
    """
    Get OpenAI GPT-4o model configured for complex orchestration tasks.

    Returns:
        Configured OpenAI model optimized for workflow coordination
    """
    provider = OpenAIProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=httpx.Timeout(300.0),  # Extended timeout for complex operations
        max_retries=3
    )

    model = OpenAIModel(
        settings.llm_model,
        provider=provider,
        # Optimized for structured output and coordination tasks
        temperature=0.2,  # Low temperature for consistent coordination
        max_tokens=4000   # Sufficient for detailed execution plans
    )

    logger.info(f"Initialized {settings.llm_model} for orchestration tasks")
    return model


def get_fallback_model() -> Optional[OpenAIModel]:
    """
    Fallback to GPT-4o-mini for less critical operations.

    Returns:
        Fallback model or None if not configured
    """
    if hasattr(settings, 'fallback_api_key') and settings.fallback_api_key:
        provider = OpenAIProvider(
            api_key=settings.fallback_api_key,
            timeout=httpx.Timeout(120.0)
        )
        model = OpenAIModel("gpt-4o-mini", provider=provider)
        logger.info("Initialized GPT-4o-mini as fallback model")
        return model

    logger.info("No fallback model configured")
    return None