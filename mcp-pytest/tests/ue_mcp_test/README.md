# UE-MCP Tool Tests

This directory contains comprehensive tests for all UE-MCP (Unreal Engine MCP Server) tools.

## Test Categories

### 1. Editor Management Tests (`test_editor_management.py`)
- `editor.launch` - Start the Unreal Editor
- `editor.status` - Get editor status
- `editor.stop` - Stop the editor

### 2. Code Execution Tests (`test_editor_execute.py`)
- `editor.execute` - Execute Python code in the editor

### 3. Configuration Tests (`test_editor_configure.py`)
- `editor.configure` - Check and fix project configuration
- `editor.pip_install` - Install Python packages in UE5

### 4. Build Tests (`test_project_build.py`)
- `project.build` - Build the UE5 project using UnrealBuildTool

### 5. Capture Tools Tests (`test_capture_tools.py`)
- `editor.capture.orbital` - Multi-angle orbital screenshots
- `editor.capture.pie` - Play-In-Editor session screenshots
- `editor.capture.window` - Editor window screenshots (Windows only)

### 6. Diagnostic Tools Tests (`test_diagnostic_tools.py`)
- `editor.asset.diagnostic` - Run diagnostics on UE5 assets

## Test Markers

Tests are marked with the following markers:

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | Unit tests (no UE5 required) |
| `@pytest.mark.integration` | Integration tests (may require UE5) |
| `@pytest.mark.requires_editor` | Requires running UE Editor |
| `@pytest.mark.slow` | Slow tests (may take minutes) |
| `@pytest.mark.mock` | Tests using mocked dependencies |
| `@pytest.mark.mcp_timeout(N)` | Custom timeout of N seconds |

## Running Tests

### Prerequisites

1. Install mcp-pytest:
   ```bash
   cd D:/Code/mcp-test/mcp-pytest
   pip install -e .
   ```

2. Ensure UE-MCP server is available:
   ```bash
   cd D:/Code/ue-mcp
   uv sync
   ```

### Run All Tests

```bash
cd D:/Code/mcp-test/mcp-pytest/tests/ue_mcp_test
pytest -v
```

### Run Unit Tests Only (No UE5 Required)

```bash
pytest -v -m unit
```

### Run Integration Tests (Requires UE5)

```bash
pytest -v -m integration
```

### Run Tests Requiring Running Editor

```bash
pytest -v -m requires_editor
```

### Skip Slow Tests

```bash
pytest -v -m "not slow"
```

### Run Specific Test File

```bash
pytest test_editor_management.py -v
pytest test_capture_tools.py -v
```

### Run Specific Test

```bash
pytest test_editor_management.py::test_server_connection -v
```

## Configuration

### mcp_servers.yaml

The MCP server configuration is in `mcp_servers.yaml`. Update paths if needed:

```yaml
servers:
  - name: ue-mcp
    command: uv
    args:
      - "run"
      - "--directory"
      - "D:/Code/ue-mcp"  # Update this path
      - "ue-mcp"
    cwd: "D:/Code/ue-mcp/tests/fixtures/EmptyProjectTemplate"
```

### pytest.ini

Test configuration in `pytest.ini`:
- Async mode enabled
- Custom markers defined
- Logging configured

## Test Assertions

Tests use mcp-pytest assertion framework:

```python
from mcp_pytest import (
    SuccessAssertion,      # MCP call succeeds
    DurationAssertion,      # Execution time limit
    ResultContainsAssertion, # Result contains text
    ResultMatchesAssertion,  # Result matches regex
    ErrorAssertion,          # Expect error
    CustomAssertion,         # Custom validation
)
```

### Example Custom Assertion

```python
# Check that response has expected structure
valid_response = CustomAssertion(
    check_func=lambda r: "success" in json.loads(r.text_content),
    description="Response should contain 'success' field",
)
```

## Directory Structure

```
ue_mcp_test/
├── conftest.py              # Shared fixtures
├── mcp_servers.yaml         # MCP server configuration
├── pytest.ini               # Pytest configuration
├── README.md                # This file
├── test_editor_management.py  # Editor management tests
├── test_editor_execute.py     # Code execution tests
├── test_editor_configure.py   # Configuration tests
├── test_project_build.py      # Build tests
├── test_capture_tools.py      # Capture tool tests
└── test_diagnostic_tools.py   # Diagnostic tool tests
```

## Tested Tools Summary

| Tool | Test File | Unit Tests | Integration Tests |
|------|-----------|------------|-------------------|
| `editor.launch` | test_editor_management.py | ✓ | ✓ |
| `editor.status` | test_editor_management.py | ✓ | ✓ |
| `editor.stop` | test_editor_management.py | ✓ | ✓ |
| `editor.execute` | test_editor_execute.py | ✓ | ✓ |
| `editor.configure` | test_editor_configure.py | ✓ | ✓ |
| `editor.pip_install` | test_editor_configure.py | ✓ | ✓ |
| `project.build` | test_project_build.py | ✓ | ✓ |
| `editor.capture.orbital` | test_capture_tools.py | ✓ | ✓ |
| `editor.capture.pie` | test_capture_tools.py | ✓ | ✓ |
| `editor.capture.window` | test_capture_tools.py | ✓ | ✓ |
| `editor.asset.diagnostic` | test_diagnostic_tools.py | ✓ | ✓ |
