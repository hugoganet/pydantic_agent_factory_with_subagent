"""
Dependencies and external service integrations for Tool Integration Agent.
Handles Google APIs, database connections, and audit logging.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from datetime import datetime
import logging
import structlog
import json
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

import asyncpg
import aiosqlite
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import StaticPool

from .settings import ToolIntegrationSettings

logger = logging.getLogger(__name__)


@dataclass
class ToolIntegrationDependencies:
    """
    Type-safe dependency injection for Tool Integration Agent.
    Handles Google APIs, database connections, and audit logging.
    """

    # Configuration
    settings: ToolIntegrationSettings

    # Runtime Context
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None

    # Service Clients (lazy initialization)
    _google_drive_service: Optional[Any] = field(default=None, init=False, repr=False)
    _gmail_service: Optional[Any] = field(default=None, init=False, repr=False)
    _db_pool: Optional[Any] = field(default=None, init=False, repr=False)
    _audit_logger: Optional[Any] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """Initialize audit logger after instance creation."""
        self._audit_logger = self._setup_audit_logger()

    def _setup_audit_logger(self) -> structlog.BoundLogger:
        """Setup structured audit logger."""
        # Configure structlog for audit logging
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.processors.add_log_level,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.BoundLogger,
            logger_factory=structlog.PrintLoggerFactory(),
            context_class=dict,
            cache_logger_on_first_use=True,
        )

        # Create audit log directory if it doesn't exist
        log_path = Path(self.settings.audit_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Return bound logger with context
        return structlog.get_logger("tool_integration_audit").bind(
            session_id=self.session_id,
            user_id=self.user_id
        )

    async def get_google_drive_service(self):
        """Get or create Google Drive API service client."""
        if self._google_drive_service is not None:
            return self._google_drive_service

        try:
            if self.settings.use_mock_google_apis:
                self._google_drive_service = MockGoogleDriveService()
            else:
                # Load service account credentials
                credentials = service_account.Credentials.from_service_account_file(
                    self.settings.google_application_credentials,
                    scopes=self.settings.google_drive_scopes
                )

                # Build the service
                self._google_drive_service = build(
                    'drive', 'v3', credentials=credentials
                )

            logger.info("Google Drive service initialized successfully")
            return self._google_drive_service

        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            raise

    async def get_gmail_service(self):
        """Get or create Gmail API service client."""
        if self._gmail_service is not None:
            return self._gmail_service

        try:
            if self.settings.use_mock_google_apis:
                self._gmail_service = MockGmailService()
            else:
                # Load service account credentials
                credentials = service_account.Credentials.from_service_account_file(
                    self.settings.google_application_credentials,
                    scopes=self.settings.gmail_scopes
                )

                # Build the service
                self._gmail_service = build(
                    'gmail', 'v1', credentials=credentials
                )

            logger.info("Gmail service initialized successfully")
            return self._gmail_service

        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            raise

    async def get_database_connection(self):
        """Get or create database connection pool."""
        if self._db_pool is not None:
            return self._db_pool

        try:
            if self.settings.use_mock_database:
                self._db_pool = MockDatabaseConnection()
            elif self.settings.database_url.startswith('postgresql://'):
                # Create async PostgreSQL engine
                self._db_pool = create_async_engine(
                    self.settings.database_url.replace('postgresql://', 'postgresql+asyncpg://'),
                    pool_size=self.settings.database_pool_size,
                    max_overflow=self.settings.database_max_overflow,
                    echo=self.settings.debug
                )
            elif self.settings.database_url.startswith('sqlite://'):
                # Create async SQLite engine
                self._db_pool = create_async_engine(
                    self.settings.database_url.replace('sqlite://', 'sqlite+aiosqlite://'),
                    poolclass=StaticPool,
                    echo=self.settings.debug
                )
            else:
                raise ValueError(f"Unsupported database URL: {self.settings.database_url}")

            logger.info("Database connection pool initialized successfully")
            return self._db_pool

        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise

    async def log_tool_access(self,
                              tool_name: str,
                              operation: str,
                              resource_accessed: str,
                              success: bool,
                              execution_time_ms: int,
                              data_volume: int = 0,
                              error_message: Optional[str] = None):
        """
        Log tool access operation for audit purposes.

        Args:
            tool_name: Name of the tool used
            operation: Operation performed
            resource_accessed: Resource that was accessed
            success: Whether the operation succeeded
            execution_time_ms: Execution time in milliseconds
            data_volume: Amount of data processed in bytes
            error_message: Error message if operation failed
        """
        try:
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": self.request_id,
                "user_id": self.user_id,
                "session_id": self.session_id,
                "tool_name": tool_name,
                "operation": operation,
                "resource_accessed": resource_accessed,
                "success": success,
                "execution_time_ms": execution_time_ms,
                "data_volume": data_volume
            }

            if error_message:
                audit_entry["error_message"] = error_message

            # Log to structured logger
            if self._audit_logger:
                self._audit_logger.info("tool_access", **audit_entry)

            # Also write to audit file
            with open(self.settings.audit_log_file, 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    async def cleanup(self):
        """Clean up resources and connections."""
        try:
            if self._db_pool:
                if hasattr(self._db_pool, 'dispose'):
                    await self._db_pool.dispose()
                self._db_pool = None

            logger.info("Dependencies cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Mock classes for testing and development

class MockGoogleDriveService:
    """Mock Google Drive service for testing."""

    def files(self):
        return MockDriveFiles()


class MockDriveFiles:
    """Mock Google Drive files interface."""

    def list(self, **kwargs):
        return MockDriveRequest()


class MockDriveRequest:
    """Mock Google Drive request."""

    def execute(self):
        return {
            'items': [
                {
                    'id': 'mock_doc_1',
                    'name': 'Mock Document 1',
                    'mimeType': 'application/vnd.google-apps.document',
                    'modifiedTime': '2025-09-26T12:00:00Z',
                    'owners': [{'emailAddress': 'test@example.com'}]
                }
            ]
        }


class MockGmailService:
    """Mock Gmail service for testing."""

    def users(self):
        return MockGmailUsers()


class MockGmailUsers:
    """Mock Gmail users interface."""

    def messages(self):
        return MockGmailMessages()


class MockGmailMessages:
    """Mock Gmail messages interface."""

    def list(self, **kwargs):
        return MockGmailRequest()


class MockGmailRequest:
    """Mock Gmail request."""

    def execute(self):
        return {
            'messages': [
                {
                    'id': 'mock_msg_1',
                    'threadId': 'mock_thread_1'
                }
            ]
        }


class MockDatabaseConnection:
    """Mock database connection for testing."""

    async def execute(self, query: str, params: Dict[str, Any] = None):
        """Mock execute method."""
        return [
            {'id': 1, 'title': 'Mock Data 1', 'content': 'Mock content'},
            {'id': 2, 'title': 'Mock Data 2', 'content': 'Another mock content'}
        ]

    async def dispose(self):
        """Mock dispose method."""
        pass