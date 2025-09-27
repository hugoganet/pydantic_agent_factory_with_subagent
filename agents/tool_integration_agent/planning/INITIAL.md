# Tool Integration Agent - Simple Requirements

## What This Agent Does
Provides secure interface to internal enterprise tools (Google Drive, Gmail, databases) and external APIs for research data extraction, serving as the primary data bridge in the Research Engineering Workflow system.

## Core Features (MVP)
1. **Google Drive Integration** - Search and extract content from Google Drive documents with OAuth 2.0 authentication
2. **Gmail Analysis** - Analyze email content and extract relevant information for research purposes
3. **Database Querying** - Execute read-only queries against PostgreSQL and SQLite databases for internal data

## Technical Setup

### Model
- **Provider**: openai
- **Model**: gpt-4
- **Why**: Handles complex document analysis and structured data extraction reliably with good tool integration

### Required Tools
1. **google_drive_search**: Search Google Drive documents by query with file type and date filters
2. **gmail_extract_content**: Extract relevant information from Gmail messages with threading support
3. **database_query**: Execute safe SELECT queries against configured databases with result formatting

### External Services
- **Google Drive API**: Document search and content extraction
- **Gmail API**: Email content analysis and metadata extraction
- **Database Connections**: PostgreSQL/SQLite read-only access for internal data queries

## Environment Variables
```bash
# LLM Configuration
LLM_API_KEY=your-openai-api-key

# Google Services
GOOGLE_DRIVE_CREDENTIALS_PATH=path/to/google-credentials.json
GMAIL_API_CREDENTIALS=path/to/gmail-credentials.json

# Database Configuration
DATABASE_URL=postgresql://user:pass@host:5432/db_name
SQLITE_DB_PATH=path/to/local.db

# Security Configuration
MAX_QUERY_RESULTS=100
RATE_LIMIT_PER_MINUTE=60
AUDIT_LOG_LEVEL=INFO
```

## Input/Output Models

### Input Models
```python
class ToolRequest(BaseModel):
    request_id: str
    tool_type: Literal["google_drive", "gmail", "database"]
    operation: str
    parameters: Dict[str, Any]
    authentication: Dict[str, str]
    filters: Optional[Dict[str, Any]] = None

class GoogleDriveQuery(BaseModel):
    query: str
    file_types: List[str] = ["docs", "sheets", "pdf"]
    folder_ids: Optional[List[str]] = None
    date_range: Optional[Dict[str, str]] = None
```

### Output Models
```python
class ToolResponse(BaseModel):
    request_id: str
    tool_type: str
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    extraction_quality: float
    timestamp: datetime

class InternalDocument(BaseModel):
    document_id: str
    title: str
    content: str
    source_tool: str
    metadata: Dict[str, Any]
    access_permissions: List[str]
    last_modified: datetime
```

## Success Criteria

- [ ] Successfully authenticates with Google Drive and Gmail using OAuth 2.0
- [ ] Extracts content from 90% of accessible documents and emails
- [ ] Executes database queries safely with proper SQL injection protection
- [ ] Handles API rate limits gracefully with exponential backoff
- [ ] Maintains audit logs for all data access operations
- [ ] Processes internal documents within 2 minutes average
- [ ] Integrates with Research Orchestrator and Quality Assessment agents
- [ ] Returns structured data in consistent format for downstream agents

## Inter-Agent Communication

### Receives From
- **Research Orchestrator**: Tool requests with specific parameters and authentication context
- **Workflow Coordinator**: Health checks and status requests

### Sends To
- **Quality Assessment Agent**: Extracted documents with metadata for credibility scoring
- **Data Synthesis Agent**: Internal documents and structured data for report generation
- **Workflow Coordinator**: Status updates and completion notifications

## Security & Privacy

### Authentication & Authorization
- OAuth 2.0 flows for Google services with secure token storage
- Database connections use read-only credentials with minimal permissions
- All API keys stored in environment variables, never in code

### Access Control
- Respects Google Drive sharing permissions and folder access controls
- Gmail access limited to authorized mailboxes and date ranges
- Database queries restricted to approved tables and operations

### Audit & Compliance
- Log all data access operations with request ID, user, and timestamp
- Track document access patterns for compliance reporting
- Implement data retention policies for extracted content

## Assumptions Made

- Using Google Workspace APIs (not personal Google accounts) for enterprise access
- Database queries are read-only (SELECT statements only) for security
- Rate limiting handled with exponential backoff (no complex queue management)
- Document content extracted as plain text initially (no advanced formatting preservation)
- Authentication tokens refreshed automatically using stored credentials
- Tool requests are authenticated and authorized at the orchestrator level

## Integration Points

### With Research Orchestrator
- Receives standardized `ToolRequest` messages with tool type and parameters
- Returns structured `ToolResponse` with extracted data and quality metrics
- Supports batch processing for multiple document requests

### With Quality Assessment Agent
- Provides extracted documents with source metadata for credibility evaluation
- Includes access permissions and last-modified dates for freshness assessment

### With Data Synthesis Agent
- Delivers internal documents in structured format for report integration
- Maintains document lineage for proper attribution in final reports

## Error Handling Strategy

### API Failures
- Retry with exponential backoff for transient failures
- Graceful degradation when specific services are unavailable
- Clear error messages for authentication and permission issues

### Data Quality Issues
- Validate extracted content before returning to calling agents
- Flag documents that couldn't be processed with reason codes
- Provide partial results when some tools succeed but others fail

---
Generated: 2025-09-26
Note: This is an MVP focused on Google Drive, Gmail, and database integration. Additional tools (Slack, CRM systems) can be added after basic functionality is working and validated.