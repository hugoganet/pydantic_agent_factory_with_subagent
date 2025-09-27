"""Test configuration for Workflow Coordinator Agent tests."""

import pytest
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime
from uuid import uuid4

from ..models import AgentConfig
from ..dependencies import MetricsCollector


class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self):
        self.data = {}
        self.hash_data = {}

    async def ping(self):
        return True

    async def set(self, key: str, value: Any, ex: int = None):
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
        if name not in self.hash_data:
            self.hash_data[name] = {}
        self.hash_data[name].update(mapping)
        return len(mapping)

    async def hget(self, name: str, key: str):
        return self.hash_data.get(name, {}).get(key)

    async def hgetall(self, name: str):
        return self.hash_data.get(name, {})


@dataclass
class MockMetricsCollector:
    """Mock metrics collector for testing."""
    interval: int = 30
    metrics: Dict[str, float] = field(default_factory=dict)

    def record_metric(self, name: str, value: float):
        self.metrics[name] = value

    def get_metrics(self) -> Dict[str, float]:
        return self.metrics.copy()


@dataclass
class MockCoordinatorDependencies:
    """Mock dependencies for testing."""
    redis_client: MockRedis = field(default_factory=MockRedis)
    message_queue: MockRedis = field(default_factory=MockRedis)
    max_parallel_agents: int = 3
    health_check_interval: int = 5
    monitored_agents: Dict[str, AgentConfig] = field(default_factory=dict)
    metrics_collector: MockMetricsCollector = field(default_factory=MockMetricsCollector)
    session_id: str = "test-session"

    async def cleanup(self):
        """Mock cleanup method."""
        pass


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for testing."""
    monitored_agents = {
        "test-agent-1": AgentConfig(
            agent_id="test-agent-1",
            agent_name="Test Agent 1",
            health_check_endpoint="/health",
            priority=1
        ),
        "test-agent-2": AgentConfig(
            agent_id="test-agent-2",
            agent_name="Test Agent 2",
            health_check_endpoint="/health",
            priority=2
        ),
        "test-agent-3": AgentConfig(
            agent_id="test-agent-3",
            agent_name="Test Agent 3",
            health_check_endpoint="/health",
            priority=3
        ),
    }

    deps = MockCoordinatorDependencies(
        monitored_agents=monitored_agents
    )
    return deps


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_coordination_request():
    """Sample coordination request for testing."""
    from ..models import CoordinationRequest

    return CoordinationRequest(
        workflow_id="test-workflow-123",
        participating_agents=["test-agent-1", "test-agent-2"],
        coordination_type="parallel",
        dependencies={},
        timeout_settings={"default": 300},
        retry_policies={"default": {"max_attempts": 3}}
    )


@pytest.fixture
def sample_agent_message():
    """Sample agent message for testing."""
    from ..models import AgentMessage

    return AgentMessage(
        sender_id="test-agent-1",
        recipient_id="test-agent-2",
        message_type="task",
        payload={"action": "process", "data": "test-data"},
        correlation_id="test-correlation-123"
    )