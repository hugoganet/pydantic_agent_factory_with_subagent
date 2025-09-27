"""
Integration tests for Data Synthesis Agent.
"""

import pytest
import time

from ..agent import health_check
from ..models import SynthesisRequest, ResearchFinding
from ..dependencies import SynthesisDependencies


class TestAgentIntegration:
    """Test complete agent integration."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test agent health check functionality."""
        health_status = await health_check()

        assert "status" in health_status
        assert health_status["status"] in ["healthy", "unhealthy"]
        assert "agent_id" in health_status

    def test_synthesis_request_validation(self, multiple_research_findings):
        """Test synthesis request validation."""
        valid_request = SynthesisRequest(
            request_id="validation_test",
            research_findings=multiple_research_findings,
            output_format="executive",
            target_audience="executives"
        )

        assert valid_request.request_id == "validation_test"
        assert len(valid_request.research_findings) > 0

    def test_dependencies_creation(self):
        """Test synthesis dependencies creation."""
        deps = SynthesisDependencies(
            session_id="test_session",
            synthesis_request_id="test_request",
            research_phase_complete=True,
            debug_mode=True
        )

        assert deps.session_id == "test_session"
        assert deps.research_phase_complete is True
        assert deps.debug_mode is True

        # Test validation
        assert deps.validate_synthesis_readiness(5) is True
        assert deps.validate_synthesis_readiness(0) is False

    def test_dependencies_metrics(self):
        """Test dependencies metrics tracking."""
        deps = SynthesisDependencies(session_id="metrics_test")

        # Test timer
        deps.start_synthesis_timer()
        time.sleep(0.01)  # Small delay
        duration = deps.get_synthesis_duration()

        assert duration is not None
        assert duration > 0

        # Test metrics
        deps.add_synthesis_metric("test_metric", 42)
        assert deps.synthesis_metrics["test_metric"] == 42


class TestWorkflowIntegration:
    """Test workflow integration patterns."""

    def test_synthesis_request_from_upstream_agents(self):
        """Test creating synthesis request from upstream agent data."""
        findings = [
            ResearchFinding(
                source_agent="web_research_agent",
                finding_id="web_1",
                content="Web research finding",
                confidence_level=0.8,
                key_insights=["AI trends"]
            ),
            ResearchFinding(
                source_agent="tool_integration_agent",
                finding_id="tool_1",
                content="Internal tool analysis",
                confidence_level=0.9,
                key_insights=["productivity"]
            )
        ]

        request = SynthesisRequest(
            request_id="workflow_test",
            research_findings=findings,
            output_format="detailed",
            target_audience="researchers"
        )

        source_agents = {f.source_agent for f in request.research_findings}
        expected_agents = {"web_research_agent", "tool_integration_agent"}

        assert source_agents == expected_agents

    def test_workflow_context(self):
        """Test workflow context generation."""
        deps = SynthesisDependencies(
            session_id="context_test",
            synthesis_request_id="req_123",
            target_audience="executives"
        )

        context = deps.get_workflow_context()

        assert context["agent_id"] == "data_synthesis_agent"
        assert context["session_id"] == "context_test"


class TestPerformanceIntegration:
    """Test performance requirements."""

    def test_large_dataset_handling(self):
        """Test handling of large research datasets."""
        findings = []
        for i in range(50):
            findings.append(ResearchFinding(
                source_agent=f"agent_{i % 3}",
                finding_id=f"finding_{i}",
                content=f"Research finding {i}",
                confidence_level=0.7 + (i % 3) * 0.1,
                key_insights=[f"insight_{i}"]
            ))

        request = SynthesisRequest(
            request_id="large_dataset_test",
            research_findings=findings,
            output_format="executive",
            target_audience="executives"
        )

        assert len(request.research_findings) == 50

    def test_timeout_configuration(self):
        """Test timeout configuration."""
        deps = SynthesisDependencies(
            synthesis_timeout=120,
            session_id="timeout_test"
        )

        assert deps.synthesis_timeout == 120

        deps.start_synthesis_timer()
        assert deps.start_time is not None