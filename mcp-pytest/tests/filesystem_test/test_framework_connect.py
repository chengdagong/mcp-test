"""Test framework connection code directly."""

import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_with_exit_stack():
    """Test using AsyncExitStack like the framework does."""
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "D:/Code/mcp-test/mcp-pytest/tests/filesystem_test/workspace"],
    )

    print("Testing with AsyncExitStack (like framework)...")

    exit_stack = AsyncExitStack()

    try:
        async with asyncio.timeout(60):
            print("  Starting stdio_client...")
            read_stream, write_stream = await exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            print("  stdio_client started!")

            print("  Creating ClientSession...")
            session = await exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            print("  ClientSession created!")

            print("  Initializing...")
            await session.initialize()
            print("  Initialized!")

            # Test list_tools
            print("  Listing tools...")
            result = await session.list_tools()
            print(f"  Found {len(result.tools)} tools!")

    except asyncio.TimeoutError:
        print("  TIMEOUT!")
    finally:
        print("  Cleaning up...")
        await exit_stack.aclose()
        print("  Done!")


async def test_with_context_manager():
    """Test using context managers directly (like manual test)."""
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "D:/Code/mcp-test/mcp-pytest/tests/filesystem_test/workspace"],
    )

    print("\nTesting with context managers (like manual test)...")

    async with stdio_client(server_params) as (read_stream, write_stream):
        print("  stdio_client started!")
        async with ClientSession(read_stream, write_stream) as session:
            print("  ClientSession created!")
            await session.initialize()
            print("  Initialized!")

            result = await session.list_tools()
            print(f"  Found {len(result.tools)} tools!")


if __name__ == "__main__":
    # Run both tests
    asyncio.run(test_with_exit_stack())
    print("\n" + "="*50 + "\n")
    asyncio.run(test_with_context_manager())
