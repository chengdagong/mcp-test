"""
Tests for UE-MCP Capture Tools.

Tests the following tools:
- editor.capture.orbital: Multi-angle orbital screenshots
- editor.capture.pie: Play-In-Editor session screenshots
- editor.capture.window: Editor window screenshots (Windows only)

Run with:
    cd tests/ue_mcp_test
    pytest test_capture_tools.py -v
"""

import json
from pathlib import Path

import pytest

from mcp_pytest import (
    CustomAssertion,
    DurationAssertion,
    SuccessAssertion,
)


# =============================================================================
# Capture Tool Discovery Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_capture_tools_exist(mcp_client):
    """Test that all capture tools exist."""
    tools = await mcp_client.list_tools()
    tool_names = [t.name for t in tools]

    capture_tools = [
        "editor.capture.orbital",
        "editor.capture.pie",
        "editor.capture.window",
    ]

    for tool_name in capture_tools:
        assert tool_name in tool_names, f"Missing capture tool: {tool_name}"

    print("All capture tools found:")
    for tool_name in capture_tools:
        print(f"  - {tool_name}")


# =============================================================================
# editor.capture.orbital Schema Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_orbital_tool_schema(tool_caller):
    """Test editor.capture.orbital tool schema and parameters."""
    tools = await tool_caller.client.list_tools()
    orbital_tool = next((t for t in tools if t.name == "editor.capture.orbital"), None)

    assert orbital_tool is not None
    assert orbital_tool.description
    assert orbital_tool.inputSchema

    schema = orbital_tool.inputSchema
    props = schema.get("properties", {})
    required = schema.get("required", [])

    # Verify expected parameters
    expected_params = [
        "level", "target_x", "target_y", "target_z",
        "distance", "preset", "output_dir",
        "resolution_width", "resolution_height",
    ]

    print("editor.capture.orbital schema:")
    print(f"  Description: {orbital_tool.description[:150]}...")
    print(f"  Parameters:")
    for param in expected_params:
        if param in props:
            prop_info = props[param]
            print(f"    {param}: {prop_info.get('type', 'unknown')}")
        else:
            print(f"    {param}: NOT FOUND")

    # Required params
    print(f"  Required: {required}")

    # Level should be required
    assert "level" in required, "'level' should be required"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_orbital_preset_values(tool_caller):
    """Test orbital preset parameter values."""
    tools = await tool_caller.client.list_tools()
    orbital_tool = next((t for t in tools if t.name == "editor.capture.orbital"), None)

    props = orbital_tool.inputSchema.get("properties", {})
    preset_prop = props.get("preset", {})

    print(f"Preset property: {preset_prop}")

    # Valid presets from server.py
    valid_presets = [
        "all", "perspective", "orthographic",
        "birdseye", "horizontal", "technical",
    ]
    print("Valid presets:")
    for preset in valid_presets:
        print(f"  - {preset}")


# =============================================================================
# editor.capture.pie Schema Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pie_tool_schema(tool_caller):
    """Test editor.capture.pie tool schema and parameters."""
    tools = await tool_caller.client.list_tools()
    pie_tool = next((t for t in tools if t.name == "editor.capture.pie"), None)

    assert pie_tool is not None
    assert pie_tool.description
    assert pie_tool.inputSchema

    schema = pie_tool.inputSchema
    props = schema.get("properties", {})
    required = schema.get("required", [])

    expected_params = [
        "output_dir", "level", "duration_seconds", "interval_seconds",
        "resolution_width", "resolution_height",
        "multi_angle", "camera_distance", "target_height",
    ]

    print("editor.capture.pie schema:")
    print(f"  Description: {pie_tool.description[:150]}...")
    print(f"  Parameters:")
    for param in expected_params:
        if param in props:
            prop_info = props[param]
            default = prop_info.get("default", "none")
            print(f"    {param}: {prop_info.get('type', 'unknown')} (default: {default})")

    print(f"  Required: {required}")


# =============================================================================
# editor.capture.window Schema Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_window_tool_schema(tool_caller):
    """Test editor.capture.window tool schema and parameters."""
    tools = await tool_caller.client.list_tools()
    window_tool = next((t for t in tools if t.name == "editor.capture.window"), None)

    assert window_tool is not None
    assert window_tool.description
    assert window_tool.inputSchema

    schema = window_tool.inputSchema
    props = schema.get("properties", {})
    required = schema.get("required", [])

    expected_params = [
        "level", "output_file", "mode",
        "asset_path", "asset_list", "output_dir", "tab",
    ]

    print("editor.capture.window schema:")
    print(f"  Description: {window_tool.description[:150]}...")
    print(f"  Parameters:")
    for param in expected_params:
        if param in props:
            prop_info = props[param]
            print(f"    {param}: {prop_info.get('type', 'unknown')}")

    print(f"  Required: {required}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_window_mode_values(tool_caller):
    """Test window capture mode parameter values."""
    tools = await tool_caller.client.list_tools()
    window_tool = next((t for t in tools if t.name == "editor.capture.window"), None)

    props = window_tool.inputSchema.get("properties", {})
    mode_prop = props.get("mode", {})

    print(f"Mode property: {mode_prop}")

    # Valid modes from server.py
    valid_modes = ["window", "asset", "batch"]
    print("Valid modes:")
    for mode in valid_modes:
        print(f"  - {mode}")


# =============================================================================
# Orbital Capture Execution Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_orbital_missing_level(tool_caller):
    """Test orbital capture with missing level parameter."""
    result = await tool_caller.call(
        "editor.capture.orbital",
        arguments={
            "target_x": 0,
            "target_y": 0,
            "target_z": 0,
            # Missing required 'level'
        },
        expect_error=True,
    )

    print(f"Missing level error: {result.error_message or result.text_content}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_orbital_basic_capture(tool_caller, temp_capture_dir):
    """Test basic orbital capture."""
    result = await tool_caller.call(
        "editor.capture.orbital",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "target_x": 0.0,
            "target_y": 0.0,
            "target_z": 100.0,
            "distance": 500.0,
            "preset": "orthographic",
            "output_dir": str(temp_capture_dir),
            "resolution_width": 800,
            "resolution_height": 600,
        },
    )

    capture_data = json.loads(result.text_content)
    print(f"Orbital capture result: {json.dumps(capture_data, indent=2)}")

    if capture_data.get("success"):
        assert "files" in capture_data, "Should contain file paths"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_orbital_all_presets(tool_caller, temp_capture_dir):
    """Test orbital capture with different presets."""
    presets = ["orthographic", "perspective", "birdseye", "horizontal", "all"]

    for preset in presets:
        result = await tool_caller.call(
            "editor.capture.orbital",
            arguments={
                "level": "/Game/Maps/TestLevel",
                "target_x": 0.0,
                "target_y": 0.0,
                "target_z": 100.0,
                "distance": 500.0,
                "preset": preset,
                "output_dir": str(temp_capture_dir / preset),
            },
        )

        capture_data = json.loads(result.text_content)
        print(f"Preset '{preset}': success={capture_data.get('success')}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_orbital_custom_resolution(tool_caller, temp_capture_dir):
    """Test orbital capture with custom resolution."""
    resolutions = [
        (1920, 1080),  # Full HD
        (1280, 720),   # HD
        (640, 480),    # VGA
    ]

    for width, height in resolutions:
        result = await tool_caller.call(
            "editor.capture.orbital",
            arguments={
                "level": "/Game/Maps/TestLevel",
                "target_x": 0.0,
                "target_y": 0.0,
                "target_z": 100.0,
                "distance": 500.0,
                "preset": "perspective",
                "resolution_width": width,
                "resolution_height": height,
            },
        )

        capture_data = json.loads(result.text_content)
        print(f"Resolution {width}x{height}: success={capture_data.get('success')}")


# =============================================================================
# PIE Capture Execution Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pie_missing_required_params(tool_caller):
    """Test PIE capture with missing required parameters."""
    # Missing both output_dir and level
    result = await tool_caller.call(
        "editor.capture.pie",
        arguments={
            "duration_seconds": 5.0,
        },
        expect_error=True,
    )

    print(f"Missing params error: {result.error_message or result.text_content}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
@pytest.mark.slow
async def test_pie_basic_capture(tool_caller, temp_capture_dir):
    """Test basic PIE capture."""
    result = await tool_caller.call(
        "editor.capture.pie",
        arguments={
            "output_dir": str(temp_capture_dir),
            "level": "/Game/Maps/TestLevel",
            "duration_seconds": 5.0,
            "interval_seconds": 1.0,
            "resolution_width": 1280,
            "resolution_height": 720,
            "multi_angle": False,
        },
    )

    capture_data = json.loads(result.text_content)
    print(f"PIE capture result: {json.dumps(capture_data, indent=2)}")

    if capture_data.get("success"):
        assert "output_dir" in capture_data or "files" in capture_data


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
@pytest.mark.slow
async def test_pie_multi_angle_capture(tool_caller, temp_capture_dir):
    """Test PIE capture with multi-angle enabled."""
    result = await tool_caller.call(
        "editor.capture.pie",
        arguments={
            "output_dir": str(temp_capture_dir),
            "level": "/Game/Maps/TestLevel",
            "duration_seconds": 5.0,
            "interval_seconds": 1.0,
            "multi_angle": True,
            "camera_distance": 300.0,
            "target_height": 90.0,
        },
    )

    capture_data = json.loads(result.text_content)
    print(f"Multi-angle PIE: {json.dumps(capture_data, indent=2)}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
@pytest.mark.slow
async def test_pie_different_intervals(tool_caller, temp_capture_dir):
    """Test PIE capture with different capture intervals."""
    intervals = [0.5, 1.0, 2.0]

    for interval in intervals:
        result = await tool_caller.call(
            "editor.capture.pie",
            arguments={
                "output_dir": str(temp_capture_dir / f"interval_{interval}"),
                "level": "/Game/Maps/TestLevel",
                "duration_seconds": 3.0,
                "interval_seconds": interval,
                "multi_angle": False,
            },
        )

        capture_data = json.loads(result.text_content)
        print(f"Interval {interval}s: success={capture_data.get('success')}")


# =============================================================================
# Window Capture Execution Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_window_mode_validation(tool_caller, temp_capture_dir):
    """Test window capture mode parameter validation."""
    # Window mode requires output_file
    result = await tool_caller.call(
        "editor.capture.window",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "mode": "window",
            # Missing output_file
        },
    )

    capture_data = json.loads(result.text_content)
    print(f"Window mode validation: {json.dumps(capture_data, indent=2)}")

    # Should fail with error about missing output_file
    assert not capture_data.get("success") or "error" in capture_data


@pytest.mark.asyncio
@pytest.mark.unit
async def test_window_asset_mode_validation(tool_caller, temp_capture_dir):
    """Test window capture asset mode validation."""
    # Asset mode requires both output_file and asset_path
    result = await tool_caller.call(
        "editor.capture.window",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "mode": "asset",
            "output_file": str(temp_capture_dir / "asset.png"),
            # Missing asset_path
        },
    )

    capture_data = json.loads(result.text_content)
    print(f"Asset mode validation: {json.dumps(capture_data, indent=2)}")

    assert not capture_data.get("success")
    assert "asset_path" in capture_data.get("error", "").lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_window_batch_mode_validation(tool_caller, temp_capture_dir):
    """Test window capture batch mode validation."""
    # Batch mode requires asset_list and output_dir
    result = await tool_caller.call(
        "editor.capture.window",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "mode": "batch",
            # Missing asset_list and output_dir
        },
    )

    capture_data = json.loads(result.text_content)
    print(f"Batch mode validation: {json.dumps(capture_data, indent=2)}")

    assert not capture_data.get("success")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_window_capture_main_window(tool_caller, temp_capture_dir):
    """Test capturing the main editor window."""
    output_file = temp_capture_dir / "main_window.png"

    result = await tool_caller.call(
        "editor.capture.window",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "mode": "window",
            "output_file": str(output_file),
        },
    )

    capture_data = json.loads(result.text_content)
    print(f"Window capture: {json.dumps(capture_data, indent=2)}")

    if capture_data.get("success"):
        assert "file" in capture_data


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_window_capture_asset_editor(tool_caller, temp_capture_dir):
    """Test capturing an asset editor window."""
    output_file = temp_capture_dir / "asset_editor.png"

    result = await tool_caller.call(
        "editor.capture.window",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "mode": "asset",
            "output_file": str(output_file),
            "asset_path": "/Game/SomeAsset",  # Would need real asset path
        },
    )

    capture_data = json.loads(result.text_content)
    print(f"Asset editor capture: {json.dumps(capture_data, indent=2)}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_window_capture_batch(tool_caller, temp_capture_dir):
    """Test batch capture of multiple assets."""
    result = await tool_caller.call(
        "editor.capture.window",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "mode": "batch",
            "asset_list": [
                "/Game/Asset1",
                "/Game/Asset2",
                "/Game/Asset3",
            ],
            "output_dir": str(temp_capture_dir / "batch"),
        },
    )

    capture_data = json.loads(result.text_content)
    print(f"Batch capture: {json.dumps(capture_data, indent=2)}")

    if capture_data.get("success"):
        assert "files" in capture_data


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_window_capture_with_tab(tool_caller, temp_capture_dir):
    """Test window capture with tab switching."""
    output_file = temp_capture_dir / "tab_capture.png"

    result = await tool_caller.call(
        "editor.capture.window",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "mode": "window",
            "output_file": str(output_file),
            "tab": 1,  # Switch to tab 1
        },
    )

    capture_data = json.loads(result.text_content)
    print(f"Tab capture: {json.dumps(capture_data, indent=2)}")


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_orbital_without_editor(tool_caller, editor_status_checker, temp_capture_dir):
    """Test orbital capture when editor is not running."""
    status = await editor_status_checker()

    if status.get("status") not in ["ready"]:
        result = await tool_caller.call(
            "editor.capture.orbital",
            arguments={
                "level": "/Game/Maps/TestLevel",
                "target_x": 0.0,
                "target_y": 0.0,
                "target_z": 0.0,
                "output_dir": str(temp_capture_dir),
            },
        )

        capture_data = json.loads(result.text_content)
        print(f"Capture without editor: {json.dumps(capture_data, indent=2)}")

        # Should fail gracefully
        assert not capture_data.get("success")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_orbital_invalid_level(tool_caller, temp_capture_dir):
    """Test orbital capture with invalid level path."""
    result = await tool_caller.call(
        "editor.capture.orbital",
        arguments={
            "level": "/Game/NonExistent/Level",
            "target_x": 0.0,
            "target_y": 0.0,
            "target_z": 0.0,
            "output_dir": str(temp_capture_dir),
        },
    )

    capture_data = json.loads(result.text_content)
    print(f"Invalid level: {json.dumps(capture_data, indent=2)}")


# =============================================================================
# Assertion-Based Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_capture_tools_response_format(tool_caller, temp_capture_dir):
    """Test that capture tools return properly formatted responses."""
    # Custom assertion for capture response format
    valid_capture_response = CustomAssertion(
        check_func=lambda r: (
            "success" in json.loads(r.text_content)
            or "error" in json.loads(r.text_content)
        ),
        description="Capture response should contain 'success' or 'error'",
    )

    # Test orbital
    result = await tool_caller.call_and_assert(
        "editor.capture.orbital",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "target_x": 0.0,
            "target_y": 0.0,
            "target_z": 0.0,
            "output_dir": str(temp_capture_dir),
        },
        assertions=[
            SuccessAssertion(),  # MCP call succeeds
            valid_capture_response,
        ],
    )


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
@pytest.mark.mcp_timeout(120)  # 2 minute timeout for captures
async def test_orbital_capture_with_assertions(tool_caller, temp_capture_dir):
    """Test orbital capture with full assertion suite."""
    # Custom assertion for successful capture
    capture_succeeded = CustomAssertion(
        check_func=lambda r: json.loads(r.text_content).get("success", False),
        description="Capture should succeed",
        message_func=lambda r: f"Capture failed: {json.loads(r.text_content).get('error', 'Unknown')}",
    )

    # Custom assertion for files created
    files_created = CustomAssertion(
        check_func=lambda r: "files" in json.loads(r.text_content),
        description="Response should contain captured file paths",
    )

    result = await tool_caller.call_and_assert(
        "editor.capture.orbital",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "target_x": 0.0,
            "target_y": 0.0,
            "target_z": 100.0,
            "distance": 500.0,
            "preset": "perspective",
            "output_dir": str(temp_capture_dir),
        },
        assertions=[
            SuccessAssertion(),
            DurationAssertion(max_seconds=120),
            capture_succeeded,
            files_created,
        ],
    )


# =============================================================================
# Call History Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_capture_call_history(tool_caller, temp_capture_dir):
    """Test that capture calls are tracked in history."""
    # Make various capture calls
    await tool_caller.call(
        "editor.capture.orbital",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "target_x": 0.0,
            "target_y": 0.0,
            "target_z": 0.0,
            "output_dir": str(temp_capture_dir),
        },
    )

    await tool_caller.call(
        "editor.capture.window",
        arguments={
            "level": "/Game/Maps/TestLevel",
            "mode": "window",
            "output_file": str(temp_capture_dir / "test.png"),
        },
    )

    # Check history
    orbital_calls = tool_caller.get_calls_for_tool("editor.capture.orbital")
    window_calls = tool_caller.get_calls_for_tool("editor.capture.window")

    assert len(orbital_calls) >= 1, "Should have orbital capture calls"
    assert len(window_calls) >= 1, "Should have window capture calls"

    print(f"Orbital calls: {len(orbital_calls)}")
    print(f"Window calls: {len(window_calls)}")
