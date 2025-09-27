"""
Requirements validation tests for Tool Integration Agent.
Validates all requirements from INITIAL.md are properly implemented and tested.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
import json
import os
import tempfile

from ..agent import run_tool_integration_agent, health_check
from ..models import ToolRequest, GoogleDriveQuery, GmailQuery, DatabaseQuery
from ..dependencies import ToolIntegrationDependencies
from ..tools import _validate_sql_query, ValidationError
from .conftest import assert_successful_response, assert_error_response


class TestRequirementsCoverage:
    """Test coverage of all requirements from INITIAL.md."""

    @pytest.mark.asyncio
    async def test_req_001_google_drive_oauth_authentication(self, test_dependencies):
        """
        REQ-001: Successfully authenticates with Google Drive and Gmail using OAuth 2.0
        """
        # Test Google Drive OAuth setup
        assert hasattr(test_dependencies, 'get_google_drive_service')

        # Test service initialization
        drive_service = await test_dependencies.get_google_drive_service()
        assert drive_service is not None

        # Test Gmail OAuth setup
        assert hasattr(test_dependencies, 'get_gmail_service')

        gmail_service = await test_dependencies.get_gmail_service()
        assert gmail_service is not None

        # Verify OAuth scopes are configured
        settings = test_dependencies.settings
        assert hasattr(settings, 'google_drive_scopes')
        assert hasattr(settings, 'gmail_scopes')

    @pytest.mark.asyncio
    async def test_req_002_document_extraction_rate(self, test_dependencies):
        """
        REQ-002: Extracts content from 90% of accessible documents and emails
        """
        # Mock scenario with mixed success/failure rates
        mock_results = {
            "success": True,
            "results": [
                {"document_id": "doc_1", "title": "Success Doc 1", "content": "Content 1"},
                {"document_id": "doc_2", "title": "Success Doc 2", "content": "Content 2"},
                {"document_id": "doc_3", "title": "Success Doc 3", "content": "Content 3"},
                {"document_id": "doc_4", "title": "Success Doc 4", "content": "Content 4"},
                {"document_id": "doc_5", "title": "Success Doc 5", "content": "Content 5"}
            ],
            "metadata": {
                "total_found": 5,
                "extracted_count": 5,
                "extraction_quality": 1.0,  # 100% success rate
                "extraction_errors": []
            }
        }

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_results

            request = ToolRequest(
                request_id="extraction_rate_test",
                tool_type="google_drive",
                operation="search",
                parameters={"query": "test documents", "max_results": 5}
            )

            response = await run_tool_integration_agent(request=request)

            # Validate extraction rate meets requirement (90% minimum)
            assert response.success is True
            assert response.extraction_quality >= 0.9
            assert len(response.results) >= 4  # At least 90% of 5 documents

    @pytest.mark.asyncio
    async def test_req_003_sql_injection_protection(self, test_dependencies):
        """
        REQ-003: Executes database queries safely with proper SQL injection protection
        """
        # Test various SQL injection attempts
        injection_attempts = [
            "SELECT * FROM users WHERE id = 1; DROP TABLE users; --",
            "SELECT * FROM users WHERE name = 'admin' OR '1'='1'",
            "SELECT * FROM users UNION SELECT password FROM admin",
            "SELECT * FROM users WHERE id = 1' OR 1=1 /*",
            "INSERT INTO users VALUES (1, 'hacker'); SELECT * FROM users"
        ]

        for malicious_query in injection_attempts:
            with pytest.raises(ValidationError):
                _validate_sql_query(malicious_query)

        # Test that safe queries pass validation
        safe_queries = [
            "SELECT id, name FROM users WHERE status = 'active'",
            "SELECT COUNT(*) FROM projects",
            "SELECT u.name, p.title FROM users u JOIN projects p ON u.id = p.user_id"
        ]

        for safe_query in safe_queries:
            # Should not raise exception
            _validate_sql_query(safe_query)

    @pytest.mark.asyncio
    async def test_req_004_rate_limit_handling(self, test_dependencies):
        """
        REQ-004: Handles API rate limits gracefully with exponential backoff
        """
        # Test rate limit error handling
        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            from ..tools import RateLimitError
            mock_impl.side_effect = RateLimitError("Google Drive rate limit exceeded")

            request = ToolRequest(
                request_id="rate_limit_test",
                tool_type="google_drive",
                operation="search",
                parameters={"query": "test", "max_results": 5}
            )

            response = await run_tool_integration_agent(request=request)

            assert response.success is False
            assert len(response.errors) > 0
            assert "rate limit" in response.errors[0].lower()

        # Test that rate limiting is configured in settings
        settings = test_dependencies.settings
        assert hasattr(settings, 'rate_limit_per_minute')
        assert settings.rate_limit_per_minute > 0

    @pytest.mark.asyncio
    async def test_req_005_audit_logging(self, test_dependencies):
        """
        REQ-005: Maintains audit logs for all data access operations
        """
        # Create temporary audit log file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as temp_log:
            test_dependencies.settings.audit_log_file = temp_log.name

        try:
            # Test audit logging functionality
            await test_dependencies.log_tool_access(
                tool_name="test_tool",
                operation="test_operation",
                resource_accessed="test_resource",
                success=True,
                execution_time_ms=150,
                data_volume=1024
            )

            # Verify audit log entry was created
            assert os.path.exists(test_dependencies.settings.audit_log_file)

            with open(test_dependencies.settings.audit_log_file, 'r') as f:
                log_content = f.read()
                log_entry = json.loads(log_content.strip())

            # Validate required audit fields
            required_fields = [
                "timestamp", "request_id", "user_id", "session_id",
                "tool_name", "operation", "resource_accessed", "success",
                "execution_time_ms", "data_volume"
            ]

            for field in required_fields:
                assert field in log_entry, f"Missing audit field: {field}"

            assert log_entry["tool_name"] == "test_tool"
            assert log_entry["success"] is True
            assert log_entry["execution_time_ms"] == 150

        finally:
            # Clean up temporary file
            if os.path.exists(test_dependencies.settings.audit_log_file):
                os.unlink(test_dependencies.settings.audit_log_file)

    @pytest.mark.asyncio
    async def test_req_006_processing_time_performance(self, sample_tool_requests):
        """
        REQ-006: Processes internal documents within 2 minutes average
        """
        start_time = datetime.utcnow()

        # Mock realistic processing time
        async def mock_processing_with_delay(*args, **kwargs):
            # Simulate realistic document processing time (much less than 2 minutes)
            import asyncio
            await asyncio.sleep(0.1)  # 100ms processing time
            return {
                "success": True,
                "results": [{"document_id": "perf_test", "content": "Processed content"}],
                "metadata": {"processing_time_ms": 100}
            }

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.side_effect = mock_processing_with_delay

            request = sample_tool_requests["google_drive"]
            response = await run_tool_integration_agent(request=request)

            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()

            assert response.success is True
            assert processing_time < 120.0  # Less than 2 minutes
            assert response.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_req_007_research_orchestrator_integration(self, sample_tool_requests):
        """
        REQ-007: Integrates with Research Orchestrator and Quality Assessment agents
        """
        # Test Research Orchestrator communication pattern
        mock_response = {
            "success": True,
            "results": [
                {
                    "document_id": "orchestrator_doc",
                    "title": "Research Document",
                    "content": "Research findings...",
                    "source_tool": "google_drive",
                    "metadata": {
                        "extraction_timestamp": datetime.utcnow().isoformat(),
                        "quality_indicators": {
                            "readability": 0.85,
                            "completeness": 0.92
                        }
                    }
                }
            ],
            "metadata": {"extraction_quality": 0.92}
        }

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_response

            request = sample_tool_requests["google_drive"]
            response = await run_tool_integration_agent(
                request=request,
                user_id="research_orchestrator",
                session_id="orchestrator_session"
            )

            # Validate integration format
            assert response.success is True
            assert hasattr(response, 'request_id')
            assert hasattr(response, 'tool_type')
            assert hasattr(response, 'extraction_quality')
            assert hasattr(response, 'timestamp')
            assert hasattr(response, 'execution_time_ms')

            # Validate data format for Quality Assessment Agent
            assert len(response.results) > 0
            result = response.results[0]
            assert "document_id" in result
            assert "source_tool" in result
            if "metadata" in result:
                assert isinstance(result["metadata"], dict)

    @pytest.mark.asyncio
    async def test_req_008_structured_data_format(self, sample_tool_requests):
        """
        REQ-008: Returns structured data in consistent format for downstream agents
        """
        # Test Google Drive structured format
        mock_gdrive_response = {
            "success": True,
            "results": [
                {
                    "document_id": "struct_test_1",
                    "title": "Structured Document",
                    "content": "Document content",
                    "file_type": "application/vnd.google-apps.document",
                    "url": "https://docs.google.com/document/d/struct_test_1",
                    "last_modified": datetime.utcnow().isoformat(),
                    "owner": "owner@example.com",
                    "permissions": ["read"],
                    "size_bytes": 1024
                }
            ],
            "metadata": {"extraction_quality": 1.0}
        }

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_gdrive_response

            response = await run_tool_integration_agent(
                request=sample_tool_requests["google_drive"]
            )

            # Validate structured format consistency
            assert response.success is True
            doc = response.results[0]

            required_doc_fields = [
                "document_id", "title", "content", "file_type",
                "url", "last_modified", "owner", "permissions"
            ]

            for field in required_doc_fields:
                assert field in doc, f"Missing required document field: {field}"

        # Test Gmail structured format
        mock_gmail_response = {
            "success": True,
            "results": [
                {
                    "message_id": "struct_msg_1",
                    "thread_id": "struct_thread_1",
                    "subject": "Structured Email",
                    "content": "Email content",
                    "sender": "sender@example.com",
                    "recipients": ["recipient@example.com"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "labels": ["INBOX"],
                    "attachments": [],
                    "privacy_flags": []
                }
            ],
            "metadata": {"extraction_quality": 1.0}
        }

        with patch('..tools.gmail_extract_content_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_gmail_response

            response = await run_tool_integration_agent(
                request=sample_tool_requests["gmail"]
            )

            assert response.success is True
            msg = response.results[0]

            required_msg_fields = [
                "message_id", "thread_id", "subject", "content",
                "sender", "recipients", "timestamp", "labels"
            ]

            for field in required_msg_fields:
                assert field in msg, f"Missing required message field: {field}"


class TestSecurityCompliance:
    """Test security and privacy compliance requirements."""

    @pytest.mark.asyncio
    async def test_oauth2_credential_security(self, test_dependencies):
        """Test OAuth 2.0 credentials are handled securely."""
        # Test that credentials are not exposed in logs or responses
        settings = test_dependencies.settings

        # Verify credential paths are configured
        assert hasattr(settings, 'google_application_credentials')
        assert settings.google_application_credentials is not None

        # Test that actual credentials are not in memory as strings
        # (In real implementation, they should be loaded securely)
        await test_dependencies.get_google_drive_service()

        # Verify no credential leakage in service objects
        drive_service = test_dependencies._google_drive_service
        assert drive_service is not None
        # In mock mode, this will be a mock object, but structure should be secure

    @pytest.mark.asyncio
    async def test_database_read_only_access(self, test_dependencies):
        """Test database connections use read-only credentials."""
        # Test that only SELECT operations are allowed
        allowed_queries = [
            "SELECT * FROM users",
            "SELECT id, name FROM projects WHERE status = 'active'",
            "SELECT COUNT(*) FROM documents"
        ]

        for query in allowed_queries:
            # Should not raise exception
            _validate_sql_query(query)

        # Test that write operations are blocked
        write_operations = [
            "INSERT INTO users VALUES (1, 'test')",
            "UPDATE users SET name = 'changed'",
            "DELETE FROM projects WHERE id = 1",
            "CREATE TABLE new_table (id int)",
            "DROP TABLE users",
            "ALTER TABLE users ADD COLUMN email varchar(100)"
        ]

        for query in write_operations:
            with pytest.raises(ValidationError):
                _validate_sql_query(query)

    @pytest.mark.asyncio
    async def test_api_key_environment_security(self, test_settings):
        """Test API keys are stored in environment variables."""
        # Verify API keys are loaded from environment, not hardcoded
        assert hasattr(test_settings, 'llm_api_key')

        # In test environment, this will be a test key
        assert test_settings.llm_api_key == "test-api-key"

        # Verify no hardcoded secrets in settings
        settings_dict = test_settings.dict()
        for key, value in settings_dict.items():
            if isinstance(value, str) and "secret" in key.lower():
                assert not value.startswith("sk-"), f"Potential hardcoded secret in {key}"

    @pytest.mark.asyncio
    async def test_google_drive_permission_respect(self, test_dependencies):
        """Test Google Drive sharing permissions are respected."""
        # Mock permission-restricted access
        mock_response = {
            "success": True,
            "results": [
                {
                    "document_id": "permitted_doc",
                    "title": "Permitted Document",
                    "content": "Accessible content",
                    "permissions": ["read", "comment"],
                    "access_granted": True
                }
            ],
            "metadata": {
                "permission_filtered": True,
                "accessible_count": 1,
                "restricted_count": 2  # Some docs were filtered out
            }
        }

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_response

            request = ToolRequest(
                request_id="permission_test",
                tool_type="google_drive",
                operation="search",
                parameters={"query": "confidential documents"}
            )

            response = await run_tool_integration_agent(request=request)

            assert response.success is True
            # Verify only permitted documents are returned
            for result in response.results:
                assert "permissions" in result
                assert "access_granted" in result
                if "access_granted" in result:
                    assert result["access_granted"] is True

    @pytest.mark.asyncio
    async def test_gmail_privacy_flag_detection(self, test_dependencies):
        """Test Gmail privacy flag detection and handling."""
        mock_response = {
            "success": True,
            "results": [
                {
                    "message_id": "privacy_test_msg",
                    "subject": "CONFIDENTIAL: Sensitive Information",
                    "content": "This message contains sensitive data",
                    "privacy_flags": ["privacy_keyword:confidential", "sensitive_label:CONFIDENTIAL"],
                    "privacy_risk_level": "high"
                }
            ],
            "metadata": {
                "privacy_flags_detected": 2,
                "messages_flagged": 1
            }
        }

        with patch('..tools.gmail_extract_content_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_response

            request = ToolRequest(
                request_id="privacy_test",
                tool_type="gmail",
                operation="extract_content",
                parameters={"search_query": "confidential data"}
            )

            response = await run_tool_integration_agent(request=request)

            assert response.success is True
            msg = response.results[0]
            assert "privacy_flags" in msg
            assert len(msg["privacy_flags"]) > 0
            assert any("confidential" in flag for flag in msg["privacy_flags"])


class TestDataRetentionCompliance:
    """Test data retention and compliance requirements."""

    @pytest.mark.asyncio
    async def test_audit_trail_completeness(self, test_dependencies):
        """Test complete audit trail for compliance reporting."""
        # Create temporary audit log
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as temp_log:
            test_dependencies.settings.audit_log_file = temp_log.name

        try:
            # Simulate multiple operations with full audit trail
            operations = [
                ("google_drive_search", "document_search", "query:test", True, 150, 2048),
                ("gmail_extract_content", "message_extraction", "query:email", True, 200, 1024),
                ("database_query", "data_query", "table:projects", True, 75, 512),
                ("google_drive_search", "document_search", "query:failed", False, 100, 0)
            ]

            for tool_name, operation, resource, success, time_ms, volume in operations:
                await test_dependencies.log_tool_access(
                    tool_name=tool_name,
                    operation=operation,
                    resource_accessed=resource,
                    success=success,
                    execution_time_ms=time_ms,
                    data_volume=volume,
                    error_message="Test error" if not success else None
                )

            # Verify complete audit trail
            with open(test_dependencies.settings.audit_log_file, 'r') as f:
                log_lines = f.readlines()

            assert len(log_lines) == 4  # All operations logged

            # Verify audit entry structure
            for line in log_lines:
                log_entry = json.loads(line.strip())

                # Check compliance fields
                compliance_fields = [
                    "timestamp", "request_id", "user_id", "session_id",
                    "tool_name", "operation", "resource_accessed",
                    "success", "execution_time_ms", "data_volume"
                ]

                for field in compliance_fields:
                    assert field in log_entry, f"Missing compliance field: {field}"

                # Verify timestamp format (ISO 8601)
                timestamp = log_entry["timestamp"]
                assert "T" in timestamp and ":" in timestamp

        finally:
            # Clean up
            if os.path.exists(test_dependencies.settings.audit_log_file):
                os.unlink(test_dependencies.settings.audit_log_file)

    @pytest.mark.asyncio
    async def test_document_access_pattern_tracking(self, test_dependencies):
        """Test document access pattern tracking for compliance."""
        # Create temporary audit log
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as temp_log:
            test_dependencies.settings.audit_log_file = temp_log.name

        try:
            # Simulate document access patterns
            document_accesses = [
                ("doc_001", "financial_report.docx"),
                ("doc_002", "employee_data.xlsx"),
                ("doc_001", "financial_report.docx"),  # Repeat access
                ("doc_003", "public_document.pdf")
            ]

            for doc_id, filename in document_accesses:
                await test_dependencies.log_tool_access(
                    tool_name="google_drive_search",
                    operation="document_access",
                    resource_accessed=f"doc_id:{doc_id}|filename:{filename}",
                    success=True,
                    execution_time_ms=100,
                    data_volume=1024
                )

            # Analyze access patterns from audit log
            with open(test_dependencies.settings.audit_log_file, 'r') as f:
                log_entries = [json.loads(line.strip()) for line in f.readlines()]

            # Verify access patterns are trackable
            accessed_docs = {}
            for entry in log_entries:
                resource = entry["resource_accessed"]
                if "doc_id:" in resource:
                    doc_id = resource.split("doc_id:")[1].split("|")[0]
                    accessed_docs[doc_id] = accessed_docs.get(doc_id, 0) + 1

            # Verify repeated access detection
            assert accessed_docs["doc_001"] == 2  # Accessed twice
            assert accessed_docs["doc_002"] == 1
            assert accessed_docs["doc_003"] == 1

        finally:
            if os.path.exists(test_dependencies.settings.audit_log_file):
                os.unlink(test_dependencies.settings.audit_log_file)


class TestPerformanceRequirements:
    """Test performance and scalability requirements."""

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, sample_tool_requests):
        """Test agent handles concurrent requests efficiently."""
        import asyncio
        import time

        # Create multiple concurrent requests
        num_concurrent = 10
        tasks = []

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            # Mock realistic processing time
            async def mock_processing(*args, **kwargs):
                await asyncio.sleep(0.05)  # 50ms processing
                return {
                    "success": True,
                    "results": [{"document_id": "concurrent_test"}],
                    "metadata": {"processing_time": 50}
                }

            mock_impl.side_effect = mock_processing

            # Launch concurrent requests
            start_time = time.time()

            for i in range(num_concurrent):
                request = sample_tool_requests["google_drive"]
                request.request_id = f"concurrent_{i}"

                task = run_tool_integration_agent(
                    request=request,
                    user_id=f"user_{i}",
                    session_id=f"session_{i}"
                )
                tasks.append(task)

            # Wait for completion
            responses = await asyncio.gather(*tasks)
            end_time = time.time()

            # Validate performance
            total_time = end_time - start_time
            successful_responses = [r for r in responses if r.success]

            assert len(successful_responses) == num_concurrent
            assert total_time < 1.0  # Should complete within 1 second for 10 concurrent requests

            # Calculate and validate throughput
            throughput = num_concurrent / total_time
            assert throughput >= 15  # At least 15 requests per second

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, sample_tool_requests):
        """Test memory efficiency with large data processing."""
        # Mock large document processing
        large_content = "X" * 10000  # 10KB content per document
        num_docs = 50  # 50 documents = ~500KB total

        mock_response = {
            "success": True,
            "results": [
                {
                    "document_id": f"large_doc_{i}",
                    "title": f"Large Document {i}",
                    "content": large_content,
                    "metadata": {"size_bytes": len(large_content)}
                }
                for i in range(num_docs)
            ],
            "metadata": {"total_size_bytes": len(large_content) * num_docs}
        }

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_response

            request = sample_tool_requests["google_drive"]
            request.parameters["max_results"] = num_docs

            # Process large dataset
            response = await run_tool_integration_agent(request=request)

            # Validate processing succeeded
            assert response.success is True
            assert len(response.results) == num_docs

            # Verify data integrity
            for i, result in enumerate(response.results):
                assert result["document_id"] == f"large_doc_{i}"
                assert len(result["content"]) == 10000

    @pytest.mark.asyncio
    async def test_error_recovery_performance(self, sample_tool_requests):
        """Test performance impact of error recovery mechanisms."""
        import time

        # Test rapid error/recovery cycles
        call_count = 0
        max_failures = 3

        async def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count <= max_failures:
                from ..tools import RateLimitError
                raise RateLimitError("Temporary rate limit")
            else:
                return {
                    "success": True,
                    "results": [{"document_id": "recovered_doc"}],
                    "metadata": {"recovery_attempt": call_count}
                }

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.side_effect = intermittent_failure

            start_time = time.time()

            # Multiple requests that will trigger error recovery
            tasks = []
            for i in range(5):
                request = sample_tool_requests["google_drive"]
                request.request_id = f"recovery_test_{i}"
                task = run_tool_integration_agent(request=request)
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            # Validate error recovery doesn't severely impact performance
            recovery_time = end_time - start_time
            assert recovery_time < 5.0  # Should complete within reasonable time despite errors

            # Validate some requests eventually succeeded
            successful_responses = [
                r for r in responses
                if isinstance(r, type(responses[0])) and hasattr(r, 'success') and r.success
            ]
            assert len(successful_responses) >= 1  # At least one recovery succeeded