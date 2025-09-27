"""
Settings and configuration management for Tool Integration Agent.
Handles environment variables, validation, and secure credential management.
"""

from pydantic import Field, ConfigDict, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ToolIntegrationSettings(BaseSettings):
    """
    Comprehensive settings for Tool Integration Agent with environment variable support.
    Handles Google APIs, database connections, and security configurations.
    """

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_api_key: str = Field(..., description="API key for the LLM provider")
    llm_model: str = Field(default="gpt-4", description="Model name to use")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL for the LLM API"
    )

    # Google Services Authentication
    google_application_credentials: str = Field(
        ...,
        description="Path to Google service account credentials JSON file"
    )
    google_oauth_client_id: str = Field(
        ...,
        description="Google OAuth 2.0 client ID"
    )
    google_oauth_client_secret: str = Field(
        ...,
        description="Google OAuth 2.0 client secret"
    )
    google_oauth_redirect_uri: str = Field(
        default="http://localhost:8080/oauth2callback",
        description="OAuth 2.0 redirect URI"
    )

    # Google Drive Configuration
    google_drive_scopes: List[str] = Field(
        default=[
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.metadata.readonly"
        ],
        description="Google Drive API scopes"
    )
    google_drive_max_results: int = Field(
        default=100,
        description="Maximum results per Google Drive query"
    )

    # Gmail Configuration
    gmail_scopes: List[str] = Field(
        default=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.metadata"
        ],
        description="Gmail API scopes"
    )
    gmail_max_results: int = Field(
        default=100,
        description="Maximum results per Gmail query"
    )

    # Database Configuration
    database_url: str = Field(..., description="Primary database connection URL")
    sqlite_db_path: Optional[str] = Field(
        default=None,
        description="Path to SQLite database file"
    )
    database_pool_size: int = Field(
        default=5,
        description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=10,
        description="Maximum database connection overflow"
    )

    # Security & Rate Limiting
    max_query_results: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum results for any single query"
    )
    rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Rate limit for API requests per minute"
    )
    audit_log_level: str = Field(
        default="INFO",
        description="Audit log level"
    )
    audit_log_file: str = Field(
        default="./logs/tool_integration_audit.log",
        description="Path to audit log file"
    )

    # OAuth Token Storage (Production)
    oauth_token_storage_path: Optional[str] = Field(
        default=None,
        description="Path to secure OAuth token storage directory"
    )
    oauth_token_encryption_key: Optional[str] = Field(
        default=None,
        description="Encryption key for OAuth tokens (32 bytes, base64 encoded)"
    )

    # Application Settings
    app_env: str = Field(
        default="development",
        description="Application environment"
    )
    log_level: str = Field(default="INFO", description="Application log level")
    debug: bool = Field(default=False, description="Debug mode enabled")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    timeout_seconds: int = Field(
        default=60,
        description="Request timeout in seconds"
    )
    session_timeout_hours: int = Field(
        default=8,
        description="Session timeout in hours"
    )

    # Development & Testing
    test_database_url: Optional[str] = Field(
        default="sqlite:///test_research.db",
        description="Test database connection URL"
    )
    use_mock_google_apis: bool = Field(
        default=False,
        description="Use mock Google APIs for testing"
    )
    use_mock_database: bool = Field(
        default=False,
        description="Use mock database for testing"
    )

    @validator('llm_api_key')
    def validate_llm_api_key(cls, v):
        """Validate LLM API key format."""
        if len(v) < 20:
            raise ValueError("LLM API key must be at least 20 characters long")
        if not v.startswith('sk-'):
            logger.warning("LLM API key does not start with 'sk-', may be invalid")
        return v

    @validator('google_application_credentials')
    def validate_google_credentials_path(cls, v):
        """Validate Google credentials file exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Google credentials file not found: {v}")
        if not path.suffix == '.json':
            raise ValueError("Google credentials file must be a JSON file")
        return v

    @validator('database_url')
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not (v.startswith('postgresql://') or v.startswith('sqlite://')):
            raise ValueError("Database URL must start with 'postgresql://' or 'sqlite://'")
        return v

    @validator('audit_log_file')
    def validate_audit_log_path(cls, v):
        """Ensure audit log directory exists."""
        path = Path(v)
        path.parent.mkdir(parents=True, exist_ok=True)
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == 'production'

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env.lower() == 'development'


def load_settings() -> ToolIntegrationSettings:
    """
    Load settings with proper error handling and environment loading.

    Returns:
        ToolIntegrationSettings: Validated settings instance

    Raises:
        ValueError: If required settings are missing or invalid
    """
    # Load environment variables from .env file
    load_dotenv()

    try:
        settings = ToolIntegrationSettings()
        logger.info(f"Settings loaded successfully for environment: {settings.app_env}")
        return settings
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "llm_api_key" in str(e).lower():
            error_msg += "\nMake sure to set LLM_API_KEY in your .env file"
        elif "google_application_credentials" in str(e).lower():
            error_msg += "\nMake sure to set GOOGLE_APPLICATION_CREDENTIALS path in your .env file"
        elif "database_url" in str(e).lower():
            error_msg += "\nMake sure to set DATABASE_URL in your .env file"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


# Global settings instance
settings = load_settings()