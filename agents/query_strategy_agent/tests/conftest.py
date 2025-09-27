"""
Test configuration and fixtures for Query Strategy Agent.
"""

import pytest
from typing import Dict, Any, List, Optional
from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import agent
from ..dependencies import AgentDependencies
from ..settings import settings


@pytest.fixture
def test_model():
    """Create TestModel for basic agent testing."""
    return TestModel()


@pytest.fixture
def test_agent():
    """Create agent with TestModel for testing."""
    test_model = TestModel()
    return agent.override(model=test_model)


@pytest.fixture
def test_dependencies():
    """Create test dependencies."""
    return AgentDependencies(
        workflow_id="test_workflow_123",
        orchestrator_session_id="test_session_456",
        research_context={"test_mode": True},
        complexity_threshold_low=3.0,
        complexity_threshold_high=7.0,
        confidence_threshold=0.7,
        debug=True
    )


@pytest.fixture
def test_dependencies_with_history():
    """Create test dependencies with historical data."""
    return AgentDependencies(
        workflow_id="test_workflow_123",
        orchestrator_session_id="test_session_456",
        research_context={"test_mode": True},
        complexity_threshold_low=3.0,
        complexity_threshold_high=7.0,
        confidence_threshold=0.7,
        debug=True,
        historical_strategies=[
            {"strategy": "simple_direct", "duration": 15, "success": True, "complexity": 2.5},
            {"strategy": "moderate_multisource", "duration": 45, "success": True, "complexity": 5.2},
            {"strategy": "complex_iterative", "duration": 90, "success": False, "complexity": 8.1}
        ],
        success_metrics={"success_rate": 0.75, "avg_duration": 50}
    )


@pytest.fixture
def sample_queries():
    """Sample research queries for testing."""
    return {
        "simple": "What is machine learning?",
        "moderate": "How does deep learning differ from traditional machine learning approaches in terms of performance and computational requirements?",
        "complex": "What are the ethical implications of using AI in healthcare decision-making, particularly regarding bias in algorithmic diagnosis and treatment recommendations across different demographic groups?",
        "technical": "Analyze the computational complexity of transformer architectures in natural language processing and their scalability limitations for real-time applications",
        "interdisciplinary": "How do psychological factors influence economic decision-making in behavioral economics research, and what methodological approaches are used to study this intersection?",
        "temporal": "What were the key technological developments in artificial intelligence from 1950 to 2023, and how did they influence current deep learning paradigms?",
        "empty": "",
        "very_long": " ".join(["This is a very long research query about artificial intelligence and machine learning"] * 20)
    }


@pytest.fixture
def sample_constraints():
    """Sample constraint configurations for testing."""
    return {
        "strict_time": {"time_limit": 15, "source_limit": 3, "quality_threshold": 0.8},
        "moderate": {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7},
        "relaxed": {"time_limit": 120, "source_limit": 20, "quality_threshold": 0.6},
        "high_quality": {"time_limit": 90, "source_limit": 15, "quality_threshold": 0.9},
        "minimal": {"time_limit": 10, "source_limit": 1, "quality_threshold": 0.5}
    }


@pytest.fixture
def expected_complexity_ranges():
    """Expected complexity score ranges for sample queries."""
    return {
        "simple": (1.0, 3.0),
        "moderate": (4.0, 6.5),
        "complex": (7.0, 9.5),
        "technical": (6.0, 9.0),
        "interdisciplinary": (5.0, 8.5),
        "temporal": (5.5, 8.0)
    }


def create_complexity_analysis_function():
    """Create function model for complexity analysis testing."""
    call_count = 0

    async def complexity_function(messages, tools):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            # First call - analyze complexity
            return {
                "analyze_complexity": {
                    "research_query": "test query",
                    "constraints": {"time_limit": 60}
                }
            }
        else:
            # Response with analysis
            return ModelTextResponse(
                content="Based on the complexity analysis, this query has moderate complexity..."
            )

    return complexity_function


def create_strategy_recommendation_function():
    """Create function model for strategy recommendation testing."""
    call_count = 0

    async def strategy_function(messages, tools):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return ModelTextResponse(
                content="I'll analyze the query and recommend an optimal strategy"
            )
        elif call_count == 2:
            # Call complexity analysis
            return {
                "analyze_complexity": {
                    "research_query": "test query",
                    "constraints": {"time_limit": 60}
                }
            }
        elif call_count == 3:
            # Call strategy recommendation
            return {
                "recommend_strategy": {
                    "complexity_metrics": {"overall_complexity": 5.0},
                    "constraints": {"time_limit": 60, "source_limit": 10},
                    "use_historical": True
                }
            }
        elif call_count == 4:
            # Call risk assessment
            return {
                "assess_risks": {
                    "complexity_metrics": {"overall_complexity": 5.0},
                    "strategy_plan": {"recommended_strategy": "moderate_multisource"},
                    "constraints": {"time_limit": 60}
                }
            }
        else:
            # Final comprehensive response
            return ModelTextResponse(
                content="Comprehensive strategy analysis complete with recommendations and risk assessment."
            )

    return strategy_function


@pytest.fixture
def complexity_function_model():
    """Function model for complexity analysis testing."""
    return FunctionModel(create_complexity_analysis_function())


@pytest.fixture
def strategy_function_model():
    """Function model for full strategy workflow testing."""
    return FunctionModel(create_strategy_recommendation_function())


@pytest.fixture
def performance_test_queries():
    """Queries specifically designed for performance testing."""
    return [
        "Simple query for performance testing",
        "Medium complexity query about machine learning algorithms for performance evaluation",
        "Complex interdisciplinary query about the intersection of artificial intelligence, behavioral psychology, and economic policy making for comprehensive performance testing scenarios"
    ]


class MockComplexityResult:
    """Mock complexity analysis result for testing."""

    def __init__(self, complexity: float):
        self.data = {
            "success": True,
            "complexity_metrics": {
                "scope_score": complexity * 0.8,
                "technical_difficulty": complexity * 0.9,
                "data_availability": 7.0,
                "interdisciplinary_factor": complexity * 0.6,
                "overall_complexity": complexity
            },
            "analysis_details": {
                "identified_concepts": ["concept1", "concept2"],
                "technical_terms": ["term1", "term2"],
                "complexity_indicators": ["indicator1"],
                "estimated_sources_needed": int(complexity / 2) + 1,
                "word_count": int(complexity * 10),
                "concept_count": int(complexity)
            },
            "processing_time": 0.1
        }


@pytest.fixture
def mock_complexity_results():
    """Mock complexity results for different complexity levels."""
    return {
        "simple": MockComplexityResult(2.5),
        "moderate": MockComplexityResult(5.2),
        "complex": MockComplexityResult(8.1)
    }


# Performance test configuration
@pytest.fixture
def performance_config():
    """Configuration for performance tests."""
    return {
        "response_time_limit": 30.0,  # 30 seconds
        "complexity_precision_target": 0.9,  # 90% precision
        "time_estimate_accuracy": 0.2,  # Within 20% accuracy
        "concurrent_request_count": 5,
        "test_iterations": 10
    }


# Error simulation fixtures
@pytest.fixture
def error_scenarios():
    """Error scenarios for testing error handling."""
    return {
        "empty_query": "",
        "null_constraints": None,
        "invalid_complexity": {"overall_complexity": "invalid"},
        "missing_strategy_plan": {},
        "timeout_simulation": {"simulate_timeout": True}
    }