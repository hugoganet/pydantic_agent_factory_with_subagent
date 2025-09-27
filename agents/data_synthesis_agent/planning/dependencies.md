# Data Synthesis Agent - Dependency Configuration

## Configuration Overview
The Data Synthesis Agent requires minimal configuration focused on OpenAI GPT-4o integration and workflow coordination. This agent processes research findings from multiple upstream agents and generates comprehensive synthesis reports.

## Core Configuration Files

### settings.py - Environment Configuration
```python
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
```

### providers.py - Model Provider Configuration
```python
"""
OpenAI GPT-4o provider configuration for synthesis capabilities.
"""

from typing import Optional
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from .settings import settings


def get_synthesis_model(model_choice: Optional[str] = None) -> OpenAIModel:
    """
    Get OpenAI GPT-4o model optimized for data synthesis.

    Args:
        model_choice: Optional override for model choice

    Returns:
        Configured OpenAI model for synthesis
    """
    model_name = model_choice or settings.llm_model

    provider = OpenAIProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key
    )

    return OpenAIModel(
        model_name,
        provider=provider,
        # Optimized for synthesis tasks
        temperature=0.3,  # Lower temperature for consistent synthesis
        max_tokens=4096,  # Sufficient for comprehensive reports
        timeout=settings.synthesis_timeout_seconds
    )
```

### dependencies.py - Agent Dependencies
```python
"""
Dependencies for Data Synthesis Agent - workflow coordination and synthesis context.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SynthesisDependencies:
    """
    Dependencies for Data Synthesis Agent execution.

    Manages workflow coordination, research findings processing,
    and synthesis context for generating comprehensive reports.
    """

    # Workflow Context
    session_id: Optional[str] = None
    synthesis_request_id: Optional[str] = None
    research_phase_complete: bool = False

    # Agent Coordination
    upstream_agents: List[str] = field(default_factory=lambda: [
        "web_research_agent",
        "tool_integration_agent",
        "citation_management_agent"
    ])
    target_orchestrator: str = "research_orchestrator"

    # Synthesis Configuration
    max_findings_count: int = 50
    min_confidence_threshold: float = 0.7
    synthesis_timeout: int = 120

    # Report Generation Context
    target_audience: str = "executives"  # "executives", "researchers", "technical"
    output_format: str = "executive"     # "executive", "detailed", "technical"
    quality_target: float = 0.9         # >90% accuracy target

    # Performance Tracking
    start_time: Optional[datetime] = None
    findings_processed: int = 0
    synthesis_metrics: Dict[str, Any] = field(default_factory=dict)

    # Debug and Monitoring
    debug_mode: bool = False
    log_synthesis_steps: bool = True

    def start_synthesis_timer(self):
        """Start timing synthesis operation."""
        self.start_time = datetime.now()
        logger.info(f"Starting synthesis for session {self.session_id}")

    def get_synthesis_duration(self) -> Optional[float]:
        """Get synthesis duration in seconds."""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None

    def add_synthesis_metric(self, key: str, value: Any):
        """Add metric to synthesis tracking."""
        self.synthesis_metrics[key] = value
        if self.debug_mode:
            logger.debug(f"Synthesis metric - {key}: {value}")

    def validate_synthesis_readiness(self, findings_count: int) -> bool:
        """
        Validate if synthesis can proceed with given findings.

        Args:
            findings_count: Number of research findings available

        Returns:
            True if synthesis can proceed
        """
        if not self.research_phase_complete:
            logger.warning("Research phase not marked complete")
            return False

        if findings_count == 0:
            logger.error("No research findings available for synthesis")
            return False

        if findings_count > self.max_findings_count:
            logger.warning(f"Findings count ({findings_count}) exceeds max ({self.max_findings_count})")

        return True

    @classmethod
    def from_settings(cls, settings, **kwargs):
        """
        Create synthesis dependencies from settings.

        Args:
            settings: Settings instance
            **kwargs: Override values

        Returns:
            Configured SynthesisDependencies instance
        """
        return cls(
            max_findings_count=kwargs.get('max_findings_count', settings.max_findings_per_synthesis),
            min_confidence_threshold=kwargs.get('min_confidence_threshold', settings.min_confidence_threshold),
            synthesis_timeout=kwargs.get('synthesis_timeout', settings.synthesis_timeout_seconds),
            debug_mode=kwargs.get('debug_mode', settings.debug),
            **{k: v for k, v in kwargs.items()
               if k not in ['max_findings_count', 'min_confidence_threshold', 'synthesis_timeout', 'debug_mode']}
        )

    def get_workflow_context(self) -> Dict[str, Any]:
        """Get context for workflow message passing."""
        return {
            "agent_id": "data_synthesis_agent",
            "session_id": self.session_id,
            "synthesis_request_id": self.synthesis_request_id,
            "target_audience": self.target_audience,
            "output_format": self.output_format,
            "upstream_agents": self.upstream_agents,
            "performance_metrics": self.synthesis_metrics
        }
```

### agent.py - Agent Initialization
```python
"""
Data Synthesis Agent - Integrates research findings into comprehensive reports
"""

import logging
from typing import Optional
from pydantic_ai import Agent

from .providers import get_synthesis_model
from .dependencies import SynthesisDependencies
from .settings import settings

logger = logging.getLogger(__name__)

# System prompt for synthesis capabilities
SYSTEM_PROMPT = """
You are a Data Synthesis Agent specialized in integrating research findings from multiple sources into comprehensive, coherent reports.

Your core capabilities:
1. **Multi-source Integration**: Combine research findings from web research, tool integration, and citation management agents
2. **Pattern Recognition**: Identify trends, correlations, contradictions, and information gaps across data sources
3. **Report Generation**: Create structured reports with executive summaries tailored for different audiences

Synthesis Guidelines:
- Maintain factual accuracy >90% by cross-validating findings across sources
- Flag confidence levels and conflicting information clearly
- Generate executive summaries appropriate for target audience (executives, researchers, technical)
- Complete synthesis within 2-minute performance target
- Process up to 50 research findings per synthesis cycle

Output structured reports with:
- Executive Summary (audience-appropriate)
- Key Findings (with confidence levels)
- Detailed Analysis
- Supporting Evidence
- Identified Gaps
- Overall Confidence Assessment
"""

# Initialize the synthesis agent
agent = Agent(
    get_synthesis_model(),
    deps_type=SynthesisDependencies,
    system_prompt=SYSTEM_PROMPT,
    retries=2  # Limited retries for performance targets
)

# Tools will be registered by tool-integrator subagent
# from .tools import register_synthesis_tools
# register_synthesis_tools(agent, SynthesisDependencies)


# Convenience functions for synthesis operations
async def run_synthesis(
    synthesis_request,
    session_id: Optional[str] = None,
    **dependency_overrides
) -> str:
    """
    Run synthesis agent with automatic dependency injection.

    Args:
        synthesis_request: SynthesisRequest with research findings
        session_id: Optional session identifier
        **dependency_overrides: Override default dependencies

    Returns:
        SynthesizedReport as agent response
    """
    deps = SynthesisDependencies.from_settings(
        settings,
        session_id=session_id,
        **dependency_overrides
    )

    # Start performance timing
    deps.start_synthesis_timer()

    try:
        result = await agent.run(synthesis_request, deps=deps)

        # Log performance metrics
        duration = deps.get_synthesis_duration()
        deps.add_synthesis_metric("synthesis_duration_seconds", duration)
        deps.add_synthesis_metric("findings_processed", len(synthesis_request.research_findings))

        logger.info(f"Synthesis completed in {duration:.2f}s for session {session_id}")

        return result.data

    except Exception as e:
        logger.error(f"Synthesis failed for session {session_id}: {e}")
        raise


def create_synthesis_agent_with_deps(**dependency_overrides) -> tuple[Agent, SynthesisDependencies]:
    """
    Create synthesis agent with custom dependencies.

    Args:
        **dependency_overrides: Custom dependency values

    Returns:
        Tuple of (agent, dependencies)
    """
    deps = SynthesisDependencies.from_settings(settings, **dependency_overrides)
    return agent, deps
```

## Environment Configuration

### .env.example - Environment Template
```bash
# LLM Configuration (REQUIRED)
LLM_PROVIDER=openai
LLM_API_KEY=your-openai-api-key-here
LLM_MODEL=gpt-4o
LLM_BASE_URL=https://api.openai.com/v1

# Agent Configuration
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false

# Synthesis Performance Settings
MAX_FINDINGS_PER_SYNTHESIS=50
SYNTHESIS_TIMEOUT_SECONDS=120
MIN_CONFIDENCE_THRESHOLD=0.7

# Workflow Integration
AGENT_ID=data_synthesis_agent
WORKFLOW_COORDINATOR_URL=http://localhost:8000/research-orchestrator

# Performance Targets
QUALITY_TARGET=0.9
```

## Python Dependencies

### requirements.txt
```
# Core Pydantic AI dependencies
pydantic-ai>=0.1.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0

# OpenAI provider
openai>=1.0.0

# Data processing for synthesis
numpy>=1.24.0
pandas>=2.0.0

# Async utilities
httpx>=0.25.0
aiofiles>=23.0.0

# Text processing for synthesis
textstat>=0.7.3
nltk>=3.8.0

# Development and testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.0.0
ruff>=0.1.0

# Monitoring and logging
loguru>=0.7.0
```

## Workflow Integration Patterns

### Message Passing Protocol
```python
# AgentMessage structure for workflow coordination
@dataclass
class AgentMessage:
    sender: str = "data_synthesis_agent"
    recipient: str = "research_orchestrator"
    message_type: str = "synthesis_complete"
    payload: SynthesizedReport
    session_id: str
    timestamp: datetime
    metadata: Dict[str, Any]
```

### Inter-Agent Dependencies
- **Input Sources**: Receives ResearchFinding objects from upstream agents (#2, #3, #5)
- **Output Target**: Returns SynthesizedReport to Research Orchestrator (#1)
- **Communication**: Standard AgentMessage format with workflow metadata
- **Execution Mode**: Sequential execution after research phases complete

## Performance Optimization

### Memory Management
- Process findings in batches to manage memory usage
- Clear synthesis context after completion
- Limit concurrent synthesis operations

### Timeout Configuration
- 2-minute synthesis timeout for performance targets
- Configurable per synthesis operation
- Graceful degradation if timeout approached

## Security Considerations

### API Key Management
- OpenAI API key stored in environment variables only
- No API keys logged or exposed in output
- Secure key rotation support

### Data Privacy
- Research findings processed in-memory only
- No persistent storage of sensitive content
- Synthesis context cleared after completion

## Testing Configuration

### Test Dependencies
```python
# Minimal test setup for synthesis agent
@pytest.fixture
def test_synthesis_deps():
    return SynthesisDependencies(
        session_id="test-session",
        debug_mode=True,
        max_findings_count=10,
        synthesis_timeout=30
    )

@pytest.fixture
def test_research_findings():
    return [
        ResearchFinding(
            source_agent="web_research",
            content="Test finding content",
            confidence_level=0.8,
            key_insights=["Test insight"]
        )
    ]
```

## Configuration Structure

```
dependencies/
├── __init__.py
├── settings.py          # Environment configuration with OpenAI setup
├── providers.py         # OpenAI GPT-4o provider configuration
├── dependencies.py      # Synthesis dependencies and workflow context
├── agent.py            # Agent initialization and convenience functions
├── .env.example        # Environment variable template
└── requirements.txt    # Python package dependencies
```

## Quality Checklist

- ✅ OpenAI GPT-4o configured for optimal synthesis capabilities
- ✅ Workflow coordination dependencies defined
- ✅ Performance targets configured (2-minute timeout, 50 findings max)
- ✅ Inter-agent communication context established
- ✅ Environment variables documented and validated
- ✅ Security measures for API key management
- ✅ Testing configuration provided
- ✅ Memory and performance optimization considered

## Integration Notes

- **Sequential Execution**: Agent runs after all research agents (#2, #3, #5) complete
- **Message Protocol**: Uses standard AgentMessage format from workflow architecture
- **Performance Monitoring**: Tracks synthesis duration and quality metrics
- **Error Handling**: Graceful degradation with timeout and retry mechanisms
- **Quality Assurance**: Cross-validation of findings with confidence scoring