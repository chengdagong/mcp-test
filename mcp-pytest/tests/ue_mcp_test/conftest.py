"""
Pytest configuration for UE-MCP tests.

Provides fixtures and utilities for testing Unreal Engine MCP server.

CRITICAL: Event Loop Configuration
==================================
MCP servers require module-scoped event loops to work correctly with pytest-asyncio.
See pytest.ini for asyncio_default_fixture_loop_scope and asyncio_default_test_loop_scope settings.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any, Iterator

import pytest


# =============================================================================
# Path Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def ue_mcp_root() -> Path:
    """Root directory of the ue-mcp project."""
    return Path("D:/Code/ue-mcp")


@pytest.fixture(scope="session")
def test_fixtures_dir(ue_mcp_root: Path) -> Path:
    """Test fixtures directory containing sample UE projects."""
    return ue_mcp_root / "tests" / "fixtures"


@pytest.fixture(scope="session")
def empty_project_path(test_fixtures_dir: Path) -> Path:
    """Path to the EmptyProjectTemplate fixture."""
    return test_fixtures_dir / "EmptyProjectTemplate"


@pytest.fixture(scope="session")
def sample_uproject_path(empty_project_path: Path) -> Path:
    """Path to the sample .uproject file."""
    return empty_project_path / "EmptyProjectTemplate.uproject"


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory(prefix="ue_mcp_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_capture_dir(temp_output_dir: Path) -> Path:
    """Directory for capture outputs."""
    capture_dir = temp_output_dir / "captures"
    capture_dir.mkdir(parents=True, exist_ok=True)
    return capture_dir


# =============================================================================
# MCP Tool Response Helpers
# =============================================================================


def parse_mcp_result(result) -> dict[str, Any]:
    """Parse MCP tool result content."""
    if hasattr(result, "text_content"):
        try:
            return json.loads(result.text_content)
        except json.JSONDecodeError:
            return {"raw_content": result.text_content}
    return {"result": result}


def assert_success_result(result, message: str = ""):
    """Assert that an MCP result indicates success."""
    parsed = parse_mcp_result(result)
    assert parsed.get("success", False), f"Expected success. {message}. Result: {parsed}"
    return parsed


def assert_error_result(result, expected_error: str = None):
    """Assert that an MCP result indicates an error."""
    parsed = parse_mcp_result(result)
    assert not parsed.get("success", True), f"Expected error but got success. Result: {parsed}"
    if expected_error:
        error_msg = parsed.get("error", "")
        assert expected_error in error_msg, (
            f"Expected '{expected_error}' in error message. Got: {error_msg}"
        )
    return parsed


# =============================================================================
# Editor State Fixtures
# =============================================================================


@pytest.fixture
def editor_status_checker(tool_caller):
    """Helper to check editor status."""

    async def check_status():
        result = await tool_caller.call("editor.status", arguments={})
        return parse_mcp_result(result)

    return check_status


@pytest.fixture
def editor_launcher(tool_caller):
    """Helper to launch editor with custom settings."""

    async def launch(wait: bool = False, wait_timeout: float = 30.0, additional_paths: list = None):
        args = {"wait": wait, "wait_timeout": wait_timeout}
        if additional_paths:
            args["additional_paths"] = additional_paths
        result = await tool_caller.call("editor.launch", arguments=args)
        return parse_mcp_result(result)

    return launch


@pytest.fixture
def editor_stopper(tool_caller):
    """Helper to stop editor."""

    async def stop():
        result = await tool_caller.call("editor.stop", arguments={})
        return parse_mcp_result(result)

    return stop


# =============================================================================
# Test Utilities
# =============================================================================


@pytest.fixture
def expected_tools():
    """List of expected tool names in ue-mcp server."""
    return [
        "editor.launch",
        "editor.status",
        "editor.stop",
        "editor.execute",
        "editor.configure",
        "editor.pip_install",
        "editor.capture.orbital",
        "editor.capture.pie",
        "editor.capture.window",
        "editor.asset.diagnostic",
        "project.build",
    ]


# =============================================================================
# Event Loop Configuration
# =============================================================================


@pytest.fixture(scope="module")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Create a module-scoped event loop.

    This ensures MCP client sessions created in module-scoped fixtures
    remain valid across all tests in the module.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# =============================================================================
# Configuration Hooks
# =============================================================================


def pytest_configure(config):
    """Additional pytest configuration."""
    print("\n=== UE-MCP Tool Test Suite ===\n")
    print("Testing Unreal Engine MCP Server Tools")
    print("=" * 40)
