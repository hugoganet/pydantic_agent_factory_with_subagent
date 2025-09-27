# 🎪 Workflow Coordinator Agent - Dependencies Specification

## 🔧 Core Dependencies Configuration

### Environment Variables (Essential Only)

```env
# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4
LLM_BASE_URL=https://api.openai.com/v1

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_DB=0
REDIS_PASSWORD=optional_redis_password

# System Configuration
MAX_PARALLEL_AGENTS=5
HEALTH_CHECK_INTERVAL=10
MESSAGE_RETRY_ATTEMPTS=3
WORKFLOW_TIMEOUT=600
LOG_LEVEL=INFO

# Monitoring Configuration
SYSTEM_METRICS_INTERVAL=30
ALERT_THRESHOLD_RESPONSE_TIME=5000
ALERT_THRESHOLD_ERROR_RATE=10
```

### Python Dependencies (Minimal Set)

```txt
# Core Framework
pydantic-ai[openai]==0.0.14
pydantic==2.10.4
pydantic-settings==2.6.1

# Environment Management
python-dotenv==1.0.1

# Redis for Message Queue
redis==5.2.1
aioredis==2.0.1

# Async Support
asyncio==3.4.3

# Logging and Monitoring
structlog==24.4.0

# Testing (for development)
pytest==8.3.4
pytest-asyncio==0.25.0
```

## 📦 Dependency Classes

### CoordinatorDependencies

```python
@dataclass
class CoordinatorDependencies:
    """Main dependencies for Workflow Coordinator Agent"""

    # Redis connections
    redis_client: Redis
    message_queue: aioredis.Redis

    # System configuration
    max_parallel_agents: int = 5
    health_check_interval: int = 10

    # Agent registry
    monitored_agents: Dict[str, AgentConfig] = field(default_factory=dict)

    # Performance tracking
    metrics_collector: MetricsCollector

    # Session management
    session_id: str = field(default_factory=lambda: str(uuid4()))
```

### AgentConfig Model

```python
class AgentConfig(BaseModel):
    """Configuration for monitored agents"""
    agent_id: str
    agent_name: str
    health_check_endpoint: str
    priority: int = 1
    timeout_seconds: int = 30
    retry_policy: RetryPolicy
```

### RetryPolicy Model

```python
class RetryPolicy(BaseModel):
    """Retry configuration for agent communications"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
```

## 🔗 External Service Integrations

### Redis Connection Configuration

```python
class RedisConfig(BaseSettings):
    """Redis configuration with environment support"""

    model_config = ConfigDict(
        env_file=".env",
        env_prefix="REDIS_",
        case_sensitive=False
    )

    url: str = "redis://localhost:6379"
    db: int = 0
    password: Optional[str] = None
    decode_responses: bool = True
    socket_timeout: int = 30
    health_check_interval: int = 30

async def get_redis_client() -> Redis:
    """Initialize Redis client with proper configuration"""
    config = RedisConfig()
    return Redis.from_url(
        config.url,
        db=config.db,
        password=config.password,
        decode_responses=config.decode_responses
    )
```

### LLM Model Provider

```python
def get_llm_model():
    """Get configured LLM model for coordination decisions"""
    settings = load_settings()

    if settings.llm_provider.lower() == "openai":
        provider = OpenAIProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key
        )
        return OpenAIModel(settings.llm_model, provider=provider)
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
```

## ⚙️ Settings Management

### Settings Class with Validation

```python
class CoordinatorSettings(BaseSettings):
    """Workflow Coordinator settings with environment variable support"""

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

def load_settings() -> CoordinatorSettings:
    """Load settings with proper error handling"""
    load_dotenv()

    try:
        return CoordinatorSettings()
    except Exception as e:
        error_msg = f"Failed to load coordinator settings: {e}"
        if "openai_api_key" in str(e).lower():
            error_msg += "\nMake sure to set OPENAI_API_KEY in your .env file"
        raise ValueError(error_msg) from e
```

## 🔄 Dependency Injection Pattern

### Dependency Factory

```python
async def create_coordinator_dependencies() -> CoordinatorDependencies:
    """Factory function to create all dependencies"""
    settings = load_settings()

    # Initialize Redis connections
    redis_client = await get_redis_client()
    message_queue = aioredis.from_url(settings.redis_url)

    # Initialize metrics collector
    metrics_collector = MetricsCollector(
        interval=settings.system_metrics_interval
    )

    # Define monitored agents
    monitored_agents = {
        "research-orchestrator": AgentConfig(
            agent_id="research-orchestrator",
            agent_name="Research Orchestrator Agent",
            health_check_endpoint="/health",
            priority=1
        ),
        "web-research": AgentConfig(
            agent_id="web-research",
            agent_name="Web Research Agent",
            health_check_endpoint="/health",
            priority=2
        ),
        "tool-integration": AgentConfig(
            agent_id="tool-integration",
            agent_name="Tool Integration Agent",
            health_check_endpoint="/health",
            priority=2
        ),
        "quality-assessment": AgentConfig(
            agent_id="quality-assessment",
            agent_name="Quality Assessment Agent",
            health_check_endpoint="/health",
            priority=3
        ),
        "citation-management": AgentConfig(
            agent_id="citation-management",
            agent_name="Citation Management Agent",
            health_check_endpoint="/health",
            priority=4
        ),
        "query-strategy": AgentConfig(
            agent_id="query-strategy",
            agent_name="Query Strategy Agent",
            health_check_endpoint="/health",
            priority=1
        ),
        "data-synthesis": AgentConfig(
            agent_id="data-synthesis",
            agent_name="Data Synthesis Agent",
            health_check_endpoint="/health",
            priority=5
        )
    }

    return CoordinatorDependencies(
        redis_client=redis_client,
        message_queue=message_queue,
        max_parallel_agents=settings.max_parallel_agents,
        health_check_interval=settings.health_check_interval,
        monitored_agents=monitored_agents,
        metrics_collector=metrics_collector
    )
```

## 🧪 Testing Dependencies

### Test Configuration

```python
@dataclass
class MockCoordinatorDependencies:
    """Mock dependencies for testing"""
    redis_client: MockRedis = field(default_factory=MockRedis)
    message_queue: MockAsyncRedis = field(default_factory=MockAsyncRedis)
    max_parallel_agents: int = 3
    health_check_interval: int = 5
    monitored_agents: Dict[str, AgentConfig] = field(default_factory=dict)
    metrics_collector: MockMetricsCollector = field(default_factory=MockMetricsCollector)
    session_id: str = "test-session"

def create_test_dependencies() -> MockCoordinatorDependencies:
    """Create mock dependencies for testing"""
    return MockCoordinatorDependencies()
```

This dependency specification provides a minimal, focused configuration for the Workflow Coordinator Agent while ensuring proper integration with Redis for message queuing and state management, along with comprehensive monitoring capabilities.