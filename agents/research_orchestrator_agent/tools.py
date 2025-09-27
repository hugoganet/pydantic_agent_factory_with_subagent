"""
Research Orchestrator Agent - Tool Functions

Coordination tools for orchestrating the research engineering workflow system.
Implements inter-agent communication, task distribution, and quality assessment.
"""

import logging
from typing import Dict, Any, List, Optional, Literal
from pydantic_ai import RunContext
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import uuid
import json
import redis.asyncio as redis

from .dependencies import OrchestratorDependencies

logger = logging.getLogger(__name__)


# Tool parameter models for validation
class ResearchRequest(BaseModel):
    """Parameters for research request analysis."""
    query: str = Field(..., description="User's research request")
    complexity: Optional[Literal["simple", "medium", "complex"]] = Field(None, description="Query complexity level")
    timeout_minutes: int = Field(10, ge=1, le=30, description="Maximum research time allowed")
    quality_threshold: float = Field(0.8, ge=0.0, le=1.0, description="Minimum source credibility required")


class TaskDistributionRequest(BaseModel):
    """Parameters for parallel task distribution."""
    execution_plan: Dict[str, Any] = Field(..., description="Strategic execution plan from analysis")
    target_agents: List[str] = Field(..., description="List of agent IDs to coordinate")
    max_parallel: int = Field(5, ge=1, le=10, description="Maximum parallel agents")
    dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="Task dependency mapping")


class QualityAssessmentRequest(BaseModel):
    """Parameters for quality gate coordination."""
    research_results: List[Dict[str, Any]] = Field(..., description="Results from research agents")
    quality_threshold: float = Field(0.8, ge=0.0, le=1.0, description="Minimum credibility threshold")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")


class ReportSynthesisRequest(BaseModel):
    """Parameters for final report synthesis."""
    validated_data: List[Dict[str, Any]] = Field(..., description="Quality-verified research data")
    citations: List[Dict[str, Any]] = Field(..., description="Formatted citations from citation agent")
    synthesis_format: Literal["comprehensive", "summary", "detailed"] = Field("comprehensive", description="Report format")


# AgentMessage and TaskAssignment models
class AgentMessage(BaseModel):
    """Standard inter-agent communication format"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = Field(default="research_orchestrator")
    recipient_id: str = Field(..., description="Target agent ID")
    message_type: Literal["task", "result", "status", "error", "health"] = Field(..., description="Message type")
    payload: Dict[str, Any] = Field(..., description="Message payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(..., description="Request correlation ID")
    priority: int = Field(1, ge=1, le=5, description="Message priority")
    retry_count: int = Field(0, ge=0, description="Retry attempt count")


class TaskAssignment(BaseModel):
    """Task assignment from orchestrator to agents"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = Field(..., description="Target agent ID")
    operation: str = Field(..., description="Operation to perform")
    parameters: Dict[str, Any] = Field(..., description="Task parameters")
    deadline: Optional[datetime] = Field(None, description="Task deadline")
    dependencies: List[str] = Field(default_factory=list, description="Required task dependencies")
    quality_requirements: Dict[str, float] = Field(
        default_factory=lambda: {"min_credibility": 0.8, "min_confidence": 0.7}
    )


# Standalone tool implementation functions
async def analyze_research_request_tool(
    redis_client: redis.Redis,
    query: str,
    complexity: Optional[str] = None,
    timeout_minutes: int = 10,
    quality_threshold: float = 0.8
) -> Dict[str, Any]:
    """Analyze research request and create strategic execution plan."""
    try:
        # Analyze query complexity if not provided
        if not complexity:
            word_count = len(query.split())
            if word_count < 10:
                complexity = "simple"
            elif word_count < 30:
                complexity = "medium"
            else:
                complexity = "complex"

        # Create strategic execution plan
        execution_plan = {
            "strategy_id": str(uuid.uuid4()),
            "query": query,
            "complexity": complexity,
            "timeout_minutes": timeout_minutes,
            "quality_threshold": quality_threshold,
            "phases": {
                "planning": {"duration_seconds": 30, "agents": ["query_strategy_agent"]},
                "research": {
                    "duration_seconds": 180,
                    "agents": ["web_research_agent", "tool_integration_agent"],
                    "parallel": True
                },
                "assessment": {"duration_seconds": 60, "agents": ["quality_assessment_agent"]},
                "attribution": {"duration_seconds": 30, "agents": ["citation_management_agent"]},
                "synthesis": {"duration_seconds": 120, "agents": ["data_synthesis_agent"]},
                "delivery": {"duration_seconds": 30, "agents": ["research_orchestrator"]}
            },
            "task_breakdown": [],
            "resource_allocation": {
                "max_parallel_agents": 5,
                "total_estimated_time": timeout_minutes * 60
            }
        }

        # Create task breakdown based on complexity
        if complexity == "simple":
            execution_plan["task_breakdown"] = [
                {"task": "web_search", "agent": "web_research_agent", "priority": 1},
                {"task": "quality_check", "agent": "quality_assessment_agent", "priority": 2}
            ]
        elif complexity == "medium":
            execution_plan["task_breakdown"] = [
                {"task": "web_search", "agent": "web_research_agent", "priority": 1},
                {"task": "tool_integration", "agent": "tool_integration_agent", "priority": 1},
                {"task": "quality_check", "agent": "quality_assessment_agent", "priority": 2},
                {"task": "citation_format", "agent": "citation_management_agent", "priority": 3}
            ]
        else:  # complex
            execution_plan["task_breakdown"] = [
                {"task": "strategy_consult", "agent": "query_strategy_agent", "priority": 1},
                {"task": "web_search", "agent": "web_research_agent", "priority": 2},
                {"task": "tool_integration", "agent": "tool_integration_agent", "priority": 2},
                {"task": "quality_check", "agent": "quality_assessment_agent", "priority": 3},
                {"task": "citation_format", "agent": "citation_management_agent", "priority": 4},
                {"task": "data_synthesis", "agent": "data_synthesis_agent", "priority": 5}
            ]

        # Store plan in Redis for coordination
        await redis_client.setex(
            f"execution_plan:{execution_plan['strategy_id']}",
            3600,  # 1 hour TTL
            json.dumps(execution_plan, default=str)
        )

        logger.info(f"Created execution plan for {complexity} query: {execution_plan['strategy_id']}")
        return {
            "success": True,
            "execution_plan": execution_plan,
            "estimated_completion": datetime.utcnow() + timedelta(minutes=timeout_minutes)
        }

    except Exception as e:
        logger.error(f"Research request analysis failed: {e}")
        return {"success": False, "error": str(e)}


async def distribute_parallel_tasks_tool(
    redis_client: redis.Redis,
    execution_plan: Dict[str, Any],
    target_agents: List[str],
    max_parallel: int = 5,
    dependencies: Dict[str, List[str]] = None
) -> Dict[str, Any]:
    """Distribute tasks to multiple agents for parallel execution."""
    try:
        if dependencies is None:
            dependencies = {}

        correlation_id = str(uuid.uuid4())
        task_assignments = []
        agent_messages = []

        # Create task assignments for each phase
        for phase_name, phase_config in execution_plan.get("phases", {}).items():
            if phase_config.get("parallel", False):
                # Parallel execution phase
                for agent_id in phase_config.get("agents", []):
                    if agent_id in target_agents:
                        # Create task assignment
                        task = TaskAssignment(
                            agent_id=agent_id,
                            operation=f"{phase_name}_operation",
                            parameters={
                                "query": execution_plan["query"],
                                "phase": phase_name,
                                "timeout_seconds": phase_config.get("duration_seconds", 180),
                                "quality_threshold": execution_plan.get("quality_threshold", 0.8)
                            },
                            deadline=datetime.utcnow() + timedelta(seconds=phase_config.get("duration_seconds", 180)),
                            dependencies=dependencies.get(agent_id, []),
                            quality_requirements=execution_plan.get("quality_requirements", {
                                "min_credibility": 0.8,
                                "min_confidence": 0.7
                            })
                        )
                        task_assignments.append(task)

                        # Create agent message
                        message = AgentMessage(
                            recipient_id=agent_id,
                            message_type="task",
                            payload=task.model_dump(),
                            correlation_id=correlation_id,
                            priority=1 if phase_config.get("parallel") else 2
                        )
                        agent_messages.append(message)

        # Send messages via Redis
        sent_messages = []
        for message in agent_messages[:max_parallel]:  # Limit to max_parallel
            try:
                await redis_client.lpush(
                    f"agent_queue:{message.recipient_id}",
                    message.model_dump_json()
                )

                # Store message for tracking
                await redis_client.setex(
                    f"message:{message.message_id}",
                    1800,  # 30 minutes TTL
                    message.model_dump_json()
                )

                sent_messages.append({
                    "message_id": message.message_id,
                    "agent_id": message.recipient_id,
                    "status": "sent"
                })

                logger.info(f"Sent task to {message.recipient_id}: {message.message_id}")

            except Exception as e:
                logger.error(f"Failed to send message to {message.recipient_id}: {e}")
                sent_messages.append({
                    "message_id": message.message_id,
                    "agent_id": message.recipient_id,
                    "status": "failed",
                    "error": str(e)
                })

        # Store coordination state
        coordination_state = {
            "correlation_id": correlation_id,
            "execution_plan_id": execution_plan.get("strategy_id"),
            "sent_messages": sent_messages,
            "task_assignments": [task.model_dump() for task in task_assignments],
            "status": "distributed",
            "timestamp": datetime.utcnow().isoformat()
        }

        await redis_client.setex(
            f"coordination:{correlation_id}",
            3600,  # 1 hour TTL
            json.dumps(coordination_state, default=str)
        )

        return {
            "success": True,
            "correlation_id": correlation_id,
            "tasks_sent": len(sent_messages),
            "agents_coordinated": [msg["agent_id"] for msg in sent_messages if msg["status"] == "sent"],
            "coordination_state": coordination_state
        }

    except Exception as e:
        logger.error(f"Task distribution failed: {e}")
        return {"success": False, "error": str(e)}


def register_tools(agent, deps_type):
    """Register all coordination tools with the agent."""

    @agent.tool
    async def analyze_research_request(
        ctx: RunContext[deps_type],
        query: str,
        complexity: Optional[Literal["simple", "medium", "complex"]] = None,
        timeout_minutes: int = 10,
        quality_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """Analyze research request and create strategic execution plan."""
        try:
            # Update phase context
            ctx.deps.current_phase = "planning"

            result = await analyze_research_request_tool(
                redis_client=ctx.deps.redis_client,
                query=query,
                complexity=complexity,
                timeout_minutes=timeout_minutes,
                quality_threshold=quality_threshold
            )

            if result["success"]:
                logger.info(f"Research request analyzed: {result['execution_plan']['strategy_id']}")

            return result
        except Exception as e:
            logger.error(f"Research request analysis failed: {e}")
            return {"success": False, "error": str(e)}

    @agent.tool
    async def distribute_parallel_tasks(
        ctx: RunContext[deps_type],
        execution_plan: Dict[str, Any],
        target_agents: List[str],
        max_parallel: int = 5,
        dependencies: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """Distribute tasks to multiple agents for parallel execution."""
        try:
            # Update phase context
            ctx.deps.current_phase = "research"
            ctx.deps.active_agents = target_agents[:max_parallel]

            result = await distribute_parallel_tasks_tool(
                redis_client=ctx.deps.redis_client,
                execution_plan=execution_plan,
                target_agents=target_agents,
                max_parallel=max_parallel,
                dependencies=dependencies or {}
            )

            if result["success"]:
                logger.info(f"Distributed tasks to {result['tasks_sent']} agents: {result['correlation_id']}")

            return result
        except Exception as e:
            logger.error(f"Task distribution failed: {e}")
            return {"success": False, "error": str(e)}

    @agent.tool
    async def coordinate_quality_assessment(
        ctx: RunContext[deps_type],
        research_results: List[Dict[str, Any]],
        quality_threshold: float = 0.8,
        confidence_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Coordinate quality assessment of research results."""
        try:
            # Update phase context
            ctx.deps.current_phase = "assessment"
            ctx.deps.active_agents = ["quality_assessment_agent"]

            correlation_id = str(uuid.uuid4())

            # Create quality assessment task
            quality_task = TaskAssignment(
                agent_id="quality_assessment_agent",
                operation="assess_source_quality",
                parameters={
                    "research_data": research_results,
                    "quality_threshold": quality_threshold,
                    "confidence_threshold": confidence_threshold,
                    "assessment_criteria": [
                        "source_credibility",
                        "information_accuracy",
                        "citation_quality",
                        "data_completeness"
                    ]
                },
                deadline=datetime.utcnow() + timedelta(minutes=2),
                quality_requirements={
                    "min_credibility": quality_threshold,
                    "min_confidence": confidence_threshold
                }
            )

            # Send quality assessment request
            quality_message = AgentMessage(
                recipient_id="quality_assessment_agent",
                message_type="task",
                payload=quality_task.model_dump(),
                correlation_id=correlation_id,
                priority=1
            )

            await ctx.deps.redis_client.lpush(
                "agent_queue:quality_assessment_agent",
                quality_message.model_dump_json()
            )

            logger.info(f"Submitted quality assessment request: {correlation_id}")

            return {
                "success": True,
                "correlation_id": correlation_id,
                "task_id": quality_task.task_id,
                "message_id": quality_message.message_id,
                "assessment_status": "submitted",
                "results_count": len(research_results)
            }

        except Exception as e:
            logger.error(f"Quality assessment coordination failed: {e}")
            return {"success": False, "error": str(e)}

    @agent.tool
    async def synthesize_final_report(
        ctx: RunContext[deps_type],
        validated_data: List[Dict[str, Any]],
        citations: List[Dict[str, Any]],
        synthesis_format: Literal["comprehensive", "summary", "detailed"] = "comprehensive"
    ) -> Dict[str, Any]:
        """Synthesize final comprehensive research report."""
        try:
            # Update phase context
            ctx.deps.current_phase = "synthesis"
            ctx.deps.active_agents = ["data_synthesis_agent"]

            correlation_id = str(uuid.uuid4())

            # Create data synthesis task
            synthesis_task = TaskAssignment(
                agent_id="data_synthesis_agent",
                operation="synthesize_research_report",
                parameters={
                    "validated_research_data": validated_data,
                    "formatted_citations": citations,
                    "report_format": synthesis_format,
                    "synthesis_requirements": {
                        "include_executive_summary": True,
                        "include_methodology": True,
                        "include_source_analysis": True,
                        "include_gaps_limitations": True,
                        "citation_style": "academic"
                    }
                },
                deadline=datetime.utcnow() + timedelta(minutes=3),
                quality_requirements={
                    "min_completeness": 0.9,
                    "citation_accuracy": 1.0
                }
            )

            # Send synthesis request
            synthesis_message = AgentMessage(
                recipient_id="data_synthesis_agent",
                message_type="task",
                payload=synthesis_task.model_dump(),
                correlation_id=correlation_id,
                priority=1
            )

            await ctx.deps.redis_client.lpush(
                "agent_queue:data_synthesis_agent",
                synthesis_message.model_dump_json()
            )

            logger.info(f"Submitted report synthesis request: {correlation_id}")

            return {
                "success": True,
                "correlation_id": correlation_id,
                "task_id": synthesis_task.task_id,
                "message_id": synthesis_message.message_id,
                "synthesis_status": "submitted",
                "report_format": synthesis_format,
                "data_summary": {
                    "validated_sources": len(validated_data),
                    "formatted_citations": len(citations),
                    "estimated_completion": (datetime.utcnow() + timedelta(minutes=3)).isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Report synthesis coordination failed: {e}")
            return {"success": False, "error": str(e)}

    logger.info(f"Registered coordination tools with Research Orchestrator agent")