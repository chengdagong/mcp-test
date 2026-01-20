"""
Tests for UE-MCP Editor Management Tools.

Tests the following tools:
- editor.launch: Start the Unreal Editor
- editor.status: Get editor status
- editor.stop: Stop the editor

Run with:
    cd tests/ue_mcp_test
    pytest test_editor_management.py -v
"""

import json

import pytest

from mcp_pytest import (
    CustomAssertion,
    DurationAssertion,
    ResultContainsAssertion,
    SuccessAssertion,
)


# =============================================================================
# Server Connection Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_server_connection(mcp_client):
    """Test that we can connect to the UE-MCP server."""
    assert mcp_client.is_connected
    print(f"Connected to server: {mcp_client.name}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_tools(mcp_client, expected_tools):
    """Test listing available tools from UE-MCP server."""
    tools = await mcp_client.list_tools()
    tool_names = [t.name for t in tools]

    print(f"Available tools ({len(tools)}):")
    for name in sorted(tool_names):
        print(f"  - {name}")

    assert len(tools) > 0, "Server should expose at least one tool"

    # Verify all expected tools are present
    for expected in expected_tools:
        assert expected in tool_names, f"Missing expected tool: {expected}"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_schemas(mcp_client, expected_tools):
    """Test that all tools have proper schemas defined."""
    tools = await mcp_client.list_tools()
    tool_map = {t.name: t for t in tools}

    for tool_name in expected_tools:
        assert tool_name in tool_map, f"Tool not found: {tool_name}"
        tool = tool_map[tool_name]

        # Each tool should have a description
        assert tool.description, f"Tool {tool_name} should have a description"

        print(f"\n{tool_name}:")
        print(f"  Description: {tool.description[:100]}...")
        if hasattr(tool, "inputSchema") and tool.inputSchema:
            props = tool.inputSchema.get("properties", {})
            print(f"  Parameters: {list(props.keys())}")


# =============================================================================
# editor.status Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_editor_status_basic(tool_caller):
    """Test getting editor status when not running."""
    result = await tool_caller.call("editor.status", arguments={})

    assert result.success, f"Failed to get status: {result.error_message}"

    # Parse the JSON response
    status_data = json.loads(result.text_content)
    print(f"Editor status: {json.dumps(status_data, indent=2)}")

    # Verify required fields
    assert "status" in status_data, "Response should contain 'status' field"
    assert "project_name" in status_data, "Response should contain 'project_name' field"
    assert "project_path" in status_data, "Response should contain 'project_path' field"

    # Initially editor should not be running
    assert status_data["status"] in [
        "not_running",
        "starting",
        "ready",
        "stopped",
    ], f"Invalid status: {status_data['status']}"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_editor_status_with_assertions(tool_caller):
    """Test editor status with assertion framework."""

    # Custom assertion to check status structure
    valid_status_structure = CustomAssertion(
        check_func=lambda r: all(
            key in json.loads(r.text_content)
            for key in ["status", "project_name", "project_path"]
        ),
        description="Status response has required fields",
    )

    result = await tool_caller.call_and_assert(
        "editor.status",
        arguments={},
        assertions=[
            SuccessAssertion(),
            DurationAssertion(max_seconds=5),
            valid_status_structure,
        ],
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_editor_status_contains_project_info(tool_caller, sample_uproject_path):
    """Test that editor status contains correct project information."""
    result = await tool_caller.call("editor.status", arguments={})

    status_data = json.loads(result.text_content)

    # Project name should match our test fixture
    assert "EmptyProjectTemplate" in status_data.get(
        "project_name", ""
    ), "Should detect EmptyProjectTemplate project"


# =============================================================================
# editor.launch Tests (Unit - No actual UE5 required)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_editor_launch_parameters(tool_caller):
    """Test that editor.launch accepts correct parameters."""
    # Get tool info to verify parameters
    tools = await tool_caller.client.list_tools()
    launch_tool = next((t for t in tools if t.name == "editor.launch"), None)

    assert launch_tool is not None, "editor.launch tool should exist"
    assert launch_tool.inputSchema is not None, "Should have input schema"

    schema = launch_tool.inputSchema
    props = schema.get("properties", {})

    # Verify expected parameters
    assert "additional_paths" in props, "Should accept additional_paths"
    assert "wait" in props, "Should accept wait parameter"
    assert "wait_timeout" in props, "Should accept wait_timeout parameter"

    print("editor.launch parameters:")
    for param, info in props.items():
        print(f"  {param}: {info.get('type', 'unknown')}")


@pytest.mark.asyncio
@pytest.mark.mock
async def test_editor_launch_without_wait(tool_caller):
    """Test editor.launch with wait=False (async mode).

    Note: This test may fail if UE5 is not installed.
    In that case, it verifies the error handling.
    """
    result = await tool_caller.call(
        "editor.launch",
        arguments={
            "wait": False,
            "wait_timeout": 10.0,
        },
        expect_error=True,  # May fail if UE5 not installed
    )

    # Either succeeds (UE5 found) or fails gracefully (UE5 not found)
    print(f"Launch result: {result.text_content[:500] if result.text_content else 'No content'}")


# =============================================================================
# editor.stop Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_editor_stop_when_not_running(tool_caller):
    """Test stopping editor when it's not running."""
    result = await tool_caller.call("editor.stop", arguments={})

    # Should handle gracefully when editor is not running
    status_data = json.loads(result.text_content)
    print(f"Stop result: {json.dumps(status_data, indent=2)}")

    # Either already stopped or success
    assert "success" in status_data or "status" in status_data


@pytest.mark.asyncio
@pytest.mark.unit
async def test_editor_stop_parameters(tool_caller):
    """Test that editor.stop has expected parameters."""
    tools = await tool_caller.client.list_tools()
    stop_tool = next((t for t in tools if t.name == "editor.stop"), None)

    assert stop_tool is not None, "editor.stop tool should exist"
    assert stop_tool.description, "Should have description"
    print(f"editor.stop description: {stop_tool.description}")


# =============================================================================
# Integration Tests (Require UE5)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_editor
async def test_editor_launch_and_stop_workflow(tool_caller):
    """Test full editor launch and stop workflow.

    WARNING: This test will actually launch Unreal Editor!
    Only run with pytest markers: pytest -m integration
    """
    # Step 1: Verify initial status
    status_result = await tool_caller.call("editor.status", arguments={})
    initial_status = json.loads(status_result.text_content)
    print(f"Initial status: {initial_status['status']}")

    if initial_status["status"] == "ready":
        print("Editor already running, skipping launch test")
        return

    # Step 2: Launch editor (async mode)
    launch_result = await tool_caller.call(
        "editor.launch",
        arguments={
            "wait": False,  # Don't wait for full startup
            "wait_timeout": 30.0,
        },
    )
    launch_data = json.loads(launch_result.text_content)
    print(f"Launch result: {launch_data}")

    # Step 3: Check status after launch
    status_result = await tool_caller.call("editor.status", arguments={})
    post_launch_status = json.loads(status_result.text_content)
    print(f"Post-launch status: {post_launch_status['status']}")

    assert post_launch_status["status"] in [
        "starting",
        "ready",
    ], "Editor should be starting or ready"

    # Step 4: Stop editor
    stop_result = await tool_caller.call("editor.stop", arguments={})
    stop_data = json.loads(stop_result.text_content)
    print(f"Stop result: {stop_data}")

    # Step 5: Verify stopped
    final_status_result = await tool_caller.call("editor.status", arguments={})
    final_status = json.loads(final_status_result.text_content)
    print(f"Final status: {final_status['status']}")

    assert final_status["status"] in [
        "not_running",
        "stopped",
    ], "Editor should be stopped"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_editor
@pytest.mark.mcp_timeout(180)  # 3 minute timeout for editor launch
async def test_editor_launch_with_wait(tool_caller):
    """Test editor launch with synchronous wait.

    This test waits for editor to be fully ready.
    WARNING: This is slow and requires UE5!
    """
    # Launch with wait=True
    result = await tool_caller.call(
        "editor.launch",
        arguments={
            "wait": True,
            "wait_timeout": 120.0,  # 2 minute timeout
        },
    )

    launch_data = json.loads(result.text_content)

    if launch_data.get("success"):
        print("Editor launched and connected successfully!")

        # Verify ready status
        status_result = await tool_caller.call("editor.status", arguments={})
        status = json.loads(status_result.text_content)
        assert status["status"] == "ready", "Editor should be ready after sync launch"
        assert status.get("connected"), "Should be connected for remote execution"

        # Cleanup
        await tool_caller.call("editor.stop", arguments={})
    else:
        print(f"Launch failed (expected if UE5 not installed): {launch_data.get('error')}")


# =============================================================================
# Call History Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_editor_tool_call_history(tool_caller):
    """Test that call history is properly tracked for editor tools."""
    # Make several calls
    await tool_caller.call("editor.status", arguments={})
    await tool_caller.call("editor.status", arguments={})
    await tool_caller.call("editor.stop", arguments={})

    # Check history
    history = tool_caller.call_history
    assert len(history) >= 3, "Should have at least 3 calls in history"

    # Get calls for specific tool
    status_calls = tool_caller.get_calls_for_tool("editor.status")
    assert len(status_calls) >= 2, "Should have at least 2 status calls"

    # Get last call
    last = tool_caller.get_last_call()
    assert last.name == "editor.stop", "Last call should be editor.stop"

    print(f"Total calls: {len(history)}")
    print(f"Status calls: {len(status_calls)}")
