"""Configuration settings for Quality Assessment Agent."""

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from dotenv import load_dotenv
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration
    openai_api_key: str = Field(..., description="OpenAI API key for GPT-4o-mini")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model name")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL"
    )

    # Fact-checking API (optional)
    fact_check_api_key: Optional[str] = Field(
        default=None,
        description="FactCheck.org API key (optional)"
    )

    # Quality Assessment Configuration
    credibility_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum credibility threshold for flagging"
    )
    bias_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Bias threshold for flagging"
    )
    processing_timeout: int = Field(
        default=30,
        description="Maximum processing time per source (seconds)"
    )
    max_concurrent_assessments: int = Field(
        default=10,
        description="Maximum concurrent source assessments"
    )

    # Agent Configuration
    agent_id: str = Field(
        default="quality_assessment_agent",
        description="Unique agent identifier"
    )
    agent_version: str = Field(
        default="1.0.0",
        description="Agent version"
    )

    # Scoring Weights for Credibility Assessment
    domain_authority_weight: float = Field(default=0.30, description="Domain authority weight")
    content_quality_weight: float = Field(default=0.25, description="Content quality weight")
    author_credentials_weight: float = Field(default=0.20, description="Author credentials weight")
    source_type_weight: float = Field(default=0.15, description="Source type weight")
    freshness_weight: float = Field(default=0.10, description="Freshness weight")


def load_settings() -> Settings:
    """Load settings with proper error handling and environment loading."""
    # Load environment variables from .env file
    load_dotenv()

    try:
        return Settings()
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "openai_api_key" in str(e).lower():
            error_msg += "\nMake sure to set OPENAI_API_KEY in your .env file"
        raise ValueError(error_msg) from e


# Global settings instance
settings = load_settings()