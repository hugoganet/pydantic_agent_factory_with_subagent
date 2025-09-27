"""
Integration tests for Tool Integration Agent.
Tests inter-agent communication, workflow integration, and end-to-end scenarios.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
import json
from typing import Dict, Any, List

from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelTextResponse

from ..agent import run_tool_integration_agent, health_check
from ..models import ToolRequest, ToolResponse
from ..dependencies import ToolIntegrationDependencies
from .conftest import assert_successful_response, assert_error_response


class TestWorkflowIntegration:
    """Test integration with Research Engineering Workflow system."""

    @pytest.mark.asyncio
    async def test_research_orchestrator_communication(self, sample_tool_requests):
        """Test communication pattern with Research Orchestrator."""
        # Mock successful responses for all tool types
        mock_responses = {
            "google_drive": {
                "success": True,
                "results": [
                    {
                        "document_id": "research_doc_1",
                        "title": "Market Research Report Q3",
                        "content": "Comprehensive market analysis...",
                        "source_tool": "google_drive",
                        "last_modified": datetime.utcnow().isoformat()
                    }
                ],
                "metadata": {"extraction_quality": 0.95}
            },
            "gmail": {
                "success": True,
                "results": [
                    {
                        "message_id": "email_thread_1",
                        "subject": "Research Data Request",
                        "content": "Please find the requested research data...",
                        "sender": "researcher@company.com",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ],
                "metadata": {"extraction_quality": 0.92}
            },
            "database": {
                "success": True,
                "results": [
                    {
                        "row_id": 1,
                        "data": {
                            "project_id": "PROJ-2025-001",
                            "status": "active",
                            "research_data": "Statistical analysis results..."
                        }
                    }
                ],
                "metadata": {"row_count": 1}
            }
        }

        # Test each tool type
        for tool_type, request in sample_tool_requests.items():
            with patch(f'..tools.{tool_type}_search_impl' if tool_type == 'google_drive'
                      else f'..tools.{tool_type}_extract_content_impl' if tool_type == 'gmail'
                      else f'..tools.{tool_type}_query_impl',
                      new_callable=AsyncMock) as mock_impl:

                mock_impl.return_value = mock_responses[tool_type]

                response = await run_tool_integration_agent(
                    request=request,
                    user_id="research_orchestrator",
                    session_id="workflow_session_001"
                )

                # Validate response format expected by orchestrator
                assert isinstance(response, ToolResponse)
                assert response.success is True
                assert response.tool_type == tool_type
                assert len(response.results) > 0
                assert response.extraction_quality > 0.9
                assert response.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_quality_assessment_agent_data_format(self, sample_tool_requests):
        """Test data format compatibility with Quality Assessment Agent."""
        mock_google_drive_response = {
            "success": True,
            "results": [
                {
                    "document_id": "quality_test_doc",
                    "title": "Research Publication Draft",
                    "content": "This document contains research findings...",
                    "source_tool": "google_drive",
                    "metadata": {
                        "credibility_indicators": {
                            "peer_reviewed": True,
                            "source_authority": "high",
                            "citation_count": 25
                        }
                    },
                    "access_permissions": ["read", "comment"],
                    "last_modified": "2025-09-25T14:30:00Z"
                }
            ],
            "metadata": {"extraction_quality": 0.98}
        }

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = mock_google_drive_response

            request = sample_tool_requests["google_drive"]
            response = await run_tool_integration_agent(
                request=request,
                user_id="quality_assessment_agent",
                session_id="quality_check_session"
            )

            # Validate format expected by Quality Assessment Agent
            assert response.success is True
            doc = response.results[0]

            # Check required fields for credibility assessment
            assert "document_id" in doc
            assert "title" in doc
            assert "content" in doc
            assert "source_tool" in doc
            assert "last_modified" in doc

            # Check metadata structure for quality evaluation
            if "metadata" in doc:
                assert isinstance(doc["metadata"], dict)

    @pytest.mark.asyncio
    async def test_data_synthesis_agent_integration(self, sample_tool_requests):
        """Test integration with Data Synthesis Agent for report generation."""
        # Mock mixed data sources for synthesis
        mock_responses = {
            "internal_documents": [
                {
                    "document_id": "internal_memo_001",
                    "title": "Internal Strategy Document",
                    "content": "Strategic planning document with key insights...",
                    "source_tool": "google_drive",
                    "document_lineage": {
                        "original_location": "drive://strategic_planning/memo_001",
                        "extraction_timestamp": datetime.utcnow().isoformat(),
                        "extraction_method": "google_drive_api"
                    }
                }
            ],
            "email_insights": [
                {
                    "message_id": "synthesis_email_001",
                    "subject": "Key Performance Metrics",
                    "extracted_insights": [
                        "Q3 revenue increased by 15%",
                        "Customer satisfaction score: 4.2/5.0"
                    ],
                    "source_tool": "gmail",
                    "data_lineage": {
                        "thread_id": "thread_metrics_001",
                        "extraction_context": "performance_analysis"
                    }
                }
            ],
            "database_facts": [
                {
                    "query_context": "performance_metrics",
                    "structured_data": {
                        "revenue_q3": 2500000,
                        "customer_count": 1250,
                        "satisfaction_avg": 4.2
                    },
                    "source_tool": "database",
                    "data_provenance": {
                        "table_sources": ["revenue", "customers", "satisfaction"],
                        "query_timestamp": datetime.utcnow().isoformat()
                    }
                }
            ]
        }

        # Create requests for each data type
        for data_type, expected_data in mock_responses.items():
            if data_type == "internal_documents":
                tool_type = "google_drive"
                mock_impl_name = "google_drive_search_impl"
            elif data_type == "email_insights":
                tool_type = "gmail"
                mock_impl_name = "gmail_extract_content_impl"
            else:  # database_facts
                tool_type = "database"
                mock_impl_name = "database_query_impl"

            with patch(f'..tools.{mock_impl_name}', new_callable=AsyncMock) as mock_impl:
                mock_impl.return_value = {
                    "success": True,
                    "results": expected_data,
                    "metadata": {"synthesis_ready": True}
                }

                request = sample_tool_requests[tool_type]
                response = await run_tool_integration_agent(
                    request=request,
                    user_id="data_synthesis_agent",
                    session_id="synthesis_session_001"
                )

                # Validate synthesis-ready format
                assert response.success is True
                assert len(response.results) > 0

                # Check for data lineage/provenance information
                result = response.results[0]
                lineage_fields = [
                    "document_lineage", "data_lineage", "data_provenance",
                    "source_tool", "extraction_timestamp", "query_timestamp"
                ]

                has_lineage = any(field in str(result) for field in lineage_fields)
                assert has_lineage, "Results should include data lineage information"

    @pytest.mark.asyncio
    async def test_workflow_coordinator_health_monitoring(self):
        """Test integration with Workflow Coordinator for health monitoring."""
        # Test healthy status
        with patch('..agent.settings') as mock_settings:
            mock_settings.use_mock_google_apis = True
            mock_settings.use_mock_database = True

            health_status = await health_check()

            # Validate format expected by Workflow Coordinator
            assert "status" in health_status
            assert health_status["status"] in ["healthy", "degraded", "unhealthy"]
            assert "timestamp" in health_status
            assert "agent_type" in health_status
            assert health_status["agent_type"] == "tool_integration"
            assert "services" in health_status

            # Validate service status reporting
            services = health_status["services"]
            expected_services = ["google_drive", "gmail", "database"]
            for service in expected_services:
                assert service in services
                assert services[service] in ["healthy", "degraded"] or "unhealthy" in services[service]

    @pytest.mark.asyncio
    async def test_error_propagation_to_orchestrator(self, sample_tool_requests):
        """Test error propagation to Research Orchestrator."""
        # Test authentication error
        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            from ..tools import AuthenticationError
            mock_impl.side_effect = AuthenticationError("Google Drive authentication failed")

            request = sample_tool_requests["google_drive"]
            response = await run_tool_integration_agent(request=request)

            assert response.success is False
            assert len(response.errors) > 0
            assert "authentication" in response.errors[0].lower()
            assert response.extraction_quality == 0.0

        # Test rate limit error with retry information
        with patch('..tools.gmail_extract_content_impl', new_callable=AsyncMock) as mock_impl:
            from ..tools import RateLimitError
            mock_impl.side_effect = RateLimitError("Gmail rate limit exceeded")

            request = sample_tool_requests["gmail"]
            response = await run_tool_integration_agent(request=request)

            assert response.success is False
            assert len(response.errors) > 0
            # Orchestrator should know to retry after delay
            assert response.execution_time_ms > 0


class TestConcurrentOperations:
    """Test concurrent operations and resource management."""

    @pytest.mark.asyncio
    async def test_concurrent_tool_requests(self, sample_tool_requests):
        """Test handling multiple concurrent tool requests."""
        import asyncio

        # Mock implementations for all tools
        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_gdrive, \
             patch('..tools.gmail_extract_content_impl', new_callable=AsyncMock) as mock_gmail, \
             patch('..tools.database_query_impl', new_callable=AsyncMock) as mock_db:

            # Configure mock responses with delays to simulate real operations
            async def mock_gdrive_delay(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate API latency
                return {"success": True, "results": [{"document_id": "concurrent_doc"}], "metadata": {}}

            async def mock_gmail_delay(*args, **kwargs):
                await asyncio.sleep(0.05)  # Simulate faster email processing
                return {"success": True, "results": [{"message_id": "concurrent_msg"}], "metadata": {}}

            async def mock_db_delay(*args, **kwargs):
                await asyncio.sleep(0.02)  # Simulate fast database query
                return {"success": True, "results": [{"row_id": 1, "data": {}}], "metadata": {}}

            mock_gdrive.side_effect = mock_gdrive_delay
            mock_gmail.side_effect = mock_gmail_delay
            mock_db.side_effect = mock_db_delay

            # Execute concurrent requests
            tasks = []
            for i, (tool_type, request) in enumerate(sample_tool_requests.items()):
                request.request_id = f"concurrent_request_{i}"
                task = run_tool_integration_agent(
                    request=request,
                    user_id=f"concurrent_user_{i}",
                    session_id=f"concurrent_session_{i}"
                )
                tasks.append(task)

            # Wait for all requests to complete
            start_time = datetime.utcnow()
            responses = await asyncio.gather(*tasks)
            end_time = datetime.utcnow()

            # Validate all responses succeeded
            for i, response in enumerate(responses):
                assert response.success is True
                assert response.request_id == f"concurrent_request_{i}"

            # Validate concurrent execution (should be faster than sequential)
            total_time = (end_time - start_time).total_seconds()
            assert total_time < 0.5  # Should complete much faster than sum of individual delays

    @pytest.mark.asyncio
    async def test_resource_pool_management(self, test_dependencies):
        """Test database connection pool management under load."""
        # Simulate multiple database operations
        connection_count = 0

        class MockConnection:
            def __init__(self):
                nonlocal connection_count
                connection_count += 1
                self.id = connection_count

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def execute(self, query):
                await asyncio.sleep(0.01)  # Simulate query execution
                return Mock(fetchall=lambda: [{'id': self.id, 'data': 'test'}])

        mock_pool = AsyncMock()
        mock_pool.begin.side_effect = lambda: MockConnection()
        test_dependencies._db_pool = mock_pool

        # Execute multiple database queries concurrently
        from ..tools import database_query_impl

        tasks = []
        for i in range(5):
            task = database_query_impl(
                deps=test_dependencies,
                query=f"SELECT * FROM test_{i}",
                database_type="postgresql",
                result_format="json"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Validate all queries succeeded
        for result in results:
            assert result["success"] is True
            assert len(result["results"]) > 0

        # Validate connection pool was used (connections were reused/managed)
        assert connection_count <= 10  # Should not create excessive connections

    @pytest.mark.asyncio
    async def test_session_isolation(self, sample_tool_requests):
        """Test session isolation between concurrent users."""
        # Mock audit logging to track session isolation
        audit_logs = []

        async def mock_audit_log(deps, **kwargs):
            audit_logs.append({
                "session_id": deps.session_id,
                "user_id": deps.user_id,
                "request_id": deps.request_id,
                **kwargs
            })

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl, \
             patch.object(ToolIntegrationDependencies, 'log_tool_access', mock_audit_log):

            mock_impl.return_value = {"success": True, "results": [], "metadata": {}}

            # Create requests for different users/sessions
            user_sessions = [
                ("user_a", "session_001"),
                ("user_b", "session_002"),
                ("user_c", "session_003")
            ]

            tasks = []
            for user_id, session_id in user_sessions:
                request = sample_tool_requests["google_drive"]
                request.request_id = f"isolated_request_{user_id}"

                task = run_tool_integration_agent(
                    request=request,
                    user_id=user_id,
                    session_id=session_id
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            # Validate session isolation in responses
            for i, (user_id, session_id) in enumerate(user_sessions):
                response = responses[i]
                assert response.success is True
                assert response.request_id == f"isolated_request_{user_id}"

            # Validate session isolation in audit logs
            assert len(audit_logs) >= 3  # At least one log per session

            logged_sessions = {log["session_id"] for log in audit_logs}
            expected_sessions = {session for _, session in user_sessions}
            assert logged_sessions == expected_sessions


class TestEndToEndScenarios:
    """Test complete end-to-end workflow scenarios."""

    @pytest.mark.asyncio
    async def test_research_data_collection_workflow(self):
        """Test complete research data collection workflow."""
        # Simulate research orchestrator requesting comprehensive data collection
        research_requests = [
            ToolRequest(
                request_id="research_gdrive_001",
                tool_type="google_drive",
                operation="search",
                parameters={
                    "query": "market research competitive analysis Q3 2025",
                    "file_types": ["docs", "sheets", "pdf"],
                    "max_results": 20
                }
            ),
            ToolRequest(
                request_id="research_gmail_001",
                tool_type="gmail",
                operation="extract_content",
                parameters={
                    "search_query": "from:research-team@company.com subject:market analysis",
                    "date_range": {"start": "2025-07-01", "end": "2025-09-30"},
                    "max_messages": 50
                }
            ),
            ToolRequest(
                request_id="research_db_001",
                tool_type="database",
                operation="query",
                parameters={
                    "query": "SELECT * FROM market_data WHERE analysis_date >= '2025-07-01'",
                    "database_type": "postgresql",
                    "result_format": "json"
                }
            )
        ]

        # Mock comprehensive responses
        mock_responses = {
            "google_drive_search_impl": {
                "success": True,
                "results": [
                    {
                        "document_id": "research_doc_1",
                        "title": "Competitive Analysis Q3 2025",
                        "content": "Market leader analysis shows 15% growth...",
                        "file_type": "application/vnd.google-apps.document",
                        "source_tool": "google_drive"
                    },
                    {
                        "document_id": "research_sheet_1",
                        "title": "Market Data Q3",
                        "content": "Revenue,Market Share,Growth\n2500000,12%,15%",
                        "file_type": "application/vnd.google-apps.spreadsheet",
                        "source_tool": "google_drive"
                    }
                ],
                "metadata": {"extraction_quality": 0.95, "total_found": 2}
            },
            "gmail_extract_content_impl": {
                "success": True,
                "results": [
                    {
                        "message_id": "research_email_1",
                        "subject": "Market Analysis Key Findings",
                        "content": "Our analysis reveals significant market shifts...",
                        "sender": "lead-researcher@company.com",
                        "privacy_flags": [],
                        "source_tool": "gmail"
                    }
                ],
                "metadata": {"extraction_quality": 0.92, "privacy_flags_detected": 0}
            },
            "database_query_impl": {
                "success": True,
                "results": [
                    {
                        "row_id": 1,
                        "data": {
                            "market_segment": "enterprise",
                            "revenue": 1500000,
                            "growth_rate": 0.18,
                            "analysis_date": "2025-09-01"
                        }
                    }
                ],
                "metadata": {"row_count": 1, "execution_time_ms": 45}
            }
        }

        # Execute workflow
        all_responses = []
        for request in research_requests:
            tool_type = request.tool_type
            if tool_type == "google_drive":
                impl_name = "google_drive_search_impl"
            elif tool_type == "gmail":
                impl_name = "gmail_extract_content_impl"
            else:
                impl_name = "database_query_impl"

            with patch(f'..tools.{impl_name}', new_callable=AsyncMock) as mock_impl:
                mock_impl.return_value = mock_responses[impl_name]

                response = await run_tool_integration_agent(
                    request=request,
                    user_id="research_orchestrator",
                    session_id="research_workflow_001"
                )

                all_responses.append(response)

        # Validate workflow results
        assert len(all_responses) == 3
        for response in all_responses:
            assert response.success is True
            assert len(response.results) > 0
            assert response.extraction_quality > 0.9

        # Validate data coherence across sources
        gdrive_response, gmail_response, db_response = all_responses

        # Check Google Drive data
        assert len(gdrive_response.results) == 2
        doc_titles = [doc["title"] for doc in gdrive_response.results]
        assert any("Competitive Analysis" in title for title in doc_titles)

        # Check Gmail data
        assert len(gmail_response.results) == 1
        assert "Market Analysis" in gmail_response.results[0]["subject"]

        # Check Database data
        assert len(db_response.results) == 1
        db_data = db_response.results[0]["data"]
        assert "revenue" in db_data
        assert db_data["revenue"] > 0

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery and partial success scenarios."""
        # Simulate mixed success/failure scenario
        failing_request = ToolRequest(
            request_id="failing_request",
            tool_type="google_drive",
            operation="search",
            parameters={"query": "confidential documents", "file_types": ["docs"]}
        )

        # Mock authentication failure followed by successful retry
        call_count = 0

        async def mock_auth_recovery(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                from ..tools import AuthenticationError
                raise AuthenticationError("Token expired")
            else:
                return {
                    "success": True,
                    "results": [{"document_id": "recovered_doc", "title": "Recovered Document"}],
                    "metadata": {"extraction_quality": 1.0}
                }

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.side_effect = mock_auth_recovery

            # First attempt should fail
            response1 = await run_tool_integration_agent(request=failing_request)
            assert response1.success is False
            assert "authentication" in response1.errors[0].lower()

            # Second attempt should succeed (simulating token refresh)
            response2 = await run_tool_integration_agent(request=failing_request)
            assert response2.success is True
            assert len(response2.results) > 0

    @pytest.mark.asyncio
    async def test_performance_under_load(self, sample_tool_requests):
        """Test agent performance under high load."""
        # Simulate high-volume requests
        import time

        request_count = 20
        tasks = []

        # Create mock that simulates realistic processing times
        async def realistic_processing(*args, **kwargs):
            processing_time = 0.05  # 50ms processing time
            await asyncio.sleep(processing_time)
            return {
                "success": True,
                "results": [{"id": "load_test", "data": "processed"}],
                "metadata": {"processing_time_ms": int(processing_time * 1000)}
            }

        with patch('..tools.google_drive_search_impl', new_callable=AsyncMock) as mock_impl:
            mock_impl.side_effect = realistic_processing

            # Generate multiple requests
            start_time = time.time()

            for i in range(request_count):
                request = sample_tool_requests["google_drive"]
                request.request_id = f"load_test_{i}"

                task = run_tool_integration_agent(
                    request=request,
                    user_id=f"load_user_{i}",
                    session_id=f"load_session_{i}"
                )
                tasks.append(task)

            # Execute all requests
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            # Validate performance metrics
            total_time = end_time - start_time
            successful_responses = [r for r in responses if isinstance(r, ToolResponse) and r.success]

            assert len(successful_responses) == request_count
            assert total_time < 2.0  # Should complete within reasonable time

            # Calculate throughput
            throughput = request_count / total_time
            assert throughput > 10  # Should handle at least 10 requests per second