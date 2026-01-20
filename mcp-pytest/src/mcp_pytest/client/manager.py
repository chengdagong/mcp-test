"""Multi-server connection manager for MCP tests."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from mcp_pytest.client.session import MCPClientSession

if TYPE_CHECKING:
    from mcp_pytest.config.models import MCPTestConfig
    from mcp_pytest.logging.mcp_logger import MCPLogger

logger = logging.getLogger(__name__)


class MCPServerManager:
    """
    Manage multiple MCP server connections.

    Provides centralized lifecycle management for all configured MCP servers,
    supporting both sequential and parallel startup.
    """

    def __init__(
        self,
        config: MCPTestConfig,
        mcp_logger: Optional[MCPLogger] = None,
    ):
        """
        Initialize server manager.

        Args:
            config: MCP test configuration with server definitions.
            mcp_logger: Optional logger for MCP communications.
        """
        self._config = config
        self._mcp_logger = mcp_logger
        self._sessions: Dict[str, MCPClientSession] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    @property
    def server_names(self) -> List[str]:
        """Get list of configured server names."""
        return self._config.get_server_names()

    @property
    def connected_servers(self) -> List[str]:
        """Get list of currently connected server names."""
        return [name for name, session in self._sessions.items() if session.is_connected]

    async def start_server(self, server_name: str) -> MCPClientSession:
        """
        Start a specific server and return its session.

        Args:
            server_name: Name of the server to start.

        Returns:
            Connected MCPClientSession.

        Raises:
            ValueError: If server name is not in configuration.
            ConnectionError: If connection fails.
        """
        # Get or create lock for this server
        if server_name not in self._locks:
            self._locks[server_name] = asyncio.Lock()

        async with self._locks[server_name]:
            # Check if already connected
            if server_name in self._sessions and self._sessions[server_name].is_connected:
                logger.debug(f"Server '{server_name}' is already connected")
                return self._sessions[server_name]

            # Get server config
            server_config = self._config.get_server(server_name)
            if server_config is None:
                available = ", ".join(self.server_names) or "(none)"
                raise ValueError(
                    f"Server '{server_name}' not found in configuration. "
                    f"Available servers: {available}"
                )

            # Create and connect session
            session = MCPClientSession(server_config, self._mcp_logger)
            await session.connect()

            self._sessions[server_name] = session
            return session

    async def start_all_servers(
        self, parallel: bool = False
    ) -> Dict[str, MCPClientSession]:
        """
        Start all configured servers.

        Args:
            parallel: If True, start servers concurrently. Default is False.

        Returns:
            Dict mapping server names to their sessions.

        Raises:
            ConnectionError: If any server fails to connect (when not parallel).
            ExceptionGroup: If multiple servers fail (when parallel).
        """
        if not self._config.servers:
            logger.warning("No servers configured")
            return {}

        server_names = self.server_names

        if parallel:
            return await self._start_servers_parallel(server_names)
        else:
            return await self._start_servers_sequential(server_names)

    async def _start_servers_sequential(
        self, server_names: List[str]
    ) -> Dict[str, MCPClientSession]:
        """Start servers one by one."""
        for name in server_names:
            await self.start_server(name)
        return self._sessions.copy()

    async def _start_servers_parallel(
        self, server_names: List[str]
    ) -> Dict[str, MCPClientSession]:
        """Start servers concurrently."""
        tasks = [self.start_server(name) for name in server_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for errors
        errors = []
        for name, result in zip(server_names, results):
            if isinstance(result, Exception):
                errors.append((name, result))
                logger.error(f"Failed to start server '{name}': {result}")

        if errors:
            # Clean up successfully started servers
            await self.stop_all_servers()
            error_msgs = [f"{name}: {err}" for name, err in errors]
            raise ConnectionError(
                f"Failed to start {len(errors)} server(s):\n" + "\n".join(error_msgs)
            )

        return self._sessions.copy()

    async def stop_server(self, server_name: str) -> None:
        """
        Stop a specific server.

        Args:
            server_name: Name of the server to stop.
        """
        if server_name not in self._sessions:
            logger.debug(f"Server '{server_name}' is not managed")
            return

        session = self._sessions[server_name]
        if session.is_connected:
            await session.disconnect()

        del self._sessions[server_name]

    async def stop_all_servers(self) -> None:
        """Stop all running servers."""
        server_names = list(self._sessions.keys())

        for name in server_names:
            try:
                await self.stop_server(name)
            except Exception as e:
                logger.warning(f"Error stopping server '{name}': {e}")

    def get_session(self, server_name: str) -> Optional[MCPClientSession]:
        """
        Get session for a specific server.

        Args:
            server_name: Name of the server.

        Returns:
            MCPClientSession if connected, None otherwise.
        """
        session = self._sessions.get(server_name)
        if session and session.is_connected:
            return session
        return None

    def get_default_session(self) -> Optional[MCPClientSession]:
        """
        Get the first configured server's session.

        Returns:
            MCPClientSession of the first server, or None if no servers.
        """
        if not self._config.servers:
            return None
        return self.get_session(self._config.servers[0].name)

    async def __aenter__(self) -> "MCPServerManager":
        """Async context manager entry - starts all servers."""
        await self.start_all_servers(parallel=self._config.parallel_servers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - stops all servers."""
        await self.stop_all_servers()
