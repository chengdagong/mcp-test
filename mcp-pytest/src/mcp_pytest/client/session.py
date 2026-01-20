"""MCP ClientSession wrapper with enhanced functionality."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, Tool

if TYPE_CHECKING:
    from mcp_pytest.config.models import ServerConfig
    from mcp_pytest.logging.mcp_logger import MCPLogger

logger = logging.getLogger(__name__)


class MCPClientSession:
    """
    Wrapper around MCP ClientSession with enhanced functionality.

    Provides:
    - Automatic connection management
    - Logging integration
    - Timeout handling
    - Error handling
    """

    def __init__(
        self,
        server_config: ServerConfig,
        mcp_logger: Optional[MCPLogger] = None,
    ):
        """
        Initialize MCP client session.

        Args:
            server_config: Server configuration from YAML.
            mcp_logger: Optional logger for MCP communications.
        """
        self._config = server_config
        self._mcp_logger = mcp_logger
        self._session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._read_stream = None
        self._write_stream = None

    @property
    def name(self) -> str:
        """Get server name."""
        return self._config.name

    @property
    def is_connected(self) -> bool:
        """Check if session is connected."""
        return self._session is not None

    def _build_server_params(self) -> StdioServerParameters:
        """Build StdioServerParameters from config."""
        # Merge environment variables
        env = {**os.environ, **self._config.env}

        return StdioServerParameters(
            command=self._config.command,
            args=self._config.args,
            env=env,
            cwd=str(self._config.cwd) if self._config.cwd else None,
        )

    async def connect(self) -> None:
        """
        Establish connection to MCP server.

        Raises:
            TimeoutError: If connection times out.
            ConnectionError: If connection fails.
        """
        if self.is_connected:
            logger.warning(f"Session '{self.name}' is already connected")
            return

        logger.info(f"Connecting to MCP server '{self.name}'...")

        try:
            self._exit_stack = AsyncExitStack()

            server_params = self._build_server_params()

            # Connect with timeout
            async with asyncio.timeout(self._config.startup_timeout):
                # Enter stdio client context
                self._read_stream, self._write_stream = await self._exit_stack.enter_async_context(
                    stdio_client(server_params)
                )

                # Create and enter session context
                self._session = await self._exit_stack.enter_async_context(
                    ClientSession(self._read_stream, self._write_stream)
                )

                # Initialize protocol
                await self._session.initialize()

            logger.info(f"Connected to MCP server '{self.name}'")

            if self._mcp_logger:
                self._mcp_logger.log_connection(self.name, "connected")

        except asyncio.TimeoutError:
            await self._cleanup()
            raise TimeoutError(
                f"Connection to MCP server '{self.name}' timed out "
                f"after {self._config.startup_timeout}s"
            )
        except Exception as e:
            await self._cleanup()
            raise ConnectionError(f"Failed to connect to MCP server '{self.name}': {e}") from e

    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        if not self.is_connected:
            return

        logger.info(f"Disconnecting from MCP server '{self.name}'...")

        try:
            async with asyncio.timeout(self._config.shutdown_timeout):
                await self._cleanup()
            logger.info(f"Disconnected from MCP server '{self.name}'")

            if self._mcp_logger:
                self._mcp_logger.log_connection(self.name, "disconnected")

        except asyncio.TimeoutError:
            logger.warning(f"Disconnect from '{self.name}' timed out, forcing cleanup")
            await self._cleanup()

    async def _cleanup(self) -> None:
        """Clean up resources."""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                logger.warning(f"Error during cleanup for '{self.name}': {e}")
        self._session = None
        self._exit_stack = None
        self._read_stream = None
        self._write_stream = None

    async def list_tools(self) -> List[Tool]:
        """
        Get available tools from server.

        Returns:
            List of available tools.

        Raises:
            ConnectionError: If not connected.
        """
        self._ensure_connected()

        if self._mcp_logger:
            self._mcp_logger.log_request(self.name, "tools/list", {})

        result = await self._session.list_tools()  # type: ignore

        if self._mcp_logger:
            self._mcp_logger.log_response(
                self.name, "tools/list", {"tool_count": len(result.tools)}
            )

        return result.tools

    async def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> CallToolResult:
        """
        Call a tool with logging and timeout support.

        Args:
            name: Name of the tool to call.
            arguments: Arguments to pass to the tool.
            timeout: Optional timeout in seconds. Uses config default if not specified.

        Returns:
            CallToolResult from the tool execution.

        Raises:
            ConnectionError: If not connected.
            TimeoutError: If tool call times out.
        """
        self._ensure_connected()

        if arguments is None:
            arguments = {}

        effective_timeout = timeout if timeout is not None else self._config.startup_timeout

        if self._mcp_logger:
            self._mcp_logger.log_request(self.name, f"tools/call/{name}", arguments)

        try:
            async with asyncio.timeout(effective_timeout):
                result = await self._session.call_tool(name, arguments)  # type: ignore

            if self._mcp_logger:
                self._mcp_logger.log_response(
                    self.name,
                    f"tools/call/{name}",
                    {
                        "is_error": result.isError if hasattr(result, "isError") else False,
                        "content_count": len(result.content) if result.content else 0,
                    },
                )

            return result

        except asyncio.TimeoutError:
            if self._mcp_logger:
                self._mcp_logger.log_error(
                    self.name, f"tools/call/{name}", f"Timeout after {effective_timeout}s"
                )
            raise TimeoutError(f"Tool call '{name}' timed out after {effective_timeout}s")

    async def list_resources(self) -> Any:
        """Get available resources from server."""
        self._ensure_connected()
        return await self._session.list_resources()  # type: ignore

    async def list_prompts(self) -> Any:
        """Get available prompts from server."""
        self._ensure_connected()
        return await self._session.list_prompts()  # type: ignore

    def _ensure_connected(self) -> None:
        """Ensure session is connected."""
        if not self.is_connected:
            raise ConnectionError(f"MCP server '{self.name}' is not connected")

    async def __aenter__(self) -> "MCPClientSession":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
