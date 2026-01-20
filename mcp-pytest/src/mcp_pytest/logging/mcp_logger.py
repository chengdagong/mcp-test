"""MCP communication logger with detailed protocol tracking."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class MessageDirection(Enum):
    """Direction of MCP message."""

    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    CONNECTION = "connection"


@dataclass
class MCPMessage:
    """Represents a logged MCP message."""

    timestamp: datetime
    direction: MessageDirection
    server_name: str
    method: str
    data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction.value,
            "server": self.server_name,
            "method": self.method,
            "data": self.data,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class ColoredFormatter(logging.Formatter):
    """Formatter with color support for console output."""

    COLORS = {
        "RESET": "\033[0m",
        "BOLD": "\033[1m",
        "BLUE": "\033[94m",
        "GREEN": "\033[92m",
        "YELLOW": "\033[93m",
        "RED": "\033[91m",
        "CYAN": "\033[96m",
        "MAGENTA": "\033[95m",
    }

    DIRECTION_COLORS = {
        MessageDirection.REQUEST: "BLUE",
        MessageDirection.RESPONSE: "GREEN",
        MessageDirection.ERROR: "RED",
        MessageDirection.CONNECTION: "CYAN",
    }

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        # Get MCP-specific data if available
        mcp_data = getattr(record, "mcp_data", None)

        if mcp_data and isinstance(mcp_data, MCPMessage):
            return self._format_mcp_message(mcp_data)

        # Fall back to standard formatting
        return super().format(record)

    def _format_mcp_message(self, msg: MCPMessage) -> str:
        """Format an MCP message for console output."""
        timestamp = msg.timestamp.strftime("%H:%M:%S.%f")[:-3]

        direction_symbol = {
            MessageDirection.REQUEST: "→",
            MessageDirection.RESPONSE: "←",
            MessageDirection.ERROR: "✗",
            MessageDirection.CONNECTION: "◆",
        }.get(msg.direction, "?")

        color = self.DIRECTION_COLORS.get(msg.direction, "RESET")

        # Build message parts
        parts = [
            f"[{timestamp}]",
            f"[{msg.server_name}]",
            direction_symbol,
            msg.method,
        ]

        if msg.duration_ms is not None:
            parts.append(f"({msg.duration_ms:.1f}ms)")

        if msg.error:
            parts.append(f"ERROR: {msg.error}")
        elif msg.data:
            data_str = json.dumps(msg.data, default=str)
            if len(data_str) > 100:
                data_str = data_str[:100] + "..."
            parts.append(data_str)

        text = " ".join(parts)

        if self.use_colors:
            return f"{self.COLORS[color]}{text}{self.COLORS['RESET']}"
        return text


class MCPLogger:
    """
    Logger for MCP protocol communications.

    Provides:
    - Detailed request/response logging
    - Console output with colors
    - JSON export for debugging
    - Message history tracking
    """

    def __init__(
        self,
        name: str = "mcp_pytest",
        level: str = "INFO",
        log_to_console: bool = True,
        log_to_file: Optional[Path] = None,
        use_colors: bool = True,
    ):
        """
        Initialize MCP logger.

        Args:
            name: Logger name.
            level: Logging level (DEBUG, INFO, WARNING, ERROR).
            log_to_console: Whether to log to console.
            log_to_file: Optional path to log file.
            use_colors: Whether to use colors in console output.
        """
        self._name = name
        self._logger = logging.getLogger(f"mcp_pytest.{name}")
        self._logger.setLevel(getattr(logging, level.upper()))
        self._messages: List[MCPMessage] = []
        self._request_times: Dict[str, datetime] = {}

        # Prevent duplicate handlers
        self._logger.handlers.clear()

        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(ColoredFormatter(use_colors=use_colors))
            self._logger.addHandler(console_handler)

        if log_to_file:
            file_handler = logging.FileHandler(log_to_file)
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            self._logger.addHandler(file_handler)

    def log_request(
        self,
        server_name: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Log an outgoing MCP request.

        Args:
            server_name: Name of the target server.
            method: MCP method being called.
            params: Request parameters.

        Returns:
            Request ID for correlation with response.
        """
        timestamp = datetime.now()
        request_id = f"{server_name}:{method}:{timestamp.timestamp()}"

        self._request_times[request_id] = timestamp

        message = MCPMessage(
            timestamp=timestamp,
            direction=MessageDirection.REQUEST,
            server_name=server_name,
            method=method,
            data=params,
        )

        self._messages.append(message)
        self._log_message(message)

        return request_id

    def log_response(
        self,
        server_name: str,
        method: str,
        result: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Log an incoming MCP response.

        Args:
            server_name: Name of the source server.
            method: MCP method that was called.
            result: Response result data.
            request_id: Optional request ID for duration calculation.
        """
        timestamp = datetime.now()
        duration_ms = None

        if request_id and request_id in self._request_times:
            start_time = self._request_times.pop(request_id)
            duration_ms = (timestamp - start_time).total_seconds() * 1000

        message = MCPMessage(
            timestamp=timestamp,
            direction=MessageDirection.RESPONSE,
            server_name=server_name,
            method=method,
            data=result,
            duration_ms=duration_ms,
        )

        self._messages.append(message)
        self._log_message(message)

    def log_error(
        self,
        server_name: str,
        method: str,
        error: str,
    ) -> None:
        """
        Log an MCP error.

        Args:
            server_name: Name of the server.
            method: MCP method that failed.
            error: Error message.
        """
        message = MCPMessage(
            timestamp=datetime.now(),
            direction=MessageDirection.ERROR,
            server_name=server_name,
            method=method,
            error=error,
        )

        self._messages.append(message)
        self._log_message(message, level=logging.ERROR)

    def log_connection(self, server_name: str, status: str) -> None:
        """
        Log a connection status change.

        Args:
            server_name: Name of the server.
            status: Connection status (connected, disconnected, etc.).
        """
        message = MCPMessage(
            timestamp=datetime.now(),
            direction=MessageDirection.CONNECTION,
            server_name=server_name,
            method=f"connection/{status}",
        )

        self._messages.append(message)
        self._log_message(message)

    def _log_message(
        self,
        message: MCPMessage,
        level: int = logging.INFO,
    ) -> None:
        """Log a message through the Python logger."""
        record = self._logger.makeRecord(
            name=self._logger.name,
            level=level,
            fn="",
            lno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        record.mcp_data = message
        self._logger.handle(record)

    def get_messages(
        self,
        server_name: Optional[str] = None,
        direction: Optional[MessageDirection] = None,
    ) -> List[MCPMessage]:
        """
        Get logged messages with optional filtering.

        Args:
            server_name: Filter by server name.
            direction: Filter by message direction.

        Returns:
            List of matching messages.
        """
        messages = self._messages

        if server_name:
            messages = [m for m in messages if m.server_name == server_name]

        if direction:
            messages = [m for m in messages if m.direction == direction]

        return messages

    def export_to_json(self, filepath: Path | str) -> None:
        """
        Export all messages to JSON file.

        Args:
            filepath: Path to output JSON file.
        """
        data = [msg.to_dict() for msg in self._messages]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def clear(self) -> None:
        """Clear message history."""
        self._messages.clear()
        self._request_times.clear()

    @property
    def message_count(self) -> int:
        """Get total number of logged messages."""
        return len(self._messages)
