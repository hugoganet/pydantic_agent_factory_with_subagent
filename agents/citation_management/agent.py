"""
Citation Management Agent - Main Pydantic AI agent implementation.
Handles academic citation formatting, duplicate detection, and validation.
"""

import logging
from typing import List, Dict, Any
from pydantic_ai import Agent, RunContext

from .models import (
    CitationRequest,
    CitationResponse,
    CitationDependencies,
    FormattedCitation,
    CitationValidation
)
from .providers import get_llm_model
from .tools import format_citations, detect_duplicates, validate_citations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# System prompt from planning
SYSTEM_PROMPT = """
You are an expert Citation Management Agent specializing in academic source attribution and reference formatting. Your primary purpose is to generate precise, academically compliant citations across multiple style formats and manage comprehensive bibliography creation within research workflows.

Core Competencies:
1. Multi-style citation formatting (APA, MLA, Chicago, IEEE, Harvard)
2. Bibliography generation with alphabetical sorting and duplicate detection
3. Citation validation and completeness verification
4. Source metadata normalization and quality assurance
5. Academic style consistency enforcement

Your Approach:
- Prioritize academic precision and accuracy in all citation formats
- Follow official style guide requirements strictly for each format
- Provide clear validation feedback for incomplete or problematic sources
- Maintain consistent formatting within each citation style
- Process citations efficiently while preserving quality standards
- Handle missing metadata gracefully with appropriate fallbacks

Available Tools:
- format_citations: Generate individual citations in specified academic styles
- detect_duplicates: Identify and merge duplicate sources using fuzzy matching
- validate_citations: Verify completeness against style-specific requirements

Output Guidelines:
- Generate structured CitationResponse objects with all required fields
- Provide inline citations and full reference entries for each source
- Create properly formatted bibliographies sorted alphabetically
- Include validation results with clear error/warning messages
- Map source IDs to citation keys for workflow integration

Quality Standards:
- Achieve 95% accuracy in duplicate detection based on title/author/URL matching
- Process 100+ citations within 1-minute execution time
- Flag all missing required fields with specific guidance
- Maintain style consistency across all generated citations
- Provide actionable feedback for incomplete source metadata

You approach each citation task with academic rigor, ensuring that all formatted citations meet professional research standards while maintaining efficient processing for high-volume requests.
"""

# Create the agent
try:
    agent = Agent(
        get_llm_model(),
        deps_type=CitationDependencies,
        system_prompt=SYSTEM_PROMPT
    )
except Exception as e:
    # For testing environments where API key might not be valid
    from pydantic_ai.models.test import TestModel
    agent = Agent(
        TestModel(),
        deps_type=CitationDependencies,
        system_prompt=SYSTEM_PROMPT
    )


@agent.tool
async def format_citations_tool(
    ctx: RunContext[CitationDependencies],
    sources: List[Dict[str, Any]],
    citation_style: str,
    include_bibliography: bool = True
) -> List[Dict[str, Any]]:
    """
    Format source metadata into academic citations following specified style guidelines.

    Args:
        sources: List of source metadata dictionaries
        citation_style: Target academic citation style (APA, MLA, Chicago, IEEE, Harvard)
        include_bibliography: Whether to generate full bibliographic references

    Returns:
        List of formatted citation dictionaries
    """
    from .models import SourceToCite

    # Convert dict sources to SourceToCite objects
    source_objects = []
    for source_dict in sources:
        try:
            source = SourceToCite(**source_dict)
            source_objects.append(source)
        except Exception as e:
            logger.warning(f"Failed to parse source: {e}")
            continue

    formatted = await format_citations(ctx, source_objects, citation_style, include_bibliography)

    # Convert back to dictionaries for LLM processing
    return [citation.model_dump() for citation in formatted]


@agent.tool
async def detect_duplicates_tool(
    ctx: RunContext[CitationDependencies],
    sources: List[Dict[str, Any]],
    similarity_threshold: float = 0.85
) -> Dict[str, Any]:
    """
    Identify duplicate sources and provide merge recommendations.

    Args:
        sources: List of source metadata dictionaries
        similarity_threshold: Confidence threshold for duplicate matching (0.0-1.0)

    Returns:
        Dictionary containing deduplicated sources and merge mapping
    """
    from .models import SourceToCite

    # Convert dict sources to SourceToCite objects
    source_objects = []
    for source_dict in sources:
        try:
            source = SourceToCite(**source_dict)
            source_objects.append(source)
        except Exception as e:
            logger.warning(f"Failed to parse source for duplicate detection: {e}")
            continue

    result = await detect_duplicates(ctx, source_objects, similarity_threshold)

    # Convert SourceToCite objects back to dicts
    result["unique_sources"] = [source.model_dump() for source in result["unique_sources"]]

    return result


@agent.tool
async def validate_citations_tool(
    ctx: RunContext[CitationDependencies],
    citations: List[Dict[str, Any]],
    validation_rules: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Validate citation completeness and accuracy against style requirements.

    Args:
        citations: List of formatted citation dictionaries
        validation_rules: Style-specific validation requirements

    Returns:
        Validation results with warnings, errors, and missing fields
    """
    from .models import FormattedCitation

    # Convert dict citations to FormattedCitation objects
    citation_objects = []
    for citation_dict in citations:
        try:
            citation = FormattedCitation(**citation_dict)
            citation_objects.append(citation)
        except Exception as e:
            logger.warning(f"Failed to parse citation for validation: {e}")
            continue

    if validation_rules is None:
        validation_rules = {}

    validation = await validate_citations(ctx, citation_objects, validation_rules)
    return validation.model_dump()


async def process_citation_request(
    request: CitationRequest,
    dependencies: CitationDependencies = None
) -> CitationResponse:
    """
    Process a complete citation request through the agent.

    Args:
        request: CitationRequest with sources and formatting requirements
        dependencies: Optional CitationDependencies for configuration

    Returns:
        CitationResponse with formatted citations and validation results
    """
    if dependencies is None:
        dependencies = CitationDependencies()

    try:
        # Run the agent with the citation request
        result = await agent.run(
            f"""Process this citation request:

Request ID: {request.request_id}
Citation Style: {request.citation_style}
Include Bibliography: {request.include_bibliography}
Sort Alphabetically: {request.sort_alphabetically}
Number of Sources: {len(request.sources)}

Please:
1. Use detect_duplicates_tool to identify and merge duplicate sources
2. Use format_citations_tool to format all unique sources in {request.citation_style} style
3. Use validate_citations_tool to check citation completeness
4. Generate a complete CitationResponse with bibliography and citation mapping

Sources to process:
{[source.model_dump() for source in request.sources]}
""",
            deps=dependencies
        )

        return result.data

    except Exception as e:
        logger.error(f"Failed to process citation request {request.request_id}: {e}")

        # Return error response
        return CitationResponse(
            request_id=request.request_id,
            citations=[],
            bibliography=[],
            citation_map={},
            style_used=request.citation_style,
            validation_results=CitationValidation(
                total_sources=len(request.sources),
                valid_citations=0,
                warnings=[],
                errors=[f"Agent processing failed: {str(e)}"],
                missing_fields={},
                duplicate_sources=[]
            )
        )


# Main execution function for workflow integration
async def run_citation_agent(
    sources: List[Dict[str, Any]],
    citation_style: str = "APA",
    request_id: str = "citation_request",
    include_bibliography: bool = True,
    sort_alphabetically: bool = True
) -> CitationResponse:
    """
    Main entry point for citation processing.

    Args:
        sources: List of source metadata dictionaries
        citation_style: Academic citation style (APA, MLA, Chicago, IEEE, Harvard)
        request_id: Unique identifier for the request
        include_bibliography: Whether to generate bibliography
        sort_alphabetically: Whether to sort bibliography alphabetically

    Returns:
        CitationResponse with formatted citations and validation
    """
    from .models import SourceToCite

    # Convert sources to SourceToCite objects
    source_objects = []
    for source_dict in sources:
        try:
            source = SourceToCite(**source_dict)
            source_objects.append(source)
        except Exception as e:
            logger.warning(f"Failed to parse source: {e}")
            continue

    # Create citation request
    request = CitationRequest(
        request_id=request_id,
        sources=source_objects,
        citation_style=citation_style,
        include_bibliography=include_bibliography,
        sort_alphabetically=sort_alphabetically
    )

    # Process the request
    dependencies = CitationDependencies()
    return await process_citation_request(request, dependencies)


if __name__ == "__main__":
    # Example usage
    import asyncio

    sample_sources = [
        {
            "source_id": "src_1",
            "title": "The Impact of AI on Research",
            "authors": ["Smith, John", "Doe, Jane"],
            "publication_date": "2023-01-15",
            "url": "https://example.com/ai-research",
            "source_type": "web",
            "additional_metadata": {}
        },
        {
            "source_id": "src_2",
            "title": "Machine Learning Fundamentals",
            "authors": ["Brown, Alice"],
            "publication_date": "2022-12-01",
            "source_type": "journal",
            "additional_metadata": {
                "journal_name": "Journal of AI",
                "volume": "10",
                "pages": "123-145"
            }
        }
    ]

    async def main():
        result = await run_citation_agent(
            sources=sample_sources,
            citation_style="APA",
            request_id="test_request"
        )
        print(f"Processed {len(result.citations)} citations")
        print(f"Validation: {result.validation_results.valid_citations} valid citations")

    asyncio.run(main())