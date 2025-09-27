"""
Performance tests for Query Strategy Agent.
Tests response times, throughput, and performance requirements.
"""

import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

from ..agent import agent, analyze_research_strategy, quick_complexity_check
from ..tools import analyze_query_complexity, recommend_research_strategy, assess_research_risks
from ..dependencies import AgentDependencies
from pydantic_ai.models.test import TestModel


class TestResponseTimeRequirements:
    """Test response time requirements from INITIAL.md."""

    @pytest.mark.asyncio
    async def test_sub_30_second_response_requirement(self, test_agent, test_dependencies, performance_config):
        """Test that agent responds within 30 seconds (requirement from INITIAL.md)."""
        start_time = time.time()

        result = await test_agent.run(
            "Analyze the complexity and recommend strategy for quantum computing applications in cryptography",
            deps=test_dependencies
        )

        end_time = time.time()
        response_time = end_time - start_time

        assert result.data is not None
        assert response_time < performance_config["response_time_limit"], \
            f"Response took {response_time:.2f}s, exceeding 30s limit"

    @pytest.mark.asyncio
    async def test_tool_performance_requirements(self, performance_test_queries, performance_config):
        """Test that individual tools meet performance requirements."""
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7}

        for query in performance_test_queries:
            # Test complexity analysis performance
            start_time = time.time()
            complexity_result = await analyze_query_complexity(query, constraints)
            complexity_time = time.time() - start_time

            assert complexity_result["success"] is True
            assert complexity_time < 5.0, f"Complexity analysis took {complexity_time:.2f}s"

            # Test strategy recommendation performance
            start_time = time.time()
            strategy_result = await recommend_research_strategy(
                complexity_result["complexity_metrics"],
                constraints
            )
            strategy_time = time.time() - start_time

            assert strategy_result["success"] is True
            assert strategy_time < 3.0, f"Strategy recommendation took {strategy_time:.2f}s"

            # Test risk assessment performance
            start_time = time.time()
            risk_result = await assess_research_risks(
                complexity_result["complexity_metrics"],
                strategy_result,
                constraints
            )
            risk_time = time.time() - start_time

            assert risk_result["success"] is True
            assert risk_time < 2.0, f"Risk assessment took {risk_time:.2f}s"

    @pytest.mark.asyncio
    async def test_quick_complexity_check_performance(self, performance_test_queries):
        """Test quick complexity check meets performance goals."""
        for query in performance_test_queries:
            start_time = time.time()
            score = await quick_complexity_check(query)
            end_time = time.time()

            response_time = end_time - start_time

            assert isinstance(score, float)
            assert 1.0 <= score <= 10.0
            assert response_time < 1.0, f"Quick check took {response_time:.2f}s"

    @pytest.mark.asyncio
    async def test_analyze_research_strategy_performance(self, performance_test_queries):
        """Test analyze_research_strategy function performance."""
        constraints = {"time_limit": 60, "source_limit": 8, "quality_threshold": 0.7}

        for query in performance_test_queries:
            start_time = time.time()

            result = await analyze_research_strategy(
                query,
                constraints=constraints,
                workflow_context={"test_mode": True}
            )

            end_time = time.time()
            response_time = end_time - start_time

            assert isinstance(result, dict)
            assert "success" in result
            assert response_time < 15.0, f"Full analysis took {response_time:.2f}s"


class TestThroughputAndConcurrency:
    """Test agent throughput and concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_complexity_analysis(self, performance_test_queries):
        """Test concurrent complexity analysis requests."""
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7}

        # Create concurrent tasks
        tasks = [
            analyze_query_complexity(query, constraints)
            for query in performance_test_queries
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = end_time - start_time

        # All should succeed
        assert all(result["success"] for result in results)

        # Concurrent execution should be faster than sequential
        assert total_time < len(performance_test_queries) * 2.0

    @pytest.mark.asyncio
    async def test_concurrent_agent_requests(self, test_dependencies, performance_config):
        """Test concurrent agent requests."""
        test_model = TestModel()
        test_agent = agent.override(model=test_model)

        queries = [
            "Analyze machine learning complexity",
            "Recommend strategy for data science research",
            "Assess risks in AI development",
            "Evaluate quantum computing research approach",
            "Strategic analysis for blockchain applications"
        ]

        # Create concurrent agent tasks
        tasks = [
            test_agent.run(query, deps=test_dependencies)
            for query in queries[:performance_config["concurrent_request_count"]]
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = end_time - start_time

        # All should succeed
        assert all(result.data is not None for result in results)

        # Should handle concurrent requests efficiently
        assert total_time < 10.0

    @pytest.mark.asyncio
    async def test_sequential_vs_concurrent_performance(self, performance_test_queries):
        """Compare sequential vs concurrent performance."""
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7}

        # Sequential execution
        sequential_start = time.time()
        sequential_results = []
        for query in performance_test_queries:
            result = await analyze_query_complexity(query, constraints)
            sequential_results.append(result)
        sequential_time = time.time() - sequential_start

        # Concurrent execution
        concurrent_start = time.time()
        tasks = [analyze_query_complexity(query, constraints) for query in performance_test_queries]
        concurrent_results = await asyncio.gather(*tasks)
        concurrent_time = time.time() - concurrent_start

        # Both should succeed
        assert all(result["success"] for result in sequential_results)
        assert all(result["success"] for result in concurrent_results)

        # Concurrent should be faster or similar (TestModel doesn't benefit much from concurrency)
        assert concurrent_time <= sequential_time * 1.2

    @pytest.mark.asyncio
    async def test_sustained_load_performance(self, performance_config):
        """Test sustained load performance over multiple iterations."""
        test_model = TestModel()
        test_agent = agent.override(model=test_model)
        test_deps = AgentDependencies(debug=False)

        query = "Sustained load test query for performance evaluation"
        iterations = performance_config["test_iterations"]
        response_times = []

        for i in range(iterations):
            start_time = time.time()

            result = await test_agent.run(f"{query} - iteration {i}", deps=test_deps)

            end_time = time.time()
            response_time = end_time - start_time

            assert result.data is not None
            response_times.append(response_time)

        # Performance should remain consistent
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0

        assert avg_time < 5.0, f"Average response time {avg_time:.2f}s too high"
        assert max_time < 10.0, f"Maximum response time {max_time:.2f}s too high"
        assert std_dev < 2.0, f"Response time variance {std_dev:.2f}s too high"


class TestPerformanceBenchmarks:
    """Test specific performance benchmarks."""

    @pytest.mark.asyncio
    async def test_complexity_scoring_precision(self, sample_queries, expected_complexity_ranges, performance_config):
        """Test complexity scoring precision meets 90% target."""
        correct_predictions = 0
        total_predictions = 0

        for query_type, query in sample_queries.items():
            if query_type in ["empty", "very_long"]:
                continue

            if query_type not in expected_complexity_ranges:
                continue

            result = await analyze_query_complexity(query, {"time_limit": 60})

            if result["success"]:
                complexity = result["complexity_metrics"]["overall_complexity"]
                expected_range = expected_complexity_ranges[query_type]

                total_predictions += 1
                if expected_range[0] <= complexity <= expected_range[1]:
                    correct_predictions += 1

        precision = correct_predictions / total_predictions if total_predictions > 0 else 0
        target_precision = performance_config["complexity_precision_target"]

        assert precision >= target_precision, \
            f"Complexity precision {precision:.2f} below target {target_precision}"

    @pytest.mark.asyncio
    async def test_time_estimation_accuracy(self, sample_queries, sample_constraints, performance_config):
        """Test time estimation accuracy within 20% target."""
        accurate_estimates = 0
        total_estimates = 0

        for query_type, query in sample_queries.items():
            if query_type in ["empty", "very_long"]:
                continue

            for constraint_type, constraints in sample_constraints.items():
                complexity_result = await analyze_query_complexity(query, constraints)

                if complexity_result["success"]:
                    strategy_result = await recommend_research_strategy(
                        complexity_result["complexity_metrics"],
                        constraints
                    )

                    if strategy_result["success"]:
                        estimated_duration = strategy_result["strategy_recommendation"]["estimated_duration"]
                        time_limit = constraints["time_limit"]

                        total_estimates += 1

                        # Check if estimate is within 20% of time limit or reasonable base expectations
                        base_expectations = {
                            "simple": 15,
                            "moderate": 45,
                            "complex": 90,
                            "technical": 75,
                            "interdisciplinary": 60,
                            "temporal": 70
                        }

                        expected_duration = base_expectations.get(query_type, 45)
                        if time_limit < expected_duration:
                            expected_duration = time_limit

                        accuracy_ratio = abs(estimated_duration - expected_duration) / expected_duration
                        target_accuracy = performance_config["time_estimate_accuracy"]

                        if accuracy_ratio <= target_accuracy:
                            accurate_estimates += 1

        accuracy = accurate_estimates / total_estimates if total_estimates > 0 else 0

        assert accuracy >= 0.6, f"Time estimation accuracy {accuracy:.2f} below reasonable threshold"

    @pytest.mark.asyncio
    async def test_memory_usage_efficiency(self, test_dependencies_with_history):
        """Test memory usage efficiency with historical data."""
        test_model = TestModel()
        test_agent = agent.override(model=test_model)

        # Baseline memory state
        initial_history_size = len(test_dependencies_with_history.historical_strategies or [])

        # Perform multiple operations
        queries = [
            "Memory test query 1",
            "Memory test query 2",
            "Memory test query 3"
        ]

        for query in queries:
            result = await test_agent.run(query, deps=test_dependencies_with_history)
            assert result.data is not None

            # Simulate updating historical context
            test_dependencies_with_history.update_historical_context({
                "query": query,
                "strategy": "test_strategy",
                "success": True,
                "duration": 30
            })

        # Memory usage should be controlled
        final_history_size = len(test_dependencies_with_history.historical_strategies)

        # Should have added entries but not grow unbounded
        assert final_history_size >= initial_history_size
        assert final_history_size <= 100  # Should respect the limit

    @pytest.mark.asyncio
    async def test_cache_performance_impact(self, test_dependencies):
        """Test performance impact of caching system."""
        test_model = TestModel()
        test_agent = agent.override(model=test_model)
        test_dependencies.debug = True

        query = "Cache performance test query about machine learning"

        # First run - no cache
        start_time = time.time()
        result1 = await test_agent.run(f"Analyze: {query}", deps=test_dependencies)
        first_run_time = time.time() - start_time

        # Second run - with cache
        start_time = time.time()
        result2 = await test_agent.run(f"Analyze: {query}", deps=test_dependencies)
        second_run_time = time.time() - start_time

        assert result1.data is not None
        assert result2.data is not None

        # Cache should be used in second run
        cached_score = test_dependencies.get_cached_complexity(query)
        assert cached_score is not None

        # Both runs should be fast with TestModel, but second might be slightly faster
        assert first_run_time < 5.0
        assert second_run_time < 5.0


class TestScalabilityMetrics:
    """Test scalability and load characteristics."""

    @pytest.mark.asyncio
    async def test_query_length_scalability(self):
        """Test performance across different query lengths."""
        base_query = "machine learning research complexity analysis"

        # Test different query lengths
        length_multipliers = [1, 5, 10, 20]
        response_times = []

        for multiplier in length_multipliers:
            long_query = (base_query + " ") * multiplier

            start_time = time.time()
            result = await analyze_query_complexity(long_query, {"time_limit": 60})
            end_time = time.time()

            response_time = end_time - start_time
            response_times.append(response_time)

            assert result["success"] is True

        # Response time should scale reasonably with query length
        # Longer queries shouldn't cause exponential slowdown
        for i in range(1, len(response_times)):
            ratio = response_times[i] / response_times[0]
            assert ratio < length_multipliers[i] * 0.5, \
                f"Response time scaling ratio {ratio:.2f} too high for length multiplier {length_multipliers[i]}"

    @pytest.mark.asyncio
    async def test_complexity_range_performance(self):
        """Test performance consistency across complexity ranges."""
        queries_by_complexity = {
            "simple": "What is AI?",
            "moderate": "How do neural networks process information for pattern recognition?",
            "complex": "What are the theoretical foundations and practical implications of quantum machine learning algorithms in the context of cryptographic security and distributed computing systems?"
        }

        response_times = {}

        for complexity_level, query in queries_by_complexity.items():
            start_time = time.time()
            result = await analyze_query_complexity(query, {"time_limit": 60})
            end_time = time.time()

            response_times[complexity_level] = end_time - start_time

            assert result["success"] is True

        # All complexity levels should perform within reasonable bounds
        for level, response_time in response_times.items():
            assert response_time < 3.0, f"{level} query took {response_time:.2f}s"

    @pytest.mark.asyncio
    async def test_constraint_variation_performance(self, sample_constraints):
        """Test performance with different constraint configurations."""
        test_query = "Performance test query for constraint variations"

        for constraint_name, constraints in sample_constraints.items():
            start_time = time.time()

            # Run full pipeline
            complexity_result = await analyze_query_complexity(test_query, constraints)

            if complexity_result["success"]:
                strategy_result = await recommend_research_strategy(
                    complexity_result["complexity_metrics"],
                    constraints
                )

                if strategy_result["success"]:
                    risk_result = await assess_research_risks(
                        complexity_result["complexity_metrics"],
                        strategy_result,
                        constraints
                    )

            end_time = time.time()
            total_time = end_time - start_time

            # Should perform consistently regardless of constraints
            assert total_time < 5.0, f"Constraint variation {constraint_name} took {total_time:.2f}s"


class TestPerformanceRegression:
    """Test for performance regressions."""

    @pytest.mark.asyncio
    async def test_baseline_performance_metrics(self, performance_test_queries):
        """Establish baseline performance metrics."""
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7}

        metrics = {
            "complexity_analysis_times": [],
            "strategy_recommendation_times": [],
            "risk_assessment_times": [],
            "total_pipeline_times": []
        }

        for query in performance_test_queries:
            # Measure complexity analysis
            start_time = time.time()
            complexity_result = await analyze_query_complexity(query, constraints)
            complexity_time = time.time() - start_time
            metrics["complexity_analysis_times"].append(complexity_time)

            if complexity_result["success"]:
                # Measure strategy recommendation
                start_time = time.time()
                strategy_result = await recommend_research_strategy(
                    complexity_result["complexity_metrics"],
                    constraints
                )
                strategy_time = time.time() - start_time
                metrics["strategy_recommendation_times"].append(strategy_time)

                if strategy_result["success"]:
                    # Measure risk assessment
                    start_time = time.time()
                    risk_result = await assess_research_risks(
                        complexity_result["complexity_metrics"],
                        strategy_result,
                        constraints
                    )
                    risk_time = time.time() - start_time
                    metrics["risk_assessment_times"].append(risk_time)

                    # Total pipeline time
                    total_time = complexity_time + strategy_time + risk_time
                    metrics["total_pipeline_times"].append(total_time)

        # Baseline expectations (these should not regress)
        avg_complexity_time = statistics.mean(metrics["complexity_analysis_times"])
        avg_strategy_time = statistics.mean(metrics["strategy_recommendation_times"])
        avg_risk_time = statistics.mean(metrics["risk_assessment_times"])
        avg_total_time = statistics.mean(metrics["total_pipeline_times"])

        assert avg_complexity_time < 1.0, f"Complexity analysis baseline: {avg_complexity_time:.2f}s"
        assert avg_strategy_time < 0.5, f"Strategy recommendation baseline: {avg_strategy_time:.2f}s"
        assert avg_risk_time < 0.3, f"Risk assessment baseline: {avg_risk_time:.2f}s"
        assert avg_total_time < 2.0, f"Total pipeline baseline: {avg_total_time:.2f}s"

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test performance under sustained load."""
        query = "Load test query for performance validation"
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7}

        # Simulate sustained load
        load_duration = 10  # seconds
        start_load_time = time.time()
        completed_requests = 0
        response_times = []

        while time.time() - start_load_time < load_duration:
            request_start = time.time()

            result = await analyze_query_complexity(query, constraints)

            request_end = time.time()
            response_time = request_end - request_start
            response_times.append(response_time)

            assert result["success"] is True
            completed_requests += 1

        # Performance metrics under load
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        requests_per_second = completed_requests / load_duration

        # Performance should remain reasonable under load
        assert avg_response_time < 2.0, f"Average response time under load: {avg_response_time:.2f}s"
        assert max_response_time < 5.0, f"Maximum response time under load: {max_response_time:.2f}s"
        assert requests_per_second > 1.0, f"Throughput under load: {requests_per_second:.2f} req/s"