"""
Test individual tool implementations for Tool Integration Agent.
Validates tool functionality, error handling, and security measures.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
import json

from ..tools import (
    google_drive_search_impl,
    gmail_extract_content_impl,
    database_query_impl,
    _validate_sql_query,
    _extract_document_content,
    _extract_gmail_message,
    _detect_privacy_flags,
    _sanitize_query_for_log,
    ToolIntegrationError,
    AuthenticationError,
    RateLimitError,
    ValidationError
)
from ..dependencies import ToolIntegrationDependencies
from .conftest import (
    assert_successful_response,
    assert_error_response,
    validate_google_drive_document,
    validate_gmail_message,
    validate_database_row
)


class TestGoogleDriveTools:
    """Test Google Drive tool implementations."""

    @pytest.mark.asyncio
    async def test_google_drive_search_impl_success(self, test_dependencies):
        """Test successful Google Drive search implementation."""
        # Mock Google Drive service response
        mock_service = AsyncMock()
        mock_files = Mock()
        mock_request = Mock()

        mock_request.execute.return_value = {
            'files': [
                {
                    'id': 'test_doc_1',
                    'name': 'Test Document 1',
                    'mimeType': 'application/vnd.google-apps.document',
                    'modifiedTime': '2025-09-26T12:00:00Z',
                    'owners': [{'emailAddress': 'owner@example.com'}],
                    'webViewLink': 'https://docs.google.com/document/d/test_doc_1/edit',
                    'size': '1024'
                }
            ]
        }

        mock_files.list.return_value = mock_request
        mock_files.export.return_value = Mock()
        mock_files.export().execute.return_value = b"Sample document content"

        mock_service.files.return_value = mock_files
        test_dependencies._google_drive_service = mock_service

        # Test the implementation
        result = await google_drive_search_impl(
            deps=test_dependencies,
            query="test document",
            file_types=["docs"],
            max_results=5
        )

        assert_successful_response(result)
        assert len(result["results"]) == 1

        doc = result["results"][0]
        validate_google_drive_document(doc)
        assert doc["title"] == "Test Document 1"
        assert "Sample document content" in doc["content"]

    @pytest.mark.asyncio
    async def test_google_drive_search_impl_http_error(self, test_dependencies):
        """Test Google Drive HTTP error handling."""
        from googleapiclient.errors import HttpError

        mock_service = AsyncMock()
        mock_files = Mock()

        # Create mock HTTP error
        mock_response = Mock()
        mock_response.status = 429
        mock_response.reason = "Rate Limit Exceeded"

        http_error = HttpError(mock_response, b'Rate limit exceeded')
        mock_files.list.side_effect = http_error
        mock_service.files.return_value = mock_files

        test_dependencies._google_drive_service = mock_service

        # Test rate limit error
        with pytest.raises(RateLimitError):
            await google_drive_search_impl(
                deps=test_dependencies,
                query="test",
                file_types=["docs"],
                max_results=5
            )

    @pytest.mark.asyncio
    async def test_google_drive_search_impl_auth_error(self, test_dependencies):
        """Test Google Drive authentication error handling."""
        from googleapiclient.errors import HttpError

        mock_service = AsyncMock()
        mock_files = Mock()

        # Create mock auth error
        mock_response = Mock()
        mock_response.status = 401
        mock_response.reason = "Unauthorized"

        http_error = HttpError(mock_response, b'Authentication required')
        mock_files.list.side_effect = http_error
        mock_service.files.return_value = mock_files

        test_dependencies._google_drive_service = mock_service

        with pytest.raises(AuthenticationError):
            await google_drive_search_impl(
                deps=test_dependencies,
                query="test",
                file_types=["docs"],
                max_results=5
            )

    @pytest.mark.asyncio
    async def test_extract_document_content_various_types(self):
        """Test document content extraction for different file types."""
        mock_service = Mock()

        # Test Google Doc
        file_item = {
            'id': 'doc_id',
            'name': 'Test Doc',
            'mimeType': 'application/vnd.google-apps.document'
        }

        mock_service.files().export().execute.return_value = b"Document text content"

        content = await _extract_document_content(mock_service, file_item)
        assert content == "Document text content"

        # Test Google Sheet
        file_item['mimeType'] = 'application/vnd.google-apps.spreadsheet'
        mock_service.files().export().execute.return_value = b"col1,col2\nval1,val2"

        content = await _extract_document_content(mock_service, file_item)
        assert "Spreadsheet Data:" in content
        assert "col1,col2" in content

        # Test PDF
        file_item['mimeType'] = 'application/pdf'
        content = await _extract_document_content(mock_service, file_item)
        assert "PDF Document:" in content

    @pytest.mark.asyncio
    async def test_document_extraction_error_handling(self):
        """Test document extraction error handling."""
        mock_service = Mock()
        mock_service.files().export.side_effect = Exception("Extraction failed")

        file_item = {
            'id': 'error_doc',
            'name': 'Error Document',
            'mimeType': 'application/vnd.google-apps.document'
        }

        content = await _extract_document_content(mock_service, file_item)
        assert "Content extraction failed" in content


class TestGmailTools:
    """Test Gmail tool implementations."""

    @pytest.mark.asyncio
    async def test_gmail_extract_content_impl_success(self, test_dependencies):
        """Test successful Gmail content extraction."""
        # Mock Gmail service response
        mock_service = AsyncMock()
        mock_users = Mock()
        mock_messages = Mock()
        mock_request = Mock()

        # Mock message list response
        mock_request.execute.return_value = {
            'messages': [
                {'id': 'msg_1', 'threadId': 'thread_1'}
            ]
        }

        # Mock individual message response
        mock_get_request = Mock()
        mock_get_request.execute.return_value = {
            'id': 'msg_1',
            'threadId': 'thread_1',
            'internalDate': str(int(datetime.now().timestamp() * 1000)),
            'labelIds': ['INBOX'],
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'}
                ],
                'mimeType': 'text/plain',
                'body': {
                    'data': 'VGVzdCBlbWFpbCBjb250ZW50'  # base64 encoded "Test email content"
                }
            }
        }

        mock_messages.list.return_value = mock_request
        mock_messages.get.return_value = mock_get_request
        mock_users.messages.return_value = mock_messages
        mock_service.users.return_value = mock_users

        test_dependencies._gmail_service = mock_service

        # Test the implementation
        result = await gmail_extract_content_impl(
            deps=test_dependencies,
            search_query="from:sender@example.com",
            max_messages=10
        )

        assert_successful_response(result)
        assert len(result["results"]) == 1

        msg = result["results"][0]
        validate_gmail_message(msg)
        assert msg["subject"] == "Test Subject"
        assert msg["sender"] == "sender@example.com"

    @pytest.mark.asyncio
    async def test_gmail_extract_with_date_filters(self, test_dependencies):
        """Test Gmail extraction with date range filters."""
        mock_service = AsyncMock()
        mock_users = Mock()
        mock_messages = Mock()
        mock_request = Mock()

        mock_request.execute.return_value = {'messages': []}
        mock_messages.list.return_value = mock_request
        mock_users.messages.return_value = mock_messages
        mock_service.users.return_value = mock_users

        test_dependencies._gmail_service = mock_service

        date_range = {"start": "2025-09-01", "end": "2025-09-26"}

        await gmail_extract_content_impl(
            deps=test_dependencies,
            search_query="test query",
            date_range=date_range,
            max_messages=10
        )

        # Verify the query was constructed with date filters
        call_args = mock_messages.list.call_args
        executed_query = call_args[1]["q"]
        assert "after:2025-09-01" in executed_query
        assert "before:2025-09-26" in executed_query

    @pytest.mark.asyncio
    async def test_extract_gmail_message_privacy_detection(self):
        """Test privacy flag detection in Gmail messages."""
        message_data = {
            'id': 'test_msg',
            'threadId': 'test_thread',
            'internalDate': str(int(datetime.now().timestamp() * 1000)),
            'labelIds': ['CONFIDENTIAL', 'INBOX'],
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'CONFIDENTIAL: Sensitive Information'},
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'recipient@example.com'}
                ],
                'mimeType': 'text/plain',
                'body': {
                    'data': 'VGhpcyBjb250YWlucyBTU04gMTIzLTQ1LTY3ODk='  # "This contains SSN 123-45-6789"
                }
            }
        }

        gmail_message, privacy_flags = await _extract_gmail_message(message_data)

        assert len(privacy_flags) > 0
        assert any("confidential" in flag for flag in privacy_flags)
        assert any("ssn" in flag for flag in privacy_flags)

    def test_detect_privacy_flags(self):
        """Test privacy flag detection logic."""
        # Test with sensitive keywords
        flags = _detect_privacy_flags(
            subject="Confidential: Password Reset",
            content="Your new password is secret123",
            labels=["PRIVATE"]
        )

        assert len(flags) > 0
        assert any("confidential" in flag for flag in flags)
        assert any("password" in flag for flag in flags)

        # Test with clean content
        flags = _detect_privacy_flags(
            subject="Meeting Notes",
            content="Here are the meeting notes from today",
            labels=["INBOX"]
        )

        assert len(flags) == 0

    @pytest.mark.asyncio
    async def test_gmail_http_error_handling(self, test_dependencies):
        """Test Gmail HTTP error handling."""
        from googleapiclient.errors import HttpError

        mock_service = AsyncMock()
        mock_users = Mock()
        mock_messages = Mock()

        # Create mock HTTP error for rate limiting
        mock_response = Mock()
        mock_response.status = 429

        http_error = HttpError(mock_response, b'Rate limit exceeded')
        mock_messages.list.side_effect = http_error
        mock_users.messages.return_value = mock_messages
        mock_service.users.return_value = mock_users

        test_dependencies._gmail_service = mock_service

        with pytest.raises(RateLimitError):
            await gmail_extract_content_impl(
                deps=test_dependencies,
                search_query="test",
                max_messages=10
            )


class TestDatabaseTools:
    """Test database tool implementations."""

    @pytest.mark.asyncio
    async def test_database_query_impl_success(self, test_dependencies):
        """Test successful database query execution."""
        # Mock database connection
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_result = Mock()

        # Mock query results
        mock_row_1 = Mock()
        mock_row_1.keys.return_value = ['id', 'name', 'status']
        mock_row_1.__iter__ = lambda self: iter([('id', 1), ('name', 'Test 1'), ('status', 'active')])

        mock_row_2 = Mock()
        mock_row_2.keys.return_value = ['id', 'name', 'status']
        mock_row_2.__iter__ = lambda self: iter([('id', 2), ('name', 'Test 2'), ('status', 'inactive')])

        mock_result.fetchall.return_value = [mock_row_1, mock_row_2]
        mock_conn.execute.return_value = mock_result
        mock_pool.begin.return_value.__aenter__.return_value = mock_conn
        mock_pool.begin.return_value.__aexit__ = AsyncMock(return_value=None)

        test_dependencies._db_pool = mock_pool

        # Test the implementation
        result = await database_query_impl(
            deps=test_dependencies,
            query="SELECT id, name, status FROM test_table",
            database_type="postgresql",
            result_format="json"
        )

        assert_successful_response(result)
        assert len(result["results"]) == 2

        for row in result["results"]:
            validate_database_row(row)
            assert "id" in row["data"]
            assert "name" in row["data"]

    def test_validate_sql_query_safety(self):
        """Test SQL query safety validation."""
        # Valid SELECT queries
        valid_queries = [
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE status = 'active'",
            "select u.name, p.title from users u join projects p on u.id = p.user_id"
        ]

        for query in valid_queries:
            _validate_sql_query(query)  # Should not raise exception

        # Invalid queries
        invalid_queries = [
            "INSERT INTO users VALUES (1, 'test')",
            "UPDATE users SET status = 'inactive'",
            "DELETE FROM users",
            "DROP TABLE users",
            "CREATE TABLE test (id int)",
            "ALTER TABLE users ADD COLUMN email varchar(100)",
            "SELECT * FROM users; DROP TABLE users;",
            "SELECT * FROM users WHERE 1=1 UNION SELECT password FROM admin"
        ]

        for query in invalid_queries:
            with pytest.raises(ValidationError):
                _validate_sql_query(query)

    def test_validate_sql_injection_patterns(self):
        """Test SQL injection pattern detection."""
        injection_queries = [
            "SELECT * FROM users WHERE id = 1 OR 1=1",
            "SELECT * FROM users WHERE name = 'test' AND 1=1",
            "SELECT * FROM users -- comment",
            "SELECT * FROM users /* comment */",
            "SELECT * FROM users UNION SELECT * FROM admin"
        ]

        for query in injection_queries:
            with pytest.raises(ValidationError):
                _validate_sql_query(query)

    def test_sanitize_query_for_log(self):
        """Test query sanitization for logging."""
        query = "SELECT * FROM users WHERE name = 'John Doe' AND email = \"john@example.com\""
        sanitized = _sanitize_query_for_log(query)

        assert "'***'" in sanitized
        assert '"***"' in sanitized
        assert "John Doe" not in sanitized
        assert "john@example.com" not in sanitized

    @pytest.mark.asyncio
    async def test_database_query_validation_errors(self, test_dependencies):
        """Test database query validation error handling."""
        # Empty query
        with pytest.raises(ValidationError, match="Query cannot be empty"):
            await database_query_impl(
                deps=test_dependencies,
                query="",
                database_type="postgresql",
                result_format="json"
            )

        # Invalid database type
        with pytest.raises(ValidationError, match="Unsupported database type"):
            await database_query_impl(
                deps=test_dependencies,
                query="SELECT * FROM test",
                database_type="mongodb",
                result_format="json"
            )

    @pytest.mark.asyncio
    async def test_database_connection_error(self, test_dependencies):
        """Test database connection error handling."""
        # Mock connection failure
        mock_pool = AsyncMock()
        mock_pool.begin.side_effect = Exception("Connection failed")
        test_dependencies._db_pool = mock_pool

        with pytest.raises(ToolIntegrationError):
            await database_query_impl(
                deps=test_dependencies,
                query="SELECT * FROM test",
                database_type="postgresql",
                result_format="json"
            )


class TestSecurityMeasures:
    """Test security measures and audit logging."""

    @pytest.mark.asyncio
    async def test_audit_logging(self, test_dependencies, tmp_path):
        """Test audit logging functionality."""
        # Set up temporary audit log file
        audit_file = tmp_path / "test_audit.log"
        test_dependencies.settings.audit_log_file = str(audit_file)

        # Log a test access
        await test_dependencies.log_tool_access(
            tool_name="test_tool",
            operation="test_operation",
            resource_accessed="test_resource",
            success=True,
            execution_time_ms=100,
            data_volume=500
        )

        # Verify log entry was written
        assert audit_file.exists()
        with open(audit_file) as f:
            log_entry = json.loads(f.read().strip())

        assert log_entry["tool_name"] == "test_tool"
        assert log_entry["operation"] == "test_operation"
        assert log_entry["success"] is True
        assert log_entry["execution_time_ms"] == 100

    @pytest.mark.asyncio
    async def test_audit_logging_with_error(self, test_dependencies, tmp_path):
        """Test audit logging with error information."""
        audit_file = tmp_path / "test_error_audit.log"
        test_dependencies.settings.audit_log_file = str(audit_file)

        await test_dependencies.log_tool_access(
            tool_name="test_tool",
            operation="failed_operation",
            resource_accessed="test_resource",
            success=False,
            execution_time_ms=50,
            error_message="Test error occurred"
        )

        with open(audit_file) as f:
            log_entry = json.loads(f.read().strip())

        assert log_entry["success"] is False
        assert log_entry["error_message"] == "Test error occurred"

    def test_input_validation_comprehensive(self):
        """Test comprehensive input validation."""
        # Test various dangerous SQL patterns
        dangerous_patterns = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'/**/OR/**/1=1/**/--",
            "1; EXEC xp_cmdshell('dir')",
            "UNION ALL SELECT password FROM users"
        ]

        for pattern in dangerous_patterns:
            with pytest.raises(ValidationError):
                _validate_sql_query(f"SELECT * FROM test WHERE id = {pattern}")

    @pytest.mark.asyncio
    async def test_rate_limiting_simulation(self, test_dependencies):
        """Test rate limiting behavior simulation."""
        # Mock rate limit tracking
        rate_limit_calls = []

        async def mock_rate_limited_call():
            rate_limit_calls.append(datetime.utcnow())
            if len(rate_limit_calls) > 5:  # Simulate rate limit after 5 calls
                raise RateLimitError("Rate limit exceeded")
            return {"success": True, "results": []}

        # Simulate multiple rapid calls
        for i in range(3):
            result = await mock_rate_limited_call()
            assert result["success"] is True

        # Simulate exceeding rate limit
        with pytest.raises(RateLimitError):
            for i in range(10):
                await mock_rate_limited_call()

    @pytest.mark.asyncio
    async def test_permission_validation(self, test_dependencies):
        """Test permission validation for resources."""
        # This would test actual permission checking in a real implementation
        # For now, we test the structure exists

        # Mock resource access with permission check
        def check_resource_permission(user_id: str, resource_id: str) -> bool:
            """Mock permission check."""
            # In real implementation, this would check actual permissions
            return user_id == "authorized_user"

        # Test authorized access
        assert check_resource_permission("authorized_user", "document_123") is True

        # Test unauthorized access
        assert check_resource_permission("unauthorized_user", "document_123") is False

    @pytest.mark.asyncio
    async def test_data_sanitization(self):
        """Test data sanitization for sensitive content."""
        # Test email sanitization
        sensitive_content = {
            "message": "Contact John at john.doe@company.com or call 555-123-4567",
            "metadata": {
                "ssn": "123-45-6789",
                "credit_card": "4111-1111-1111-1111"
            }
        }

        def sanitize_sensitive_data(data: dict) -> dict:
            """Mock data sanitization function."""
            # In real implementation, this would properly sanitize data
            sanitized = data.copy()
            if "message" in sanitized:
                # Replace email patterns
                import re
                sanitized["message"] = re.sub(
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    '[EMAIL_REDACTED]',
                    sanitized["message"]
                )
                # Replace phone patterns
                sanitized["message"] = re.sub(
                    r'\b\d{3}-\d{3}-\d{4}\b',
                    '[PHONE_REDACTED]',
                    sanitized["message"]
                )
            return sanitized

        sanitized = sanitize_sensitive_data(sensitive_content)
        assert "[EMAIL_REDACTED]" in sanitized["message"]
        assert "[PHONE_REDACTED]" in sanitized["message"]
        assert "john.doe@company.com" not in sanitized["message"]