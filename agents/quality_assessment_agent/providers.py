"""Model providers for Quality Assessment Agent."""

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from .settings import settings


def get_openai_model() -> OpenAIModel:
    """Get configured OpenAI model with proper settings."""
    provider = OpenAIProvider(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key
    )
    return OpenAIModel(settings.openai_model, provider=provider)


def get_assessment_model() -> OpenAIModel:
    """Get the primary model for quality assessment tasks."""
    return get_openai_model()