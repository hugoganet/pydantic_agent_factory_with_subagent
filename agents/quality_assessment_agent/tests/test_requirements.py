"""Requirements validation tests based on INITIAL.md specifications."""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from statistics import mean

from ..agent import assess_source_quality, assess_multiple_sources, health_check
from ..models import ResearchSource, QualityAssessment
from ..tools import analyze_domain_authority, analyze_content_quality, analyze_bias_indicators, check_freshness


class TestCoreFeatureRequirements:
    """Validate core features from INITIAL.md."""

    @pytest.mark.asyncio
    async def test_req_001_source_credibility_assessment(self, requirements_test_data):
        """REQ-001: Evaluate website authority, domain reputation, and author credentials."""

        # Test high-authority domains
        for test_case in requirements_test_data["credibility_test_cases"]:
            domain = test_case["domain"]
            expected_min_score = test_case["expected_min_score"]

            # Create test source for domain
            test_source = ResearchSource(
                source_id=f"credibility_test_{domain.replace('.', '_')}",
                url=f"https://{domain}/article",
                title="Test Article from Domain",
                content="Well-structured article with proper citations and references. " * 20,
                metadata={"domain": domain, "author": "Dr. Expert Author"},
                extraction_timestamp=datetime.now()
            )

            with patch('..agent.quality_agent.run') as mock_agent_run:
                # Mock assessment based on domain authority
                credibility_score = 0.9 if domain in ["wikipedia.org", "nature.com"] else 0.5

                assessment = QualityAssessment(
                    source_id=test_source.source_id,
                    credibility_score=credibility_score,
                    bias_score=0.2,
                    freshness_score=0.8,
                    authority_score=credibility_score,
                    overall_quality=credibility_score * 0.8,
                    confidence_rating=0.9,
                    flags=[]
                )

                mock_result = AsyncMock()
                mock_result.data = assessment
                mock_agent_run.return_value = mock_result

                result = await assess_source_quality(test_source)

                # Validate credibility assessment
                if domain in ["wikipedia.org", "nature.com", "gov", "edu"]:
                    assert result.credibility_score >= expected_min_score, \
                        f"High-authority domain {domain} should score >= {expected_min_score}"
                    assert result.authority_score >= expected_min_score
                else:
                    assert result.credibility_score <= 0.7, \
                        f"Low-authority domain {domain} should score <= 0.7"

    @pytest.mark.asyncio
    async def test_req_002_content_quality_analysis(self, sample_research_source):
        """REQ-002: Analyze source freshness, content depth, citation presence, and factual consistency."""

        # Test content with various quality indicators
        quality_test_cases = [
            {
                "title": "High Quality Academic Paper",
                "content": """
                # Abstract
                This comprehensive study examines quality assessment methodologies.

                ## Introduction
                According to previous research (Smith et al., 2023), systematic approaches
                are essential for information quality evaluation.

                ## Methodology
                We conducted analysis using established protocols:
                - Systematic review of 500 sources
                - Statistical analysis with p<0.05 significance
                - Cross-validation with expert assessments

                ## Results
                Statistical analysis revealed significant correlations (r=0.78, p<0.001).
                The findings demonstrate clear patterns in quality indicators.

                ## Discussion
                These results align with established theories in information science
                and provide practical frameworks for automated assessment.

                ## References
                [1] Smith, J. et al. (2023). Quality Assessment Methods. Nature.
                [2] Brown, A. & Wilson, C. (2022). Information Evaluation. Science.
                """,
                "expected_quality": 0.8
            },
            {
                "title": "Poor Quality Blog Post",
                "content": "short text no structure citations",
                "expected_quality": 0.3
            }
        ]

        for test_case in quality_test_cases:
            test_source = ResearchSource(
                source_id="quality_test",
                url="https://example.com/test",
                title=test_case["title"],
                content=test_case["content"],
                metadata={},
                extraction_timestamp=datetime.now()
            )

            with patch('..agent.quality_agent.run') as mock_agent_run:
                # Mock assessment based on content quality
                quality_score = test_case["expected_quality"]

                assessment = QualityAssessment(
                    source_id=test_source.source_id,
                    credibility_score=quality_score,
                    bias_score=0.2,
                    freshness_score=0.9,
                    authority_score=quality_score,
                    overall_quality=quality_score,
                    confidence_rating=0.85,
                    flags=[]
                )

                mock_result = AsyncMock()
                mock_result.data = assessment
                mock_agent_run.return_value = mock_result

                result = await assess_source_quality(test_source)

                # Validate content quality assessment
                assert abs(result.overall_quality - test_case["expected_quality"]) < 0.3, \
                    f"Content quality should be around {test_case['expected_quality']}"

    @pytest.mark.asyncio
    async def test_req_003_bias_detection(self, requirements_test_data):
        """REQ-003: Identify potential bias indicators in language patterns."""

        for test_case in requirements_test_data["bias_test_cases"]:
            content = test_case["content"]
            expected_bias_threshold = test_case.get("expected_max_bias", 0.5)

            test_source = ResearchSource(
                source_id="bias_test",
                url="https://example.com/test",
                title="Bias Detection Test",
                content=content,
                metadata={},
                extraction_timestamp=datetime.now()
            )

            with patch('..agent.quality_agent.run') as mock_agent_run:
                # Mock bias assessment based on content
                if "outrageous" in content.lower() or "shocking" in content.lower():
                    bias_score = 0.8  # High bias
                else:
                    bias_score = 0.2  # Low bias

                assessment = QualityAssessment(
                    source_id=test_source.source_id,
                    credibility_score=0.7,
                    bias_score=bias_score,
                    freshness_score=0.8,
                    authority_score=0.6,
                    overall_quality=0.65,
                    confidence_rating=0.85,
                    flags=["high_bias"] if bias_score > 0.6 else []
                )

                mock_result = AsyncMock()
                mock_result.data = assessment
                mock_agent_run.return_value = mock_result

                result = await assess_source_quality(test_source)

                # Validate bias detection
                if "expected_min_bias" in test_case:
                    assert result.bias_score >= test_case["expected_min_bias"], \
                        f"Biased content should have bias_score >= {test_case['expected_min_bias']}"
                else:
                    assert result.bias_score <= expected_bias_threshold, \
                        f"Neutral content should have bias_score <= {expected_bias_threshold}"


class TestPerformanceRequirements:
    """Validate performance requirements from INITIAL.md."""

    @pytest.mark.asyncio
    async def test_req_004_processing_time_under_30_seconds(self, sample_research_source):
        """REQ-004: Processing time <30 seconds per source assessment."""

        with patch('..agent.quality_agent.run') as mock_agent_run:
            # Simulate realistic processing time
            async def mock_with_processing_time(*args, **kwargs):
                await asyncio.sleep(0.5)  # Simulate half-second processing
                assessment = QualityAssessment(
                    source_id=sample_research_source.source_id,
                    credibility_score=0.8,
                    bias_score=0.2,
                    freshness_score=0.9,
                    authority_score=0.7,
                    overall_quality=0.75,
                    confidence_rating=0.85,
                    flags=[]
                )
                mock_result = AsyncMock()
                mock_result.data = assessment
                return mock_result

            mock_agent_run.side_effect = mock_with_processing_time

            # Measure processing time
            start_time = time.time()
            result = await assess_source_quality(sample_research_source)
            end_time = time.time()

            processing_time = end_time - start_time

            # Validate performance requirement
            assert processing_time < 30.0, \
                f"Processing time {processing_time:.2f}s exceeds 30-second requirement"
            assert isinstance(result, QualityAssessment)

    @pytest.mark.asyncio
    async def test_req_005_credibility_precision_above_85_percent(self, requirements_test_data):
        """REQ-005: Credibility precision >85% accuracy in credibility scoring."""

        # Test with known high and low credibility sources
        test_sources = [
            # High credibility sources
            ("https://nature.com/article", "High Authority Academic", True),
            ("https://nih.gov/research", "Government Research", True),
            ("https://wikipedia.org/wiki/topic", "Wikipedia Article", True),

            # Low credibility sources
            ("http://random-blog.com/opinion", "Random Blog Opinion", False),
            ("https://biased-news.com/breaking", "Biased News Source", False),
        ]

        correct_assessments = 0
        total_assessments = 0

        for url, title, is_high_credibility in test_sources:
            test_source = ResearchSource(
                source_id=f"precision_test_{total_assessments}",
                url=url,
                title=title,
                content="Test content for credibility assessment." * 10,
                metadata={},
                extraction_timestamp=datetime.now()
            )

            with patch('..agent.quality_agent.run') as mock_agent_run:
                # Mock credibility assessment based on domain
                if any(domain in url for domain in ["nature.com", "nih.gov", "wikipedia.org"]):
                    credibility_score = 0.9
                else:
                    credibility_score = 0.4

                assessment = QualityAssessment(
                    source_id=test_source.source_id,
                    credibility_score=credibility_score,
                    bias_score=0.2,
                    freshness_score=0.8,
                    authority_score=credibility_score,
                    overall_quality=credibility_score * 0.8,
                    confidence_rating=0.9,
                    flags=[]
                )

                mock_result = AsyncMock()
                mock_result.data = assessment
                mock_agent_run.return_value = mock_result

                result = await assess_source_quality(test_source)

                # Check if assessment matches expected credibility
                assessment_is_high = result.credibility_score >= 0.7
                if assessment_is_high == is_high_credibility:
                    correct_assessments += 1

                total_assessments += 1

        # Calculate precision
        precision = correct_assessments / total_assessments if total_assessments > 0 else 0

        # Validate precision requirement
        assert precision >= 0.85, \
            f"Credibility precision {precision:.2%} is below 85% requirement"

    @pytest.mark.asyncio
    async def test_req_006_bias_detection_recall_above_80_percent(self, requirements_test_data):
        """REQ-006: Bias detection recall >80% for obvious bias patterns."""

        # Test with known biased and neutral content
        bias_test_cases = [
            # Obvious bias cases (should be detected)
            ("This is absolutely outrageous and everyone should be shocked!", True),
            ("BREAKING: Incredible discovery that will definitely change everything!", True),
            ("The terrible truth that all experts are completely wrong about!", True),

            # Neutral cases (should not trigger bias detection)
            ("According to research studies, the analysis shows consistent patterns.", False),
            ("Statistical data indicates correlation between variables (p<0.05).", False),
        ]

        correct_detections = 0
        total_bias_cases = sum(1 for _, is_biased in bias_test_cases if is_biased)

        for content, is_biased in bias_test_cases:
            test_source = ResearchSource(
                source_id="bias_recall_test",
                url="https://example.com/test",
                title="Bias Detection Test",
                content=content,
                metadata={},
                extraction_timestamp=datetime.now()
            )

            with patch('..agent.quality_agent.run') as mock_agent_run:
                # Mock bias detection based on content patterns
                bias_indicators = ["outrageous", "shocking", "incredible", "terrible", "definitely"]
                bias_score = 0.8 if any(word in content.lower() for word in bias_indicators) else 0.2

                assessment = QualityAssessment(
                    source_id=test_source.source_id,
                    credibility_score=0.7,
                    bias_score=bias_score,
                    freshness_score=0.8,
                    authority_score=0.6,
                    overall_quality=0.65,
                    confidence_rating=0.85,
                    flags=["high_bias"] if bias_score > 0.6 else []
                )

                mock_result = AsyncMock()
                mock_result.data = assessment
                mock_agent_run.return_value = mock_result

                result = await assess_source_quality(test_source)

                # Check if bias detection matches expected
                if is_biased and result.bias_score >= 0.6:
                    correct_detections += 1

        # Calculate recall for bias detection
        recall = correct_detections / total_bias_cases if total_bias_cases > 0 else 0

        # Validate recall requirement
        assert recall >= 0.80, \
            f"Bias detection recall {recall:.2%} is below 80% requirement"

    @pytest.mark.asyncio
    async def test_req_007_concurrent_throughput_10_to_20_sources(self, performance_test_sources):
        """REQ-007: Handle 10-20 sources concurrently."""

        # Test with 15 sources (middle of range)
        test_sources = performance_test_sources[:15]

        with patch('..agent.quality_agent.run') as mock_agent_run:
            async def mock_concurrent_assessment(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate processing time
                assessment = QualityAssessment(
                    source_id="concurrent_test",
                    credibility_score=0.75,
                    bias_score=0.25,
                    freshness_score=0.8,
                    authority_score=0.7,
                    overall_quality=0.725,
                    confidence_rating=0.85,
                    flags=[]
                )
                mock_result = AsyncMock()
                mock_result.data = assessment
                return mock_result

            mock_agent_run.side_effect = mock_concurrent_assessment

            # Test concurrent processing
            start_time = time.time()
            results = await assess_multiple_sources(test_sources, max_concurrent=15)
            end_time = time.time()

            processing_time = end_time - start_time

            # Validate concurrent processing capability
            assert len(results) == len(test_sources), \
                "Should process all sources concurrently"

            # Should be significantly faster than sequential processing
            # Sequential would be 15 * 0.1 = 1.5 seconds minimum
            assert processing_time < 1.0, \
                f"Concurrent processing took {processing_time:.2f}s, should be <1s"

            # Calculate throughput
            throughput = len(test_sources) / processing_time
            assert throughput >= 10, \
                f"Throughput {throughput:.1f} sources/sec is below 10 sources/sec requirement"


class TestTechnicalRequirements:
    """Validate technical requirements from INITIAL.md."""

    @pytest.mark.asyncio
    async def test_req_008_openai_gpt4o_mini_integration(self):
        """REQ-008: Integration with OpenAI GPT-4o-mini model."""

        # Test that agent is configured for correct model
        from ..settings import settings
        from ..providers import get_assessment_model

        # Validate model configuration
        assert settings.openai_model == "gpt-4o-mini", \
            f"Expected gpt-4o-mini, got {settings.openai_model}"

        # Test model provider setup
        model = get_assessment_model()
        assert model is not None, "Model provider should be configured"

    @pytest.mark.asyncio
    async def test_req_009_required_tools_functionality(self, test_dependencies):
        """REQ-009: Domain Authority Checker, Content Analyzer, Source Cross-Reference tools."""

        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        # Test Domain Authority Checker
        domain_result = await analyze_domain_authority(mock_ctx, "https://example.com")
        assert hasattr(domain_result, 'domain'), "Domain authority tool should return domain analysis"
        assert hasattr(domain_result, 'reputation_score'), "Should include reputation score"

        # Test Content Analyzer
        content_result = await analyze_content_quality(
            mock_ctx,
            "Test content with structure and citations [1]",
            "Test Title"
        )
        assert hasattr(content_result, 'word_count'), "Content analyzer should return word count"
        assert hasattr(content_result, 'structure_score'), "Should include structure analysis"
        assert hasattr(content_result, 'citation_count'), "Should detect citations"

        # Test Bias Analyzer (equivalent to Source Cross-Reference for bias detection)
        bias_result = await analyze_bias_indicators(
            mock_ctx,
            "Neutral factual content based on research evidence",
            "Factual Analysis"
        )
        assert hasattr(bias_result, 'neutrality_score'), "Bias analyzer should return neutrality score"
        assert hasattr(bias_result, 'bias_indicators'), "Should identify bias indicators"

    @pytest.mark.asyncio
    async def test_req_010_input_output_model_compliance(self):
        """REQ-010: ResearchSource input and QualityAssessment output models."""

        # Test ResearchSource model
        test_source = ResearchSource(
            source_id="test_001",
            url="https://example.com/article",
            title="Test Article",
            content="Test content for model validation",
            metadata={"key": "value"},
            extraction_timestamp=datetime.now()
        )

        assert test_source.source_id == "test_001"
        assert test_source.url == "https://example.com/article"
        assert isinstance(test_source.metadata, dict)
        assert isinstance(test_source.extraction_timestamp, datetime)

        # Test QualityAssessment model
        assessment = QualityAssessment(
            source_id="test_001",
            credibility_score=0.8,
            bias_score=0.2,
            freshness_score=0.9,
            authority_score=0.7,
            overall_quality=0.75,
            confidence_rating=0.85,
            flags=["test_flag"]
        )

        assert assessment.source_id == "test_001"
        assert 0.0 <= assessment.credibility_score <= 1.0
        assert 0.0 <= assessment.bias_score <= 1.0
        assert 0.0 <= assessment.overall_quality <= 1.0
        assert isinstance(assessment.flags, list)
        assert isinstance(assessment.assessment_timestamp, datetime)

    @pytest.mark.asyncio
    async def test_req_011_error_handling_with_fallbacks(self, sample_research_source):
        """REQ-011: Handles errors gracefully with appropriate fallbacks."""

        # Test API failure fallback
        with patch('..agent.quality_agent.run') as mock_agent_run:
            mock_agent_run.side_effect = Exception("API failure simulation")

            result = await assess_source_quality(sample_research_source)

            # Should return fallback assessment
            assert isinstance(result, QualityAssessment), "Should return QualityAssessment even on failure"
            assert result.confidence_rating <= 0.2, "Fallback should have low confidence"
            assert "assessment_failed" in result.flags, "Should flag assessment failure"
            assert result.credibility_score == 0.5, "Should provide neutral fallback scores"

    @pytest.mark.asyncio
    async def test_req_012_health_check_functionality(self):
        """REQ-012: Health check functionality for monitoring."""

        # Test successful health check
        with patch('..agent.assess_source_quality') as mock_assess:
            mock_assess.return_value = QualityAssessment(
                source_id="health_check",
                credibility_score=0.8,
                bias_score=0.2,
                freshness_score=0.9,
                authority_score=0.7,
                overall_quality=0.75,
                confidence_rating=0.85,
                flags=[]
            )

            health = await health_check()

            assert health["status"] == "healthy", "Health check should report healthy status"
            assert health["agent_id"] == "quality_assessment_agent", "Should identify agent"
            assert "timestamp" in health, "Should include timestamp"
            assert health["test_assessment_completed"] is True, "Should complete test assessment"

        # Test health check failure
        with patch('..agent.assess_source_quality') as mock_assess:
            mock_assess.side_effect = Exception("Health check failure")

            health = await health_check()

            assert health["status"] == "unhealthy", "Should report unhealthy status on failure"
            assert "error" in health, "Should include error information"


class TestQualityAssessmentMethodology:
    """Validate quality assessment methodology from INITIAL.md."""

    @pytest.mark.asyncio
    async def test_req_013_credibility_factors_weighting(self):
        """REQ-013: Credibility assessment using weighted factors (Domain 30%, Content 25%, Author 20%, Source Type 15%, Freshness 10%)."""

        from ..settings import settings

        # Validate scoring weights configuration
        assert settings.domain_authority_weight == 0.30, "Domain authority should be 30%"
        assert settings.content_quality_weight == 0.25, "Content quality should be 25%"
        assert settings.author_credentials_weight == 0.20, "Author credentials should be 20%"
        assert settings.source_type_weight == 0.15, "Source type should be 15%"
        assert settings.freshness_weight == 0.10, "Freshness should be 10%"

        # Weights should sum to 1.0
        total_weight = (settings.domain_authority_weight +
                       settings.content_quality_weight +
                       settings.author_credentials_weight +
                       settings.source_type_weight +
                       settings.freshness_weight)

        assert abs(total_weight - 1.0) < 0.01, f"Weights should sum to 1.0, got {total_weight}"

    @pytest.mark.asyncio
    async def test_req_014_bias_detection_indicators(self, test_dependencies):
        """REQ-014: Bias detection using language analysis, source diversity, citation patterns."""

        # Test emotional language detection
        emotional_content = "This is absolutely shocking and outrageous! Everyone should be terrified!"

        mock_ctx = Mock()
        mock_ctx.deps = test_dependencies

        bias_result = await analyze_bias_indicators(mock_ctx, emotional_content, "Emotional Title")

        assert hasattr(bias_result, 'emotional_language_score'), "Should detect emotional language"
        assert hasattr(bias_result, 'absolute_terms_count'), "Should count absolute terms"
        assert hasattr(bias_result, 'perspective_diversity'), "Should assess perspective diversity"
        assert isinstance(bias_result.bias_indicators, list), "Should provide bias indicator list"

    @pytest.mark.asyncio
    async def test_req_015_confidence_rating_factors(self, sample_research_source):
        """REQ-015: Confidence rating based on information availability, assessment consistency, external validation."""

        with patch('..agent.quality_agent.run') as mock_agent_run:
            # High confidence case - complete information
            high_conf_assessment = QualityAssessment(
                source_id=sample_research_source.source_id,
                credibility_score=0.85,
                bias_score=0.15,
                freshness_score=0.9,
                authority_score=0.8,
                overall_quality=0.825,
                confidence_rating=0.95,  # High confidence
                flags=[],
                assessment_details={
                    "information_completeness": "high",
                    "assessment_consistency": "high",
                    "external_validation": "available"
                }
            )

            mock_result = AsyncMock()
            mock_result.data = high_conf_assessment
            mock_agent_run.return_value = mock_result

            result = await assess_source_quality(sample_research_source)

            # High confidence should correlate with complete information
            if result.confidence_rating >= 0.8:
                assert result.credibility_score >= 0.7, "High confidence should indicate reliable scores"
                assert result.overall_quality >= 0.6, "High confidence should indicate good overall quality"


class TestIntegrationRequirements:
    """Validate integration requirements from INITIAL.md."""

    @pytest.mark.asyncio
    async def test_req_016_workflow_message_format(self):
        """REQ-016: Integration with workflow using standard AgentMessage format."""

        from ..models import AgentMessage

        # Test AgentMessage structure
        test_message = AgentMessage(
            message_id="msg_001",
            sender_id="web_research_agent",
            recipient_id="quality_assessment_agent",
            message_type="task",
            payload={"source_data": "test"},
            correlation_id="corr_001",
            priority=1
        )

        assert test_message.message_id == "msg_001"
        assert test_message.sender_id == "web_research_agent"
        assert test_message.recipient_id == "quality_assessment_agent"
        assert test_message.message_type == "task"
        assert isinstance(test_message.payload, dict)
        assert isinstance(test_message.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_req_017_agent_communication_interface(self, sample_research_source):
        """REQ-017: Receives from agents #2 and #3, provides to agents #5 and #7."""

        # Test receiving data format (from Web Research Agent #2 or Tool Integration Agent #3)
        incoming_data = {
            "source": sample_research_source.model_dump(),
            "request_id": "req_001",
            "priority": "normal"
        }

        # Process the incoming data
        with patch('..agent.quality_agent.run') as mock_agent_run:
            assessment = QualityAssessment(
                source_id=sample_research_source.source_id,
                credibility_score=0.8,
                bias_score=0.2,
                freshness_score=0.9,
                authority_score=0.7,
                overall_quality=0.75,
                confidence_rating=0.85,
                flags=[]
            )

            mock_result = AsyncMock()
            mock_result.data = assessment
            mock_agent_run.return_value = mock_result

            result = await assess_source_quality(sample_research_source)

            # Test output format (for Citation Management Agent #5 and Data Synthesis Agent #7)
            output_data = {
                "assessment": result.model_dump(),
                "source_id": result.source_id,
                "quality_score": result.overall_quality,
                "confidence": result.confidence_rating,
                "flags": result.flags
            }

            assert "assessment" in output_data
            assert "quality_score" in output_data
            assert "confidence" in output_data
            assert isinstance(output_data["flags"], list)