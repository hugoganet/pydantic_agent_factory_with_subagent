"""
Model provider configuration for Citation Management Agent.
Single provider setup with OpenAI GPT-4o-mini.
"""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from .settings import Settings


def get_citation_model(settings: Settings) -> OpenAIChatModel:
    """
    Get configured OpenAI model for citation processing.
    Optimized for structured output and cost efficiency.
    """
    provider = OpenAIProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key
    )

    return OpenAIChatModel(
        model_name=settings.llm_model,
        provider=provider
    )


def get_llm_model():
    """Get configured LLM model with proper environment loading."""
    from .settings import load_settings
    settings = load_settings()
    return get_citation_model(settings)