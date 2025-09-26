# Research Orchestrator Agent

Master coordinator for the Research Engineering Workflow system. Orchestrates 7 specialized agents across a 6-phase research workflow to deliver comprehensive research reports with quality assurance.

## Overview

The Research Orchestrator Agent serves as the central command hub for complex multi-agent research operations. It analyzes research requests, creates strategic execution plans, coordinates parallel agent execution, and synthesizes final comprehensive reports with proper source attribution.

### Key Capabilities

- **Master Coordination**: Orchestrates 7 specialized agents in parallel workflows
- **Strategic Planning**: Analyzes request complexity and creates optimal execution strategies
- **Quality Assurance**: Enforces >0.8 source credibility and >0.7 confidence thresholds
- **Performance Optimization**: Maintains <10 minute research completion time
- **Error Recovery**: Robust retry mechanisms with exponential backoff
- **Real-time Monitoring**: Comprehensive workflow state tracking and health monitoring

## Architecture

### Agent Network

The orchestrator coordinates these specialized agents:

1. **Query Strategy Agent (#6)**: Strategic planning recommendations
2. **Web Research Agent (#2)**: Web search and content extraction
3. **Tool Integration Agent (#3)**: Internal systems and API integration
4. **Quality Assessment Agent (#4)**: Source credibility verification
5. **Citation Management Agent (#5)**: Reference formatting and attribution
6. **Data Synthesis Agent (#7)**: Multi-source information integration
7. **Workflow Coordinator Agent (#8)**: System health monitoring

### Workflow Phases

1. **Planning** (30s): Request analysis and strategy coordination
2. **Research** (2-3 min): Parallel Web Research + Tool Integration
3. **Assessment** (1 min): Quality verification and credibility scoring
4. **Attribution** (30s): Citation formatting and reference management
5. **Synthesis** (1-2 min): Multi-source data integration and report generation
6. **Delivery** (30s): Final report compilation and user delivery

## Quick Start

### Installation

```bash
# Navigate to agent directory
cd agents/research_orchestrator_agent

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Environment Configuration

Required environment variables:

```bash
# OpenAI API for GPT-4o model
LLM_API_KEY=your-openai-api-key

# Redis for inter-agent communication
REDIS_URL=redis://localhost:6379/0

# Agent endpoints (adjust ports as needed)
AGENT_ENDPOINT_WEB_RESEARCH=http://localhost:8002
AGENT_ENDPOINT_TOOL_INTEGRATION=http://localhost:8003
# ... (see .env.example for complete list)
```

### Basic Usage

```python
from research_orchestrator_agent import run_orchestration

# Simple research request
result = await run_orchestration(
    "Research the latest developments in quantum computing and their applications in cryptography"
)

print(result)  # Comprehensive research report with citations
```

### Advanced Usage

```python
from research_orchestrator_agent import orchestrator_agent, OrchestratorDependencies
from research_orchestrator_agent.settings import settings

# Custom configuration
deps = OrchestratorDependencies.from_settings(
    settings,
    max_parallel_agents=3,
    research_timeout=300,  # 5 minutes
    min_source_quality=0.9,  # Higher quality threshold
    priority_level="high"
)

# Execute with custom dependencies
await deps.setup_infrastructure()
result = await orchestrator_agent.run(
    "Analyze market trends in renewable energy sector",
    deps=deps
)
await deps.cleanup()
```

## API Reference

### Core Functions

#### `run_orchestration(research_request, session_id=None, priority_level=None, **overrides)`

Execute complete research orchestration with automatic dependency management.

**Parameters:**
- `research_request` (str): User's research query
- `session_id` (str, optional): Session identifier for tracking
- `priority_level` (str, optional): Priority level ('high', 'normal', 'low')
- `**overrides`: Custom dependency configurations

**Returns:**
- `str`: Comprehensive research report with citations

#### `health_check()`

Check orchestrator health status and connectivity.

**Returns:**
- `dict`: Health status with connectivity information

### Agent Tools

The orchestrator provides 4 core coordination tools:

#### `analyze_research_request`

Analyzes research requests and creates strategic execution plans.

```python
result = await analyze_research_request(
    query="Research artificial intelligence in healthcare",
    complexity="medium",  # auto-detected if not provided
    timeout_minutes=10,
    quality_threshold=0.8
)
```

#### `distribute_parallel_tasks`

Distributes tasks to multiple agents for parallel execution.

```python
result = await distribute_parallel_tasks(
    execution_plan=analysis_result["execution_plan"],
    target_agents=["web_research_agent", "tool_integration_agent"],
    max_parallel=5
)
```

#### `coordinate_quality_assessment`

Coordinates quality assessment of research results.

```python
result = await coordinate_quality_assessment(
    research_results=research_data,
    quality_threshold=0.8,
    confidence_threshold=0.7
)
```

#### `synthesize_final_report`

Synthesizes final comprehensive research report.

```python
result = await synthesize_final_report(
    validated_data=quality_verified_data,
    citations=formatted_citations,
    synthesis_format="comprehensive"
)
```

## Configuration

### Quality Thresholds

```python
# Default quality requirements
quality_config = {
    "min_source_quality_score": 0.8,      # Source credibility
    "min_confidence_rating": 0.7,         # Confidence threshold
    "max_quality_retries": 2               # Quality improvement attempts
}
```

### Performance Settings

```python
# Performance optimization
performance_config = {
    "max_parallel_agents": 5,             # Max concurrent agents
    "research_timeout_minutes": 10,       # Total research time limit
    "task_timeout_seconds": 180,          # Individual task timeout
    "retry_max_attempts": 3,              # Error recovery attempts
}
```

### Agent Endpoints

Configure HTTP endpoints for coordinated agents:

```python
agent_endpoints = {
    "web_research": "http://localhost:8002",
    "tool_integration": "http://localhost:8003",
    "quality_assessment": "http://localhost:8004",
    "citation_management": "http://localhost:8005",
    "query_strategy": "http://localhost:8006",
    "data_synthesis": "http://localhost:8007",
    "workflow_coordinator": "http://localhost:8008"
}
```

## Examples

### Simple Research Query

```python
import asyncio
from research_orchestrator_agent import run_orchestration

async def simple_research():
    query = "What are the environmental impacts of electric vehicles?"

    result = await run_orchestration(query)
    print(f"Research complete: {len(result)} characters")
    return result

asyncio.run(simple_research())
```

### High-Priority Research

```python
async def urgent_research():
    query = "Critical security vulnerabilities in container orchestration platforms"

    # High priority mode: faster execution, higher quality thresholds
    result = await run_orchestration(
        query,
        priority_level="high",
        min_source_quality=0.9,
        research_timeout=300  # 5 minutes only
    )

    return result
```

### Custom Session Tracking

```python
import uuid
from datetime import datetime

async def tracked_research():
    session_id = str(uuid.uuid4())

    query = "Machine learning applications in drug discovery"

    result = await run_orchestration(
        query,
        session_id=session_id,
        user_id="research_team_001"
    )

    print(f"Session {session_id} completed at {datetime.now()}")
    return result
```

### Error Handling

```python
async def robust_research():
    try:
        result = await run_orchestration(
            "Complex multi-domain research query",
            research_timeout=600,  # 10 minutes
            retry_max_attempts=5   # Extra retry attempts
        )

        return result

    except Exception as e:
        print(f"Research failed: {e}")

        # Check health status
        health = await health_check()
        if health["status"] == "unhealthy":
            print(f"System issue: {health.get('error')}")

        raise
```

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_agent.py -v          # Agent functionality
python -m pytest tests/test_tools.py -v         # Coordination tools
python -m pytest tests/test_integration.py -v   # Integration tests
python -m pytest tests/test_validation.py -v    # Requirements validation

# Run with coverage
python -m pytest tests/ --cov=agents.research_orchestrator_agent --cov-report=html
```

### Test Configuration

Tests use TestModel and FunctionModel for dependency-free validation:

```python
from pydantic_ai.models.test import TestModel
from research_orchestrator_agent import orchestrator_agent

# Override model for testing
test_agent = orchestrator_agent.override(
    model=TestModel(
        custom_result_text="Strategic execution plan created successfully"
    )
)

result = await test_agent.run("Test research request", deps=test_deps)
```

## Performance Monitoring

### Metrics Collection

The orchestrator automatically collects performance metrics:

```python
# Access metrics after orchestration
deps = OrchestratorDependencies.from_settings(settings)
await deps.setup_infrastructure()

# Run orchestration
result = await orchestrator_agent.run(query, deps=deps)

# Get performance metrics
metrics = deps.get_task_metrics()
print(f"Execution time: {metrics['elapsed_seconds']}s")
print(f"Success rate: {metrics['completed_tasks']}/{metrics['active_tasks'] + metrics['completed_tasks']}")

await deps.cleanup()
```

### Health Monitoring

```python
# Regular health checks
health_status = await health_check()

if health_status["status"] == "healthy":
    print(f"Orchestrator ready: {health_status['agent_endpoints']} agents configured")
else:
    print(f"Health issue: {health_status.get('error')}")
```

## Troubleshooting

### Common Issues

**Redis Connection Failed**
```
Error: Failed to connect to Redis
Solution: Ensure Redis is running on specified URL
```

**Agent Timeout**
```
Error: Task timeout exceeded
Solution: Increase task_timeout_seconds or check agent availability
```

**Quality Threshold Not Met**
```
Error: Source credibility below threshold
Solution: Lower min_source_quality_score or improve source selection
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("research_orchestrator_agent")

# Run with debug output
result = await run_orchestration(query)
```

## Contributing

### Development Setup

```bash
# Clone and setup development environment
git clone <repository>
cd agents/research_orchestrator_agent

# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov black ruff mypy

# Run code quality checks
black .
ruff check .
mypy .

# Run tests before committing
python -m pytest tests/ -v --cov
```

### Code Style

- Follow PEP 8 with Black formatting
- Use type hints for all functions
- Document all public methods with docstrings
- Maintain >90% test coverage

## License

Research Engineering Workflow System
Part of the Pydantic AI Agent Factory

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the test suite for usage examples
3. Examine logs for detailed error information
4. Verify all dependencies and configurations

The Research Orchestrator Agent is designed for high reliability and comprehensive error reporting to facilitate quick issue resolution.