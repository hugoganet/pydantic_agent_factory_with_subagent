#!/usr/bin/env python3
"""
Research Orchestrator Agent - Command Line Interface

Provides command-line access to the research orchestration functionality
for the Research Engineering Workflow system.
"""

import asyncio
import click
import json
import sys
from typing import Optional
from pathlib import Path

from . import run_orchestration, health_check, settings


@click.group()
@click.version_option()
def cli():
    """Research Orchestrator Agent - Master coordinator for research workflows."""
    pass


@cli.command()
@click.argument('query', type=str)
@click.option('--session-id', type=str, help='Session identifier for tracking')
@click.option('--priority', type=click.Choice(['low', 'normal', 'high']),
              default='normal', help='Research priority level')
@click.option('--timeout', type=int, default=10,
              help='Research timeout in minutes')
@click.option('--quality-threshold', type=float, default=0.8,
              help='Minimum source credibility threshold (0.0-1.0)')
@click.option('--max-parallel', type=int, default=5,
              help='Maximum parallel agents')
@click.option('--output', type=click.Path(),
              help='Output file for research report')
@click.option('--format', 'output_format',
              type=click.Choice(['text', 'json', 'markdown']),
              default='text', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
async def research(query: str, session_id: Optional[str], priority: str,
                  timeout: int, quality_threshold: float, max_parallel: int,
                  output: Optional[str], output_format: str, verbose: bool):
    """Execute a research orchestration request."""

    if verbose:
        click.echo(f"Starting research orchestration...")
        click.echo(f"Query: {query}")
        click.echo(f"Priority: {priority}")
        click.echo(f"Timeout: {timeout} minutes")
        click.echo(f"Quality threshold: {quality_threshold}")
        click.echo(f"Max parallel agents: {max_parallel}")
        click.echo()

    try:
        # Execute research orchestration
        result = await run_orchestration(
            research_request=query,
            session_id=session_id,
            priority_level=priority if priority != 'normal' else None,
            research_timeout=timeout * 60,
            min_source_quality=quality_threshold,
            max_parallel_agents=max_parallel
        )

        # Format output
        if output_format == 'json':
            formatted_result = json.dumps({
                "query": query,
                "session_id": session_id,
                "priority": priority,
                "result": result,
                "metadata": {
                    "timeout_minutes": timeout,
                    "quality_threshold": quality_threshold,
                    "max_parallel_agents": max_parallel
                }
            }, indent=2)
        elif output_format == 'markdown':
            formatted_result = f"""# Research Report

## Query
{query}

## Results
{result}

## Metadata
- Session ID: {session_id or 'N/A'}
- Priority: {priority}
- Timeout: {timeout} minutes
- Quality Threshold: {quality_threshold}
- Max Parallel Agents: {max_parallel}
"""
        else:  # text format
            formatted_result = result

        # Output to file or stdout
        if output:
            Path(output).write_text(formatted_result, encoding='utf-8')
            click.echo(f"Research report saved to: {output}")
        else:
            click.echo(formatted_result)

        if verbose:
            click.echo(f"\n✅ Research completed successfully")

    except Exception as e:
        click.echo(f"❌ Research failed: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--format', 'output_format',
              type=click.Choice(['text', 'json']),
              default='text', help='Output format')
async def health(output_format: str):
    """Check orchestrator health status."""

    try:
        health_status = await health_check()

        if output_format == 'json':
            click.echo(json.dumps(health_status, indent=2))
        else:
            status_emoji = "✅" if health_status.get("status") == "healthy" else "❌"
            click.echo(f"{status_emoji} Orchestrator Status: {health_status.get('status', 'unknown')}")

            if health_status.get("status") == "healthy":
                click.echo(f"Model: {health_status.get('model')}")
                click.echo(f"Redis Connected: {health_status.get('redis_connected')}")
                click.echo(f"Agent Endpoints: {health_status.get('agent_endpoints')}")
                click.echo(f"Max Parallel Agents: {health_status.get('max_parallel_agents')}")

                quality_thresholds = health_status.get('quality_thresholds', {})
                click.echo(f"Quality Thresholds:")
                click.echo(f"  - Source Quality: {quality_thresholds.get('min_source_quality')}")
                click.echo(f"  - Confidence: {quality_thresholds.get('min_confidence')}")
            else:
                click.echo(f"Error: {health_status.get('error')}")

    except Exception as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', 'output_format',
              type=click.Choice(['text', 'json']),
              default='text', help='Output format')
def config(output_format: str):
    """Show current configuration."""

    config_data = {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "redis_url": settings.redis_url,
        "max_parallel_agents": settings.max_parallel_agents,
        "research_timeout_minutes": settings.research_timeout_minutes,
        "task_timeout_seconds": settings.task_timeout_seconds,
        "min_source_quality_score": settings.min_source_quality_score,
        "min_confidence_rating": settings.min_confidence_rating,
        "agent_endpoints": settings.agent_endpoints,
        "log_level": settings.log_level,
        "debug": settings.debug
    }

    if output_format == 'json':
        # Remove sensitive information for JSON output
        safe_config = {k: v for k, v in config_data.items()
                       if k not in ['llm_api_key', 'redis_password']}
        click.echo(json.dumps(safe_config, indent=2))
    else:
        click.echo("🔧 Research Orchestrator Configuration:")
        click.echo()
        click.echo(f"LLM Provider: {config_data['llm_provider']}")
        click.echo(f"LLM Model: {config_data['llm_model']}")
        click.echo(f"Redis URL: {config_data['redis_url']}")
        click.echo()
        click.echo("Orchestration Settings:")
        click.echo(f"  Max Parallel Agents: {config_data['max_parallel_agents']}")
        click.echo(f"  Research Timeout: {config_data['research_timeout_minutes']} minutes")
        click.echo(f"  Task Timeout: {config_data['task_timeout_seconds']} seconds")
        click.echo()
        click.echo("Quality Thresholds:")
        click.echo(f"  Source Quality: {config_data['min_source_quality_score']}")
        click.echo(f"  Confidence Rating: {config_data['min_confidence_rating']}")
        click.echo()
        click.echo("Agent Endpoints:")
        for agent_name, endpoint in config_data['agent_endpoints'].items():
            click.echo(f"  {agent_name}: {endpoint}")


@cli.command()
@click.argument('query', type=str)
@click.option('--complexity', type=click.Choice(['simple', 'medium', 'complex']),
              help='Query complexity (auto-detected if not specified)')
@click.option('--timeout', type=int, default=10, help='Timeout in minutes')
@click.option('--quality-threshold', type=float, default=0.8,
              help='Quality threshold (0.0-1.0)')
def analyze(query: str, complexity: Optional[str], timeout: int,
           quality_threshold: float):
    """Analyze a research request without executing it."""

    click.echo(f"🔍 Analyzing research request...")
    click.echo(f"Query: {query}")
    click.echo()

    # Simple analysis based on query characteristics
    word_count = len(query.split())

    if not complexity:
        if word_count < 10:
            detected_complexity = "simple"
        elif word_count < 30:
            detected_complexity = "medium"
        else:
            detected_complexity = "complex"
    else:
        detected_complexity = complexity

    click.echo(f"Detected Complexity: {detected_complexity}")
    click.echo(f"Word Count: {word_count}")
    click.echo(f"Estimated Time: {timeout} minutes")
    click.echo(f"Quality Threshold: {quality_threshold}")
    click.echo()

    # Show estimated workflow phases
    phases = {
        "simple": ["research", "assessment"],
        "medium": ["research", "tool_integration", "assessment", "attribution"],
        "complex": ["planning", "research", "tool_integration", "assessment", "attribution", "synthesis"]
    }

    estimated_phases = phases.get(detected_complexity, phases["complex"])
    click.echo(f"Estimated Workflow Phases: {len(estimated_phases)}")
    for i, phase in enumerate(estimated_phases, 1):
        click.echo(f"  {i}. {phase.title()}")

    # Estimated agents involved
    agents = {
        "simple": ["web_research", "quality_assessment"],
        "medium": ["web_research", "tool_integration", "quality_assessment", "citation_management"],
        "complex": ["query_strategy", "web_research", "tool_integration", "quality_assessment",
                   "citation_management", "data_synthesis"]
    }

    estimated_agents = agents.get(detected_complexity, agents["complex"])
    click.echo(f"\nEstimated Agents Involved: {len(estimated_agents)}")
    for agent in estimated_agents:
        click.echo(f"  - {agent.replace('_', ' ').title()}")


def main():
    """Main CLI entry point."""
    # Handle async commands
    def run_async_command(func):
        def wrapper(*args, **kwargs):
            return asyncio.run(func(*args, **kwargs))
        return wrapper

    # Apply async wrapper to async commands
    cli.commands['research'].callback = run_async_command(cli.commands['research'].callback)
    cli.commands['health'].callback = run_async_command(cli.commands['health'].callback)

    cli()


if __name__ == '__main__':
    main()