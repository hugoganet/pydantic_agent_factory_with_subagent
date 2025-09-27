"""
Tools for Query Strategy Agent.
Analytical tools for complexity assessment, strategy recommendation, and risk analysis.
"""

import re
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import asdict
import time

logger = logging.getLogger(__name__)

# Simple NLP utilities (avoiding external dependencies for now)
def count_technical_terms(text: str) -> int:
    """Count technical terminology indicators in text."""
    technical_patterns = [
        r'\b\w+(?:ing|tion|ity|ism|ology|graphy|metry)\b',  # Suffix patterns
        r'\b[A-Z]+[a-z]*\b',  # Capitalized terms
        r'\b\w*(?:analysis|research|study|method|technique|approach|model|theory)\w*\b'  # Domain terms
    ]

    count = 0
    text_lower = text.lower()
    for pattern in technical_patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        count += len(matches)

    return count

def estimate_concept_count(text: str) -> int:
    """Estimate number of distinct concepts in the query."""
    # Simple heuristic: unique nouns and key terms
    words = re.findall(r'\b\w+\b', text.lower())

    # Filter for likely concept words (nouns, domain terms)
    concept_indicators = set()
    for word in words:
        if len(word) > 3 and word not in ['this', 'that', 'with', 'from', 'they', 'have', 'been', 'will', 'what', 'when', 'where', 'why', 'how']:
            concept_indicators.add(word)

    return len(concept_indicators)

def detect_temporal_scope(text: str) -> float:
    """Detect temporal complexity indicators."""
    temporal_patterns = [
        r'\b(?:historical|history|past|previous|former|ancient|medieval|modern)\b',
        r'\b(?:trend|evolution|change|development|progress)\b',
        r'\b(?:future|predict|forecast|upcoming|next|later)\b',
        r'\b(?:century|decade|year|period|era|age)\b',
        r'\b\d{4}\b',  # Years
        r'\b(?:before|after|during|since|until|from.*to)\b'
    ]

    score = 0
    text_lower = text.lower()
    for pattern in temporal_patterns:
        matches = re.findall(pattern, text_lower)
        score += len(matches) * 0.5

    return min(score, 3.0)  # Cap at 3.0

def detect_interdisciplinary_factors(text: str) -> float:
    """Detect cross-disciplinary complexity indicators."""
    domain_terms = {
        'science': ['physics', 'chemistry', 'biology', 'mathematics', 'statistics'],
        'technology': ['software', 'hardware', 'digital', 'computer', 'algorithm', 'data'],
        'social': ['psychology', 'sociology', 'anthropology', 'culture', 'society'],
        'business': ['market', 'economic', 'financial', 'business', 'commerce', 'industry'],
        'policy': ['government', 'policy', 'regulation', 'law', 'legal', 'political'],
        'health': ['medical', 'health', 'clinical', 'patient', 'treatment', 'disease']
    }

    text_lower = text.lower()
    detected_domains = set()

    for domain, terms in domain_terms.items():
        for term in terms:
            if term in text_lower:
                detected_domains.add(domain)
                break

    # Score based on number of domains detected
    domain_count = len(detected_domains)
    if domain_count <= 1:
        return 1.0
    elif domain_count == 2:
        return 3.0
    elif domain_count == 3:
        return 6.0
    else:
        return 8.0

async def analyze_query_complexity(
    research_query: str,
    constraints: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyzes research query complexity using NLP techniques to extract complexity indicators.

    Args:
        research_query: The research question/task to analyze
        constraints: Research constraints including time_limit, source_limit, quality_threshold

    Returns:
        Dictionary containing complexity metrics and analysis details
    """
    start_time = time.time()

    try:
        if not research_query or not research_query.strip():
            raise ValueError("Research query cannot be empty")

        query = research_query.strip()

        # Basic text analysis
        word_count = len(query.split())
        char_count = len(query)
        sentence_count = len(re.split(r'[.!?]+', query))

        # Complexity scoring (1-10 scale)
        # Scope Score: Based on query length and breadth
        scope_base = min(word_count / 10, 5.0)  # Base score from word count
        concept_count = estimate_concept_count(query)
        scope_score = min(scope_base + (concept_count * 0.3), 10.0)

        # Technical Difficulty: Based on terminology density
        tech_terms = count_technical_terms(query)
        tech_density = tech_terms / max(word_count, 1)
        technical_difficulty = min(1.0 + (tech_density * 15), 10.0)

        # Data Availability: Heuristic based on query type
        question_words = ['what', 'how', 'why', 'when', 'where', 'who']
        has_question_words = any(word in query.lower() for word in question_words)
        specific_terms = count_technical_terms(query)

        if has_question_words and specific_terms > 2:
            data_availability = 6.0  # Moderate - specific questions might have limited sources
        elif 'recent' in query.lower() or 'latest' in query.lower():
            data_availability = 4.0  # Lower - recent info may be scarce
        else:
            data_availability = 7.0  # Higher - general topics usually have more sources

        # Interdisciplinary Factor
        interdisciplinary_factor = detect_interdisciplinary_factors(query)

        # Temporal complexity
        temporal_complexity = detect_temporal_scope(query)
        technical_difficulty += temporal_complexity
        technical_difficulty = min(technical_difficulty, 10.0)

        # Overall complexity (weighted average)
        overall_complexity = (
            scope_score * 0.3 +
            technical_difficulty * 0.3 +
            data_availability * 0.2 +
            interdisciplinary_factor * 0.2
        )

        # Identify key concepts and technical terms
        identified_concepts = list(set(re.findall(r'\b\w{4,}\b', query.lower())))[:10]  # Limit to 10
        technical_terms_list = []

        # Simple technical term extraction
        tech_pattern = r'\b\w+(?:ing|tion|ity|ism|ology|graphy|metry|analysis|research|study|method)\b'
        technical_terms_list = list(set(re.findall(tech_pattern, query.lower(), re.IGNORECASE)))[:5]

        # Complexity indicators
        complexity_indicators = []
        if word_count > 20:
            complexity_indicators.append("long query")
        if concept_count > 5:
            complexity_indicators.append("multiple concepts")
        if tech_terms > 3:
            complexity_indicators.append("technical terminology")
        if interdisciplinary_factor > 3:
            complexity_indicators.append("interdisciplinary")
        if temporal_complexity > 1:
            complexity_indicators.append("temporal complexity")
        if '?' in query and sentence_count > 1:
            complexity_indicators.append("multi-part question")

        # Estimate sources needed
        if overall_complexity < 3:
            estimated_sources = 1
        elif overall_complexity < 6:
            estimated_sources = 3
        elif overall_complexity < 8:
            estimated_sources = 5
        else:
            estimated_sources = 8

        processing_time = time.time() - start_time

        return {
            "success": True,
            "complexity_metrics": {
                "scope_score": round(scope_score, 1),
                "technical_difficulty": round(technical_difficulty, 1),
                "data_availability": round(data_availability, 1),
                "interdisciplinary_factor": round(interdisciplinary_factor, 1),
                "overall_complexity": round(overall_complexity, 1)
            },
            "analysis_details": {
                "identified_concepts": identified_concepts,
                "technical_terms": technical_terms_list,
                "complexity_indicators": complexity_indicators,
                "estimated_sources_needed": estimated_sources,
                "word_count": word_count,
                "concept_count": concept_count
            },
            "processing_time": round(processing_time, 2)
        }

    except ValueError as e:
        logger.error(f"Input validation error in complexity analysis: {e}")
        return {
            "success": False,
            "error": f"Invalid input: {str(e)}",
            "error_type": "validation"
        }
    except Exception as e:
        logger.error(f"Unexpected error in complexity analysis: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "internal"
        }

async def recommend_research_strategy(
    complexity_metrics: Dict[str, float],
    constraints: Dict[str, Any],
    historical_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Recommends optimal research strategy based on complexity assessment and constraints.

    Args:
        complexity_metrics: Output from analyze_query_complexity
        constraints: Research constraints (time_limit, source_limit, quality_threshold)
        historical_data: Optional performance data from previous similar queries

    Returns:
        Dictionary containing strategy recommendation and execution plan
    """
    start_time = time.time()

    try:
        if not complexity_metrics or "overall_complexity" not in complexity_metrics:
            raise ValueError("Valid complexity metrics required")

        overall_complexity = complexity_metrics["overall_complexity"]

        # Extract constraints with defaults
        time_limit = constraints.get("time_limit", 60)  # minutes
        source_limit = constraints.get("source_limit", 10)
        quality_threshold = constraints.get("quality_threshold", 0.7)

        # Strategy Selection Logic
        if overall_complexity < 3.0:
            strategy_type = "simple_direct"
            base_duration = 15
            recommended_sources = min(2, source_limit)
            phases = ["search", "validate"]
            parallel_groups = [["search_primary", "search_secondary"]]

        elif overall_complexity <= 7.0:
            strategy_type = "moderate_multisource"
            base_duration = 45
            recommended_sources = min(5, source_limit)
            phases = ["research", "analysis", "synthesis"]
            parallel_groups = [
                ["web_search", "database_search"],
                ["source_validation", "content_extraction"],
                ["analysis_tasks"]
            ]

        else:
            strategy_type = "complex_iterative"
            base_duration = 90
            recommended_sources = min(8, source_limit)
            phases = ["initial_research", "deep_analysis", "cross_validation", "synthesis", "review"]
            parallel_groups = [
                ["broad_search", "targeted_search", "expert_sources"],
                ["fact_checking", "credibility_assessment"],
                ["synthesis_tasks", "citation_management"]
            ]

        # Adjust for constraints
        if time_limit < base_duration:
            # Time-constrained adjustments
            if strategy_type == "complex_iterative":
                strategy_type = "moderate_multisource"
                phases = ["research", "analysis", "synthesis"]
                recommended_sources = min(4, source_limit)
                base_duration = min(time_limit, 45)
            elif strategy_type == "moderate_multisource" and time_limit < 30:
                strategy_type = "simple_direct"
                phases = ["search", "validate"]
                recommended_sources = min(2, source_limit)
                base_duration = min(time_limit, 20)

        estimated_duration = min(base_duration, time_limit)

        # Calculate time per phase
        if len(phases) == 2:
            time_allocation = {"search": 0.6, "validate": 0.4}
        elif len(phases) == 3:
            time_allocation = {"research": 0.4, "analysis": 0.35, "synthesis": 0.25}
        else:
            # Equal distribution for complex strategies
            time_per_phase = 1.0 / len(phases)
            time_allocation = {phase: time_per_phase for phase in phases}

        time_per_phase = {
            phase: int(estimated_duration * allocation)
            for phase, allocation in time_allocation.items()
        }

        # Fallback strategies
        fallback_strategies = []
        if strategy_type != "simple_direct":
            fallback_strategies.append("reduce_scope")
        if estimated_duration == time_limit:
            fallback_strategies.append("extend_timeline")
        if recommended_sources == source_limit:
            fallback_strategies.append("prioritize_sources")
        if quality_threshold > 0.8:
            fallback_strategies.append("adjust_quality_threshold")

        # Quality checkpoints
        quality_checkpoints = []
        if "research" in phases:
            quality_checkpoints.append({
                "phase": "research",
                "criteria": "minimum_sources_found",
                "threshold": max(2, recommended_sources // 2)
            })
        if "analysis" in phases:
            quality_checkpoints.append({
                "phase": "analysis",
                "criteria": "quality_threshold_met",
                "threshold": quality_threshold
            })

        # Confidence scoring
        confidence_factors = []
        base_confidence = 0.7

        # Adjust confidence based on constraints alignment
        if time_limit >= base_duration:
            confidence_factors.append(0.1)  # Adequate time
        if source_limit >= recommended_sources:
            confidence_factors.append(0.1)  # Adequate sources
        if quality_threshold <= 0.8:
            confidence_factors.append(0.05)  # Reasonable quality bar

        # Historical data influence
        if historical_data and "success_rate" in historical_data:
            historical_success = historical_data["success_rate"]
            confidence_factors.append((historical_success - 0.5) * 0.1)

        confidence_score = min(base_confidence + sum(confidence_factors), 1.0)

        # Strategy reasoning
        reasoning_parts = [
            f"Query complexity ({overall_complexity:.1f}) indicates {strategy_type.replace('_', ' ')} approach."
        ]

        if time_limit < base_duration:
            reasoning_parts.append(f"Time constraint ({time_limit}min) requires streamlined execution.")
        if source_limit < recommended_sources:
            reasoning_parts.append(f"Source limit ({source_limit}) requires selective sourcing.")

        reasoning = " ".join(reasoning_parts)

        processing_time = time.time() - start_time

        return {
            "success": True,
            "strategy_recommendation": {
                "recommended_strategy": strategy_type,
                "reasoning": reasoning,
                "confidence_score": round(confidence_score, 2),
                "estimated_duration": estimated_duration
            },
            "execution_plan": {
                "phases": phases,
                "parallel_groups": parallel_groups,
                "fallback_strategies": fallback_strategies,
                "quality_checkpoints": quality_checkpoints
            },
            "resource_allocation": {
                "time_per_phase": time_per_phase,
                "recommended_sources": recommended_sources,
                "parallel_capacity": len(parallel_groups[0]) if parallel_groups else 1
            },
            "processing_time": round(processing_time, 2)
        }

    except ValueError as e:
        logger.error(f"Input validation error in strategy recommendation: {e}")
        return {
            "success": False,
            "error": f"Invalid input: {str(e)}",
            "error_type": "validation"
        }
    except Exception as e:
        logger.error(f"Unexpected error in strategy recommendation: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "internal"
        }

async def assess_research_risks(
    complexity_metrics: Dict[str, float],
    strategy_plan: Dict[str, Any],
    constraints: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Identifies potential risks and provides mitigation strategies for research execution.

    Args:
        complexity_metrics: Complexity analysis results
        strategy_plan: Recommended strategy and execution plan
        constraints: Research constraints and requirements

    Returns:
        Dictionary containing risk assessment and mitigation strategies
    """
    start_time = time.time()

    try:
        if not complexity_metrics or not strategy_plan:
            raise ValueError("Complexity metrics and strategy plan are required")

        overall_complexity = complexity_metrics.get("overall_complexity", 5.0)
        data_availability = complexity_metrics.get("data_availability", 5.0)
        technical_difficulty = complexity_metrics.get("technical_difficulty", 5.0)

        estimated_duration = strategy_plan.get("strategy_recommendation", {}).get("estimated_duration", 60)
        recommended_sources = strategy_plan.get("resource_allocation", {}).get("recommended_sources", 5)

        time_limit = constraints.get("time_limit", 60)
        source_limit = constraints.get("source_limit", 10)
        quality_threshold = constraints.get("quality_threshold", 0.7)

        risks = {}

        # Data Availability Risk
        data_risk_prob = max(0.1, min(0.9, (10 - data_availability) / 10))
        data_risk_impact = 7 if recommended_sources > 3 else 5
        risks["data_availability"] = {
            "probability": round(data_risk_prob, 2),
            "impact": data_risk_impact,
            "priority": round(data_risk_prob * data_risk_impact, 1)
        }

        # Time Constraint Risk
        time_buffer = time_limit - estimated_duration
        time_risk_prob = max(0.1, min(0.9, 1 - (time_buffer / max(estimated_duration, 1))))
        time_risk_impact = 8 if overall_complexity > 7 else 6
        risks["time_constraint"] = {
            "probability": round(time_risk_prob, 2),
            "impact": time_risk_impact,
            "priority": round(time_risk_prob * time_risk_impact, 1)
        }

        # Quality Risk
        quality_risk_prob = max(0.1, min(0.8, quality_threshold))  # Higher threshold = higher risk
        quality_risk_impact = 6
        if technical_difficulty > 7:
            quality_risk_prob += 0.2  # Technical queries have quality challenges
        risks["quality_risk"] = {
            "probability": round(min(quality_risk_prob, 0.9), 2),
            "impact": quality_risk_impact,
            "priority": round(quality_risk_prob * quality_risk_impact, 1)
        }

        # Scope Creep Risk
        scope_risk_prob = max(0.1, overall_complexity / 10 * 0.6)
        scope_risk_impact = 5
        if "interdisciplinary" in complexity_metrics.get("analysis_details", {}).get("complexity_indicators", []):
            scope_risk_prob += 0.2
        risks["scope_creep"] = {
            "probability": round(min(scope_risk_prob, 0.8), 2),
            "impact": scope_risk_impact,
            "priority": round(scope_risk_prob * scope_risk_impact, 1)
        }

        # Technical Risk (for highly technical queries)
        if technical_difficulty > 7:
            tech_risk_prob = min(0.7, technical_difficulty / 10)
            risks["technical_risk"] = {
                "probability": round(tech_risk_prob, 2),
                "impact": 7,
                "priority": round(tech_risk_prob * 7, 1)
            }

        # Overall risk level
        max_priority = max(risk["priority"] for risk in risks.values())
        if max_priority > 6:
            overall_risk_level = "high"
        elif max_priority > 3:
            overall_risk_level = "medium"
        else:
            overall_risk_level = "low"

        # Critical risks (priority > 4)
        critical_risks = [risk_type for risk_type, risk_data in risks.items() if risk_data["priority"] > 4.0]

        # Mitigation strategies
        mitigation_strategies = {
            "time_constraint": "Implement phased approach with early quality checkpoints and scope reduction options",
            "data_availability": "Prepare alternative sources, expand search parameters, and consider expert consultation",
            "quality_risk": "Set intermediate quality validation steps and multiple source verification",
            "scope_creep": "Define clear research boundaries with regular scope validation checkpoints",
            "technical_risk": "Engage domain experts and use authoritative technical sources"
        }

        # Contingency plans
        contingency_plans = {
            "high_risk_scenario": "Reduce scope to core objectives and focus on highest-confidence findings",
            "resource_shortage": "Prioritize highest-impact sources and streamline analysis process",
            "time_overrun": "Implement rapid synthesis with executive summary of key findings",
            "quality_shortfall": "Extend validation phase and increase source diversity"
        }

        processing_time = time.time() - start_time

        return {
            "success": True,
            "risk_assessment": {
                "overall_risk_level": overall_risk_level,
                "critical_risks": critical_risks,
                "risk_scores": risks
            },
            "mitigation_strategies": {
                risk_type: mitigation_strategies.get(risk_type, "Monitor and adjust approach as needed")
                for risk_type in risks.keys()
            },
            "contingency_plans": contingency_plans,
            "processing_time": round(processing_time, 2)
        }

    except ValueError as e:
        logger.error(f"Input validation error in risk assessment: {e}")
        return {
            "success": False,
            "error": f"Invalid input: {str(e)}",
            "error_type": "validation"
        }
    except Exception as e:
        logger.error(f"Unexpected error in risk assessment: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "internal"
        }