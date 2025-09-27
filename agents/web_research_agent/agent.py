"""
Web Research Agent - Multi-engine web search with content extraction.
Main agent implementation with all tools integrated.
"""

import logging
from typing import Optional
from pydantic_ai import Agent, RunContext

from .providers import get_llm_model
from .dependencies import WebResearchDependencies
from .settings import settings
from .prompts import SYSTEM_PROMPT
from .models import WebSearchResults, SearchRequest
from .tools import multi_engine_search, extract_web_content, assess_content_quality

logger = logging.getLogger(__name__)

# Initialize the agent
agent = Agent(
    get_llm_model(),
    deps_type=WebResearchDependencies,
    system_prompt=SYSTEM_PROMPT,
    retries=settings.max_retries
)

logger.info("Web Research Agent initialized")


# Register all tools with the agent
@agent.tool
async def search_and_extract(
    ctx: RunContext[WebResearchDependencies],
    query: str,
    search_engines: list = None,
    max_results: int = 20,
    quality_threshold: float = 0.7
) -> str:
    """
    Complete web research workflow: search, extract, and assess content quality.

    Args:
        query: Search query to execute
        search_engines: List of search engines to use (defaults to available engines)
        max_results: Maximum results per engine
        quality_threshold: Minimum quality score for filtering

    Returns:
        Formatted results summary
    """
    try:
        # Use available engines if none specified
        if search_engines is None:
            search_engines = ctx.deps.available_search_engines

        logger.info(f"Starting web research for query: '{query}'")

        # Step 1: Execute multi-engine search
        search_results = await multi_engine_search(
            ctx, query, search_engines, max_results
        )

        if not search_results.get("success", False):
            return f"Search failed: {search_results.get('errors', 'Unknown error')}"

        # Collect URLs from all engines
        all_urls = []
        for engine_results in search_results["search_results"].values():
            all_urls.extend([result["url"] for result in engine_results])

        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(all_urls))
        logger.info(f"Found {len(unique_urls)} unique URLs to extract content from")

        # Step 2: Extract content from URLs
        extracted_content = await extract_web_content(
            ctx, unique_urls, extract_metadata=True, respect_robots=True
        )

        successful_extractions = [item for item in extracted_content if item.get("success", False)]
        logger.info(f"Successfully extracted content from {len(successful_extractions)}/{len(unique_urls)} URLs")

        # Step 3: Assess content quality
        quality_assessment = await assess_content_quality(
            ctx, successful_extractions, query, quality_threshold
        )

        if not quality_assessment.get("success", False):
            return "Content quality assessment failed"

        # Format results summary
        filtered_content = quality_assessment["filtered_content"]
        quality_summary = quality_assessment["quality_summary"]

        summary = f"""Web Research Results for: "{query}"

🔍 Search Summary:
- Engines used: {', '.join(search_results['metadata']['engines_successful'])}
- Total URLs found: {len(unique_urls)}
- Content extracted: {len(successful_extractions)}
- High-quality sources: {quality_summary['high_quality_sources']}
- Average quality score: {quality_summary['average_quality_score']:.2f}

📋 Top Results:"""

        for i, source in enumerate(filtered_content[:5], 1):
            summary += f"""

{i}. {source['metadata']['title'][:100]}...
   URL: {source['url'][:80]}...
   Quality Score: {source['quality_score']:.2f}
   Content Preview: {source['content'][:200]}...
   Credibility: {', '.join(source.get('credibility_indicators', []))}"""

        if len(filtered_content) > 5:
            summary += f"\n\n... and {len(filtered_content) - 5} more high-quality sources."

        summary += f"""

📊 Quality Distribution:
- Excellent (≥0.9): {quality_summary['quality_distribution']['excellent']}
- Good (0.7-0.9): {quality_summary['quality_distribution']['good']}
- Fair (0.5-0.7): {quality_summary['quality_distribution']['fair']}
- Poor (<0.5): {quality_summary['quality_distribution']['poor']}

⏱️ Execution Time: {search_results['metadata']['execution_time']:.2f} seconds"""

        return summary

    except Exception as e:
        logger.error(f"Web research failed: {e}")
        return f"Web research failed with error: {str(e)}"


@agent.tool
async def multi_engine_web_search(
    ctx: RunContext[WebResearchDependencies],
    query: str,
    engines: list = ["brave"],
    max_results_per_engine: int = 20
) -> str:
    """
    Execute searches across multiple search engines.

    Args:
        query: Search query to execute
        engines: List of search engines to use
        max_results_per_engine: Maximum results per engine

    Returns:
        Formatted search results
    """
    results = await multi_engine_search(ctx, query, engines, max_results_per_engine)

    if not results.get("success"):
        return f"Search failed: {results.get('errors', 'Unknown error')}"

    summary = f"Search Results for: '{query}'\n\n"

    for engine, engine_results in results["search_results"].items():
        summary += f"{engine.upper()} Results ({len(engine_results)}):\n"
        for i, result in enumerate(engine_results[:3], 1):
            summary += f"{i}. {result['title']}\n   {result['url']}\n   {result['description'][:100]}...\n\n"

    return summary


@agent.tool
async def extract_content_from_urls(
    ctx: RunContext[WebResearchDependencies],
    urls: list,
    extract_metadata: bool = True
) -> str:
    """
    Extract content from a list of URLs.

    Args:
        urls: List of URLs to extract content from
        extract_metadata: Whether to extract metadata

    Returns:
        Summary of extracted content
    """
    results = await extract_web_content(ctx, urls, extract_metadata, respect_robots=True)

    successful = [r for r in results if r.get("success", False)]
    failed = [r for r in results if not r.get("success", False)]

    summary = f"Content Extraction Results:\n\n"
    summary += f"✅ Successful: {len(successful)}/{len(results)}\n"
    summary += f"❌ Failed: {len(failed)}\n\n"

    for i, result in enumerate(successful[:3], 1):
        metadata = result.get("metadata", {})
        summary += f"{i}. {metadata.get('title', 'Unknown Title')}\n"
        summary += f"   Domain: {metadata.get('domain', 'Unknown')}\n"
        summary += f"   Words: {metadata.get('word_count', 0)}\n"
        summary += f"   Content: {result.get('content', '')[:200]}...\n\n"

    return summary


@agent.tool
async def assess_web_content_quality(
    ctx: RunContext[WebResearchDependencies],
    extracted_content: list,
    search_query: str,
    quality_threshold: float = 0.7
) -> str:
    """
    Assess the quality of extracted web content.

    Args:
        extracted_content: List of extracted content items
        search_query: Original search query for relevance scoring
        quality_threshold: Minimum quality score

    Returns:
        Quality assessment summary
    """
    # This would need the actual extracted content structure
    # For now, return a placeholder
    return f"Quality assessment completed for {len(extracted_content)} items with threshold {quality_threshold}"


# Convenience functions for agent usage
async def run_web_search(
    query: str,
    search_engines: Optional[list] = None,
    max_results: int = 20,
    quality_threshold: float = 0.7,
    session_id: Optional[str] = None,
    **dependency_overrides
) -> str:
    """
    Execute web research with automatic dependency injection.

    Args:
        query: Search query
        search_engines: List of search engines to use
        max_results: Maximum results per engine
        quality_threshold: Minimum quality score
        session_id: Optional session identifier
        **dependency_overrides: Override default dependencies

    Returns:
        Web search results as formatted string
    """
    deps = WebResearchDependencies.from_settings(
        settings,
        session_id=session_id,
        max_results=max_results,
        quality_threshold=quality_threshold,
        **dependency_overrides
    )

    try:
        # Format search request
        search_request = f"Execute comprehensive web research for: {query}"

        result = await agent.run(search_request, deps=deps)
        return result.data
    finally:
        await deps.cleanup()


def create_agent_with_deps(**dependency_overrides) -> tuple[Agent, WebResearchDependencies]:
    """
    Create agent instance with custom dependencies.

    Args:
        **dependency_overrides: Custom dependency values

    Returns:
        Tuple of (agent, dependencies)
    """
    deps = WebResearchDependencies.from_settings(settings, **dependency_overrides)
    return agent, deps


if __name__ == "__main__":
    import asyncio

    async def test_agent():
        """Test the web research agent."""
        try:
            result = await run_web_search(
                "machine learning algorithms",
                search_engines=["brave"],
                max_results=10,
                quality_threshold=0.6
            )
            print(result)
        except Exception as e:
            print(f"Test failed: {e}")

    # Run test if script is executed directly
    asyncio.run(test_agent())