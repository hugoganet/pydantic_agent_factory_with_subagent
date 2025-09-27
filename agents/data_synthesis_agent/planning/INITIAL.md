# Data Synthesis Agent - Requirements

## What This Agent Does
Integrates research findings from multiple agents and sources to generate comprehensive, coherent reports with validated insights and executive summaries tailored for different audiences.

## Core Features (MVP)
1. **Multi-source Data Integration**: Combine and normalize research findings from Web Research, Tool Integration, and Citation Management agents
2. **Pattern Recognition & Gap Analysis**: Identify trends, correlations, contradictions, and information gaps across integrated data sources
3. **Report Generation**: Create structured reports with executive summaries, key findings, and detailed analysis for target audiences

## Technical Setup

### Model
- **Provider**: openai
- **Model**: gpt-4o
- **Why**: Superior reasoning and synthesis capabilities needed for complex information integration and narrative generation

### Required Tools
1. **data_integrator**: Normalizes and combines research findings from multiple agent sources into unified data structures
2. **pattern_analyzer**: Identifies trends, correlations, and contradictions across integrated research data
3. **report_generator**: Creates structured reports with executive summaries and detailed analysis sections

### External Services
- None required (processes internal agent data)

## Environment Variables
```bash
LLM_API_KEY=your-openai-api-key
```

## Input Models

### SynthesisRequest
```python
@dataclass
class SynthesisRequest:
    research_findings: List[ResearchFinding]
    synthesis_requirements: str
    output_format: str  # "executive", "detailed", "technical"
    target_audience: str  # "executives", "researchers", "technical"
```

### ResearchFinding
```python
@dataclass
class ResearchFinding:
    source_agent: str  # "web_research", "tool_integration", "citation_management"
    content: str
    sources: List[str]
    confidence_level: float  # 0.0-1.0
    key_insights: List[str]
    timestamp: str
```

## Output Models

### SynthesizedReport
```python
@dataclass
class SynthesizedReport:
    executive_summary: str
    key_findings: List[KeyFinding]
    detailed_analysis: str
    supporting_evidence: List[str]
    identified_gaps: List[str]
    confidence_assessment: float
    generation_metadata: dict
```

### KeyFinding
```python
@dataclass
class KeyFinding:
    title: str
    description: str
    supporting_sources: List[str]
    confidence_level: float
    cross_validation_status: str  # "validated", "conflicting", "insufficient"
```

## Workflow Integration

### Phase 5: Synthesis (Sequential)
- **Input Sources**: Web Research Agent (#2), Tool Integration Agent (#3), Citation Management Agent (#5)
- **Output Target**: Research Orchestrator (#1)
- **Communication Protocol**: Standard AgentMessage format
- **Execution Mode**: Sequential after all research phases complete

### Performance Targets
- **Synthesis Time**: Complete within 2 minutes for standard reports
- **Quality Target**: >90% factual accuracy in synthesized content
- **Integration Efficiency**: Process up to 50 research findings per synthesis cycle

## Success Criteria

- [ ] Successfully integrates research findings from multiple agent sources
- [ ] Identifies patterns, trends, and contradictions across integrated data
- [ ] Generates coherent reports with executive summaries for different audiences
- [ ] Cross-validates findings and flags confidence levels accurately
- [ ] Completes synthesis within performance targets (2 minutes)
- [ ] Maintains >90% factual accuracy in final reports

## Assumptions Made

- Research findings arrive in standardized ResearchFinding format from upstream agents
- All source agents provide confidence levels and structured key insights
- Report generation focuses on 3 primary formats: executive, detailed, technical
- Cross-validation relies on source overlap and confidence scoring rather than external fact-checking
- Synthesis operates on completed research batches rather than streaming data

## Dependencies

### Internal Agent Dependencies
- **Web Research Agent (#2)**: Primary research content and web-based findings
- **Tool Integration Agent (#3)**: Specialized tool outputs and technical analysis
- **Citation Management Agent (#5)**: Source validation and citation formatting

### Communication Pattern
```python
# Receives AgentMessage from Research Orchestrator
synthesis_request = SynthesisRequest(...)
synthesized_report = await agent.run(synthesis_request, deps=deps)
# Returns SynthesizedReport to Research Orchestrator
```

---
Generated: 2025-09-26
Note: This is an MVP focusing on core synthesis capabilities. Advanced features like real-time streaming synthesis or external fact-checking can be added after the basic agent works.