"""Tool calling helper with enhanced result handling."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from mcp.types import CallToolResult, TextContent

if TYPE_CHECKING:
    from mcp_pytest.assertions.base import BaseAssertion
    from mcp_pytest.cleanup.tracker import FileTracker
    from mcp_pytest.client.session import MCPClientSession


@dataclass
class ToolCallResult:
    """Enhanced tool call result with metadata."""

    name: str
    arguments: Dict[str, Any]
    result: CallToolResult
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None
    _text_content: Optional[str] = field(default=None, repr=False)

    @property
    def text_content(self) -> str:
        """
        Get text content from result.

        Returns:
            Concatenated text content from all TextContent blocks.
        """
        if self._text_content is not None:
            return self._text_content

        if not self.result.content:
            return ""

        texts = []
        for content in self.result.content:
            if isinstance(content, TextContent):
                texts.append(content.text)
            elif hasattr(content, "text"):
                texts.append(str(content.text))

        self._text_content = "\n".join(texts)
        return self._text_content

    @property
    def is_error(self) -> bool:
        """Check if result is an error."""
        return hasattr(self.result, "isError") and self.result.isError

    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"ToolCallResult({self.name}, {status}, {self.duration_seconds:.2f}s)"


class ToolCaller:
    """
    Helper class for calling MCP tools with validation and assertions.

    Provides:
    - Enhanced result handling
    - Duration tracking
    - Call history
    - Assertion integration
    - File tracking integration
    """

    def __init__(
        self,
        session: MCPClientSession,
        default_timeout: float = 30.0,
        file_tracker: Optional[FileTracker] = None,
    ):
        """
        Initialize tool caller.

        Args:
            session: MCP client session to use for calls.
            default_timeout: Default timeout for tool calls in seconds.
            file_tracker: Optional file tracker for cleanup.
        """
        self._session = session
        self._default_timeout = default_timeout
        self._file_tracker = file_tracker
        self._call_history: List[ToolCallResult] = []

    @property
    def session(self) -> MCPClientSession:
        """Get the underlying MCP session."""
        return self._session

    @property
    def call_history(self) -> List[ToolCallResult]:
        """Get history of all tool calls."""
        return self._call_history.copy()

    async def call(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        expect_error: bool = False,
    ) -> ToolCallResult:
        """
        Call a tool and return enhanced result.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.
            timeout: Optional timeout in seconds.
            expect_error: If True, success is determined by whether an error occurred.

        Returns:
            ToolCallResult with call details and result.
        """
        if arguments is None:
            arguments = {}

        effective_timeout = timeout if timeout is not None else self._default_timeout

        start_time = time.perf_counter()
        error_message: Optional[str] = None
        success = True

        try:
            result = await self._session.call_tool(tool_name, arguments, effective_timeout)
            duration = time.perf_counter() - start_time

            # Determine success
            is_error = hasattr(result, "isError") and result.isError

            if expect_error:
                success = is_error
                if not success:
                    error_message = "Expected error but tool succeeded"
            else:
                success = not is_error
                if is_error:
                    # Extract error message from content
                    error_message = self._extract_error_message(result)

        except TimeoutError as e:
            duration = time.perf_counter() - start_time
            result = CallToolResult(content=[], isError=True)
            success = expect_error
            error_message = str(e)

        except Exception as e:
            duration = time.perf_counter() - start_time
            result = CallToolResult(content=[], isError=True)
            success = expect_error
            error_message = f"Tool call failed: {e}"

        call_result = ToolCallResult(
            name=tool_name,
            arguments=arguments,
            result=result,
            duration_seconds=duration,
            success=success,
            error_message=error_message,
        )

        self._call_history.append(call_result)
        return call_result

    async def call_and_assert(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        assertions: Optional[List[BaseAssertion]] = None,
        timeout: Optional[float] = None,
    ) -> ToolCallResult:
        """
        Call a tool and run assertions on the result.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.
            assertions: List of assertions to check.
            timeout: Optional timeout in seconds.

        Returns:
            ToolCallResult with call details.

        Raises:
            AssertionError: If any assertion fails.
        """
        result = await self.call(tool_name, arguments, timeout)

        if assertions:
            failed_assertions = []

            for assertion in assertions:
                assertion_result = assertion.check(result)
                if not assertion_result.passed:
                    failed_assertions.append(
                        f"- {assertion.description}: {assertion_result.message}"
                    )

            if failed_assertions:
                raise AssertionError(
                    f"Tool call '{tool_name}' failed assertions:\n"
                    + "\n".join(failed_assertions)
                )

        return result

    async def list_tools(self) -> List[str]:
        """
        Get list of available tool names.

        Returns:
            List of tool names.
        """
        tools = await self._session.list_tools()
        return [tool.name for tool in tools]

    async def wait_for_condition(
        self,
        condition: Callable[[], bool],
        timeout: float = 30.0,
        poll_interval: float = 0.5,
        description: str = "condition",
    ) -> bool:
        """
        Wait for a condition to become true.

        Useful for waiting on async operations triggered by tool calls.

        Args:
            condition: Callable that returns True when condition is met.
            timeout: Maximum time to wait in seconds.
            poll_interval: Time between condition checks in seconds.
            description: Description of the condition for error messages.

        Returns:
            True if condition was met, False if timed out.
        """
        import asyncio

        start_time = time.perf_counter()

        while (time.perf_counter() - start_time) < timeout:
            try:
                if condition():
                    return True
            except Exception:
                pass  # Ignore errors during condition check

            await asyncio.sleep(poll_interval)

        return False

    def clear_history(self) -> None:
        """Clear call history."""
        self._call_history.clear()

    def get_last_call(self) -> Optional[ToolCallResult]:
        """Get the most recent tool call result."""
        return self._call_history[-1] if self._call_history else None

    def get_calls_for_tool(self, tool_name: str) -> List[ToolCallResult]:
        """Get all calls for a specific tool."""
        return [c for c in self._call_history if c.name == tool_name]

    @staticmethod
    def _extract_error_message(result: CallToolResult) -> str:
        """Extract error message from CallToolResult."""
        if not result.content:
            return "Unknown error"

        for content in result.content:
            if isinstance(content, TextContent):
                return content.text
            if hasattr(content, "text"):
                return str(content.text)

        return "Unknown error"
