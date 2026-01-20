"""Simple test to debug the list_tools issue."""

import pytest


@pytest.mark.asyncio
async def test_connection_only(mcp_client):
    """Just test connection."""
    print(f"Connected: {mcp_client.is_connected}")
    print(f"Server name: {mcp_client.name}")
    assert mcp_client.is_connected


@pytest.mark.asyncio
async def test_list_tools_simple(mcp_client):
    """Test list_tools."""
    print("Calling list_tools...")
    tools = await mcp_client.list_tools()
    print(f"Got {len(tools)} tools")
    for t in tools:
        print(f"  - {t.name}")
    assert len(tools) > 0
