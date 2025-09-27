# Citation Management Agent - Tool Specifications

Tools for Citation Management Agent - Pydantic AI agent tools implementation for academic citation formatting, duplicate detection, and validation.

## Overview

This document specifies the three essential tools needed for the Citation Management Agent to handle academic citation formatting across multiple styles (APA, MLA, Chicago, IEEE, Harvard), detect and merge duplicate sources, and validate citation completeness.

## Tool 1: Format Citations

### Purpose
Generate properly formatted citations in specified academic styles, converting source metadata into both inline citations and full bibliographic references.

### Tool Specification
```python
@agent.tool
async def format_citations(
    ctx: RunContext[AgentDependencies],
    sources: List[SourceToCite],
    citation_style: Literal["APA", "MLA", "Chicago", "IEEE", "Harvard"],
    include_bibliography: bool = True
) -> List[FormattedCitation]:
    """
    Format source metadata into academic citations following specified style guidelines.

    Args:
        sources: List of source metadata objects to be formatted
        citation_style: Target academic citation style
        include_bibliography: Whether to generate full bibliographic references

    Returns:
        List of FormattedCitation objects with inline and full citations
    """
```

### Implementation Strategy
- **Style Templates**: Use rule-based templates for each of the 5 academic styles
- **Metadata Normalization**: Standardize author names, dates, and titles before formatting
- **Field Mapping**: Map SourceToCite fields to style-specific requirements
- **Error Handling**: Graceful degradation for incomplete metadata with clear warnings

### Performance Considerations
- Process multiple citations in batch to optimize LLM token usage
- Cache common citation patterns to reduce redundant processing
- Target: Process 100+ citations within 1 minute execution time

### Error Handling Patterns
```python
try:
    formatted_citation = await format_single_citation(source, style)
    return FormattedCitation(
        source_id=source.source_id,
        citation_key=generate_citation_key(source),
        inline_citation=formatted_citation.inline,
        full_citation=formatted_citation.full,
        citation_style=citation_style,
        validation_status="valid"
    )
except MissingMetadataError as e:
    logger.warning(f"Incomplete metadata for source {source.source_id}: {e}")
    return FormattedCitation(
        validation_status="warning",
        # ... partial citation with available data
    )
```

## Tool 2: Detect Duplicates

### Purpose
Identify and merge duplicate source citations based on metadata comparison, achieving 95% accuracy for duplicate detection through fuzzy matching algorithms.

### Tool Specification
```python
@agent.tool
async def detect_duplicates(
    ctx: RunContext[AgentDependencies],
    sources: List[SourceToCite],
    similarity_threshold: float = 0.85
) -> Dict[str, Any]:
    """
    Identify duplicate sources and provide merge recommendations.

    Args:
        sources: List of sources to analyze for duplicates
        similarity_threshold: Confidence threshold for duplicate matching (0.0-1.0)

    Returns:
        Dictionary containing deduplicated sources and merge mapping
    """
```

### Implementation Strategy
- **Fuzzy Matching**: Compare normalized titles, author lists, and URLs
- **Confidence Scoring**: Rate match probability using weighted similarity metrics
- **Metadata Preservation**: Keep highest-quality source data when merging
- **Clustering Algorithm**: Group similar sources and identify best representative

### Similarity Metrics
```python
# Weight factors for different metadata fields
SIMILARITY_WEIGHTS = {
    "title": 0.4,           # Normalized title comparison
    "authors": 0.3,         # Author name matching
    "url": 0.2,             # URL domain and path similarity
    "publication_date": 0.1 # Date proximity matching
}
```

### Performance Considerations
- Use efficient string similarity algorithms (Levenshtein, Jaro-Winkler)
- Implement early stopping for low-similarity pairs
- Process in batches to handle large source lists efficiently

### Error Handling Patterns
```python
try:
    similarity_score = calculate_similarity(source1, source2)
    if similarity_score >= similarity_threshold:
        merged_source = merge_sources(source1, source2)
        return {"merged": True, "source": merged_source, "confidence": similarity_score}
except Exception as e:
    logger.error(f"Duplicate detection failed: {e}")
    return {"merged": False, "error": str(e)}
```

## Tool 3: Validate Citations

### Purpose
Check citation completeness and accuracy against academic style requirements, providing clear feedback on missing fields and validation warnings.

### Tool Specification
```python
@agent.tool
async def validate_citations(
    ctx: RunContext[AgentDependencies],
    citations: List[FormattedCitation],
    validation_rules: Dict[str, Any]
) -> CitationValidation:
    """
    Validate citation completeness and accuracy against style requirements.

    Args:
        citations: List of formatted citations to validate
        validation_rules: Style-specific validation requirements

    Returns:
        CitationValidation with status, warnings, and missing fields
    """
```

### Implementation Strategy
- **Style-Specific Rules**: Define required fields for each academic style
- **Field Validation**: Check presence and format of required metadata
- **Quality Assessment**: Evaluate citation formatting consistency
- **Feedback Generation**: Provide actionable improvement suggestions

### Validation Rules by Style
```python
VALIDATION_RULES = {
    "APA": {
        "required": ["authors", "publication_date", "title"],
        "conditional": {"web": ["url"], "journal": ["journal_name", "volume"]}
    },
    "MLA": {
        "required": ["authors", "title"],
        "conditional": {"web": ["url", "access_date"], "book": ["publisher", "publication_date"]}
    },
    "Chicago": {
        "required": ["authors", "title", "publication_date"],
        "conditional": {"journal": ["journal_name", "volume", "issue"]}
    },
    "IEEE": {
        "required": ["authors", "title", "publication_date"],
        "conditional": {"journal": ["journal_name", "volume", "pages"]}
    },
    "Harvard": {
        "required": ["authors", "publication_date", "title"],
        "conditional": {"web": ["url"], "book": ["publisher"]}
    }
}
```

### Performance Considerations
- Batch validation of multiple citations simultaneously
- Use efficient field checking algorithms
- Cache validation results for repeated citation patterns

### Error Handling Patterns
```python
try:
    validation_result = validate_single_citation(citation, rules)
    missing_fields = check_required_fields(citation.source, rules)

    return CitationValidation(
        total_sources=len(citations),
        valid_citations=count_valid(citations),
        warnings=collect_warnings(citations),
        errors=collect_errors(citations),
        missing_fields=missing_fields,
        duplicate_sources=[]  # Populated by detect_duplicates tool
    )
except ValidationError as e:
    logger.error(f"Citation validation failed: {e}")
    return CitationValidation(errors=[str(e)])
```

## Tool Integration Architecture

### Context Dependencies
```python
@dataclass
class AgentDependencies:
    """Dependencies for Citation Management Agent execution"""
    openai_api_key: str
    processing_mode: str = "batch"  # "batch" or "streaming"
    max_concurrent_requests: int = 10
    citation_cache: Optional[Dict] = None
```

### Tool Orchestration
The three tools work together in sequence:
1. **detect_duplicates** → Remove/merge duplicate sources
2. **format_citations** → Generate formatted citations for unique sources
3. **validate_citations** → Check completeness and provide feedback

### Error Recovery Strategy
- **Partial Processing**: Continue with available data when some sources fail
- **Graceful Degradation**: Provide simplified citations when full formatting fails
- **Clear Feedback**: Return specific error messages indicating missing information
- **Retry Logic**: Implement exponential backoff for transient LLM API failures

## Performance Optimization

### Batch Processing
- Group similar citation styles together in LLM calls
- Process duplicate detection in parallel for large source lists
- Cache formatted citations to avoid redundant API calls

### Memory Management
- Stream processing for large citation requests (100+ sources)
- Efficient data structures for similarity comparisons
- Cleanup intermediate results after processing

### Rate Limiting
```python
import asyncio
from asyncio import Semaphore

# Limit concurrent LLM requests
REQUEST_SEMAPHORE = Semaphore(5)

async def rate_limited_format(source, style):
    async with REQUEST_SEMAPHORE:
        return await format_citation_with_llm(source, style)
```

## Testing Strategy

### Unit Testing
- Test each tool individually with mock data
- Validate citation formatting against style guide examples
- Test duplicate detection with known duplicate pairs
- Test validation rules for each academic style

### Integration Testing
- End-to-end citation request processing
- Tool orchestration and error propagation
- Performance testing with 100+ citations
- Memory usage and efficiency testing

### Quality Assurance
- Citation accuracy validation against academic standards
- Duplicate detection accuracy measurement (target: 95%)
- Validation feedback clarity and actionability
- Consistency across different citation styles

## Security Considerations

### Input Sanitization
- Validate source metadata formats and lengths
- Sanitize URLs and external references
- Prevent injection attacks through metadata fields

### API Key Management
- Secure handling of OpenAI API keys through environment variables
- No logging of sensitive authentication information
- Proper error handling that doesn't expose API credentials

### Rate Limiting and Abuse Prevention
- Implement request throttling to prevent API quota exhaustion
- Monitor and log unusual processing patterns
- Graceful handling of API rate limit responses

---

**Note**: These tool specifications are designed for the MVP implementation focusing on core citation formatting functionality. The tools prioritize simplicity, reliability, and performance while providing comprehensive academic citation support across all major styles.