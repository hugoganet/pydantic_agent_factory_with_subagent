# Query Strategy Agent - Requirements

## What This Agent Does
Analyzes research queries and recommends optimal strategies for execution within the Research Engineering Multi-Agent Workflow. Acts as an advisory service that helps the Research Orchestrator Agent select the most effective approach for complex research tasks.

## Core Features (MVP)

1. **Query Complexity Analysis**: Evaluate research queries using NLP techniques to determine scope, difficulty, and resource requirements
2. **Strategy Recommendation**: Select optimal research approach based on complexity assessment and constraints
3. **Risk Assessment**: Identify potential challenges and provide mitigation strategies for research execution

## Technical Setup

### Model
- **Provider**: openai
- **Model**: gpt-4o
- **Why**: Advanced reasoning capabilities needed for strategic analysis and complexity assessment

### Required Tools
1. **analyze_query_complexity**: Processes research queries to extract complexity indicators using NLP analysis
2. **recommend_strategy**: Evaluates constraints and historical data to suggest optimal research approach
3. **assess_risks**: Identifies potential challenges and provides mitigation strategies

### External Services
- **None**: This agent operates as a pure advisory service without external API dependencies

## Agent Classification
- **Type**: Advisory Agent (Strategy & Optimization)
- **Role**: Agent #6 in Research Engineering Multi-Agent Workflow
- **Dependencies**: None (standalone advisory service)
- **Consumers**: Research Orchestrator Agent (primary)

## Input Models

### StrategyRequest
```python
class StrategyRequest:
    research_query: str
    complexity_indicators: List[str]
    constraints: ResearchConstraints
    success_criteria: SuccessCriteria
    historical_data: Optional[HistoricalData]
```

### ResearchConstraints
```python
class ResearchConstraints:
    time_limit: int  # minutes
    source_limit: int  # max sources to analyze
    quality_threshold: float  # 0.0-1.0
    preferred_sources: List[str]
    excluded_sources: List[str]
```

### ComplexityMetrics
```python
class ComplexityMetrics:
    scope_score: float  # 1-10 scale
    technical_difficulty: float  # 1-10 scale
    data_availability: float  # 1-10 scale
    interdisciplinary_factor: float  # 1-10 scale
```

## Output Models

### StrategyRecommendation
```python
class StrategyRecommendation:
    recommended_strategy: str
    reasoning: str
    execution_plan: ExecutionPlan
    risk_assessment: RiskAssessment
    confidence_score: float  # 0.0-1.0
    estimated_duration: int  # minutes
```

### ExecutionPlan
```python
class ExecutionPlan:
    phases: List[str]
    parallel_groups: List[List[str]]
    fallback_strategies: List[str]
    quality_checkpoints: List[QualityCheckpoint]
```

### RiskAssessment
```python
class RiskAssessment:
    identified_risks: List[str]
    risk_scores: Dict[str, float]  # risk -> probability (0.0-1.0)
    mitigation_strategies: Dict[str, str]  # risk -> strategy
```

## Core Functionality

### Strategy Selection Logic
1. **Simple Queries** (complexity < 3): Direct search with single source
2. **Moderate Queries** (complexity 3-7): Multi-source analysis with synthesis
3. **Complex Queries** (complexity > 7): Phased approach with iterative refinement

### Complexity Assessment Factors
- Query length and linguistic complexity
- Number of distinct concepts/topics
- Technical terminology density
- Temporal scope requirements
- Multi-disciplinary indicators

### Risk Categories
- **Data Availability**: Sources may be limited or paywalled
- **Time Constraints**: Query complexity exceeds time limits
- **Quality Issues**: Sources may not meet quality threshold
- **Scope Creep**: Query may expand beyond initial parameters

## Environment Variables
```bash
LLM_API_KEY=your-openai-api-key
# No additional external API keys required
```

## Success Criteria

- [ ] Accurately assesses query complexity with consistent scoring (1-10 scale)
- [ ] Recommends appropriate strategy based on complexity and constraints
- [ ] Provides realistic time estimates within reasonable accuracy
- [ ] Identifies key risks and provides actionable mitigation strategies
- [ ] Returns structured recommendations in under 30 seconds
- [ ] Integrates seamlessly with Research Orchestrator Agent

## Integration Points

### Research Orchestrator Agent
- **Input**: Receives StrategyRequest from orchestrator
- **Output**: Returns StrategyRecommendation with execution guidance
- **Workflow**: Advisory role - orchestrator makes final decisions

### Performance Metrics
- Strategy recommendation accuracy based on actual execution results
- Time estimation accuracy (target: within 20% of actual)
- Risk prediction effectiveness (measured by mitigation success)

## Assumptions Made

- Historical data will be maintained by the Research Orchestrator Agent
- Complex queries requiring deep domain expertise will be flagged for human review
- Basic NLP analysis sufficient for complexity assessment (no advanced ML models required)
- Strategy recommendations focus on approach rather than specific source selection
- Risk assessment covers workflow risks rather than content accuracy risks

## System Prompt Focus Areas

1. **Strategic Thinking**: Analyze queries holistically and recommend comprehensive approaches
2. **Risk Awareness**: Proactively identify potential challenges in research execution
3. **Resource Optimization**: Balance quality requirements with time/source constraints
4. **Adaptive Planning**: Consider fallback strategies and quality checkpoints

## Workflow Position

**Position**: Agent #6 in 8-agent Research Engineering Workflow
**Phase**: Planning & Strategy (pre-execution advisory)
**Criticality**: Medium priority - enhances execution efficiency but not blocking

---
Generated: 2025-09-26
Note: This is an MVP focused on core strategy recommendation functionality. Advanced features like machine learning-based predictions and detailed historical analysis can be added after the basic agent works reliably.