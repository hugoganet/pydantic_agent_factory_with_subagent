"""Workflow Coordinator Agent - Main implementation."""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic_ai import Agent, RunContext

from .models import (
    SystemStatus,
    CoordinationRequest,
    CoordinationReport,
    AgentMessage,
    WorkflowState,
    AgentHealthStatus
)
from .dependencies import CoordinatorDependencies, create_coordinator_dependencies
from .providers import get_llm_model
from .prompts import COORDINATOR_SYSTEM_PROMPT
from .tools import check_agent_health, manage_workflow_state, route_agent_message


# Create the Workflow Coordinator Agent
workflow_coordinator_agent = Agent(
    get_llm_model(),
    deps_type=CoordinatorDependencies,
    system_prompt=COORDINATOR_SYSTEM_PROMPT,
)


@workflow_coordinator_agent.tool
async def get_system_status(ctx: RunContext[CoordinatorDependencies]) -> SystemStatus:
    """
    Get comprehensive system health and status report.

    Returns:
        Complete system status with all agent health information
    """
    # Get health status for all agents
    agent_statuses = await check_agent_health(ctx)

    # Determine overall health
    failed_count = sum(1 for status in agent_statuses.values() if status.status == "failed")
    degraded_count = sum(1 for status in agent_statuses.values() if status.status == "degraded")

    if failed_count > 0:
        overall_health = "critical"
    elif degraded_count > 0:
        overall_health = "degraded"
    else:
        overall_health = "healthy"

    # Get active workflows (mock for now)
    active_workflows = []
    try:
        # In a real implementation, we'd scan Redis for active workflow keys
        workflow_keys = []  # Would get from Redis scan
        for workflow_id in workflow_keys:
            workflow_state = await manage_workflow_state(ctx, workflow_id, "get")
            if workflow_state.status in ["pending", "running"]:
                active_workflows.append(workflow_state)
    except Exception as e:
        print(f"Error getting active workflows: {e}")

    # Get system metrics
    system_metrics = ctx.deps.metrics_collector.get_metrics()

    # Generate alerts
    alerts = []
    for agent_id, status in agent_statuses.items():
        alerts.extend(status.alerts)

    if overall_health == "critical":
        alerts.append("System is in critical state - multiple agents failed")
    elif overall_health == "degraded":
        alerts.append("System is degraded - some agents are not performing optimally")

    return SystemStatus(
        overall_health=overall_health,
        agent_statuses=agent_statuses,
        active_workflows=active_workflows,
        system_metrics=system_metrics,
        alerts=alerts
    )


@workflow_coordinator_agent.tool
async def coordinate_workflow(
    ctx: RunContext[CoordinatorDependencies],
    coordination_request: CoordinationRequest
) -> CoordinationReport:
    """
    Coordinate execution of a research workflow.

    Args:
        coordination_request: Details of workflow to coordinate

    Returns:
        Comprehensive coordination report with execution details
    """
    start_time = datetime.now()

    # Create workflow state
    workflow_state = await manage_workflow_state(
        ctx,
        coordination_request.workflow_id,
        "create",
        {
            "participating_agents": coordination_request.participating_agents,
            "coordination_type": coordination_request.coordination_type,
            "dependencies": coordination_request.dependencies
        }
    )

    # Get initial health status of participating agents
    initial_health = {}
    for agent_id in coordination_request.participating_agents:
        health_status = await check_agent_health(ctx, agent_id)
        if agent_id in health_status:
            initial_health[agent_id] = health_status[agent_id]

    # Update workflow to running
    await manage_workflow_state(
        ctx,
        coordination_request.workflow_id,
        "update",
        {"status": "running", "current_phase": "execution", "progress_percent": 10.0}
    )

    # Simulate workflow coordination based on type
    execution_summary = {}
    timing_analysis = {}
    error_summary = {"errors": [], "warnings": []}
    recommendations = []

    try:
        if coordination_request.coordination_type == "parallel":
            # Coordinate parallel execution
            execution_summary["type"] = "parallel"
            execution_summary["agents_count"] = len(coordination_request.participating_agents)

            # Check if we have too many parallel agents
            if len(coordination_request.participating_agents) > ctx.deps.max_parallel_agents:
                error_summary["warnings"].append(
                    f"Too many parallel agents ({len(coordination_request.participating_agents)} > {ctx.deps.max_parallel_agents})"
                )
                recommendations.append("Consider reducing parallel agent count or increasing system capacity")

            timing_analysis["parallel_execution_time"] = 120.0  # Mock timing

            # Update progress
            await manage_workflow_state(
                ctx,
                coordination_request.workflow_id,
                "update",
                {"progress_percent": 75.0}
            )

        elif coordination_request.coordination_type == "sequential":
            # Coordinate sequential execution
            execution_summary["type"] = "sequential"
            execution_summary["sequence_length"] = len(coordination_request.participating_agents)

            timing_analysis["sequential_execution_time"] = 300.0  # Mock timing

            # Update progress
            await manage_workflow_state(
                ctx,
                coordination_request.workflow_id,
                "update",
                {"progress_percent": 80.0}
            )

        elif coordination_request.coordination_type == "pipeline":
            # Coordinate pipeline execution
            execution_summary["type"] = "pipeline"
            execution_summary["pipeline_stages"] = len(coordination_request.participating_agents)

            timing_analysis["pipeline_execution_time"] = 200.0  # Mock timing

            # Check dependencies
            for agent, deps in coordination_request.dependencies.items():
                if agent in coordination_request.participating_agents:
                    for dep in deps:
                        if dep not in coordination_request.participating_agents:
                            error_summary["errors"].append(
                                f"Agent {agent} depends on {dep} which is not in participating agents"
                            )

            # Update progress
            await manage_workflow_state(
                ctx,
                coordination_request.workflow_id,
                "update",
                {"progress_percent": 85.0}
            )

        # Mark workflow as completed
        await manage_workflow_state(
            ctx,
            coordination_request.workflow_id,
            "update",
            {"status": "completed", "progress_percent": 100.0}
        )

        execution_summary["status"] = "completed"
        execution_summary["duration_seconds"] = (datetime.now() - start_time).total_seconds()

    except Exception as e:
        error_summary["errors"].append(str(e))
        execution_summary["status"] = "failed"

        # Mark workflow as failed
        await manage_workflow_state(
            ctx,
            coordination_request.workflow_id,
            "update",
            {"status": "failed", "error_details": str(e)}
        )

    # Get final health status
    final_health = []
    for agent_id in coordination_request.participating_agents:
        health_status = await check_agent_health(ctx, agent_id)
        if agent_id in health_status:
            final_health.append(health_status[agent_id])

    # Generate recommendations
    if not recommendations:
        if execution_summary.get("status") == "completed":
            recommendations.append("Workflow completed successfully")
        else:
            recommendations.append("Review error logs and retry failed operations")

    return CoordinationReport(
        workflow_id=coordination_request.workflow_id,
        execution_summary=execution_summary,
        agent_performance=final_health,
        timing_analysis=timing_analysis,
        error_summary=error_summary,
        recommendations=recommendations
    )


@workflow_coordinator_agent.tool
async def handle_message_routing(
    ctx: RunContext[CoordinatorDependencies],
    message: AgentMessage
) -> str:
    """
    Route a message between agents.

    Args:
        message: Message to route

    Returns:
        Status message about routing result
    """
    result = await route_agent_message(ctx, message, validate_dependencies=True)

    if result.routing_status == "queued":
        return f"Message {result.message_id} successfully queued for {message.recipient_id}"
    elif result.routing_status == "rejected":
        return f"Message {result.message_id} rejected: {result.error_message}"
    else:
        return f"Message {result.message_id} failed to route: {result.error_message}"


async def run_coordinator_agent(query: str) -> str:
    """
    Run the Workflow Coordinator Agent with a query.

    Args:
        query: Query or command for the coordinator

    Returns:
        Response from the coordinator
    """
    deps = await create_coordinator_dependencies()

    try:
        result = await workflow_coordinator_agent.run(
            query,
            deps=deps
        )
        return result.data
    except Exception as e:
        return f"Error running coordinator: {str(e)}"
    finally:
        await deps.cleanup()


async def main():
    """Main entry point for testing the coordinator agent."""
    # Test queries
    test_queries = [
        "Get the current system status",
        "Check health of all research agents",
        "What is the overall system health?",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        response = await run_coordinator_agent(query)
        print(f"Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())