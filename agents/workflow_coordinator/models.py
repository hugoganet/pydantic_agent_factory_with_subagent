"""Pydantic models for the Workflow Coordinator Agent."""

from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from uuid import uuid4


# Input Models
class CoordinationRequest(BaseModel):
    """Request to coordinate workflow execution."""
    workflow_id: str
    participating_agents: List[str]
    coordination_type: Literal["parallel", "sequential", "pipeline", "conditional"]
    dependencies: Dict[str, List[str]]
    timeout_settings: Dict[str, int] = Field(default_factory=dict)
    retry_policies: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class AgentHealthCheck(BaseModel):
    """Health check data for an agent."""
    agent_id: str
    timestamp: datetime
    status: Literal["healthy", "degraded", "failed"]
    response_time: float
    error_rate: float
    resource_usage: Dict[str, float]


class AgentMessage(BaseModel):
    """Standard inter-agent communication format."""
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    sender_id: str
    recipient_id: str
    message_type: Literal["task", "result", "status", "error", "health"]
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: str
    priority: int = 1
    retry_count: int = 0


# Output Models
class AgentHealthStatus(BaseModel):
    """Health status response for an agent."""
    agent_id: str
    status: Literal["healthy", "degraded", "failed"]
    response_time_ms: float
    error_rate_percent: float
    resource_usage: Dict[str, float]
    last_check_timestamp: datetime
    alerts: List[str] = Field(default_factory=list)


class WorkflowState(BaseModel):
    """Current state of a workflow execution."""
    workflow_id: str
    status: Literal["pending", "running", "completed", "failed", "paused"]
    participating_agents: List[str]
    current_phase: str
    progress_percent: float
    created_at: datetime
    updated_at: datetime
    error_details: Optional[str] = None


class MessageRoutingResult(BaseModel):
    """Result of message routing operation."""
    message_id: str
    routing_status: Literal["delivered", "queued", "failed", "rejected"]
    delivery_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    next_retry_at: Optional[datetime] = None


class SystemStatus(BaseModel):
    """Overall system health and status."""
    overall_health: Literal["healthy", "degraded", "critical"]
    agent_statuses: Dict[str, AgentHealthStatus]
    active_workflows: List[WorkflowState]
    system_metrics: Dict[str, float]
    alerts: List[str] = Field(default_factory=list)


class CoordinationReport(BaseModel):
    """Comprehensive workflow coordination report."""
    workflow_id: str
    execution_summary: Dict[str, Any]
    agent_performance: List[AgentHealthStatus]
    timing_analysis: Dict[str, float]
    error_summary: Dict[str, Any]
    recommendations: List[str]


# Configuration Models
class AgentConfig(BaseModel):
    """Configuration for monitored agents."""
    agent_id: str
    agent_name: str
    health_check_endpoint: str
    priority: int = 1
    timeout_seconds: int = 30
    retry_policy: Dict[str, Any] = Field(default_factory=dict)


class RetryPolicy(BaseModel):
    """Retry configuration for agent communications."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0