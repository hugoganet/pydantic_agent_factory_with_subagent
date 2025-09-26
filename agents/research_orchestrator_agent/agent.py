"""
Research Orchestrator Agent - Main Agent Implementation

Master coordinator for the Research Engineering Workflow system.
Orchestrates 7 specialized agents across a 6-phase research workflow.
"""

import logging
import uuid
from typing import Optional

from pydantic_ai import Agent, RunContext

from .providers import get_orchestrator_model, get_fallback_model
from .dependencies import OrchestratorDependencies
from .prompts import (
    SYSTEM_PROMPT,
    get_orchestration_context,
    CRISIS_MANAGEMENT_PROMPT,
    HIGH_PRIORITY_PROMPT
)
from .tools import register_tools
from .settings import settings

# Setup logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Initialize the orchestrator agent
orchestrator_agent = Agent(
    get_orchestrator_model(),
    deps_type=OrchestratorDependencies,
    system_prompt=SYSTEM_PROMPT,
    retries=settings.retry_max_attempts
)

# Register fallback model for reliability
fallback = get_fallback_model()
if fallback:
    orchestrator_agent.models.append(fallback)
    logger.info("Fallback model (GPT-4o-mini) configured")

# Add dynamic orchestration context
@orchestrator_agent.system_prompt
async def orchestration_context_handler(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Add dynamic context based on current workflow state."""
    return await get_orchestration_context(ctx)

# Add crisis management capability
@orchestrator_agent.system_prompt
async def crisis_mode_handler(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Activate crisis management mode when system health is degraded."""
    if ctx.deps.system_health and ctx.deps.system_health.get("status") == "degraded":
        return CRISIS_MANAGEMENT_PROMPT
    return ""

# Add high-priority mode capability
@orchestrator_agent.system_prompt
async def priority_mode_handler(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Activate high-priority mode for urgent research requests."""
    if ctx.deps.priority_level and ctx.deps.priority_level == "high":
        return HIGH_PRIORITY_PROMPT
    return ""

# Register all coordination tools
register_tools(orchestrator_agent, OrchestratorDependencies)

logger.info("Research Orchestrator Agent initialized with all tools and capabilities")


# Convenience function for orchestrator usage
async def run_orchestration(
    research_request: str,
    session_id: Optional[str] = None,
    priority_level: Optional[str] = None,
    **dependency_overrides
) -> str:
    """
    Execute research orchestration with automatic dependency management.

    Args:
        research_request: User's research query/request
        session_id: Optional session identifier
        priority_level: Optional priority level ('high', 'normal', 'low')
        **dependency_overrides: Custom dependency configurations

    Returns:
        Comprehensive research report as string
    """
    deps = OrchestratorDependencies.from_settings(
        settings,
        session_id=session_id or str(uuid.uuid4()),
        research_request_id=str(uuid.uuid4()),
        priority_level=priority_level,
        **dependency_overrides
    )

    try:
        # Initialize infrastructure
        await deps.setup_infrastructure()
        logger.info(f"Starting orchestration for session: {deps.session_id}")

        # Execute orchestration
        result = await orchestrator_agent.run(research_request, deps=deps)

        # Log performance metrics
        metrics = deps.get_task_metrics()
        logger.info(f"Orchestration completed: {metrics}")

        return result.data

    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        raise
    finally:
        await deps.cleanup()


# Health check function
async def health_check() -> dict:
    """
    Check health status of the orchestrator agent.

    Returns:
        Health status information
    """
    try:
        # Basic dependency check
        deps = OrchestratorDependencies.from_settings(settings)
        await deps.setup_infrastructure()

        # Test Redis connection
        await deps.redis_client.ping()

        # Test HTTP client
        health_status = {
            "status": "healthy",
            "agent_type": "research_orchestrator",
            "model": settings.llm_model,
            "redis_connected": True,
            "agent_endpoints": len(deps.agent_endpoints),
            "max_parallel_agents": deps.max_parallel_agents,
            "quality_thresholds": {
                "min_source_quality": deps.min_source_quality,
                "min_confidence": deps.min_confidence_rating
            }
        }

        await deps.cleanup()
        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


if __name__ == "__main__":
    import asyncio

    async def test_orchestrator():
        """Test the orchestrator with a sample request."""
        test_request = "Research the latest developments in quantum computing and their potential applications in cryptography."

        print("Testing Research Orchestrator Agent...")
        result = await run_orchestration(test_request)
        print(f"Result: {result}")

        # Run health check
        health = await health_check()
        print(f"Health: {health}")

    asyncio.run(test_orchestrator())