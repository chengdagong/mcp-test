"""
Sample MCP Server for testing mcp-pytest.

This is a minimal MCP server that provides a few test tools.
Run with: python sample_server.py
"""

import asyncio
import json
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


# Create the server
server = Server("sample-test-server")


@server.list_tools()
async def list_tools():
    """List available tools."""
    return [
        Tool(
            name="echo",
            description="Echo back the input message",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo back",
                    }
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="add",
            description="Add two numbers",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"},
                },
                "required": ["a", "b"],
            },
        ),
        Tool(
            name="get_time",
            description="Get the current time",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="slow_operation",
            description="Simulate a slow operation",
            inputSchema={
                "type": "object",
                "properties": {
                    "delay": {
                        "type": "number",
                        "description": "Delay in seconds",
                        "default": 1,
                    }
                },
            },
        ),
        Tool(
            name="fail",
            description="Always fails with an error",
            inputSchema={
                "type": "object",
                "properties": {
                    "error_message": {
                        "type": "string",
                        "description": "Error message to return",
                        "default": "Intentional failure",
                    }
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""

    if name == "echo":
        message = arguments.get("message", "")
        return [TextContent(type="text", text=f"Echo: {message}")]

    elif name == "add":
        a = arguments.get("a", 0)
        b = arguments.get("b", 0)
        result = a + b
        return [TextContent(type="text", text=f"Result: {result}")]

    elif name == "get_time":
        current_time = datetime.now().isoformat()
        return [TextContent(type="text", text=f"Current time: {current_time}")]

    elif name == "slow_operation":
        delay = arguments.get("delay", 1)
        await asyncio.sleep(delay)
        return [TextContent(type="text", text=f"Completed after {delay}s delay")]

    elif name == "fail":
        error_message = arguments.get("error_message", "Intentional failure")
        raise Exception(error_message)

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
