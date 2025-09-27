# 🎪 Workflow Coordinator Agent

The Workflow Coordinator Agent is responsible for system orchestration and dependency verification in the research engineering multi-agent workflow system.

## 📋 Overview

This agent monitors and coordinates 7 specialized research agents:
1. Research Orchestrator Agent
2. Web Research Agent
3. Tool Integration Agent
4. Quality Assessment Agent
5. Citation Management Agent
6. Query Strategy Agent
7. Data Synthesis Agent

## 🎯 Core Capabilities

- **Real-time Agent Health Monitoring**: Track performance and availability of all research agents
- **Workflow Orchestration**: Coordinate complex multi-agent workflows (parallel, sequential, pipeline, conditional)
- **Dependency Management**: Ensure proper execution order and data flow
- **Error Recovery**: Handle failures and implement automated recovery strategies
- **Performance Optimization**: Monitor and optimize system performance
- **Message Routing**: Manage inter-agent communication

## 🚀 Quick Start

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start Redis (required for message queuing):
```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or install Redis locally
redis-server
```

### Usage

#### Basic Agent Query
```python
from workflow_coordinator import run_coordinator_agent

# Get system status
response = await run_coordinator_agent("Get the current system status")
print(response)

# Check agent health
response = await run_coordinator_agent("Check health of all research agents")
print(response)
```

#### Programmatic API Usage
```python
from workflow_coordinator import (
    workflow_coordinator_agent,
    create_coordinator_dependencies,
    CoordinationRequest
)

# Create dependencies
deps = await create_coordinator_dependencies()

# Use agent tools directly
system_status = await workflow_coordinator_agent.get_system_status(deps)
print(f"System Health: {system_status.overall_health}")

# Coordinate a workflow
coordination_request = CoordinationRequest(
    workflow_id="research-task-001",
    participating_agents=["web-research", "quality-assessment", "data-synthesis"],
    coordination_type="pipeline",
    dependencies={
        "quality-assessment": ["web-research"],
        "data-synthesis": ["quality-assessment"]
    }
)

report = await workflow_coordinator_agent.coordinate_workflow(deps, coordination_request)
print(f"Workflow Status: {report.execution_summary['status']}")
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM | Required |
| `LLM_MODEL` | LLM model to use | `gpt-4` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `MAX_PARALLEL_AGENTS` | Maximum parallel agents | `5` |
| `HEALTH_CHECK_INTERVAL` | Health check frequency (seconds) | `10` |
| `WORKFLOW_TIMEOUT` | Workflow timeout (seconds) | `600` |

### Agent Configuration

The coordinator monitors these agents by default:
- research-orchestrator
- web-research
- tool-integration
- quality-assessment
- citation-management
- query-strategy
- data-synthesis

## 📊 Monitoring & Metrics

The agent provides comprehensive monitoring:

### System Status
- Overall system health (healthy/degraded/critical)
- Individual agent health status
- Active workflow tracking
- System performance metrics

### Performance Metrics
- Agent response times
- Error rates by agent
- Message routing latency
- Workflow completion times
- Resource utilization

### Health Checks
- Automatic health checks every 10 seconds
- Agent failure detection within 10 seconds
- Automated recovery mechanisms
- Alert generation for degraded services

## 🔄 Workflow Coordination Types

### Parallel Execution
Coordinate multiple agents working simultaneously:
```python
coordination_request = CoordinationRequest(
    workflow_id="parallel-research",
    participating_agents=["web-research", "tool-integration"],
    coordination_type="parallel",
    dependencies={}
)
```

### Sequential Execution
Coordinate agents running one after another:
```python
coordination_request = CoordinationRequest(
    workflow_id="sequential-research",
    participating_agents=["query-strategy", "web-research", "data-synthesis"],
    coordination_type="sequential",
    dependencies={}
)
```

### Pipeline Execution
Coordinate agents with data dependencies:
```python
coordination_request = CoordinationRequest(
    workflow_id="pipeline-research",
    participating_agents=["web-research", "quality-assessment", "citation-management", "data-synthesis"],
    coordination_type="pipeline",
    dependencies={
        "quality-assessment": ["web-research"],
        "citation-management": ["quality-assessment"],
        "data-synthesis": ["citation-management"]
    }
)
```

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v --cov=agents/workflow_coordinator
```

## 📈 Success Criteria

The agent meets these performance targets:
- ✅ Maintain 99.5% system uptime
- ✅ Detect agent failures within 10 seconds
- ✅ Successfully coordinate parallel execution of 5+ agents
- ✅ Handle workflow failures with automatic recovery
- ✅ Provide real-time system status and performance metrics
- ✅ Maintain complete audit logs for all workflows

## 🔗 Integration

This agent integrates with the broader research engineering workflow system. It's designed to work with the other 7 research agents in the multi-agent architecture.

For the complete system architecture, see: `research_engineering_workflow/WORKFLOW_ARCHITECTURE.md`

## 📚 API Reference

### Main Functions

- `run_coordinator_agent(query: str)`: Run agent with natural language query
- `create_coordinator_dependencies()`: Initialize agent dependencies
- `get_system_status()`: Get comprehensive system health report
- `coordinate_workflow(request: CoordinationRequest)`: Coordinate workflow execution
- `handle_message_routing(message: AgentMessage)`: Route messages between agents

### Data Models

- `SystemStatus`: Complete system health information
- `CoordinationRequest`: Workflow coordination parameters
- `CoordinationReport`: Workflow execution results
- `AgentHealthStatus`: Individual agent health metrics
- `WorkflowState`: Workflow execution state
- `AgentMessage`: Standard inter-agent message format

## 🤝 Contributing

This agent is part of the research engineering workflow system. Follow the Pydantic AI agent development guidelines in the root `CLAUDE.md` file.

## 📄 License

Part of the Pydantic AI Agent Factory system.