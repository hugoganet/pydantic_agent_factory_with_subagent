"""Quality assessment tools for analyzing source credibility and bias."""

import re
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse
import aiohttp
from pydantic_ai import RunContext

from .dependencies import QualityAssessmentDependencies
from .models import DomainAnalysis, ContentAnalysis, BiasAnalysis


async def analyze_domain_authority(
    ctx: RunContext[QualityAssessmentDependencies],
    url: Optional[str]
) -> DomainAnalysis:
    """Analyze domain authority and reputation indicators."""
    if not url:
        return DomainAnalysis(
            domain="unknown",
            authority_indicators=["no_url_provided"]
        )

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check SSL
        ssl_enabled = url.startswith("https://")

        # Basic domain reputation heuristics
        authority_indicators = []
        reputation_score = 0.5  # Default neutral score

        # Known high-authority domains
        high_authority_domains = {
            "wikipedia.org": 0.9,
            "gov": 0.95,
            "edu": 0.9,
            "nature.com": 0.9,
            "science.org": 0.9,
            "plos.org": 0.9,
            "nih.gov": 0.95,
            "cdc.gov": 0.95,
            "who.int": 0.95,
            "reuters.com": 0.8,
            "bbc.com": 0.8,
            "apnews.com": 0.8
        }

        # Check for known high-authority patterns
        for pattern, score in high_authority_domains.items():
            if pattern in domain:
                reputation_score = score
                authority_indicators.append(f"high_authority_domain:{pattern}")
                break

        # Check for academic/government indicators
        if domain.endswith('.edu'):
            reputation_score = max(reputation_score, 0.85)
            authority_indicators.append("educational_domain")
        elif domain.endswith('.gov'):
            reputation_score = max(reputation_score, 0.9)
            authority_indicators.append("government_domain")
        elif domain.endswith('.org'):
            reputation_score = max(reputation_score, 0.7)
            authority_indicators.append("organization_domain")

        # SSL bonus
        if ssl_enabled:
            authority_indicators.append("ssl_enabled")
            reputation_score = min(1.0, reputation_score + 0.05)

        # Domain age estimation (simplified)
        domain_age_score = 0.5  # Default for unknown
        if any(indicator in domain for indicator in ["wikipedia", "gov", "edu"]):
            domain_age_score = 0.9
        elif len(domain.split('.')[0]) > 8:  # Longer domain names might be more established
            domain_age_score = 0.6

        return DomainAnalysis(
            domain=domain,
            ssl_enabled=ssl_enabled,
            domain_age_score=domain_age_score,
            reputation_score=reputation_score,
            authority_indicators=authority_indicators
        )

    except Exception as e:
        return DomainAnalysis(
            domain="parse_error",
            authority_indicators=[f"analysis_error:{str(e)[:50]}"]
        )


async def analyze_content_quality(
    ctx: RunContext[QualityAssessmentDependencies],
    content: str,
    title: str = ""
) -> ContentAnalysis:
    """Analyze content quality indicators."""
    try:
        # Basic content metrics
        words = content.split()
        word_count = len(words)

        # Structure quality heuristics
        structure_score = 0.0

        # Check for basic structure elements
        if title and len(title) > 10:
            structure_score += 0.2

        # Check for paragraphs (double newlines)
        paragraphs = len(re.split(r'\n\s*\n', content))
        if paragraphs > 2:
            structure_score += 0.3

        # Check for headings (simple heuristic)
        heading_patterns = [r'^#+\s', r'^[A-Z][^a-z]*$', r'\n[A-Z][^a-z]*\n']
        heading_count = sum(len(re.findall(pattern, content, re.MULTILINE)) for pattern in heading_patterns)
        if heading_count > 0:
            structure_score += 0.2

        # Check for lists
        list_patterns = [r'^\s*[-*+]\s', r'^\s*\d+\.\s']
        list_count = sum(len(re.findall(pattern, content, re.MULTILINE)) for pattern in list_patterns)
        if list_count > 0:
            structure_score += 0.1

        # Word count quality assessment
        if word_count > 500:
            structure_score += 0.2
        elif word_count > 200:
            structure_score += 0.1

        structure_score = min(1.0, structure_score)

        # Citation detection (simplified)
        citation_patterns = [
            r'\[[\d,\s-]+\]',  # [1], [1-3], [1,2,3]
            r'\([\w\s]+,?\s*\d{4}\)',  # (Author, 2023)
            r'https?://\S+',  # URLs
            r'doi:\S+',  # DOI references
            r'et al\.',  # Academic citations
        ]

        citation_count = sum(len(re.findall(pattern, content, re.IGNORECASE)) for pattern in citation_patterns)

        # Readability score (simplified)
        if word_count == 0:
            readability_score = 0.0
        else:
            sentences = len(re.split(r'[.!?]+', content))
            avg_words_per_sentence = word_count / max(sentences, 1)

            # Ideal range: 15-20 words per sentence
            if 10 <= avg_words_per_sentence <= 25:
                readability_score = 0.8
            elif 5 <= avg_words_per_sentence <= 35:
                readability_score = 0.6
            else:
                readability_score = 0.4

        # Completeness score based on content depth
        completeness_score = 0.5  # Default
        if word_count > 1000 and citation_count > 3:
            completeness_score = 0.9
        elif word_count > 500 and citation_count > 1:
            completeness_score = 0.7
        elif word_count > 200:
            completeness_score = 0.6

        return ContentAnalysis(
            word_count=word_count,
            structure_score=structure_score,
            citation_count=citation_count,
            readability_score=readability_score,
            completeness_score=completeness_score
        )

    except Exception as e:
        return ContentAnalysis(
            word_count=0,
            structure_score=0.0,
            citation_count=0,
            readability_score=0.0,
            completeness_score=0.0
        )


async def analyze_bias_indicators(
    ctx: RunContext[QualityAssessmentDependencies],
    content: str,
    title: str = ""
) -> BiasAnalysis:
    """Analyze content for bias indicators."""
    try:
        full_text = f"{title} {content}".lower()
        bias_indicators = []

        # Emotional language indicators
        emotional_words = [
            'shocking', 'outrageous', 'incredible', 'unbelievable', 'devastating',
            'horrific', 'amazing', 'fantastic', 'terrible', 'awful', 'brilliant',
            'genius', 'stupid', 'ridiculous', 'absurd', 'insane', 'crazy'
        ]

        emotional_count = sum(full_text.count(word) for word in emotional_words)
        word_count = len(content.split())
        emotional_language_score = min(1.0, emotional_count / max(word_count / 100, 1))

        if emotional_language_score > 0.1:
            bias_indicators.append(f"high_emotional_language:{emotional_count}")

        # Absolute terms
        absolute_terms = [
            'always', 'never', 'all', 'none', 'everyone', 'nobody', 'everything',
            'nothing', 'completely', 'totally', 'absolutely', 'definitely',
            'certainly', 'obviously', 'clearly', 'undoubtedly'
        ]

        absolute_terms_count = sum(full_text.count(term) for term in absolute_terms)

        if absolute_terms_count > word_count / 200:  # More than 0.5% absolute terms
            bias_indicators.append(f"excessive_absolute_terms:{absolute_terms_count}")

        # Opinion vs fact language
        opinion_indicators = [
            'i think', 'i believe', 'in my opinion', 'i feel', 'seems to',
            'appears to', 'might be', 'could be', 'probably', 'likely'
        ]

        fact_indicators = [
            'according to', 'research shows', 'studies indicate', 'data reveals',
            'statistics show', 'evidence suggests', 'analysis found'
        ]

        opinion_count = sum(full_text.count(indicator) for indicator in opinion_indicators)
        fact_count = sum(full_text.count(indicator) for indicator in fact_indicators)

        # Perspective diversity assessment
        if fact_count > opinion_count:
            perspective_diversity = 0.8
        elif fact_count == opinion_count and fact_count > 0:
            perspective_diversity = 0.7
        elif opinion_count > 0:
            perspective_diversity = 0.4
            bias_indicators.append("opinion_heavy_content")
        else:
            perspective_diversity = 0.5

        # Political bias indicators (simplified)
        left_indicators = ['progressive', 'liberal', 'socialist', 'equality', 'justice']
        right_indicators = ['conservative', 'traditional', 'freedom', 'liberty', 'individual']

        left_count = sum(full_text.count(term) for term in left_indicators)
        right_count = sum(full_text.count(term) for term in right_indicators)

        if abs(left_count - right_count) > 3:
            bias_indicators.append("potential_political_bias")

        # Overall neutrality score
        neutrality_score = 1.0 - (emotional_language_score * 0.4 +
                                  min(absolute_terms_count / max(word_count / 100, 1), 1.0) * 0.3 +
                                  (1.0 - perspective_diversity) * 0.3)
        neutrality_score = max(0.0, neutrality_score)

        return BiasAnalysis(
            emotional_language_score=emotional_language_score,
            absolute_terms_count=absolute_terms_count,
            perspective_diversity=perspective_diversity,
            bias_indicators=bias_indicators,
            neutrality_score=neutrality_score
        )

    except Exception as e:
        return BiasAnalysis(
            emotional_language_score=0.0,
            absolute_terms_count=0,
            perspective_diversity=0.5,
            bias_indicators=[f"analysis_error:{str(e)[:50]}"],
            neutrality_score=0.5
        )


async def check_freshness(
    ctx: RunContext[QualityAssessmentDependencies],
    extraction_timestamp: datetime,
    metadata: Dict[str, Any]
) -> float:
    """Assess content freshness based on timestamps and metadata."""
    try:
        now = datetime.now()

        # Check metadata for publication date
        pub_date = None
        date_fields = ['published_date', 'publication_date', 'date', 'last_modified']

        for field in date_fields:
            if field in metadata and metadata[field]:
                try:
                    if isinstance(metadata[field], str):
                        # Try common date formats
                        date_formats = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%d/%m/%Y']
                        for fmt in date_formats:
                            try:
                                pub_date = datetime.strptime(metadata[field], fmt)
                                break
                            except ValueError:
                                continue
                    elif isinstance(metadata[field], datetime):
                        pub_date = metadata[field]
                except:
                    continue

                if pub_date:
                    break

        # Use extraction timestamp if no publication date found
        reference_date = pub_date or extraction_timestamp
        age_days = (now - reference_date).days

        # Freshness scoring
        if age_days <= 7:
            return 1.0
        elif age_days <= 30:
            return 0.9
        elif age_days <= 90:
            return 0.8
        elif age_days <= 365:
            return 0.6
        elif age_days <= 730:  # 2 years
            return 0.4
        else:
            return 0.2

    except Exception:
        # Default to moderate freshness if can't determine
        return 0.5