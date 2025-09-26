"""
Research Orchestrator Agent - Dependencies

Manages inter-agent communication, workflow state, and performance tracking
for the master coordinator in the Research Engineering Workflow system.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from collections import Counter
import redis.asyncio as redis
import httpx
import logging
import uuid

from .settings import settings

logger = logging.getLogger(__name__)


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

    # Workflow Phase Tracking
    current_phase: Optional[str] = None
    active_agents: list = field(default_factory=list)
    quality_requirements: Dict[str, float] = field(default_factory=dict)
    system_health: Optional[Dict[str, Any]] = None
    priority_level: Optional[str] = None

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
        self.correlation_id = str(uuid.uuid4())
        self.research_request_id = str(uuid.uuid4())

        # Setup agent status monitoring
        if not self.agent_endpoints:
            self.agent_endpoints = settings.agent_endpoints

        for agent_id in self.agent_endpoints:
            self.agent_status[agent_id] = "unknown"

        # Initialize quality requirements
        if not self.quality_requirements:
            self.quality_requirements = {
                "min_credibility": self.min_source_quality,
                "min_confidence": self.min_confidence_rating
            }

        logger.info(f"Infrastructure setup complete for session: {self.session_id}")

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
            "remaining_timeout": max(0, self.research_timeout - elapsed),
            "current_phase": self.current_phase,
            "active_agents": len(self.active_agents)
        }

    @classmethod
    def from_settings(cls, settings_obj=None, **kwargs):
        """Create dependencies from settings with overrides."""
        if settings_obj is None:
            settings_obj = settings

        return cls(
            agent_endpoints=kwargs.get('agent_endpoints', settings_obj.agent_endpoints),
            max_parallel_agents=kwargs.get('max_parallel_agents', settings_obj.max_parallel_agents),
            research_timeout=kwargs.get('research_timeout', settings_obj.research_timeout_minutes * 60),
            task_timeout=kwargs.get('task_timeout', settings_obj.task_timeout_seconds),
            retry_max_attempts=kwargs.get('retry_max_attempts', settings_obj.retry_max_attempts),
            retry_backoff=kwargs.get('retry_backoff', settings_obj.retry_backoff_seconds),
            min_source_quality=kwargs.get('min_source_quality', settings_obj.min_source_quality_score),
            min_confidence_rating=kwargs.get('min_confidence_rating', settings_obj.min_confidence_rating),
            max_quality_retries=kwargs.get('max_quality_retries', settings_obj.max_quality_retries),
            enable_metrics=kwargs.get('enable_metrics', settings_obj.enable_performance_tracking),
            **{k: v for k, v in kwargs.items()
               if k not in [
                   'agent_endpoints', 'max_parallel_agents', 'research_timeout',
                   'task_timeout', 'retry_max_attempts', 'retry_backoff',
                   'min_source_quality', 'min_confidence_rating', 'max_quality_retries',
                   'enable_metrics'
               ]}
        )