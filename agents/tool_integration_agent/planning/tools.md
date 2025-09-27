# Tool Integration Agent - Tool Specifications

## Overview
This document specifies the 3 essential tools for the Tool Integration Agent that provides secure access to Google Drive, Gmail, and database systems within the Research Engineering Workflow.

**Philosophy**: Simple, secure, single-purpose tools with robust error handling and OAuth 2.0 authentication.

---

## Tool 1: Google Drive Document Search and Extraction

### Tool Name: `google_drive_search`

### Description
Search Google Drive documents by query with file type and date filters, then extract content from matching documents. Handles OAuth 2.0 authentication and respects sharing permissions.

### Parameters
- `query` (str, required): Search query for document titles and content
- `file_types` (List[str], optional): File types to search ["docs", "sheets", "pdf", "slides"]
- `max_results` (int, optional): Maximum documents to return (default: 10, max: 50)

### Authentication Requirements
- OAuth 2.0 flow with Google Drive API scopes
- Credentials stored in `GOOGLE_DRIVE_CREDENTIALS_PATH` environment variable
- Automatic token refresh handling

### Return Format
```python
{
    "success": bool,
    "results": [
        {
            "document_id": str,
            "title": str,
            "content": str,  # Extracted plain text
            "file_type": str,
            "url": str,
            "last_modified": datetime,
            "owner": str,
            "permissions": List[str]
        }
    ],
    "metadata": {
        "total_found": int,
        "extraction_quality": float,  # 0.0-1.0 success rate
        "rate_limit_remaining": int
    }
}
```

### Error Handling
- **Authentication Errors**: Return clear message for token refresh or permission issues
- **Rate Limiting**: Implement exponential backoff (1s, 2s, 4s, 8s intervals)
- **Content Extraction Failures**: Include partial results with error flags
- **Network Issues**: Retry up to 3 times with increasing delays

### Security Considerations
- Respect Google Drive sharing permissions
- Log all document access with request ID and timestamp
- Never cache sensitive document content
- Validate file types to prevent arbitrary file access

---

## Tool 2: Gmail Content Analysis and Extraction

### Tool Name: `gmail_extract_content`

### Description
Extract relevant information from Gmail messages with threading support and metadata analysis. Focuses on research-relevant content while respecting privacy boundaries.

### Parameters
- `search_query` (str, required): Gmail search query (supports Gmail search operators)
- `date_range` (Dict[str, str], optional): {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
- `max_messages` (int, optional): Maximum messages to analyze (default: 20, max: 100)

### Authentication Requirements
- OAuth 2.0 flow with Gmail API read-only scopes
- Credentials stored in `GMAIL_API_CREDENTIALS` environment variable
- Automatic token refresh with secure storage

### Return Format
```python
{
    "success": bool,
    "results": [
        {
            "message_id": str,
            "thread_id": str,
            "subject": str,
            "content": str,  # Cleaned message body
            "sender": str,
            "recipients": List[str],
            "timestamp": datetime,
            "labels": List[str],
            "attachments": List[Dict[str, str]]  # filename, type, size
        }
    ],
    "metadata": {
        "total_messages": int,
        "threads_analyzed": int,
        "extraction_quality": float,
        "privacy_flags": List[str]  # Detected sensitive content types
    }
}
```

### Error Handling
- **Authentication Issues**: Clear OAuth error messages with refresh guidance
- **Rate Limiting**: Gmail API quota management with 250 quota units/user/second
- **Content Processing**: Skip corrupted messages, log partial failures
- **Privacy Protection**: Detect and flag PII, skip messages with sensitive labels

### Security Considerations
- Read-only access to authorized mailboxes only
- Audit log all email access operations
- Filter out emails marked as confidential/private
- Respect organizational email retention policies

---

## Tool 3: Database Query Execution (Read-Only)

### Tool Name: `database_query`

### Description
Execute safe SELECT queries against PostgreSQL and SQLite databases with SQL injection protection and result formatting for research data extraction.

### Parameters
- `query` (str, required): SELECT SQL query to execute
- `database_type` (str, required): "postgresql" or "sqlite"
- `result_format` (str, optional): "json" or "csv" (default: "json")

### Authentication Requirements
- Database connection strings in environment variables
- Read-only database user credentials with minimal table permissions
- Connection pooling with secure credential management

### Return Format
```python
{
    "success": bool,
    "results": [
        {
            "row_id": int,
            "data": Dict[str, Any]  # Column name -> value mapping
        }
    ],
    "metadata": {
        "query_executed": str,  # Sanitized query for audit
        "execution_time_ms": int,
        "row_count": int,
        "columns": List[str],
        "database_type": str
    }
}
```

### Error Handling
- **SQL Injection Prevention**: Use parameterized queries, whitelist table/column names
- **Query Validation**: Block non-SELECT statements, limit query complexity
- **Connection Issues**: Retry logic with connection pool management
- **Result Size Limits**: Enforce maximum rows (100) and timeout (30 seconds)

### Security Considerations
- **Query Sanitization**: Strict SQL parsing to allow only SELECT operations
- **Table Permissions**: Access only to approved tables/views
- **Audit Logging**: Log all queries with user context and execution time
- **Data Masking**: Automatically mask PII fields in query results

### Allowed Query Patterns
```sql
-- ✅ Allowed
SELECT column1, column2 FROM approved_table WHERE condition = ?
SELECT COUNT(*) FROM public.research_data WHERE created_at > ?
SELECT * FROM reports WHERE status = 'published' LIMIT 50

-- ❌ Blocked
INSERT, UPDATE, DELETE, DROP, CREATE statements
Queries accessing system tables or restricted schemas
Queries without WHERE clauses on large tables (>1000 rows)
Complex JOINs spanning more than 3 tables
```

---

## Implementation Guidelines

### Common Error Response Format
All tools should return consistent error responses:
```python
{
    "success": False,
    "error": {
        "type": str,  # "authentication", "rate_limit", "validation", "network"
        "message": str,  # Human-readable error description
        "code": str,  # Machine-readable error code
        "retry_after": Optional[int]  # Seconds to wait before retry
    },
    "metadata": {
        "timestamp": datetime,
        "request_id": str
    }
}
```

### Rate Limiting Strategy
- **Google Drive API**: 100 requests/100 seconds/user
- **Gmail API**: 250 quota units/user/second
- **Database Queries**: 60 queries/minute/user
- **Implementation**: Use `asyncio.Semaphore` with exponential backoff

### Caching Strategy
- **Document Content**: No persistent caching for security
- **API Tokens**: Secure in-memory cache with auto-refresh
- **Query Results**: Short-term cache (5 minutes) for identical queries
- **Metadata**: Cache file/message metadata for 1 hour

### Audit Logging Requirements
```python
{
    "timestamp": datetime,
    "request_id": str,
    "tool_name": str,
    "user_context": str,
    "operation": str,
    "resource_accessed": str,  # Document ID, message ID, table name
    "success": bool,
    "execution_time_ms": int,
    "data_volume": int  # Bytes extracted/returned
}
```

### Testing Strategy
- **Unit Tests**: Mock external APIs with realistic response data
- **Integration Tests**: Test OAuth flows with sandbox credentials
- **Security Tests**: Validate SQL injection prevention and access controls
- **Performance Tests**: Verify rate limiting and timeout handling

---

## Tool Registration Pattern

```python
def register_tools(agent, deps_type):
    """Register all integration tools with the agent."""

    @agent.tool
    async def google_drive_search(
        ctx: RunContext[deps_type],
        query: str,
        file_types: List[str] = ["docs", "sheets", "pdf"],
        max_results: int = 10
    ) -> Dict[str, Any]:
        # Implementation delegates to standalone function

    @agent.tool
    async def gmail_extract_content(
        ctx: RunContext[deps_type],
        search_query: str,
        date_range: Optional[Dict[str, str]] = None,
        max_messages: int = 20
    ) -> Dict[str, Any]:
        # Implementation delegates to standalone function

    @agent.tool
    async def database_query(
        ctx: RunContext[deps_type],
        query: str,
        database_type: str,
        result_format: str = "json"
    ) -> Dict[str, Any]:
        # Implementation delegates to standalone function
```

---

## Dependencies Required

### Python Packages
```text
google-api-python-client==2.70.0  # Google Drive/Gmail APIs
google-auth-oauthlib==0.8.0       # OAuth 2.0 authentication
google-auth==2.15.0               # Google authentication
asyncpg==0.29.0                   # PostgreSQL async driver
aiosqlite==0.18.0                 # SQLite async driver
tenacity==8.2.0                   # Retry logic
pydantic==2.5.0                   # Data validation
httpx==0.25.0                     # HTTP client for API calls
```

### Environment Variables
```bash
# Google Services Authentication
GOOGLE_DRIVE_CREDENTIALS_PATH=./credentials/google-drive.json
GMAIL_API_CREDENTIALS=./credentials/gmail.json

# Database Configuration
DATABASE_URL=postgresql://readonly_user:password@host:5432/research_db
SQLITE_DB_PATH=./data/local_research.db

# Security & Rate Limiting
MAX_QUERY_RESULTS=100
RATE_LIMIT_PER_MINUTE=60
AUDIT_LOG_LEVEL=INFO
AUDIT_LOG_PATH=./logs/tool_access.log
```

---

## Success Criteria

### Functionality
- ✅ Successfully authenticate with Google services using OAuth 2.0
- ✅ Extract content from 90% of accessible documents and emails
- ✅ Execute database queries safely with SQL injection protection
- ✅ Handle API rate limits with exponential backoff

### Security
- ✅ All sensitive data access operations logged with audit trail
- ✅ OAuth tokens managed securely with automatic refresh
- ✅ Database access limited to read-only operations on approved tables
- ✅ Input validation prevents injection attacks

### Performance
- ✅ Process document requests within 2 minutes average
- ✅ Handle concurrent requests with proper rate limiting
- ✅ Graceful degradation when individual services are unavailable
- ✅ Memory efficient processing of large documents/datasets

---

**Generated**: 2025-09-26
**Note**: This specification focuses on the 3 essential integration tools. Additional tools (Slack, CRM systems) can be added after core functionality is validated.