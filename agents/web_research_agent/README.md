# Web Research Agent

A specialized Pydantic AI agent for comprehensive multi-engine web search, content extraction, and quality assessment. This agent is designed to be part of the larger research engineering workflow system.

## Features

- **Multi-Engine Search**: Execute searches across Brave, Google, and Bing APIs with intelligent fallback
- **Content Extraction**: Extract clean, readable text content from web sources with metadata preservation
- **Quality Assessment**: Filter results based on relevance scores and credibility indicators
- **Parallel Processing**: Handle 50+ sources concurrently within 3-minute time constraints
- **Workflow Integration**: Seamlessly integrate with the research engineering workflow system

## Quick Start

### 1. Installation

```bash
# Clone the repository and navigate to the agent directory
cd agents/web_research_agent

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required API keys (at least one):
- `LLM_API_KEY`: OpenAI API key for GPT-4o-mini
- `BRAVE_API_KEY`: Brave Search API key (recommended)
- `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID`: Google Custom Search
- `BING_SEARCH_API_KEY`: Bing Search API key

### 3. Basic Usage

```python
from agents.web_research_agent import run_web_search

# Execute a comprehensive web research
result = await run_web_search(
    query="machine learning algorithms",
    search_engines=["brave", "google"],
    max_results=20,
    quality_threshold=0.7
)
print(result)
```

### 4. Advanced Usage

```python
from agents.web_research_agent import agent, WebResearchDependencies, settings

# Create custom dependencies
deps = WebResearchDependencies.from_settings(
    settings,
    max_results=50,
    quality_threshold=0.8,
    session_id="research-session-123"
)

# Use the agent directly
result = await agent.run(
    "Find recent research on quantum computing applications",
    deps=deps
)

print(result.data)

# Cleanup resources
await deps.cleanup()
```

## Architecture

### Core Components

1. **Agent** (`agent.py`): Main Pydantic AI agent with integrated tools
2. **Tools** (`tools.py`): Three essential tools for search, extraction, and quality assessment
3. **Models** (`models.py`): Pydantic models for input/output structures
4. **Dependencies** (`dependencies.py`): Dependency injection and resource management
5. **Settings** (`settings.py`): Configuration management with environment variable support

### Tool Overview

#### 1. Multi-Engine Search
- Executes searches across Brave, Google, and Bing APIs
- Intelligent fallback handling if engines fail
- Rate limiting and retry mechanisms
- Returns structured search results with metadata

#### 2. Content Extraction
- Extracts clean text content from web URLs
- Respects robots.txt files
- Parallel processing with batch management
- Comprehensive metadata extraction

#### 3. Content Quality Assessment
- Multi-factor quality scoring algorithm:
  - Relevance score (40%) using TF-IDF similarity
  - Content quality (30%) based on structure and completeness
  - Source credibility (20%) from domain reputation and metadata
  - Freshness score (10%) based on publication date
- Configurable quality thresholds
- Detailed credibility indicators

## Performance

- **Concurrent Processing**: Up to 50 sources in parallel
- **Time Target**: Complete research within 3 minutes
- **Success Rate**: 95% content extraction success rate
- **Quality Standard**: >0.8 average relevance score

## API Reference

### Main Functions

#### `run_web_search(query, search_engines=None, max_results=20, quality_threshold=0.7, **kwargs)`

Execute comprehensive web research with automatic dependency injection.

**Parameters:**
- `query` (str): Search query to execute
- `search_engines` (list, optional): Search engines to use
- `max_results` (int): Maximum results per engine
- `quality_threshold` (float): Minimum quality score for filtering
- `session_id` (str, optional): Session identifier for tracking

**Returns:**
- `str`: Formatted research results with quality metrics

#### `create_agent_with_deps(**overrides)`

Create agent instance with custom dependencies.

**Returns:**
- `tuple`: (Agent instance, WebResearchDependencies instance)

### Models

#### `SearchRequest`
Input model for search requests with comprehensive configuration.

#### `WebSearchResults`
Complete output model with search results, metadata, and quality summary.

#### `WebSource`
Individual web source with extracted content and quality metrics.

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_API_KEY` | Yes | - | OpenAI API key |
| `BRAVE_API_KEY` | Optional* | - | Brave Search API key |
| `GOOGLE_SEARCH_API_KEY` | Optional* | - | Google Search API key |
| `GOOGLE_SEARCH_ENGINE_ID` | Optional* | - | Google Custom Search Engine ID |
| `BING_SEARCH_API_KEY` | Optional* | - | Bing Search API key |
| `DEFAULT_MAX_RESULTS` | No | 20 | Default max results per search |
| `DEFAULT_QUALITY_THRESHOLD` | No | 0.7 | Default quality threshold |
| `REQUEST_TIMEOUT` | No | 30 | Request timeout in seconds |
| `RATE_LIMIT_DELAY` | No | 1.0 | Rate limit delay between requests |

*At least one search engine API key is required.

## Error Handling

The agent implements comprehensive error handling:

- **Search Engine Failures**: Automatic fallback to next available engine
- **Network Timeouts**: Retry with exponential backoff
- **Content Extraction Failures**: Graceful degradation with error logging
- **Rate Limiting**: Automatic delay management
- **Resource Management**: Proper cleanup of HTTP sessions

## Integration

### Workflow Integration

This agent is designed to integrate with the research engineering workflow:

```python
# Receives SearchRequest via AgentMessage format
# Processes request and returns WebSearchResults
# Coordinates with Quality Assessment Agent downstream
```

### Custom Tool Integration

Add custom tools to the agent:

```python
@agent.tool
async def custom_search_tool(ctx: RunContext[WebResearchDependencies], custom_param: str) -> str:
    # Custom tool implementation
    return "Custom tool result"
```

## Testing

Run the included test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-aiohttp

# Run tests
pytest tests/ -v
```

## Development

### Code Style

The project uses Black and Ruff for code formatting:

```bash
black agents/web_research_agent/
ruff check agents/web_research_agent/
```

### Adding Features

1. Update models in `models.py` for new data structures
2. Implement functionality in `tools.py` or create new tool files
3. Register tools with the agent in `agent.py`
4. Update configuration in `settings.py` if needed
5. Add tests for new functionality

## Security

- All API keys stored in environment variables
- Robots.txt compliance by default
- Conservative rate limiting
- Input validation and sanitization
- No logging of sensitive information

## Performance Monitoring

The agent provides detailed metrics:

- Search execution times
- Content extraction success rates
- Quality score distributions
- Rate limit events
- Resource usage

## License

Part of the Pydantic AI Agent Factory project.

## Support

For issues and questions:
1. Check the planning documents in `planning/` directory
2. Review the workflow architecture documentation
3. Create an issue in the main repository

---

**Agent Version**: 1.0.0
**Created**: 2024-09-26
**Pydantic AI Compatible**: ✅