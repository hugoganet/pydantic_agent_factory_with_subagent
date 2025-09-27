"""
Model providers configuration for Tool Integration Agent.
Handles LLM model initialization and provider setup.
"""

from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from .settings import ToolIntegrationSettings, load_settings
import logging

logger = logging.getLogger(__name__)


def get_llm_model(settings: ToolIntegrationSettings = None):
    """
    Get configured LLM model with proper environment loading.

    Args:
        settings: Optional settings instance, loads from environment if not provided

    Returns:
        OpenAIModel: Configured model instance

    Raises:
        ValueError: If model configuration is invalid
    """
    if settings is None:
        settings = load_settings()

    try:
        # Create OpenAI provider with configuration
        provider = OpenAIProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key
        )

        # Create and return the model
        model = OpenAIModel(settings.llm_model, provider=provider)

        logger.info(f"LLM model initialized: {settings.llm_model} via {settings.llm_provider}")
        return model

    except Exception as e:
        error_msg = f"Failed to initialize LLM model: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


# Default model instance for the agent
default_model = get_llm_model()