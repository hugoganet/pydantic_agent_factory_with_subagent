"""Tools for the Workflow Coordinator Agent."""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pydantic_ai import RunContext

from .models import (
    AgentHealthStatus,
    WorkflowState,
    MessageRoutingResult,
    AgentMessage,
    SystemStatus
)
from .dependencies import CoordinatorDependencies


async def check_agent_health(
    ctx: RunContext[CoordinatorDependencies],
    agent_id: Optional[str] = None
) -> Dict[str, AgentHealthStatus]:
    """
    Check health status of specific agent or all agents.

    Args:
        agent_id: Specific agent to check (optional, defaults to all agents)

    Returns:
        Dictionary of agent health statuses
    """
    start_time = time.time()
    results = {}

    # Determine which agents to check
    agents_to_check = {}
    if agent_id and agent_id in ctx.deps.monitored_agents:
        agents_to_check[agent_id] = ctx.deps.monitored_agents[agent_id]
    else:
        agents_to_check = ctx.deps.monitored_agents

    for aid, agent_config in agents_to_check.items():
        try:
            # Simulate health check (in real implementation, would ping agent)
            check_start = time.time()

            # Check if agent has recent activity in Redis
            last_activity_key = f"agent_activity:{aid}"
            last_activity = await ctx.deps.redis_client.get(last_activity_key)

            response_time_ms = (time.time() - check_start) * 1000

            # Determine status based on last activity
            if last_activity:
                last_activity_time = datetime.fromisoformat(last_activity)
                time_since_activity = datetime.now() - last_activity_time

                if time_since_activity < timedelta(seconds=30):
                    status = "healthy"
                    error_rate = 0.0
                elif time_since_activity < timedelta(minutes=5):
                    status = "degraded"
                    error_rate = 5.0
                else:
                    status = "failed"
                    error_rate = 100.0
            else:
                # No activity recorded, assume new/healthy for now
                status = "healthy"
                error_rate = 0.0
                # Record current time as activity
                await ctx.deps.redis_client.set(
                    last_activity_key,
                    datetime.now().isoformat(),
                    ex=3600
                )

            # Create health status
            health_status = AgentHealthStatus(
                agent_id=aid,
                status=status,
                response_time_ms=response_time_ms,
                error_rate_percent=error_rate,
                resource_usage={"memory_mb": 256.0, "cpu_percent": 10.0},
                last_check_timestamp=datetime.now(),
                alerts=[] if status == "healthy" else [f"Agent {aid} is {status}"]
            )

            results[aid] = health_status

            # Update metrics
            ctx.deps.metrics_collector.record_metric(
                f"agent_{aid}_response_time", response_time_ms
            )
            ctx.deps.metrics_collector.record_metric(
                f"agent_{aid}_error_rate", error_rate
            )

        except Exception as e:
            # Create failed health status
            results[aid] = AgentHealthStatus(
                agent_id=aid,
                status="failed",
                response_time_ms=9999.0,
                error_rate_percent=100.0,
                resource_usage={},
                last_check_timestamp=datetime.now(),
                alerts=[f"Health check failed: {str(e)}"]
            )

    total_time = (time.time() - start_time) * 1000
    ctx.deps.metrics_collector.record_metric("health_check_duration", total_time)

    return results


async def manage_workflow_state(
    ctx: RunContext[CoordinatorDependencies],
    workflow_id: str,
    action: str,
    state_data: Optional[Dict[str, Any]] = None
) -> WorkflowState:
    """
    Manage workflow execution state in Redis.

    Args:
        workflow_id: Unique identifier for the workflow
        action: State management operation ("create", "update", "get", "delete")
        state_data: Workflow state information (for create/update)

    Returns:
        Current workflow state
    """
    redis_key = f"workflow:{workflow_id}"

    try:
        if action == "create":
            if not state_data:
                raise ValueError("state_data required for create action")

            workflow_state = WorkflowState(
                workflow_id=workflow_id,
                status="pending",
                participating_agents=state_data.get("participating_agents", []),
                current_phase="initialization",
                progress_percent=0.0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            # Store in Redis with 1 hour TTL
            await ctx.deps.redis_client.set(
                redis_key,
                workflow_state.model_dump_json(),
                ex=3600
            )

            return workflow_state

        elif action == "update":
            if not state_data:
                raise ValueError("state_data required for update action")

            # Get existing state
            existing_data = await ctx.deps.redis_client.get(redis_key)
            if not existing_data:
                raise ValueError(f"Workflow {workflow_id} not found")

            existing_state = WorkflowState.model_validate_json(existing_data)

            # Update fields
            for key, value in state_data.items():
                if hasattr(existing_state, key):
                    setattr(existing_state, key, value)

            existing_state.updated_at = datetime.now()

            # Store updated state
            await ctx.deps.redis_client.set(
                redis_key,
                existing_state.model_dump_json(),
                ex=3600
            )

            return existing_state

        elif action == "get":
            existing_data = await ctx.deps.redis_client.get(redis_key)
            if not existing_data:
                raise ValueError(f"Workflow {workflow_id} not found")

            return WorkflowState.model_validate_json(existing_data)

        elif action == "delete":
            await ctx.deps.redis_client.delete(redis_key)

            return WorkflowState(
                workflow_id=workflow_id,
                status="deleted",
                participating_agents=[],
                current_phase="deleted",
                progress_percent=100.0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

        else:
            raise ValueError(f"Invalid action: {action}")

    except Exception as e:
        # Return error state
        return WorkflowState(
            workflow_id=workflow_id,
            status="failed",
            participating_agents=[],
            current_phase="error",
            progress_percent=0.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            error_details=str(e)
        )


async def route_agent_message(
    ctx: RunContext[CoordinatorDependencies],
    message: AgentMessage,
    validate_dependencies: bool = True
) -> MessageRoutingResult:
    """
    Route messages between agents with dependency validation.

    Args:
        message: Standard AgentMessage to route
        validate_dependencies: Check if sender/receiver dependencies are met

    Returns:
        Routing result with delivery status and any validation errors
    """
    start_time = time.time()

    try:
        # Validate message format
        if not message.sender_id or not message.recipient_id:
            return MessageRoutingResult(
                message_id=message.message_id,
                routing_status="rejected",
                error_message="Missing sender_id or recipient_id"
            )

        # Check if sender and recipient are valid agents
        if validate_dependencies:
            if message.sender_id not in ctx.deps.monitored_agents:
                return MessageRoutingResult(
                    message_id=message.message_id,
                    routing_status="rejected",
                    error_message=f"Unknown sender agent: {message.sender_id}"
                )

            if message.recipient_id not in ctx.deps.monitored_agents:
                return MessageRoutingResult(
                    message_id=message.message_id,
                    routing_status="rejected",
                    error_message=f"Unknown recipient agent: {message.recipient_id}"
                )

        # Queue message in Redis
        queue_key = f"message_queue:{message.recipient_id}"
        message_data = {
            "message_id": message.message_id,
            "sender_id": message.sender_id,
            "message_type": message.message_type,
            "payload": json.dumps(message.payload),
            "timestamp": message.timestamp.isoformat(),
            "correlation_id": message.correlation_id,
            "priority": message.priority,
            "retry_count": message.retry_count
        }

        # Store message with priority (lower number = higher priority)
        await ctx.deps.redis_client.hset(
            f"message:{message.message_id}",
            mapping=message_data
        )

        # Add to recipient's queue
        await ctx.deps.redis_client.set(
            f"queue_item:{message.recipient_id}:{message.message_id}",
            "pending",
            ex=3600
        )

        delivery_time = (time.time() - start_time) * 1000

        # Update metrics
        ctx.deps.metrics_collector.record_metric("message_routing_time", delivery_time)
        ctx.deps.metrics_collector.record_metric("messages_routed_total", 1)

        return MessageRoutingResult(
            message_id=message.message_id,
            routing_status="queued",
            delivery_time_ms=delivery_time
        )

    except Exception as e:
        return MessageRoutingResult(
            message_id=message.message_id,
            routing_status="failed",
            error_message=str(e)
        )