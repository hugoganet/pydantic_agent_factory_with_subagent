"""Dependencies for the Workflow Coordinator Agent."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from uuid import uuid4
import redis.asyncio as redis
import aioredis
from redis import Redis

from .models import AgentConfig, RetryPolicy
from .settings import load_settings


@dataclass
class MetricsCollector:
    """Simple metrics collector for system monitoring."""
    interval: int = 30
    metrics: Dict[str, float] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)

    def record_metric(self, name: str, value: float):
        """Record a metric value."""
        self.metrics[name] = value

    def get_metrics(self) -> Dict[str, float]:
        """Get current metrics."""
        uptime = time.time() - self.start_time
        self.metrics["uptime_seconds"] = uptime
        return self.metrics.copy()


@dataclass
class CoordinatorDependencies:
    """Main dependencies for Workflow Coordinator Agent."""

    # Redis connections
    redis_client: redis.Redis
    message_queue: redis.Redis

    # System configuration
    max_parallel_agents: int = 5
    health_check_interval: int = 10

    # Agent registry
    monitored_agents: Dict[str, AgentConfig] = field(default_factory=dict)

    # Performance tracking
    metrics_collector: MetricsCollector

    # Session management
    session_id: str = field(default_factory=lambda: str(uuid4()))

    async def cleanup(self):
        """Clean up resources."""
        try:
            await self.redis_client.close()
            await self.message_queue.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")


async def get_redis_client() -> redis.Redis:
    """Initialize Redis client with proper configuration."""
    settings = load_settings()
    try:
        client = redis.from_url(
            settings.redis_url,
            db=settings.redis_db,
            decode_responses=True,
            socket_timeout=30,
            health_check_interval=30
        )
        # Test connection
        await client.ping()
        return client
    except Exception as e:
        # Fallback to mock client for development
        print(f"Redis connection failed: {e}. Using mock client.")
        return MockRedisClient()


class MockRedisClient:
    """Mock Redis client for development/testing."""
    def __init__(self):
        self.data = {}

    async def ping(self):
        return True

    async def set(self, key: str, value: Any, ex: Optional[int] = None):
        self.data[key] = value
        return True

    async def get(self, key: str):
        return self.data.get(key)

    async def delete(self, *keys):
        for key in keys:
            self.data.pop(key, None)
        return len(keys)

    async def close(self):
        pass

    async def hset(self, name: str, mapping: Dict[str, Any]):
        if name not in self.data:
            self.data[name] = {}
        self.data[name].update(mapping)
        return len(mapping)

    async def hget(self, name: str, key: str):
        return self.data.get(name, {}).get(key)

    async def hgetall(self, name: str):
        return self.data.get(name, {})


async def create_coordinator_dependencies() -> CoordinatorDependencies:
    """Factory function to create all dependencies."""
    settings = load_settings()

    # Initialize Redis connections
    redis_client = await get_redis_client()
    message_queue = redis_client  # Use same client for simplicity

    # Initialize metrics collector
    metrics_collector = MetricsCollector(
        interval=settings.system_metrics_interval
    )

    # Define monitored agents based on workflow architecture
    monitored_agents = {
        "research-orchestrator": AgentConfig(
            agent_id="research-orchestrator",
            agent_name="Research Orchestrator Agent",
            health_check_endpoint="/health",
            priority=1,
            retry_policy={
                "max_attempts": 3,
                "base_delay": 1.0,
                "max_delay": 30.0,
                "exponential_base": 2.0
            }
        ),
        "web-research": AgentConfig(
            agent_id="web-research",
            agent_name="Web Research Agent",
            health_check_endpoint="/health",
            priority=2,
            retry_policy={
                "max_attempts": 3,
                "base_delay": 1.0,
                "max_delay": 30.0,
                "exponential_base": 2.0
            }
        ),
        "tool-integration": AgentConfig(
            agent_id="tool-integration",
            agent_name="Tool Integration Agent",
            health_check_endpoint="/health",
            priority=2,
            retry_policy={
                "max_attempts": 3,
                "base_delay": 1.0,
                "max_delay": 30.0,
                "exponential_base": 2.0
            }
        ),
        "quality-assessment": AgentConfig(
            agent_id="quality-assessment",
            agent_name="Quality Assessment Agent",
            health_check_endpoint="/health",
            priority=3,
            retry_policy={
                "max_attempts": 3,
                "base_delay": 1.0,
                "max_delay": 30.0,
                "exponential_base": 2.0
            }
        ),
        "citation-management": AgentConfig(
            agent_id="citation-management",
            agent_name="Citation Management Agent",
            health_check_endpoint="/health",
            priority=4,
            retry_policy={
                "max_attempts": 3,
                "base_delay": 1.0,
                "max_delay": 30.0,
                "exponential_base": 2.0
            }
        ),
        "query-strategy": AgentConfig(
            agent_id="query-strategy",
            agent_name="Query Strategy Agent",
            health_check_endpoint="/health",
            priority=1,
            retry_policy={
                "max_attempts": 3,
                "base_delay": 1.0,
                "max_delay": 30.0,
                "exponential_base": 2.0
            }
        ),
        "data-synthesis": AgentConfig(
            agent_id="data-synthesis",
            agent_name="Data Synthesis Agent",
            health_check_endpoint="/health",
            priority=5,
            retry_policy={
                "max_attempts": 3,
                "base_delay": 1.0,
                "max_delay": 30.0,
                "exponential_base": 2.0
            }
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