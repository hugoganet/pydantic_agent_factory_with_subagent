"""
Query Strategy Agent - Strategic advisory service for research workflow optimization.
"""

import logging
from typing import Optional, Dict, Any
from pydantic_ai import Agent, RunContext

from .providers import get_llm_model
from .dependencies import AgentDependencies
from .settings import settings
from .prompts import SYSTEM_PROMPT
from .tools import analyze_query_complexity, recommend_research_strategy, assess_research_risks

logger = logging.getLogger(__name__)

# Initialize the agent with GPT-4o for strategic reasoning
agent = Agent(
    get_llm_model(),
    deps_type=AgentDependencies,
    system_prompt=SYSTEM_PROMPT,
    retries=settings.max_retries
)

# Register analytical tools
@agent.tool
async def analyze_complexity(
    ctx: RunContext[AgentDependencies],
    research_query: str,
    constraints: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Analyze research query complexity using NLP techniques.

    Args:
        research_query: The research question to analyze
        constraints: Optional research constraints

    Returns:
        Complexity metrics and analysis details
    """
    if constraints is None:
        constraints = {}

    # Check cache first for performance
    cached_score = ctx.deps.get_cached_complexity(research_query)
    if cached_score is not None and ctx.deps.debug:
        logger.info(f"Using cached complexity score: {cached_score}")

    result = await analyze_query_complexity(research_query, constraints)

    # Cache the result
    if result.get("success") and "complexity_metrics" in result:
        overall_complexity = result["complexity_metrics"]["overall_complexity"]
        ctx.deps.cache_complexity_score(research_query, overall_complexity)

    return result

@agent.tool
async def recommend_strategy(
    ctx: RunContext[AgentDependencies],
    complexity_metrics: Dict[str, float],
    constraints: Dict[str, Any],
    use_historical: bool = True
) -> Dict[str, Any]:
    """
    Recommend optimal research strategy based on complexity and constraints.

    Args:
        complexity_metrics: Output from complexity analysis
        constraints: Research constraints
        use_historical: Whether to use historical data in recommendations

    Returns:
        Strategy recommendation and execution plan
    """
    historical_data = None
    if use_historical and ctx.deps.historical_strategies:
        # Use recent historical data for improved recommendations
        historical_data = {
            "success_rate": ctx.deps.success_metrics.get("success_rate", 0.7) if ctx.deps.success_metrics else 0.7,
            "avg_duration": sum(s.get("duration", 60) for s in ctx.deps.historical_strategies[-10:]) / min(10, len(ctx.deps.historical_strategies))
        }

    return await recommend_research_strategy(complexity_metrics, constraints, historical_data)

@agent.tool
async def assess_risks(
    ctx: RunContext[AgentDependencies],
    complexity_metrics: Dict[str, float],
    strategy_plan: Dict[str, Any],
    constraints: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Assess research risks and provide mitigation strategies.

    Args:
        complexity_metrics: Complexity analysis results
        strategy_plan: Recommended strategy and execution plan
        constraints: Research constraints

    Returns:
        Risk assessment and mitigation strategies
    """
    return await assess_research_risks(complexity_metrics, strategy_plan, constraints)

# Convenience functions for agent usage
async def analyze_research_strategy(
    research_query: str,
    constraints: Optional[Dict[str, Any]] = None,
    workflow_context: Optional[Dict[str, Any]] = None,
    **dependency_overrides
) -> Dict[str, Any]:
    """
    Analyze research query and recommend optimal strategy.

    Args:
        research_query: The research question to analyze
        constraints: Optional constraint parameters
        workflow_context: Context from Research Orchestrator
        **dependency_overrides: Override default dependencies

    Returns:
        Comprehensive strategy analysis with execution plan and risk assessment
    """
    deps = AgentDependencies.from_settings(
        settings,
        research_context=workflow_context,
        **dependency_overrides
    )

    # Build analysis prompt with structured approach
    prompt_parts = [
        "Please analyze this research query and provide comprehensive strategic recommendations:",
        f"Research Query: {research_query}"
    ]

    if constraints:
        constraints_str = ", ".join([f"{k}: {v}" for k, v in constraints.items()])
        prompt_parts.append(f"Constraints: {constraints_str}")

    if workflow_context:
        prompt_parts.append(f"Workflow Context: {workflow_context}")

    prompt_parts.extend([
        "",
        "Please provide:",
        "1. Detailed complexity analysis with scoring (1-10 scale)",
        "2. Recommended research strategy with clear reasoning",
        "3. Comprehensive risk assessment with mitigation strategies",
        "4. Realistic timeline and resource estimates",
        "5. Quality checkpoints and fallback options"
    ])

    analysis_prompt = "\n".join(prompt_parts)

    try:
        result = await agent.run(analysis_prompt, deps=deps)
        return {
            "success": True,
            "strategy_analysis": result.data,
            "agent_context": {
                "workflow_id": deps.workflow_id,
                "session_id": deps.orchestrator_session_id
            }
        }
    except Exception as e:
        logger.error(f"Error in strategy analysis: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "agent_execution"
        }

def create_strategy_agent_with_deps(**dependency_overrides) -> tuple[Agent, AgentDependencies]:
    """
    Create strategy agent instance with custom dependencies.

    Args:
        **dependency_overrides: Custom dependency values

    Returns:
        Tuple of (agent, dependencies)
    """
    deps = AgentDependencies.from_settings(settings, **dependency_overrides)
    return agent, deps

async def quick_complexity_check(research_query: str) -> float:
    """
    Quick complexity assessment for triage purposes.

    Args:
        research_query: Query to assess

    Returns:
        Complexity score (1-10 scale)
    """
    try:
        result = await analyze_query_complexity(research_query, {})
        if result.get("success"):
            return result["complexity_metrics"]["overall_complexity"]
        return 5.0  # Default moderate complexity
    except Exception as e:
        logger.error(f"Error in quick complexity check: {e}")
        return 5.0