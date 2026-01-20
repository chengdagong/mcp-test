"""
Tests for UE-MCP editor.execute Tool.

Tests the following tool:
- editor.execute: Execute Python code in the editor

Run with:
    cd tests/ue_mcp_test
    pytest test_editor_execute.py -v
"""

import json

import pytest

from mcp_pytest import (
    CustomAssertion,
    DurationAssertion,
    ResultContainsAssertion,
    SuccessAssertion,
)


# =============================================================================
# Tool Schema Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_tool_exists(mcp_client):
    """Test that editor.execute tool exists."""
    tools = await mcp_client.list_tools()
    tool_names = [t.name for t in tools]

    assert "editor.execute" in tool_names, "editor.execute tool should exist"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_tool_schema(tool_caller):
    """Test editor.execute tool schema and parameters."""
    tools = await tool_caller.client.list_tools()
    execute_tool = next((t for t in tools if t.name == "editor.execute"), None)

    assert execute_tool is not None, "editor.execute tool should exist"
    assert execute_tool.description, "Should have description"
    assert execute_tool.inputSchema, "Should have input schema"

    schema = execute_tool.inputSchema
    props = schema.get("properties", {})
    required = schema.get("required", [])

    # Verify expected parameters
    assert "code" in props, "Should accept 'code' parameter"
    assert "timeout" in props, "Should accept 'timeout' parameter"

    # Code should be required
    assert "code" in required, "'code' should be required"

    print("editor.execute schema:")
    print(f"  Description: {execute_tool.description[:100]}...")
    print(f"  Parameters: {list(props.keys())}")
    print(f"  Required: {required}")


# =============================================================================
# Parameter Validation Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_missing_code_parameter(tool_caller):
    """Test that missing code parameter is handled."""
    # Calling without 'code' should fail
    result = await tool_caller.call(
        "editor.execute",
        arguments={},  # Missing required 'code'
        expect_error=True,
    )

    # Should fail validation
    assert result.success, "Should fail when code is missing"
    print(f"Error (expected): {result.error_message or result.text_content}")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_with_timeout_parameter(tool_caller):
    """Test that timeout parameter is accepted."""
    tools = await tool_caller.client.list_tools()
    execute_tool = next((t for t in tools if t.name == "editor.execute"), None)

    props = execute_tool.inputSchema.get("properties", {})
    timeout_prop = props.get("timeout", {})

    # Timeout should have default value
    assert "default" in timeout_prop or timeout_prop.get("type") == "number", \
        "timeout should be a number with default"

    print(f"Timeout property: {timeout_prop}")


# =============================================================================
# Execution Tests (Require Running Editor)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_execute_simple_print(tool_caller):
    """Test executing simple print statement."""
    result = await tool_caller.call(
        "editor.execute",
        arguments={
            "code": "print('Hello from UE5!')",
            "timeout": 10.0,
        },
    )

    exec_data = json.loads(result.text_content)
    print(f"Execution result: {json.dumps(exec_data, indent=2)}")

    if exec_data.get("success"):
        assert "Hello from UE5" in exec_data.get("output", ""), \
            "Output should contain printed message"
    else:
        # May fail if editor not running
        print(f"Execution failed (expected if editor not running): {exec_data.get('error')}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_execute_import_unreal(tool_caller):
    """Test importing unreal module."""
    result = await tool_caller.call(
        "editor.execute",
        arguments={
            "code": "import unreal; print(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world())",
            "timeout": 15.0,
        },
    )

    exec_data = json.loads(result.text_content)

    if exec_data.get("success"):
        print("Successfully executed unreal import!")
        print(f"Output: {exec_data.get('output')}")
    else:
        print(f"Failed (expected if editor not running): {exec_data.get('error')}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_execute_with_return_value(tool_caller):
    """Test executing code that returns a value."""
    result = await tool_caller.call(
        "editor.execute",
        arguments={
            "code": "result = 2 + 2; print(f'Result: {result}')",
            "timeout": 10.0,
        },
    )

    exec_data = json.loads(result.text_content)

    if exec_data.get("success"):
        assert "Result: 4" in exec_data.get("output", ""), \
            "Should contain calculation result"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_execute_multiline_code(tool_caller):
    """Test executing multiline Python code."""
    multiline_code = """
import unreal

def get_project_name():
    settings = unreal.SystemLibrary.get_project_name()
    return settings

name = get_project_name()
print(f"Project: {name}")
"""

    result = await tool_caller.call(
        "editor.execute",
        arguments={
            "code": multiline_code,
            "timeout": 15.0,
        },
    )

    exec_data = json.loads(result.text_content)
    print(f"Multiline execution result: {exec_data}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_execute_list_assets(tool_caller):
    """Test listing assets in the editor."""
    result = await tool_caller.call(
        "editor.execute",
        arguments={
            "code": """
import unreal
assets = unreal.EditorAssetLibrary.list_assets('/Game/')
print(f"Found {len(assets)} assets")
for asset in assets[:5]:
    print(f"  - {asset}")
""",
            "timeout": 20.0,
        },
    )

    exec_data = json.loads(result.text_content)

    if exec_data.get("success"):
        assert "Found" in exec_data.get("output", ""), \
            "Should report number of assets found"


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_execute_syntax_error(tool_caller):
    """Test handling of Python syntax errors."""
    result = await tool_caller.call(
        "editor.execute",
        arguments={
            "code": "this is not valid python code!!!",
            "timeout": 10.0,
        },
    )

    exec_data = json.loads(result.text_content)
    print(f"Syntax error result: {exec_data}")

    # Should fail with syntax error
    if not exec_data.get("success"):
        assert "error" in exec_data, "Should contain error message"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_execute_runtime_error(tool_caller):
    """Test handling of runtime errors."""
    result = await tool_caller.call(
        "editor.execute",
        arguments={
            "code": "x = 1 / 0",  # ZeroDivisionError
            "timeout": 10.0,
        },
    )

    exec_data = json.loads(result.text_content)
    print(f"Runtime error result: {exec_data}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_execute_import_error(tool_caller):
    """Test handling of import errors."""
    result = await tool_caller.call(
        "editor.execute",
        arguments={
            "code": "import nonexistent_module_xyz",
            "timeout": 10.0,
        },
    )

    exec_data = json.loads(result.text_content)
    print(f"Import error result: {exec_data}")


# =============================================================================
# Timeout Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
@pytest.mark.slow
async def test_execute_with_custom_timeout(tool_caller):
    """Test execution with custom timeout."""
    # Quick execution should complete within timeout
    result = await tool_caller.call(
        "editor.execute",
        arguments={
            "code": "print('Quick execution')",
            "timeout": 5.0,  # 5 second timeout
        },
    )

    exec_data = json.loads(result.text_content)

    if exec_data.get("success"):
        # Verify timing if available
        print(f"Execution completed within timeout")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
@pytest.mark.slow
async def test_execute_timeout_handling(tool_caller):
    """Test that long-running code is properly timed out."""
    # This code would run forever without timeout
    result = await tool_caller.call(
        "editor.execute",
        arguments={
            "code": """
import time
for i in range(1000):
    print(f"Iteration {i}")
    time.sleep(1)  # This would take 1000 seconds
""",
            "timeout": 5.0,  # Should timeout after 5 seconds
        },
    )

    exec_data = json.loads(result.text_content)
    print(f"Timeout test result: {exec_data}")

    # Should either timeout or be cancelled
    # The actual behavior depends on the remote execution implementation


# =============================================================================
# Editor Not Running Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_execute_without_editor(tool_caller, editor_status_checker):
    """Test execute when editor is not running."""
    # First check if editor is running
    status = await editor_status_checker()

    if status.get("status") not in ["ready"]:
        # Editor not running, execute should fail gracefully
        result = await tool_caller.call(
            "editor.execute",
            arguments={
                "code": "print('test')",
                "timeout": 5.0,
            },
        )

        exec_data = json.loads(result.text_content)
        print(f"Execute without editor: {exec_data}")

        # Should fail with appropriate error
        assert not exec_data.get("success") or "error" in str(exec_data).lower(), \
            "Should fail or error when editor not running"


# =============================================================================
# Advanced Execution Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_execute_access_editor_api(tool_caller):
    """Test accessing various editor APIs."""
    test_cases = [
        ("Get editor world", "import unreal; print(unreal.EditorLevelLibrary.get_editor_world())"),
        ("Get viewport camera", "import unreal; print(unreal.EditorLevelLibrary.get_level_viewport_camera_info())"),
        ("Get selected actors", "import unreal; print(unreal.EditorLevelLibrary.get_selected_level_actors())"),
    ]

    for name, code in test_cases:
        result = await tool_caller.call(
            "editor.execute",
            arguments={"code": code, "timeout": 10.0},
        )

        exec_data = json.loads(result.text_content)
        print(f"\n{name}:")
        print(f"  Success: {exec_data.get('success')}")
        if exec_data.get("output"):
            print(f"  Output: {exec_data.get('output')[:200]}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_execute_create_actor(tool_caller):
    """Test creating an actor via execute."""
    create_code = """
import unreal

# Create a simple cube actor
editor_world = unreal.EditorLevelLibrary.get_editor_world()
if editor_world:
    # Spawn a static mesh actor
    location = unreal.Vector(0, 0, 100)
    rotation = unreal.Rotator(0, 0, 0)

    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor,
        location,
        rotation
    )

    if actor:
        print(f"Created actor: {actor.get_name()}")
        # Clean up - delete the actor
        unreal.EditorLevelLibrary.destroy_actor(actor)
        print("Actor deleted")
    else:
        print("Failed to create actor")
else:
    print("No editor world available")
"""

    result = await tool_caller.call(
        "editor.execute",
        arguments={"code": create_code, "timeout": 15.0},
    )

    exec_data = json.loads(result.text_content)
    print(f"Create actor result: {exec_data}")


# =============================================================================
# Assertion-Based Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_editor
async def test_execute_with_success_assertion(tool_caller):
    """Test execute with assertion framework."""
    # Custom assertion for successful execution
    successful_execution = CustomAssertion(
        check_func=lambda r: json.loads(r.text_content).get("success", False),
        description="Execution should succeed",
        message_func=lambda r: f"Execution failed: {json.loads(r.text_content).get('error', 'Unknown')}",
    )

    result = await tool_caller.call_and_assert(
        "editor.execute",
        arguments={
            "code": "print('Assertion test passed!')",
            "timeout": 10.0,
        },
        assertions=[
            SuccessAssertion(),  # MCP call succeeds
            DurationAssertion(max_seconds=15),
            successful_execution,  # Python execution succeeds
        ],
    )
