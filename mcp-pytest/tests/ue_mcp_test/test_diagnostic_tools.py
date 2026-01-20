"""
Tests for UE-MCP Diagnostic Tools.

Tests the following tool:
- editor.asset.diagnostic: Run diagnostics on UE5 assets

Run with:
    cd tests/ue_mcp_test
    pytest test_diagnostic_tools.py -v
"""

import json

import pytest

from mcp_pytest import (
    CustomAssertion,
    DurationAssertion,
    SuccessAssertion,
)


# =============================================================================
# Tool Discovery Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_diagnostic_tool_exists(mcp_client):
    """Test that editor.asset.diagnostic tool exists."""
    tools = await mcp_client.list_tools()
    tool_names = [t.name for t in tools]

    assert "editor.asset.diagnostic" in tool_names, \
        "editor.asset.diagnostic tool should exist"


# =============================================================================
# Tool Schema Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_diagnostic_tool_schema(tool_caller):
    """Test editor.asset.diagnostic tool schema and parameters."""
    tools = await tool_caller.client.list_tools()
    diagnostic_tool = next((t for t in tools if t.name == "editor.asset.diagnostic"), None)

    assert diagnostic_tool is not None
    assert diagnostic_tool.description
    assert diagnostic_tool.inputSchema

    schema = diagnostic_tool.inputSchema
    props = schema.get("properties", {})
    required = schema.get("required", [])

    print("editor.asset.diagnostic schema:")
    print(f"  Description: {diagnostic_tool.description[:200]}...")
    print(f"  Parameters: {list(props.keys())}")
    print(f"  Required: {required}")

    # asset_path should be required
    assert "asset_path" in props, "Should have 'asset_path' parameter"
    assert "asset_path" in required, "'asset_path' should be required"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_diagnostic_tool_description(tool_caller):
    """Test that diagnostic tool has informative description."""
    tools = await tool_caller.client.list_tools()
    diagnostic_tool = next((t for t in tools if t.name == "editor.asset.diagnostic"), None)

    description = diagnostic_tool.description

    # Description should mention supported asset types
    supported_types = ["Level", "Blueprint", "Material", "StaticMesh"]
    found_types = [t for t in supported_types if t.lower() in description.lower()]

    print(f"Description mentions asset types: {found_types}")

    # Description should explain return format
    return_fields = ["success", "asset_type", "issues", "errors", "warnings"]
    found_fields = [f for f in return_fields if f.lower() in description.lower()]

    print(f"Description mentions return fields: {found_fields}")


# =============================================================================
# Parameter Validation Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_diagnostic_missing_asset_path(tool_caller):
    """Test diagnostic with missing asset_path parameter."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={},  # Missing required 'asset_path'
        expect_error=True,
    )

    print(f"Missing asset_path error: {result.error_message or result.text_content}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_diagnostic_empty_asset_path(tool_caller):
    """Test diagnostic with empty asset_path."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={"asset_path": ""},
    )

    diag_data = json.loads(result.text_content)
    print(f"Empty asset_path result: {json.dumps(diag_data, indent=2)}")


# =============================================================================
# Diagnostic Execution Tests (Require Running Editor)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_diagnostic_level_asset(tool_caller):
    """Test running diagnostics on a Level asset."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={
            "asset_path": "/Game/Maps/TestLevel",
        },
    )

    diag_data = json.loads(result.text_content)
    print(f"Level diagnostic: {json.dumps(diag_data, indent=2)}")

    if diag_data.get("success"):
        # Check expected response structure
        assert "asset_path" in diag_data, "Should contain asset_path"
        assert "asset_type" in diag_data, "Should contain asset_type"
        assert "issues" in diag_data, "Should contain issues list"
        assert "errors" in diag_data, "Should contain error count"
        assert "warnings" in diag_data, "Should contain warning count"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_diagnostic_blueprint_asset(tool_caller):
    """Test running diagnostics on a Blueprint asset."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={
            "asset_path": "/Game/Blueprints/TestBlueprint",
        },
    )

    diag_data = json.loads(result.text_content)
    print(f"Blueprint diagnostic: {json.dumps(diag_data, indent=2)}")

    if diag_data.get("success"):
        assert diag_data.get("asset_type") in ["Blueprint", "Actor Blueprint", "Unknown"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_diagnostic_material_asset(tool_caller):
    """Test running diagnostics on a Material asset."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={
            "asset_path": "/Game/Materials/TestMaterial",
        },
    )

    diag_data = json.loads(result.text_content)
    print(f"Material diagnostic: {json.dumps(diag_data, indent=2)}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_diagnostic_static_mesh_asset(tool_caller):
    """Test running diagnostics on a StaticMesh asset."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={
            "asset_path": "/Game/Meshes/TestMesh",
        },
    )

    diag_data = json.loads(result.text_content)
    print(f"StaticMesh diagnostic: {json.dumps(diag_data, indent=2)}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_diagnostic_texture_asset(tool_caller):
    """Test running diagnostics on a Texture asset."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={
            "asset_path": "/Game/Textures/TestTexture",
        },
    )

    diag_data = json.loads(result.text_content)
    print(f"Texture diagnostic: {json.dumps(diag_data, indent=2)}")


# =============================================================================
# Response Structure Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_diagnostic_response_structure(tool_caller):
    """Test that diagnostic returns expected response structure."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={
            "asset_path": "/Game/Maps/TestLevel",
        },
    )

    diag_data = json.loads(result.text_content)

    if diag_data.get("success"):
        # Verify required fields
        required_fields = [
            "success", "asset_path", "asset_type", "asset_name",
            "errors", "warnings", "issues",
        ]

        for field in required_fields:
            assert field in diag_data, f"Response should contain '{field}'"

        # Verify issues structure
        issues = diag_data.get("issues", [])
        if issues:
            first_issue = issues[0]
            issue_fields = ["severity", "category", "message"]
            for field in issue_fields:
                assert field in first_issue, f"Issue should contain '{field}'"

        print(f"Response structure valid. Found {len(issues)} issues.")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_diagnostic_issue_severity_levels(tool_caller):
    """Test that issues have valid severity levels."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={
            "asset_path": "/Game/Maps/TestLevel",
        },
    )

    diag_data = json.loads(result.text_content)

    if diag_data.get("success"):
        issues = diag_data.get("issues", [])
        valid_severities = ["error", "warning", "info", "suggestion"]

        for issue in issues:
            severity = issue.get("severity", "").lower()
            assert severity in valid_severities, \
                f"Invalid severity: {severity}"

        # Count by severity
        error_count = sum(1 for i in issues if i.get("severity", "").lower() == "error")
        warning_count = sum(1 for i in issues if i.get("severity", "").lower() == "warning")

        print(f"Severity breakdown: {error_count} errors, {warning_count} warnings")


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_diagnostic_nonexistent_asset(tool_caller):
    """Test diagnostic on non-existent asset."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={
            "asset_path": "/Game/NonExistent/Asset12345",
        },
    )

    diag_data = json.loads(result.text_content)
    print(f"Non-existent asset: {json.dumps(diag_data, indent=2)}")

    # Should fail gracefully
    if not diag_data.get("success"):
        assert "error" in diag_data, "Should contain error message"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_diagnostic_invalid_asset_path_format(tool_caller):
    """Test diagnostic with invalid asset path format."""
    invalid_paths = [
        "not/a/valid/path",  # Missing /Game prefix
        "Game/Maps/Test",    # Missing leading slash
        "/InvalidRoot/Asset",  # Invalid root
    ]

    for invalid_path in invalid_paths:
        result = await tool_caller.call(
            "editor.asset.diagnostic",
            arguments={
                "asset_path": invalid_path,
            },
        )

        diag_data = json.loads(result.text_content)
        print(f"Invalid path '{invalid_path}': success={diag_data.get('success')}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_diagnostic_without_editor(tool_caller, editor_status_checker):
    """Test diagnostic when editor is not running."""
    status = await editor_status_checker()

    if status.get("status") not in ["ready"]:
        result = await tool_caller.call(
            "editor.asset.diagnostic",
            arguments={
                "asset_path": "/Game/Maps/TestLevel",
            },
        )

        diag_data = json.loads(result.text_content)
        print(f"Diagnostic without editor: {json.dumps(diag_data, indent=2)}")

        # Should fail gracefully
        assert not diag_data.get("success")


# =============================================================================
# Multiple Asset Diagnostic Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_diagnostic_multiple_assets(tool_caller):
    """Test running diagnostics on multiple assets sequentially."""
    assets_to_test = [
        "/Game/Maps/TestLevel",
        "/Game/Blueprints/TestBP",
        "/Game/Materials/TestMat",
    ]

    results = {}
    for asset_path in assets_to_test:
        result = await tool_caller.call(
            "editor.asset.diagnostic",
            arguments={"asset_path": asset_path},
        )

        diag_data = json.loads(result.text_content)
        results[asset_path] = diag_data

    print("Multiple asset diagnostics:")
    for path, data in results.items():
        success = data.get("success", False)
        asset_type = data.get("asset_type", "Unknown")
        errors = data.get("errors", 0)
        warnings = data.get("warnings", 0)
        print(f"  {path}: success={success}, type={asset_type}, errors={errors}, warnings={warnings}")


# =============================================================================
# Assertion-Based Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_diagnostic_response_format(tool_caller):
    """Test that diagnostic returns properly formatted response."""
    # Custom assertion for response format
    valid_response = CustomAssertion(
        check_func=lambda r: (
            "success" in json.loads(r.text_content)
            or "error" in json.loads(r.text_content)
        ),
        description="Response should contain 'success' or 'error'",
    )

    result = await tool_caller.call_and_assert(
        "editor.asset.diagnostic",
        arguments={"asset_path": "/Game/Maps/TestLevel"},
        assertions=[
            SuccessAssertion(),  # MCP call succeeds
            valid_response,
        ],
    )


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_diagnostic_with_full_assertions(tool_caller):
    """Test diagnostic with comprehensive assertions."""
    # Custom assertion for successful diagnostic
    diagnostic_succeeded = CustomAssertion(
        check_func=lambda r: json.loads(r.text_content).get("success", False),
        description="Diagnostic should succeed",
        message_func=lambda r: f"Diagnostic failed: {json.loads(r.text_content).get('error', 'Unknown')}",
    )

    # Custom assertion for proper structure
    has_issues_list = CustomAssertion(
        check_func=lambda r: "issues" in json.loads(r.text_content) and \
            isinstance(json.loads(r.text_content).get("issues"), list),
        description="Response should have issues list",
    )

    result = await tool_caller.call_and_assert(
        "editor.asset.diagnostic",
        arguments={"asset_path": "/Game/Maps/TestLevel"},
        assertions=[
            SuccessAssertion(),
            DurationAssertion(max_seconds=60),
            diagnostic_succeeded,
            has_issues_list,
        ],
    )


# =============================================================================
# Performance Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
@pytest.mark.slow
async def test_diagnostic_large_level(tool_caller):
    """Test diagnostic performance on a larger level."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={
            "asset_path": "/Game/Maps/LargeTestLevel",  # Would need actual large level
        },
    )

    diag_data = json.loads(result.text_content)
    print(f"Large level diagnostic: {diag_data}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_diagnostic_call_history(tool_caller):
    """Test that diagnostic calls are tracked in history."""
    # Make diagnostic call
    await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={"asset_path": "/Game/Maps/TestLevel"},
    )

    # Check history
    diag_calls = tool_caller.get_calls_for_tool("editor.asset.diagnostic")
    assert len(diag_calls) >= 1, "Should have diagnostic calls in history"

    last_call = diag_calls[-1]
    assert last_call.arguments.get("asset_path") == "/Game/Maps/TestLevel"

    print(f"Diagnostic call tracked: {last_call.name}")
    print(f"  Arguments: {last_call.arguments}")
    print(f"  Duration: {last_call.duration_seconds:.2f}s")


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_diagnostic_special_characters_in_path(tool_caller):
    """Test diagnostic with special characters in asset path."""
    special_paths = [
        "/Game/Maps/Test Level",      # Space
        "/Game/Maps/Test_Level",      # Underscore (valid)
        "/Game/Maps/Test-Level",      # Hyphen
    ]

    for path in special_paths:
        result = await tool_caller.call(
            "editor.asset.diagnostic",
            arguments={"asset_path": path},
        )

        diag_data = json.loads(result.text_content)
        print(f"Special path '{path}': success={diag_data.get('success')}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_diagnostic_unicode_asset_path(tool_caller):
    """Test diagnostic with unicode characters in path."""
    result = await tool_caller.call(
        "editor.asset.diagnostic",
        arguments={
            "asset_path": "/Game/Maps/测试关卡",  # Chinese characters
        },
    )

    diag_data = json.loads(result.text_content)
    print(f"Unicode path result: {diag_data}")
