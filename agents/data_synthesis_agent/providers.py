"""
OpenAI GPT-4o provider configuration for synthesis capabilities.
"""

from typing import Optional
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from .settings import settings


def get_synthesis_model(model_choice: Optional[str] = None) -> OpenAIModel:
    """
    Get OpenAI GPT-4o model optimized for data synthesis.

    Args:
        model_choice: Optional override for model choice

    Returns:
        Configured OpenAI model for synthesis
    """
    model_name = model_choice or settings.llm_model

    provider = OpenAIProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key
    )

    return OpenAIModel(
        model_name,
        provider=provider,
        # Optimized for synthesis tasks
        temperature=0.3,  # Lower temperature for consistent synthesis
        max_tokens=4096,  # Sufficient for comprehensive reports
        timeout=settings.synthesis_timeout_seconds
    )