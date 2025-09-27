# Tool Integration Agent - Dependencies Configuration

This document specifies the minimal dependency and configuration requirements for the Tool Integration Agent, focusing on enterprise security standards and Google API integration.

## Core Dependencies Architecture

### Configuration Management Strategy
- **Environment Variables**: Use python-dotenv with pydantic-settings for secure credential management
- **OAuth 2.0 Flow**: Google APIs client library with automatic token refresh
- **Database Connection**: SQLAlchemy with connection pooling for PostgreSQL/SQLite
- **Security**: Comprehensive audit logging with structured output
- **Model Provider**: Single OpenAI GPT-4 configuration (no fallbacks for MVP)

## Environment Variables Specification

### Required Environment Variables (.env)

```bash
# LLM Configuration (REQUIRED)
LLM_PROVIDER=openai
LLM_API_KEY=your-openai-api-key-here
LLM_MODEL=gpt-4
LLM_BASE_URL=https://api.openai.com/v1

# Google Services Authentication (REQUIRED)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-service-account.json
GOOGLE_OAUTH_CLIENT_ID=your-oauth-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-oauth-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8080/oauth2callback

# Google Drive API Configuration
GOOGLE_DRIVE_SCOPES=https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/drive.metadata.readonly
GOOGLE_DRIVE_MAX_RESULTS=100

# Gmail API Configuration
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.metadata
GMAIL_MAX_RESULTS=100

# Database Configuration (REQUIRED)
DATABASE_URL=postgresql://readonly_user:password@localhost:5432/research_db
SQLITE_DB_PATH=/path/to/local/research.db
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Security & Rate Limiting
MAX_QUERY_RESULTS=100
RATE_LIMIT_PER_MINUTE=60
AUDIT_LOG_LEVEL=INFO
AUDIT_LOG_FILE=/path/to/logs/tool_integration_audit.log

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false
MAX_RETRIES=3
TIMEOUT_SECONDS=60
SESSION_TIMEOUT_HOURS=8

# OAuth Token Storage (for production)
OAUTH_TOKEN_STORAGE_PATH=/path/to/secure/tokens/
OAUTH_TOKEN_ENCRYPTION_KEY=your-32-byte-encryption-key
```

## Python Dependencies (requirements.txt)

```txt
# Core Pydantic AI framework
pydantic-ai>=0.1.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0

# LLM Provider
openai>=1.0.0

# Google API Client Libraries
google-auth>=2.16.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.2.0
google-api-python-client>=2.100.0
googleapis-common-protos>=1.60.0

# Database Connectors
sqlalchemy>=2.0.0
asyncpg>=0.28.0  # PostgreSQL async driver
aiosqlite>=0.19.0  # SQLite async driver
psycopg2-binary>=2.9.0  # PostgreSQL sync driver (fallback)

# HTTP Client and Security
httpx>=0.25.0
aiofiles>=23.0.0
cryptography>=41.0.0
authlib>=1.2.0  # OAuth 2.0 implementation

# Audit Logging and Monitoring
structlog>=23.0.0
python-json-logger>=2.0.0

# Development and Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.11.0
black>=23.0.0
ruff>=0.1.0
```

## Dependency Injection Configuration

### AgentDependencies Structure

```python
@dataclass
class ToolIntegrationDependencies:
    """
    Type-safe dependency injection for Tool Integration Agent.
    Handles Google APIs, database connections, and audit logging.
    """

    # Authentication Credentials
    google_credentials_path: str
    oauth_client_id: str
    oauth_client_secret: str
    database_url: str

    # Configuration Settings
    max_query_results: int = 100
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 60
    session_timeout_hours: int = 8

    # Runtime Context
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None

    # Service Clients (lazy initialization)
    _google_drive_service: Optional[Any] = field(default=None, init=False, repr=False)
    _gmail_service: Optional[Any] = field(default=None, init=False, repr=False)
    _db_pool: Optional[Any] = field(default=None, init=False, repr=False)
    _audit_logger: Optional[Any] = field(default=None, init=False, repr=False)

    # Security & Monitoring
    audit_log_level: str = "INFO"
    debug_mode: bool = False
```

## Service Integration Specifications

### Google APIs Configuration

```python
# Google Drive API Setup
GOOGLE_DRIVE_CONFIG = {
    "service_name": "drive",
    "version": "v3",
    "scopes": [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.metadata.readonly"
    ],
    "rate_limits": {
        "requests_per_100_seconds": 1000,
        "requests_per_user_per_100_seconds": 100
    }
}

# Gmail API Setup
GMAIL_CONFIG = {
    "service_name": "gmail",
    "version": "v1",
    "scopes": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.metadata"
    ],
    "rate_limits": {
        "requests_per_100_seconds": 1000,
        "requests_per_user_per_100_seconds": 250
    }
}
```

### Database Connection Configuration

```python
# PostgreSQL Configuration
POSTGRESQL_CONFIG = {
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "echo": False,  # Set to True for SQL logging in development
    "isolation_level": "READ_COMMITTED"
}

# SQLite Configuration (for local development)
SQLITE_CONFIG = {
    "check_same_thread": False,
    "pool_timeout": 10,
    "echo": False
}
```

## Security Configuration Specifications

### OAuth 2.0 Flow Configuration

```python
OAUTH_CONFIG = {
    "flow_type": "authorization_code",
    "redirect_uri": "http://localhost:8080/oauth2callback",
    "access_type": "offline",  # For refresh tokens
    "prompt": "consent",  # Force consent screen
    "include_granted_scopes": True,
    "token_storage": {
        "encryption": True,
        "rotation_days": 30,
        "backup_enabled": True
    }
}
```

### API Security Measures

```python
SECURITY_CONFIG = {
    "rate_limiting": {
        "google_apis": "60/minute",
        "database_queries": "100/minute",
        "overall_requests": "200/minute"
    },
    "query_validation": {
        "max_results": 100,
        "allowed_tables": ["research_data", "document_metadata"],
        "blocked_operations": ["INSERT", "UPDATE", "DELETE", "DROP"],
        "sql_injection_protection": True
    },
    "audit_requirements": {
        "log_all_requests": True,
        "log_level": "INFO",
        "include_user_context": True,
        "retention_days": 90
    }
}
```

## Audit Logging Configuration

### Structured Logging Format

```python
AUDIT_LOG_CONFIG = {
    "format": "json",
    "fields": [
        "timestamp",
        "request_id",
        "user_id",
        "tool_type",
        "operation",
        "resource_accessed",
        "success",
        "error_message",
        "response_size",
        "duration_ms"
    ],
    "destinations": [
        "file",  # Local file for development
        "stdout"  # Container logging
    ],
    "log_rotation": {
        "max_size": "100MB",
        "backup_count": 5,
        "compress": True
    }
}
```

## Error Handling Configuration

### Retry Strategy Configuration

```python
RETRY_CONFIG = {
    "google_apis": {
        "max_retries": 3,
        "backoff_strategy": "exponential",
        "base_delay": 1.0,
        "max_delay": 60.0,
        "retry_on": ["429", "500", "502", "503", "504"]
    },
    "database": {
        "max_retries": 2,
        "backoff_strategy": "linear",
        "base_delay": 0.5,
        "retry_on": ["connection_timeout", "temporary_failure"]
    },
    "llm_requests": {
        "max_retries": 3,
        "backoff_strategy": "exponential",
        "base_delay": 2.0,
        "max_delay": 30.0
    }
}
```

## Environment File Template (.env.example)

```bash
# =============================================================================
# Tool Integration Agent - Environment Configuration
# =============================================================================

# LLM Configuration (REQUIRED)
LLM_PROVIDER=openai
LLM_API_KEY=your-openai-api-key-here
LLM_MODEL=gpt-4
LLM_BASE_URL=https://api.openai.com/v1

# =============================================================================
# Google Services Authentication (REQUIRED)
# =============================================================================

# Service Account Key (for server-to-server authentication)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-service-account.json

# OAuth 2.0 Credentials (for user authentication)
GOOGLE_OAUTH_CLIENT_ID=your-oauth-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-oauth-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8080/oauth2callback

# Google Drive API Settings
GOOGLE_DRIVE_SCOPES=https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/drive.metadata.readonly
GOOGLE_DRIVE_MAX_RESULTS=100

# Gmail API Settings
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.metadata
GMAIL_MAX_RESULTS=100

# =============================================================================
# Database Configuration (REQUIRED)
# =============================================================================

# Primary Database (PostgreSQL)
DATABASE_URL=postgresql://readonly_user:secure_password@localhost:5432/research_db
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Local Database (SQLite) - for development
SQLITE_DB_PATH=/path/to/local/research.db

# =============================================================================
# Security & Rate Limiting
# =============================================================================

MAX_QUERY_RESULTS=100
RATE_LIMIT_PER_MINUTE=60
AUDIT_LOG_LEVEL=INFO
AUDIT_LOG_FILE=/path/to/logs/tool_integration_audit.log

# OAuth Token Storage (PRODUCTION ONLY)
OAUTH_TOKEN_STORAGE_PATH=/path/to/secure/tokens/
OAUTH_TOKEN_ENCRYPTION_KEY=your-32-byte-base64-encoded-encryption-key

# =============================================================================
# Application Settings
# =============================================================================

APP_ENV=development  # Options: development, staging, production
LOG_LEVEL=INFO       # Options: DEBUG, INFO, WARNING, ERROR
DEBUG=false
MAX_RETRIES=3
TIMEOUT_SECONDS=60
SESSION_TIMEOUT_HOURS=8

# =============================================================================
# Development & Testing
# =============================================================================

# Test Database (for running tests)
TEST_DATABASE_URL=sqlite:///test_research.db

# Mock API Settings (for testing without real APIs)
USE_MOCK_GOOGLE_APIS=false
USE_MOCK_DATABASE=false
```

## Settings Validation Rules

### Required Validations

```python
VALIDATION_RULES = {
    "llm_api_key": {
        "required": True,
        "min_length": 20,
        "pattern": "^sk-"
    },
    "google_credentials_path": {
        "required": True,
        "file_exists": True,
        "extension": ".json"
    },
    "database_url": {
        "required": True,
        "pattern": "^(postgresql|sqlite)://"
    },
    "max_query_results": {
        "type": "int",
        "min_value": 1,
        "max_value": 1000
    },
    "rate_limit_per_minute": {
        "type": "int",
        "min_value": 1,
        "max_value": 1000
    }
}
```

## Production Deployment Considerations

### Environment-Specific Configurations

```python
ENVIRONMENT_OVERRIDES = {
    "development": {
        "debug": True,
        "log_level": "DEBUG",
        "use_mock_apis": True,
        "oauth_redirect_uri": "http://localhost:8080/oauth2callback"
    },
    "staging": {
        "debug": False,
        "log_level": "INFO",
        "use_mock_apis": False,
        "oauth_redirect_uri": "https://staging.research.company.com/oauth2callback"
    },
    "production": {
        "debug": False,
        "log_level": "WARNING",
        "use_mock_apis": False,
        "oauth_redirect_uri": "https://research.company.com/oauth2callback",
        "enhanced_security": True
    }
}
```

### Security Hardening (Production)

```python
PRODUCTION_SECURITY = {
    "oauth_token_encryption": True,
    "database_ssl_required": True,
    "api_key_rotation_days": 30,
    "audit_log_encryption": True,
    "session_timeout_minutes": 60,
    "ip_whitelist_required": True,
    "certificate_pinning": True
}
```

## Quality Assurance Checklist

### Dependency Verification

- ✅ All required environment variables documented
- ✅ Google API client libraries properly configured
- ✅ Database connection pooling configured
- ✅ OAuth 2.0 flow with refresh tokens
- ✅ Comprehensive audit logging
- ✅ Rate limiting and security measures
- ✅ Error handling with retry strategies
- ✅ Development and production configurations
- ✅ Environment validation rules defined
- ✅ Security hardening for production deployment

### Integration Points

- ✅ Compatible with Pydantic AI agent framework
- ✅ Type-safe dependency injection
- ✅ Structured logging for monitoring
- ✅ Configuration management with pydantic-settings
- ✅ Environment variable loading with python-dotenv
- ✅ Secure credential management
- ✅ Multi-environment support (dev/staging/prod)

---

**Generated**: 2025-09-26
**Output Directory**: agents/tool_integration_agent/planning/dependencies.md
**Focus**: Enterprise security, Google API integration, audit compliance