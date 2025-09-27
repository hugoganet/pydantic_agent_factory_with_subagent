"""
Tool implementations for Tool Integration Agent.
Provides secure access to Google Drive, Gmail, and database systems.
"""

import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import logging
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
import httpx

from .models import (
    ToolResponse,
    ToolError,
    GoogleDriveDocument,
    GmailMessage,
    DatabaseRow
)
from .dependencies import ToolIntegrationDependencies

logger = logging.getLogger(__name__)


class ToolIntegrationError(Exception):
    """Base exception for tool integration errors."""
    pass


class AuthenticationError(ToolIntegrationError):
    """Raised when authentication fails."""
    pass


class RateLimitError(ToolIntegrationError):
    """Raised when rate limits are exceeded."""
    pass


class ValidationError(ToolIntegrationError):
    """Raised when input validation fails."""
    pass


# Google Drive Tools

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(HttpError)
)
async def google_drive_search_impl(
    deps: ToolIntegrationDependencies,
    query: str,
    file_types: List[str] = ["docs", "sheets", "pdf"],
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Implementation of Google Drive document search and extraction.

    Args:
        deps: Dependencies with Google Drive service
        query: Search query for document titles and content
        file_types: File types to search
        max_results: Maximum documents to return

    Returns:
        Dict containing search results and metadata
    """
    start_time = time.time()
    request_id = deps.request_id or "unknown"

    try:
        # Get Google Drive service
        drive_service = await deps.get_google_drive_service()

        # Build search query with file type filters
        mime_type_map = {
            "docs": "application/vnd.google-apps.document",
            "sheets": "application/vnd.google-apps.spreadsheet",
            "pdf": "application/pdf",
            "slides": "application/vnd.google-apps.presentation"
        }

        mime_types = [mime_type_map.get(ft, ft) for ft in file_types if ft in mime_type_map]
        mime_type_query = " or ".join([f"mimeType='{mt}'" for mt in mime_types])

        # Construct Google Drive search query
        drive_query = f"fullText contains '{query}'"
        if mime_type_query:
            drive_query += f" and ({mime_type_query})"

        # Execute search
        results = drive_service.files().list(
            q=drive_query,
            pageSize=min(max_results, deps.settings.google_drive_max_results),
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, owners, webViewLink, size)"
        ).execute()

        documents = []
        extraction_errors = []

        # Process each found file
        for file_item in results.get('files', []):
            try:
                # Extract document content based on type
                content = await _extract_document_content(drive_service, file_item)

                document = GoogleDriveDocument(
                    document_id=file_item['id'],
                    title=file_item['name'],
                    content=content,
                    file_type=file_item['mimeType'],
                    url=file_item.get('webViewLink', ''),
                    last_modified=datetime.fromisoformat(
                        file_item['modifiedTime'].replace('Z', '+00:00')
                    ),
                    owner=file_item.get('owners', [{}])[0].get('emailAddress', 'unknown'),
                    permissions=['read'],  # Default permission, could be enhanced
                    size_bytes=int(file_item.get('size', 0)) if file_item.get('size') else None
                )

                documents.append(document.dict())

            except Exception as e:
                extraction_errors.append(f"Failed to extract {file_item['name']}: {str(e)}")
                logger.error(f"Document extraction error: {e}")

        # Calculate quality score
        extraction_quality = len(documents) / len(results.get('files', [])) if results.get('files') else 1.0

        # Prepare response
        response_data = {
            "success": True,
            "results": documents,
            "metadata": {
                "total_found": len(results.get('files', [])),
                "extracted_count": len(documents),
                "extraction_quality": extraction_quality,
                "rate_limit_remaining": 100,  # Would be actual rate limit info
                "query_executed": query,
                "file_types_searched": file_types
            }
        }

        if extraction_errors:
            response_data["metadata"]["extraction_errors"] = extraction_errors

        # Log successful operation
        execution_time_ms = int((time.time() - start_time) * 1000)
        await deps.log_tool_access(
            tool_name="google_drive_search",
            operation="document_search",
            resource_accessed=f"query:{query}",
            success=True,
            execution_time_ms=execution_time_ms,
            data_volume=sum(len(doc.get("content", "")) for doc in documents)
        )

        return response_data

    except HttpError as e:
        error_msg = f"Google Drive API error: {e}"
        logger.error(error_msg)

        await deps.log_tool_access(
            tool_name="google_drive_search",
            operation="document_search",
            resource_accessed=f"query:{query}",
            success=False,
            execution_time_ms=int((time.time() - start_time) * 1000),
            error_message=error_msg
        )

        if e.resp.status == 429:
            raise RateLimitError("Google Drive rate limit exceeded")
        elif e.resp.status in [401, 403]:
            raise AuthenticationError("Google Drive authentication failed")
        else:
            raise ToolIntegrationError(error_msg)

    except Exception as e:
        error_msg = f"Unexpected error in Google Drive search: {e}"
        logger.error(error_msg)

        await deps.log_tool_access(
            tool_name="google_drive_search",
            operation="document_search",
            resource_accessed=f"query:{query}",
            success=False,
            execution_time_ms=int((time.time() - start_time) * 1000),
            error_message=error_msg
        )

        raise ToolIntegrationError(error_msg)


async def _extract_document_content(drive_service, file_item: Dict[str, Any]) -> str:
    """Extract text content from Google Drive document."""
    try:
        file_id = file_item['id']
        mime_type = file_item['mimeType']

        if 'google-apps.document' in mime_type:
            # Export Google Doc as plain text
            content = drive_service.files().export(
                fileId=file_id,
                mimeType='text/plain'
            ).execute()
            return content.decode('utf-8') if isinstance(content, bytes) else str(content)

        elif 'google-apps.spreadsheet' in mime_type:
            # Export Google Sheet as CSV, then convert to readable format
            content = drive_service.files().export(
                fileId=file_id,
                mimeType='text/csv'
            ).execute()
            csv_content = content.decode('utf-8') if isinstance(content, bytes) else str(content)
            return f"Spreadsheet Data:\n{csv_content}"

        elif mime_type == 'application/pdf':
            # For PDFs, just return metadata (would need additional PDF parsing library)
            return f"PDF Document: {file_item['name']} (content extraction requires additional processing)"

        else:
            return f"Document type {mime_type} - content extraction not implemented"

    except Exception as e:
        logger.error(f"Content extraction failed for {file_item['name']}: {e}")
        return f"Content extraction failed: {str(e)}"


# Gmail Tools

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(HttpError)
)
async def gmail_extract_content_impl(
    deps: ToolIntegrationDependencies,
    search_query: str,
    date_range: Optional[Dict[str, str]] = None,
    max_messages: int = 20
) -> Dict[str, Any]:
    """
    Implementation of Gmail content analysis and extraction.

    Args:
        deps: Dependencies with Gmail service
        search_query: Gmail search query
        date_range: Optional date range filter
        max_messages: Maximum messages to analyze

    Returns:
        Dict containing extracted messages and metadata
    """
    start_time = time.time()
    request_id = deps.request_id or "unknown"

    try:
        # Get Gmail service
        gmail_service = await deps.get_gmail_service()

        # Build Gmail search query with date filters
        gmail_query = search_query
        if date_range:
            if 'start' in date_range:
                gmail_query += f" after:{date_range['start']}"
            if 'end' in date_range:
                gmail_query += f" before:{date_range['end']}"

        # Search for messages
        messages_result = gmail_service.users().messages().list(
            userId='me',
            q=gmail_query,
            maxResults=min(max_messages, deps.settings.gmail_max_results)
        ).execute()

        messages_data = []
        extraction_errors = []
        privacy_flags_count = 0

        # Process each message
        for message_ref in messages_result.get('messages', []):
            try:
                # Get full message details
                message = gmail_service.users().messages().get(
                    userId='me',
                    messageId=message_ref['id'],
                    format='full'
                ).execute()

                # Extract message content and metadata
                extracted_message, privacy_flags = await _extract_gmail_message(message)
                if privacy_flags:
                    privacy_flags_count += 1

                messages_data.append(extracted_message.dict())

            except Exception as e:
                extraction_errors.append(f"Failed to extract message {message_ref['id']}: {str(e)}")
                logger.error(f"Message extraction error: {e}")

        # Calculate extraction quality
        total_messages = len(messages_result.get('messages', []))
        extraction_quality = len(messages_data) / total_messages if total_messages > 0 else 1.0

        # Prepare response
        response_data = {
            "success": True,
            "results": messages_data,
            "metadata": {
                "total_messages": total_messages,
                "extracted_count": len(messages_data),
                "threads_analyzed": len(set(msg.get("thread_id") for msg in messages_data)),
                "extraction_quality": extraction_quality,
                "privacy_flags_detected": privacy_flags_count,
                "query_executed": search_query,
                "date_range": date_range
            }
        }

        if extraction_errors:
            response_data["metadata"]["extraction_errors"] = extraction_errors

        # Log successful operation
        execution_time_ms = int((time.time() - start_time) * 1000)
        await deps.log_tool_access(
            tool_name="gmail_extract_content",
            operation="message_extraction",
            resource_accessed=f"query:{search_query}",
            success=True,
            execution_time_ms=execution_time_ms,
            data_volume=sum(len(msg.get("content", "")) for msg in messages_data)
        )

        return response_data

    except HttpError as e:
        error_msg = f"Gmail API error: {e}"
        logger.error(error_msg)

        await deps.log_tool_access(
            tool_name="gmail_extract_content",
            operation="message_extraction",
            resource_accessed=f"query:{search_query}",
            success=False,
            execution_time_ms=int((time.time() - start_time) * 1000),
            error_message=error_msg
        )

        if e.resp.status == 429:
            raise RateLimitError("Gmail rate limit exceeded")
        elif e.resp.status in [401, 403]:
            raise AuthenticationError("Gmail authentication failed")
        else:
            raise ToolIntegrationError(error_msg)

    except Exception as e:
        error_msg = f"Unexpected error in Gmail extraction: {e}"
        logger.error(error_msg)

        await deps.log_tool_access(
            tool_name="gmail_extract_content",
            operation="message_extraction",
            resource_accessed=f"query:{search_query}",
            success=False,
            execution_time_ms=int((time.time() - start_time) * 1000),
            error_message=error_msg
        )

        raise ToolIntegrationError(error_msg)


async def _extract_gmail_message(message: Dict[str, Any]) -> tuple[GmailMessage, List[str]]:
    """Extract content from Gmail message and detect privacy flags."""
    headers = message['payload'].get('headers', [])
    header_dict = {h['name']: h['value'] for h in headers}

    # Extract basic message info
    subject = header_dict.get('Subject', 'No Subject')
    sender = header_dict.get('From', 'Unknown')
    recipients = _parse_email_list(header_dict.get('To', ''))

    # Extract message body
    body_content = await _extract_message_body(message['payload'])

    # Detect privacy/sensitivity flags
    privacy_flags = _detect_privacy_flags(subject, body_content, message.get('labelIds', []))

    gmail_message = GmailMessage(
        message_id=message['id'],
        thread_id=message['threadId'],
        subject=subject,
        content=body_content,
        sender=sender,
        recipients=recipients,
        timestamp=datetime.fromtimestamp(int(message['internalDate']) / 1000),
        labels=message.get('labelIds', []),
        attachments=_extract_attachments(message['payload']),
        privacy_flags=privacy_flags
    )

    return gmail_message, privacy_flags


async def _extract_message_body(payload: Dict[str, Any]) -> str:
    """Extract text content from Gmail message payload."""
    body_content = ""

    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                import base64
                decoded = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                body_content += decoded + "\n"
    elif payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
        import base64
        body_content = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

    return body_content.strip()


def _parse_email_list(email_string: str) -> List[str]:
    """Parse comma-separated email addresses."""
    if not email_string:
        return []

    # Simple email extraction (could be enhanced with proper parsing)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, email_string)
    return emails


def _detect_privacy_flags(subject: str, content: str, labels: List[str]) -> List[str]:
    """Detect privacy and sensitivity indicators in email content."""
    privacy_flags = []

    # Check for sensitive labels
    sensitive_labels = ['CONFIDENTIAL', 'PRIVATE', 'RESTRICTED']
    for label in labels:
        if any(sens in label.upper() for sens in sensitive_labels):
            privacy_flags.append(f"sensitive_label:{label}")

    # Check for privacy keywords in subject/content
    privacy_keywords = [
        'confidential', 'private', 'secret', 'sensitive', 'restricted',
        'ssn', 'social security', 'credit card', 'password', 'credentials'
    ]

    combined_text = (subject + " " + content).lower()
    for keyword in privacy_keywords:
        if keyword in combined_text:
            privacy_flags.append(f"privacy_keyword:{keyword}")

    return list(set(privacy_flags))  # Remove duplicates


def _extract_attachments(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract attachment metadata from message payload."""
    attachments = []

    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('filename'):
                attachments.append({
                    'filename': part['filename'],
                    'type': part['mimeType'],
                    'size': str(part['body'].get('size', 0))
                })

    return attachments


# Database Tools

async def database_query_impl(
    deps: ToolIntegrationDependencies,
    query: str,
    database_type: str,
    result_format: str = "json"
) -> Dict[str, Any]:
    """
    Implementation of secure database query execution.

    Args:
        deps: Dependencies with database connection
        query: SQL SELECT query to execute
        database_type: Type of database (postgresql/sqlite)
        result_format: Format for results (json/csv)

    Returns:
        Dict containing query results and metadata
    """
    start_time = time.time()
    request_id = deps.request_id or "unknown"

    try:
        # Validate query safety
        _validate_sql_query(query)

        # Get database connection
        db_pool = await deps.get_database_connection()

        # Execute query based on database type
        if database_type == "postgresql":
            results = await _execute_postgresql_query(db_pool, query)
        elif database_type == "sqlite":
            results = await _execute_sqlite_query(db_pool, query)
        else:
            raise ValidationError(f"Unsupported database type: {database_type}")

        # Format results
        formatted_results = []
        for i, row in enumerate(results[:deps.settings.max_query_results]):
            formatted_results.append({
                "row_id": i + 1,
                "data": dict(row) if hasattr(row, 'keys') else row
            })

        # Prepare response
        response_data = {
            "success": True,
            "results": formatted_results,
            "metadata": {
                "query_executed": _sanitize_query_for_log(query),
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "row_count": len(formatted_results),
                "columns": list(formatted_results[0]["data"].keys()) if formatted_results else [],
                "database_type": database_type,
                "result_format": result_format
            }
        }

        # Log successful operation
        execution_time_ms = int((time.time() - start_time) * 1000)
        await deps.log_tool_access(
            tool_name="database_query",
            operation="query_execution",
            resource_accessed=f"db:{database_type}",
            success=True,
            execution_time_ms=execution_time_ms,
            data_volume=len(json.dumps(formatted_results))
        )

        return response_data

    except ValidationError as e:
        error_msg = f"Query validation error: {e}"
        logger.error(error_msg)

        await deps.log_tool_access(
            tool_name="database_query",
            operation="query_execution",
            resource_accessed=f"db:{database_type}",
            success=False,
            execution_time_ms=int((time.time() - start_time) * 1000),
            error_message=error_msg
        )

        raise

    except Exception as e:
        error_msg = f"Database query error: {e}"
        logger.error(error_msg)

        await deps.log_tool_access(
            tool_name="database_query",
            operation="query_execution",
            resource_accessed=f"db:{database_type}",
            success=False,
            execution_time_ms=int((time.time() - start_time) * 1000),
            error_message=error_msg
        )

        raise ToolIntegrationError(error_msg)


def _validate_sql_query(query: str) -> None:
    """Validate SQL query for security and safety."""
    query_lower = query.lower().strip()

    # Must start with SELECT
    if not query_lower.startswith('select'):
        raise ValidationError("Only SELECT queries are allowed")

    # Block dangerous operations
    dangerous_keywords = [
        'insert', 'update', 'delete', 'drop', 'create', 'alter',
        'truncate', 'exec', 'execute', 'sp_', 'xp_', 'into', 'merge'
    ]

    for keyword in dangerous_keywords:
        if keyword in query_lower:
            raise ValidationError(f"Query contains prohibited keyword: {keyword}")

    # Check for potential SQL injection patterns
    injection_patterns = [
        r'--', r'/\*', r'\*/', r';.*--', r'union.*select',
        r'or.*1.*=.*1', r'and.*1.*=.*1'
    ]

    for pattern in injection_patterns:
        if re.search(pattern, query_lower):
            raise ValidationError(f"Query contains potential injection pattern: {pattern}")


async def _execute_postgresql_query(db_pool, query: str) -> List[Dict[str, Any]]:
    """Execute query against PostgreSQL database."""
    async with db_pool.begin() as conn:
        result = await conn.execute(query)
        return [dict(row) for row in result.fetchall()]


async def _execute_sqlite_query(db_pool, query: str) -> List[Dict[str, Any]]:
    """Execute query against SQLite database."""
    async with db_pool.begin() as conn:
        result = await conn.execute(query)
        columns = result.keys()
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def _sanitize_query_for_log(query: str) -> str:
    """Sanitize SQL query for logging purposes."""
    # Remove potential sensitive data patterns
    sanitized = re.sub(r"'[^']*'", "'***'", query)
    sanitized = re.sub(r'"[^"]*"', '"***"', sanitized)
    return sanitized