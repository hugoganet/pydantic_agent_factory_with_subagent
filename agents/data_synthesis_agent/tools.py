"""
Tools for Data Synthesis Agent.

Implements the three core synthesis tools:
1. data_integrator - Combines and normalizes research findings
2. pattern_analyzer - Identifies trends and contradictions
3. report_generator - Creates structured reports
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict

from pydantic_ai import RunContext
from .dependencies import SynthesisDependencies
from .models import ResearchFinding

logger = logging.getLogger(__name__)


def register_synthesis_tools(agent, deps_type):
    """Register all synthesis tools with the agent."""

    @agent.tool
    async def data_integrator(
        ctx: RunContext[deps_type],
        research_findings: List[ResearchFinding],
        normalization_strategy: str = "confidence_weighted"
    ) -> Dict[str, Any]:
        """
        Combine and normalize research findings from multiple agent sources.

        Args:
            ctx: Agent runtime context with dependencies
            research_findings: List of ResearchFinding objects from different agents
            normalization_strategy: Strategy for handling conflicts ("confidence_weighted", "source_priority", "consensus")

        Returns:
            Dict with integrated data, source mapping, and conflict flags
        """
        logger.info(f"Integrating {len(research_findings)} research findings")

        try:
            # Initialize result structure
            result = {
                "success": True,
                "integrated_data": {
                    "unified_findings": [],
                    "source_mapping": defaultdict(list),
                    "conflict_flags": [],
                    "confidence_matrix": {},
                    "processing_stats": {}
                },
                "metadata": {
                    "total_findings": len(research_findings),
                    "duplicate_count": 0,
                    "integration_timestamp": datetime.now().isoformat()
                }
            }

            # Process findings by source agent
            findings_by_agent = defaultdict(list)
            for finding in research_findings:
                findings_by_agent[finding.source_agent].append(finding)

            # Track content for deduplication
            content_signatures = {}
            duplicates_found = 0

            # Process each finding
            for finding in research_findings:
                # Create content signature for deduplication
                content_sig = hash(finding.content[:200])

                if content_sig in content_signatures:
                    # Handle duplicate content
                    existing_finding = content_signatures[content_sig]
                    duplicates_found += 1

                    # Merge confidence levels using strategy
                    if normalization_strategy == "confidence_weighted":
                        merged_confidence = max(existing_finding["confidence_level"], finding.confidence_level)
                        existing_finding["confidence_level"] = merged_confidence

                    # Add source mapping
                    existing_finding["source_agents"].append(finding.source_agent)

                    logger.debug(f"Merged duplicate finding from {finding.source_agent}")

                else:
                    # New unique finding
                    unified_finding = {
                        "finding_id": finding.finding_id,
                        "content": finding.content,
                        "confidence_level": finding.confidence_level,
                        "key_insights": finding.key_insights,
                        "source_agents": [finding.source_agent],
                        "sources": [source.model_dump() for source in finding.sources],
                        "timestamp": finding.timestamp.isoformat(),
                        "metadata": finding.metadata
                    }

                    content_signatures[content_sig] = unified_finding
                    result["integrated_data"]["unified_findings"].append(unified_finding)

                    # Update source mapping
                    result["integrated_data"]["source_mapping"][finding.source_agent].append(finding.finding_id)

            # Identify potential conflicts
            conflicts = []
            confidence_scores = {}

            # Group findings by topic/theme for conflict detection
            topic_groups = defaultdict(list)
            for finding in result["integrated_data"]["unified_findings"]:
                # Simple topic grouping based on key insights
                for insight in finding.get("key_insights", []):
                    topic_groups[insight.lower()].append(finding)

            # Check for contradictions within topic groups
            for topic, findings in topic_groups.items():
                if len(findings) > 1:
                    confidence_scores[topic] = sum(f["confidence_level"] for f in findings) / len(findings)

                    # Simple conflict detection based on opposing keywords
                    opposing_keywords = [
                        ("increase", "decrease"), ("positive", "negative"),
                        ("improve", "decline"), ("up", "down"), ("rise", "fall")
                    ]

                    contents = [f["content"].lower() for f in findings]
                    for pos, neg in opposing_keywords:
                        if any(pos in content for content in contents) and any(neg in content for content in contents):
                            conflicts.append({
                                "conflict_id": f"conflict_{len(conflicts)}",
                                "topic": topic,
                                "description": f"Conflicting information found regarding {topic}",
                                "affected_findings": [f["finding_id"] for f in findings],
                                "confidence_impact": "medium"
                            })

            result["integrated_data"]["conflict_flags"] = conflicts
            result["integrated_data"]["confidence_matrix"] = confidence_scores
            result["integrated_data"]["processing_stats"] = {
                "unique_findings": len(result["integrated_data"]["unified_findings"]),
                "conflicts_detected": len(conflicts),
                "average_confidence": sum(f["confidence_level"] for f in result["integrated_data"]["unified_findings"]) / len(result["integrated_data"]["unified_findings"]) if result["integrated_data"]["unified_findings"] else 0,
                "source_agents_count": len(findings_by_agent)
            }

            result["metadata"]["duplicate_count"] = duplicates_found

            # Update context metrics
            ctx.deps.add_synthesis_metric("integration_duplicates", duplicates_found)
            ctx.deps.add_synthesis_metric("integration_conflicts", len(conflicts))

            logger.info(f"Integration complete: {len(result['integrated_data']['unified_findings'])} unique findings")
            return result

        except Exception as e:
            logger.error(f"Data integration failed: {e}")
            return {
                "success": False,
                "integrated_data": {},
                "metadata": {"error": str(e)},
                "error": f"Integration failed: {e}"
            }

    @agent.tool
    async def pattern_analyzer(
        ctx: RunContext[deps_type],
        integrated_data: Dict[str, Any],
        analysis_depth: str = "standard"
    ) -> Dict[str, Any]:
        """
        Identify trends, correlations, contradictions, and gaps in integrated data.

        Args:
            ctx: Agent runtime context with dependencies
            integrated_data: Output from data_integrator tool
            analysis_depth: Level of analysis ("quick", "standard", "comprehensive")

        Returns:
            Dict with identified patterns, correlations, and trend analysis
        """
        logger.info(f"Analyzing patterns with depth: {analysis_depth}")

        try:
            if not integrated_data.get("success", False):
                raise ValueError("Invalid integrated_data provided")

            findings = integrated_data["integrated_data"]["unified_findings"]

            result = {
                "success": True,
                "analysis_results": {
                    "identified_patterns": [],
                    "correlations": [],
                    "contradictions": integrated_data["integrated_data"]["conflict_flags"],
                    "information_gaps": [],
                    "trend_analysis": {},
                    "confidence_assessment": {}
                },
                "metadata": {
                    "analysis_timestamp": datetime.now().isoformat(),
                    "patterns_found": 0,
                    "contradictions_detected": len(integrated_data["integrated_data"]["conflict_flags"])
                }
            }

            # Pattern identification based on key insights frequency
            insight_frequency = defaultdict(int)
            insight_confidence = defaultdict(list)

            for finding in findings:
                for insight in finding.get("key_insights", []):
                    insight_frequency[insight.lower()] += 1
                    insight_confidence[insight.lower()].append(finding["confidence_level"])

            # Identify significant patterns (mentioned by multiple sources)
            patterns = []
            for insight, frequency in insight_frequency.items():
                if frequency >= 2:  # Pattern threshold
                    avg_confidence = sum(insight_confidence[insight]) / len(insight_confidence[insight])
                    patterns.append({
                        "pattern_id": f"pattern_{len(patterns)}",
                        "description": insight,
                        "frequency": frequency,
                        "confidence": avg_confidence,
                        "significance": "high" if frequency >= 3 else "medium",
                        "supporting_findings": frequency
                    })

            result["analysis_results"]["identified_patterns"] = patterns

            # Correlation analysis - simple keyword co-occurrence
            correlations = []
            if analysis_depth in ["standard", "comprehensive"]:
                insights = list(insight_frequency.keys())
                for i, insight1 in enumerate(insights):
                    for insight2 in insights[i+1:]:
                        # Check co-occurrence in findings
                        cooccurrence_count = 0
                        for finding in findings:
                            finding_insights = [ins.lower() for ins in finding.get("key_insights", [])]
                            if insight1 in finding_insights and insight2 in finding_insights:
                                cooccurrence_count += 1

                        if cooccurrence_count >= 2:
                            correlations.append({
                                "correlation_id": f"corr_{len(correlations)}",
                                "insight1": insight1,
                                "insight2": insight2,
                                "strength": cooccurrence_count,
                                "confidence": min(
                                    sum(insight_confidence[insight1]) / len(insight_confidence[insight1]),
                                    sum(insight_confidence[insight2]) / len(insight_confidence[insight2])
                                )
                            })

            result["analysis_results"]["correlations"] = correlations

            # Information gap identification
            gaps = []
            expected_coverage_areas = ["methodology", "limitations", "implications", "recommendations"]

            for area in expected_coverage_areas:
                area_coverage = sum(1 for finding in findings
                                 if any(area in insight.lower() for insight in finding.get("key_insights", [])))
                if area_coverage == 0:
                    gaps.append(f"No information found regarding {area}")
                elif area_coverage < len(findings) * 0.3:  # Less than 30% coverage
                    gaps.append(f"Limited information available regarding {area}")

            result["analysis_results"]["information_gaps"] = gaps

            # Trend analysis - time-based if timestamps available
            trend_analysis = {
                "temporal_patterns": "insufficient_temporal_data",
                "confidence_trends": {
                    "overall_trend": "stable",
                    "average_confidence": sum(f["confidence_level"] for f in findings) / len(findings) if findings else 0,
                    "confidence_range": {
                        "min": min(f["confidence_level"] for f in findings) if findings else 0,
                        "max": max(f["confidence_level"] for f in findings) if findings else 0
                    }
                }
            }

            result["analysis_results"]["trend_analysis"] = trend_analysis

            # Confidence assessment
            confidence_assessment = {
                "pattern_confidence": sum(p["confidence"] for p in patterns) / len(patterns) if patterns else 0,
                "correlation_confidence": sum(c["confidence"] for c in correlations) / len(correlations) if correlations else 0,
                "overall_analysis_confidence": len(patterns) * 0.1 + len(correlations) * 0.05  # Heuristic
            }

            result["analysis_results"]["confidence_assessment"] = confidence_assessment
            result["metadata"]["patterns_found"] = len(patterns)

            # Update context metrics
            ctx.deps.add_synthesis_metric("patterns_identified", len(patterns))
            ctx.deps.add_synthesis_metric("correlations_found", len(correlations))
            ctx.deps.add_synthesis_metric("gaps_identified", len(gaps))

            logger.info(f"Pattern analysis complete: {len(patterns)} patterns, {len(correlations)} correlations")
            return result

        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return {
                "success": False,
                "analysis_results": {},
                "metadata": {"error": str(e)},
                "error": f"Analysis failed: {e}"
            }

    @agent.tool
    async def report_generator(
        ctx: RunContext[deps_type],
        analysis_results: Dict[str, Any],
        output_format: str = "detailed",
        target_audience: str = "researchers"
    ) -> Dict[str, Any]:
        """
        Generate structured reports with executive summaries and detailed analysis.

        Args:
            ctx: Agent runtime context with dependencies
            analysis_results: Output from pattern_analyzer tool
            output_format: Report format ("executive", "detailed", "technical")
            target_audience: Target audience ("executives", "researchers", "technical")

        Returns:
            Dict with synthesized report and generation metadata
        """
        logger.info(f"Generating {output_format} report for {target_audience}")

        try:
            if not analysis_results.get("success", False):
                raise ValueError("Invalid analysis_results provided")

            analysis_data = analysis_results["analysis_results"]
            patterns = analysis_data.get("identified_patterns", [])
            correlations = analysis_data.get("correlations", [])
            contradictions = analysis_data.get("contradictions", [])
            gaps = analysis_data.get("information_gaps", [])
            confidence_data = analysis_data.get("confidence_assessment", {})

            # Generate executive summary
            exec_summary_parts = []

            if patterns:
                key_patterns = [p["description"] for p in patterns[:3]]  # Top 3 patterns
                exec_summary_parts.append(f"Key patterns identified: {', '.join(key_patterns)}")

            if contradictions:
                exec_summary_parts.append(f"Found {len(contradictions)} potential contradictions requiring attention")

            if gaps:
                exec_summary_parts.append(f"Identified {len(gaps)} information gaps for future research")

            overall_confidence = confidence_data.get("overall_analysis_confidence", 0.7)
            exec_summary_parts.append(f"Overall analysis confidence: {overall_confidence:.1%}")

            executive_summary = ". ".join(exec_summary_parts) + "."

            # Generate key findings
            key_findings = []

            # Convert patterns to key findings
            for i, pattern in enumerate(patterns[:5]):  # Top 5 patterns
                key_findings.append({
                    "finding_id": f"finding_{i+1}",
                    "title": f"Pattern: {pattern['description'].title()}",
                    "description": f"Identified across {pattern['frequency']} sources with {pattern['confidence']:.1%} confidence",
                    "supporting_sources": [f"Multiple sources ({pattern['frequency']} mentions)"],
                    "confidence_level": pattern["confidence"],
                    "significance": pattern.get("significance", "medium"),
                    "cross_validation_status": "validated" if pattern["frequency"] >= 3 else "insufficient"
                })

            # Add correlations as findings
            for i, corr in enumerate(correlations[:3]):  # Top 3 correlations
                key_findings.append({
                    "finding_id": f"correlation_{i+1}",
                    "title": f"Correlation: {corr['insight1'].title()} & {corr['insight2'].title()}",
                    "description": f"Strong correlation found between these insights (strength: {corr['strength']})",
                    "supporting_sources": [f"{corr['strength']} co-occurrences"],
                    "confidence_level": corr["confidence"],
                    "significance": "medium",
                    "cross_validation_status": "validated" if corr["strength"] >= 3 else "insufficient"
                })

            # Generate detailed analysis
            detailed_analysis_parts = []

            if output_format in ["detailed", "technical"]:
                detailed_analysis_parts.append("## Pattern Analysis")
                if patterns:
                    detailed_analysis_parts.append(f"Analysis identified {len(patterns)} significant patterns across the research findings:")
                    for pattern in patterns:
                        detailed_analysis_parts.append(f"- {pattern['description'].title()}: {pattern['frequency']} mentions, {pattern['confidence']:.1%} confidence")
                else:
                    detailed_analysis_parts.append("No significant patterns identified in the research findings.")

                if correlations:
                    detailed_analysis_parts.append("## Correlation Analysis")
                    detailed_analysis_parts.append(f"Found {len(correlations)} significant correlations:")
                    for corr in correlations:
                        detailed_analysis_parts.append(f"- {corr['insight1'].title()} ↔ {corr['insight2'].title()} (strength: {corr['strength']})")

                if contradictions:
                    detailed_analysis_parts.append("## Contradictions and Conflicts")
                    for conflict in contradictions:
                        detailed_analysis_parts.append(f"- {conflict['description']}")
            else:
                # Executive format - shorter analysis
                detailed_analysis_parts.append("## Summary Analysis")
                detailed_analysis_parts.append(f"Research synthesis processed findings from multiple sources, identifying {len(patterns)} key patterns and {len(correlations)} significant correlations.")

            detailed_analysis = "\n\n".join(detailed_analysis_parts)

            # Generate supporting evidence
            supporting_evidence = []
            for pattern in patterns[:3]:  # Top patterns as evidence
                supporting_evidence.append(f"Pattern '{pattern['description']}' supported by {pattern['frequency']} independent sources")

            # Generate recommendations if gaps found
            recommendations = []
            if gaps:
                recommendations.append("Conduct additional research to address identified information gaps")
                for gap in gaps[:3]:  # Top 3 gaps
                    recommendations.append(f"Focus on: {gap}")

            if contradictions:
                recommendations.append("Investigate contradictory findings to resolve discrepancies")

            # Calculate overall confidence assessment
            confidence_assessment = max(0.5, min(0.95, overall_confidence))  # Bounded between 50-95%

            # Build final report
            synthesized_report = {
                "executive_summary": executive_summary,
                "key_findings": key_findings,
                "detailed_analysis": detailed_analysis,
                "supporting_evidence": supporting_evidence,
                "identified_gaps": gaps,
                "confidence_assessment": confidence_assessment,
                "recommendations": recommendations,
                "methodology_notes": f"Synthesis performed using {output_format} format for {target_audience} audience with pattern analysis and cross-validation"
            }

            # Generation metadata
            generation_metadata = {
                "report_format": output_format,
                "target_audience": target_audience,
                "word_count": len(detailed_analysis.split()),
                "generation_timestamp": datetime.now().isoformat(),
                "source_count": len(patterns) + len(correlations),
                "quality_metrics": {
                    "patterns_included": len(patterns),
                    "correlations_included": len(correlations),
                    "contradictions_flagged": len(contradictions),
                    "gaps_identified": len(gaps),
                    "overall_confidence": confidence_assessment
                }
            }

            result = {
                "success": True,
                "synthesized_report": synthesized_report,
                "generation_metadata": generation_metadata
            }

            # Update context metrics
            ctx.deps.add_synthesis_metric("report_generated", True)
            ctx.deps.add_synthesis_metric("report_confidence", confidence_assessment)
            ctx.deps.add_synthesis_metric("key_findings_count", len(key_findings))

            logger.info(f"Report generation complete: {len(key_findings)} key findings, {confidence_assessment:.1%} confidence")
            return result

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {
                "success": False,
                "synthesized_report": {},
                "generation_metadata": {"error": str(e)},
                "error": f"Report generation failed: {e}"
            }