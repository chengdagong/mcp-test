"""
Pytest configuration for filesystem MCP tests.

CRITICAL: Event Loop Configuration for MCP Testing
==================================================

MCP servers require careful event loop management when testing with pytest-asyncio.
The key issue is that module-scoped async fixtures (mcp_server_manager, mcp_client)
must share the same event loop as the test functions that use them.

Without proper configuration, you may encounter:
- Tests hanging or timing out (typically ~30s, matching default timeout)
- "Attempted to exit cancel scope in a different task" warnings
- Inconsistent test behavior between runs

Solution: Use module-scoped event loops
---------------------------------------
This is configured in pytest.ini with:
    asyncio_mode = auto
    asyncio_default_fixture_loop_scope = session
    asyncio_default_test_loop_scope = session

And we provide a module-scoped event_loop fixture below as a fallback.
"""

from __future__ import annotations

import asyncio
from typing import Iterator

import pytest


# This file ensures pytest finds and uses the mcp-pytest plugin
# The plugin is automatically loaded via entry_points in pyproject.toml


@pytest.fixture(scope="module")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Create a module-scoped event loop.

    This ensures that:
    1. Module-scoped async fixtures (mcp_server_manager, mcp_client) are created
       in the same event loop that tests will use.
    2. The MCP client session remains valid across all tests in the module.
    3. No event loop switching occurs between fixture setup and test execution.

    This fixture works in conjunction with pytest.ini settings:
        asyncio_default_fixture_loop_scope = session
        asyncio_default_test_loop_scope = session
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


def pytest_configure(config):
    """Additional pytest configuration."""
    print("\n=== Filesystem MCP Test Suite ===\n")
