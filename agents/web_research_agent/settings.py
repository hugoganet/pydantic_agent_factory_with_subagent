"""
Configuration management for Web Research Agent.
Uses pydantic-settings with python-dotenv for environment variable handling.
"""

import os
from typing import Optional, List, Dict, Any
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

    # LLM Configuration
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_api_key: str = Field(..., description="API key for LLM provider")
    llm_model: str = Field(default="gpt-4o-mini", description="Model name")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL for LLM API"
    )

    # Search Engine API Keys (at least one required)
    brave_api_key: Optional[str] = Field(None, description="Brave Search API key")
    google_search_api_key: Optional[str] = Field(None, description="Google Search API key")
    google_search_engine_id: Optional[str] = Field(None, description="Google Custom Search Engine ID")
    bing_search_api_key: Optional[str] = Field(None, description="Bing Search API key")

    # Web Research Configuration
    default_max_results: int = Field(default=20, ge=1, le=100, description="Default max results per search")
    default_quality_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Default quality threshold"
    )
    request_timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    rate_limit_delay: float = Field(default=1.0, ge=0.1, le=10.0, description="Rate limit delay between requests")
    max_parallel_requests: int = Field(default=10, ge=1, le=50, description="Maximum parallel requests")

    # Content Processing Configuration
    max_content_length: int = Field(default=50000, description="Maximum content length to extract")
    content_cache_ttl: int = Field(default=3600, description="Content cache TTL in seconds")
    user_agent: str = Field(
        default="WebResearchAgent/1.0 (+https://pydantic.ai)",
        description="User agent for web requests"
    )
    respect_robots_txt: bool = Field(default=True, description="Respect robots.txt files")

    # Application Configuration
    app_env: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")
    max_retries: int = Field(default=3, description="Max retry attempts")

    @field_validator("llm_api_key")
    @classmethod
    def validate_llm_key(cls, v):
        """Ensure LLM API key is not empty."""
        if not v or v.strip() == "":
            raise ValueError("LLM API key cannot be empty")
        return v

    def get_available_search_engines(self) -> List[str]:
        """Get list of available search engines based on API keys."""
        engines = []
        if self.brave_api_key:
            engines.append("brave")
        if self.google_search_api_key and self.google_search_engine_id:
            engines.append("google")
        if self.bing_search_api_key:
            engines.append("bing")

        if not engines:
            raise ValueError("At least one search engine API key must be provided")

        return engines

    @field_validator("app_env")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"app_env must be one of {valid_envs}")
        return v

def load_settings() -> Settings:
    """Load settings with proper error handling."""
    try:
        settings = Settings()
        # Validate that at least one search engine is available
        settings.get_available_search_engines()
        return settings
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "llm_api_key" in str(e).lower():
            error_msg += "\nMake sure to set LLM_API_KEY in your .env file"
        elif "search engine" in str(e).lower():
            error_msg += "\nMake sure to set at least one search engine API key"
        raise ValueError(error_msg) from e

# Global settings instance
settings = load_settings()