"""
Tests for UE-MCP editor.configure and editor.pip_install Tools.

Tests the following tools:
- editor.configure: Check and fix project configuration
- editor.pip_install: Install Python packages in UE5

Run with:
    cd tests/ue_mcp_test
    pytest test_editor_configure.py -v
"""

import json

import pytest

from mcp_pytest import (
    CustomAssertion,
    DurationAssertion,
    SuccessAssertion,
)


# =============================================================================
# editor.configure Tool Schema Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_configure_tool_exists(mcp_client):
    """Test that editor.configure tool exists."""
    tools = await mcp_client.list_tools()
    tool_names = [t.name for t in tools]

    assert "editor.configure" in tool_names, "editor.configure tool should exist"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_configure_tool_schema(tool_caller):
    """Test editor.configure tool schema and parameters."""
    tools = await tool_caller.client.list_tools()
    configure_tool = next((t for t in tools if t.name == "editor.configure"), None)

    assert configure_tool is not None, "editor.configure tool should exist"
    assert configure_tool.description, "Should have description"
    assert configure_tool.inputSchema, "Should have input schema"

    schema = configure_tool.inputSchema
    props = schema.get("properties", {})

    # Verify expected parameters
    assert "auto_fix" in props, "Should accept 'auto_fix' parameter"
    assert "additional_paths" in props, "Should accept 'additional_paths' parameter"

    print("editor.configure schema:")
    print(f"  Description: {configure_tool.description[:150]}...")
    print(f"  Parameters: {list(props.keys())}")

    # Check auto_fix default
    auto_fix_prop = props.get("auto_fix", {})
    print(f"  auto_fix type: {auto_fix_prop.get('type')}")


# =============================================================================
# editor.configure Execution Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_configure_check_only(tool_caller):
    """Test configuration check without auto-fix."""
    result = await tool_caller.call(
        "editor.configure",
        arguments={
            "auto_fix": False,  # Don't modify files
        },
    )

    assert result.success, f"Configuration check failed: {result.error_message}"

    config_data = json.loads(result.text_content)
    print(f"Configuration check result: {json.dumps(config_data, indent=2)}")

    # Should return check results
    # The response structure depends on implementation


@pytest.mark.asyncio
@pytest.mark.unit
async def test_configure_with_auto_fix(tool_caller):
    """Test configuration with auto-fix enabled."""
    result = await tool_caller.call(
        "editor.configure",
        arguments={
            "auto_fix": True,  # Allow modifications
        },
    )

    config_data = json.loads(result.text_content)
    print(f"Auto-fix result: {json.dumps(config_data, indent=2)}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_configure_with_additional_paths(tool_caller, temp_output_dir):
    """Test configuration with additional Python paths."""
    # Create a test path
    test_path = str(temp_output_dir / "custom_scripts")

    result = await tool_caller.call(
        "editor.configure",
        arguments={
            "auto_fix": True,
            "additional_paths": [test_path],
        },
    )

    config_data = json.loads(result.text_content)
    print(f"Configure with paths: {json.dumps(config_data, indent=2)}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_configure_multiple_paths(tool_caller, temp_output_dir):
    """Test configuration with multiple additional paths."""
    paths = [
        str(temp_output_dir / "scripts1"),
        str(temp_output_dir / "scripts2"),
        str(temp_output_dir / "utils"),
    ]

    result = await tool_caller.call(
        "editor.configure",
        arguments={
            "auto_fix": True,
            "additional_paths": paths,
        },
    )

    config_data = json.loads(result.text_content)
    print(f"Multiple paths result: {config_data}")


# =============================================================================
# Configuration Validation Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_configure_validates_project(tool_caller):
    """Test that configure validates the UE project."""
    result = await tool_caller.call(
        "editor.configure",
        arguments={"auto_fix": False},
    )

    config_data = json.loads(result.text_content)

    # Should check Python plugin
    # Should check remote execution settings
    # Should check Python paths

    # The exact fields depend on implementation
    print(f"Validation result: {config_data}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_configure_response_structure(tool_caller):
    """Test that configure returns expected response structure."""
    result = await tool_caller.call(
        "editor.configure",
        arguments={"auto_fix": False},
    )

    config_data = json.loads(result.text_content)

    # Custom assertion for response structure
    has_check_results = CustomAssertion(
        check_func=lambda r: isinstance(json.loads(r.text_content), dict),
        description="Response should be a dictionary",
    )

    # Verify it's a valid response
    assert isinstance(config_data, dict), "Should return a dictionary"


# =============================================================================
# editor.pip_install Tool Schema Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pip_install_tool_exists(mcp_client):
    """Test that editor.pip_install tool exists."""
    tools = await mcp_client.list_tools()
    tool_names = [t.name for t in tools]

    assert "editor.pip_install" in tool_names, "editor.pip_install tool should exist"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pip_install_tool_schema(tool_caller):
    """Test editor.pip_install tool schema and parameters."""
    tools = await tool_caller.client.list_tools()
    pip_tool = next((t for t in tools if t.name == "editor.pip_install"), None)

    assert pip_tool is not None, "editor.pip_install tool should exist"
    assert pip_tool.description, "Should have description"
    assert pip_tool.inputSchema, "Should have input schema"

    schema = pip_tool.inputSchema
    props = schema.get("properties", {})
    required = schema.get("required", [])

    # Verify expected parameters
    assert "packages" in props, "Should accept 'packages' parameter"
    assert "upgrade" in props, "Should accept 'upgrade' parameter"

    # Packages should be required
    assert "packages" in required, "'packages' should be required"

    print("editor.pip_install schema:")
    print(f"  Description: {pip_tool.description[:150]}...")
    print(f"  Parameters: {list(props.keys())}")
    print(f"  Required: {required}")


# =============================================================================
# editor.pip_install Parameter Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pip_install_missing_packages(tool_caller):
    """Test pip_install with missing packages parameter."""
    result = await tool_caller.call(
        "editor.pip_install",
        arguments={},  # Missing required 'packages'
        expect_error=True,
    )

    # Should fail validation
    print(f"Missing packages error: {result.error_message or result.text_content}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pip_install_empty_packages(tool_caller):
    """Test pip_install with empty packages list."""
    result = await tool_caller.call(
        "editor.pip_install",
        arguments={"packages": []},
    )

    pip_data = json.loads(result.text_content)
    print(f"Empty packages result: {pip_data}")


# =============================================================================
# editor.pip_install Execution Tests (Require UE5)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_pip_install_single_package(tool_caller):
    """Test installing a single package.

    Note: This test requires UE5 to be installed.
    """
    result = await tool_caller.call(
        "editor.pip_install",
        arguments={
            "packages": ["requests"],  # Common, safe package
            "upgrade": False,
        },
    )

    pip_data = json.loads(result.text_content)
    print(f"Install result: {json.dumps(pip_data, indent=2)}")

    if pip_data.get("success"):
        assert "packages" in pip_data, "Should list installed packages"
        assert "python_path" in pip_data, "Should show Python path used"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_pip_install_multiple_packages(tool_caller):
    """Test installing multiple packages."""
    result = await tool_caller.call(
        "editor.pip_install",
        arguments={
            "packages": ["requests", "Pillow"],
            "upgrade": False,
        },
    )

    pip_data = json.loads(result.text_content)
    print(f"Multi-package install: {json.dumps(pip_data, indent=2)}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_pip_install_with_upgrade(tool_caller):
    """Test installing with upgrade flag."""
    result = await tool_caller.call(
        "editor.pip_install",
        arguments={
            "packages": ["pip"],  # Upgrade pip itself
            "upgrade": True,
        },
    )

    pip_data = json.loads(result.text_content)
    print(f"Upgrade result: {json.dumps(pip_data, indent=2)}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_pip_install_nonexistent_package(tool_caller):
    """Test installing a package that doesn't exist."""
    result = await tool_caller.call(
        "editor.pip_install",
        arguments={
            "packages": ["this-package-does-not-exist-xyz-123"],
            "upgrade": False,
        },
    )

    pip_data = json.loads(result.text_content)
    print(f"Nonexistent package result: {json.dumps(pip_data, indent=2)}")

    # Should fail gracefully
    if not pip_data.get("success"):
        assert "error" in pip_data or "output" in pip_data, \
            "Should provide error information"


# =============================================================================
# Combined Configuration Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_configure_then_pip_install(tool_caller):
    """Test running configure followed by pip_install."""
    # Step 1: Configure project
    config_result = await tool_caller.call(
        "editor.configure",
        arguments={"auto_fix": True},
    )
    config_data = json.loads(config_result.text_content)
    print(f"Configure: {config_data}")

    # Step 2: Install packages
    pip_result = await tool_caller.call(
        "editor.pip_install",
        arguments={
            "packages": ["requests"],
            "upgrade": False,
        },
    )
    pip_data = json.loads(pip_result.text_content)
    print(f"Pip install: {pip_data}")


# =============================================================================
# Assertion-Based Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_configure_with_assertions(tool_caller):
    """Test configure with assertion framework."""
    result = await tool_caller.call_and_assert(
        "editor.configure",
        arguments={"auto_fix": False},
        assertions=[
            SuccessAssertion(),
            DurationAssertion(max_seconds=30),
        ],
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pip_install_response_format(tool_caller):
    """Test that pip_install returns properly formatted response."""
    # Custom assertion for response format
    valid_response = CustomAssertion(
        check_func=lambda r: "success" in json.loads(r.text_content) or "error" in json.loads(r.text_content),
        description="Response should contain 'success' or 'error' field",
    )

    result = await tool_caller.call_and_assert(
        "editor.pip_install",
        arguments={"packages": []},
        assertions=[
            SuccessAssertion(),
            valid_response,
        ],
    )
