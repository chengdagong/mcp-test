"""Test with custom fixtures demonstrating different scoping strategies."""

import pytest
from pathlib import Path
from typing import AsyncGenerator

from mcp_pytest.config.loader import ConfigLoader
from mcp_pytest.client.session import MCPClientSession
from mcp_pytest.client.tool_caller import ToolCaller
from mcp_pytest.cleanup.tracker import FileTracker

# The workspace directory that the filesystem MCP server has access to
WORKSPACE = "D:/Code/mcp-test/mcp-pytest/tests/filesystem_test/workspace"


@pytest.fixture(scope="module")
def server_config():
    """Load server config directly."""
    root_dir = Path(__file__).parent
    config = ConfigLoader.load("mcp_servers.yaml", root_dir)
    return config.servers[0]


# Note: MCP sessions should generally be module-scoped to avoid connection
# overhead and potential issues with rapid connect/disconnect cycles.
@pytest.fixture(scope="module")
async def mcp_session(server_config) -> AsyncGenerator[MCPClientSession, None]:
    """Module-scoped MCP session for this test file."""
    session = MCPClientSession(server_config, None)
    await session.connect()
    yield session
    await session.disconnect()


@pytest.fixture
def file_tracker_func() -> FileTracker:
    """Function-scoped file tracker."""
    return FileTracker()


@pytest.fixture
def tool_caller_func(mcp_session, file_tracker_func) -> ToolCaller:
    """Function-scoped tool caller (session is shared, but caller is per-test)."""
    return ToolCaller(
        session=mcp_session,
        default_timeout=30,
        file_tracker=file_tracker_func,
    )


@pytest.mark.asyncio
async def test_connection(mcp_session):
    """Test connection."""
    assert mcp_session.is_connected
    print(f"Connected to: {mcp_session.name}")


@pytest.mark.asyncio
async def test_list_tools(mcp_session):
    """Test list tools."""
    tools = await mcp_session.list_tools()
    print(f"Found {len(tools)} tools")
    assert len(tools) > 0


@pytest.mark.asyncio
async def test_read_file(tool_caller_func):
    """Test reading a file."""
    result = await tool_caller_func.call(
        "read_file",
        arguments={"path": f"{WORKSPACE}/sample.txt"},
    )
    assert result.success, f"Failed: {result.error_message}"
    assert "Hello" in result.text_content
    print(f"Content: {result.text_content}")


@pytest.mark.asyncio
async def test_list_directory(tool_caller_func):
    """Test listing directory."""
    result = await tool_caller_func.call(
        "list_directory",
        arguments={"path": WORKSPACE},
    )
    assert result.success, f"Failed: {result.error_message}"
    assert "sample.txt" in result.text_content
    print(f"Directory:\n{result.text_content}")
