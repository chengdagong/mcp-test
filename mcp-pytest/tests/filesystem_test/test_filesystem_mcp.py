"""
Tests for Anthropic's official filesystem MCP server.

This tests the mcp-pytest framework using a real MCP server.
Run with:
    cd tests/filesystem_test
    pytest test_filesystem_mcp.py -v

Note: The filesystem MCP server requires absolute paths. All file paths
in this test use the WORKSPACE constant which points to the allowed directory.
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

# The workspace directory that the filesystem MCP server has access to
# All file paths must be absolute paths within this directory
WORKSPACE = "D:/Code/mcp-test/mcp-pytest/tests/filesystem_test/workspace"


# =============================================================================
# Basic Connection Tests
# =============================================================================


@pytest.mark.asyncio
async def test_server_connection(mcp_client):
    """Test that we can connect to the filesystem MCP server."""
    assert mcp_client.is_connected
    print(f"Connected to server: {mcp_client.name}")


@pytest.mark.asyncio
async def test_list_tools(mcp_client):
    """Test listing available tools from filesystem server."""
    tools = await mcp_client.list_tools()

    # Filesystem server should have these tools
    tool_names = [t.name for t in tools]
    print(f"Available tools: {tool_names}")

    assert len(tools) > 0, "Server should expose at least one tool"

    # Common filesystem tools
    expected_tools = ["read_file", "write_file", "list_directory"]
    for expected in expected_tools:
        assert expected in tool_names, f"Missing expected tool: {expected}"


# =============================================================================
# Read File Tests
# =============================================================================


@pytest.mark.asyncio
async def test_read_file_basic(tool_caller):
    """Test reading an existing file."""
    result = await tool_caller.call(
        "read_file",
        arguments={"path": f"{WORKSPACE}/sample.txt"},
    )

    assert result.success, f"Failed to read file: {result.error_message}"
    assert "Hello" in result.text_content
    assert "sample file" in result.text_content


@pytest.mark.asyncio
async def test_read_file_with_assertions(tool_caller):
    """Test reading file with multiple assertions."""
    result = await tool_caller.call_and_assert(
        "read_file",
        arguments={"path": f"{WORKSPACE}/sample.txt"},
        assertions=[
            SuccessAssertion(),
            ResultContainsAssertion("Hello"),
            ResultContainsAssertion("Line 2"),
            ResultMatchesAssertion(r"\d+"),  # Should contain numbers
            DurationAssertion(max_seconds=10),
        ],
    )

    print(f"File content:\n{result.text_content}")


@pytest.mark.asyncio
async def test_read_nonexistent_file(tool_caller):
    """Test reading a file that doesn't exist."""
    result = await tool_caller.call(
        "read_file",
        arguments={"path": f"{WORKSPACE}/nonexistent_file_12345.txt"},
        expect_error=True,
    )

    # The call should fail (expect_error=True means success if it fails)
    assert result.success, "Reading nonexistent file should fail"
    print(f"Error message: {result.error_message}")


# =============================================================================
# Write File Tests
# =============================================================================


@pytest.mark.asyncio
async def test_write_file(tool_caller, file_tracker):
    """Test writing a new file."""
    test_content = "This is a test file created by mcp-pytest.\nLine 2."
    test_file = f"{WORKSPACE}/test_output.txt"

    # Track the file for cleanup
    file_tracker.track(test_file, "test_write_file")

    result = await tool_caller.call(
        "write_file",
        arguments={
            "path": test_file,
            "content": test_content,
        },
    )

    assert result.success, f"Failed to write file: {result.error_message}"

    # Verify by reading back
    read_result = await tool_caller.call(
        "read_file",
        arguments={"path": test_file},
    )

    assert read_result.success
    assert "test file created by mcp-pytest" in read_result.text_content


@pytest.mark.asyncio
async def test_write_and_read_with_assertions(tool_caller, file_tracker):
    """Test write and read workflow with assertions."""
    test_file = f"{WORKSPACE}/assertion_test.txt"

    # Track for cleanup
    file_tracker.track(test_file, "test_write_and_read_with_assertions")

    # Write
    write_result = await tool_caller.call_and_assert(
        "write_file",
        arguments={
            "path": test_file,
            "content": "Assertion test content: SUCCESS_MARKER",
        },
        assertions=[
            SuccessAssertion(),
            DurationAssertion(max_seconds=5),
        ],
    )

    # Read back
    read_result = await tool_caller.call_and_assert(
        "read_file",
        arguments={"path": test_file},
        assertions=[
            SuccessAssertion(),
            ResultContainsAssertion("SUCCESS_MARKER"),
        ],
    )


# =============================================================================
# List Directory Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_directory(tool_caller):
    """Test listing directory contents."""
    result = await tool_caller.call(
        "list_directory",
        arguments={"path": WORKSPACE},
    )

    assert result.success, f"Failed to list directory: {result.error_message}"
    assert "sample.txt" in result.text_content
    print(f"Directory listing:\n{result.text_content}")


@pytest.mark.asyncio
async def test_list_directory_with_assertions(tool_caller):
    """Test list directory with assertions."""
    result = await tool_caller.call_and_assert(
        "list_directory",
        arguments={"path": WORKSPACE},
        assertions=[
            SuccessAssertion(),
            ResultContainsAssertion("sample.txt"),
            DurationAssertion(max_seconds=5),
        ],
    )


# =============================================================================
# Custom Assertion Tests
# =============================================================================


@pytest.mark.asyncio
async def test_custom_assertion(tool_caller):
    """Test using custom assertion function."""
    # Custom assertion that checks line count
    has_multiple_lines = CustomAssertion(
        check_func=lambda r: r.text_content.count("\n") >= 2,
        description="File has at least 3 lines",
    )

    result = await tool_caller.call_and_assert(
        "read_file",
        arguments={"path": f"{WORKSPACE}/sample.txt"},
        assertions=[
            SuccessAssertion(),
            has_multiple_lines,
        ],
    )


@pytest.mark.asyncio
async def test_complex_custom_assertion(tool_caller):
    """Test with a more complex custom assertion."""
    # Check that content matches expected format
    valid_sample_file = CustomAssertion(
        check_func=lambda r: (
            "Hello" in r.text_content and "Line 2" in r.text_content and "12345" in r.text_content
        ),
        description="Sample file has expected structure",
        message_func=lambda r: f"Content did not match expected structure. Got: {r.text_content[:100]}...",
    )

    result = await tool_caller.call_and_assert(
        "read_file",
        arguments={"path": f"{WORKSPACE}/sample.txt"},
        assertions=[valid_sample_file],
    )


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
async def test_error_assertion(tool_caller):
    """Test ErrorAssertion for expected failures."""
    result = await tool_caller.call(
        "read_file",
        arguments={"path": f"{WORKSPACE}/this_file_does_not_exist.txt"},
        expect_error=True,
    )

    # Verify error using ErrorAssertion
    error_check = ErrorAssertion()  # Any error
    assertion_result = error_check.check(result)
    print(f"ErrorAssertion result: {assertion_result}")


@pytest.mark.asyncio
async def test_invalid_tool_call(tool_caller):
    """Test calling a tool that doesn't exist."""
    result = await tool_caller.call(
        "nonexistent_tool_xyz",
        arguments={},
        expect_error=True,
    )

    assert result.success, "Calling nonexistent tool should fail"


# =============================================================================
# Timeout Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.mcp_timeout(5)  # 5 second timeout
async def test_with_custom_timeout(tool_caller):
    """Test with custom timeout marker."""
    result = await tool_caller.call(
        "read_file",
        arguments={"path": f"{WORKSPACE}/sample.txt"},
    )

    assert result.success
    assert result.duration_seconds < 5


# =============================================================================
# Call History Tests
# =============================================================================


@pytest.mark.asyncio
async def test_call_history_tracking(tool_caller):
    """Test that call history is properly tracked."""
    # Make several calls
    await tool_caller.call("list_directory", {"path": WORKSPACE})
    await tool_caller.call("read_file", {"path": f"{WORKSPACE}/sample.txt"})
    await tool_caller.call("read_file", {"path": f"{WORKSPACE}/sample.txt"})

    # Check history
    history = tool_caller.call_history
    assert len(history) >= 3

    # Get last call
    last = tool_caller.get_last_call()
    assert last is not None
    assert last.name == "read_file"

    # Get calls for specific tool
    read_calls = tool_caller.get_calls_for_tool("read_file")
    assert len(read_calls) >= 2

    print(f"Total calls: {len(history)}")
    print(f"Read file calls: {len(read_calls)}")


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_full_workflow(tool_caller, file_tracker):
    """Test a complete file workflow: create, read, verify, list."""
    filename = "workflow_test.txt"
    filepath = f"{WORKSPACE}/{filename}"
    content = "Workflow test: Step 1 - Created\nStep 2 - Content added"

    # Track for cleanup
    file_tracker.track(filepath, "test_full_workflow")

    # Step 1: Write file
    write_result = await tool_caller.call_and_assert(
        "write_file",
        arguments={"path": filepath, "content": content},
        assertions=[SuccessAssertion()],
    )
    print("Step 1: File written")

    # Step 2: Verify in directory listing
    list_result = await tool_caller.call_and_assert(
        "list_directory",
        arguments={"path": WORKSPACE},
        assertions=[
            SuccessAssertion(),
            ResultContainsAssertion(filename),
        ],
    )
    print("Step 2: File visible in directory")

    # Step 3: Read and verify content
    read_result = await tool_caller.call_and_assert(
        "read_file",
        arguments={"path": filepath},
        assertions=[
            SuccessAssertion(),
            ResultContainsAssertion("Workflow test"),
            ResultContainsAssertion("Step 1"),
            ResultContainsAssertion("Step 2"),
        ],
    )
    print("Step 3: Content verified")

    # Summary
    print(f"\nWorkflow completed successfully!")
    print(f"Total tool calls: {len(tool_caller.call_history)}")
