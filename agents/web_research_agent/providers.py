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