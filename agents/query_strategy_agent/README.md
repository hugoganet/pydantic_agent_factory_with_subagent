# Query Strategy Agent

Strategic advisory service for research approach optimization within the Research Engineering Multi-Agent Workflow.

## Overview

The Query Strategy Agent analyzes research queries and provides strategic recommendations for optimal execution. It serves as Agent #6 in the 8-agent Research Engineering Workflow, providing advisory services to the Research Orchestrator Agent.

## Core Features

### 🔍 Query Complexity Analysis
- NLP-based complexity assessment using structured 1-10 scale methodology
- Evaluates scope, technical difficulty, data availability, and interdisciplinary factors
- Identifies key concepts and complexity indicators

### 🎯 Strategy Recommendation
- Recommends optimal research approach based on complexity and constraints
- Supports simple direct, moderate multi-source, and complex iterative strategies
- Provides realistic time estimates and resource allocation

### ⚠️ Risk Assessment
- Identifies potential challenges in research execution
- Assesses data availability, time constraints, quality, and scope creep risks
- Provides specific mitigation strategies and contingency plans

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your OpenAI API key
```

### Basic Usage

```python
from query_strategy_agent import analyze_research_strategy

# Analyze a research query
result = await analyze_research_strategy(
    research_query="How do machine learning algorithms impact climate change research?",
    constraints={
        "time_limit": 45,  # minutes
        "source_limit": 5,
        "quality_threshold": 0.8
    }
)

print(f"Recommended strategy: {result['strategy_analysis']}")
```

### Quick Complexity Check

```python
from query_strategy_agent import quick_complexity_check

complexity = await quick_complexity_check(
    "What are the latest developments in quantum computing?"
)
print(f"Complexity score: {complexity}/10")
```

## API Reference

### Core Functions

#### `analyze_research_strategy(research_query, constraints=None, workflow_context=None, **overrides)`
Comprehensive strategy analysis with complexity assessment, strategy recommendation, and risk analysis.

**Parameters:**
- `research_query` (str): The research question to analyze
- `constraints` (dict, optional): Time, source, and quality constraints
- `workflow_context` (dict, optional): Context from Research Orchestrator
- `**overrides`: Override default agent dependencies

**Returns:** Dictionary with strategy analysis, execution plan, and risk assessment

#### `quick_complexity_check(research_query)`
Fast complexity assessment for triage purposes.

**Parameters:**
- `research_query` (str): Query to assess

**Returns:** Float (1-10 complexity score)

### Agent Tools

#### `analyze_complexity`
- Analyzes query complexity using NLP techniques
- Returns complexity metrics and analysis details
- Caches results for performance optimization

#### `recommend_strategy`
- Selects optimal research approach based on complexity
- Considers constraints and historical performance data
- Provides execution plan with phases and resource allocation

#### `assess_risks`
- Identifies potential execution risks and challenges
- Calculates risk probabilities and impact scores
- Provides specific mitigation strategies

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_API_KEY` | OpenAI API key (required) | - |
| `LLM_MODEL` | Model for strategic reasoning | gpt-4o |
| `COMPLEXITY_THRESHOLD_LOW` | Low complexity threshold | 3.0 |
| `COMPLEXITY_THRESHOLD_HIGH` | High complexity threshold | 7.0 |
| `DEFAULT_CONFIDENCE_THRESHOLD` | Minimum recommendation confidence | 0.7 |

### Agent Dependencies

```python
from query_strategy_agent import AgentDependencies, settings

# Custom dependencies
deps = AgentDependencies.from_settings(
    settings,
    workflow_id="research_session_123",
    complexity_threshold_low=2.5,
    confidence_threshold=0.8
)
```

## Integration with Research Workflow

### Input from Research Orchestrator
```python
# Workflow integration example
workflow_context = {
    "session_id": "research_123",
    "orchestrator_id": "orchestrator_main",
    "research_domain": "climate_science",
    "previous_strategies": ["moderate_multisource"]
}

result = await analyze_research_strategy(
    research_query="Impact of Arctic ice melt on global sea levels",
    constraints={"time_limit": 60, "quality_threshold": 0.9},
    workflow_context=workflow_context
)
```

### Output to Research Orchestrator
```python
# Structured output format
{
    "success": True,
    "strategy_analysis": {
        "complexity_score": 7.2,
        "recommended_strategy": "complex_iterative",
        "estimated_duration": 75,
        "confidence_score": 0.82
    },
    "execution_plan": {
        "phases": ["initial_research", "deep_analysis", "synthesis"],
        "parallel_groups": [["web_search", "expert_sources"]],
        "quality_checkpoints": [...]
    },
    "risk_assessment": {
        "overall_risk_level": "medium",
        "critical_risks": ["time_constraint"],
        "mitigation_strategies": {...}
    }
}
```

## Strategy Types

### Simple Direct (Complexity < 3.0)
- Single high-quality source validation
- 15-20 minute execution time
- Minimal parallel processing

### Moderate Multi-source (Complexity 3.0-7.0)
- Multiple source analysis with synthesis
- 30-45 minute execution time
- Parallel research and validation phases

### Complex Iterative (Complexity > 7.0)
- Phased approach with quality checkpoints
- 60-90 minute execution time
- Maximum parallel processing and expert consultation

## Risk Categories

- **Data Availability**: Limited or inaccessible sources
- **Time Constraints**: Complexity exceeds available time
- **Quality Risk**: Sources may not meet quality standards
- **Scope Creep**: Research may expand beyond parameters
- **Technical Risk**: Domain expertise requirements

## Performance Characteristics

- **Response Time**: Sub-30 second strategy recommendations
- **Complexity Analysis**: ~0.15 seconds per query
- **Memory Usage**: <50MB typical operation
- **Accuracy**: 90% complexity assessment precision target

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=query_strategy_agent --cov-report=html

# Run specific test categories
pytest tests/test_complexity.py -v  # Complexity analysis tests
pytest tests/test_strategy.py -v    # Strategy recommendation tests
pytest tests/test_risk.py -v        # Risk assessment tests
```

## Development

### Project Structure
```
query_strategy_agent/
├── __init__.py          # Package exports
├── agent.py            # Main agent implementation
├── settings.py         # Configuration management
├── providers.py        # LLM provider setup
├── dependencies.py     # Agent dependencies
├── tools.py           # Analytical tools
├── prompts.py         # System prompts
├── requirements.txt   # Python dependencies
├── .env.example      # Environment template
└── README.md         # This file
```

### Code Quality
```bash
# Format code
black query_strategy_agent/

# Lint code
ruff query_strategy_agent/

# Type checking
mypy query_strategy_agent/
```

## Workflow Architecture Position

**Agent #6** in Research Engineering Multi-Agent Workflow:
- **Dependencies**: None (standalone advisory service)
- **Consumers**: Research Orchestrator Agent (primary)
- **Phase**: Planning & Strategy (pre-execution advisory)
- **Priority**: Medium (optimization enhancement, not blocking)

## Contributing

1. Follow existing code patterns and structure
2. Maintain comprehensive test coverage
3. Update documentation for API changes
4. Ensure compatibility with Research Orchestrator Agent interface
5. Test integration with workflow architecture

## License

Part of the Research Engineering Multi-Agent Workflow system.
See project root for license information.