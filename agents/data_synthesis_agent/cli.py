"""
CLI interface for Data Synthesis Agent.

Provides command-line access to synthesis functionality for development
and testing purposes.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

import click
from datetime import datetime

from .agent import run_synthesis, health_check
from .models import SynthesisRequest, ResearchFinding, SynthesisRequirements, ResearchSource
from .settings import settings


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Data Synthesis Agent - CLI Interface for research synthesis operations."""
    pass


@cli.command()
def health():
    """Check agent health status."""
    async def check_health():
        try:
            status = await health_check()
            if status["status"] == "healthy":
                click.echo(click.style("✅ Agent is healthy", fg="green"))
                click.echo(f"Agent ID: {status['agent_id']}")
                click.echo(f"Model: {status['model']}")
                click.echo(f"Tools: {status['tools_registered']}")
                click.echo(f"Max Findings: {status['max_findings']}")
                click.echo(f"Timeout: {status['timeout_seconds']}s")
            else:
                click.echo(click.style("❌ Agent is unhealthy", fg="red"))
                click.echo(f"Error: {status.get('error', 'Unknown error')}")
                sys.exit(1)
        except Exception as e:
            click.echo(click.style(f"❌ Health check failed: {e}", fg="red"))
            sys.exit(1)

    asyncio.run(check_health())


@cli.command()
@click.argument("findings_file", type=click.Path(exists=True, path_type=Path))
@click.option("--output-format",
              type=click.Choice(["executive", "detailed", "technical"]),
              default="executive",
              help="Output format for the synthesis report")
@click.option("--target-audience",
              type=click.Choice(["executives", "researchers", "technical", "general"]),
              default="executives",
              help="Target audience for the report")
@click.option("--output-file", "-o",
              type=click.Path(path_type=Path),
              help="Output file for synthesis report")
@click.option("--session-id",
              help="Session identifier for tracking")
def synthesize(findings_file: Path, output_format: str, target_audience: str,
               output_file: Path, session_id: str):
    """
    Synthesize research findings from a JSON file.

    FINDINGS_FILE should contain a JSON array of research findings.
    """
    async def run_synthesis_cli():
        try:
            # Load research findings from file
            with open(findings_file, 'r', encoding='utf-8') as f:
                findings_data = json.load(f)

            if not isinstance(findings_data, list):
                raise ValueError("Findings file must contain a JSON array")

            # Convert to ResearchFinding objects
            research_findings = []
            for i, finding_data in enumerate(findings_data):
                # Ensure required fields
                if not finding_data.get("source_agent"):
                    finding_data["source_agent"] = "unknown"
                if not finding_data.get("finding_id"):
                    finding_data["finding_id"] = f"finding_{i}"
                if not finding_data.get("content"):
                    finding_data["content"] = "No content provided"
                if "confidence_level" not in finding_data:
                    finding_data["confidence_level"] = 0.7

                # Convert sources if present
                sources = []
                for source_data in finding_data.get("sources", []):
                    sources.append(ResearchSource(**source_data))
                finding_data["sources"] = sources

                research_findings.append(ResearchFinding(**finding_data))

            click.echo(f"Loaded {len(research_findings)} research findings")

            # Create synthesis request
            request_id = f"cli_synthesis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            synthesis_request = SynthesisRequest(
                request_id=request_id,
                research_findings=research_findings,
                synthesis_requirements=SynthesisRequirements(),
                output_format=output_format,
                target_audience=target_audience
            )

            click.echo(f"Starting synthesis (format: {output_format}, audience: {target_audience})")

            # Run synthesis
            result = await run_synthesis(
                synthesis_request,
                session_id=session_id
            )

            # Output results
            if output_file:
                # Save to file
                output_data = result.model_dump()
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, default=str)
                click.echo(f"✅ Synthesis report saved to {output_file}")
            else:
                # Print to console
                click.echo("\n" + "="*80)
                click.echo(click.style("SYNTHESIS REPORT", fg="blue", bold=True))
                click.echo("="*80)

                click.echo(click.style("\nExecutive Summary:", fg="green", bold=True))
                click.echo(result.executive_summary)

                click.echo(click.style(f"\nKey Findings ({len(result.key_findings)}):", fg="green", bold=True))
                for finding in result.key_findings[:5]:  # Show top 5
                    click.echo(f"• {finding.title} (confidence: {finding.confidence_level:.1%})")

                if result.gaps_identified:
                    click.echo(click.style(f"\nInformation Gaps ({len(result.gaps_identified)}):", fg="yellow", bold=True))
                    for gap in result.gaps_identified[:3]:  # Show top 3
                        click.echo(f"• {gap.description}")

                click.echo(click.style(f"\nOverall Confidence: {result.confidence_assessment.overall_confidence:.1%}", fg="blue", bold=True))
                click.echo(f"Processing Time: {result.metadata.synthesis_duration_seconds:.2f}s")

        except Exception as e:
            click.echo(click.style(f"❌ Synthesis failed: {e}", fg="red"))
            sys.exit(1)

    asyncio.run(run_synthesis_cli())


@cli.command()
@click.option("--count", "-n", default=3, help="Number of sample findings to generate")
@click.option("--output-file", "-o",
              type=click.Path(path_type=Path),
              default="sample_findings.json",
              help="Output file for sample findings")
def generate_sample(count: int, output_file: Path):
    """Generate sample research findings for testing."""
    sample_findings = []

    topics = [
        ("AI Impact on Employment", "artificial intelligence", "job market"),
        ("Climate Change Effects", "climate change", "environmental"),
        ("Remote Work Productivity", "remote work", "productivity"),
        ("Renewable Energy Adoption", "renewable energy", "sustainability"),
        ("Digital Health Solutions", "digital health", "healthcare technology")
    ]

    for i in range(count):
        topic, keyword1, keyword2 = topics[i % len(topics)]

        finding = {
            "source_agent": ["web_research_agent", "tool_integration_agent"][i % 2],
            "finding_id": f"sample_finding_{i+1}",
            "content": f"Research indicates significant developments in {topic.lower()}. "
                      f"Studies show that {keyword1} is increasingly affecting {keyword2}. "
                      f"Multiple sources confirm this trend with varying degrees of certainty.",
            "sources": [
                {
                    "title": f"Study on {topic}",
                    "url": f"https://example.com/research/{keyword1.replace(' ', '-')}",
                    "source_type": "web"
                }
            ],
            "confidence_level": 0.7 + (i % 3) * 0.1,  # Vary confidence 0.7-0.9
            "key_insights": [
                f"{topic} shows significant impact",
                f"{keyword1.title()} adoption increasing",
                f"Future implications for {keyword2}"
            ],
            "metadata": {
                "extraction_method": "sample_generation",
                "topic_category": topic
            }
        }

        sample_findings.append(finding)

    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_findings, f, indent=2)

    click.echo(f"✅ Generated {count} sample findings in {output_file}")
    click.echo(f"Run synthesis with: synthesis-cli synthesize {output_file}")


@cli.command()
def config():
    """Show current agent configuration."""
    click.echo(click.style("Data Synthesis Agent Configuration", fg="blue", bold=True))
    click.echo(f"Agent ID: {settings.agent_id}")
    click.echo(f"LLM Provider: {settings.llm_provider}")
    click.echo(f"LLM Model: {settings.llm_model}")
    click.echo(f"Environment: {settings.app_env}")
    click.echo(f"Log Level: {settings.log_level}")
    click.echo(f"Debug Mode: {settings.debug}")
    click.echo(f"Max Findings: {settings.max_findings_per_synthesis}")
    click.echo(f"Timeout: {settings.synthesis_timeout_seconds}s")
    click.echo(f"Min Confidence: {settings.min_confidence_threshold}")


if __name__ == "__main__":
    cli()