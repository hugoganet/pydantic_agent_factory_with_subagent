# Quality Assessment Agent - Simple Requirements

## What This Agent Does
Evaluates the credibility, quality, and trustworthiness of research sources by analyzing content authority, detecting bias, and verifying facts across multiple sources to provide quality scores and confidence ratings for other research agents.

## Core Features (MVP)
1. **Source Credibility Assessment**: Evaluate website authority, domain reputation, and author credentials using basic scoring algorithms
2. **Content Quality Analysis**: Analyze source freshness, content depth, citation presence, and factual consistency
3. **Basic Bias Detection**: Identify potential bias indicators in language patterns and source selection using simple NLP techniques

## Technical Setup

### Model
- **Provider**: OpenAI
- **Model**: gpt-4o-mini
- **Why**: Fast inference for quality assessment tasks, good at analytical reasoning, cost-effective for high-volume processing

### Required Tools
1. **Domain Authority Checker**: Basic domain reputation scoring using simple heuristics (age, SSL, etc.)
2. **Content Analyzer**: Extract and analyze content characteristics (length, structure, citations)
3. **Source Cross-Reference**: Simple fact verification by comparing claims across multiple sources

### External Services
- **FactCheck.org API**: For fact-checking verification (with fallback to basic comparison)
- **Domain metadata APIs**: For basic authority assessment (optional, can use heuristics)

## Environment Variables
```bash
OPENAI_API_KEY=your-openai-api-key
FACT_CHECK_API_KEY=your-factcheck-api-key
```

## Input/Output Models

### Input: ResearchSource
```python
class ResearchSource(BaseModel):
    source_id: str
    url: Optional[str]
    title: str
    content: str
    metadata: Dict[str, Any]
    extraction_timestamp: datetime
```

### Output: QualityAssessment
```python
class QualityAssessment(BaseModel):
    source_id: str
    credibility_score: float  # 0.0-1.0
    bias_score: float         # 0.0-1.0 (0 = no bias)
    freshness_score: float    # 0.0-1.0
    authority_score: float    # 0.0-1.0
    overall_quality: float    # 0.0-1.0
    confidence_rating: float  # 0.0-1.0
    flags: List[str]         # Warning flags
    assessment_timestamp: datetime
```

## Integration with Workflow

### Agent Communication
- **Receives**: Raw research data from Web Research Agent (#2) and Tool Integration Agent (#3)
- **Provides**: Quality scores and assessments to Citation Management Agent (#5) and Data Synthesis Agent (#7)
- **Message Format**: Standard AgentMessage with ResearchSource payload and QualityAssessment response

### Performance Requirements
- **Processing Time**: <30 seconds per source assessment
- **Credibility Precision**: >85% accuracy in credibility scoring
- **Bias Detection Recall**: >80% for obvious bias patterns
- **Throughput**: Handle 10-20 sources concurrently

## Success Criteria

- [ ] Accurately assesses source credibility using domain authority and content analysis
- [ ] Detects obvious bias patterns in content and language
- [ ] Provides consistent quality scores that correlate with human assessment
- [ ] Integrates seamlessly with workflow message format
- [ ] Handles errors gracefully with appropriate fallbacks
- [ ] Processes sources within performance targets

## Assumptions Made

- **Simple Scoring Algorithm**: Use weighted combination of basic factors rather than complex ML models
- **English Content Focus**: Initial implementation focuses on English-language sources
- **Web Sources Primary**: Optimized for web content, with basic support for other source types
- **Basic Fact-Checking**: Simple cross-referencing rather than deep fact verification
- **Standard Web Patterns**: Assumes common web page structures and metadata formats
- **Fallback to Heuristics**: When external APIs fail, use rule-based scoring
- **No User Feedback Loop**: Quality assessments are final without human verification in MVP

## Quality Assessment Methodology

### Credibility Factors (Weighted Average)
- **Domain Authority** (30%): Age, SSL, reputation indicators
- **Content Quality** (25%): Length, structure, citations present
- **Author Credentials** (20%): Byline presence, bio information
- **Source Type** (15%): Academic, news, blog, social media classification
- **Freshness** (10%): Content publication and update dates

### Bias Detection Indicators
- **Language Analysis**: Emotional language, absolute terms, loaded words
- **Source Diversity**: Single-perspective vs multiple viewpoints
- **Citation Patterns**: Self-referential vs diverse source citation
- **Publication Context**: Known biased publications or neutral sources

### Confidence Rating Factors
- **Information Availability**: Completeness of source metadata
- **Assessment Consistency**: Agreement between multiple quality indicators
- **External Validation**: Availability of fact-checking or cross-references

---
Generated: 2025-09-26
Note: This is an MVP focusing on essential quality assessment. Advanced ML models, real-time fact-checking, and sophisticated bias detection can be added after the basic agent works reliably within the workflow.