# Citation Management Agent

Academic source attribution and reference formatting agent for the Research Engineering Workflow system.

## Overview

The Citation Management Agent provides comprehensive citation formatting capabilities across multiple academic styles, duplicate source detection, and citation validation. It integrates seamlessly with the Research Engineering Workflow to ensure proper source attribution in research outputs.

## Features

- **Multi-Style Citation Formatting**: Supports APA, MLA, Chicago, IEEE, and Harvard citation styles
- **Duplicate Detection**: Intelligent source deduplication with 95% accuracy using fuzzy matching
- **Citation Validation**: Comprehensive completeness checking with actionable feedback
- **Bibliography Generation**: Alphabetically sorted reference lists
- **Workflow Integration**: Standard AgentMessage protocol for inter-agent communication
- **High Performance**: Processes 100+ citations within 1 minute

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your OpenAI API key
LLM_API_KEY=sk-your-openai-api-key-here
```

### Basic Usage

```python
import asyncio
from agents.citation_management import run_citation_agent

# Sample sources
sources = [
    {
        "source_id": "src_1",
        "title": "The Impact of AI on Research",
        "authors": ["Smith, John", "Doe, Jane"],
        "publication_date": "2023-01-15",
        "url": "https://example.com/ai-research",
        "source_type": "web"
    }
]

async def main():
    result = await run_citation_agent(
        sources=sources,
        citation_style="APA",
        request_id="example_request"
    )

    print(f"Generated {len(result.citations)} citations")
    for citation in result.citations:
        print(f"Inline: {citation.inline_citation}")
        print(f"Full: {citation.full_citation}")

asyncio.run(main())
```

## API Reference

### Main Functions

#### `run_citation_agent(sources, citation_style, request_id, **kwargs)`

Main entry point for citation processing.

**Parameters:**
- `sources` (List[Dict]): Source metadata dictionaries
- `citation_style` (str): Citation style ("APA", "MLA", "Chicago", "IEEE", "Harvard")
- `request_id` (str): Unique request identifier
- `include_bibliography` (bool): Generate bibliography (default: True)
- `sort_alphabetically` (bool): Sort bibliography alphabetically (default: True)

**Returns:**
- `CitationResponse`: Complete citation results with validation

### Models

#### `SourceToCite`

Source metadata for citation formatting.

```python
{
    "source_id": str,
    "title": str,
    "authors": List[str],
    "publication_date": Optional[date],
    "url": Optional[str],
    "source_type": "web" | "journal" | "book" | "report" | "other",
    "additional_metadata": Dict[str, Any]
}
```

#### `CitationResponse`

Complete citation processing results.

```python
{
    "request_id": str,
    "citations": List[FormattedCitation],
    "bibliography": List[str],
    "citation_map": Dict[str, str],  # source_id -> citation_key
    "style_used": str,
    "validation_results": CitationValidation
}
```

## Citation Styles

### APA (7th Edition)
- In-text: (Smith, 2023)
- Reference: Smith, J. (2023). Title. Publisher.

### MLA (9th Edition)
- In-text: (Smith)
- Works Cited: Smith, John. "Title." Publisher, 2023.

### Chicago (17th Edition)
- In-text: (Smith, 2023)
- Bibliography: Smith, John. "Title." 2023.

### IEEE
- In-text: [1]
- Reference: J. Smith, "Title," 2023.

### Harvard
- In-text: (Smith 2023)
- Reference: Smith, J 2023, 'Title'.

## Workflow Integration

The agent integrates with the Research Engineering Workflow through standard AgentMessage protocol:

### Receiving Citation Requests

```python
# From Quality Assessment Agent (#4)
{
    "sender_id": "quality_assessment_agent",
    "recipient_id": "citation_management_agent",
    "message_type": "citation_request",
    "payload": {
        "sources": [...],
        "citation_style": "APA",
        "include_bibliography": True
    }
}
```

### Sending Citation Responses

```python
# To Data Synthesis Agent (#7)
{
    "sender_id": "citation_management_agent",
    "recipient_id": "data_synthesis_agent",
    "message_type": "citation_response",
    "payload": {
        "formatted_citations": [...],
        "bibliography": [...],
        "citation_map": {...}
    }
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | - | OpenAI API key (required) |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `CITATION_BATCH_SIZE` | `50` | Citations per batch |
| `DUPLICATE_THRESHOLD` | `0.85` | Duplicate detection threshold |
| `LOG_LEVEL` | `INFO` | Logging level |

### Dependencies Configuration

```python
from agents.citation_management import CitationDependencies

deps = CitationDependencies(
    batch_size=50,
    duplicate_threshold=0.85,
    validate_citations=True,
    max_retries=3,
    timeout=30
)
```

## Performance

- **Processing Speed**: 100+ citations within 1 minute
- **Duplicate Detection**: 95% accuracy with fuzzy matching
- **Memory Usage**: <500MB for typical workloads
- **API Efficiency**: Batched processing to minimize token usage

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=agents/citation_management

# Run specific test categories
pytest tests/test_citation_formatting.py -v
pytest tests/test_duplicate_detection.py -v
pytest tests/test_validation.py -v
```

## Error Handling

The agent provides graceful error handling:

- **Incomplete Sources**: Generates partial citations with warnings
- **Invalid Formats**: Falls back to basic formatting with error status
- **API Failures**: Implements retry logic with exponential backoff
- **Validation Errors**: Clear feedback on missing required fields

## Troubleshooting

### Common Issues

1. **Missing API Key**
   ```
   Error: Invalid OpenAI API key format
   Solution: Set LLM_API_KEY in .env file
   ```

2. **Duplicate Detection Not Working**
   ```
   Check: DUPLICATE_THRESHOLD setting (0.0-1.0)
   Try: Lower threshold for more aggressive detection
   ```

3. **Citation Formatting Errors**
   ```
   Check: Source metadata completeness
   Review: Required fields for citation style
   ```

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

## Contributing

1. Follow the Pydantic AI agent patterns
2. Add tests for new citation styles
3. Update validation rules for style requirements
4. Maintain 95% test coverage

## License

Part of the Research Engineering Workflow system.

## Support

For issues related to:
- Citation formatting: Check official style guides
- API errors: Verify OpenAI API key and quotas
- Performance: Review batch size and timeout settings
- Integration: Check AgentMessage protocol compliance