"""
Pydantic models for Tool Integration Agent input/output structures.
Defines structured data models for tool requests, responses, and internal documents.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
from uuid import uuid4


class ToolRequest(BaseModel):
    """Request model for tool integration operations."""

    request_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique request identifier")
    tool_type: Literal["google_drive", "gmail", "database"] = Field(
        ..., description="Type of tool to use"
    )
    operation: str = Field(..., description="Operation to perform")
    parameters: Dict[str, Any] = Field(..., description="Operation-specific parameters")
    authentication: Dict[str, str] = Field(
        default_factory=dict, description="Authentication context"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional filters to apply"
    )

    @validator('tool_type')
    def validate_tool_type(cls, v):
        """Validate tool type is supported."""
        supported_tools = {"google_drive", "gmail", "database"}
        if v not in supported_tools:
            raise ValueError(f"Tool type must be one of {supported_tools}")
        return v


class GoogleDriveQuery(BaseModel):
    """Specific query model for Google Drive operations."""

    query: str = Field(..., description="Search query for document titles and content")
    file_types: List[str] = Field(
        default=["docs", "sheets", "pdf"],
        description="File types to search"
    )
    folder_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific folder IDs to search within"
    )
    date_range: Optional[Dict[str, str]] = Field(
        default=None,
        description="Date range filter with 'start' and 'end' keys"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum results to return"
    )


class GmailQuery(BaseModel):
    """Specific query model for Gmail operations."""

    search_query: str = Field(
        ...,
        description="Gmail search query (supports Gmail search operators)"
    )
    date_range: Optional[Dict[str, str]] = Field(
        default=None,
        description="Date range with 'start' and 'end' in YYYY-MM-DD format"
    )
    max_messages: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum messages to analyze"
    )


class DatabaseQuery(BaseModel):
    """Specific query model for database operations."""

    query: str = Field(..., description="SELECT SQL query to execute")
    database_type: Literal["postgresql", "sqlite"] = Field(
        ..., description="Type of database"
    )
    result_format: Literal["json", "csv"] = Field(
        default="json",
        description="Format for query results"
    )
    max_rows: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum rows to return"
    )

    @validator('query')
    def validate_query_safety(cls, v):
        """Validate query is safe (SELECT only)."""
        query_lower = v.lower().strip()
        if not query_lower.startswith('select'):
            raise ValueError("Only SELECT queries are allowed")

        # Block dangerous operations
        dangerous_keywords = [
            'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'truncate', 'exec', 'execute', 'sp_', 'xp_'
        ]
        for keyword in dangerous_keywords:
            if keyword in query_lower:
                raise ValueError(f"Query contains prohibited keyword: {keyword}")

        return v


class InternalDocument(BaseModel):
    """Model for internal documents extracted from various sources."""

    document_id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Extracted document content")
    source_tool: str = Field(..., description="Tool used to extract the document")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional document metadata"
    )
    access_permissions: List[str] = Field(
        default_factory=list,
        description="Document access permissions"
    )
    last_modified: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last modification timestamp"
    )
    extraction_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the document was extracted"
    )
    quality_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Quality score of the extracted content"
    )


class ToolResponse(BaseModel):
    """Standard response model for tool integration operations."""

    request_id: str = Field(..., description="Original request identifier")
    tool_type: str = Field(..., description="Tool that processed the request")
    success: bool = Field(..., description="Whether the operation succeeded")
    results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Operation results"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Response metadata and metrics"
    )
    extraction_quality: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Overall quality of data extraction"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )
    execution_time_ms: int = Field(
        default=0,
        ge=0,
        description="Execution time in milliseconds"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Any errors that occurred during processing"
    )


class ToolError(BaseModel):
    """Standard error response model."""

    request_id: str = Field(..., description="Original request identifier")
    tool_type: str = Field(..., description="Tool that encountered the error")
    error_type: Literal[
        "authentication",
        "rate_limit",
        "validation",
        "network",
        "permission",
        "internal"
    ] = Field(..., description="Type of error encountered")
    error_message: str = Field(..., description="Human-readable error description")
    error_code: str = Field(..., description="Machine-readable error code")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )
    retry_after: Optional[int] = Field(
        default=None,
        description="Seconds to wait before retry (for rate limit errors)"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error details"
    )


class GoogleDriveDocument(BaseModel):
    """Model for Google Drive document metadata and content."""

    document_id: str = Field(..., description="Google Drive document ID")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Extracted plain text content")
    file_type: str = Field(..., description="Document file type")
    url: str = Field(..., description="Document URL")
    last_modified: datetime = Field(..., description="Last modification date")
    owner: str = Field(..., description="Document owner email")
    permissions: List[str] = Field(
        default_factory=list,
        description="Document sharing permissions"
    )
    size_bytes: Optional[int] = Field(
        default=None,
        description="Document size in bytes"
    )


class GmailMessage(BaseModel):
    """Model for Gmail message metadata and content."""

    message_id: str = Field(..., description="Gmail message ID")
    thread_id: str = Field(..., description="Gmail thread ID")
    subject: str = Field(..., description="Email subject")
    content: str = Field(..., description="Cleaned message body")
    sender: str = Field(..., description="Sender email address")
    recipients: List[str] = Field(
        default_factory=list,
        description="Recipient email addresses"
    )
    timestamp: datetime = Field(..., description="Message timestamp")
    labels: List[str] = Field(
        default_factory=list,
        description="Gmail labels applied to message"
    )
    attachments: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Attachment metadata (filename, type, size)"
    )
    privacy_flags: List[str] = Field(
        default_factory=list,
        description="Detected privacy/sensitivity flags"
    )


class DatabaseRow(BaseModel):
    """Model for database query result rows."""

    row_id: int = Field(..., description="Row identifier")
    data: Dict[str, Any] = Field(..., description="Column name to value mapping")
    table_name: str = Field(..., description="Source table name")
    query_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the query was executed"
    )