"""Test using asyncio backend explicitly."""

import pytest
from pathlib import Path

from mcp_pytest.config.loader import ConfigLoader
from mcp_pytest.client.session import MCPClientSession


@pytest.fixture(scope="module")
def server_config():
    """Load server config directly."""
    root_dir = Path(__file__).parent
    config = ConfigLoader.load("mcp_servers.yaml", root_dir)
    return config.servers[0]


@pytest.mark.asyncio
async def test_direct_connection_asyncio(server_config):
    """Test connecting directly using asyncio marker."""
    print(f"Server config: {server_config}")

    session = MCPClientSession(server_config, None)

    try:
        print("Connecting...")
        await session.connect()
        print(f"Connected: {session.is_connected}")

        print("Listing tools...")
        tools = await session.list_tools()
        print(f"Found {len(tools)} tools")

        for t in tools:
            print(f"  - {t.name}")

        assert len(tools) > 0

    finally:
        print("Disconnecting...")
        await session.disconnect()
        print("Done!")
