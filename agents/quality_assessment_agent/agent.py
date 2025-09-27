"""Quality Assessment Agent for evaluating source credibility and bias detection."""

import asyncio
from datetime import datetime
from typing import List, Dict, Any
import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model

from .models import ResearchSource, QualityAssessment
from .dependencies import QualityAssessmentDependencies, get_dependencies
from .providers import get_assessment_model
from .tools import (
    analyze_domain_authority,
    analyze_content_quality,
    analyze_bias_indicators,
    check_freshness
)
from .settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# System prompt for quality assessment
QUALITY_ASSESSMENT_PROMPT = """You are a Quality Assessment Agent specialized in evaluating source credibility, detecting bias, and assessing information quality. Your role is to provide objective, consistent quality scores for research sources.

Your responsibilities:
1. Evaluate source credibility based on domain authority, content quality, and author credentials
2. Detect bias indicators in language, perspective, and presentation
3. Assess content freshness and relevance
4. Provide confidence ratings for your assessments
5. Flag potential quality issues or concerns

Assessment approach:
- Be objective and consistent in your evaluations
- Consider multiple quality factors with appropriate weights
- Provide detailed reasoning for your assessments
- Flag sources that may require additional scrutiny
- Focus on factual accuracy and credibility indicators

Your assessments will be used by other agents for citation prioritization and synthesis decisions. Maintain high standards while being practical about real-world content variations."""

# Create the agent
quality_agent = Agent(
    get_assessment_model(),
    deps_type=QualityAssessmentDependencies,
    result_type=QualityAssessment,
    system_prompt=QUALITY_ASSESSMENT_PROMPT
)


@quality_agent.tool
async def assess_domain_authority(
    ctx: RunContext[QualityAssessmentDependencies],
    url: str
) -> str:
    """Assess domain authority and reputation for a given URL."""
    try:
        analysis = await analyze_domain_authority(ctx, url)
        return (
            f"Domain: {analysis.domain}\n"
            f"SSL Enabled: {analysis.ssl_enabled}\n"
            f"Domain Age Score: {analysis.domain_age_score:.2f}\n"
            f"Reputation Score: {analysis.reputation_score:.2f}\n"
            f"Authority Indicators: {', '.join(analysis.authority_indicators)}"
        )
    except Exception as e:
        logger.error(f"Domain authority assessment failed: {e}")
        return f"Domain authority assessment failed: {str(e)}"


@quality_agent.tool
async def assess_content_quality(
    ctx: RunContext[QualityAssessmentDependencies],
    content: str,
    title: str = ""
) -> str:
    """Assess content quality indicators including structure, citations, and completeness."""
    try:
        analysis = await analyze_content_quality(ctx, content, title)
        return (
            f"Word Count: {analysis.word_count}\n"
            f"Structure Score: {analysis.structure_score:.2f}\n"
            f"Citation Count: {analysis.citation_count}\n"
            f"Readability Score: {analysis.readability_score:.2f}\n"
            f"Completeness Score: {analysis.completeness_score:.2f}"
        )
    except Exception as e:
        logger.error(f"Content quality assessment failed: {e}")
        return f"Content quality assessment failed: {str(e)}"


@quality_agent.tool
async def assess_bias_indicators(
    ctx: RunContext[QualityAssessmentDependencies],
    content: str,
    title: str = ""
) -> str:
    """Analyze content for bias indicators and neutrality."""
    try:
        analysis = await analyze_bias_indicators(ctx, content, title)
        return (
            f"Emotional Language Score: {analysis.emotional_language_score:.2f}\n"
            f"Absolute Terms Count: {analysis.absolute_terms_count}\n"
            f"Perspective Diversity: {analysis.perspective_diversity:.2f}\n"
            f"Neutrality Score: {analysis.neutrality_score:.2f}\n"
            f"Bias Indicators: {', '.join(analysis.bias_indicators) if analysis.bias_indicators else 'None detected'}"
        )
    except Exception as e:
        logger.error(f"Bias assessment failed: {e}")
        return f"Bias assessment failed: {str(e)}"


@quality_agent.tool
async def assess_content_freshness(
    ctx: RunContext[QualityAssessmentDependencies],
    extraction_timestamp: str,
    metadata: str
) -> str:
    """Assess content freshness based on publication and extraction dates."""
    try:
        # Convert string timestamp back to datetime
        extraction_dt = datetime.fromisoformat(extraction_timestamp.replace('Z', '+00:00'))

        # Parse metadata (assuming JSON string)
        import json
        metadata_dict = json.loads(metadata) if metadata else {}

        freshness_score = await check_freshness(ctx, extraction_dt, metadata_dict)

        return f"Freshness Score: {freshness_score:.2f}"
    except Exception as e:
        logger.error(f"Freshness assessment failed: {e}")
        return f"Freshness assessment failed: {str(e)}"


async def assess_source_quality(
    source: ResearchSource,
    deps: QualityAssessmentDependencies = None
) -> QualityAssessment:
    """
    Main function to assess the quality of a research source.

    Args:
        source: The research source to assess
        deps: Dependencies for the assessment (optional)

    Returns:
        QualityAssessment with detailed quality metrics
    """
    if deps is None:
        deps = get_dependencies()

    try:
        logger.info(f"Starting quality assessment for source: {source.source_id}")

        # Prepare the assessment prompt
        assessment_prompt = f"""
        Please assess the quality of this research source:

        Title: {source.title}
        URL: {source.url or 'Not provided'}
        Content Length: {len(source.content)} characters
        Extraction Time: {source.extraction_timestamp}

        Use the available tools to analyze:
        1. Domain authority and reputation
        2. Content quality and structure
        3. Bias indicators and neutrality
        4. Content freshness

        Then provide a comprehensive quality assessment with scores and detailed reasoning.
        """

        # Run the assessment
        result = await quality_agent.run(
            assessment_prompt,
            deps=deps,
            message_history=[]
        )

        logger.info(f"Quality assessment completed for source: {source.source_id}")
        return result.data

    except Exception as e:
        logger.error(f"Quality assessment failed for source {source.source_id}: {e}")

        # Return fallback assessment
        return QualityAssessment(
            source_id=source.source_id,
            credibility_score=0.5,
            bias_score=0.5,
            freshness_score=0.5,
            authority_score=0.5,
            overall_quality=0.5,
            confidence_rating=0.1,
            flags=["assessment_failed", str(e)[:100]],
            assessment_details={"error": str(e)}
        )


async def assess_multiple_sources(
    sources: List[ResearchSource],
    max_concurrent: int = None
) -> List[QualityAssessment]:
    """
    Assess quality of multiple sources concurrently.

    Args:
        sources: List of research sources to assess
        max_concurrent: Maximum concurrent assessments (default from settings)

    Returns:
        List of quality assessments
    """
    if max_concurrent is None:
        max_concurrent = settings.max_concurrent_assessments

    deps = get_dependencies()

    try:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def assess_with_semaphore(source):
            async with semaphore:
                return await assess_source_quality(source, deps)

        logger.info(f"Starting concurrent assessment of {len(sources)} sources")
        assessments = await asyncio.gather(
            *[assess_with_semaphore(source) for source in sources],
            return_exceptions=True
        )

        # Handle any exceptions
        results = []
        for i, assessment in enumerate(assessments):
            if isinstance(assessment, Exception):
                logger.error(f"Assessment failed for source {sources[i].source_id}: {assessment}")
                results.append(QualityAssessment(
                    source_id=sources[i].source_id,
                    credibility_score=0.5,
                    bias_score=0.5,
                    freshness_score=0.5,
                    authority_score=0.5,
                    overall_quality=0.5,
                    confidence_rating=0.1,
                    flags=["concurrent_assessment_failed"],
                    assessment_details={"error": str(assessment)}
                ))
            else:
                results.append(assessment)

        logger.info(f"Completed concurrent assessment of {len(sources)} sources")
        return results

    finally:
        await deps.close()


# Health check function
async def health_check() -> Dict[str, Any]:
    """Perform health check for the Quality Assessment Agent."""
    try:
        # Test basic agent functionality
        test_source = ResearchSource(
            source_id="health_check",
            title="Test Source",
            content="This is a test source for health checking.",
            extraction_timestamp=datetime.now()
        )

        assessment = await assess_source_quality(test_source)

        return {
            "status": "healthy",
            "agent_id": settings.agent_id,
            "version": settings.agent_version,
            "timestamp": datetime.now().isoformat(),
            "test_assessment_completed": True,
            "test_confidence": assessment.confidence_rating
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "agent_id": settings.agent_id,
            "version": settings.agent_version,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


if __name__ == "__main__":
    # Example usage
    async def main():
        # Test assessment
        test_source = ResearchSource(
            source_id="test_001",
            url="https://example.com/article",
            title="Example Article Title",
            content="This is example content for testing the quality assessment agent. It contains some information about a topic.",
            extraction_timestamp=datetime.now()
        )

        assessment = await assess_source_quality(test_source)
        print(f"Assessment completed: {assessment}")

        # Health check
        health = await health_check()
        print(f"Health check: {health}")

    asyncio.run(main())