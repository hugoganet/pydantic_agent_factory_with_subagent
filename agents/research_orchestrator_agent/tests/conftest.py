"""
Test configuration for Research Orchestrator Agent.
Provides test fixtures, mocks, and shared utilities.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import uuid

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import orchestrator_agent
from ..dependencies import OrchestratorDependencies
from ..settings import Settings, load_settings
from ..tools import AgentMessage, TaskAssignment


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Create test settings with mock configurations."""
    return Settings(
        llm_api_key="test_api_key",
        llm_model="gpt-4o",
        redis_url="redis://localhost:6379/15",  # Use different DB for tests
        max_parallel_agents=3,
        research_timeout_minutes=5,
        task_timeout_seconds=60,
        min_source_quality_score=0.8,
        min_confidence_rating=0.7,
        debug=True,
        app_env="test"
    )


@pytest.fixture
def mock_redis():
    """Create a mock Redis client with realistic behavior."""
    redis_mock = AsyncMock()

    # Mock storage for Redis operations
    redis_storage = {}

    async def mock_setex(key: str, ttl: int, value: str):
        redis_storage[key] = {"value": value, "ttl": ttl, "expires": datetime.utcnow() + timedelta(seconds=ttl)}
        return True

    async def mock_get(key: str):
        if key in redis_storage:
            item = redis_storage[key]
            if datetime.utcnow() < item["expires"]:
                return item["value"]
        return None

    async def mock_lpush(queue: str, message: str):
        if queue not in redis_storage:
            redis_storage[queue] = []
        redis_storage[queue].append(message)
        return len(redis_storage[queue])

    async def mock_rpop(queue: str):
        if queue in redis_storage and redis_storage[queue]:
            return redis_storage[queue].pop(0)
        return None

    async def mock_ping():
        return True

    async def mock_close():
        pass

    redis_mock.setex.side_effect = mock_setex
    redis_mock.get.side_effect = mock_get
    redis_mock.lpush.side_effect = mock_lpush
    redis_mock.rpop.side_effect = mock_rpop
    redis_mock.ping.side_effect = mock_ping
    redis_mock.close.side_effect = mock_close
    redis_mock.storage = redis_storage  # Expose for test inspection

    return redis_mock


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client for agent communications."""
    http_mock = AsyncMock()

    # Mock successful health checks for all agents
    async def mock_get(url: str, **kwargs):
        response_mock = AsyncMock()
        if "health" in url:
            response_mock.json.return_value = {"status": "healthy", "agent_id": "test_agent"}
            response_mock.status_code = 200
        else:
            response_mock.json.return_value = {"success": True, "result": "mock_result"}
            response_mock.status_code = 200
        return response_mock

    async def mock_post(url: str, **kwargs):
        response_mock = AsyncMock()
        response_mock.json.return_value = {"success": True, "task_id": str(uuid.uuid4())}
        response_mock.status_code = 200
        return response_mock

    async def mock_aclose():
        pass

    http_mock.get.side_effect = mock_get
    http_mock.post.side_effect = mock_post
    http_mock.aclose.side_effect = mock_aclose

    return http_mock


@pytest.fixture
def test_dependencies(test_settings, mock_redis, mock_http_client):
    """Create test dependencies with mocked infrastructure."""
    deps = OrchestratorDependencies.from_settings(
        test_settings,
        session_id="test_session_123",
        research_request_id="test_request_456"
    )

    # Inject mocks
    deps.redis_client = mock_redis
    deps.http_client = mock_http_client
    deps.execution_start_time = datetime.utcnow()

    return deps


@pytest.fixture
def test_agent():
    """Create agent with TestModel for fast testing."""
    test_model = TestModel()
    return orchestrator_agent.override(model=test_model)


@pytest.fixture
def sample_research_request():
    """Sample research request for testing."""
    return "Research the latest developments in quantum computing and their potential applications in cryptography, focusing on post-quantum cryptography algorithms and current implementation challenges."


@pytest.fixture
def sample_execution_plan():
    """Sample execution plan for testing."""
    return {
        "strategy_id": str(uuid.uuid4()),
        "query": "test research query",
        "complexity": "medium",
        "timeout_minutes": 10,
        "quality_threshold": 0.8,
        "phases": {
            "planning": {"duration_seconds": 30, "agents": ["query_strategy_agent"]},
            "research": {
                "duration_seconds": 180,
                "agents": ["web_research_agent", "tool_integration_agent"],
                "parallel": True
            },
            "assessment": {"duration_seconds": 60, "agents": ["quality_assessment_agent"]},
            "attribution": {"duration_seconds": 30, "agents": ["citation_management_agent"]},
            "synthesis": {"duration_seconds": 120, "agents": ["data_synthesis_agent"]},
            "delivery": {"duration_seconds": 30, "agents": ["research_orchestrator"]}
        },
        "task_breakdown": [
            {"task": "web_search", "agent": "web_research_agent", "priority": 1},
            {"task": "tool_integration", "agent": "tool_integration_agent", "priority": 1},
            {"task": "quality_check", "agent": "quality_assessment_agent", "priority": 2}
        ],
        "resource_allocation": {
            "max_parallel_agents": 5,
            "total_estimated_time": 600
        }
    }


@pytest.fixture
def sample_research_results():
    """Sample research results for quality assessment testing."""
    return [
        {
            "source": "academic_paper",
            "title": "Quantum Computing Advances 2024",
            "content": "Recent developments in quantum error correction...",
            "url": "https://example.com/paper1",
            "credibility_score": 0.95,
            "publication_date": "2024-01-15"
        },
        {
            "source": "news_article",
            "title": "Industry Adoption of Quantum Cryptography",
            "content": "Major tech companies announce quantum crypto initiatives...",
            "url": "https://example.com/news1",
            "credibility_score": 0.75,
            "publication_date": "2024-02-01"
        },
        {
            "source": "research_report",
            "title": "Post-Quantum Cryptography Standards",
            "content": "NIST releases updated standards for PQC algorithms...",
            "url": "https://example.com/report1",
            "credibility_score": 0.92,
            "publication_date": "2024-01-30"
        }
    ]


@pytest.fixture
def sample_citations():
    """Sample formatted citations for testing."""
    return [
        {
            "id": "ref_001",
            "type": "academic_paper",
            "authors": ["Smith, J.", "Doe, A."],
            "title": "Quantum Computing Advances 2024",
            "journal": "Journal of Quantum Research",
            "year": 2024,
            "doi": "10.1000/xyz123",
            "citation_text": "Smith, J., & Doe, A. (2024). Quantum Computing Advances 2024. Journal of Quantum Research, 45(3), 123-145."
        },
        {
            "id": "ref_002",
            "type": "report",
            "organization": "NIST",
            "title": "Post-Quantum Cryptography Standards",
            "year": 2024,
            "url": "https://example.com/report1",
            "citation_text": "NIST. (2024). Post-Quantum Cryptography Standards. Retrieved from https://example.com/report1"
        }
    ]


def create_orchestration_function_model(responses: List[Dict[str, Any]]):
    """
    Create a FunctionModel with predefined orchestration responses.

    Args:
        responses: List of response configurations for different calls
    """
    call_count = 0

    async def orchestration_function(messages, tools):
        nonlocal call_count

        if call_count < len(responses):
            response = responses[call_count]
            call_count += 1

            if response.get("type") == "tool_call":
                return response["tool_call"]
            else:
                return ModelTextResponse(content=response.get("content", "Orchestration response"))
        else:
            return ModelTextResponse(content="Final orchestration complete")

    return FunctionModel(orchestration_function)


@pytest.fixture
def performance_test_data():
    """Data for performance testing."""
    return {
        "max_completion_time_seconds": 600,  # 10 minutes
        "target_success_rate": 0.95,
        "min_parallel_efficiency": 0.8,
        "expected_phases": ["planning", "research", "assessment", "attribution", "synthesis", "delivery"]
    }


# Async context manager for Redis mocking
class AsyncRedisMock:
    def __init__(self, redis_mock):
        self.redis_mock = redis_mock

    async def __aenter__(self):
        return self.redis_mock

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def async_redis_mock(mock_redis):
    """Provide async context manager for Redis mocking."""
    return AsyncRedisMock(mock_redis)


# Helper functions for test utilities
def create_mock_agent_message(recipient_id: str, message_type: str = "task") -> AgentMessage:
    """Create a mock AgentMessage for testing."""
    return AgentMessage(
        recipient_id=recipient_id,
        message_type=message_type,
        payload={"test": "data"},
        correlation_id=str(uuid.uuid4())
    )


def create_mock_task_assignment(agent_id: str, operation: str) -> TaskAssignment:
    """Create a mock TaskAssignment for testing."""
    return TaskAssignment(
        agent_id=agent_id,
        operation=operation,
        parameters={"test_param": "test_value"},
        deadline=datetime.utcnow() + timedelta(minutes=5)
    )


def assert_quality_thresholds(result: Dict[str, Any], min_credibility: float = 0.8, min_confidence: float = 0.7):
    """Assert that quality thresholds are met in results."""
    if "quality_scores" in result:
        scores = result["quality_scores"]
        assert scores.get("credibility", 0) >= min_credibility, f"Credibility {scores.get('credibility')} below threshold {min_credibility}"
        assert scores.get("confidence", 0) >= min_confidence, f"Confidence {scores.get('confidence')} below threshold {min_confidence}"


def assert_performance_metrics(result: Dict[str, Any], max_time: int = 600):
    """Assert that performance metrics meet requirements."""
    if "performance" in result:
        perf = result["performance"]
        assert perf.get("total_time_seconds", 0) <= max_time, f"Execution time {perf.get('total_time_seconds')} exceeds limit {max_time}"
        assert perf.get("success_rate", 0) >= 0.95, f"Success rate {perf.get('success_rate')} below 95%"