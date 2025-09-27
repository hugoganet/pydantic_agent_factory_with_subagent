"""
Research Orchestrator Agent - Settings and Configuration

Environment-based configuration for the master coordinator agent in the
Research Engineering Workflow system.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Research Orchestrator configuration with environment variable support."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration (Required - OpenAI GPT-4o for complex reasoning)
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_api_key: str = Field(..., description="OpenAI API key for GPT-4o")
    llm_model: str = Field(default="gpt-4o", description="Model for complex coordination")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API endpoint"
    )

    # Inter-Agent Communication (Required - Redis for message queuing)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection for inter-agent messaging"
    )
    redis_password: Optional[str] = Field(None, description="Redis password if required")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_pool_size: int = Field(default=10, description="Redis connection pool size")

    # Workflow Orchestration Configuration
    max_parallel_agents: int = Field(default=5, description="Max simultaneous agent execution")
    research_timeout_minutes: int = Field(default=10, description="Total research timeout")
    task_timeout_seconds: int = Field(default=180, description="Individual task timeout")
    retry_max_attempts: int = Field(default=3, description="Max retry attempts per task")
    retry_backoff_seconds: int = Field(default=2, description="Exponential backoff base")

    # Quality Thresholds for Orchestration
    min_source_quality_score: float = Field(
        default=0.8,
        description="Minimum source credibility threshold"
    )
    min_confidence_rating: float = Field(
        default=0.7,
        description="Minimum confidence score for acceptance"
    )
    max_quality_retries: int = Field(
        default=2,
        description="Max retries for quality improvements"
    )

    # Agent Endpoint Configuration (for coordinated agents)
    agent_endpoints: Dict[str, str] = Field(
        default_factory=lambda: {
            "web_research": "http://localhost:8002",
            "tool_integration": "http://localhost:8003",
            "quality_assessment": "http://localhost:8004",
            "citation_management": "http://localhost:8005",
            "query_strategy": "http://localhost:8006",
            "data_synthesis": "http://localhost:8007",
            "workflow_coordinator": "http://localhost:8008"
        },
        description="HTTP endpoints for coordinated agents"
    )

    # Performance Monitoring
    enable_performance_tracking: bool = Field(
        default=True,
        description="Enable detailed performance metrics"
    )
    metrics_collection_interval: int = Field(
        default=30,
        description="Metrics collection interval in seconds"
    )
    health_check_interval: int = Field(
        default=60,
        description="Agent health check interval in seconds"
    )

    # Application Configuration
    app_env: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")


def load_settings() -> Settings:
    """Load settings with proper error handling and environment loading."""
    try:
        return Settings()
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "llm_api_key" in str(e).lower():
            error_msg += "\nMake sure to set LLM_API_KEY in your .env file"
        raise ValueError(error_msg) from e


# Global settings instance
settings = load_settings()