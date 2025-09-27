# Research Orchestrator Agent - Dependencies Configuration

## Overview

This document specifies the dependency configuration for the Research Orchestrator Agent, which serves as the master coordinator for a 7-agent research workflow system. The orchestrator requires robust infrastructure for inter-agent communication, workflow state management, and performance monitoring.

## Environment Configuration (settings.py)

### Core Settings Structure

```python
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
```

## Model Provider Configuration (providers.py)

### OpenAI GPT-4o Configuration

```python
def get_orchestrator_model() -> OpenAIModel:
    """
    Get OpenAI GPT-4o model configured for complex orchestration tasks.

    Returns:
        Configured OpenAI model optimized for workflow coordination
    """
    provider = OpenAIProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=httpx.Timeout(300.0),  # Extended timeout for complex operations
        max_retries=3
    )

    return OpenAIModel(
        settings.llm_model,
        provider=provider,
        # Optimized for structured output and coordination tasks
        temperature=0.2,  # Low temperature for consistent coordination
        max_tokens=4000   # Sufficient for detailed execution plans
    )

def get_fallback_model() -> Optional[OpenAIModel]:
    """
    Fallback to GPT-4o-mini for less critical operations.

    Returns:
        Fallback model or None if not configured
    """
    if hasattr(settings, 'fallback_api_key') and settings.fallback_api_key:
        provider = OpenAIProvider(
            api_key=settings.fallback_api_key,
            timeout=httpx.Timeout(120.0)
        )
        return OpenAIModel("gpt-4o-mini", provider=provider)
    return None
```

## Agent Dependencies (dependencies.py)

### Orchestrator Dependencies Dataclass

```python
@dataclass
class OrchestratorDependencies:
    """
    Dependencies for Research Orchestrator agent.
    Manages inter-agent communication, workflow state, and performance tracking.
    """

    # Core Infrastructure
    redis_client: Optional[redis.Redis] = None
    http_client: Optional[httpx.AsyncClient] = None

    # Agent Communication
    agent_endpoints: Dict[str, str] = field(default_factory=dict)
    message_queue_prefix: str = "research_orchestrator"
    correlation_id: Optional[str] = None

    # Workflow Configuration
    max_parallel_agents: int = 5
    research_timeout: int = 600  # 10 minutes in seconds
    task_timeout: int = 180     # 3 minutes per task
    retry_max_attempts: int = 3
    retry_backoff: int = 2

    # Quality Thresholds
    min_source_quality: float = 0.8
    min_confidence_rating: float = 0.7
    max_quality_retries: int = 2

    # Performance Tracking
    enable_metrics: bool = True
    metrics_store: Optional[Dict[str, Any]] = field(default_factory=dict)
    execution_start_time: Optional[datetime] = None

    # Workflow State Management
    active_tasks: Dict[str, Any] = field(default_factory=dict)
    completed_tasks: Dict[str, Any] = field(default_factory=dict)
    failed_tasks: Dict[str, Any] = field(default_factory=dict)
    agent_status: Dict[str, str] = field(default_factory=dict)

    # Session Context
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    research_request_id: Optional[str] = None

    # Resource Management (lazy initialization)
    _redis_pool: Optional[redis.ConnectionPool] = field(default=None, init=False, repr=False)
    _performance_monitor: Optional[Any] = field(default=None, init=False, repr=False)

    @property
    def redis_pool(self):
        """Lazy initialization of Redis connection pool."""
        if self._redis_pool is None:
            self._redis_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_pool_size,
                decode_responses=True
            )
            logger.info("Redis connection pool initialized")
        return self._redis_pool

    @property
    def performance_monitor(self):
        """Lazy initialization of performance monitoring."""
        if self._performance_monitor is None and self.enable_metrics:
            # Initialize performance monitoring system
            logger.info("Performance monitoring initialized")
        return self._performance_monitor

    async def init_redis_client(self):
        """Initialize Redis client for inter-agent messaging."""
        if not self.redis_client:
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis client initialized and tested")

    async def init_http_client(self):
        """Initialize HTTP client for agent communications."""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.task_timeout),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
            )
            logger.info("HTTP client initialized")

    async def setup_infrastructure(self):
        """Initialize all infrastructure components."""
        await self.init_redis_client()
        await self.init_http_client()

        # Initialize workflow state
        self.execution_start_time = datetime.utcnow()

        # Setup agent status monitoring
        for agent_id in self.agent_endpoints:
            self.agent_status[agent_id] = "unknown"

    async def cleanup(self):
        """Cleanup all resources."""
        if self.redis_client:
            await self.redis_client.close()
        if self.http_client:
            await self.http_client.aclose()
        if self._redis_pool:
            self._redis_pool.disconnect()
        logger.info("All resources cleaned up")

    def get_task_metrics(self) -> Dict[str, Any]:
        """Get current task execution metrics."""
        if not self.execution_start_time:
            return {}

        elapsed = (datetime.utcnow() - self.execution_start_time).total_seconds()

        return {
            "elapsed_seconds": elapsed,
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "agent_status_summary": dict(Counter(self.agent_status.values())),
            "remaining_timeout": max(0, self.research_timeout - elapsed)
        }

    @classmethod
    def from_settings(cls, settings, **kwargs):
        """Create dependencies from settings with overrides."""
        return cls(
            agent_endpoints=kwargs.get('agent_endpoints', settings.agent_endpoints),
            max_parallel_agents=kwargs.get('max_parallel_agents', settings.max_parallel_agents),
            research_timeout=kwargs.get('research_timeout', settings.research_timeout_minutes * 60),
            task_timeout=kwargs.get('task_timeout', settings.task_timeout_seconds),
            retry_max_attempts=kwargs.get('retry_max_attempts', settings.retry_max_attempts),
            retry_backoff=kwargs.get('retry_backoff', settings.retry_backoff_seconds),
            min_source_quality=kwargs.get('min_source_quality', settings.min_source_quality_score),
            min_confidence_rating=kwargs.get('min_confidence_rating', settings.min_confidence_rating),
            max_quality_retries=kwargs.get('max_quality_retries', settings.max_quality_retries),
            enable_metrics=kwargs.get('enable_metrics', settings.enable_performance_tracking),
            **{k: v for k, v in kwargs.items()
               if k not in [
                   'agent_endpoints', 'max_parallel_agents', 'research_timeout',
                   'task_timeout', 'retry_max_attempts', 'retry_backoff',
                   'min_source_quality', 'min_confidence_rating', 'max_quality_retries',
                   'enable_metrics'
               ]}
        )
```

## Agent Initialization (agent.py)

### Core Agent Setup

```python
# System prompt will be provided by prompt-engineer subagent
SYSTEM_PROMPT = """
[System prompt for Research Orchestrator will be inserted by prompt-engineer]
"""

# Initialize the orchestrator agent
orchestrator_agent = Agent(
    get_orchestrator_model(),
    deps_type=OrchestratorDependencies,
    system_prompt=SYSTEM_PROMPT,
    retries=settings.retry_max_attempts
)

# Register fallback model for reliability
fallback = get_fallback_model()
if fallback:
    orchestrator_agent.models.append(fallback)
    logger.info("Fallback model (GPT-4o-mini) configured")

# Convenience function for orchestrator usage
async def run_orchestration(
    research_request: str,
    session_id: Optional[str] = None,
    **dependency_overrides
) -> str:
    """
    Execute research orchestration with automatic dependency management.

    Args:
        research_request: User's research query/request
        session_id: Optional session identifier
        **dependency_overrides: Custom dependency configurations

    Returns:
        Comprehensive research report as string
    """
    deps = OrchestratorDependencies.from_settings(
        settings,
        session_id=session_id,
        research_request_id=str(uuid.uuid4()),
        **dependency_overrides
    )

    try:
        # Initialize infrastructure
        await deps.setup_infrastructure()

        # Execute orchestration
        result = await orchestrator_agent.run(research_request, deps=deps)

        # Log performance metrics
        metrics = deps.get_task_metrics()
        logger.info(f"Orchestration completed: {metrics}")

        return result.data
    finally:
        await deps.cleanup()
```

## Environment Variables (.env.example)

```bash
# Core LLM Configuration (REQUIRED)
LLM_PROVIDER=openai
LLM_API_KEY=your-openai-api-key-here
LLM_MODEL=gpt-4o
LLM_BASE_URL=https://api.openai.com/v1

# Inter-Agent Communication Infrastructure (REQUIRED)
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=optional-redis-password
REDIS_DB=0
REDIS_POOL_SIZE=10

# Workflow Orchestration Settings
MAX_PARALLEL_AGENTS=5
RESEARCH_TIMEOUT_MINUTES=10
TASK_TIMEOUT_SECONDS=180
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_SECONDS=2

# Quality Control Thresholds
MIN_SOURCE_QUALITY_SCORE=0.8
MIN_CONFIDENCE_RATING=0.7
MAX_QUALITY_RETRIES=2

# Coordinated Agent Endpoints (HTTP services)
AGENT_ENDPOINT_WEB_RESEARCH=http://localhost:8002
AGENT_ENDPOINT_TOOL_INTEGRATION=http://localhost:8003
AGENT_ENDPOINT_QUALITY_ASSESSMENT=http://localhost:8004
AGENT_ENDPOINT_CITATION_MANAGEMENT=http://localhost:8005
AGENT_ENDPOINT_QUERY_STRATEGY=http://localhost:8006
AGENT_ENDPOINT_DATA_SYNTHESIS=http://localhost:8007
AGENT_ENDPOINT_WORKFLOW_COORDINATOR=http://localhost:8008

# Performance Monitoring
ENABLE_PERFORMANCE_TRACKING=true
METRICS_COLLECTION_INTERVAL=30
HEALTH_CHECK_INTERVAL=60

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false

# Optional Fallback Configuration
FALLBACK_API_KEY=your-fallback-api-key
```

## Python Dependencies (requirements.txt)

```txt
# Core Pydantic AI Framework
pydantic-ai>=0.1.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0

# LLM Provider (OpenAI for GPT-4o)
openai>=1.0.0

# Inter-Agent Communication & Infrastructure
redis>=5.0.0
httpx>=0.25.0
aioredis>=2.0.0

# Async Utilities & Performance
asyncio-throttle>=1.0.0
tenacity>=8.0.0  # For retry mechanisms
asyncio-mqtt>=0.11.0  # Alternative messaging if needed

# Data Processing & Validation
pydantic[email]>=2.0.0
typing-extensions>=4.8.0
python-multipart>=0.0.6

# Monitoring & Logging
structlog>=23.0.0
prometheus-client>=0.17.0  # For metrics collection
psutil>=5.9.0  # For system monitoring

# Development & Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-redis>=3.0.0
pytest-httpx>=0.23.0
faker>=20.0.0  # For test data generation

# Code Quality
black>=23.0.0
ruff>=0.1.0
mypy>=1.6.0

# Optional Performance Extensions
uvloop>=0.18.0  # For improved async performance on Unix
orjson>=3.9.0   # For faster JSON serialization
```

## Infrastructure Dependencies

### Redis Configuration for Message Queuing

```bash
# Redis setup for inter-agent messaging
# Production: Use Redis Cluster or AWS ElastiCache
# Development: Local Redis instance

redis-server --port 6379 --save 900 1 --save 300 10 --save 60 10000
```

### Agent Communication Protocol

```python
# Inter-agent message structure (used across all 7 coordinated agents)
class AgentMessage(BaseModel):
    """Standard communication format between orchestrator and agents."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = "research_orchestrator"
    recipient_id: str
    message_type: Literal["task", "result", "status", "error", "health"]
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str
    priority: int = Field(default=1, ge=1, le=5)
    retry_count: int = Field(default=0, ge=0)
    deadline: Optional[datetime] = None

class TaskAssignment(BaseModel):
    """Task assignment from orchestrator to coordinated agents."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    operation: str
    parameters: Dict[str, Any]
    deadline: Optional[datetime] = None
    dependencies: List[str] = Field(default_factory=list)
    quality_requirements: Dict[str, float] = Field(
        default_factory=lambda: {"min_credibility": 0.8, "min_confidence": 0.7}
    )
    retry_policy: Dict[str, Any] = Field(
        default_factory=lambda: {"max_attempts": 3, "backoff_seconds": 2}
    )
```

## Security Considerations

### API Key Management
- Store OpenAI API key securely (never commit to version control)
- Use separate API keys for different environments
- Implement key rotation support for production
- Monitor API usage and set spending limits

### Inter-Agent Communication Security
- Use Redis AUTH if deployed in shared environment
- Implement message signing for critical operations
- Rate limiting on agent endpoints
- Network isolation between agent services

### Resource Protection
- Connection pooling limits to prevent resource exhaustion
- Timeout enforcement on all external operations
- Circuit breaker pattern for failing agents
- Memory usage monitoring for large research operations

## Performance Optimization

### Redis Optimization
```python
# Redis connection pool settings for high-throughput orchestration
redis_settings = {
    "max_connections": 10,
    "retry_on_timeout": True,
    "socket_keepalive": True,
    "socket_keepalive_options": {
        "TCP_KEEPIDLE": 1,
        "TCP_KEEPINTVL": 3,
        "TCP_KEEPCNT": 5,
    }
}
```

### HTTP Client Optimization
```python
# HTTP client settings for agent communication
http_limits = httpx.Limits(
    max_connections=20,      # Total connection pool
    max_keepalive_connections=10,  # Keep-alive connections
    keepalive_expiry=30.0   # Keep-alive timeout
)
```

## Testing Configuration

### Test Dependencies Mock
```python
@pytest.fixture
async def test_orchestrator_deps():
    """Mock dependencies for testing orchestration logic."""
    return OrchestratorDependencies(
        # Mock Redis with fakeredis
        redis_client=MockRedisClient(),
        # Mock HTTP client with responses
        http_client=MockHttpClient(),
        # Test configuration
        agent_endpoints={
            "web_research": "http://mock-web-research",
            "quality_assessment": "http://mock-quality",
            "data_synthesis": "http://mock-synthesis"
        },
        research_timeout=300,  # 5 minutes for tests
        enable_metrics=True,
        session_id="test-session",
        correlation_id="test-correlation"
    )
```

## Directory Structure

```
dependencies/
├── __init__.py
├── settings.py              # Environment configuration with Redis & agent endpoints
├── providers.py             # OpenAI GPT-4o model configuration
├── dependencies.py          # Orchestrator dependencies with workflow state
├── agent.py                # Agent initialization with coordination setup
├── message_protocols.py    # Inter-agent communication protocols
├── .env.example            # Complete environment template
└── requirements.txt        # All Python dependencies including Redis
```

## Quality Checklist

- ✅ OpenAI GPT-4o model configured for complex coordination tasks
- ✅ Redis infrastructure for inter-agent message queuing
- ✅ HTTP endpoints for all 7 coordinated agents
- ✅ Workflow state management with timeout enforcement
- ✅ Quality threshold configuration for source verification
- ✅ Performance monitoring and metrics collection
- ✅ Resource cleanup and connection pooling
- ✅ Error recovery and retry mechanisms
- ✅ Security measures for API keys and communications
- ✅ Testing infrastructure with mocks and fixtures

---

**Generated**: 2025-09-26
**Purpose**: Dependency specification for Research Orchestrator Agent - master coordinator for 7-agent research workflow system requiring robust infrastructure for inter-agent communication, workflow state management, and performance monitoring.