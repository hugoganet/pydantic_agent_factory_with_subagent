"""
Configuration management for Data Synthesis Agent.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration - OpenAI GPT-4o for synthesis capabilities
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_api_key: str = Field(..., description="OpenAI API key")
    llm_model: str = Field(default="gpt-4o", description="OpenAI model for synthesis")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL"
    )

    # Agent Configuration
    app_env: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")

    # Performance Configuration
    max_findings_per_synthesis: int = Field(default=50, description="Max research findings per synthesis")
    synthesis_timeout_seconds: int = Field(default=120, description="Synthesis timeout (2 minutes)")
    min_confidence_threshold: float = Field(default=0.7, description="Minimum confidence for synthesis")

    # Workflow Integration
    agent_id: str = Field(default="data_synthesis_agent", description="Agent identifier")
    workflow_coordinator_url: Optional[str] = Field(None, description="Research orchestrator endpoint")

    @field_validator("llm_api_key")
    @classmethod
    def validate_llm_key(cls, v):
        """Ensure OpenAI API key is not empty."""
        if not v or v.strip() == "":
            raise ValueError("OpenAI API key cannot be empty")
        return v

    @field_validator("min_confidence_threshold")
    @classmethod
    def validate_confidence(cls, v):
        """Validate confidence threshold range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        return v


def load_settings() -> Settings:
    """Load settings with proper error handling."""
    try:
        return Settings()
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "llm_api_key" in str(e).lower():
            error_msg += "\nMake sure to set LLM_API_KEY in your .env file"
        raise ValueError(error_msg) from e


# Global settings instance
settings = load_settings()