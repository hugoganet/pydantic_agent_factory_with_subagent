# Quality Assessment Agent

A specialized Pydantic AI agent for evaluating source credibility, detecting bias, and assessing information quality in research workflows.

## Overview

The Quality Assessment Agent (#4) is a foundational service in the Research Engineering Workflow that provides objective quality scores for research sources. It evaluates credibility, detects bias patterns, and assesses content freshness to help downstream agents make informed decisions about source prioritization and synthesis.

## Features

- **Source Credibility Assessment**: Domain authority, content quality, and author credentials
- **Bias Detection**: Language analysis, perspective diversity, and neutrality scoring
- **Content Quality Analysis**: Structure, citations, readability, and completeness
- **Freshness Evaluation**: Publication date analysis and content recency scoring
- **Concurrent Processing**: Handle 10-20 sources simultaneously
- **Error Resilience**: Graceful fallbacks and comprehensive error handling

## Quick Start

### Installation

```bash
# Clone or navigate to the agent directory
cd agents/quality_assessment_agent

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### Environment Configuration

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional
FACT_CHECK_API_KEY=your_factcheck_api_key_here
CREDIBILITY_THRESHOLD=0.7
BIAS_THRESHOLD=0.6
PROCESSING_TIMEOUT=30
```

### Basic Usage

```python
import asyncio
from datetime import datetime
from agents.quality_assessment_agent import assess_source_quality, ResearchSource

async def main():
    # Create a research source
    source = ResearchSource(
        source_id="article_001",
        url="https://example.com/article",
        title="Research Article Title",
        content="Full article content here...",
        extraction_timestamp=datetime.now()
    )

    # Assess quality
    assessment = await assess_source_quality(source)

    print(f"Credibility Score: {assessment.credibility_score:.2f}")
    print(f"Bias Score: {assessment.bias_score:.2f}")
    print(f"Overall Quality: {assessment.overall_quality:.2f}")
    print(f"Quality Flags: {assessment.flags}")

asyncio.run(main())
```

### Batch Processing

```python
from agents.quality_assessment_agent import assess_multiple_sources

async def batch_assessment():
    sources = [source1, source2, source3]  # List of ResearchSource objects
    assessments = await assess_multiple_sources(sources, max_concurrent=5)

    for assessment in assessments:
        print(f"{assessment.source_id}: {assessment.overall_quality:.2f}")

asyncio.run(batch_assessment())
```

## API Reference

### Core Functions

#### `assess_source_quality(source: ResearchSource) -> QualityAssessment`

Assess the quality of a single research source.

**Parameters:**
- `source`: ResearchSource object containing source data

**Returns:**
- `QualityAssessment`: Detailed quality metrics and scores

#### `assess_multiple_sources(sources: List[ResearchSource], max_concurrent: int = 10) -> List[QualityAssessment]`

Assess quality of multiple sources concurrently.

**Parameters:**
- `sources`: List of ResearchSource objects
- `max_concurrent`: Maximum concurrent assessments (default: 10)

**Returns:**
- `List[QualityAssessment]`: Quality assessments for all sources

#### `health_check() -> Dict[str, Any]`

Perform agent health check.

**Returns:**
- `Dict`: Health status and diagnostic information

### Data Models

#### `ResearchSource`

Input model for sources to be assessed.

```python
class ResearchSource(BaseModel):
    source_id: str                    # Unique identifier
    url: Optional[str]                # Source URL
    title: str                        # Source title
    content: str                      # Full content text
    metadata: Dict[str, Any]          # Additional metadata
    extraction_timestamp: datetime   # When source was extracted
```

#### `QualityAssessment`

Output model with quality metrics.

```python
class QualityAssessment(BaseModel):
    source_id: str              # Source identifier
    credibility_score: float    # 0.0-1.0 credibility rating
    bias_score: float           # 0.0-1.0 bias level (0=no bias)
    freshness_score: float      # 0.0-1.0 content freshness
    authority_score: float      # 0.0-1.0 domain authority
    overall_quality: float      # 0.0-1.0 composite quality
    confidence_rating: float    # 0.0-1.0 assessment confidence
    flags: List[str]           # Warning flags
    assessment_timestamp: datetime
    assessment_details: Dict[str, Any]  # Detailed breakdown
```

## Quality Assessment Methodology

### Credibility Scoring (Weighted Average)

- **Domain Authority** (30%): SSL, domain reputation, known high-authority indicators
- **Content Quality** (25%): Structure, citations, readability, completeness
- **Author Credentials** (20%): Byline presence, author information
- **Source Type** (15%): Academic, news, blog classification
- **Freshness** (10%): Publication and update dates

### Bias Detection Indicators

- **Emotional Language**: Detection of charged, emotional terms
- **Absolute Terms**: Excessive use of absolute statements
- **Perspective Diversity**: Single vs. multiple viewpoint analysis
- **Opinion vs. Fact**: Balance of opinion and factual content

### Performance Targets

- **Processing Time**: <30 seconds per source
- **Credibility Precision**: >85% accuracy
- **Bias Detection Recall**: >80% for obvious patterns
- **Concurrent Throughput**: 10-20 sources simultaneously

## Integration with Research Workflow

### Workflow Position

The Quality Assessment Agent serves as Agent #4 in the Research Engineering Workflow:

```
Web Research Agent (#2) ──┐
                          ├──► Quality Assessment Agent (#4) ──┐
Tool Integration Agent (#3) ──┘                                 ├──► Citation Management (#5)
                                                                 ├──► Data Synthesis (#7)
```

### Message Protocol

#### Input Message Format

```python
{
    "message_type": "task",
    "sender_id": "web_research_agent",
    "recipient_id": "quality_assessment_agent",
    "payload": {
        "sources": [ResearchSource, ...]
    }
}
```

#### Output Message Format

```python
{
    "message_type": "result",
    "sender_id": "quality_assessment_agent",
    "recipient_id": "citation_management_agent",
    "payload": {
        "assessments": [QualityAssessment, ...]
    }
}
```

## Testing

### Run Tests

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt

# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_requirements.py -v  # Requirements validation
pytest tests/test_performance.py -v  # Performance tests
pytest tests/test_agent.py -v        # Agent functionality

# Run with coverage
pytest tests/ --cov=agents.quality_assessment_agent --cov-report=html
```

### Test Coverage

The agent includes comprehensive tests covering:

- ✅ Core agent functionality with TestModel
- ✅ Tool validation and error handling
- ✅ Integration scenarios and workflow compliance
- ✅ Performance requirements (<30s processing)
- ✅ Error resilience and fallback mechanisms
- ✅ All requirements from INITIAL.md specification

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model name |
| `FACT_CHECK_API_KEY` | No | - | Fact-checking API key |
| `CREDIBILITY_THRESHOLD` | No | `0.7` | Credibility flag threshold |
| `BIAS_THRESHOLD` | No | `0.6` | Bias flag threshold |
| `PROCESSING_TIMEOUT` | No | `30` | Processing timeout (seconds) |
| `MAX_CONCURRENT_ASSESSMENTS` | No | `10` | Max concurrent sources |

### Scoring Weights

| Weight | Default | Description |
|--------|---------|-------------|
| `DOMAIN_AUTHORITY_WEIGHT` | `0.30` | Domain authority importance |
| `CONTENT_QUALITY_WEIGHT` | `0.25` | Content quality importance |
| `AUTHOR_CREDENTIALS_WEIGHT` | `0.20` | Author credentials importance |
| `SOURCE_TYPE_WEIGHT` | `0.15` | Source type importance |
| `FRESHNESS_WEIGHT` | `0.10` | Freshness importance |

## Error Handling

The agent implements comprehensive error handling:

- **Graceful Degradation**: Fallback scores when analysis fails
- **Timeout Protection**: Processing timeout enforcement
- **API Resilience**: External service failure handling
- **Concurrent Safety**: Error isolation in batch processing
- **Logging**: Detailed error logging for debugging

## Deployment

### Production Checklist

- [ ] Environment variables configured
- [ ] API keys secured and validated
- [ ] Health check endpoint accessible
- [ ] Monitoring and logging configured
- [ ] Performance testing completed
- [ ] Error handling validated

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
ENV PYTHONPATH=/app

CMD ["python", "-m", "agents.quality_assessment_agent.agent"]
```

## Monitoring

### Health Check Endpoint

```python
from agents.quality_assessment_agent import health_check

health_status = await health_check()
# Returns: {"status": "healthy", "agent_id": "quality_assessment_agent", ...}
```

### Key Metrics

- Processing time per source
- Concurrent assessment throughput
- Error rate and failure types
- Confidence rating distribution
- API response times

## Contributing

1. Follow existing code patterns and documentation
2. Add tests for new functionality
3. Ensure all tests pass: `pytest tests/ -v`
4. Update documentation for API changes
5. Validate performance requirements

## License

Part of the Research Engineering Workflow project. See main project license.

---

**Agent Version**: 1.0.0
**Last Updated**: 2025-09-27
**Status**: Production Ready ✅