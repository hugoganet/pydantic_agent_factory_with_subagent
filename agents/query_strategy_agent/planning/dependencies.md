# Query Strategy Agent - Dependency Configuration

## Overview

The Query Strategy Agent operates as a pure advisory service with minimal external dependencies. It requires only LLM configuration and basic NLP libraries for text analysis. No external APIs or complex service integrations are needed.

## Core Configuration Files

### settings.py - Environment Configuration
```python
"""
Configuration management for Query Strategy Agent.
Minimal setup for pure advisory service with NLP analysis.
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

    # LLM Configuration (OpenAI GPT-4o for strategic reasoning)
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_api_key: str = Field(..., description="OpenAI API key")
    llm_model: str = Field(default="gpt-4o", description="GPT-4o for advanced reasoning")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL"
    )

    # Application Configuration
    app_env: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")
    max_retries: int = Field(default=3, description="Max retry attempts for LLM")
    timeout_seconds: int = Field(default=30, description="LLM request timeout")

    # Analysis Configuration
    complexity_threshold_low: float = Field(default=3.0, description="Low complexity threshold")
    complexity_threshold_high: float = Field(default=7.0, description="High complexity threshold")
    default_confidence_threshold: float = Field(default=0.7, description="Minimum confidence for recommendations")

    @field_validator("llm_api_key")
    @classmethod
    def validate_llm_key(cls, v):
        """Ensure OpenAI API key is not empty."""
        if not v or v.strip() == "":
            raise ValueError("OpenAI API key cannot be empty")
        return v

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
        return Settings()
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "llm_api_key" in str(e).lower():
            error_msg += "\nMake sure to set LLM_API_KEY in your .env file"
        raise ValueError(error_msg) from e

# Global settings instance
settings = load_settings()
```

### providers.py - Model Provider Configuration
```python
"""
LLM provider configuration for Query Strategy Agent.
Focused on OpenAI GPT-4o for strategic reasoning capabilities.
"""

from typing import Optional
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from .settings import settings

def get_llm_model(model_choice: Optional[str] = None) -> OpenAIModel:
    """
    Get OpenAI GPT-4o model for strategic analysis.

    Args:
        model_choice: Optional override for model choice

    Returns:
        Configured OpenAI model instance
    """
    model_name = model_choice or settings.llm_model

    provider_instance = OpenAIProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key
    )

    return OpenAIModel(model_name, provider=provider_instance)
```

### dependencies.py - Agent Dependencies
```python
"""
Dependencies for Query Strategy Agent.
Minimal dependencies for pure advisory service.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

@dataclass
class AgentDependencies:
    """
    Dependencies for Query Strategy Agent runtime context.

    Minimal dependency set for pure advisory service with workflow integration.
    """

    # Workflow Context (from Research Orchestrator)
    workflow_id: Optional[str] = None
    orchestrator_session_id: Optional[str] = None
    research_context: Optional[Dict[str, Any]] = None

    # Analysis Configuration
    complexity_threshold_low: float = 3.0
    complexity_threshold_high: float = 7.0
    confidence_threshold: float = 0.7

    # Runtime Settings
    max_retries: int = 3
    timeout: int = 30
    debug: bool = False

    # Historical Context (optional for improved recommendations)
    historical_strategies: Optional[List[Dict[str, Any]]] = field(default=None)
    success_metrics: Optional[Dict[str, float]] = field(default=None)

    # NLP Processing Cache (in-memory only)
    _complexity_cache: Dict[str, float] = field(default_factory=dict, init=False, repr=False)
    _strategy_cache: Dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def cache_complexity_score(self, query: str, score: float):
        """Cache complexity analysis for performance."""
        query_hash = hash(query.lower().strip())
        self._complexity_cache[str(query_hash)] = score

    def get_cached_complexity(self, query: str) -> Optional[float]:
        """Retrieve cached complexity score."""
        query_hash = hash(query.lower().strip())
        return self._complexity_cache.get(str(query_hash))

    def update_historical_context(self, strategy_result: Dict[str, Any]):
        """Update historical context with execution results."""
        if self.historical_strategies is None:
            self.historical_strategies = []

        self.historical_strategies.append(strategy_result)

        # Keep only recent entries to prevent memory bloat
        if len(self.historical_strategies) > 100:
            self.historical_strategies = self.historical_strategies[-50:]

    @classmethod
    def from_settings(cls, settings, **kwargs):
        """
        Create dependencies from settings with overrides.

        Args:
            settings: Settings instance
            **kwargs: Override values

        Returns:
            Configured AgentDependencies instance
        """
        return cls(
            complexity_threshold_low=kwargs.get(
                'complexity_threshold_low',
                settings.complexity_threshold_low
            ),
            complexity_threshold_high=kwargs.get(
                'complexity_threshold_high',
                settings.complexity_threshold_high
            ),
            confidence_threshold=kwargs.get(
                'confidence_threshold',
                settings.default_confidence_threshold
            ),
            max_retries=kwargs.get('max_retries', settings.max_retries),
            timeout=kwargs.get('timeout', settings.timeout_seconds),
            debug=kwargs.get('debug', settings.debug),
            **{k: v for k, v in kwargs.items()
               if k not in [
                   'complexity_threshold_low', 'complexity_threshold_high',
                   'confidence_threshold', 'max_retries', 'timeout', 'debug'
               ]}
        )
```

### agent.py - Agent Initialization
```python
"""
Query Strategy Agent - Strategic advisory service for research workflow optimization.
"""

import logging
from typing import Optional
from pydantic_ai import Agent

from .providers import get_llm_model
from .dependencies import AgentDependencies
from .settings import settings

logger = logging.getLogger(__name__)

# System prompt (will be provided by prompt-engineer subagent)
SYSTEM_PROMPT = """
[System prompt will be inserted here by prompt-engineer]
"""

# Initialize the agent with GPT-4o for strategic reasoning
agent = Agent(
    get_llm_model(),
    deps_type=AgentDependencies,
    system_prompt=SYSTEM_PROMPT,
    retries=settings.max_retries
)

# Tools will be registered by tool-integrator subagent:
# - analyze_query_complexity: NLP-based complexity assessment
# - recommend_strategy: Strategy selection based on complexity
# - assess_risks: Risk identification and mitigation planning

# Convenience functions for agent usage
async def analyze_research_strategy(
    research_query: str,
    constraints: Optional[dict] = None,
    workflow_context: Optional[dict] = None,
    **dependency_overrides
) -> dict:
    """
    Analyze research query and recommend optimal strategy.

    Args:
        research_query: The research question to analyze
        constraints: Optional constraint parameters
        workflow_context: Context from Research Orchestrator
        **dependency_overrides: Override default dependencies

    Returns:
        Strategy recommendation with execution plan and risk assessment
    """
    deps = AgentDependencies.from_settings(
        settings,
        research_context=workflow_context,
        **dependency_overrides
    )

    # Build analysis prompt with context
    prompt_parts = [f"Research Query: {research_query}"]

    if constraints:
        prompt_parts.append(f"Constraints: {constraints}")

    if workflow_context:
        prompt_parts.append(f"Workflow Context: {workflow_context}")

    analysis_prompt = "\n\n".join(prompt_parts)

    result = await agent.run(analysis_prompt, deps=deps)
    return result.data

def create_strategy_agent_with_deps(**dependency_overrides) -> tuple[Agent, AgentDependencies]:
    """
    Create strategy agent instance with custom dependencies.

    Args:
        **dependency_overrides: Custom dependency values

    Returns:
        Tuple of (agent, dependencies)
    """
    deps = AgentDependencies.from_settings(settings, **dependency_overrides)
    return agent, deps
```

## Environment File Template

### .env.example
```bash
# LLM Configuration (REQUIRED)
LLM_PROVIDER=openai
LLM_API_KEY=your-openai-api-key-here
LLM_MODEL=gpt-4o
LLM_BASE_URL=https://api.openai.com/v1

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false
MAX_RETRIES=3
TIMEOUT_SECONDS=30

# Analysis Configuration
COMPLEXITY_THRESHOLD_LOW=3.0
COMPLEXITY_THRESHOLD_HIGH=7.0
DEFAULT_CONFIDENCE_THRESHOLD=0.7
```

## Python Dependencies

### requirements.txt
```
# Core Pydantic AI dependencies
pydantic-ai>=0.1.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0

# LLM Provider (OpenAI only for this agent)
openai>=1.0.0

# Basic NLP for complexity analysis
nltk>=3.8.0
spacy>=3.7.0
textstat>=0.7.0  # Readability metrics

# Async utilities
httpx>=0.25.0
aiofiles>=23.0.0

# Development and testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.0.0
ruff>=0.1.0

# Logging
loguru>=0.7.0
```

## Directory Structure

```
dependencies/
├── __init__.py
├── settings.py       # Environment configuration
├── providers.py      # OpenAI provider setup
├── dependencies.py   # Agent dependencies (minimal)
├── agent.py         # Agent initialization
├── .env.example     # Environment template
└── requirements.txt # Python dependencies
```

## NLP Library Configuration

### Optional NLP Setup
Since this agent performs complexity analysis, basic NLP libraries are included:

- **NLTK**: For basic text analysis and tokenization
- **spaCy**: For more advanced linguistic analysis (optional)
- **textstat**: For readability and complexity metrics

These are lightweight libraries suitable for complexity assessment without requiring heavy ML models.

## Security Considerations

### API Key Management
- Only requires OpenAI API key
- Uses python-dotenv for secure environment loading
- No additional external service credentials needed

### Input Validation
- Validates research queries and constraints
- Sanitizes text inputs for NLP analysis
- Implements basic rate limiting for analysis operations

## Integration Notes

### Workflow Integration
- Receives context from Research Orchestrator Agent
- Returns structured recommendations via Pydantic models
- Maintains minimal state for historical context
- No persistent storage requirements

### Performance Characteristics
- Pure advisory service with fast response times
- In-memory caching for frequently analyzed queries
- No external API dependencies beyond LLM
- Minimal resource footprint

## Testing Configuration

### Test Dependencies
```python
# Additional test dependencies
pytest-mock>=3.11.0  # For mocking NLP operations
hypothesis>=6.88.0   # Property-based testing for complexity scores
```

### Mock Configurations
- TestModel for unit testing strategy logic
- Mock NLP operations for consistent test results
- Deterministic complexity scoring for validation

This dependency configuration provides a minimal, focused setup for the Query Strategy Agent that supports its advisory role in the Research Engineering Multi-Agent Workflow while maintaining simplicity and reliability.