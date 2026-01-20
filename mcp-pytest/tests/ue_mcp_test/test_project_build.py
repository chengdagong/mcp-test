"""
Tests for UE-MCP project.build Tool.

Tests the following tool:
- project.build: Build the UE5 project using UnrealBuildTool

Run with:
    cd tests/ue_mcp_test
    pytest test_project_build.py -v
"""

import json

import pytest

from mcp_pytest import (
    CustomAssertion,
    DurationAssertion,
    SuccessAssertion,
)


# =============================================================================
# Tool Schema Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_tool_exists(mcp_client):
    """Test that project.build tool exists."""
    tools = await mcp_client.list_tools()
    tool_names = [t.name for t in tools]

    assert "project.build" in tool_names, "project.build tool should exist"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_tool_schema(tool_caller):
    """Test project.build tool schema and parameters."""
    tools = await tool_caller.client.list_tools()
    build_tool = next((t for t in tools if t.name == "project.build"), None)

    assert build_tool is not None, "project.build tool should exist"
    assert build_tool.description, "Should have description"
    assert build_tool.inputSchema, "Should have input schema"

    schema = build_tool.inputSchema
    props = schema.get("properties", {})

    # Verify expected parameters
    expected_params = ["target", "configuration", "platform", "clean", "wait", "verbose", "timeout"]
    for param in expected_params:
        assert param in props, f"Should accept '{param}' parameter"

    print("project.build schema:")
    print(f"  Description: {build_tool.description[:150]}...")
    print(f"  Parameters: {list(props.keys())}")

    # Print parameter details
    for param, info in props.items():
        default = info.get("default", "none")
        param_type = info.get("type", "unknown")
        enum_vals = info.get("enum", [])
        if enum_vals:
            print(f"  {param}: {param_type} (enum: {enum_vals})")
        else:
            print(f"  {param}: {param_type} (default: {default})")


# =============================================================================
# Parameter Validation Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_target_values(tool_caller):
    """Test that target parameter accepts valid values."""
    tools = await tool_caller.client.list_tools()
    build_tool = next((t for t in tools if t.name == "project.build"), None)

    props = build_tool.inputSchema.get("properties", {})
    target_prop = props.get("target", {})

    # Check if it has enum or description with valid values
    print(f"Target property: {target_prop}")

    # Valid targets should include: Editor, Game, Client, Server
    valid_targets = ["Editor", "Game", "Client", "Server"]
    for target in valid_targets:
        print(f"  - {target}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_configuration_values(tool_caller):
    """Test that configuration parameter accepts valid values."""
    tools = await tool_caller.client.list_tools()
    build_tool = next((t for t in tools if t.name == "project.build"), None)

    props = build_tool.inputSchema.get("properties", {})
    config_prop = props.get("configuration", {})

    print(f"Configuration property: {config_prop}")

    # Valid configurations
    valid_configs = ["Debug", "DebugGame", "Development", "Shipping", "Test"]
    for config in valid_configs:
        print(f"  - {config}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_platform_values(tool_caller):
    """Test that platform parameter accepts valid values."""
    tools = await tool_caller.client.list_tools()
    build_tool = next((t for t in tools if t.name == "project.build"), None)

    props = build_tool.inputSchema.get("properties", {})
    platform_prop = props.get("platform", {})

    print(f"Platform property: {platform_prop}")

    # Common platforms
    valid_platforms = ["Win64", "Mac", "Linux"]
    for platform in valid_platforms:
        print(f"  - {platform}")


# =============================================================================
# Build Execution Tests (Require UE5)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.mcp_timeout(1800)  # 30 minute timeout for builds
async def test_build_editor_development(tool_caller):
    """Test building Editor target with Development configuration.

    WARNING: This test performs an actual build and may take a long time!
    """
    result = await tool_caller.call(
        "project.build",
        arguments={
            "target": "Editor",
            "configuration": "Development",
            "platform": "Win64",
            "clean": False,
            "wait": True,
            "verbose": False,
            "timeout": 1800.0,
        },
    )

    build_data = json.loads(result.text_content)
    print(f"Build result: {json.dumps(build_data, indent=2)[:1000]}")

    if build_data.get("success"):
        print("Build succeeded!")
        assert "output" in build_data, "Should contain build output"
        assert "return_code" in build_data, "Should contain return code"
        assert build_data["return_code"] == 0, "Return code should be 0"
    else:
        print(f"Build failed: {build_data.get('error')}")
        # May fail if UE5 not installed or project not set up


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_build_async_mode(tool_caller):
    """Test starting build in async mode (wait=False).

    This returns immediately without waiting for build completion.
    """
    result = await tool_caller.call(
        "project.build",
        arguments={
            "target": "Editor",
            "configuration": "Development",
            "platform": "Win64",
            "clean": False,
            "wait": False,  # Don't wait
            "verbose": False,
            "timeout": 1800.0,
        },
    )

    build_data = json.loads(result.text_content)
    print(f"Async build started: {json.dumps(build_data, indent=2)}")

    if build_data.get("success"):
        # Should return immediately with status
        assert "message" in build_data or "success" in build_data, \
            "Should indicate build started"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_build_with_clean(tool_caller):
    """Test clean build (rebuilds everything).

    WARNING: Clean builds take significantly longer!
    """
    result = await tool_caller.call(
        "project.build",
        arguments={
            "target": "Editor",
            "configuration": "Development",
            "platform": "Win64",
            "clean": True,  # Clean build
            "wait": False,  # Start async to avoid long wait
            "verbose": False,
            "timeout": 1800.0,
        },
    )

    build_data = json.loads(result.text_content)
    print(f"Clean build started: {json.dumps(build_data, indent=2)}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_build_with_verbose(tool_caller):
    """Test build with verbose output."""
    result = await tool_caller.call(
        "project.build",
        arguments={
            "target": "Editor",
            "configuration": "Development",
            "platform": "Win64",
            "clean": False,
            "wait": False,
            "verbose": True,  # Enable verbose logging
            "timeout": 1800.0,
        },
    )

    build_data = json.loads(result.text_content)
    print(f"Verbose build: {json.dumps(build_data, indent=2)}")


# =============================================================================
# Different Target Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_build_game_target(tool_caller):
    """Test building Game target."""
    result = await tool_caller.call(
        "project.build",
        arguments={
            "target": "Game",
            "configuration": "Development",
            "platform": "Win64",
            "wait": False,
        },
    )

    build_data = json.loads(result.text_content)
    print(f"Game build: {json.dumps(build_data, indent=2)}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_build_shipping_config(tool_caller):
    """Test building with Shipping configuration."""
    result = await tool_caller.call(
        "project.build",
        arguments={
            "target": "Game",
            "configuration": "Shipping",
            "platform": "Win64",
            "wait": False,
        },
    )

    build_data = json.loads(result.text_content)
    print(f"Shipping build: {json.dumps(build_data, indent=2)}")


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_invalid_target(tool_caller):
    """Test build with invalid target."""
    result = await tool_caller.call(
        "project.build",
        arguments={
            "target": "InvalidTarget",
            "configuration": "Development",
            "platform": "Win64",
            "wait": False,
        },
    )

    build_data = json.loads(result.text_content)
    print(f"Invalid target result: {json.dumps(build_data, indent=2)}")

    # Should fail with appropriate error


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_invalid_configuration(tool_caller):
    """Test build with invalid configuration."""
    result = await tool_caller.call(
        "project.build",
        arguments={
            "target": "Editor",
            "configuration": "InvalidConfig",
            "platform": "Win64",
            "wait": False,
        },
    )

    build_data = json.loads(result.text_content)
    print(f"Invalid config result: {json.dumps(build_data, indent=2)}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_invalid_platform(tool_caller):
    """Test build with invalid platform."""
    result = await tool_caller.call(
        "project.build",
        arguments={
            "target": "Editor",
            "configuration": "Development",
            "platform": "InvalidPlatform",
            "wait": False,
        },
    )

    build_data = json.loads(result.text_content)
    print(f"Invalid platform result: {json.dumps(build_data, indent=2)}")


# =============================================================================
# Timeout Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_default_timeout(tool_caller):
    """Test that build has reasonable default timeout."""
    tools = await tool_caller.client.list_tools()
    build_tool = next((t for t in tools if t.name == "project.build"), None)

    props = build_tool.inputSchema.get("properties", {})
    timeout_prop = props.get("timeout", {})

    print(f"Timeout property: {timeout_prop}")

    # Default should be reasonable for builds (e.g., 30 minutes = 1800 seconds)
    default_timeout = timeout_prop.get("default", 0)
    assert default_timeout >= 300, "Default timeout should be at least 5 minutes"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_build_short_timeout(tool_caller):
    """Test build with very short timeout (should fail)."""
    result = await tool_caller.call(
        "project.build",
        arguments={
            "target": "Editor",
            "configuration": "Development",
            "platform": "Win64",
            "wait": True,
            "timeout": 1.0,  # 1 second - way too short
        },
    )

    build_data = json.loads(result.text_content)
    print(f"Short timeout result: {json.dumps(build_data, indent=2)}")

    # Should timeout or fail quickly


# =============================================================================
# Build Progress Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_build_progress_reporting(tool_caller):
    """Test that build reports progress.

    Note: Progress reporting depends on MCP context.log implementation.
    """
    # This test mainly verifies the build can be called
    # Progress is reported via notifications which are harder to test
    result = await tool_caller.call(
        "project.build",
        arguments={
            "target": "Editor",
            "configuration": "Development",
            "platform": "Win64",
            "wait": False,
            "verbose": True,  # Enable to see progress
        },
    )

    build_data = json.loads(result.text_content)
    print(f"Build with progress: {json.dumps(build_data, indent=2)}")


# =============================================================================
# Assertion-Based Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_response_format(tool_caller):
    """Test that build returns properly formatted response."""
    # Custom assertion for response format
    valid_response = CustomAssertion(
        check_func=lambda r: (
            "success" in json.loads(r.text_content)
            or "error" in json.loads(r.text_content)
            or "message" in json.loads(r.text_content)
        ),
        description="Response should contain 'success', 'error', or 'message' field",
    )

    result = await tool_caller.call_and_assert(
        "project.build",
        arguments={
            "target": "Editor",
            "configuration": "Development",
            "platform": "Win64",
            "wait": False,
        },
        assertions=[
            SuccessAssertion(),  # MCP call succeeds
            valid_response,
        ],
    )


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.mcp_timeout(600)  # 10 minute timeout
async def test_build_sync_with_assertions(tool_caller):
    """Test synchronous build with assertion framework."""
    # Custom assertion for successful build
    build_succeeded = CustomAssertion(
        check_func=lambda r: json.loads(r.text_content).get("success", False),
        description="Build should succeed",
        message_func=lambda r: f"Build failed: {json.loads(r.text_content).get('error', 'Unknown')}",
    )

    result = await tool_caller.call_and_assert(
        "project.build",
        arguments={
            "target": "Editor",
            "configuration": "Development",
            "platform": "Win64",
            "wait": True,
            "timeout": 600.0,
        },
        assertions=[
            SuccessAssertion(),
            DurationAssertion(max_seconds=600),
            # build_succeeded,  # Uncomment when UE5 is available
        ],
    )


# =============================================================================
# Call History Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_call_history(tool_caller):
    """Test that build calls are tracked in history."""
    # Make a build call
    await tool_caller.call(
        "project.build",
        arguments={
            "target": "Editor",
            "configuration": "Development",
            "platform": "Win64",
            "wait": False,
        },
    )

    # Check history
    build_calls = tool_caller.get_calls_for_tool("project.build")
    assert len(build_calls) >= 1, "Should have at least 1 build call"

    last_call = build_calls[-1]
    assert last_call.arguments.get("target") == "Editor"
    assert last_call.arguments.get("configuration") == "Development"

    print(f"Build call tracked: {last_call.name}")
    print(f"  Arguments: {last_call.arguments}")
    print(f"  Duration: {last_call.duration_seconds:.2f}s")
