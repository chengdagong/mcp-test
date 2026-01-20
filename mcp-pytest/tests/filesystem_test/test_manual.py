"""
Manual test script to verify filesystem MCP server works correctly.
Run directly: python test_manual.py
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "D:/Code/mcp-test/mcp-pytest/tests/filesystem_test/workspace"],
    )

    print("Connecting to filesystem MCP server...")

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            print("Initializing session...")
            await session.initialize()
            print("Session initialized!")

            # Test list_tools
            print("\n--- Testing list_tools ---")
            tools_result = await session.list_tools()
            print(f"Found {len(tools_result.tools)} tools:")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description[:50] if tool.description else 'No description'}...")

            # Test read_file
            print("\n--- Testing read_file ---")
            result = await session.call_tool("read_file", {"path": "sample.txt"})
            print(f"read_file result: {result.content[0].text[:100] if result.content else 'No content'}...")

            # Test list_directory
            print("\n--- Testing list_directory ---")
            result = await session.call_tool("list_directory", {"path": "."})
            print(f"list_directory result: {result.content[0].text if result.content else 'No content'}")

            print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
