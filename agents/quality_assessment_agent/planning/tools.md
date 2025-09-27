# Quality Assessment Agent Tools

Tools for evaluating source credibility, detecting bias, and assessing content quality for research sources.

## Tool 1: Domain Authority Analyzer

**Purpose**: Assess website authority and domain credibility using multiple heuristics and external data sources.

**Function Signature**:
```python
@agent.tool
async def analyze_domain_authority(
    ctx: RunContext[AgentDependencies],
    url: str,
    domain: str
) -> Dict[str, Any]
```

**Parameters**:
- `url` (str): Full URL of the source to analyze
- `domain` (str): Extracted domain name for focused analysis

**Returns**:
```python
{
    "authority_score": float,        # 0.0-1.0 composite authority score
    "domain_age": Optional[int],     # Domain age in years
    "ssl_enabled": bool,             # HTTPS/SSL certificate status
    "domain_category": str,          # "academic", "news", "blog", "social", "commercial"
    "reputation_indicators": List[str], # Known quality indicators found
    "warning_flags": List[str],      # Suspicious patterns detected
    "confidence": float              # 0.0-1.0 confidence in assessment
}
```

**Core Logic**:
1. **Domain Metadata Extraction**:
   - Check domain age using WHOIS data (with caching)
   - Verify SSL certificate presence and validity
   - Extract domain extension (.edu, .gov, .org patterns)

2. **Authority Scoring Algorithm** (weighted):
   - Domain age: 20% (older = more credible)
   - SSL presence: 15% (HTTPS = more trustworthy)
   - Domain type: 25% (.edu/.gov = high, .com = medium, others = variable)
   - URL structure: 20% (clean URLs vs suspicious patterns)
   - Known reputation: 20% (whitelist/blacklist matching)

3. **Fallback Mechanisms**:
   - If WHOIS fails: Use domain extension heuristics
   - If SSL check fails: Assume HTTP (lower score)
   - If all external calls fail: Use URL pattern analysis only

**Error Handling**:
- Network timeouts: Return partial assessment with confidence penalty
- API failures: Fall back to heuristic-based scoring
- Invalid URLs: Return low authority score with appropriate flags

---

## Tool 2: Content Quality Analyzer

**Purpose**: Analyze content characteristics to assess information quality, depth, and structure.

**Function Signature**:
```python
@agent.tool_plain
def analyze_content_quality(
    content: str,
    title: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]
```

**Parameters**:
- `content` (str): Full text content of the source
- `title` (str): Source title/headline
- `metadata` (Dict): Available metadata about the source

**Returns**:
```python
{
    "quality_score": float,          # 0.0-1.0 overall content quality
    "content_length": int,           # Character count
    "structure_score": float,        # 0.0-1.0 content organization quality
    "citation_count": int,           # Number of citations/references found
    "freshness_score": float,        # 0.0-1.0 based on publication date
    "readability_score": float,      # 0.0-1.0 content clarity assessment
    "depth_indicators": List[str],   # Quality indicators found
    "quality_flags": List[str]       # Content quality issues
}
```

**Core Logic**:
1. **Content Structure Analysis**:
   - Paragraph count and average length
   - Heading structure (H1, H2, etc.)
   - List and bullet point usage
   - Sentence length distribution

2. **Citation and Reference Detection**:
   - URL pattern matching for external links
   - Academic citation format detection
   - Reference section identification
   - Source attribution patterns

3. **Quality Scoring Algorithm** (weighted):
   - Content length: 20% (optimal range 500-3000 words)
   - Structure quality: 25% (headings, paragraphs, organization)
   - Citation presence: 25% (external references found)
   - Readability: 15% (sentence complexity, vocabulary)
   - Freshness: 15% (publication/update date recency)

4. **Freshness Assessment**:
   - Extract publication date from metadata or content
   - Calculate age penalty (exponential decay after 2 years for news, 5 years for research)
   - Handle missing dates with neutral score

**Pattern Matching**:
- Academic citations: `([Author], [Year])`, `[Author] et al.`
- Web references: `http://`, `https://`, `www.`
- Quality indicators: `"study shows"`, `"research indicates"`, `"according to"`
- Warning patterns: `"some say"`, `"many believe"`, excessive capitalization

---

## Tool 3: Bias Detection Analyzer

**Purpose**: Identify potential bias indicators in content using language analysis and source patterns.

**Function Signature**:
```python
@agent.tool
async def detect_content_bias(
    ctx: RunContext[AgentDependencies],
    content: str,
    url: str,
    source_type: str
) -> Dict[str, Any]
```

**Parameters**:
- `content` (str): Full text content to analyze for bias
- `url` (str): Source URL for context and reputation checking
- `source_type` (str): Categorized source type ("news", "blog", "academic", etc.)

**Returns**:
```python
{
    "bias_score": float,             # 0.0-1.0 (0 = neutral, 1 = highly biased)
    "bias_type": str,                # "left", "right", "commercial", "confirmation", "neutral"
    "language_indicators": List[str], # Specific biased language patterns found
    "emotional_score": float,        # 0.0-1.0 emotional language intensity
    "objectivity_score": float,      # 0.0-1.0 objective vs subjective language
    "source_diversity": float,       # 0.0-1.0 based on citation diversity
    "bias_flags": List[str],         # Specific bias warning flags
    "confidence": float              # 0.0-1.0 confidence in bias assessment
}
```

**Core Logic**:
1. **Language Pattern Analysis**:
   - Emotional language detection: intensity adjectives, absolute terms
   - Loaded language: politically charged words, inflammatory terms
   - Opinion vs fact ratio: statement types analysis
   - First-person usage: "I believe", "we think" patterns

2. **Source Pattern Analysis**:
   - Citation diversity: variety of sources referenced
   - Self-referential patterns: excessive self-citation
   - Perspective balance: single vs multiple viewpoints presented
   - Cherry-picking indicators: selective data presentation

3. **Bias Scoring Algorithm**:
   - Language objectivity: 35% (factual vs opinion language)
   - Emotional intensity: 25% (calm vs inflammatory tone)
   - Source diversity: 20% (varied vs limited perspectives)
   - Known bias patterns: 20% (recognized biased source patterns)

4. **Bias Type Classification**:
   - Political bias: left/right leaning language patterns
   - Commercial bias: promotional language, product placement
   - Confirmation bias: selective evidence presentation
   - Neutral: balanced language and diverse sourcing

**Fallback Mechanisms**:
- If content too short: Analyze title and available metadata only
- If language analysis fails: Use source reputation patterns
- If all analysis fails: Return neutral with low confidence

**Bias Pattern Examples**:
- High emotional language: "outrageous", "shocking", "unbelievable"
- Absolute statements: "always", "never", "all [group] are"
- Loaded terms: Politically charged vocabulary, inflammatory descriptors
- Opinion markers: "clearly", "obviously", "any reasonable person"

---

## Tool Integration Architecture

### Error Handling Strategy

All tools implement consistent error handling:

```python
try:
    # Core tool logic
    result = await tool_operation()
    return {"success": True, "data": result}
except APIException as e:
    logger.warning(f"API failure: {e}, falling back to heuristics")
    fallback_result = heuristic_analysis()
    return {"success": True, "data": fallback_result, "fallback": True}
except Exception as e:
    logger.error(f"Tool error: {e}")
    return {"success": False, "error": str(e)}
```

### Performance Optimization

- **Caching**: Domain reputation and WHOIS data cached for 24 hours
- **Timeouts**: All external calls timeout after 10 seconds
- **Parallel Processing**: Independent analysis components run concurrently
- **Lightweight Analysis**: Prioritize fast heuristics over complex computations

### Quality Score Composition

Final quality assessment combines all tool outputs:

```python
overall_quality = (
    authority_score * 0.30 +      # Domain authority weight
    content_quality * 0.35 +     # Content quality weight
    (1.0 - bias_score) * 0.25 +  # Bias penalty (inverted)
    freshness_score * 0.10       # Freshness weight
)

confidence_rating = min(
    domain_confidence,
    content_confidence,
    bias_confidence
) * availability_penalty  # Penalty for missing data
```

### Dependencies Required

- `httpx`: For HTTP requests and domain analysis
- `python-dateutil`: For date parsing and freshness calculation
- `re`: For pattern matching and content analysis
- `urllib.parse`: For URL parsing and validation
- `textstat`: For readability analysis (optional, fallback available)

### External API Integration

- **Fallback Philosophy**: Every external call has a heuristic fallback
- **Timeout Management**: 10-second timeouts on all external requests
- **Rate Limiting**: Maximum 5 concurrent external API calls
- **Graceful Degradation**: Partial assessments returned when APIs fail

---

## Testing Strategy

### Test Coverage Areas

1. **Domain Authority Tool**:
   - Valid domains with known reputation
   - Invalid/malformed URLs
   - Network timeout scenarios
   - SSL certificate variations

2. **Content Quality Tool**:
   - Various content lengths and structures
   - Different citation formats and counts
   - Missing metadata scenarios
   - Edge cases (very short/long content)

3. **Bias Detection Tool**:
   - Known biased vs neutral content samples
   - Different source types and contexts
   - Emotional vs factual language samples
   - Mixed bias scenarios

### Mock Data Requirements

- Sample domains with known authority levels
- Content samples with varying quality characteristics
- Biased and neutral text samples for validation
- Metadata examples from different source types

---

**Generated**: 2025-09-26
**Purpose**: Tool specifications for Quality Assessment Agent MVP - Simple, focused tools for credibility assessment, content quality analysis, and bias detection with robust fallback mechanisms.