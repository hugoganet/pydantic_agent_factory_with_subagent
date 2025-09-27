# Tool Integration Agent

A Pydantic AI agent that provides secure interface to internal enterprise tools and external APIs for the Research Engineering Workflow system. This agent serves as the primary data bridge between external enterprise tools and research workflow agents.

## 🎯 Agent Overview

**Primary Role**: Interface with internal tools and external APIs for research data gathering

**Agent Type**: System integration specialist for enterprise tools

**Priority**: MEDIUM (Specialized use cases)

**Dependencies**: Provides data to Quality Assessment Agent and Data Synthesis Agent

## 🔧 Core Features

### Supported Integrations

1. **Google Drive Integration** - Search and extract content from Google Drive documents with OAuth 2.0 authentication
2. **Gmail Analysis** - Analyze email content and extract relevant information for research purposes
3. **Database Querying** - Execute read-only queries against PostgreSQL and SQLite databases for internal data

### Security & Compliance Features

- **OAuth 2.0 Authentication**: Secure authentication flows for Google services
- **Permission Respect**: Honors existing access permissions and sharing controls
- **Audit Logging**: Comprehensive logging of all data access operations
- **Rate Limiting**: Built-in handling with exponential backoff
- **SQL Injection Protection**: Safe database query execution with parameter validation

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Cloud Project with Drive and Gmail APIs enabled
- Database access (PostgreSQL or SQLite)
- OpenAI API key

### Installation

1. Clone the repository and navigate to the agent directory:
```bash
cd agents/tool_integration_agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Configure Google API credentials:
   - Create a service account in Google Cloud Console
   - Download the credentials JSON file
   - Update `GOOGLE_APPLICATION_CREDENTIALS` in your `.env` file

### Basic Usage

```python
from tool_integration_agent import (
    run_tool_integration_agent,
    ToolRequest
)

# Example: Search Google Drive
request = ToolRequest(
    tool_type="google_drive",
    operation="search",
    parameters={
        "query": "quarterly report",
        "file_types": ["docs", "pdf"],
        "max_results": 10
    }
)

result = await run_tool_integration_agent(request)
print(f"Found {len(result.results)} documents")
```

## 📊 API Reference

### Main Functions

#### `run_tool_integration_agent(request, user_id=None, session_id=None)`

Main entry point for running the Tool Integration Agent.

**Parameters:**
- `request` (ToolRequest): Tool request with parameters
- `user_id` (str, optional): User identifier for audit logging
- `session_id` (str, optional): Session identifier for request tracking

**Returns:** ToolResponse with results or error information

#### `health_check()`

Check the health status of the Tool Integration Agent and its dependencies.

**Returns:** Dict with health status information

### Data Models

#### ToolRequest
```python
{
    "request_id": "uuid-string",
    "tool_type": "google_drive|gmail|database",
    "operation": "search|extract|query",
    "parameters": {
        # Tool-specific parameters
    },
    "authentication": {},  # Optional auth context
    "filters": {}          # Optional filters
}
```

#### ToolResponse
```python
{
    "request_id": "uuid-string",
    "tool_type": "google_drive|gmail|database",
    "success": true,
    "results": [...],      # Array of extracted data
    "metadata": {...},     # Response metadata
    "extraction_quality": 0.95,
    "timestamp": "2025-09-26T12:00:00Z",
    "execution_time_ms": 1500,
    "errors": []           # Array of error messages (if any)
}
```

### Tool-Specific APIs

#### Google Drive Search

```python
# Via direct agent tool call
result = await google_drive_search(
    ctx,
    query="project documentation",
    file_types=["docs", "sheets", "pdf"],
    max_results=20
)

# Via ToolRequest
request = ToolRequest(
    tool_type="google_drive",
    operation="search",
    parameters={
        "query": "project documentation",
        "file_types": ["docs", "sheets", "pdf"],
        "max_results": 20
    }
)
```

#### Gmail Content Extraction

```python
# Via direct agent tool call
result = await gmail_extract_content(
    ctx,
    search_query="from:client@company.com subject:requirements",
    date_range={"start": "2024-01-01", "end": "2024-12-31"},
    max_messages=50
)

# Via ToolRequest
request = ToolRequest(
    tool_type="gmail",
    operation="extract",
    parameters={
        "search_query": "from:client@company.com subject:requirements",
        "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
        "max_messages": 50
    }
)
```

#### Database Query

```python
# Via direct agent tool call
result = await database_query(
    ctx,
    query="SELECT id, title, created_at FROM documents WHERE status = 'published'",
    database_type="postgresql",
    result_format="json"
)

# Via ToolRequest
request = ToolRequest(
    tool_type="database",
    operation="query",
    parameters={
        "query": "SELECT id, title, created_at FROM documents WHERE status = 'published'",
        "database_type": "postgresql",
        "result_format": "json"
    }
)
```

## 🔐 Security Configuration

### Environment Variables

Required environment variables for secure operation:

```bash
# LLM Configuration
LLM_API_KEY=your-openai-api-key

# Google Services
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-credentials.json
GOOGLE_OAUTH_CLIENT_ID=your-oauth-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-oauth-client-secret

# Database Access
DATABASE_URL=postgresql://readonly_user:password@host:5432/db_name

# Security Settings
MAX_QUERY_RESULTS=100
RATE_LIMIT_PER_MINUTE=60
AUDIT_LOG_FILE=/path/to/audit.log
```

### Google API Setup

1. **Create Google Cloud Project**
2. **Enable APIs**: Drive API, Gmail API
3. **Create Service Account**: Download JSON credentials
4. **Set up OAuth 2.0**: For user authentication (if needed)
5. **Configure Scopes**:
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/gmail.readonly`

### Database Security

- Use read-only database credentials
- Limit access to approved tables/views
- Enable SQL query validation and injection protection
- Configure connection pooling with appropriate limits

## 📈 Performance & Monitoring

### Rate Limits

- **Google Drive API**: 100 requests/100 seconds/user
- **Gmail API**: 250 quota units/user/second
- **Database Queries**: 60 queries/minute/user

### Monitoring

The agent provides comprehensive monitoring through:

- **Health Checks**: `/health` endpoint for service status
- **Audit Logging**: All operations logged with structured format
- **Performance Metrics**: Execution time, success rates, data volume
- **Error Tracking**: Detailed error reporting with retry information

### Audit Log Format

```json
{
  "timestamp": "2025-09-26T12:00:00Z",
  "request_id": "uuid-string",
  "user_id": "user-identifier",
  "tool_name": "google_drive_search",
  "operation": "document_search",
  "resource_accessed": "query:quarterly report",
  "success": true,
  "execution_time_ms": 1500,
  "data_volume": 1024
}
```

## 🧪 Testing

### Unit Tests

Run unit tests with mock services:

```bash
# Set up test environment
export USE_MOCK_GOOGLE_APIS=true
export USE_MOCK_DATABASE=true

# Run tests
pytest tests/ -v --cov=tool_integration_agent
```

### Integration Tests

Test with sandbox APIs:

```bash
# Configure sandbox credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/test-credentials.json
export DATABASE_URL=sqlite:///test.db

# Run integration tests
pytest tests/integration/ -v
```

## 🔧 Development

### Project Structure

```
tool_integration_agent/
├── __init__.py           # Package initialization
├── agent.py             # Main agent implementation
├── models.py            # Pydantic data models
├── tools.py             # Tool implementations
├── dependencies.py      # Dependencies and services
├── providers.py         # LLM model providers
├── prompts.py          # System prompts
├── settings.py         # Configuration management
├── requirements.txt    # Python dependencies
├── .env.example       # Environment template
└── README.md          # This file
```

### Adding New Tools

1. **Define Models**: Add input/output models in `models.py`
2. **Implement Tool**: Add tool logic in `tools.py`
3. **Register Tool**: Add tool decorator in `agent.py`
4. **Add Tests**: Create tests for the new functionality
5. **Update Documentation**: Update README and API reference

### Code Quality

- **Linting**: Uses `ruff` for code linting
- **Formatting**: Uses `black` for code formatting
- **Type Hints**: Full type annotation coverage
- **Documentation**: Comprehensive docstrings and comments

## 🐛 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Google credentials file exists and is valid
   - Check OAuth 2.0 client configuration
   - Ensure proper API scopes are configured

2. **Database Connection Issues**
   - Verify database URL format and credentials
   - Check network connectivity and firewall rules
   - Ensure database user has appropriate permissions

3. **Rate Limit Errors**
   - Monitor API usage quotas
   - Implement exponential backoff (built-in)
   - Consider request batching for efficiency

4. **Permission Errors**
   - Verify user has access to requested resources
   - Check Google Drive/Gmail sharing permissions
   - Review database table access controls

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
export DEBUG=true
```

This will provide detailed logging for troubleshooting.

## 🤝 Integration with Research Workflow

This agent integrates with the Research Engineering Workflow system:

### Input Sources
- **Research Orchestrator**: Receives tool requests with parameters
- **Workflow Coordinator**: Handles health checks and monitoring

### Output Destinations
- **Quality Assessment Agent**: Provides extracted documents for credibility scoring
- **Data Synthesis Agent**: Supplies internal documents for report generation

### Message Format

The agent uses standardized message formats for inter-agent communication:

```python
# Incoming from Research Orchestrator
{
    "sender_id": "research_orchestrator",
    "recipient_id": "tool_integration_agent",
    "message_type": "task",
    "payload": {
        "tool_request": { ... }
    }
}

# Outgoing to Quality Assessment
{
    "sender_id": "tool_integration_agent",
    "recipient_id": "quality_assessment_agent",
    "message_type": "result",
    "payload": {
        "documents": [ ... ],
        "extraction_quality": 0.95
    }
}
```

## 📜 License

This agent is part of the Research Engineering Workflow system. See the main repository LICENSE file for details.

## 🆘 Support

For issues and questions:

1. Check the troubleshooting section above
2. Review audit logs for error details
3. Create an issue in the main repository
4. Contact the development team

---

**Version**: 1.0.0
**Last Updated**: 2025-09-26
**Agent Type**: Tool Integration Specialist