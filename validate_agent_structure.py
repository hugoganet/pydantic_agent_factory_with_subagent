#!/usr/bin/env python3
"""Validation script to verify the Workflow Coordinator Agent structure."""

import os
import sys
from pathlib import Path


def validate_agent_structure():
    """Validate that all required agent files and components exist."""

    agent_path = Path("agents/workflow_coordinator")

    # Check required files
    required_files = [
        "agent.py",
        "models.py",
        "tools.py",
        "dependencies.py",
        "settings.py",
        "providers.py",
        "prompts.py",
        "__init__.py",
        "requirements.txt",
        ".env.example",
        "README.md",
    ]

    # Check planning documents
    planning_files = [
        "planning/INITIAL.md",
        "planning/prompts.md",
        "planning/tools.md",
        "planning/dependencies.md",
    ]

    # Check test files
    test_files = [
        "tests/conftest.py",
        "tests/test_agent.py",
        "tests/test_tools.py",
        "tests/test_integration.py",
        "tests/test_validation.py",
        "tests/VALIDATION_REPORT.md",
    ]

    print("🎪 Workflow Coordinator Agent Structure Validation")
    print("=" * 50)

    all_valid = True

    # Validate main files
    print("\n📁 Main Agent Files:")
    for file in required_files:
        file_path = agent_path / file
        if file_path.exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
            all_valid = False

    # Validate planning documents
    print("\n📋 Planning Documents:")
    for file in planning_files:
        file_path = agent_path / file
        if file_path.exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
            all_valid = False

    # Validate test files
    print("\n🧪 Test Suite:")
    for file in test_files:
        file_path = agent_path / file
        if file_path.exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
            all_valid = False

    # Check Python imports (without executing)
    print("\n🔧 Python Module Validation:")
    try:
        import ast
        agent_file = agent_path / "agent.py"
        with open(agent_file, 'r') as f:
            tree = ast.parse(f.read())

        # Check for required imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module)

        required_imports = ["pydantic_ai", "asyncio", ".models", ".dependencies", ".tools"]
        for imp in required_imports:
            if any(imp in str(i) for i in imports if i):
                print(f"  ✅ Import found: {imp}")
            else:
                print(f"  ⚠️  Import might be missing: {imp}")

        # Check for agent definition
        agent_defined = any(
            isinstance(node, ast.Assign) and
            any(target.id == "workflow_coordinator_agent" for target in node.targets if hasattr(target, 'id'))
            for node in ast.walk(tree)
        )

        if agent_defined:
            print(f"  ✅ Agent 'workflow_coordinator_agent' defined")
        else:
            print(f"  ❌ Agent 'workflow_coordinator_agent' not found")
            all_valid = False

    except Exception as e:
        print(f"  ❌ Failed to parse agent.py: {e}")
        all_valid = False

    # Check model definitions
    print("\n📊 Model Definitions:")
    try:
        models_file = agent_path / "models.py"
        with open(models_file, 'r') as f:
            content = f.read()

        required_models = [
            "CoordinationRequest",
            "AgentHealthCheck",
            "SystemStatus",
            "CoordinationReport",
            "AgentMessage",
            "WorkflowState",
            "AgentHealthStatus",
        ]

        for model in required_models:
            if f"class {model}" in content:
                print(f"  ✅ Model defined: {model}")
            else:
                print(f"  ❌ Model missing: {model}")
                all_valid = False

    except Exception as e:
        print(f"  ❌ Failed to check models.py: {e}")
        all_valid = False

    # Check tool definitions
    print("\n🔨 Tool Definitions:")
    try:
        tools_file = agent_path / "tools.py"
        with open(tools_file, 'r') as f:
            content = f.read()

        required_tools = [
            "check_agent_health",
            "manage_workflow_state",
            "route_agent_message",
        ]

        for tool in required_tools:
            if f"async def {tool}" in content:
                print(f"  ✅ Tool defined: {tool}")
            else:
                print(f"  ❌ Tool missing: {tool}")
                all_valid = False

    except Exception as e:
        print(f"  ❌ Failed to check tools.py: {e}")
        all_valid = False

    # Summary
    print("\n" + "=" * 50)
    if all_valid:
        print("✅ VALIDATION PASSED: All agent components are properly structured!")
        print("\n🎯 The Workflow Coordinator Agent is ready for:")
        print("  • Integration with the research engineering workflow")
        print("  • Monitoring all 7 research agents")
        print("  • Orchestrating complex multi-agent workflows")
        print("  • Managing inter-agent dependencies and communication")
    else:
        print("❌ VALIDATION FAILED: Some components are missing or incorrect.")
        print("Please review the issues above and fix them.")

    return all_valid


if __name__ == "__main__":
    success = validate_agent_structure()
    sys.exit(0 if success else 1)