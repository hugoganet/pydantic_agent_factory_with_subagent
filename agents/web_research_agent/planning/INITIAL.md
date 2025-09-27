# Web Research Agent - Requirements Documentation

## What This Agent Does
Specialized web search and information gathering agent that executes multi-engine searches, extracts clean content, and filters results based on quality criteria as part of the research engineering workflow.

## Core Features (MVP)

1. **Multi-Engine Web Search**: Execute searches across Brave, Google, and Bing APIs with intelligent fallback handling
2. **Content Extraction**: Extract and clean meaningful text content from web sources with metadata preservation
3. **Quality-Based Filtering**: Filter search results using relevance scores and credibility indicators with configurable thresholds

## Technical Setup

### Model
- **Provider**: openai
- **Model**: gpt-4o-mini
- **Why**: Fast, cost-effective model suitable for content processing and quality assessment tasks

### Required Tools
1. **multi_engine_search**: Execute searches across multiple search engines (Brave, Google, Bing) with rate limiting
2. **extract_web_content**: Extract and clean text content from URLs with metadata extraction
3. **assess_content_quality**: Evaluate content relevance and credibility using configurable quality thresholds

### External Services
- **Brave Search API**: Primary search engine with generous rate limits
- **Google Custom Search API**: Secondary search engine for comprehensive coverage
- **Bing Search API**: Tertiary search engine for additional result diversity
- **Web Scraping Service**: Content extraction with respect for robots.txt

## Environment Variables
```bash
# LLM Configuration
LLM_API_KEY=your-openai-api-key
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

# Search Engine APIs
BRAVE_API_KEY=your-brave-search-api-key
GOOGLE_SEARCH_API_KEY=your-google-search-api-key
GOOGLE_SEARCH_ENGINE_ID=your-custom-search-engine-id
BING_SEARCH_API_KEY=your-bing-search-api-key

# Configuration
DEFAULT_MAX_RESULTS=20
DEFAULT_QUALITY_THRESHOLD=0.7
REQUEST_TIMEOUT=30
RATE_LIMIT_DELAY=1.0
```

## Input Models

### SearchRequest
```python
class SearchRequest(BaseModel):
    search_id: str = Field(..., description="Unique identifier for this search request")
    query: str = Field(..., description="Search query to execute")
    search_engines: List[Literal["brave", "google", "bing"]] = Field(
        default=["brave"], description="Search engines to use in order of preference"
    )
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum results per engine")
    quality_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum quality score for results"
    )
    content_types: List[str] = Field(
        default=["article", "paper", "report", "news"], description="Preferred content types"
    )
    date_range: Optional[DateRange] = Field(default=None, description="Optional date filtering")

class DateRange(BaseModel):
    start_date: Optional[datetime] = Field(default=None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(default=None, description="End date for filtering")

class ContentExtraction(BaseModel):
    url: str = Field(..., description="URL to extract content from")
    extract_full_text: bool = Field(default=True, description="Extract full text content")
    extract_metadata: bool = Field(default=True, description="Extract metadata")
    extract_images: bool = Field(default=False, description="Extract image references")
```

## Output Models

### WebSearchResults
```python
class WebSearchResults(BaseModel):
    search_id: str = Field(..., description="Unique identifier matching the request")
    query_used: str = Field(..., description="Actual query executed")
    total_results: int = Field(..., description="Total number of results found")
    sources: List[WebSource] = Field(..., description="List of web sources found")
    search_metadata: SearchMetadata = Field(..., description="Search execution metadata")
    quality_summary: QualitySummary = Field(..., description="Quality assessment summary")

class WebSource(BaseModel):
    source_id: str = Field(..., description="Unique identifier for this source")
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Page title")
    content: str = Field(..., description="Extracted text content")
    metadata: SourceMetadata = Field(..., description="Source metadata")
    extraction_timestamp: datetime = Field(..., description="When content was extracted")
    credibility_indicators: List[str] = Field(
        default_factory=list, description="List of credibility indicators found"
    )
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Computed quality score")

class SourceMetadata(BaseModel):
    domain: str = Field(..., description="Source domain")
    publish_date: Optional[datetime] = Field(default=None, description="Publication date if available")
    author: Optional[str] = Field(default=None, description="Author if available")
    word_count: int = Field(..., description="Word count of extracted content")
    content_type: str = Field(..., description="Detected content type")
    language: str = Field(default="en", description="Detected language")

class SearchMetadata(BaseModel):
    engines_used: List[str] = Field(..., description="Search engines that were used")
    total_execution_time: float = Field(..., description="Total execution time in seconds")
    results_per_engine: Dict[str, int] = Field(..., description="Results count per engine")
    rate_limit_delays: Dict[str, float] = Field(..., description="Rate limit delays per engine")

class QualitySummary(BaseModel):
    average_quality_score: float = Field(..., description="Average quality score of all results")
    high_quality_count: int = Field(..., description="Number of high-quality sources (>0.8)")
    filtered_out_count: int = Field(..., description="Number of sources filtered out")
    credible_sources_count: int = Field(..., description="Number of sources with credibility indicators")
```

## Agent Dependencies

### AgentDependencies
```python
@dataclass
class WebResearchDependencies:
    # Search Engine API Clients
    brave_api_key: str
    google_search_api_key: str
    google_search_engine_id: str
    bing_search_api_key: str

    # Configuration
    max_results: int = 20
    quality_threshold: float = 0.7
    request_timeout: int = 30
    rate_limit_delay: float = 1.0

    # Session tracking
    session_id: Optional[str] = None
    workflow_context: Optional[Dict[str, Any]] = None
```

## Workflow Integration

### Inter-Agent Communication
- **Input Protocol**: Receives SearchRequest via AgentMessage format from workflow orchestrator
- **Output Protocol**: Sends WebSearchResults to Quality Assessment Agent for evaluation
- **Parallel Execution**: Works alongside Tool Integration Agent during Phase 2: Information Gathering
- **Error Handling**: Reports failures back to workflow orchestrator for retry/fallback

### Performance Requirements
- **Parallel Processing**: Handle 50+ sources concurrently using asyncio
- **Time Constraints**: Complete full search and extraction within 3 minutes
- **Quality Targets**: Maintain >0.8 average relevance score for extracted content
- **Reliability**: Successfully extract content from 95% of accessible web sources

## Success Criteria

- [ ] Successfully execute searches across all configured search engines with proper fallback
- [ ] Extract clean, readable content from web sources with 95% success rate
- [ ] Respect API rate limits and handle network errors gracefully with retry logic
- [ ] Filter results to meet specified quality thresholds consistently
- [ ] Process 50+ sources in parallel within 3-minute time constraint
- [ ] Maintain >0.8 average relevance score for extracted content
- [ ] Integrate seamlessly with workflow orchestrator and downstream agents
- [ ] Handle edge cases: blocked content, JavaScript-heavy sites, rate limiting

## Error Handling Strategy

### API Failures
- **Search Engine Fallback**: Automatically try next available search engine if primary fails
- **Rate Limit Handling**: Implement exponential backoff with configurable delays
- **Network Timeouts**: Retry failed requests up to 3 times with increasing delays

### Content Extraction Failures
- **Blocked Content**: Log and skip sources that block automated access
- **Malformed Content**: Attempt basic text extraction even from poorly formatted pages
- **JavaScript Requirements**: Use lightweight headless browsing for critical sources

### Quality Assurance
- **Content Validation**: Verify extracted content meets minimum length and quality requirements
- **Duplicate Detection**: Identify and merge substantially similar sources
- **Source Verification**: Basic checks for domain reputation and content freshness

## Assumptions Made

- **Search Engine Access**: All required API keys will be available and valid
- **Network Connectivity**: Reliable internet connection for web scraping operations
- **Content Accessibility**: Most target sources allow automated access (respect robots.txt)
- **Quality Metrics**: Simple relevance scoring based on keyword matching and content structure
- **Rate Limits**: Conservative rate limiting to avoid API throttling (1 request/second default)
- **Content Types**: Focus on text-based content, minimal handling of multimedia
- **Language Support**: Primary support for English content with basic multilingual detection

## Security Considerations

- **API Key Protection**: All API keys stored in environment variables, never logged
- **Rate Limiting**: Respect API terms of service and implement conservative limits
- **User Agent**: Use appropriate user agent strings for web scraping requests
- **Robots.txt Compliance**: Check and respect robots.txt before scraping content
- **Data Privacy**: No storage of scraped content beyond workflow execution context

---
**Generated**: 2025-09-26
**Note**: This is an MVP focused on core web research functionality. Advanced features like semantic search, content summarization, and complex quality metrics can be added after the basic agent works reliably within the workflow system.