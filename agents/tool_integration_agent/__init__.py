"""
Tool Integration Agent - Secure interface to enterprise tools and APIs.

This agent provides secure access to Google Drive, Gmail, and database systems
for the Research Engineering Workflow, maintaining strict security and audit compliance.
"""

from .agent import (
    tool_integration_agent,
    run_tool_integration_agent,
    health_check
)
from .models import (
    ToolRequest,
    ToolResponse,
    GoogleDriveQuery,
    GmailQuery,
    DatabaseQuery,
    InternalDocument
)
from .dependencies import ToolIntegrationDependencies
from .settings import load_settings

__version__ = "1.0.0"
__all__ = [
    # Main agent and functions
    "tool_integration_agent",
    "run_tool_integration_agent",
    "health_check",

    # Data models
    "ToolRequest",
    "ToolResponse",
    "GoogleDriveQuery",
    "GmailQuery",
    "DatabaseQuery",
    "InternalDocument",

    # Configuration
    "ToolIntegrationDependencies",
    "load_settings"
]