"""
Citation Management Agent tools for formatting, duplicate detection, and validation.
"""

import asyncio
import logging
from typing import List, Dict, Any
from fuzzywuzzy import fuzz
from dateutil.parser import parse as parse_date
from pydantic_ai import RunContext

from .models import (
    SourceToCite,
    FormattedCitation,
    CitationValidation,
    CitationDependencies
)

logger = logging.getLogger(__name__)


def generate_citation_key(source: SourceToCite) -> str:
    """Generate unique citation key for source."""
    if source.authors:
        # Handle "Last, First" format
        first_author = source.authors[0]
        if "," in first_author:
            author_key = first_author.split(",")[0].strip().lower()
        else:
            # Handle "First Last" format
            author_key = first_author.split()[-1].lower()
    else:
        author_key = "unknown"

    year = ""
    if source.publication_date:
        year = str(source.publication_date.year)
    elif source.additional_metadata.get("year"):
        year = str(source.additional_metadata["year"])

    return f"{author_key}{year}_{source.source_id[:8]}"


def format_apa_citation(source: SourceToCite) -> Dict[str, str]:
    """Format citation in APA style."""
    authors = ", ".join(source.authors) if source.authors else "Unknown Author"
    year = f"({source.publication_date.year})" if source.publication_date else "(n.d.)"
    title = source.title

    if source.source_type == "web":
        full_citation = f"{authors} {year}. {title}. Retrieved from {source.url or 'URL not available'}"
        inline_citation = f"({authors.split(',')[0].strip()}, {year.strip('()')})"
    elif source.source_type == "journal":
        journal = source.additional_metadata.get("journal_name", "Unknown Journal")
        volume = source.additional_metadata.get("volume", "")
        pages = source.additional_metadata.get("pages", "")
        full_citation = f"{authors} {year}. {title}. {journal}, {volume}, {pages}."
        inline_citation = f"({authors.split(',')[0].strip()}, {year.strip('()')})"
    else:
        full_citation = f"{authors} {year}. {title}."
        inline_citation = f"({authors.split(',')[0].strip()}, {year.strip('()')})"

    return {"inline": inline_citation, "full": full_citation}


def format_mla_citation(source: SourceToCite) -> Dict[str, str]:
    """Format citation in MLA style."""
    authors = source.authors[0] if source.authors else "Unknown Author"
    title = f'"{source.title}"'

    # Extract last name properly
    if authors != "Unknown Author":
        if "," in authors:
            last_name = authors.split(",")[0].strip()
        else:
            last_name = authors.split()[-1]
    else:
        last_name = "Unknown"

    if source.source_type == "web":
        url = source.url or "Web"
        date = source.publication_date.strftime("%d %b %Y") if source.publication_date else "n.d."
        full_citation = f"{authors}. {title} {url}, {date}."
        inline_citation = f"({last_name})"
    else:
        pub_info = source.additional_metadata.get("publisher", "Publisher Unknown")
        year = source.publication_date.year if source.publication_date else "n.d."
        full_citation = f"{authors}. {title} {pub_info}, {year}."
        inline_citation = f"({last_name})"

    return {"inline": inline_citation, "full": full_citation}


def format_citation_by_style(source: SourceToCite, style: str) -> Dict[str, str]:
    """Format citation according to specified style."""
    style = style.upper()

    if style == "APA":
        return format_apa_citation(source)
    elif style == "MLA":
        return format_mla_citation(source)
    elif style == "CHICAGO":
        # Simplified Chicago style
        authors = ", ".join(source.authors) if source.authors else "Unknown Author"
        title = source.title
        year = source.publication_date.year if source.publication_date else "n.d."
        full_citation = f"{authors}. \"{title}.\" {year}."
        inline_citation = f"({authors.split(',')[0].strip()}, {year})"
        return {"inline": inline_citation, "full": full_citation}
    elif style == "IEEE":
        # Simplified IEEE style
        authors = ", ".join(source.authors) if source.authors else "Unknown Author"
        title = f'"{source.title}"'
        year = source.publication_date.year if source.publication_date else "n.d."
        full_citation = f"{authors}, {title} {year}."
        inline_citation = f"[{source.source_id[:2]}]"
        return {"inline": inline_citation, "full": full_citation}
    elif style == "HARVARD":
        # Simplified Harvard style
        authors = source.authors[0] if source.authors else "Unknown Author"
        year = source.publication_date.year if source.publication_date else "n.d."
        title = source.title
        full_citation = f"{authors} {year}, '{title}'."
        inline_citation = f"({authors.split()[-1]} {year})"
        return {"inline": inline_citation, "full": full_citation}
    else:
        # Default format
        authors = ", ".join(source.authors) if source.authors else "Unknown Author"
        title = source.title
        full_citation = f"{authors}. {title}."
        inline_citation = f"({authors.split(',')[0].strip()})"
        return {"inline": inline_citation, "full": full_citation}


async def format_citations(
    ctx: RunContext[CitationDependencies],
    sources: List[SourceToCite],
    citation_style: str,
    include_bibliography: bool = True
) -> List[FormattedCitation]:
    """
    Format source metadata into academic citations following specified style guidelines.
    """
    formatted_citations = []

    for source in sources:
        try:
            citation_key = generate_citation_key(source)
            formatted = format_citation_by_style(source, citation_style)

            citation = FormattedCitation(
                source_id=source.source_id,
                citation_key=citation_key,
                inline_citation=formatted["inline"],
                full_citation=formatted["full"],
                citation_style=citation_style.upper(),
                validation_status="valid"
            )
            formatted_citations.append(citation)

        except Exception as e:
            logger.warning(f"Failed to format citation for source {source.source_id}: {e}")
            # Create partial citation
            citation = FormattedCitation(
                source_id=source.source_id,
                citation_key=f"error_{source.source_id[:8]}",
                inline_citation=f"(Error: {source.title[:30]}...)",
                full_citation=f"Error formatting citation for: {source.title}",
                citation_style=citation_style.upper(),
                validation_status="error"
            )
            formatted_citations.append(citation)

    return formatted_citations


async def detect_duplicates(
    ctx: RunContext[CitationDependencies],
    sources: List[SourceToCite],
    similarity_threshold: float = 0.85
) -> Dict[str, Any]:
    """
    Identify duplicate sources and provide merge recommendations.
    """
    duplicates = []
    unique_sources = []
    processed_indices = set()

    for i, source1 in enumerate(sources):
        if i in processed_indices:
            continue

        current_group = [source1]

        for j, source2 in enumerate(sources[i+1:], i+1):
            if j in processed_indices:
                continue

            # Calculate similarity
            title_sim = fuzz.ratio(source1.title.lower(), source2.title.lower()) / 100.0

            # Author similarity
            author_sim = 0.0
            if source1.authors and source2.authors:
                author1_str = " ".join(source1.authors).lower()
                author2_str = " ".join(source2.authors).lower()
                author_sim = fuzz.ratio(author1_str, author2_str) / 100.0

            # URL similarity
            url_sim = 0.0
            if source1.url and source2.url:
                url_sim = fuzz.ratio(source1.url, source2.url) / 100.0

            # Weighted similarity - adjust weights if URL is missing
            if source1.url and source2.url:
                # All three factors available
                total_sim = (title_sim * 0.4 + author_sim * 0.3 + url_sim * 0.3)
            else:
                # No URL comparison - weight title and author more heavily
                total_sim = (title_sim * 0.6 + author_sim * 0.4)

            if total_sim >= similarity_threshold:
                current_group.append(source2)
                processed_indices.add(j)

        if len(current_group) > 1:
            # Found duplicates - keep the most complete source
            best_source = max(current_group, key=lambda s: len(s.authors) + bool(s.publication_date) + bool(s.url))
            unique_sources.append(best_source)

            duplicate_info = {
                "primary_source_id": best_source.source_id,
                "duplicate_source_ids": [s.source_id for s in current_group if s.source_id != best_source.source_id],
                "similarity_score": total_sim
            }
            duplicates.append(duplicate_info)
        else:
            unique_sources.append(source1)

        processed_indices.add(i)

    return {
        "unique_sources": unique_sources,
        "duplicates": duplicates,
        "original_count": len(sources),
        "deduplicated_count": len(unique_sources)
    }


async def validate_citations(
    ctx: RunContext[CitationDependencies],
    citations: List[FormattedCitation],
    validation_rules: Dict[str, Any]
) -> CitationValidation:
    """
    Validate citation completeness and accuracy against style requirements.
    """
    warnings = []
    errors = []
    missing_fields = {}
    valid_count = 0

    # Get required fields for the citation style
    style = citations[0].citation_style if citations else "APA"
    required_fields = ctx.deps.get_required_fields(style)

    for citation in citations:
        citation_warnings = []
        citation_errors = []
        missing = []

        if citation.validation_status == "error":
            errors.append(f"Citation formatting failed for {citation.source_id}")
            continue

        # Check for basic formatting issues
        if not citation.inline_citation or citation.inline_citation.startswith("(Error"):
            citation_errors.append("Invalid inline citation format")

        if not citation.full_citation or "Error formatting" in citation.full_citation:
            citation_errors.append("Invalid full citation format")

        # Check for missing required fields (would need source data for complete validation)
        if citation.inline_citation == "(Unknown Author)" or "Unknown Author" in citation.full_citation:
            missing.append("authors")
            citation_warnings.append("Missing author information")

        if "(n.d.)" in citation.full_citation or "n.d." in citation.full_citation:
            missing.append("publication_date")
            citation_warnings.append("Missing publication date")

        if missing:
            missing_fields[citation.source_id] = missing

        if citation_errors:
            errors.extend([f"{citation.source_id}: {error}" for error in citation_errors])
        else:
            valid_count += 1

        if citation_warnings:
            warnings.extend([f"{citation.source_id}: {warning}" for warning in citation_warnings])

    return CitationValidation(
        total_sources=len(citations),
        valid_citations=valid_count,
        warnings=warnings,
        errors=errors,
        missing_fields=missing_fields,
        duplicate_sources=[]  # Populated by detect_duplicates
    )