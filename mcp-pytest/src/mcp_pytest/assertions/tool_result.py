"""Tool result assertions for MCP tests."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Callable, Optional, Pattern, Union

from mcp_pytest.assertions.base import AssertionResult, BaseAssertion

if TYPE_CHECKING:
    from mcp_pytest.client.tool_caller import ToolCallResult


class SuccessAssertion(BaseAssertion):
    """Assert that tool call succeeded (no error)."""

    def check(self, result: ToolCallResult) -> AssertionResult:
        return AssertionResult(
            passed=result.success,
            message="Tool call should succeed",
            expected="success=True",
            actual=f"success={result.success}",
            details=result.error_message if not result.success else None,
        )

    @property
    def description(self) -> str:
        return "Tool call succeeds"


class ErrorAssertion(BaseAssertion):
    """
    Assert that tool call failed with optional error pattern matching.

    Usage:
        ErrorAssertion()  # Just expects an error
        ErrorAssertion("not found")  # Error message must contain "not found"
        ErrorAssertion(r"error code: \d+")  # Regex pattern
    """

    def __init__(self, error_pattern: Optional[str] = None):
        """
        Initialize error assertion.

        Args:
            error_pattern: Optional regex pattern to match against error message.
        """
        self._pattern: Optional[Pattern[str]] = None
        self._pattern_str = error_pattern

        if error_pattern:
            self._pattern = re.compile(error_pattern, re.IGNORECASE)

    def check(self, result: ToolCallResult) -> AssertionResult:
        # First check that there was an error
        if result.success:
            return AssertionResult(
                passed=False,
                message="Tool call should fail",
                expected="success=False (error)",
                actual="success=True",
            )

        # If pattern specified, check it matches
        if self._pattern and result.error_message:
            if not self._pattern.search(result.error_message):
                return AssertionResult(
                    passed=False,
                    message=f"Error message should match pattern: {self._pattern_str}",
                    expected=self._pattern_str,
                    actual=result.error_message,
                )

        return AssertionResult(
            passed=True,
            message="Tool call failed as expected",
        )

    @property
    def description(self) -> str:
        if self._pattern_str:
            return f"Tool call fails with error matching '{self._pattern_str}'"
        return "Tool call fails"


class ResultContainsAssertion(BaseAssertion):
    """
    Assert that result text contains specific content.

    Usage:
        ResultContainsAssertion("success")
        ResultContainsAssertion("created", case_sensitive=False)
    """

    def __init__(
        self,
        expected: str,
        case_sensitive: bool = True,
    ):
        """
        Initialize contains assertion.

        Args:
            expected: String that must be present in result.
            case_sensitive: Whether to match case-sensitively.
        """
        self._expected = expected
        self._case_sensitive = case_sensitive

    def check(self, result: ToolCallResult) -> AssertionResult:
        text = result.text_content

        if self._case_sensitive:
            found = self._expected in text
        else:
            found = self._expected.lower() in text.lower()

        if found:
            return AssertionResult(
                passed=True,
                message=f"Result contains '{self._expected}'",
            )

        return AssertionResult(
            passed=False,
            message=f"Result should contain '{self._expected}'",
            expected=self._expected,
            actual=text[:200] + "..." if len(text) > 200 else text,
        )

    @property
    def description(self) -> str:
        return f"Result contains '{self._expected}'"


class ResultMatchesAssertion(BaseAssertion):
    """
    Assert that result text matches a regex pattern.

    Usage:
        ResultMatchesAssertion(r"id: \d+")
        ResultMatchesAssertion(r"error", flags=re.IGNORECASE)
    """

    def __init__(self, pattern: str, flags: int = 0):
        """
        Initialize regex assertion.

        Args:
            pattern: Regex pattern to match.
            flags: Regex flags (e.g., re.IGNORECASE).
        """
        self._pattern_str = pattern
        self._pattern = re.compile(pattern, flags)

    def check(self, result: ToolCallResult) -> AssertionResult:
        text = result.text_content

        if self._pattern.search(text):
            return AssertionResult(
                passed=True,
                message=f"Result matches pattern '{self._pattern_str}'",
            )

        return AssertionResult(
            passed=False,
            message=f"Result should match pattern '{self._pattern_str}'",
            expected=self._pattern_str,
            actual=text[:200] + "..." if len(text) > 200 else text,
        )

    @property
    def description(self) -> str:
        return f"Result matches '{self._pattern_str}'"


class ResultEqualsAssertion(BaseAssertion):
    """
    Assert that result text equals expected value exactly.

    Usage:
        ResultEqualsAssertion("OK")
        ResultEqualsAssertion("success", strip=True)
    """

    def __init__(self, expected: str, strip: bool = True):
        """
        Initialize equals assertion.

        Args:
            expected: Expected result text.
            strip: Whether to strip whitespace before comparison.
        """
        self._expected = expected
        self._strip = strip

    def check(self, result: ToolCallResult) -> AssertionResult:
        text = result.text_content
        expected = self._expected

        if self._strip:
            text = text.strip()
            expected = expected.strip()

        if text == expected:
            return AssertionResult(
                passed=True,
                message="Result equals expected value",
            )

        return AssertionResult(
            passed=False,
            message="Result should equal expected value",
            expected=expected,
            actual=text,
        )

    @property
    def description(self) -> str:
        return f"Result equals '{self._expected}'"


class DurationAssertion(BaseAssertion):
    """
    Assert that tool call completes within time limit.

    Usage:
        DurationAssertion(30)  # Must complete within 30 seconds
        DurationAssertion(5, min_seconds=1)  # Between 1 and 5 seconds
    """

    def __init__(
        self,
        max_seconds: float,
        min_seconds: Optional[float] = None,
    ):
        """
        Initialize duration assertion.

        Args:
            max_seconds: Maximum allowed duration in seconds.
            min_seconds: Optional minimum duration (useful for detecting mocks).
        """
        self._max_seconds = max_seconds
        self._min_seconds = min_seconds

    def check(self, result: ToolCallResult) -> AssertionResult:
        duration = result.duration_seconds

        # Check max
        if duration > self._max_seconds:
            return AssertionResult(
                passed=False,
                message=f"Tool call should complete within {self._max_seconds}s",
                expected=f"<= {self._max_seconds}s",
                actual=f"{duration:.2f}s",
            )

        # Check min if specified
        if self._min_seconds is not None and duration < self._min_seconds:
            return AssertionResult(
                passed=False,
                message=f"Tool call should take at least {self._min_seconds}s",
                expected=f">= {self._min_seconds}s",
                actual=f"{duration:.2f}s",
            )

        return AssertionResult(
            passed=True,
            message=f"Tool call completed in {duration:.2f}s",
        )

    @property
    def description(self) -> str:
        if self._min_seconds is not None:
            return f"Duration between {self._min_seconds}s and {self._max_seconds}s"
        return f"Duration <= {self._max_seconds}s"


class CustomAssertion(BaseAssertion):
    """
    Custom assertion using a callable.

    Usage:
        CustomAssertion(
            lambda r: "success" in r.text_content.lower(),
            "Result indicates success"
        )
    """

    def __init__(
        self,
        check_func: Callable[[ToolCallResult], bool],
        description: str,
        message_func: Optional[Callable[[ToolCallResult], str]] = None,
    ):
        """
        Initialize custom assertion.

        Args:
            check_func: Function that takes ToolCallResult and returns bool.
            description: Human-readable description of what is being checked.
            message_func: Optional function to generate failure message.
        """
        self._check_func = check_func
        self._description = description
        self._message_func = message_func

    def check(self, result: ToolCallResult) -> AssertionResult:
        try:
            passed = self._check_func(result)
        except Exception as e:
            return AssertionResult(
                passed=False,
                message=f"Assertion check failed with error: {e}",
                details=str(e),
            )

        if passed:
            return AssertionResult(
                passed=True,
                message=self._description,
            )

        message = self._description
        if self._message_func:
            try:
                message = self._message_func(result)
            except Exception:
                pass  # Fall back to description

        return AssertionResult(
            passed=False,
            message=f"Failed: {message}",
            actual=result.text_content[:200] if result.text_content else "(empty)",
        )

    @property
    def description(self) -> str:
        return self._description


class NotAssertion(BaseAssertion):
    """
    Negate another assertion.

    Usage:
        NotAssertion(ErrorAssertion())  # Must not be an error
        NotAssertion(ResultContainsAssertion("error"))  # Must not contain "error"
    """

    def __init__(self, assertion: BaseAssertion):
        """
        Initialize negation assertion.

        Args:
            assertion: Assertion to negate.
        """
        self._assertion = assertion

    def check(self, result: ToolCallResult) -> AssertionResult:
        inner_result = self._assertion.check(result)

        return AssertionResult(
            passed=not inner_result.passed,
            message=f"NOT ({self._assertion.description})",
            details=f"Inner assertion {'failed' if inner_result.passed else 'passed'} as expected"
            if not inner_result.passed
            else f"Inner assertion passed but should have failed",
        )

    @property
    def description(self) -> str:
        return f"NOT ({self._assertion.description})"
