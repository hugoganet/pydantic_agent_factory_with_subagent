"""
Unit tests for Query Strategy Agent analytical tools.
Tests the core NLP and analysis functions independently.
"""

import pytest
import asyncio
from typing import Dict, Any

from ..tools import (
    analyze_query_complexity,
    recommend_research_strategy,
    assess_research_risks,
    count_technical_terms,
    estimate_concept_count,
    detect_temporal_scope,
    detect_interdisciplinary_factors
)


class TestNLPUtilities:
    """Test NLP utility functions."""

    def test_count_technical_terms(self):
        """Test technical term counting."""
        # Technical text
        technical_text = "Machine learning algorithms require statistical analysis and computational optimization"
        count = count_technical_terms(technical_text)
        assert count > 3

        # Non-technical text
        simple_text = "The cat sat on the mat"
        count = count_technical_terms(simple_text)
        assert count <= 1

        # Empty text
        assert count_technical_terms("") == 0

    def test_estimate_concept_count(self):
        """Test concept counting estimation."""
        # Multi-concept query
        complex_query = "artificial intelligence machine learning neural networks deep learning"
        count = estimate_concept_count(complex_query)
        assert count >= 4

        # Simple query
        simple_query = "what is cat"
        count = estimate_concept_count(simple_query)
        assert count <= 2

        # Empty query
        assert estimate_concept_count("") == 0

    def test_detect_temporal_scope(self):
        """Test temporal complexity detection."""
        # Historical query
        historical = "What happened in 1960 during the historical period"
        score = detect_temporal_scope(historical)
        assert score > 1.0

        # Future query
        future = "What will happen in the future next decade"
        score = detect_temporal_scope(future)
        assert score > 0.5

        # Non-temporal query
        present = "What is the current state"
        score = detect_temporal_scope(present)
        assert score >= 0.0

    def test_detect_interdisciplinary_factors(self):
        """Test interdisciplinary detection."""
        # Single domain
        single = "What is machine learning algorithm performance"
        score = detect_interdisciplinary_factors(single)
        assert score <= 3.0

        # Multi-domain
        multi = "How does psychology influence economic business market decisions"
        score = detect_interdisciplinary_factors(multi)
        assert score > 3.0

        # Empty
        assert detect_interdisciplinary_factors("") == 1.0


class TestComplexityAnalysis:
    """Test query complexity analysis tool."""

    @pytest.mark.asyncio
    async def test_analyze_simple_query(self, sample_queries, expected_complexity_ranges):
        """Test complexity analysis for simple queries."""
        result = await analyze_query_complexity(
            sample_queries["simple"],
            {"time_limit": 60}
        )

        assert result["success"] is True
        assert "complexity_metrics" in result
        assert "overall_complexity" in result["complexity_metrics"]

        complexity = result["complexity_metrics"]["overall_complexity"]
        expected_range = expected_complexity_ranges["simple"]
        assert expected_range[0] <= complexity <= expected_range[1]

    @pytest.mark.asyncio
    async def test_analyze_complex_query(self, sample_queries, expected_complexity_ranges):
        """Test complexity analysis for complex queries."""
        result = await analyze_query_complexity(
            sample_queries["complex"],
            {"time_limit": 60}
        )

        assert result["success"] is True
        complexity = result["complexity_metrics"]["overall_complexity"]
        expected_range = expected_complexity_ranges["complex"]
        assert expected_range[0] <= complexity <= expected_range[1]

    @pytest.mark.asyncio
    async def test_analyze_technical_query(self, sample_queries, expected_complexity_ranges):
        """Test complexity analysis for technical queries."""
        result = await analyze_query_complexity(
            sample_queries["technical"],
            {"time_limit": 90}
        )

        assert result["success"] is True
        complexity = result["complexity_metrics"]["overall_complexity"]
        expected_range = expected_complexity_ranges["technical"]
        assert expected_range[0] <= complexity <= expected_range[1]

        # Technical queries should have high technical_difficulty
        assert result["complexity_metrics"]["technical_difficulty"] > 6.0

    @pytest.mark.asyncio
    async def test_analyze_interdisciplinary_query(self, sample_queries, expected_complexity_ranges):
        """Test complexity analysis for interdisciplinary queries."""
        result = await analyze_query_complexity(
            sample_queries["interdisciplinary"],
            {"time_limit": 90}
        )

        assert result["success"] is True
        complexity = result["complexity_metrics"]["overall_complexity"]
        expected_range = expected_complexity_ranges["interdisciplinary"]
        assert expected_range[0] <= complexity <= expected_range[1]

        # Should detect interdisciplinary indicators
        assert "interdisciplinary" in result["analysis_details"]["complexity_indicators"]

    @pytest.mark.asyncio
    async def test_complexity_consistency(self, sample_queries):
        """Test that complexity analysis is consistent for the same query."""
        query = sample_queries["moderate"]
        constraints = {"time_limit": 60}

        # Run analysis multiple times
        results = []
        for _ in range(3):
            result = await analyze_query_complexity(query, constraints)
            results.append(result["complexity_metrics"]["overall_complexity"])

        # All results should be identical (deterministic)
        assert all(score == results[0] for score in results)

    @pytest.mark.asyncio
    async def test_complexity_error_handling(self):
        """Test error handling in complexity analysis."""
        # Empty query
        result = await analyze_query_complexity("", {})
        assert result["success"] is False
        assert result["error_type"] == "validation"

        # None query
        result = await analyze_query_complexity(None, {})
        assert result["success"] is False
        assert result["error_type"] == "validation"

    @pytest.mark.asyncio
    async def test_complexity_metrics_structure(self, sample_queries):
        """Test that complexity metrics have expected structure."""
        result = await analyze_query_complexity(
            sample_queries["moderate"],
            {"time_limit": 60}
        )

        assert result["success"] is True

        # Check required metrics
        metrics = result["complexity_metrics"]
        required_metrics = [
            "scope_score", "technical_difficulty", "data_availability",
            "interdisciplinary_factor", "overall_complexity"
        ]
        for metric in required_metrics:
            assert metric in metrics
            assert 1.0 <= metrics[metric] <= 10.0

        # Check analysis details
        details = result["analysis_details"]
        required_details = [
            "identified_concepts", "technical_terms", "complexity_indicators",
            "estimated_sources_needed", "word_count", "concept_count"
        ]
        for detail in required_details:
            assert detail in details

    @pytest.mark.asyncio
    async def test_processing_time_tracking(self, sample_queries):
        """Test that processing time is tracked."""
        result = await analyze_query_complexity(
            sample_queries["moderate"],
            {"time_limit": 60}
        )

        assert result["success"] is True
        assert "processing_time" in result
        assert isinstance(result["processing_time"], (int, float))
        assert result["processing_time"] > 0


class TestStrategyRecommendation:
    """Test research strategy recommendation tool."""

    @pytest.mark.asyncio
    async def test_simple_strategy_recommendation(self):
        """Test strategy recommendation for simple complexity."""
        complexity_metrics = {
            "overall_complexity": 2.5,
            "scope_score": 2.0,
            "technical_difficulty": 2.5,
            "data_availability": 8.0,
            "interdisciplinary_factor": 1.0
        }
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7}

        result = await recommend_research_strategy(complexity_metrics, constraints)

        assert result["success"] is True
        assert result["strategy_recommendation"]["recommended_strategy"] == "simple_direct"
        assert result["strategy_recommendation"]["estimated_duration"] <= 30
        assert len(result["execution_plan"]["phases"]) == 2

    @pytest.mark.asyncio
    async def test_moderate_strategy_recommendation(self):
        """Test strategy recommendation for moderate complexity."""
        complexity_metrics = {
            "overall_complexity": 5.2,
            "scope_score": 5.0,
            "technical_difficulty": 5.5,
            "data_availability": 6.0,
            "interdisciplinary_factor": 4.0
        }
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7}

        result = await recommend_research_strategy(complexity_metrics, constraints)

        assert result["success"] is True
        assert result["strategy_recommendation"]["recommended_strategy"] == "moderate_multisource"
        assert 30 <= result["strategy_recommendation"]["estimated_duration"] <= 60
        assert len(result["execution_plan"]["phases"]) == 3

    @pytest.mark.asyncio
    async def test_complex_strategy_recommendation(self):
        """Test strategy recommendation for complex queries."""
        complexity_metrics = {
            "overall_complexity": 8.1,
            "scope_score": 8.0,
            "technical_difficulty": 8.5,
            "data_availability": 5.0,
            "interdisciplinary_factor": 8.0
        }
        constraints = {"time_limit": 120, "source_limit": 15, "quality_threshold": 0.8}

        result = await recommend_research_strategy(complexity_metrics, constraints)

        assert result["success"] is True
        assert result["strategy_recommendation"]["recommended_strategy"] == "complex_iterative"
        assert result["strategy_recommendation"]["estimated_duration"] >= 60
        assert len(result["execution_plan"]["phases"]) >= 4

    @pytest.mark.asyncio
    async def test_time_constrained_strategy(self):
        """Test strategy adjustment for time constraints."""
        complexity_metrics = {"overall_complexity": 8.0}
        constraints = {"time_limit": 20, "source_limit": 5, "quality_threshold": 0.7}

        result = await recommend_research_strategy(complexity_metrics, constraints)

        assert result["success"] is True
        # Should downgrade strategy due to time constraint
        assert result["strategy_recommendation"]["recommended_strategy"] != "complex_iterative"
        assert result["strategy_recommendation"]["estimated_duration"] <= 20

    @pytest.mark.asyncio
    async def test_historical_data_integration(self):
        """Test integration of historical data in recommendations."""
        complexity_metrics = {"overall_complexity": 5.0}
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7}
        historical_data = {
            "success_rate": 0.9,
            "avg_duration": 45
        }

        result = await recommend_research_strategy(
            complexity_metrics, constraints, historical_data
        )

        assert result["success"] is True
        # Historical success should boost confidence
        assert result["strategy_recommendation"]["confidence_score"] > 0.7

    @pytest.mark.asyncio
    async def test_strategy_confidence_scoring(self):
        """Test confidence scoring in strategy recommendations."""
        complexity_metrics = {"overall_complexity": 5.0}
        constraints = {"time_limit": 120, "source_limit": 20, "quality_threshold": 0.6}

        result = await recommend_research_strategy(complexity_metrics, constraints)

        assert result["success"] is True
        confidence = result["strategy_recommendation"]["confidence_score"]
        assert 0.0 <= confidence <= 1.0
        # Relaxed constraints should increase confidence
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_strategy_error_handling(self):
        """Test error handling in strategy recommendation."""
        # Missing complexity metrics
        result = await recommend_research_strategy({}, {"time_limit": 60})
        assert result["success"] is False
        assert result["error_type"] == "validation"

        # Invalid complexity metrics
        result = await recommend_research_strategy(
            {"overall_complexity": "invalid"}, {"time_limit": 60}
        )
        assert result["success"] is False


class TestRiskAssessment:
    """Test research risk assessment tool."""

    @pytest.mark.asyncio
    async def test_basic_risk_assessment(self):
        """Test basic risk assessment functionality."""
        complexity_metrics = {
            "overall_complexity": 6.0,
            "data_availability": 5.0,
            "technical_difficulty": 7.0
        }
        strategy_plan = {
            "strategy_recommendation": {"estimated_duration": 45},
            "resource_allocation": {"recommended_sources": 5}
        }
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.8}

        result = await assess_research_risks(complexity_metrics, strategy_plan, constraints)

        assert result["success"] is True
        assert "risk_assessment" in result
        assert "mitigation_strategies" in result
        assert "contingency_plans" in result

    @pytest.mark.asyncio
    async def test_high_risk_scenario(self):
        """Test risk assessment for high-risk scenarios."""
        complexity_metrics = {
            "overall_complexity": 9.0,
            "data_availability": 3.0,  # Low availability
            "technical_difficulty": 9.5
        }
        strategy_plan = {
            "strategy_recommendation": {"estimated_duration": 90},
            "resource_allocation": {"recommended_sources": 8}
        }
        constraints = {"time_limit": 60, "source_limit": 5, "quality_threshold": 0.9}

        result = await assess_research_risks(complexity_metrics, strategy_plan, constraints)

        assert result["success"] is True
        assert result["risk_assessment"]["overall_risk_level"] == "high"
        assert len(result["risk_assessment"]["critical_risks"]) > 0

    @pytest.mark.asyncio
    async def test_low_risk_scenario(self):
        """Test risk assessment for low-risk scenarios."""
        complexity_metrics = {
            "overall_complexity": 2.0,
            "data_availability": 9.0,
            "technical_difficulty": 2.0
        }
        strategy_plan = {
            "strategy_recommendation": {"estimated_duration": 15},
            "resource_allocation": {"recommended_sources": 2}
        }
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.6}

        result = await assess_research_risks(complexity_metrics, strategy_plan, constraints)

        assert result["success"] is True
        assert result["risk_assessment"]["overall_risk_level"] == "low"

    @pytest.mark.asyncio
    async def test_risk_types_coverage(self):
        """Test that all expected risk types are assessed."""
        complexity_metrics = {"overall_complexity": 5.0, "data_availability": 5.0, "technical_difficulty": 5.0}
        strategy_plan = {
            "strategy_recommendation": {"estimated_duration": 45},
            "resource_allocation": {"recommended_sources": 5}
        }
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7}

        result = await assess_research_risks(complexity_metrics, strategy_plan, constraints)

        assert result["success"] is True

        expected_risks = ["data_availability", "time_constraint", "quality_risk", "scope_creep"]
        risk_scores = result["risk_assessment"]["risk_scores"]

        for risk_type in expected_risks:
            assert risk_type in risk_scores
            assert "probability" in risk_scores[risk_type]
            assert "impact" in risk_scores[risk_type]
            assert "priority" in risk_scores[risk_type]

    @pytest.mark.asyncio
    async def test_technical_risk_detection(self):
        """Test detection of technical risks for highly technical queries."""
        complexity_metrics = {
            "overall_complexity": 8.0,
            "data_availability": 6.0,
            "technical_difficulty": 9.0,  # High technical difficulty
            "analysis_details": {
                "complexity_indicators": ["technical terminology", "interdisciplinary"]
            }
        }
        strategy_plan = {
            "strategy_recommendation": {"estimated_duration": 60},
            "resource_allocation": {"recommended_sources": 6}
        }
        constraints = {"time_limit": 90, "source_limit": 10, "quality_threshold": 0.8}

        result = await assess_research_risks(complexity_metrics, strategy_plan, constraints)

        assert result["success"] is True
        # Should detect technical risk
        assert "technical_risk" in result["risk_assessment"]["risk_scores"]

    @pytest.mark.asyncio
    async def test_mitigation_strategies(self):
        """Test that appropriate mitigation strategies are provided."""
        complexity_metrics = {"overall_complexity": 6.0, "data_availability": 4.0, "technical_difficulty": 6.0}
        strategy_plan = {
            "strategy_recommendation": {"estimated_duration": 50},
            "resource_allocation": {"recommended_sources": 5}
        }
        constraints = {"time_limit": 45, "source_limit": 8, "quality_threshold": 0.8}

        result = await assess_research_risks(complexity_metrics, strategy_plan, constraints)

        assert result["success"] is True

        mitigation = result["mitigation_strategies"]
        assert isinstance(mitigation, dict)
        assert len(mitigation) > 0

        # Each risk should have a mitigation strategy
        for risk_type in result["risk_assessment"]["risk_scores"]:
            assert risk_type in mitigation

    @pytest.mark.asyncio
    async def test_risk_assessment_error_handling(self):
        """Test error handling in risk assessment."""
        # Missing required parameters
        result = await assess_research_risks({}, {}, {})
        assert result["success"] is False
        assert result["error_type"] == "validation"

        # None parameters
        result = await assess_research_risks(None, None, None)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_contingency_plans(self):
        """Test contingency plan generation."""
        complexity_metrics = {"overall_complexity": 7.0, "data_availability": 5.0, "technical_difficulty": 7.0}
        strategy_plan = {
            "strategy_recommendation": {"estimated_duration": 60},
            "resource_allocation": {"recommended_sources": 6}
        }
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.8}

        result = await assess_research_risks(complexity_metrics, strategy_plan, constraints)

        assert result["success"] is True

        contingency = result["contingency_plans"]
        expected_plans = ["high_risk_scenario", "resource_shortage", "time_overrun", "quality_shortfall"]

        for plan in expected_plans:
            assert plan in contingency
            assert isinstance(contingency[plan], str)
            assert len(contingency[plan]) > 0


class TestToolIntegration:
    """Test integration between tools."""

    @pytest.mark.asyncio
    async def test_complexity_to_strategy_flow(self, sample_queries):
        """Test flow from complexity analysis to strategy recommendation."""
        query = sample_queries["moderate"]
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7}

        # First, analyze complexity
        complexity_result = await analyze_query_complexity(query, constraints)
        assert complexity_result["success"] is True

        # Then, recommend strategy
        strategy_result = await recommend_research_strategy(
            complexity_result["complexity_metrics"],
            constraints
        )
        assert strategy_result["success"] is True

        # Strategy should be appropriate for complexity
        complexity = complexity_result["complexity_metrics"]["overall_complexity"]
        strategy = strategy_result["strategy_recommendation"]["recommended_strategy"]

        if complexity < 3:
            assert strategy == "simple_direct"
        elif complexity <= 7:
            assert strategy == "moderate_multisource"
        else:
            assert strategy == "complex_iterative"

    @pytest.mark.asyncio
    async def test_strategy_to_risk_flow(self, sample_queries):
        """Test flow from strategy recommendation to risk assessment."""
        query = sample_queries["complex"]
        constraints = {"time_limit": 90, "source_limit": 15, "quality_threshold": 0.8}

        # Get complexity metrics
        complexity_result = await analyze_query_complexity(query, constraints)

        # Get strategy recommendation
        strategy_result = await recommend_research_strategy(
            complexity_result["complexity_metrics"],
            constraints
        )

        # Assess risks
        risk_result = await assess_research_risks(
            complexity_result["complexity_metrics"],
            strategy_result,
            constraints
        )

        assert risk_result["success"] is True

        # Risk level should align with complexity
        complexity = complexity_result["complexity_metrics"]["overall_complexity"]
        risk_level = risk_result["risk_assessment"]["overall_risk_level"]

        if complexity > 7:
            assert risk_level in ["medium", "high"]

    @pytest.mark.asyncio
    async def test_full_analysis_pipeline(self, sample_queries, sample_constraints):
        """Test complete analysis pipeline for different query types."""
        for query_type, query in sample_queries.items():
            if query_type in ["empty", "very_long"]:
                continue  # Skip invalid queries

            constraints = sample_constraints["moderate"]

            # Run full pipeline
            complexity_result = await analyze_query_complexity(query, constraints)

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

                    assert risk_result["success"] is True, f"Risk assessment failed for {query_type}"

    @pytest.mark.asyncio
    async def test_performance_across_tools(self, performance_test_queries):
        """Test performance consistency across all tools."""
        constraints = {"time_limit": 60, "source_limit": 10, "quality_threshold": 0.7}

        total_start_time = asyncio.get_event_loop().time()

        for query in performance_test_queries:
            # Run all tools
            complexity_result = await analyze_query_complexity(query, constraints)
            assert complexity_result["success"] is True

            strategy_result = await recommend_research_strategy(
                complexity_result["complexity_metrics"],
                constraints
            )
            assert strategy_result["success"] is True

            risk_result = await assess_research_risks(
                complexity_result["complexity_metrics"],
                strategy_result,
                constraints
            )
            assert risk_result["success"] is True

        total_time = asyncio.get_event_loop().time() - total_start_time

        # All tools should complete within reasonable time
        assert total_time < 5.0, f"Tool pipeline took too long: {total_time}s"