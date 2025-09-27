"""Settings and configuration for the Workflow Coordinator Agent."""

import os
from typing import Optional
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class CoordinatorSettings(BaseSettings):
    """Workflow Coordinator settings with environment variable support."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration
    llm_provider: str = Field(default="openai", description="LLM provider")
    openai_api_key: str = Field(..., description="OpenAI API key")
    llm_model: str = Field(default="gpt-4", description="Model name")
    llm_base_url: str = Field(default="https://api.openai.com/v1")

    # System Configuration
    max_parallel_agents: int = Field(default=5, ge=1, le=10)
    health_check_interval: int = Field(default=10, ge=5, le=60)
    workflow_timeout: int = Field(default=600, ge=60, le=3600)

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379")
    redis_db: int = Field(default=0, ge=0, le=15)

    # Monitoring Configuration
    system_metrics_interval: int = Field(default=30, ge=10, le=300)
    alert_threshold_response_time: int = Field(default=5000, ge=1000)
    alert_threshold_error_rate: int = Field(default=10, ge=1, le=50)

    # Logging
    log_level: str = Field(default="INFO")


def load_settings() -> CoordinatorSettings:
    """Load settings with proper error handling and environment loading."""
    # Load environment variables from .env file
    load_dotenv()

    try:
        return CoordinatorSettings()
    except Exception as e:
        error_msg = f"Failed to load coordinator settings: {e}"
        if "openai_api_key" in str(e).lower():
            error_msg += "\nMake sure to set OPENAI_API_KEY in your .env file"
        raise ValueError(error_msg) from e