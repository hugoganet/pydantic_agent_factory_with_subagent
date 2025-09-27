"""
Data Synthesis Agent - Integrates research findings into comprehensive reports.

This agent is responsible for combining research from multiple upstream agents
(Web Research, Tool Integration, Citation Management) into coherent, well-structured
synthesis reports for different target audiences.
"""

import logging
from typing import Optional, List

from pydantic_ai import Agent

from .models import SynthesisRequest, SynthesizedReport, ResearchFinding
from .providers import get_synthesis_model
from .dependencies import SynthesisDependencies
from .settings import settings
from .prompts import SYSTEM_PROMPT
from .tools import register_synthesis_tools

logger = logging.getLogger(__name__)

# Initialize the synthesis agent
agent = Agent(
    get_synthesis_model(),
    deps_type=SynthesisDependencies,
    system_prompt=SYSTEM_PROMPT,
    result_type=SynthesizedReport,
    retries=2  # Limited retries for performance targets
)

# Register synthesis tools
register_synthesis_tools(agent, SynthesisDependencies)

logger.info("Data Synthesis Agent initialized with 3 synthesis tools")


async def run_synthesis(
    synthesis_request: SynthesisRequest,
    session_id: Optional[str] = None,
    **dependency_overrides
) -> SynthesizedReport:
    """
    Run synthesis agent with automatic dependency injection.

    Args:
        synthesis_request: SynthesisRequest with research findings to synthesize
        session_id: Optional session identifier for tracking
        **dependency_overrides: Override default dependencies

    Returns:
        SynthesizedReport with integrated analysis and recommendations
    """
    logger.info(f"Starting synthesis for request {synthesis_request.request_id}")

    # Create dependencies with proper configuration
    deps = SynthesisDependencies.from_settings(
        settings,
        session_id=session_id,
        synthesis_request_id=synthesis_request.request_id,
        target_audience=synthesis_request.target_audience,
        output_format=synthesis_request.output_format,
        research_phase_complete=True,  # Assume research is complete when synthesis is called
        **dependency_overrides
    )

    # Validate synthesis readiness
    findings_count = len(synthesis_request.research_findings)
    if not deps.validate_synthesis_readiness(findings_count):
        raise ValueError("Synthesis conditions not met")

    # Start performance timing
    deps.start_synthesis_timer()

    try:
        # Execute synthesis with the agent
        result = await agent.run(
            f"""
            Please synthesize the following research request:

            Request ID: {synthesis_request.request_id}
            Target Audience: {synthesis_request.target_audience}
            Output Format: {synthesis_request.output_format}
            Quality Threshold: {synthesis_request.quality_threshold}

            Research Findings ({len(synthesis_request.research_findings)} total):
            {_format_findings_for_synthesis(synthesis_request.research_findings)}

            Synthesis Requirements:
            - Focus Areas: {synthesis_request.synthesis_requirements.focus_areas}
            - Depth Level: {synthesis_request.synthesis_requirements.depth_level}
            - Include Methodology: {synthesis_request.synthesis_requirements.include_methodology}
            - Include Gaps: {synthesis_request.synthesis_requirements.include_gaps}
            - Include Recommendations: {synthesis_request.synthesis_requirements.include_recommendations}

            Please use the data_integrator, pattern_analyzer, and report_generator tools to:
            1. Integrate and normalize the research findings
            2. Identify patterns, correlations, and contradictions
            3. Generate a comprehensive synthesis report

            Ensure the final report meets the specified quality threshold and target audience requirements.
            """,
            deps=deps
        )

        # Log performance metrics
        duration = deps.get_synthesis_duration()
        deps.add_synthesis_metric("synthesis_duration_seconds", duration)
        deps.add_synthesis_metric("findings_processed", findings_count)

        logger.info(f"Synthesis completed in {duration:.2f}s for session {session_id}")

        # Return the structured result
        return result.data

    except Exception as e:
        duration = deps.get_synthesis_duration()
        logger.error(f"Synthesis failed after {duration:.2f}s for session {session_id}: {e}")
        raise


def _format_findings_for_synthesis(findings: List[ResearchFinding]) -> str:
    """Format research findings for agent input."""
    formatted_findings = []

    for i, finding in enumerate(findings, 1):
        sources_text = ""
        if finding.sources:
            source_titles = [source.title for source in finding.sources[:3]]  # Limit to 3 sources
            sources_text = f" (Sources: {', '.join(source_titles)})"

        insights_text = ""
        if finding.key_insights:
            insights_text = f"\n  Key Insights: {', '.join(finding.key_insights[:3])}"  # Limit to 3 insights

        formatted_findings.append(
            f"{i}. [{finding.source_agent}] {finding.content[:300]}{'...' if len(finding.content) > 300 else ''}"
            f"{sources_text}"
            f"\n  Confidence: {finding.confidence_level:.1%}"
            f"{insights_text}\n"
        )

    return "\n".join(formatted_findings)


def create_synthesis_agent_with_deps(**dependency_overrides) -> tuple[Agent, SynthesisDependencies]:
    """
    Create synthesis agent with custom dependencies.

    Args:
        **dependency_overrides: Custom dependency values

    Returns:
        Tuple of (agent, dependencies)
    """
    deps = SynthesisDependencies.from_settings(settings, **dependency_overrides)
    return agent, deps


# Health check function for monitoring
async def health_check() -> dict:
    """
    Perform health check of the synthesis agent.

    Returns:
        Dict with health status information
    """
    try:
        # Test agent initialization
        test_deps = SynthesisDependencies(session_id="health_check")

        health_status = {
            "status": "healthy",
            "agent_id": settings.agent_id,
            "model": settings.llm_model,
            "tools_registered": 3,  # data_integrator, pattern_analyzer, report_generator
            "max_findings": settings.max_findings_per_synthesis,
            "timeout_seconds": settings.synthesis_timeout_seconds,
            "confidence_threshold": settings.min_confidence_threshold,
            "timestamp": test_deps.start_time.isoformat() if test_deps.start_time else None
        }

        logger.info("Health check passed")
        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "agent_id": settings.agent_id
        }