"""
Test core agent functionality for Tool Integration Agent.
Validates agent responses, tool integration, and error handling using TestModel.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from pydantic_ai import RunContext
from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import tool_integration_agent, run_tool_integration_agent, health_check
from ..dependencies import ToolIntegrationDependencies
from ..models import ToolRequest, ToolResponse
from .conftest import (
    assert_successful_response,
    assert_error_response,
    validate_google_drive_document,
    validate_gmail_message,
    validate_database_row
)


class TestAgentBasicFunctionality:
    """Test basic agent functionality with TestModel."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, test_agent, test_dependencies):
        """Test agent initializes correctly with dependencies."""
        assert test_agent is not None
        assert test_agent.deps_type == ToolIntegrationDependencies

    @pytest.mark.asyncio
    async def test_agent_basic_response(self, test_agent, test_dependencies):
        """Test agent provides appropriate response with TestModel."""
        # TestModel returns simple responses by default
        result = await test_agent.run(
            "Process tool integration request",
            deps=test_dependencies
        )

        assert result.data is not None
        assert isinstance(result.data, str)
        assert len(result.all_messages()) > 0

    @pytest.mark.asyncio
    async def test_agent_with_function_model(self, function_model_basic, test_dependencies):
        """Test agent with custom function model."""
        agent = tool_integration_agent.override(model=function_model_basic)

        result = await agent.run(
            "Test tool integration request",
            deps=test_dependencies
        )

        assert result.data is not None
        assert "integration" in result.data.lower()

    @pytest.mark.asyncio
    async def test_agent_tool_access(self, test_agent, test_dependencies):
        """Test agent has access to required tools."""
        tools = test_agent._tools
        tool_names = {tool.name for tool in tools}

        expected_tools = {
            "google_drive_search",
            "gmail_extract_content",
            "database_query"
        }

        assert expected_tools.issubset(tool_names), f"Missing tools: {expected_tools - tool_names}"


class TestGoogleDriveIntegration:
    """Test Google Drive search tool integration."""

    @pytest.mark.asyncio
    async def test_google_drive_search_success(
        self,
        test_agent,
        test_dependencies,
        mock_google_drive_results
    ):
        """Test successful Google Drive search operation."""
        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_google_drive_results

            # Create test context
            ctx = RunContext(deps=test_dependencies)

            # Call the tool directly
            result = await test_agent._tools[0].function(
                ctx, "quarterly report", ["docs", "pdf"], 5
            )

            assert_successful_response(result)
            assert len(result["results"]) == 2
            for doc in result["results"]:
                validate_google_drive_document(doc)

            # Verify implementation was called with correct parameters
            mock_impl.assert_called_once()
            call_args = mock_impl.call_args
            assert call_args[1]["query"] == "quarterly report"
            assert call_args[1]["file_types"] == ["docs", "pdf"]
            assert call_args[1]["max_results"] == 5

    @pytest.mark.asyncio
    async def test_google_drive_search_validation_error(self, test_agent, test_dependencies):
        """Test Google Drive search with invalid parameters."""
        ctx = RunContext(deps=test_dependencies)

        # Test empty query
        result = await test_agent._tools[0].function(ctx, "", ["docs"], 5)
        assert_error_response(result, "validation")
        assert "empty" in result["error"]["message"].lower()

        # Test invalid max_results
        result = await test_agent._tools[0].function(ctx, "test", ["docs"], 100)
        assert_error_response(result, "validation")
        assert "between 1 and 50" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_google_drive_authentication_error(
        self,
        test_agent,
        test_dependencies,
        mock_error_scenarios
    ):
        """Test Google Drive authentication failure handling."""
        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            from ..tools import AuthenticationError
            mock_impl.side_effect = AuthenticationError("Authentication failed: Invalid credentials")

            ctx = RunContext(deps=test_dependencies)
            result = await test_agent._tools[0].function(ctx, "test query", ["docs"], 5)

            assert_error_response(result, "authentication")
            assert "authentication" in result["error"]["message"].lower()
            assert result["error"]["code"] == "GDRIVE_AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_google_drive_rate_limit_error(self, test_agent, test_dependencies):
        """Test Google Drive rate limit handling."""
        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            from ..tools import RateLimitError
            mock_impl.side_effect = RateLimitError("Google Drive rate limit exceeded")

            ctx = RunContext(deps=test_dependencies)
            result = await test_agent._tools[0].function(ctx, "test query", ["docs"], 5)

            assert_error_response(result, "rate_limit")
            assert result["error"]["retry_after"] == 60


class TestGmailIntegration:
    """Test Gmail content extraction tool integration."""

    @pytest.mark.asyncio
    async def test_gmail_extract_success(
        self,
        test_agent,
        test_dependencies,
        mock_gmail_results
    ):
        """Test successful Gmail content extraction."""
        with patch('..tools.gmail_extract_content_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_gmail_results

            # Find Gmail tool
            gmail_tool = None
            for tool in test_agent._tools:
                if tool.name == "gmail_extract_content":
                    gmail_tool = tool
                    break

            assert gmail_tool is not None, "Gmail tool not found"

            ctx = RunContext(deps=test_dependencies)
            result = await gmail_tool.function(
                ctx, "from:important@company.com", None, 20
            )

            assert_successful_response(result)
            assert len(result["results"]) == 1
            for msg in result["results"]:
                validate_gmail_message(msg)

    @pytest.mark.asyncio
    async def test_gmail_extract_with_date_range(self, test_agent, test_dependencies):
        """Test Gmail extraction with date range filtering."""
        with patch('..tools.gmail_extract_content_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = {"success": True, "results": [], "metadata": {}}

            # Find Gmail tool
            gmail_tool = next(t for t in test_agent._tools if t.name == "gmail_extract_content")

            ctx = RunContext(deps=test_dependencies)
            date_range = {"start": "2025-09-01", "end": "2025-09-26"}

            result = await gmail_tool.function(
                ctx, "project update", date_range, 10
            )

            # Verify implementation was called with date range
            mock_impl.assert_called_once()
            call_args = mock_impl.call_args
            assert call_args[1]["date_range"] == date_range

    @pytest.mark.asyncio
    async def test_gmail_validation_errors(self, test_agent, test_dependencies):
        """Test Gmail extraction validation."""
        gmail_tool = next(t for t in test_agent._tools if t.name == "gmail_extract_content")
        ctx = RunContext(deps=test_dependencies)

        # Empty search query
        result = await gmail_tool.function(ctx, "", None, 20)
        assert_error_response(result, "validation")

        # Invalid max_messages
        result = await gmail_tool.function(ctx, "test", None, 150)
        assert_error_response(result, "validation")

        # Invalid date range format
        result = await gmail_tool.function(ctx, "test", {"invalid": "range"}, 20)
        assert_error_response(result, "validation")


class TestDatabaseIntegration:
    """Test database query tool integration."""

    @pytest.mark.asyncio
    async def test_database_query_success(
        self,
        test_agent,
        test_dependencies,
        mock_database_results
    ):
        """Test successful database query execution."""
        with patch('..tools.database_query_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_database_results

            # Find database tool
            db_tool = next(t for t in test_agent._tools if t.name == "database_query")

            ctx = RunContext(deps=test_dependencies)
            result = await db_tool.function(
                ctx,
                "SELECT id, name, status FROM projects",
                "postgresql",
                "json"
            )

            assert_successful_response(result)
            assert len(result["results"]) == 2
            for row in result["results"]:
                validate_database_row(row)

    @pytest.mark.asyncio
    async def test_database_query_validation(self, test_agent, test_dependencies):
        """Test database query validation."""
        db_tool = next(t for t in test_agent._tools if t.name == "database_query")
        ctx = RunContext(deps=test_dependencies)

        # Empty query
        result = await db_tool.function(ctx, "", "postgresql", "json")
        assert_error_response(result, "validation")

        # Invalid database type
        result = await db_tool.function(ctx, "SELECT * FROM test", "mongodb", "json")
        assert_error_response(result, "validation")

        # Invalid result format
        result = await db_tool.function(ctx, "SELECT * FROM test", "postgresql", "xml")
        assert_error_response(result, "validation")

    @pytest.mark.asyncio
    async def test_database_sql_injection_protection(self, test_agent, test_dependencies):
        """Test SQL injection protection."""
        with patch('..tools.database_query_impl', new_callable=AsyncMock) as mock_impl:
            from ..tools import ValidationError
            mock_impl.side_effect = ValidationError("Query contains prohibited keyword: drop")

            db_tool = next(t for t in test_agent._tools if t.name == "database_query")
            ctx = RunContext(deps=test_dependencies)

            # Test dangerous query
            result = await db_tool.function(
                ctx,
                "SELECT * FROM users; DROP TABLE users;",
                "postgresql",
                "json"
            )

            assert_error_response(result, "validation")


class TestAgentWorkflow:
    """Test complete agent workflow and integration."""

    @pytest.mark.asyncio
    async def test_run_tool_integration_agent_google_drive(
        self,
        sample_tool_requests,
        test_settings,
        mock_google_drive_results
    ):
        """Test complete workflow for Google Drive request."""
        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_google_drive_results

            request = sample_tool_requests["google_drive"]
            response = await run_tool_integration_agent(
                request=request,
                user_id="test-user",
                session_id="test-session"
            )

            assert isinstance(response, ToolResponse)
            assert response.success is True
            assert response.tool_type == "google_drive"
            assert response.request_id == request.request_id
            assert len(response.results) > 0
            assert response.extraction_quality > 0.0

    @pytest.mark.asyncio
    async def test_run_tool_integration_agent_validation_error(
        self,
        test_settings
    ):
        """Test workflow with validation error."""
        invalid_request = ToolRequest(
            request_id="test-invalid",
            tool_type="unsupported_tool",  # Invalid tool type
            operation="test",
            parameters={}
        )

        response = await run_tool_integration_agent(
            request=invalid_request,
            user_id="test-user"
        )

        assert isinstance(response, ToolResponse)
        assert response.success is False
        assert len(response.errors) > 0
        assert "unsupported" in response.errors[0].lower()

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test agent health check functionality."""
        with patch('..agent.settings') as mock_settings:
            mock_settings.use_mock_google_apis = True
            mock_settings.use_mock_database = True

            health_status = await health_check()

            assert health_status["status"] == "healthy"
            assert health_status["agent_type"] == "tool_integration"
            assert "services" in health_status
            assert health_status["services"]["google_drive"] == "healthy"
            assert health_status["services"]["gmail"] == "healthy"
            assert health_status["services"]["database"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded(self):
        """Test health check with degraded services."""
        with patch('..dependencies.ToolIntegrationDependencies.get_google_drive_service') as mock_service:
            mock_service.side_effect = Exception("Service unavailable")

            health_status = await health_check()

            assert health_status["status"] == "degraded"
            assert "google_drive" in health_status.get("issues", [])


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""

    @pytest.mark.asyncio
    async def test_network_error_handling(self, test_agent, test_dependencies):
        """Test network error handling."""
        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.side_effect = Exception("Network timeout")

            ctx = RunContext(deps=test_dependencies)
            result = await test_agent._tools[0].function(ctx, "test query", ["docs"], 5)

            assert_error_response(result, "internal")
            assert "network timeout" in result["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_partial_failure_handling(
        self,
        test_agent,
        test_dependencies
    ):
        """Test handling of partial failures."""
        # Mock scenario where some documents fail to extract
        partial_results = {
            "success": True,
            "results": [
                {
                    "document_id": "success_doc",
                    "title": "Successful Document",
                    "content": "Content extracted successfully"
                }
            ],
            "metadata": {
                "total_found": 2,
                "extracted_count": 1,
                "extraction_quality": 0.5,  # 50% success rate
                "extraction_errors": ["Failed to extract doc_2: Access denied"]
            }
        }

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = partial_results

            ctx = RunContext(deps=test_dependencies)
            result = await test_agent._tools[0].function(ctx, "test query", ["docs"], 5)

            assert_successful_response(result)
            assert result["metadata"]["extraction_quality"] == 0.5
            assert "extraction_errors" in result["metadata"]

    @pytest.mark.asyncio
    async def test_dependency_cleanup(self, test_dependencies):
        """Test proper dependency cleanup."""
        # Simulate using dependencies
        await test_dependencies.get_google_drive_service()
        await test_dependencies.get_database_connection()

        # Test cleanup
        await test_dependencies.cleanup()

        # Verify connections are cleared
        assert test_dependencies._google_drive_service is None
        assert test_dependencies._db_pool is None