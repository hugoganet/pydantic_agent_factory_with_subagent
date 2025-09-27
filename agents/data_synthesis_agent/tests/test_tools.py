"""
Tests for Data Synthesis Agent tools.
"""

import pytest
from unittest.mock import AsyncMock

from pydantic_ai import RunContext, TestModel

from ..tools import register_synthesis_tools
from ..models import ResearchFinding, ResearchSource
from ..dependencies import SynthesisDependencies


class TestDataIntegratorTool:
    """Test data integration tool functionality."""

    @pytest.fixture
    def mock_agent(self, test_dependencies):
        """Create mock agent with tools registered."""
        agent = TestModel()
        register_synthesis_tools(agent, SynthesisDependencies)
        return agent

    @pytest.fixture
    def mock_context(self, test_dependencies):
        """Create mock run context."""
        return RunContext(deps=test_dependencies)

    @pytest.mark.asyncio
    async def test_data_integration_success(self, mock_agent, mock_context, multiple_research_findings):
        """Test successful data integration."""
        # Get the data_integrator tool
        data_integrator = None
        for tool in mock_agent._function_tools.values():
            if tool.name == "data_integrator":
                data_integrator = tool.function
                break

        assert data_integrator is not None

        # Test integration
        result = await data_integrator(
            mock_context,
            multiple_research_findings,
            normalization_strategy="confidence_weighted"
        )

        assert result["success"] is True
        assert "integrated_data" in result

    @pytest.mark.asyncio
    async def test_data_integration_empty_list(self, mock_agent, mock_context):
        """Test data integration with empty findings list."""
        data_integrator = None
        for tool in mock_agent._function_tools.values():
            if tool.name == "data_integrator":
                data_integrator = tool.function
                break

        result = await data_integrator(mock_context, [])
        assert result["success"] is True


class TestPatternAnalyzerTool:
    """Test pattern analysis tool functionality."""

    @pytest.fixture
    def mock_agent(self, test_dependencies):
        """Create mock agent with tools."""
        agent = TestModel()
        register_synthesis_tools(agent, SynthesisDependencies)
        return agent

    @pytest.fixture
    def sample_integrated_data(self):
        """Sample data for pattern analysis."""
        return {
            "success": True,
            "integrated_data": {
                "unified_findings": [
                    {
                        "finding_id": "finding_1",
                        "content": "AI adoption increasing",
                        "confidence_level": 0.8,
                        "key_insights": ["AI adoption"]
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_pattern_analysis_success(self, mock_agent, test_dependencies, sample_integrated_data):
        """Test successful pattern analysis."""
        pattern_analyzer = None
        for tool in mock_agent._function_tools.values():
            if tool.name == "pattern_analyzer":
                pattern_analyzer = tool.function
                break

        assert pattern_analyzer is not None

        context = RunContext(deps=test_dependencies)
        result = await pattern_analyzer(context, sample_integrated_data)

        assert result["success"] is True
        assert "analysis_results" in result


class TestReportGeneratorTool:
    """Test report generation tool functionality."""

    @pytest.fixture
    def sample_analysis_results(self):
        """Sample analysis results."""
        return {
            "success": True,
            "analysis_results": {
                "identified_patterns": [
                    {
                        "pattern_id": "pattern_1",
                        "description": "AI adoption increasing",
                        "frequency": 3,
                        "confidence": 0.8
                    }
                ],
                "correlations": [],
                "contradictions": [],
                "information_gaps": [],
                "confidence_assessment": {"pattern_confidence": 0.8}
            }
        }

    @pytest.mark.asyncio
    async def test_report_generation_success(self, test_dependencies, sample_analysis_results):
        """Test successful report generation."""
        agent = TestModel()
        register_synthesis_tools(agent, SynthesisDependencies)

        report_generator = None
        for tool in agent._function_tools.values():
            if tool.name == "report_generator":
                report_generator = tool.function
                break

        assert report_generator is not None

        context = RunContext(deps=test_dependencies)
        result = await report_generator(context, sample_analysis_results)

        assert result["success"] is True
        assert "synthesized_report" in result


class TestToolsIntegration:
    """Test tool integration."""

    def test_tool_registration(self, test_dependencies):
        """Test that all tools are registered."""
        agent = TestModel()
        register_synthesis_tools(agent, SynthesisDependencies)

        tool_names = [tool.name for tool in agent._function_tools.values()]
        expected_tools = ["data_integrator", "pattern_analyzer", "report_generator"]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names