"""
mcp-pytest: A pytest plugin for testing MCP (Model Context Protocol) servers.

This package provides fixtures and utilities for testing MCP servers using pytest.
"""

from mcp_pytest.config.models import MCPTestConfig, ServerConfig
from mcp_pytest.client.session import MCPClientSession
from mcp_pytest.client.manager import MCPServerManager
from mcp_pytest.client.tool_caller import ToolCaller, ToolCallResult
from mcp_pytest.assertions.base import BaseAssertion, AssertionResult
from mcp_pytest.assertions.tool_result import (
    SuccessAssertion,
    ErrorAssertion,
    ResultContainsAssertion,
    ResultMatchesAssertion,
    DurationAssertion,
    CustomAssertion,
)

__version__ = "0.1.0"

__all__ = [
    # Config
    "MCPTestConfig",
    "ServerConfig",
    # Client
    "MCPClientSession",
    "MCPServerManager",
    "ToolCaller",
    "ToolCallResult",
    # Assertions
    "BaseAssertion",
    "AssertionResult",
    "SuccessAssertion",
    "ErrorAssertion",
    "ResultContainsAssertion",
    "ResultMatchesAssertion",
    "DurationAssertion",
    "CustomAssertion",
]
