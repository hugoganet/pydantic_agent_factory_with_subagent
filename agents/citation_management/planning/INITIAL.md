# Citation Management Agent - Simple Requirements

## What This Agent Does
Formats academic citations in multiple styles and manages source attribution within the Research Engineering Workflow system, providing formatted citations and comprehensive bibliographies for research reports.

## Core Features (MVP)
1. **Multi-Style Citation Formatting**: Generate accurate citations in APA, MLA, Chicago, IEEE, and Harvard formats
2. **Bibliography Generation**: Create comprehensive reference lists sorted alphabetically with duplicate detection
3. **Citation Validation**: Verify citation completeness and flag missing required information with validation feedback

## Technical Setup

### Model
- **Provider**: openai
- **Model**: gpt-4o-mini
- **Why**: Cost-effective model with excellent structured output capabilities for citation formatting tasks

### Required Tools
1. **format_citation**: Generate individual citation in specified academic style format
2. **detect_duplicates**: Identify and merge duplicate source entries based on metadata comparison
3. **validate_citation**: Check citation completeness against style requirements and flag missing information

### External Services
- None required for MVP (all processing handled via LLM reasoning)

## Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key
```

## Input Models (From GitHub Issue #13)

```python
class CitationRequest(BaseModel):
    request_id: str
    sources: List[SourceToCite]
    citation_style: Literal["APA", "MLA", "Chicago", "IEEE", "Harvard"]
    include_bibliography: bool = True
    sort_alphabetically: bool = True

class SourceToCite(BaseModel):
    source_id: str
    title: str
    authors: List[str]
    publication_date: Optional[date]
    url: Optional[str]
    source_type: Literal["web", "journal", "book", "report", "other"]
    additional_metadata: Dict[str, Any] = {}
```

## Output Models (From GitHub Issue #13)

```python
class CitationResponse(BaseModel):
    request_id: str
    citations: List[FormattedCitation]
    bibliography: List[str]
    citation_map: Dict[str, str]  # source_id -> citation_key
    style_used: str
    validation_results: CitationValidation

class FormattedCitation(BaseModel):
    source_id: str
    citation_key: str
    inline_citation: str
    full_citation: str
    citation_style: str
    validation_status: Literal["valid", "warning", "error"]

class CitationValidation(BaseModel):
    total_sources: int
    valid_citations: int
    warnings: List[str]
    errors: List[str]
    missing_fields: Dict[str, List[str]]  # source_id -> missing_fields
    duplicate_sources: List[Dict[str, str]]  # detected duplicates
```

## Workflow Integration

### Communication Protocol
- **Receives from**: Quality Assessment Agent (#4) via standard AgentMessage protocol
- **Provides to**: Data Synthesis Agent (#7) for final report generation
- **Message Type**: `citation_request` and `citation_response`

### Integration Points
```python
# Incoming message payload from Quality Assessment Agent
{
    "message_type": "citation_request",
    "payload": {
        "sources": [...],  # List of verified sources with quality scores
        "citation_style": "APA",
        "include_bibliography": True
    }
}

# Outgoing message payload to Data Synthesis Agent
{
    "message_type": "citation_response",
    "payload": {
        "formatted_citations": [...],
        "bibliography": [...],
        "citation_map": {...}
    }
}
```

## Success Criteria

- [ ] **Multi-Style Support**: Generates accurate citations in all 5 major academic styles (APA, MLA, Chicago, IEEE, Harvard)
- [ ] **Duplicate Detection**: Identifies and merges duplicate sources with 95% accuracy based on title/author/URL matching
- [ ] **Validation Feedback**: Flags incomplete citations and provides clear feedback on missing required fields
- [ ] **Performance Target**: Processes 100+ citations within 1 minute execution time
- [ ] **Consistency**: Maintains consistent formatting within each citation style across all generated citations
- [ ] **Bibliography Generation**: Creates properly formatted and alphabetically sorted reference lists

## Implementation Architecture

### Agent Structure
```
agents/citation_management/
├── agent.py              # Main Pydantic AI agent with CitationRequest/CitationResponse handling
├── tools.py              # Citation formatting, duplicate detection, validation tools
├── models.py             # Input/output Pydantic models from GitHub issue
├── citation_styles.py    # Academic style formatting rules and templates
├── dependencies.py       # External dependencies (none for MVP)
├── settings.py           # Configuration with OpenAI model settings
├── requirements.txt      # Minimal dependencies (pydantic-ai, python-dotenv)
└── .env.example          # Environment template
```

### Citation Style Implementation
- **Rule-based formatting**: Define templates for each of the 5 academic styles
- **Metadata normalization**: Standardize author names, dates, and titles
- **Field validation**: Check required fields per citation style (e.g., APA requires author, year, title)
- **Error handling**: Graceful degradation for incomplete source information

### Duplicate Detection Strategy
- **Fuzzy matching**: Compare normalized titles, author lists, and URLs
- **Confidence scoring**: Rate match probability and merge only high-confidence duplicates
- **Preservation**: Keep highest-quality source metadata when merging

## Performance Optimization

### Batch Processing
- Process multiple citations simultaneously using parallel LLM calls
- Cache formatted citations to avoid redundant processing
- Optimize token usage by batching similar citation styles

### Error Recovery
- Provide partial citations when some metadata is missing
- Clear error messages indicating what information is needed
- Fallback to simpler citation format if complex formatting fails

## Assumptions Made

- **Single Model Provider**: Using OpenAI exclusively for MVP (no fallback providers)
- **Rule-Based Validation**: Citation completeness validation based on predefined style requirements
- **Memory Storage**: No persistent storage needed - stateless processing of citation requests
- **Standard Academic Formats**: Following widely accepted academic citation style guides
- **English Language**: Primary focus on English-language sources and citation formats

## Quality Assurance

### Validation Rules
- **APA Style**: Requires author, year, title (URL for web sources)
- **MLA Style**: Requires author, title, publication info, access date for web sources
- **Chicago Style**: Requires author, title, publication info (footnote vs bibliography format)
- **IEEE Style**: Requires author, title, publication, year, pages/DOI
- **Harvard Style**: Requires author, year, title, publisher/URL

### Testing Strategy
- **Unit Tests**: Individual citation formatting for each style
- **Integration Tests**: End-to-end citation request/response validation
- **Performance Tests**: 100+ citation processing within time constraints
- **Quality Tests**: Citation accuracy against academic style guides

---
Generated: 2025-09-26
Note: This is an MVP focusing on core citation formatting functionality. Advanced features like citation network analysis, style customization, and integration with external citation databases can be added after the basic agent works reliably.