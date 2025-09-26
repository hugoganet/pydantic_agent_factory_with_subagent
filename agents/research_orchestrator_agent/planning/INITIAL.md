# Research Orchestrator Agent - Comprehensive Requirements

## What This Agent Does

The Research Orchestrator Agent serves as the master coordinator for the Research Engineering Workflow system. It analyzes complex research requests, creates strategic execution plans, coordinates parallel agent task distribution, and synthesizes final comprehensive reports with quality assurance integration.

## Core Features (MVP)

1. **Research Request Analysis & Strategy Coordination**
   - Parse complex multi-faceted research requests into actionable subtasks
   - Analyze request complexity to determine optimal research strategy (depth-first, breadth-first, targeted)
   - Create strategic execution plans with task prioritization and resource allocation

2. **Parallel Agent Task Distribution & Orchestration**
   - Coordinate simultaneous execution of Web Research Agent (#2) and Tool Integration Agent (#3)
   - Dispatch tasks using standardized AgentMessage and TaskAssignment protocols
   - Monitor agent execution progress and manage task dependencies
   - Handle parallel execution with maximum 5 agents in Phase 2

3. **Quality Assessment Coordination & Final Report Synthesis**
   - Coordinate with Quality Assessment Agent (#4) for source credibility verification
   - Integrate results from Data Synthesis Agent (#7) for final report compilation
   - Manage quality gates and error recovery across the workflow
   - Deliver comprehensive reports with proper citations and source attribution

## Technical Setup

### Model
- **Provider**: openai
- **Model**: gpt-4o
- **Why**: Complex coordination tasks require advanced reasoning capabilities and reliable structured output generation

### Required Tools

1. **Strategy Planning Tool**: Analyzes research requests and creates execution plans with task breakdown and resource allocation
2. **Task Distribution Tool**: Creates and sends AgentMessage and TaskAssignment objects to coordinated agents
3. **Progress Monitoring Tool**: Tracks agent execution status and handles dependency management
4. **Quality Gate Tool**: Coordinates with Quality Assessment Agent for source verification and confidence scoring
5. **Report Synthesis Tool**: Integrates multi-source data from Data Synthesis Agent into final comprehensive reports

### External Services

**Inter-Agent Communication System**:
- **Redis**: Message queue for inter-agent communication
- **Purpose**: Handle AgentMessage routing and TaskAssignment distribution

**Workflow Coordination**:
- **Workflow Coordinator Agent (#8)**: System health monitoring and performance tracking
- **Purpose**: Provide system status updates and error recovery coordination

**Quality Assurance Integration**:
- **Quality Assessment Agent (#4)**: Source credibility verification
- **Data Synthesis Agent (#7)**: Multi-source information integration and report generation

## Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=your_openai_key

# Inter-Agent Communication
REDIS_URL=redis://localhost:6379

# System Configuration
MAX_PARALLEL_AGENTS=5
LOG_LEVEL=INFO
RESEARCH_TIMEOUT_MINUTES=10

# Quality Thresholds
MIN_SOURCE_QUALITY_SCORE=0.8
MIN_CONFIDENCE_RATING=0.7
```

## Success Criteria

- [ ] Successfully parses complex research requests into strategic execution plans
- [ ] Coordinates parallel execution of Web Research and Tool Integration agents
- [ ] Maintains <10 minute total research completion time
- [ ] Achieves >95% task success rate with proper error recovery
- [ ] Integrates quality assessment results with >0.8 average source credibility
- [ ] Generates comprehensive final reports with proper citation management
- [ ] Handles inter-agent communication using standardized AgentMessage protocol
- [ ] Monitors and responds to system health status from Workflow Coordinator

## Technical Architecture

### Core Components

1. **Request Analyzer Module**
   - Parses user research requests into structured components
   - Identifies research scope, complexity, and requirements
   - Determines optimal strategy based on Query Strategy Agent (#6) recommendations

2. **Task Orchestrator Module**
   - Creates TaskAssignment objects for coordinated agents
   - Manages parallel execution workflow with dependency tracking
   - Handles agent communication using AgentMessage protocol

3. **Quality Gate Manager**
   - Coordinates with Quality Assessment Agent for source verification
   - Applies quality thresholds and confidence ratings
   - Manages error recovery and retry mechanisms

4. **Report Synthesizer Module**
   - Integrates results from Data Synthesis Agent
   - Generates final comprehensive reports
   - Manages citation attribution and source lineage

### Inter-Agent Protocol Implementation

```python
class AgentMessage(BaseModel):
    """Standard inter-agent communication format"""
    message_id: str
    sender_id: str = "research_orchestrator"
    recipient_id: str
    message_type: Literal["task", "result", "status", "error", "health"]
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: str
    priority: int = 1
    retry_count: int = 0

class TaskAssignment(BaseModel):
    """Task assignment from orchestrator to agents"""
    task_id: str
    agent_id: str
    operation: str
    parameters: Dict[str, Any]
    deadline: Optional[datetime]
    dependencies: List[str] = []
    quality_requirements: Dict[str, float] = {"min_credibility": 0.8}
```

### Execution Phases

**Phase 1: Planning (Sequential - 30s)**
- Receive user research request
- Coordinate with Query Strategy Agent (#6) for strategy recommendations
- Create strategic execution plan with task breakdown

**Phase 2: Research (Parallel - 2-3 min)**
- Dispatch tasks to Web Research Agent (#2) and Tool Integration Agent (#3) simultaneously
- Monitor progress and handle intermediate results
- Coordinate with Workflow Coordinator (#8) for system health

**Phase 3: Assessment (Pipeline - 1 min)**
- Send results to Quality Assessment Agent (#4) for verification
- Apply quality gates and confidence scoring
- Handle error recovery if quality thresholds not met

**Phase 4: Attribution (Sequential - 30s)**
- Coordinate Citation Management Agent (#5) for proper source attribution
- Ensure citation formatting and reference management

**Phase 5: Synthesis (Sequential - 1-2 min)**
- Send all verified data to Data Synthesis Agent (#7)
- Receive integrated report with insights and gap analysis

**Phase 6: Delivery (Sequential - 30s)**
- Compile final comprehensive report
- Deliver to user with complete source attribution
- Log completion metrics and performance data

### Performance Targets

- **Total Research Completion**: <10 minutes for standard queries
- **Task Success Rate**: >95% completion with proper error handling
- **Source Quality**: >0.8 average credibility score
- **Parallel Efficiency**: >80% time savings vs sequential execution
- **System Availability**: >99.5% uptime coordination

## Workflow Dependencies

### Receives From:
- **Query Strategy Agent (#6)**: Strategic recommendations and execution plans
- **Web Research Agent (#2)**: Web search results and extracted content
- **Tool Integration Agent (#3)**: Internal system data and API responses
- **Quality Assessment Agent (#4)**: Source credibility scores and verification status
- **Citation Management Agent (#5)**: Formatted citations and reference management
- **Data Synthesis Agent (#7)**: Integrated reports with insights and gap analysis
- **Workflow Coordinator Agent (#8)**: System health status and performance metrics

### Provides To:
- **All Agents**: Command & control coordination and task assignments
- **Users**: Final comprehensive research reports with quality assurance
- **Workflow Coordinator Agent (#8)**: Execution status and performance metrics

## Assumptions Made

- Redis available for inter-agent message queuing and coordination
- All coordinated agents implement standardized AgentMessage protocol
- Quality Assessment Agent provides consistent credibility scoring (0.0-1.0 scale)
- Data Synthesis Agent can handle multi-source integration within 2-minute timeframe
- System operates with maximum 5 parallel agents during research phase
- Error recovery can be handled through retry mechanisms with exponential backoff
- User requests can be parsed into discrete, actionable research subtasks

---
Generated: 2025-09-26
Note: This is the master coordinator agent for the Research Engineering Workflow system. It orchestrates all 7 other agents and manages the complete research pipeline from request analysis to final report delivery.