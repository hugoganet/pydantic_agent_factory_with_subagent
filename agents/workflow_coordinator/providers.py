"""LLM provider configuration for the Workflow Coordinator Agent."""

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from .settings import load_settings


def get_llm_model():
    """Get configured LLM model for coordination decisions."""
    settings = load_settings()

    if settings.llm_provider.lower() == "openai":
        provider = OpenAIProvider(
            base_url=settings.llm_base_url,
            api_key=settings.openai_api_key
        )
        return OpenAIModel(settings.llm_model, provider=provider)
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")