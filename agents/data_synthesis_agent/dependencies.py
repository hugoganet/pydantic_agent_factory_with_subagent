"""
Dependencies for Data Synthesis Agent - workflow coordination and synthesis context.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SynthesisDependencies:
    """
    Dependencies for Data Synthesis Agent execution.

    Manages workflow coordination, research findings processing,
    and synthesis context for generating comprehensive reports.
    """

    # Workflow Context
    session_id: Optional[str] = None
    synthesis_request_id: Optional[str] = None
    research_phase_complete: bool = False

    # Agent Coordination
    upstream_agents: List[str] = field(default_factory=lambda: [
        "web_research_agent",
        "tool_integration_agent",
        "citation_management_agent"
    ])
    target_orchestrator: str = "research_orchestrator"

    # Synthesis Configuration
    max_findings_count: int = 50
    min_confidence_threshold: float = 0.7
    synthesis_timeout: int = 120

    # Report Generation Context
    target_audience: str = "executives"  # "executives", "researchers", "technical"
    output_format: str = "executive"     # "executive", "detailed", "technical"
    quality_target: float = 0.9         # >90% accuracy target

    # Performance Tracking
    start_time: Optional[datetime] = None
    findings_processed: int = 0
    synthesis_metrics: Dict[str, Any] = field(default_factory=dict)

    # Debug and Monitoring
    debug_mode: bool = False
    log_synthesis_steps: bool = True

    def start_synthesis_timer(self):
        """Start timing synthesis operation."""
        self.start_time = datetime.now()
        logger.info(f"Starting synthesis for session {self.session_id}")

    def get_synthesis_duration(self) -> Optional[float]:
        """Get synthesis duration in seconds."""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None

    def add_synthesis_metric(self, key: str, value: Any):
        """Add metric to synthesis tracking."""
        self.synthesis_metrics[key] = value
        if self.debug_mode:
            logger.debug(f"Synthesis metric - {key}: {value}")

    def validate_synthesis_readiness(self, findings_count: int) -> bool:
        """
        Validate if synthesis can proceed with given findings.

        Args:
            findings_count: Number of research findings available

        Returns:
            True if synthesis can proceed
        """
        if not self.research_phase_complete:
            logger.warning("Research phase not marked complete")
            return False

        if findings_count == 0:
            logger.error("No research findings available for synthesis")
            return False

        if findings_count > self.max_findings_count:
            logger.warning(f"Findings count ({findings_count}) exceeds max ({self.max_findings_count})")

        return True

    @classmethod
    def from_settings(cls, settings, **kwargs):
        """
        Create synthesis dependencies from settings.

        Args:
            settings: Settings instance
            **kwargs: Override values

        Returns:
            Configured SynthesisDependencies instance
        """
        return cls(
            max_findings_count=kwargs.get('max_findings_count', settings.max_findings_per_synthesis),
            min_confidence_threshold=kwargs.get('min_confidence_threshold', settings.min_confidence_threshold),
            synthesis_timeout=kwargs.get('synthesis_timeout', settings.synthesis_timeout_seconds),
            debug_mode=kwargs.get('debug_mode', settings.debug),
            **{k: v for k, v in kwargs.items()
               if k not in ['max_findings_count', 'min_confidence_threshold', 'synthesis_timeout', 'debug_mode']}
        )

    def get_workflow_context(self) -> Dict[str, Any]:
        """Get context for workflow message passing."""
        return {
            "agent_id": "data_synthesis_agent",
            "session_id": self.session_id,
            "synthesis_request_id": self.synthesis_request_id,
            "target_audience": self.target_audience,
            "output_format": self.output_format,
            "upstream_agents": self.upstream_agents,
            "performance_metrics": self.synthesis_metrics
        }