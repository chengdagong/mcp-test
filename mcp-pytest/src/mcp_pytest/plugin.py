"""
Pytest plugin for MCP server testing.

This module provides fixtures and hooks for testing MCP servers using pytest.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator, Generator, Optional

import pytest
import pytest_asyncio

from mcp_pytest.cleanup.cleaner import FileCleaner
from mcp_pytest.cleanup.tracker import FileTracker
from mcp_pytest.client.manager import MCPServerManager
from mcp_pytest.client.session import MCPClientSession
from mcp_pytest.client.tool_caller import ToolCaller
from mcp_pytest.config.loader import ConfigLoader
from mcp_pytest.config.models import MCPTestConfig
from mcp_pytest.logging.mcp_logger import MCPLogger

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser

logger = logging.getLogger(__name__)


# =============================================================================
# Pytest Hooks - Configuration and Options
# =============================================================================


def pytest_addoption(parser: Parser) -> None:
    """Register pytest command-line and ini options."""
    group = parser.getgroup("mcp", "MCP Testing Options")

    group.addoption(
        "--mcp-config",
        dest="mcp_config",
        metavar="PATH",
        help="Path to MCP servers YAML configuration file",
    )

    group.addoption(
        "--mcp-log-level",
        dest="mcp_log_level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="MCP communication log level",
    )

    group.addoption(
        "--mcp-no-cleanup",
        action="store_true",
        dest="mcp_no_cleanup",
        help="Disable automatic file cleanup after tests",
    )

    group.addoption(
        "--mcp-log-file",
        dest="mcp_log_file",
        metavar="PATH",
        help="Path to write MCP communication logs",
    )

    # INI options
    parser.addini(
        "mcp_config_file",
        help="Default MCP configuration file path",
        default="mcp_servers.yaml",
    )

    parser.addini(
        "mcp_default_timeout",
        help="Default timeout for MCP tool calls (seconds)",
        default="30",
    )

    parser.addini(
        "mcp_log_messages",
        help="Log MCP protocol messages",
        type="bool",
        default=True,
    )


def pytest_configure(config: Config) -> None:
    """Configure the MCP pytest plugin."""
    # Register markers
    config.addinivalue_line(
        "markers",
        "mcp_timeout(seconds): Set timeout for MCP tool calls in this test",
    )
    config.addinivalue_line(
        "markers",
        "mcp_server(name): Specify which MCP server to use for this test",
    )
    config.addinivalue_line(
        "markers",
        "mcp_cleanup(*paths): Additional paths to clean up after test",
    )
    config.addinivalue_line(
        "markers",
        "mcp_skip_cleanup: Skip automatic cleanup for this test",
    )


# =============================================================================
# Session-scoped Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def mcp_config(request: pytest.FixtureRequest) -> MCPTestConfig:
    """
    Load MCP test configuration.

    This fixture loads configuration from:
    1. --mcp-config command line option
    2. mcp_config_file ini option
    3. Default config file search

    Returns:
        MCPTestConfig instance.
    """
    config_path = request.config.getoption("mcp_config")

    if config_path is None:
        config_path = request.config.getini("mcp_config_file")

    root_dir = Path(request.config.rootdir)

    try:
        mcp_cfg = ConfigLoader.load(config_path, root_dir)
    except FileNotFoundError:
        # Return default config if no config file found
        logger.info("No MCP configuration file found, using defaults")
        mcp_cfg = MCPTestConfig()

    # Override timeout from ini if set
    ini_timeout = request.config.getini("mcp_default_timeout")
    if ini_timeout:
        try:
            mcp_cfg.default_timeout = float(ini_timeout)
        except ValueError:
            pass

    return mcp_cfg


@pytest.fixture(scope="session")
def mcp_logger(request: pytest.FixtureRequest, mcp_config: MCPTestConfig) -> MCPLogger:
    """
    Create MCP logger instance.

    Returns:
        MCPLogger for tracking MCP communications.
    """
    # Determine log level
    log_level = request.config.getoption("mcp_log_level")
    if log_level is None:
        log_level = mcp_config.log_level

    # Check for log file
    log_file = request.config.getoption("mcp_log_file")
    log_file_path = Path(log_file) if log_file else None

    # Check if logging is enabled
    log_messages = request.config.getini("mcp_log_messages")

    return MCPLogger(
        name="test",
        level=log_level,
        log_to_console=log_messages,
        log_to_file=log_file_path,
    )


# =============================================================================
# Module-scoped Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def file_tracker() -> FileTracker:
    """
    File tracking for cleanup.

    Module-scoped to track files across tests in the same module.

    Returns:
        FileTracker instance.
    """
    return FileTracker()


@pytest.fixture(scope="module")
def file_cleaner(file_tracker: FileTracker) -> FileCleaner:
    """
    File cleanup executor.

    Returns:
        FileCleaner instance.
    """
    return FileCleaner(file_tracker)


@pytest_asyncio.fixture(scope="module")
async def mcp_server_manager(
    mcp_config: MCPTestConfig,
    mcp_logger: MCPLogger,
) -> AsyncGenerator[MCPServerManager, None]:
    """
    Module-scoped MCP server manager.

    Starts all configured servers and keeps them running for the module.
    Servers are automatically stopped when the module completes.

    Returns:
        MCPServerManager with all servers started.
    """
    manager = MCPServerManager(mcp_config, mcp_logger)

    if mcp_config.servers:
        await manager.start_all_servers(parallel=mcp_config.parallel_servers)
        logger.info(f"Started {len(manager.connected_servers)} MCP server(s)")

    yield manager

    await manager.stop_all_servers()
    logger.info("Stopped all MCP servers")


@pytest_asyncio.fixture(scope="module")
async def mcp_client(
    mcp_server_manager: MCPServerManager,
    mcp_config: MCPTestConfig,
) -> MCPClientSession:
    """
    Module-scoped MCP client session.

    Returns the first configured server's session by default.
    Use @pytest.mark.mcp_server("name") to specify a different server.

    Returns:
        MCPClientSession for the default server.

    Raises:
        pytest.skip: If no servers are configured.
    """
    if not mcp_config.servers:
        pytest.skip("No MCP servers configured")

    session = mcp_server_manager.get_default_session()
    if session is None:
        pytest.fail("Failed to get default MCP session")

    return session


# =============================================================================
# Function-scoped Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def tool_caller(
    mcp_client: MCPClientSession,
    mcp_config: MCPTestConfig,
    file_tracker: FileTracker,
    file_cleaner: FileCleaner,
    request: pytest.FixtureRequest,
) -> AsyncGenerator[ToolCaller, None]:
    """
    Function-scoped tool caller with automatic cleanup.

    Provides a ToolCaller instance configured with:
    - Timeout from @pytest.mark.mcp_timeout or config default
    - File tracking for cleanup
    - Call history tracking

    After the test, tracked files are automatically cleaned up unless
    --mcp-no-cleanup is specified or @pytest.mark.mcp_skip_cleanup is used.

    Returns:
        ToolCaller instance.
    """
    # Get timeout from marker or config
    timeout_marker = request.node.get_closest_marker("mcp_timeout")
    timeout = timeout_marker.args[0] if timeout_marker else mcp_config.default_timeout

    caller = ToolCaller(
        session=mcp_client,
        default_timeout=timeout,
        file_tracker=file_tracker,
    )

    yield caller

    # Cleanup after test
    skip_cleanup = (
        request.config.getoption("mcp_no_cleanup")
        or request.node.get_closest_marker("mcp_skip_cleanup") is not None
    )

    if not skip_cleanup:
        # Handle additional cleanup paths from marker
        cleanup_marker = request.node.get_closest_marker("mcp_cleanup")
        if cleanup_marker:
            for path in cleanup_marker.args:
                file_tracker.track(Path(path), request.node.name)

        # Stop any directory watching
        file_tracker.stop_all_watching()

        # Clean up tracked files
        file_cleaner.cleanup_test(request.node.name, force=True)


@pytest_asyncio.fixture
async def mcp_server(
    mcp_server_manager: MCPServerManager,
    request: pytest.FixtureRequest,
) -> MCPClientSession:
    """
    Get a specific server session by marker.

    Usage:
        @pytest.mark.mcp_server("server_name")
        async def test_something(mcp_server):
            ...

    Returns:
        MCPClientSession for the specified server.

    Raises:
        pytest.fail: If marker is missing or server not found.
    """
    marker = request.node.get_closest_marker("mcp_server")

    if marker is None:
        pytest.fail(
            "mcp_server fixture requires @pytest.mark.mcp_server('server_name') marker"
        )

    server_name = marker.args[0]
    session = mcp_server_manager.get_session(server_name)

    if session is None:
        available = ", ".join(mcp_server_manager.server_names) or "(none)"
        pytest.fail(
            f"MCP server '{server_name}' not found or not running. "
            f"Available servers: {available}"
        )

    return session


# =============================================================================
# Pytest Hooks - Reporting
# =============================================================================


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call):
    """Capture test results for reporting."""
    outcome = yield
    rep = outcome.get_result()

    # Store MCP call history in test report for HTML reporting
    if hasattr(item, "funcargs"):
        tool_caller = item.funcargs.get("tool_caller")
        if tool_caller and hasattr(tool_caller, "call_history"):
            rep.mcp_call_history = tool_caller.call_history


# Optional: pytest-html integration
try:
    import pytest_html

    @pytest.hookimpl(optionalhook=True)
    def pytest_html_results_table_header(cells):
        """Add MCP column to HTML report."""
        cells.insert(2, "<th>MCP Calls</th>")

    @pytest.hookimpl(optionalhook=True)
    def pytest_html_results_table_row(report, cells):
        """Add MCP call count to HTML report row."""
        call_count = len(getattr(report, "mcp_call_history", []))
        cells.insert(2, f"<td>{call_count}</td>")

except ImportError:
    pass  # pytest-html not installed
