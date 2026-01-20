"""Pydantic models for MCP test configuration."""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    name: str = Field(..., description="Unique server identifier")
    command: str = Field(..., description="Command to start the server")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    cwd: Optional[Path] = Field(None, description="Working directory for the server")
    startup_timeout: float = Field(30.0, description="Server startup timeout in seconds")
    shutdown_timeout: float = Field(10.0, description="Server shutdown timeout in seconds")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Validate that command is not empty."""
        if not v.strip():
            raise ValueError("Command cannot be empty")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty and contains valid characters."""
        if not v.strip():
            raise ValueError("Server name cannot be empty")
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Server name must be alphanumeric (with dashes/underscores allowed)")
        return v


class MCPTestConfig(BaseModel):
    """Root configuration model for MCP tests."""

    servers: List[ServerConfig] = Field(
        default_factory=list, description="List of MCP servers to test"
    )
    default_timeout: float = Field(30.0, description="Default timeout for tool calls in seconds")
    log_level: str = Field("INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    log_mcp_messages: bool = Field(True, description="Whether to log MCP protocol messages")
    cleanup_on_failure: bool = Field(
        True, description="Whether to clean up files even when tests fail"
    )
    parallel_servers: bool = Field(False, description="Whether to start servers in parallel")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper

    @field_validator("default_timeout")
    @classmethod
    def validate_timeout(cls, v: float) -> float:
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    def get_server(self, name: str) -> Optional[ServerConfig]:
        """Get a server configuration by name."""
        for server in self.servers:
            if server.name == name:
                return server
        return None

    def get_server_names(self) -> List[str]:
        """Get list of all server names."""
        return [server.name for server in self.servers]


class TestConfig(BaseModel):
    """Per-test configuration via markers."""

    timeout: Optional[float] = Field(None, description="Override timeout for this test")
    server: Optional[str] = Field(None, description="Specific server to use for this test")
    cleanup_paths: List[Path] = Field(
        default_factory=list, description="Additional paths to clean up after test"
    )
