"""
LLM provider configuration for Query Strategy Agent.
Focused on OpenAI GPT-4o for strategic reasoning capabilities.
"""

from typing import Optional
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from .settings import settings

def get_llm_model(model_choice: Optional[str] = None) -> OpenAIModel:
    """
    Get OpenAI GPT-4o model for strategic analysis.

    Args:
        model_choice: Optional override for model choice

    Returns:
        Configured OpenAI model instance
    """
    model_name = model_choice or settings.llm_model

    provider_instance = OpenAIProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key
    )

    return OpenAIModel(model_name, provider=provider_instance)