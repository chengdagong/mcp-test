"""
Tests for the sample MCP server.

Run with:
    cd examples
    pytest test_sample_server.py -v --mcp-config=mcp_servers_sample.yaml
"""

import pytest

from mcp_pytest import (
    CustomAssertion,
    DurationAssertion,
    ErrorAssertion,
    ResultContainsAssertion,
    ResultMatchesAssertion,
    SuccessAssertion,
)


# =============================================================================
# Basic Tool Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_tools(mcp_client):
    """Test that sample server exposes expected tools."""
    tools = await mcp_client.list_tools()

    tool_names = [t.name for t in tools]
    assert "echo" in tool_names
    assert "add" in tool_names
    assert "get_time" in tool_names
    assert "slow_operation" in tool_names
    assert "fail" in tool_names


@pytest.mark.asyncio
async def test_echo_tool(tool_caller):
    """Test the echo tool."""
    result = await tool_caller.call(
        "echo",
        arguments={"message": "Hello, MCP!"},
    )

    assert result.success
    assert "Hello, MCP!" in result.text_content


@pytest.mark.asyncio
async def test_add_tool(tool_caller):
    """Test the add tool."""
    result = await tool_caller.call(
        "add",
        arguments={"a": 5, "b": 3},
    )

    assert result.success
    assert "8" in result.text_content


@pytest.mark.asyncio
async def test_get_time_tool(tool_caller):
    """Test the get_time tool."""
    result = await tool_caller.call("get_time", arguments={})

    assert result.success
    # Should contain ISO format timestamp
    assert "Current time:" in result.text_content


# =============================================================================
# Assertion Tests
# =============================================================================


@pytest.mark.asyncio
async def test_with_success_assertion(tool_caller):
    """Test using SuccessAssertion."""
    result = await tool_caller.call_and_assert(
        "echo",
        arguments={"message": "test"},
        assertions=[SuccessAssertion()],
    )
    assert result.success


@pytest.mark.asyncio
async def test_with_result_contains(tool_caller):
    """Test using ResultContainsAssertion."""
    result = await tool_caller.call_and_assert(
        "echo",
        arguments={"message": "FindMe"},
        assertions=[
            SuccessAssertion(),
            ResultContainsAssertion("FindMe"),
        ],
    )


@pytest.mark.asyncio
async def test_with_regex_assertion(tool_caller):
    """Test using ResultMatchesAssertion."""
    result = await tool_caller.call_and_assert(
        "add",
        arguments={"a": 10, "b": 20},
        assertions=[
            SuccessAssertion(),
            ResultMatchesAssertion(r"Result: \d+"),  # Matches "Result: 30"
        ],
    )


@pytest.mark.asyncio
async def test_with_duration_assertion(tool_caller):
    """Test using DurationAssertion."""
    result = await tool_caller.call_and_assert(
        "echo",
        arguments={"message": "quick"},
        assertions=[
            SuccessAssertion(),
            DurationAssertion(max_seconds=5),  # Should complete in under 5s
        ],
    )


@pytest.mark.asyncio
async def test_with_custom_assertion(tool_caller):
    """Test using CustomAssertion."""
    # Custom assertion that checks the result
    is_echo = CustomAssertion(
        check_func=lambda r: r.text_content.startswith("Echo:"),
        description="Result starts with 'Echo:'",
    )

    result = await tool_caller.call_and_assert(
        "echo",
        arguments={"message": "custom test"},
        assertions=[is_echo],
    )


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
async def test_fail_tool(tool_caller):
    """Test that fail tool returns error."""
    result = await tool_caller.call(
        "fail",
        arguments={"error_message": "Test error"},
        expect_error=True,
    )

    # When expect_error=True, success means the call failed as expected
    assert result.success
    assert not result.is_error or result.error_message is not None


@pytest.mark.asyncio
async def test_nonexistent_tool(tool_caller):
    """Test calling a tool that doesn't exist."""
    result = await tool_caller.call(
        "this_tool_does_not_exist",
        arguments={},
        expect_error=True,
    )

    assert result.success  # Expected to fail


@pytest.mark.asyncio
async def test_error_assertion(tool_caller):
    """Test using ErrorAssertion."""
    result = await tool_caller.call(
        "fail",
        arguments={},
        expect_error=True,
    )

    error_assertion = ErrorAssertion()  # Just expects any error
    assertion_result = error_assertion.check(result)
    # Note: This assertion passes if the call failed


# =============================================================================
# Timeout Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.mcp_timeout(10)
async def test_slow_operation(tool_caller):
    """Test slow operation completes within timeout."""
    result = await tool_caller.call(
        "slow_operation",
        arguments={"delay": 1},  # 1 second delay
    )

    assert result.success
    assert result.duration_seconds >= 1.0


@pytest.mark.asyncio
async def test_slow_operation_with_duration_assertion(tool_caller):
    """Test slow operation with duration assertion."""
    result = await tool_caller.call_and_assert(
        "slow_operation",
        arguments={"delay": 0.5},
        assertions=[
            SuccessAssertion(),
            DurationAssertion(max_seconds=5, min_seconds=0.4),  # Between 0.4 and 5s
        ],
    )


# =============================================================================
# Call History Tests
# =============================================================================


@pytest.mark.asyncio
async def test_call_history(tool_caller):
    """Test that call history is tracked."""
    # Make several calls
    await tool_caller.call("echo", {"message": "first"})
    await tool_caller.call("echo", {"message": "second"})
    await tool_caller.call("add", {"a": 1, "b": 2})

    # Check history
    history = tool_caller.call_history
    assert len(history) == 3

    # Get last call
    last = tool_caller.get_last_call()
    assert last.name == "add"

    # Get calls for specific tool
    echo_calls = tool_caller.get_calls_for_tool("echo")
    assert len(echo_calls) == 2


# =============================================================================
# Multiple Assertions Tests
# =============================================================================


@pytest.mark.asyncio
async def test_multiple_assertions(tool_caller):
    """Test with multiple assertions that all must pass."""
    result = await tool_caller.call_and_assert(
        "add",
        arguments={"a": 100, "b": 200},
        assertions=[
            SuccessAssertion(),
            ResultContainsAssertion("300"),
            ResultMatchesAssertion(r"Result: 300"),
            DurationAssertion(max_seconds=10),
            CustomAssertion(
                check_func=lambda r: "Result" in r.text_content,
                description="Contains 'Result' keyword",
            ),
        ],
    )

    assert result.success
    assert "300" in result.text_content
