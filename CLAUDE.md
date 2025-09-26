# 🏭 Pydantic AI Agent Factory - Global Orchestration Rules

This defines the complete orchestration workflow for the AI Agent Factory system and the principles that apply to ALL Pydantic AI agent development work. When a user requests to build an AI agent, follow this systematic process using specialized subagents to transform high-level requirements into simple but complete Pydantic AI agents.

**Core Philosophy**: Transform "I want an agent that can search the web" into a fully-functional and tested Pydantic AI agent. User input is required during Phase 0 clarification, then the process runs autonomously.

---

## 🎯 Primary Directive

⚠️ **CRITICAL WORKFLOW TRIGGER**: When ANY user request involves creating, building, or developing an AI agent:

1. **IMMEDIATELY** recognize this as an agent factory request (stop everything else)
2. **MUST** follow Phase 0 first - ask clarifying questions
3. **WAIT** for user responses
4. **THEN** determine if workflow or isolated agent and proceed accordingly

**Factory Workflow Recognition Patterns** (if user says ANY of these):

- "Build an AI agent that..."
- "Create an agent for..."  
- "I need an AI assistant that can..."
- "Make a Pydantic AI agent..."
- "I want to build a Pydantic AI agent..."
- Any request mentioning agent/AI/LLM + functionality

**REQUEST TYPE DETERMINATION (happens AFTER Phase 0):**

1. After getting user clarifications, analyze request type:
   - **WORKFLOW INDICATORS**: "multiple agents", "workflow", "pipeline", "orchestration", agents (plural)
   - **ISOLATED AGENT INDICATORS**: "agent" (singular), single focused task, specific functionality

2. **IF WORKFLOW DETECTED:**
   - Check current git branch: `git branch --show-current`
   - **IF ISSUE BRANCH** (contains numbers like issue-123, 123-feature):
     - Extract issue number from branch name
     - Run `gh issue view {number}` to get issue details
     - Search for workflow directory: `find . -name "*workflow*" -type d`
     - Read WORKFLOW_ARCHITECTURE.md if found
     - Determine which agent to create based on issue content
     - Continue to Phase 1 with workflow context
   - **IF NOT ISSUE BRANCH:**
     - Call pydantic-ai-workflow-orchestrator

3. **IF ISOLATED AGENT DETECTED:**
   - Continue directly to Phase 1 (Requirements Documentation)
   - Use TodoWrite for local progress tracking

**WORKFLOW ENFORCEMENT**: You MUST:

1. Start with Phase 0 (clarifying questions)
2. Wait for user response before proceeding
3. Determine request type (workflow vs isolated agent)
4. Follow appropriate path:
   - **WORKFLOW**: Check GitHub branch → Architecture integration OR Orchestrator call
   - **ISOLATED**: Continue to Phase 1
5. Never jump directly to implementation

When you want to use or call upon a subagent, you must invoke the subagent, giving them a prompt and passing control to them.

---

## 🔄 Complete Factory Workflow

### Phase 0: Request Recognition & Clarification

**Trigger Patterns** (activate factory on any of these):

- "Build an AI agent that..."
- "Create an agent for..."
- "I need an AI assistant that can..."
- "Make a Pydantic AI agent..."
- "Develop an LLM agent..."
- Any request mentioning agent/AI/LLM + functionality

**Immediate Action**:

```
1. Acknowledge agent creation request
2. Ask 2-3 targeted clarifying questions (BEFORE determining type):
   - Primary functionality and use case
   - Single agent or multiple agents working together?
   - Preferred APIs or integrations (if applicable)
3. ⚠️ CRITICAL: STOP AND WAIT for user responses
   - Wait to proceed to step 4 until user has answered
   - Refrain from making assumptions to "keep the process moving"
   - Avoid creating folders or invoke subagents yet
   - WAIT for explicit user input before continuing
4. Only after user responds: ANALYZE REQUEST TYPE
   - Look for workflow indicators vs isolated agent indicators
   - Proceed to appropriate workflow path
```

### Phase 1: Requirements Documentation 🎯

**Subagent**: `pydantic-ai-planner`
**Trigger**: Invoked after Phase 0 clarifications and request type determination
**Mode**: AUTONOMOUS - Works without user interaction
**Philosophy**: SIMPLE, FOCUSED requirements - MVP mindset
**Progress**: Use TodoWrite for tracking

```
Actions:
1. Create TodoWrite entry for "Requirements Analysis" as in_progress
2. Receive user request + clarifications + workflow context (if applicable)
3. DETERMINE AGENT FOLDER NAME (snake_case, e.g., web_search_agent, asana_manager)
4. Create agents/[AGENT_FOLDER_NAME]/ directory
5. Analyze requirements focusing on CORE functionality only
6. Make simple, practical assumptions (single model, basic error handling)
7. Create minimal INITIAL.md with 2-3 core features maximum
8. Output: agents/[EXACT_FOLDER_NAME]/planning/INITIAL.md
   ⚠️ CRITICAL: Output to planning/ subdirectory
9. Mark TodoWrite "Requirements Analysis" as completed
```

**Quality Gate**: INITIAL.md must include:

- ✅ Agent classification and type
- ✅ Functional requirements
- ✅ Technical requirements
- ✅ External dependencies
- ✅ Success criteria

### Phase 2: Parallel Component Development ⚡

**Execute SIMULTANEOUSLY** (all three subagents work in parallel):
**Progress**: Create TodoWrite entries for all three components before parallel invocation

**CRITICAL: Use parallel tool invocation:** When invoking multiple subagents, you MUST call all three Task tools in a SINGLE message with multiple tool uses. This ensures true parallel execution.

- ❌ WRONG: Invoke planner, wait for completion, then invoke prompt engineer
- ✅ RIGHT: Single message with three Task tool invocations
- Create TodoWrite entries for "System Prompt Design", "Tool Development Planning", and "Dependency Configuration" as in_progress

#### 2A: System Prompt Engineering

**Subagent**: `pydantic-ai-prompt-engineer`
**Philosophy**: SIMPLE, CLEAR prompts - typically 100-300 words

```
Input: planning/INITIAL.md + FOLDER NAME from main agent
Output: agents/[EXACT_FOLDER_NAME]/planning/prompts.md
⚠️ CRITICAL: Output MARKDOWN file with prompt specifications, NOT Python code
Contents:
- One simple static system prompt (100-300 words)
- Skip dynamic prompts unless explicitly needed
- Focus on essential behavior only
- Mark TodoWrite "System Prompt Design" as completed when done
```

#### 2B: Tool Development Planning

**Subagent**: `pydantic-ai-tool-integrator`
**Philosophy**: MINIMAL tools - 2-3 essential functions only

```
Input: planning/INITIAL.md + FOLDER NAME from main agent
Output: agents/[EXACT_FOLDER_NAME]/planning/tools.md
⚠️ CRITICAL: Output MARKDOWN file with tool specifications, NOT Python code
Contents:
- 2-3 essential tool specifications only
- Simple parameters (1-3 per tool)
- Basic error handling
- Single-purpose tools
- Mark TodoWrite "Tool Development Planning" as completed when done
```

#### 2C: Dependency Configuration Planning

**Subagent**: `pydantic-ai-dependency-manager`
**Philosophy**: MINIMAL config - essential environment variables only

```
Input: planning/INITIAL.md + FOLDER NAME from main agent
Output: agents/[EXACT_FOLDER_NAME]/planning/dependencies.md
⚠️ CRITICAL: Output MARKDOWN file with dependency specifications, NOT Python code
Contents:
- Essential environment variables only
- Single model provider (no fallbacks)
- Simple dataclass dependencies
- Minimal Python packages
- Mark TodoWrite "Dependency Configuration" as completed when done
```

**Phase 2 Complete When**: All three subagents report completion

### Phase 3: Agent Implementation 🔨

**Actor**: Main Claude Code (not a subagent)
**Progress**: Use TodoWrite to track implementation steps

```
Actions:
1. Create TodoWrite entry "Agent Implementation" as in_progress
2. Verify all Phase 2 components completed (mark as done in TodoWrite)
3. READ the 4 markdown files from planning phase:
   - agents/[folder]/planning/INITIAL.md
   - agents/[folder]/planning/prompts.md
   - agents/[folder]/planning/tools.md
   - agents/[folder]/planning/dependencies.md
4. Use WebSearch to find Pydantic AI patterns and examples as needed
5. IMPLEMENT the actual Python code based on specifications:
   - Convert prompt specs → prompts.py
   - Convert tool specs → tools.py
   - Convert dependency specs → settings.py, providers.py, dependencies.py
6. Create complete agent implementation:
   - Combine all components into agent.py
   - Wire up dependencies and tools
   - Create main execution file
7. Mark TodoWrite "Agent Implementation" as completed
8. Structure final project:
   agents/[agent_name]/
   ├── agent.py           # Main agent
   ├── settings.py        # Configuration
   ├── providers.py       # Model providers
   ├── dependencies.py    # Dependencies
   ├── tools.py          # Tool implementations
   ├── prompts.py        # System prompts
   ├── __init__.py       # Package init
   ├── requirements.txt  # Python deps
   ├── .env.example      # Environment template
   └── README.md         # Usage documentation
```

### Phase 4: Validation & Testing ✅

**Subagent**: `pydantic-ai-validator`
**Trigger**: Automatic after implementation
**Duration**: 3-5 minutes
**Progress**: Use TodoWrite for tracking

```
Actions:
1. Create TodoWrite entry "Validation & Testing" as in_progress
2. Invoke validator subagent with agent folder path
3. Create comprehensive test suite
4. Validate against INITIAL.md requirements
5. Run tests with TestModel
6. Generate validation report
7. Mark TodoWrite "Validation & Testing" as completed
8. Output: agents/[agent_name]/tests/
   ├── test_agent.py
   ├── test_tools.py
   ├── test_integration.py
   ├── test_validation.py
   ├── conftest.py
   └── VALIDATION_REPORT.md
```

**Success Criteria**:

- All requirements validated
- Core functionality tested
- Error handling verified
- Performance acceptable

### Phase 5: Delivery & Documentation 📦

**Actor**: Main Claude Code
**Progress**: Use TodoWrite for final tracking
**Final Actions**:

```
1. Create TodoWrite entry "Documentation & Delivery" as in_progress
2. Generate comprehensive README.md
3. Create usage examples
4. Document API endpoints (if applicable)
5. Provide deployment instructions
6. Mark TodoWrite "Documentation & Delivery" as completed
7. Provide summary report to user with agent location and capabilities
```

---

## 📋 Progress Tracking Protocol

### TodoWrite Management

Use TodoWrite consistently throughout the factory workflow:

```
Standard workflow tasks:
- "Requirements Analysis" (Phase 1)
- "System Prompt Design" (Phase 2A)
- "Tool Development Planning" (Phase 2B)
- "Dependency Configuration" (Phase 2C)
- "Agent Implementation" (Phase 3)
- "Validation & Testing" (Phase 4)
- "Documentation & Delivery" (Phase 5)
```

### Task Status Management

- Create TodoWrite entry as "in_progress" when starting each phase
- Mark as "completed" immediately after phase finishes successfully
- Add new tasks if issues or additional work discovered
- Keep only one task "in_progress" at a time (except during parallel Phase 2)

### Subagent Communication

Pass consistent context to all subagents:

- Include agent folder name: "Output to agents/[FOLDER_NAME]/"
- Reference workflow context if applicable
- Provide clear specifications from planning phase

## 🎭 Subagent Invocation Rules

### Automatic Invocation

Subagents are invoked AUTOMATICALLY based on workflow phase:

```python
if user_request.contains(agent_creation_pattern):
    # Phase 0 - Main Claude Code asks clarifications
    clarifications = ask_user_questions()
    
    # Phase 1 - Invoke planner with context
    invoke("pydantic-ai-planner", context={
        "user_request": original_request,
        "clarifications": clarifications
    })
    
    # Phase 2 - Parallel automatic
    parallel_invoke([
        "pydantic-ai-prompt-engineer",
        "pydantic-ai-tool-integrator", 
        "pydantic-ai-dependency-manager"
    ])
    
    # Phase 3 - Main Claude Code
    implement_agent()
    
    # Phase 4 - Automatic
    invoke("pydantic-ai-validator")
```

### Manual Override

Users can explicitly request specific subagents:

- "Use the planner to refine requirements"
- "Have the tool integrator add web search"
- "Run the validator again"

---

## 📁 Output Directory Structure

Every agent factory run creates:

```
agents/
└── [agent_name]/
    ├── planning/              # All planning documents
    │   ├── INITIAL.md         # Requirements (planner)
    │   ├── prompts.md         # Prompt specifications (prompt-engineer)
    │   ├── tools.md           # Tool specifications (tool-integrator)
    │   └── dependencies.md    # Dependency specifications (dependency-manager)
    ├── agent.py               # Main implementation
    ├── settings.py            # Configuration
    ├── providers.py           # Model providers
    ├── dependencies.py        # Dependencies
    ├── tools.py              # Tools
    ├── prompts.py            # Prompts
    ├── cli.py                # CLI interface
    ├── requirements.txt      # Python packages
    ├── .env.example          # Environment template
    ├── README.md             # Documentation
    └── tests/                # Test suite (if created)
        ├── test_agent.py
        └── test_tools.py
```

---

## 🔧 Implementation Guidelines

### For Simple Agent Requests

Example: "Build an agent that can search the web"

```
1. Planner asks minimal questions (1-2)
2. Assumes standard patterns (Brave API, string output)
3. Completes in ~10 minutes total
4. Delivers working agent with basic tests
```

### For Complex Agent Requests

Example: "Build a multi-modal agent with database, caching, and workflow orchestration"

```
1. Planner asks comprehensive questions (4-5)
2. Multiple iterations may be needed
3. Delivers simple yet complete system with full test coverage
```

### Error Handling Protocol

If any subagent fails:

```
1. Log error with context
2. Attempt automatic recovery
3. If recovery fails, ask user for guidance
4. Continue with partial implementation if possible
5. Document limitations in README
```

---

## 📝 Main Agent Clarification Guidelines

When a user requests an AI agent, the main Claude Code agent should:

### Ask 2-3 Focused Questions

Keep questions simple and targeted:

1. **Core Functionality**: "What specific tasks should this agent handle?"
2. **Integration Needs**: "Will it need to connect to any external services or APIs?"
3. **Output Format**: "Should it return plain text, structured data, or something else?"

### Avoid Over-Questioning

- Don't ask about technical details (the planner will handle those)
- Don't ask about implementation specifics
- Keep questions high-level and user-friendly

### Pass Context to Planner

When invoking the planner, provide:

- Original user request
- User's answers to clarifying questions
- Any additional context from the conversation

## 🚀 Quick Start Examples

### Example 1: Web Search Agent

**User**: "I want to build an AI agent that can search the web"

**Claude Code Response**:

```
I'll help you build a web search AI agent using the Pydantic AI framework. Let me ask a few quick questions to better understand your needs:

1. What will the agent primarily search for? (general web content, specific domains, research papers, etc.)
2. Is this a single agent or part of multiple agents working together?
3. Should the agent summarize the results or return raw search data?

[STOPS HERE AND WAITS FOR USER TO RESPOND]

[After user responds: "It's a single agent for general web content with summaries"]

Perfect! I can see this is an isolated agent request (single agent, specific task). I'll now proceed with creating your web search agent.

📋 Creating Requirements Document...
[Invokes pydantic-ai-planner with context]

[Planner works autonomously and creates INITIAL.md]

⚙️ Building Agent Components...
[Parallel invocation of prompt-engineer, tool-integrator, dependency-manager]

🔨 Implementing Your Agent...
[Main implementation]

✅ Running Validation...
[Invokes pydantic-ai-validator]

🎉 Agent Complete!
Your web search agent is ready at: agents/web_search_agent/
```

### Example 2: Database Query Agent

**User**: "Create an agent that can query PostgreSQL databases and explain results"

**Claude Code Response**:

```
I'll create a PostgreSQL query agent with explanation capabilities. Let me ask a few quick questions first:

1. What types of queries will this agent need to run? (SELECT only, or also INSERT/UPDATE/DELETE?)
2. Is this a single agent or part of multiple agents in a workflow?
3. How detailed should the explanations be? (brief summaries or detailed analysis?)

[STOPS HERE AND WAITS FOR USER TO RESPOND]

[After user responds: "SELECT queries only, single agent, detailed analysis"]

Great! I can see this is an isolated agent request. I'll now create a comprehensive requirements document for your PostgreSQL agent.

📋 Creating Requirements Document...
[Invokes pydantic-ai-planner with context]
[Process continues autonomously]
```

### Example 3: Workflow Detection

**User**: "I want to build multiple AI agents that work together - one for data collection, one for analysis, and one for reporting"

**Claude Code Response**:

```
I'll help you build a multi-agent workflow system. Let me ask a few questions to understand your needs:

1. How should these agents communicate with each other?
2. What type of data will be collected and analyzed?
3. What format should the final reports be in?

[STOPS HERE AND WAITS FOR USER TO RESPOND]

[After user responds with workflow details]

I can see this is a workflow request (multiple agents working together). Let me check your current git branch...

[Runs: git branch --show-current]

I see you're on branch "issue-45-data-pipeline". Let me fetch the issue details...

[Runs: gh issue view 45]

Based on the issue, I need to create the data collection agent first. Let me check for workflow architecture...

[Searches for workflow directory and WORKFLOW_ARCHITECTURE.md]

Found workflow structure! I'll now create the data collection agent as specified in the architecture.

📋 Creating Requirements Document for Data Collection Agent...
[Process continues with targeted agent creation]
```

### Example 4: Workflow Without Issue Branch

**User**: "Create a pipeline of agents for customer support automation"

**Claude Code Response**:

```
I'll help you build a customer support automation pipeline. Let me ask clarifying questions:

1. What channels will receive customer requests?
2. What types of issues should be automated vs escalated?
3. How should the agents coordinate responses?

[After user responds]

This is a workflow request, but you're not on an issue branch. I'll call the workflow orchestrator to help design your multi-agent system.

🏭 Calling Workflow Orchestrator...
[Invokes pydantic-ai-workflow-orchestrator]

[Orchestrator analyzes requirements and creates architecture plan]
```

---

## 🔍 Monitoring & Debugging

### Progress Tracking

Claude Code should provide status updates:

```
✅ Phase 1: Requirements Complete (INITIAL.md created)
⏳ Phase 2: Building Components (3 subagents working...)
  ✅ Prompts: Complete
  ✅ Tools: Complete
  ⏳ Dependencies: In progress...
⏳ Phase 3: Implementation pending...
⏳ Phase 4: Validation pending...
```

### Debug Mode

Enable with: "Build agent in debug mode"

- Verbose logging from all subagents
- Intermediate outputs preserved
- Step-by-step confirmation mode
- Performance metrics collected

---

## 🛡️ Quality Assurance

### Every Agent MUST Have

1. **Comprehensive tests** using TestModel/FunctionModel
2. **Error handling** for all external operations
3. **Security measures** for API keys and inputs
4. **Documentation** for usage and deployment
5. **Environment template** (.env.example)

### Validation Checklist

Before delivery, confirm:

- [ ] All requirements from INITIAL.md implemented
- [ ] Tests passing with >80% coverage
- [ ] API keys properly managed
- [ ] Error scenarios handled
- [ ] Documentation complete
- [ ] Usage examples provided

---

## 🎨 Customization Points

### User Preferences

Users can specify:

- Preferred LLM provider (OpenAI, Anthropic, Gemini)
- Output format (string, structured, streaming)
- Testing depth (basic, comprehensive, exhaustive)
- Documentation style (minimal, standard, detailed)

### Advanced Features

For power users:

- Custom subagent configurations
- Alternative workflow sequences
- Integration with existing codebases
- CI/CD pipeline generation

---

## 📊 Success Metrics

Track factory performance:

- **Time to Completion**: Target <15 minutes for standard agents
- **Test Coverage**: Minimum 80% for agents
- **Validation Pass Rate**: 100% of requirements tested
- **User Intervention**: Minimize to initial requirements only

---

## 🔄 Continuous Improvement

### Feedback Loop

After each agent creation:

1. Analyze what worked well
2. Identify bottlenecks
3. Update subagent prompts if needed
4. Refine workflow based on patterns

### Pattern Library

Build a library of common patterns:

- Search agents
- Database agents
- Workflow orchestrators
- Chat interfaces
- API integrations

---

## 🚨 Important Rules

### ALWAYS

- ✅ Use python-dotenv for environment management
- ✅ Create a .env.example
- ✅ Follow main_agent_reference patterns
- ✅ Create comprehensive tests
- ✅ Document everything
- ✅ Validate against requirements

### Anti-patterns to ALWAYS avoid

- ❌ Hardcode API keys or secrets
- ❌ Skip testing phase
- ❌ Ignore error handling
- ❌ Create overly complex agents
- ❌ Forget security considerations

---

## 🎯 Final Checklist

Before considering an agent complete:

- [ ] Requirements captured in INITIAL.md
- [ ] All components generated by subagents
- [ ] Agent implementation complete and functional
- [ ] Tests written and passing
- [ ] Documentation comprehensive
- [ ] Security measures in place
- [ ] User provided with clear next steps

---

## 🔄 Pydantic AI Core Principles

**IMPORTANT: These principles apply to ALL Pydantic AI agent development:**

### Research Methodology for AI Agents

- **Web search extensively** - Always research Pydantic AI patterns and best practices
- **Study official documentation** - ai.pydantic.dev is the authoritative source
- **Pattern extraction** - Identify reusable agent architectures and tool patterns
- **Gotcha documentation** - Document async patterns, model limits, and context management issues

## 📚 Project Awareness & Context

- **Use a virtual environment** to run all code and tests. If one isn't already in the codebase when needed, create it
- **Use consistent Pydantic AI naming conventions** and agent structure patterns
- **Follow established agent directory organization** patterns (agent.py, tools.py, models.py)
- **Leverage Pydantic AI examples extensively** - Study existing patterns before creating new agents

## 🧱 Agent Structure & Modularity

- **Never create files longer than 500 lines** - Split into modules when approaching limit
- **Organize agent code into clearly separated modules** grouped by responsibility:
  - `agent.py` - Main agent definition and execution logic
  - `tools.py` - Tool functions used by the agent
  - `models.py` - Pydantic output models and dependency classes
  - `dependencies.py` - Context dependencies and external service integrations
- **Use clear, consistent imports** - Import from pydantic_ai package appropriately
- **Use python-dotenv and load_dotenv()** for environment variables - Follow examples/main_agent_reference/settings.py pattern
- **Never hardcode sensitive information** - Always use .env files for API keys and configuration

## 🤖 Pydantic AI Development Standards

### Agent Creation Patterns

- **Use model-agnostic design** - Support multiple providers (OpenAI, Anthropic, Gemini)
- **Implement dependency injection** - Use deps_type for external services and context
- **Define structured outputs** - Use Pydantic models for result validation
- **Include comprehensive system prompts** - Both static and dynamic instructions

### Tool Integration Standards

- **Use @agent.tool decorator** for context-aware tools with RunContext[DepsType]
- **Use @agent.tool_plain decorator** for simple tools without context dependencies
- **Implement proper parameter validation** - Use Pydantic models for tool parameters
- **Handle tool errors gracefully** - Implement retry mechanisms and error recovery

### Environment Variable Configuration with python-dotenv

```python
# Use python-dotenv and pydantic-settings for proper configuration management
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from dotenv import load_dotenv
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LLM Configuration
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_api_key: str = Field(..., description="API key for the LLM provider")
    llm_model: str = Field(default="gpt-4", description="Model name to use")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1", 
        description="Base URL for the LLM API"
    )

def load_settings() -> Settings:
    """Load settings with proper error handling and environment loading."""
    # Load environment variables from .env file
    load_dotenv()
    
    try:
        return Settings()
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "llm_api_key" in str(e).lower():
            error_msg += "\nMake sure to set LLM_API_KEY in your .env file"
        raise ValueError(error_msg) from e

def get_llm_model():
    """Get configured LLM model with proper environment loading."""
    settings = load_settings()
    provider = OpenAIProvider(
        base_url=settings.llm_base_url, 
        api_key=settings.llm_api_key
    )
    return OpenAIModel(settings.llm_model, provider=provider)
```

### Testing Standards for AI Agents

- **Use TestModel for development** - Fast validation without API calls
- **Use FunctionModel for custom behavior** - Control agent responses in tests
- **Use Agent.override() for testing** - Replace models in test contexts
- **Test both sync and async patterns** - Ensure compatibility with different execution modes
- **Test tool validation** - Verify tool parameter schemas and error handling

## ✅ Task Management for AI Development

- **Break agent development into clear steps** with specific completion criteria
- **Mark tasks complete immediately** after finishing agent implementations
- **Update task status in real-time** as agent development progresses
- **Test agent behavior** before marking implementation tasks complete

## 📎 Pydantic AI Coding Standards

### Agent Architecture

```python
# Follow main_agent_reference patterns - no result_type unless structured output needed
from pydantic_ai import Agent, RunContext
from dataclasses import dataclass
from .settings import load_settings

@dataclass
class AgentDependencies:
    """Dependencies for agent execution"""
    api_key: str
    session_id: str = None

# Load settings with proper dotenv handling
settings = load_settings()

# Simple agent with string output (default)
agent = Agent(
    get_llm_model(),  # Uses load_settings() internally
    deps_type=AgentDependencies,
    system_prompt="You are a helpful assistant..."
)

@agent.tool
async def example_tool(
    ctx: RunContext[AgentDependencies], 
    query: str
) -> str:
    """Tool with proper context access"""
    return await external_api_call(ctx.deps.api_key, query)
```
