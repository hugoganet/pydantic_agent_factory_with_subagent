"""
Test configuration for Tool Integration Agent.
Provides fixtures and test utilities for validating agent functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List
import tempfile
import os

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import tool_integration_agent
from ..dependencies import ToolIntegrationDependencies
from ..settings import ToolIntegrationSettings
from ..models import ToolRequest, GoogleDriveQuery, GmailQuery, DatabaseQuery


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Create test settings with safe defaults."""
    with tempfile.TemporaryDirectory() as temp_dir:
        return ToolIntegrationSettings(
            # LLM Configuration
            llm_api_key="test-api-key",
            llm_provider="openai",
            llm_model="gpt-4",

            # Google Services (mock mode)
            use_mock_google_apis=True,
            google_application_credentials=os.path.join(temp_dir, "fake-creds.json"),
            google_drive_max_results=50,
            gmail_max_results=100,

            # Database Configuration (mock mode)
            use_mock_database=True,
            database_url="sqlite:///test.db",
            max_query_results=100,

            # Security Settings
            rate_limit_per_minute=60,
            audit_log_file=os.path.join(temp_dir, "audit.log"),
            audit_log_level="INFO",

            # Testing flags
            debug=True
        )


@pytest.fixture
def test_dependencies(test_settings):
    """Create test dependencies with mocked services."""
    return ToolIntegrationDependencies(
        settings=test_settings,
        session_id="test-session-123",
        user_id="test-user-456",
        request_id="test-request-789"
    )


@pytest.fixture
def test_model():
    """Create TestModel for fast testing without API calls."""
    return TestModel()


@pytest.fixture
def test_agent(test_model):
    """Create agent with TestModel for testing."""
    return tool_integration_agent.override(model=test_model)


@pytest.fixture
def function_model_basic():
    """Create FunctionModel with basic responses."""

    def basic_response_function():
        call_count = 0

        async def response_function(messages, tools):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call - acknowledge request
                return ModelTextResponse(
                    content="I'll process your tool integration request"
                )
            else:
                # Subsequent calls - basic response
                return ModelTextResponse(
                    content="Tool integration completed successfully"
                )

        return response_function

    return FunctionModel(basic_response_function())


@pytest.fixture
def function_model_tool_calling():
    """Create FunctionModel that simulates tool calling behavior."""

    def tool_calling_function():
        call_count = 0

        async def response_function(messages, tools):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call - analyze request and call tool
                return {
                    "google_drive_search": {
                        "query": "test document",
                        "file_types": ["docs", "pdf"],
                        "max_results": 5
                    }
                }
            else:
                # Final response with results
                return ModelTextResponse(
                    content="Found 3 documents matching your search criteria"
                )

        return response_function

    return FunctionModel(tool_calling_function())


@pytest.fixture
def mock_google_drive_results():
    """Mock Google Drive search results."""
    return {
        "success": True,
        "results": [
            {
                "document_id": "1BvAo_test_doc_id",
                "title": "Test Document 1",
                "content": "This is a test document with sample content.",
                "file_type": "application/vnd.google-apps.document",
                "url": "https://docs.google.com/document/d/1BvAo_test_doc_id/edit",
                "last_modified": datetime.utcnow().isoformat(),
                "owner": "test@example.com",
                "permissions": ["read"],
                "size_bytes": 1024
            },
            {
                "document_id": "1CxBp_test_pdf_id",
                "title": "Test PDF Document",
                "content": "PDF content here",
                "file_type": "application/pdf",
                "url": "https://drive.google.com/file/d/1CxBp_test_pdf_id/view",
                "last_modified": datetime.utcnow().isoformat(),
                "owner": "test@example.com",
                "permissions": ["read"],
                "size_bytes": 2048
            }
        ],
        "metadata": {
            "total_found": 2,
            "extracted_count": 2,
            "extraction_quality": 1.0,
            "query_executed": "test document",
            "file_types_searched": ["docs", "pdf"]
        }
    }


@pytest.fixture
def mock_gmail_results():
    """Mock Gmail extraction results."""
    return {
        "success": True,
        "results": [
            {
                "message_id": "msg_test_123",
                "thread_id": "thread_test_456",
                "subject": "Test Email Subject",
                "content": "This is a test email with relevant content for research.",
                "sender": "sender@example.com",
                "recipients": ["recipient@example.com"],
                "timestamp": datetime.utcnow().isoformat(),
                "labels": ["INBOX", "IMPORTANT"],
                "attachments": [
                    {
                        "filename": "test_attachment.pdf",
                        "type": "application/pdf",
                        "size": "5120"
                    }
                ],
                "privacy_flags": []
            }
        ],
        "metadata": {
            "total_messages": 1,
            "extracted_count": 1,
            "threads_analyzed": 1,
            "extraction_quality": 1.0,
            "privacy_flags_detected": 0,
            "query_executed": "test query"
        }
    }


@pytest.fixture
def mock_database_results():
    """Mock database query results."""
    return {
        "success": True,
        "results": [
            {
                "row_id": 1,
                "data": {
                    "id": 1,
                    "name": "Test Record 1",
                    "status": "active",
                    "created_at": datetime.utcnow().isoformat()
                }
            },
            {
                "row_id": 2,
                "data": {
                    "id": 2,
                    "name": "Test Record 2",
                    "status": "inactive",
                    "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
                }
            }
        ],
        "metadata": {
            "query_executed": "SELECT id, name, status, created_at FROM test_table",
            "execution_time_ms": 150,
            "row_count": 2,
            "columns": ["id", "name", "status", "created_at"],
            "database_type": "postgresql",
            "result_format": "json"
        }
    }


@pytest.fixture
def sample_tool_requests():
    """Sample tool requests for testing."""
    return {
        "google_drive": ToolRequest(
            request_id="test-req-gdrive-001",
            tool_type="google_drive",
            operation="search",
            parameters={
                "query": "quarterly report",
                "file_types": ["docs", "sheets", "pdf"],
                "max_results": 10
            }
        ),
        "gmail": ToolRequest(
            request_id="test-req-gmail-001",
            tool_type="gmail",
            operation="extract_content",
            parameters={
                "search_query": "from:important@company.com subject:project update",
                "max_messages": 20,
                "date_range": {
                    "start": "2025-09-01",
                    "end": "2025-09-26"
                }
            }
        ),
        "database": ToolRequest(
            request_id="test-req-db-001",
            tool_type="database",
            operation="query",
            parameters={
                "query": "SELECT id, title, status FROM projects WHERE status = 'active'",
                "database_type": "postgresql",
                "result_format": "json"
            }
        )
    }


@pytest.fixture
def mock_error_scenarios():
    """Mock error scenarios for testing."""
    return {
        "authentication_error": {
            "success": False,
            "error": {
                "type": "authentication",
                "message": "Authentication failed: Invalid credentials",
                "code": "GDRIVE_AUTHENTICATION_ERROR"
            }
        },
        "rate_limit_error": {
            "success": False,
            "error": {
                "type": "rate_limit",
                "message": "Rate limit exceeded",
                "code": "GMAIL_RATE_LIMIT_ERROR",
                "retry_after": 60
            }
        },
        "validation_error": {
            "success": False,
            "error": {
                "type": "validation",
                "message": "Query cannot be empty",
                "code": "DB_VALIDATION_ERROR"
            }
        }
    }


# Utility functions for tests

def assert_successful_response(response: Dict[str, Any]):
    """Assert that a response indicates success."""
    assert response is not None
    assert response.get("success") is True
    assert "results" in response
    assert "metadata" in response


def assert_error_response(response: Dict[str, Any], expected_error_type: str = None):
    """Assert that a response indicates an error."""
    assert response is not None
    assert response.get("success") is False
    assert "error" in response

    if expected_error_type:
        assert response["error"].get("type") == expected_error_type


def create_mock_async_context_manager(return_value):
    """Create a mock async context manager that returns the specified value."""
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = return_value
    mock_cm.__aexit__.return_value = None
    return mock_cm


# Test data validation helpers

def validate_google_drive_document(document: Dict[str, Any]):
    """Validate structure of a Google Drive document."""
    required_fields = [
        "document_id", "title", "content", "file_type",
        "url", "last_modified", "owner", "permissions"
    ]
    for field in required_fields:
        assert field in document, f"Missing required field: {field}"


def validate_gmail_message(message: Dict[str, Any]):
    """Validate structure of a Gmail message."""
    required_fields = [
        "message_id", "thread_id", "subject", "content",
        "sender", "recipients", "timestamp", "labels"
    ]
    for field in required_fields:
        assert field in message, f"Missing required field: {field}"


def validate_database_row(row: Dict[str, Any]):
    """Validate structure of a database row."""
    required_fields = ["row_id", "data"]
    for field in required_fields:
        assert field in row, f"Missing required field: {field}"

    assert isinstance(row["data"], dict), "Row data must be a dictionary"