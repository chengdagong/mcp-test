# mcp-pytest

A pytest plugin for testing MCP (Model Context Protocol) servers.

## Features

- **Simple Setup**: Configure servers via YAML, write tests in Python
- **Async Support**: Built on pytest-asyncio for async/await testing
- **Multiple Servers**: Test multiple MCP servers in parallel
- **Rich Assertions**: Built-in assertions for common test patterns
- **Auto Cleanup**: Automatic cleanup of files created during tests
- **Detailed Logging**: Full MCP protocol logging with colors
- **HTML Reports**: Integration with pytest-html for visual reports

## Installation

```bash
pip install mcp-pytest
```

Or for development:

```bash
git clone https://github.com/yourname/mcp-pytest.git
cd mcp-pytest
pip install -e .
```

## Quick Start

### 1. Configure Your Servers

Create `mcp_servers.yaml` in your test directory:

```yaml
servers:
  - name: my-mcp-server
    command: python
    args: ["-m", "my_mcp_server"]
    startup_timeout: 30

default_timeout: 30
log_level: INFO
```

### 2. Write Tests

```python
import pytest
from mcp_pytest import SuccessAssertion, DurationAssertion

@pytest.mark.asyncio
async def test_list_tools(mcp_client):
    """Test that server exposes tools."""
    tools = await mcp_client.list_tools()
    assert len(tools) > 0

@pytest.mark.asyncio
async def test_tool_call(tool_caller):
    """Test calling a tool."""
    result = await tool_caller.call(
        "my_tool",
        arguments={"param": "value"}
    )
    assert result.success

@pytest.mark.asyncio
@pytest.mark.mcp_timeout(60)
async def test_with_assertions(tool_caller):
    """Test with built-in assertions."""
    result = await tool_caller.call_and_assert(
        "my_tool",
        arguments={"param": "value"},
        assertions=[
            SuccessAssertion(),
            DurationAssertion(30),
        ]
    )
```

### 3. Run Tests

```bash
pytest tests/ -v
```

## Configuration

### pytest.ini

```ini
[pytest]
mcp_config_file = mcp_servers.yaml
mcp_default_timeout = 30
mcp_log_messages = true
asyncio_mode = auto
asyncio_default_fixture_loop_scope = module
```

### Command Line Options

```bash
pytest --mcp-config=path/to/config.yaml  # Specify config file
pytest --mcp-log-level=DEBUG             # Set log level
pytest --mcp-no-cleanup                  # Disable auto cleanup
pytest --mcp-log-file=mcp.log            # Log to file
```

## Fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mcp_config` | session | Loaded configuration |
| `mcp_logger` | session | MCP communication logger |
| `mcp_server_manager` | module | Manages all server connections |
| `mcp_client` | module | Default MCP client session |
| `mcp_server` | function | Specific server (via marker) |
| `tool_caller` | function | Tool calling helper |
| `file_tracker` | module | Tracks files for cleanup |
| `file_cleaner` | module | Cleans up tracked files |

## Markers

```python
@pytest.mark.mcp_timeout(60)           # Set timeout for this test
@pytest.mark.mcp_server("server-name") # Use specific server
@pytest.mark.mcp_cleanup("/path")      # Additional cleanup paths
@pytest.mark.mcp_skip_cleanup          # Skip cleanup for debugging
```

## Assertions

### Built-in Assertions

```python
from mcp_pytest import (
    SuccessAssertion,       # Tool call succeeded
    ErrorAssertion,         # Tool call failed (with optional pattern)
    ResultContainsAssertion,# Result contains string
    ResultMatchesAssertion, # Result matches regex
    ResultEqualsAssertion,  # Result equals exactly
    DurationAssertion,      # Completed within time limit
    CustomAssertion,        # Custom check function
    NotAssertion,           # Negate another assertion
    AllOf,                  # All assertions must pass
    AnyOf,                  # Any assertion must pass
)
```

### Custom Assertions

```python
from mcp_pytest import CustomAssertion

my_assertion = CustomAssertion(
    check_func=lambda r: "success" in r.text_content.lower(),
    description="Result indicates success"
)

result = await tool_caller.call_and_assert(
    "my_tool",
    assertions=[my_assertion]
)
```

## Multi-Server Testing

```python
@pytest.mark.asyncio
async def test_cross_server(mcp_server_manager):
    """Test interaction between servers."""
    server_a = mcp_server_manager.get_session("server-a")
    server_b = mcp_server_manager.get_session("server-b")

    result_a = await server_a.call_tool("tool_a", {})
    result_b = await server_b.call_tool("tool_b", {"input": result_a})
```

## File Cleanup

```python
@pytest.mark.asyncio
async def test_with_cleanup(tool_caller, file_tracker):
    """Files created during test are automatically cleaned up."""
    # Track a directory
    file_tracker.start_watching("/output", "test_with_cleanup")

    # Tool creates files in /output
    await tool_caller.call("create_files", {"path": "/output"})

    # Cleanup happens automatically after test
```

## Logging

MCP protocol messages are logged with colors:

```
[14:23:45.123] [my-server] → tools/list {}
[14:23:45.456] [my-server] ← tools/list {"tool_count": 5}
[14:23:46.789] [my-server] → tools/call/my_tool {"param": "value"}
[14:23:47.012] [my-server] ← tools/call/my_tool (223.4ms) {"is_error": false}
```

Export logs to JSON for debugging:

```python
mcp_logger.export_to_json("mcp_log.json")
```

## License

MIT
