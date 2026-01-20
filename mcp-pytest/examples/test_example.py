"""
Example test file demonstrating mcp-pytest usage.

These tests assume you have configured MCP servers in mcp_servers.yaml.
Adjust the server names and tool calls to match your actual MCP server.
"""

import pytest

from mcp_pytest import (
    CustomAssertion,
    DurationAssertion,
    ErrorAssertion,
    ResultContainsAssertion,
    SuccessAssertion,
)


# =============================================================================
# Basic Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_tools(mcp_client):
    """Test that server exposes tools."""
    tools = await mcp_client.list_tools()

    # Check that at least one tool is available
    assert len(tools) > 0, "Server should expose at least one tool"

    # Print available tools for debugging
    tool_names = [t.name for t in tools]
    print(f"Available tools: {tool_names}")


@pytest.mark.asyncio
async def test_tool_call_basic(tool_caller):
    """Test basic tool call using tool_caller fixture."""
    # List available tools first
    tools = await tool_caller.list_tools()

    if not tools:
        pytest.skip("No tools available")

    # Call the first available tool (adjust for your server)
    first_tool = tools[0]
    result = await tool_caller.call(first_tool, arguments={})

    # Basic assertions
    assert result.duration_seconds >= 0
    print(f"Tool '{first_tool}' returned: {result.text_content[:200]}")


# =============================================================================
# Tests with Assertions
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.mcp_timeout(60)  # Override timeout for slow operations
async def test_tool_with_assertions(tool_caller):
    """Test tool call with multiple assertions."""
    # Skip if no tools available
    tools = await tool_caller.list_tools()
    if not tools:
        pytest.skip("No tools available")

    result = await tool_caller.call_and_assert(
        tools[0],
        arguments={},
        assertions=[
            SuccessAssertion(),  # Must succeed
            DurationAssertion(max_seconds=30),  # Must complete within 30s
        ],
    )

    # Result is returned for further inspection
    print(f"Call completed in {result.duration_seconds:.2f}s")


@pytest.mark.asyncio
async def test_custom_assertion(tool_caller):
    """Test with custom assertion function."""
    tools = await tool_caller.list_tools()
    if not tools:
        pytest.skip("No tools available")

    # Custom assertion that checks result content
    has_content = CustomAssertion(
        check_func=lambda r: len(r.text_content) > 0 or r.success,
        description="Result has content or succeeded",
    )

    result = await tool_caller.call_and_assert(
        tools[0],
        arguments={},
        assertions=[has_content],
    )


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
async def test_error_handling(tool_caller):
    """Test that invalid calls are handled properly."""
    # Try to call a non-existent tool
    result = await tool_caller.call(
        "nonexistent_tool_that_should_not_exist",
        arguments={},
        expect_error=True,  # We expect this to fail
    )

    # When expect_error=True, success means the call failed as expected
    assert result.success, "Call to nonexistent tool should fail"
    assert result.error_message is not None


@pytest.mark.asyncio
async def test_error_pattern_matching(tool_caller):
    """Test error message pattern matching."""
    result = await tool_caller.call(
        "nonexistent_tool",
        arguments={},
        expect_error=True,
    )

    # Use ErrorAssertion to verify error message pattern
    error_assertion = ErrorAssertion(r"not found|unknown|invalid")
    assertion_result = error_assertion.check(result)

    # This might fail if the error message doesn't match the pattern
    # Adjust the pattern based on your server's error messages
    print(f"Error message: {result.error_message}")


# =============================================================================
# Multi-Server Tests
# =============================================================================


@pytest.mark.asyncio
async def test_multi_server_access(mcp_server_manager):
    """Test accessing multiple servers."""
    # Get available servers
    server_names = mcp_server_manager.server_names

    if len(server_names) < 2:
        pytest.skip("Need at least 2 servers for multi-server test")

    # Access each server
    for name in server_names:
        session = mcp_server_manager.get_session(name)
        if session:
            tools = await session.list_tools()
            print(f"Server '{name}' has {len(tools)} tools")


@pytest.mark.asyncio
@pytest.mark.mcp_server("filesystem-mcp")  # Specify server by marker
async def test_specific_server(mcp_server):
    """Test a specific server using marker."""
    tools = await mcp_server.list_tools()
    print(f"Server has {len(tools)} tools")


# =============================================================================
# Cleanup Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.mcp_cleanup("/tmp/test_output")  # Paths to clean after test
async def test_with_cleanup(tool_caller, file_tracker):
    """Test that tracks and cleans up files."""
    # Track a directory for cleanup
    file_tracker.start_watching("/tmp/test_output", "test_with_cleanup")

    # Your test logic here...
    # Any files created in /tmp/test_output will be automatically cleaned up

    tools = await tool_caller.list_tools()
    print(f"Available tools: {tools}")

    # Stop watching and cleanup happens automatically via fixture


@pytest.mark.asyncio
@pytest.mark.mcp_skip_cleanup  # Disable cleanup for debugging
async def test_without_cleanup(tool_caller):
    """Test that skips cleanup (for debugging)."""
    result = await tool_caller.call(
        "some_tool",
        arguments={},
        expect_error=True,  # May fail if tool doesn't exist
    )
    # Files won't be cleaned up after this test


# =============================================================================
# Call History Tests
# =============================================================================


@pytest.mark.asyncio
async def test_call_history(tool_caller):
    """Test that call history is tracked."""
    tools = await tool_caller.list_tools()
    if not tools:
        pytest.skip("No tools available")

    # Make multiple calls
    await tool_caller.call(tools[0], arguments={}, expect_error=True)
    await tool_caller.call(tools[0], arguments={}, expect_error=True)

    # Check history
    history = tool_caller.call_history
    assert len(history) >= 2, "Should have at least 2 calls in history"

    # Get last call
    last_call = tool_caller.get_last_call()
    assert last_call is not None

    # Get calls for specific tool
    tool_calls = tool_caller.get_calls_for_tool(tools[0])
    assert len(tool_calls) >= 2
