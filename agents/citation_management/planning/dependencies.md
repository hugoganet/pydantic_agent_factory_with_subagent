# Citation Management Agent - Dependency Configuration

## Overview

Simple, minimal dependency setup for the Citation Management Agent focusing on cost-effective OpenAI GPT-4o-mini model for structured citation output. No external services required for MVP - all processing handled via LLM reasoning with rule-based validation.

## Core Dependencies

### 1. Environment Variables

#### Required Configuration
```bash
# LLM Configuration (REQUIRED)
LLM_PROVIDER=openai
LLM_API_KEY=your-openai-api-key-here
LLM_MODEL=gpt-4o-mini  # Cost-effective model for structured output
LLM_BASE_URL=https://api.openai.com/v1

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false
MAX_RETRIES=3
TIMEOUT_SECONDS=30

# Citation Processing Settings (optional)
CITATION_BATCH_SIZE=50  # Process citations in batches
DUPLICATE_THRESHOLD=0.85  # Similarity threshold for duplicate detection
VALIDATE_CITATIONS=true  # Enable citation validation
```

#### Environment Validation Requirements
- `LLM_API_KEY`: Must be non-empty OpenAI API key
- `LLM_MODEL`: Default to "gpt-4o-mini" for cost optimization
- `APP_ENV`: One of ["development", "staging", "production"]
- `LOG_LEVEL`: One of ["DEBUG", "INFO", "WARNING", "ERROR"]

### 2. Python Dependencies

#### Core Packages (requirements.txt)
```txt
# Pydantic AI Framework
pydantic-ai>=0.1.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Environment and Configuration
python-dotenv>=1.0.0

# LLM Provider
openai>=1.0.0

# Date Processing
python-dateutil>=2.8.0

# String Similarity for Duplicate Detection
fuzzywuzzy>=0.18.0
python-Levenshtein>=0.21.0  # Speed optimization for fuzzywuzzy

# Async HTTP Client
httpx>=0.25.0

# Development and Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.0.0
ruff>=0.1.0

# Optional: Enhanced logging
loguru>=0.7.0
```

#### Citation Processing Libraries (Choose One)
**Option A - Lightweight (Recommended for MVP):**
```txt
# No additional citation libraries - use LLM-based formatting
# All citation formatting handled via GPT-4o-mini with structured output
```

**Option B - Rule-based formatting:**
```txt
# BibTeX processing (if advanced citation handling needed)
pybtex>=0.24.0
```

**Option C - CSL Processing (if complex styles needed):**
```txt
# Citation Style Language processor (heavier dependency)
citeproc-py>=0.6.0
```

### 3. Model Configuration

#### LLM Provider Setup
- **Primary Model**: OpenAI GPT-4o-mini
- **Reasoning**: Cost-effective with excellent structured output capabilities
- **No Fallback**: Single provider for simplicity
- **Token Optimization**: Batch similar citation requests

#### Model Configuration Specifications
```python
# Model provider configuration
llm_provider = "openai"
llm_model = "gpt-4o-mini"
llm_base_url = "https://api.openai.com/v1"

# Model-specific settings
max_tokens = 2048  # Sufficient for citation responses
temperature = 0.1  # Low temperature for consistent formatting
```

### 4. Agent Dependencies Structure

#### CitationDependencies Dataclass
```python
@dataclass
class CitationDependencies:
    """
    Dependencies for Citation Management Agent.
    Minimal configuration for MVP implementation.
    """

    # Configuration
    session_id: Optional[str] = None
    batch_size: int = 50
    duplicate_threshold: float = 0.85
    validate_citations: bool = True

    # Processing settings
    max_retries: int = 3
    timeout: int = 30
    debug: bool = False

    # Citation style validation rules (built-in)
    _style_requirements: Dict[str, List[str]] = field(default_factory=lambda: {
        "APA": ["authors", "publication_date", "title"],
        "MLA": ["authors", "title", "publication_date"],
        "Chicago": ["authors", "title", "publication_date"],
        "IEEE": ["authors", "title", "publication_date"],
        "Harvard": ["authors", "publication_date", "title"]
    })

    # No external service clients needed for MVP
    # All processing handled via LLM reasoning
```

### 5. Configuration Files Structure

#### settings.py Configuration
```python
"""
Configuration management for Citation Management Agent.
Uses python-dotenv and pydantic-settings for environment handling.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict
from typing import Optional, Dict, List
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
        if not v or not v.startswith(("sk-", "org-")):
            raise ValueError("Invalid OpenAI API key format")
        return v

    @field_validator("duplicate_threshold")
    @classmethod
    def validate_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Duplicate threshold must be between 0.0 and 1.0")
        return v
```

#### providers.py Configuration
```python
"""
Model provider configuration for Citation Management Agent.
Single provider setup with OpenAI GPT-4o-mini.
"""

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from .settings import Settings

def get_citation_model(settings: Settings) -> OpenAIModel:
    """
    Get configured OpenAI model for citation processing.
    Optimized for structured output and cost efficiency.
    """
    provider = OpenAIProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key
    )

    return OpenAIModel(
        model_name=settings.llm_model,
        provider=provider
    )
```

### 6. External Dependencies

#### None Required for MVP
- **No database**: Citations processed stateless
- **No caching**: Simple in-memory processing
- **No external APIs**: All formatting via LLM reasoning
- **No file storage**: Return structured responses only

#### Future Considerations (Post-MVP)
```python
# Potential future dependencies (not needed for MVP)
# database_url: Optional[str] = None  # For citation caching
# redis_url: Optional[str] = None     # For session storage
# crossref_api_key: Optional[str] = None  # For metadata enrichment
```

### 7. Directory Structure

```
dependencies/
├── __init__.py
├── settings.py          # Environment configuration with validation
├── providers.py         # OpenAI model provider setup
├── dependencies.py      # CitationDependencies dataclass
├── agent.py            # Agent initialization with dependencies
├── .env.example        # Environment variable template
└── requirements.txt    # Python package dependencies
```

### 8. Environment Template (.env.example)

```bash
# Citation Management Agent Environment Configuration

# LLM Configuration (REQUIRED)
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-openai-api-key-here
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1

# Citation Processing Settings
CITATION_BATCH_SIZE=50
DUPLICATE_THRESHOLD=0.85
VALIDATE_CITATIONS=true

# Application Configuration
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false
MAX_RETRIES=3
TIMEOUT_SECONDS=30

# Development Settings (optional)
# LOG_FORMAT=structured
# ENABLE_METRICS=false
```

## Security Considerations

### API Key Management
- Never commit `.env` files to version control
- Use environment-specific API keys
- Validate API key format on startup
- Implement key rotation support for production

### Input Validation
- Validate all citation request inputs via Pydantic models
- Sanitize source metadata to prevent injection
- Limit batch sizes to prevent resource exhaustion
- Validate citation style parameters

### Rate Limiting
- Implement request batching for OpenAI API efficiency
- Add exponential backoff for API failures
- Monitor token usage for cost control

## Quality Assurance

### Configuration Validation
- All required environment variables validated on startup
- Model provider connectivity tested during initialization
- Citation style requirements validated against supported formats
- Duplicate detection threshold within valid range (0.0-1.0)

### Testing Configuration
```python
# Test-specific dependency configuration
@pytest.fixture
def test_dependencies():
    """Test dependencies with mocked external services."""
    return CitationDependencies(
        batch_size=5,  # Smaller batches for testing
        duplicate_threshold=0.8,
        validate_citations=True,
        debug=True
    )

@pytest.fixture
def test_settings():
    """Mock settings for testing without API calls."""
    return Settings(
        llm_provider="openai",
        llm_api_key="test-key-sk-test123",
        llm_model="gpt-4o-mini",
        debug=True
    )
```

## Performance Optimization

### Batch Processing Strategy
- Process multiple citations in single LLM calls
- Optimize token usage through request batching
- Implement parallel processing for large citation sets
- Cache formatted citations within session

### Resource Management
- Lazy initialization of LLM client
- Connection pooling for HTTP requests
- Memory-efficient duplicate detection algorithms
- Cleanup resources after processing completion

## Integration Points

### Workflow Communication
- Receive `CitationRequest` from Quality Assessment Agent (#4)
- Return `CitationResponse` to Data Synthesis Agent (#7)
- Standard AgentMessage protocol for inter-agent communication
- JSON serialization for structured data exchange

### Error Handling
- Graceful handling of incomplete source metadata
- Partial citation generation when data is missing
- Clear error messages for validation failures
- Fallback formatting for unsupported citation styles

---

**Implementation Priority**: Core dependencies only for MVP
**Total Dependencies**: 8 essential packages + OpenAI
**External Services**: None (LLM-based processing only)
**Configuration Complexity**: Minimal (12 environment variables)

Generated: 2025-09-26