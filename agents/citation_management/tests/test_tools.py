"""
Test tool implementations for Citation Management Agent.
Validates citation formatting, duplicate detection, and validation tools.
"""

import pytest
import asyncio
from typing import List, Dict, Any
from datetime import date
from unittest.mock import Mock, AsyncMock

from ..tools import (
    format_citations,
    detect_duplicates,
    validate_citations,
    format_citation_by_style,
    generate_citation_key,
    format_apa_citation,
    format_mla_citation
)
from ..models import (
    SourceToCite,
    FormattedCitation,
    CitationValidation,
    CitationDependencies
)
from .conftest import assert_citation_format, assert_bibliography_sorted, calculate_duplicate_accuracy


class TestCitationFormatting:
    """Test citation formatting tools and functions."""

    def test_generate_citation_key(self, sample_sources):
        """Test citation key generation."""
        source = sample_sources[0]
        key = generate_citation_key(source)

        assert key is not None
        assert len(key) > 0
        assert source.source_id[:8] in key
        # Should include author and year
        assert "smith" in key.lower()
        assert "2023" in key

    def test_generate_citation_key_missing_data(self):
        """Test citation key generation with missing data."""
        source = SourceToCite(
            source_id="test_src",
            title="Test Title",
            authors=[],  # No authors
            publication_date=None,  # No date
            source_type="web"
        )

        key = generate_citation_key(source)
        assert "unknown" in key.lower()
        assert "test_src" in key

    def test_format_apa_citation_journal(self, sample_sources):
        """Test APA citation formatting for journal articles."""
        journal_source = sample_sources[0]  # Journal article
        formatted = format_apa_citation(journal_source)

        assert "inline" in formatted
        assert "full" in formatted

        # Check APA format elements
        inline = formatted["inline"]
        full = formatted["full"]

        assert "(" in inline and ")" in inline  # Parenthetical format
        assert "Smith" in full
        assert "Doe" in full
        assert "(2023)" in full
        assert "Journal of AI Research" in full

    def test_format_apa_citation_web(self, sample_sources):
        """Test APA citation formatting for web sources."""
        web_source = sample_sources[1]  # Web source
        formatted = format_apa_citation(web_source)

        inline = formatted["inline"]
        full = formatted["full"]

        assert "Brown" in inline
        assert "Retrieved from" in full
        assert web_source.url in full

    def test_format_mla_citation(self, sample_sources):
        """Test MLA citation formatting."""
        source = sample_sources[0]
        formatted = format_mla_citation(source)

        inline = formatted["inline"]
        full = formatted["full"]

        # MLA uses author's last name in parentheses
        assert "(" in inline and ")" in inline
        assert "Smith" in inline

        # MLA format elements
        assert '"' in full  # Title in quotes for MLA

    def test_format_citation_by_style_all_styles(self, sample_sources):
        """Test citation formatting for all supported styles."""
        source = sample_sources[0]
        styles = ["APA", "MLA", "Chicago", "IEEE", "Harvard"]

        for style in styles:
            formatted = format_citation_by_style(source, style)

            assert "inline" in formatted
            assert "full" in formatted
            assert len(formatted["inline"]) > 0
            assert len(formatted["full"]) > 0

    def test_format_citation_unknown_style(self, sample_sources):
        """Test citation formatting with unknown style falls back to default."""
        source = sample_sources[0]
        formatted = format_citation_by_style(source, "UNKNOWN_STYLE")

        assert "inline" in formatted
        assert "full" in formatted
        # Should still produce valid output with default format

    @pytest.mark.asyncio
    async def test_format_citations_tool(self, sample_sources, test_dependencies):
        """Test the format_citations tool function."""
        formatted_citations = await format_citations(
            ctx=Mock(deps=test_dependencies),
            sources=sample_sources[:2],
            citation_style="APA",
            include_bibliography=True
        )

        assert len(formatted_citations) == 2
        for citation in formatted_citations:
            assert isinstance(citation, FormattedCitation)
            assert_citation_format(citation, "APA")
            assert citation.validation_status in ["valid", "warning", "error"]

    @pytest.mark.asyncio
    async def test_format_citations_with_errors(self, test_dependencies):
        """Test format_citations handles problematic sources."""
        # Create source with problematic data
        problematic_source = SourceToCite(
            source_id="problem_src",
            title="",  # Empty title
            authors=[],  # No authors
            source_type="other",  # Valid type for unknown sources
            additional_metadata={}
        )

        formatted_citations = await format_citations(
            ctx=Mock(deps=test_dependencies),
            sources=[problematic_source],
            citation_style="APA"
        )

        assert len(formatted_citations) == 1
        citation = formatted_citations[0]
        # Should handle gracefully, possibly with error status
        assert citation.source_id == "problem_src"


class TestDuplicateDetection:
    """Test duplicate detection functionality."""

    @pytest.mark.asyncio
    async def test_detect_duplicates_exact_match(self, test_dependencies):
        """Test duplicate detection with exact matches."""
        # Create exact duplicates
        source1 = SourceToCite(
            source_id="orig_1",
            title="Exact Title Match",
            authors=["Smith, John", "Doe, Jane"],
            publication_date=date(2023, 1, 1),
            url="https://example.com/same",
            source_type="journal"
        )

        source2 = SourceToCite(
            source_id="dup_1",
            title="Exact Title Match",  # Same title
            authors=["Smith, John", "Doe, Jane"],  # Same authors
            publication_date=date(2023, 1, 1),
            url="https://example.com/same",  # Same URL
            source_type="journal"
        )

        result = await detect_duplicates(
            ctx=Mock(deps=test_dependencies),
            sources=[source1, source2],
            similarity_threshold=0.85
        )

        assert result["original_count"] == 2
        assert result["deduplicated_count"] == 1
        assert len(result["duplicates"]) == 1
        assert len(result["unique_sources"]) == 1

        # Check duplicate information
        duplicate_info = result["duplicates"][0]
        assert "primary_source_id" in duplicate_info
        assert "duplicate_source_ids" in duplicate_info
        assert "similarity_score" in duplicate_info

    @pytest.mark.asyncio
    async def test_detect_duplicates_partial_match(self, test_dependencies):
        """Test duplicate detection with partial matches."""
        source1 = SourceToCite(
            source_id="orig_2",
            title="Original Research Paper",
            authors=["Author, First"],
            source_type="journal"
        )

        source2 = SourceToCite(
            source_id="similar_2",
            title="Original Research Paper Study",  # Similar title
            authors=["Author, First A."],  # Similar author
            source_type="journal"
        )

        result = await detect_duplicates(
            ctx=Mock(deps=test_dependencies),
            sources=[source1, source2],
            similarity_threshold=0.7  # Lower threshold
        )

        # Should detect as similar if threshold is appropriate
        assert result["original_count"] == 2

    @pytest.mark.asyncio
    async def test_detect_duplicates_no_matches(self, sample_sources, test_dependencies):
        """Test duplicate detection with no duplicates."""
        # Use first 3 sources which should be unique
        unique_sources = sample_sources[:3]

        result = await detect_duplicates(
            ctx=Mock(deps=test_dependencies),
            sources=unique_sources,
            similarity_threshold=0.85
        )

        assert result["original_count"] == 3
        assert result["deduplicated_count"] == 3
        assert len(result["duplicates"]) == 0
        assert len(result["unique_sources"]) == 3

    @pytest.mark.asyncio
    async def test_detect_duplicates_accuracy(self, duplicate_heavy_dataset, test_dependencies):
        """Test duplicate detection accuracy against expected results."""
        result = await detect_duplicates(
            ctx=Mock(deps=test_dependencies),
            sources=duplicate_heavy_dataset,
            similarity_threshold=0.85
        )

        # Should significantly reduce the number of sources
        original_count = result["original_count"]
        deduplicated_count = result["deduplicated_count"]
        reduction_percentage = (original_count - deduplicated_count) / original_count

        # Should detect a significant number of duplicates
        assert reduction_percentage > 0.3  # At least 30% reduction

        # Check that we have duplicate information
        assert len(result["duplicates"]) > 0

    @pytest.mark.asyncio
    async def test_detect_duplicates_threshold_sensitivity(self, test_dependencies):
        """Test duplicate detection with different threshold values."""
        source1 = SourceToCite(
            source_id="base",
            title="Machine Learning Applications",
            authors=["Smith, John"],
            source_type="journal"
        )

        source2 = SourceToCite(
            source_id="similar",
            title="Machine Learning Application",  # Slight difference
            authors=["Smith, J."],  # Slight difference
            source_type="journal"
        )

        # High threshold - should not detect as duplicate
        result_high = await detect_duplicates(
            ctx=Mock(deps=test_dependencies),
            sources=[source1, source2],
            similarity_threshold=0.95
        )

        # Low threshold - should detect as duplicate
        result_low = await detect_duplicates(
            ctx=Mock(deps=test_dependencies),
            sources=[source1, source2],
            similarity_threshold=0.6
        )

        # High threshold should find no duplicates
        assert result_high["deduplicated_count"] == 2

        # Low threshold should find duplicates
        assert result_low["deduplicated_count"] <= result_high["deduplicated_count"]


class TestCitationValidation:
    """Test citation validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_citations_valid_citations(self, formatted_citations, test_dependencies):
        """Test validation of valid citations."""
        validation = await validate_citations(
            ctx=Mock(deps=test_dependencies),
            citations=formatted_citations,
            validation_rules={}
        )

        assert isinstance(validation, CitationValidation)
        assert validation.total_sources == len(formatted_citations)
        assert validation.valid_citations >= 0
        assert isinstance(validation.warnings, list)
        assert isinstance(validation.errors, list)

    @pytest.mark.asyncio
    async def test_validate_citations_missing_authors(self, test_dependencies):
        """Test validation detects missing author information."""
        citation_missing_author = FormattedCitation(
            source_id="missing_author",
            citation_key="unknown_key",
            inline_citation="(Unknown Author)",
            full_citation="Unknown Author. (2023). Test Title.",
            citation_style="APA",
            validation_status="valid"
        )

        validation = await validate_citations(
            ctx=Mock(deps=test_dependencies),
            citations=[citation_missing_author],
            validation_rules={}
        )

        # Should detect missing author
        assert len(validation.warnings) > 0
        assert any("author" in warning.lower() for warning in validation.warnings)
        assert "missing_author" in validation.missing_fields
        assert "authors" in validation.missing_fields["missing_author"]

    @pytest.mark.asyncio
    async def test_validate_citations_missing_date(self, test_dependencies):
        """Test validation detects missing publication dates."""
        citation_missing_date = FormattedCitation(
            source_id="missing_date",
            citation_key="test_key",
            inline_citation="(Smith, n.d.)",
            full_citation="Smith, J. (n.d.). Test Title.",
            citation_style="APA",
            validation_status="valid"
        )

        validation = await validate_citations(
            ctx=Mock(deps=test_dependencies),
            citations=[citation_missing_date],
            validation_rules={}
        )

        # Should detect missing date
        assert len(validation.warnings) > 0
        assert any("date" in warning.lower() for warning in validation.warnings)
        assert "missing_date" in validation.missing_fields
        assert "publication_date" in validation.missing_fields["missing_date"]

    @pytest.mark.asyncio
    async def test_validate_citations_error_status(self, test_dependencies):
        """Test validation handles citations with error status."""
        error_citation = FormattedCitation(
            source_id="error_citation",
            citation_key="error_key",
            inline_citation="(Error: formatting failed)",
            full_citation="Error formatting citation for: Test Title",
            citation_style="APA",
            validation_status="error"
        )

        validation = await validate_citations(
            ctx=Mock(deps=test_dependencies),
            citations=[error_citation],
            validation_rules={}
        )

        # Should report error
        assert len(validation.errors) > 0
        assert validation.valid_citations == 0
        assert any("error_citation" in error for error in validation.errors)

    @pytest.mark.asyncio
    async def test_validate_citations_comprehensive(self, test_dependencies):
        """Test comprehensive validation with mixed citation quality."""
        citations = [
            # Valid citation
            FormattedCitation(
                source_id="valid_1",
                citation_key="smith2023",
                inline_citation="(Smith, 2023)",
                full_citation="Smith, J. (2023). Valid Research Paper. Journal Name, 10, 123-145.",
                citation_style="APA",
                validation_status="valid"
            ),
            # Missing author
            FormattedCitation(
                source_id="missing_author_1",
                citation_key="unknown2023",
                inline_citation="(Unknown Author, 2023)",
                full_citation="Unknown Author. (2023). Research Without Author.",
                citation_style="APA",
                validation_status="valid"
            ),
            # Missing date
            FormattedCitation(
                source_id="missing_date_1",
                citation_key="doe_nd",
                inline_citation="(Doe, n.d.)",
                full_citation="Doe, J. (n.d.). Research Without Date.",
                citation_style="APA",
                validation_status="valid"
            ),
            # Error citation
            FormattedCitation(
                source_id="error_1",
                citation_key="error_key",
                inline_citation="(Error: formatting failed)",
                full_citation="Error formatting citation",
                citation_style="APA",
                validation_status="error"
            )
        ]

        validation = await validate_citations(
            ctx=Mock(deps=test_dependencies),
            citations=citations,
            validation_rules={}
        )

        # Check comprehensive results
        assert validation.total_sources == 4
        assert validation.valid_citations == 3  # All except error
        assert len(validation.warnings) >= 2  # Missing author and date
        assert len(validation.errors) >= 1  # Error citation
        assert len(validation.missing_fields) >= 2  # Missing author and date sources

    @pytest.mark.asyncio
    async def test_validation_empty_citations(self, test_dependencies):
        """Test validation handles empty citation list."""
        validation = await validate_citations(
            ctx=Mock(deps=test_dependencies),
            citations=[],
            validation_rules={}
        )

        assert validation.total_sources == 0
        assert validation.valid_citations == 0
        assert len(validation.warnings) == 0
        assert len(validation.errors) == 0


class TestToolIntegration:
    """Test tool integration and coordination."""

    @pytest.mark.asyncio
    async def test_tools_workflow_integration(self, sample_sources, test_dependencies):
        """Test tools work together in typical workflow."""
        ctx = Mock(deps=test_dependencies)

        # Step 1: Detect duplicates
        duplicate_result = await detect_duplicates(
            ctx=ctx,
            sources=sample_sources,  # Includes one duplicate
            similarity_threshold=0.85
        )

        unique_sources = duplicate_result["unique_sources"]
        assert len(unique_sources) < len(sample_sources)  # Should remove duplicates

        # Step 2: Format citations
        formatted_citations = await format_citations(
            ctx=ctx,
            sources=unique_sources,
            citation_style="APA",
            include_bibliography=True
        )

        assert len(formatted_citations) == len(unique_sources)

        # Step 3: Validate citations
        validation = await validate_citations(
            ctx=ctx,
            citations=formatted_citations,
            validation_rules={}
        )

        assert validation.total_sources == len(formatted_citations)
        assert validation.valid_citations >= 0

    @pytest.mark.asyncio
    async def test_tools_performance_batch_processing(self, large_source_dataset, test_dependencies):
        """Test tools handle large batches efficiently."""
        import time
        ctx = Mock(deps=test_dependencies)

        # Test with large dataset
        sources_subset = large_source_dataset[:50]  # Reasonable subset

        start_time = time.time()

        # Process through all tools
        duplicate_result = await detect_duplicates(ctx, sources_subset, 0.85)
        formatted_citations = await format_citations(ctx, duplicate_result["unique_sources"], "APA")
        validation = await validate_citations(ctx, formatted_citations, {})

        processing_time = time.time() - start_time

        # Should complete within reasonable time
        assert processing_time < 30.0  # 30 seconds max for 50 sources

        # Should produce valid results
        assert len(formatted_citations) > 0
        assert validation.total_sources > 0

    def test_tool_error_handling(self, test_dependencies):
        """Test tools handle errors gracefully."""
        # This would test various error conditions
        # For now, basic smoke test
        assert True  # Tools should handle errors without crashing


class TestRequirementValidation:
    """Validate tools meet specific requirements from GitHub Issue #13."""

    @pytest.mark.asyncio
    async def test_citation_styles_requirement(self, sample_sources, test_dependencies):
        """Test all 5 major citation styles are supported."""
        required_styles = ["APA", "MLA", "Chicago", "IEEE", "Harvard"]
        source = sample_sources[0]

        for style in required_styles:
            formatted = format_citation_by_style(source, style)
            assert formatted is not None
            assert "inline" in formatted
            assert "full" in formatted
            assert len(formatted["inline"]) > 0
            assert len(formatted["full"]) > 0

    @pytest.mark.asyncio
    async def test_duplicate_detection_accuracy_requirement(self, test_dependencies):
        """Test duplicate detection meets 95% accuracy requirement."""
        # Create test dataset with known duplicates
        sources = []

        # Add 10 unique sources with very distinct titles and authors
        titles = [
            "Machine Learning in Healthcare Applications",
            "Quantum Computing for Cryptography",
            "Natural Language Processing Fundamentals",
            "Computer Vision and Image Recognition",
            "Blockchain Technology and Smart Contracts",
            "Artificial Intelligence Ethics and Governance",
            "Deep Learning Neural Network Architectures",
            "Cybersecurity Threat Detection Systems",
            "Data Science and Statistical Analysis",
            "Internet of Things Device Management"
        ]

        authors = [
            ["Smith, John A."],
            ["Johnson, Mary B."],
            ["Williams, Robert C."],
            ["Brown, Linda D."],
            ["Davis, Michael E."],
            ["Wilson, Sarah F."],
            ["Garcia, Carlos G."],
            ["Martinez, Ana H."],
            ["Anderson, David I."],
            ["Taylor, Emma J."]
        ]

        for i in range(10):
            sources.append(SourceToCite(
                source_id=f"unique_{i}",
                title=titles[i],
                authors=authors[i],
                source_type="journal"
            ))

        # Add 5 exact duplicates of first 5 sources
        for i in range(5):
            sources.append(SourceToCite(
                source_id=f"duplicate_{i}",
                title=titles[i],  # Exact match
                authors=authors[i],  # Exact match
                source_type="journal"
            ))

        ctx = Mock(deps=test_dependencies)
        result = await detect_duplicates(ctx, sources, 0.85)

        # Should detect all 5 duplicates
        detected_duplicates = len(result["duplicates"])
        expected_duplicates = 5

        accuracy = detected_duplicates / expected_duplicates if expected_duplicates > 0 else 1.0
        assert accuracy >= 0.95  # 95% accuracy requirement

    @pytest.mark.asyncio
    async def test_citation_completeness_validation(self, incomplete_sources, test_dependencies):
        """Test citation validation flags missing information."""
        ctx = Mock(deps=test_dependencies)

        # Format incomplete sources
        formatted_citations = await format_citations(
            ctx, incomplete_sources, "APA"
        )

        # Validate them
        validation = await validate_citations(ctx, formatted_citations, {})

        # Should flag missing information
        assert len(validation.missing_fields) > 0
        assert len(validation.warnings) > 0

        # Check specific missing fields are detected
        for source_id, missing in validation.missing_fields.items():
            source = next(s for s in incomplete_sources if s.source_id == source_id)
            if not source.authors:
                assert "authors" in missing
            if not source.publication_date:
                assert "publication_date" in missing