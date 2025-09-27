# Data Synthesis Agent

A Pydantic AI agent specialized in integrating research findings from multiple sources into comprehensive, audience-appropriate reports. This agent is part of the Research Engineering Workflow system and operates as the final synthesis stage (Phase 5) in the multi-agent research pipeline.

## Overview

The Data Synthesis Agent combines research findings from upstream agents (Web Research #2, Tool Integration #3, Citation Management #5) and produces structured synthesis reports for the Research Orchestrator (#1).

### Key Capabilities

- **Multi-source Data Integration**: Combines and normalizes research findings from different agent sources
- **Pattern Recognition**: Identifies trends, correlations, and contradictions across integrated data
- **Report Generation**: Creates structured reports with executive summaries tailored for different audiences
- **Cross-validation**: Validates findings across sources and provides confidence assessments
- **Gap Analysis**: Identifies missing information and research opportunities

## Installation

1. **Clone the repository and navigate to the agent directory**:
```bash
cd agents/data_synthesis_agent
```

2. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key and configuration
```

## Configuration

### Environment Variables

Required configuration in `.env`:

```bash
# LLM Configuration (REQUIRED)
LLM_API_KEY=your-openai-api-key-here
LLM_MODEL=gpt-4o
LLM_PROVIDER=openai

# Performance Settings
MAX_FINDINGS_PER_SYNTHESIS=50
SYNTHESIS_TIMEOUT_SECONDS=120
MIN_CONFIDENCE_THRESHOLD=0.7

# Agent Configuration
AGENT_ID=data_synthesis_agent
LOG_LEVEL=INFO
DEBUG=false
```

### Model Configuration

The agent is optimized for OpenAI GPT-4o with synthesis-specific parameters:
- **Temperature**: 0.3 (consistent synthesis)
- **Max Tokens**: 4096 (comprehensive reports)
- **Timeout**: 120 seconds (performance target)

## Usage

### Python API

```python
from data_synthesis_agent import run_synthesis
from data_synthesis_agent.models import SynthesisRequest, ResearchFinding, SynthesisRequirements

# Create research findings
findings = [
    ResearchFinding(
        source_agent="web_research_agent",
        finding_id="finding_1",
        content="AI adoption is accelerating across industries...",
        confidence_level=0.8,
        key_insights=["AI adoption increasing", "Cross-industry impact"]
    ),
    # ... more findings
]

# Create synthesis request
request = SynthesisRequest(
    request_id="synthesis_001",
    research_findings=findings,
    output_format="executive",
    target_audience="executives"
)

# Run synthesis
result = await run_synthesis(request, session_id="session_001")

print(result.executive_summary)
print(f"Confidence: {result.confidence_assessment.overall_confidence:.1%}")
```

### CLI Interface

The agent includes a CLI for development and testing:

```bash
# Check agent health
python -m data_synthesis_agent.cli health

# Generate sample data for testing
python -m data_synthesis_agent.cli generate-sample --count 5 --output-file sample.json

# Run synthesis on sample data
python -m data_synthesis_agent.cli synthesize sample.json \
    --output-format executive \
    --target-audience executives \
    --output-file report.json

# View current configuration
python -m data_synthesis_agent.cli config
```

## Architecture

### Core Components

1. **Data Integration Tool** (`data_integrator`)
   - Combines findings from multiple sources
   - Handles deduplication and conflict detection
   - Normalizes confidence levels and formats

2. **Pattern Analysis Tool** (`pattern_analyzer`)
   - Identifies trends and correlations
   - Detects contradictions and information gaps
   - Calculates pattern confidence scores

3. **Report Generation Tool** (`report_generator`)
   - Creates audience-specific reports
   - Generates executive summaries
   - Formats citations and evidence

### Data Models

**Input Models**:
- `SynthesisRequest`: Complete synthesis request with findings and requirements
- `ResearchFinding`: Individual finding from upstream agents
- `SynthesisRequirements`: Synthesis configuration and focus areas

**Output Models**:
- `SynthesizedReport`: Complete synthesis report with analysis
- `KeyFinding`: Individual findings with confidence and validation
- `ConfidenceAssessment`: Overall confidence metrics

### Workflow Integration

The agent integrates with the Research Engineering Workflow:

```
Web Research (#2) ─┐
                   ├─→ Data Synthesis (#7) ─→ Research Orchestrator (#1)
Tool Integration (#3) ─┤
                   ├─→
Citation Management (#5) ─┘
```

## Performance

### Targets
- **Synthesis Time**: < 2 minutes for standard reports
- **Quality Target**: > 90% factual accuracy
- **Processing Capacity**: Up to 50 research findings per synthesis
- **Confidence Threshold**: Configurable (default: 0.7)

### Monitoring

The agent tracks performance metrics:
- Synthesis duration
- Findings processed
- Patterns identified
- Confidence scores
- Error rates

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=data_synthesis_agent --cov-report=html

# Run specific test categories
pytest tests/test_integration.py -v
```

### Test Structure

- **Unit Tests**: Individual tool and model testing
- **Integration Tests**: End-to-end synthesis workflows
- **Performance Tests**: Timing and capacity validation
- **Error Handling Tests**: Failure scenarios and recovery

## Development

### Code Structure

```
agents/data_synthesis_agent/
├── __init__.py          # Package exports
├── agent.py             # Main agent implementation
├── models.py            # Pydantic data models
├── tools.py             # Synthesis tools (integration, analysis, reporting)
├── dependencies.py      # Workflow dependencies and context
├── providers.py         # OpenAI model configuration
├── settings.py          # Environment configuration
├── prompts.py          # System prompts
├── cli.py              # Command-line interface
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
└── README.md           # This file
```

### Contributing

1. Follow the existing code style (Black formatting)
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure performance targets are maintained
5. Test integration with mock upstream agents

### Debugging

Enable debug mode for detailed logging:

```bash
# In .env file
DEBUG=true
LOG_LEVEL=DEBUG

# Or via CLI
python -m data_synthesis_agent.cli synthesize sample.json --session-id debug-session
```

## Integration Examples

### With Research Orchestrator

```python
# Receive synthesis request from orchestrator
@orchestrator.tool
async def request_synthesis(findings: List[ResearchFinding]) -> SynthesizedReport:
    request = SynthesisRequest(
        request_id=f"orch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        research_findings=findings,
        output_format="detailed",
        target_audience="researchers"
    )

    return await run_synthesis(request)
```

### Custom Report Formats

```python
# Custom synthesis with specific requirements
synthesis_req = SynthesisRequest(
    request_id="custom_synthesis",
    research_findings=findings,
    synthesis_requirements=SynthesisRequirements(
        focus_areas=["methodology", "implications"],
        depth_level="comprehensive",
        include_methodology=True,
        include_gaps=True,
        include_recommendations=True
    ),
    output_format="technical",
    target_audience="technical"
)

result = await run_synthesis(synthesis_req)
```

## Error Handling

The agent handles common error scenarios:

- **Invalid Input**: Validates research findings format and requirements
- **Timeout Handling**: Graceful degradation when synthesis exceeds time limits
- **Insufficient Data**: Continues with partial synthesis when possible
- **Model Errors**: Retry logic with exponential backoff
- **Integration Failures**: Returns partial results with error flags

## Security

- API keys stored in environment variables only
- No persistent storage of research content
- Input validation and sanitization
- Configurable timeout limits
- Audit logging for all operations

## Support

For issues and questions:
1. Check the GitHub issues for similar problems
2. Review the debug logs with `DEBUG=true`
3. Test with the provided CLI commands
4. Verify environment configuration

## License

This agent is part of the Research Engineering Workflow system.
See the main repository for license information.