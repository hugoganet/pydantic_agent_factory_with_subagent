"""
Configuration management for Citation Management Agent.
Uses python-dotenv and pydantic-settings for environment handling.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict
from typing import Optional
from dotenv import load_dotenv


class Settings(BaseSettings):
    """Citation Management Agent settings."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration
    llm_provider: str = Field(default="openai")
    llm_api_key: str = Field(..., description="OpenAI API key")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_base_url: str = Field(default="https://api.openai.com/v1")

    # Citation Processing
    citation_batch_size: int = Field(default=50)
    duplicate_threshold: float = Field(default=0.85)
    validate_citations: bool = Field(default=True)

    # Application Settings
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)
    max_retries: int = Field(default=3)
    timeout_seconds: int = Field(default=30)

    @field_validator("llm_api_key")
    @classmethod
    def validate_openai_key(cls, v):
        if not v:
            raise ValueError("OpenAI API key is required")
        # Allow test keys for testing environment
        if v.startswith(("test_", "mock_")):
            return v
        if not v.startswith(("sk-", "org-")):
            raise ValueError("Invalid OpenAI API key format")
        return v

    @field_validator("duplicate_threshold")
    @classmethod
    def validate_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Duplicate threshold must be between 0.0 and 1.0")
        return v


def load_settings() -> Settings:
    """Load settings with proper error handling and environment loading."""
    # Load environment variables from .env file
    load_dotenv()

    try:
        return Settings()
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "llm_api_key" in str(e).lower():
            error_msg += "\nMake sure to set LLM_API_KEY in your .env file"
        raise ValueError(error_msg) from e