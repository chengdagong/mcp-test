"""Base assertion classes for MCP test results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from mcp_pytest.client.tool_caller import ToolCallResult


@dataclass
class AssertionResult:
    """Result of an assertion check."""

    passed: bool
    message: str
    expected: Any = None
    actual: Any = None
    details: Optional[str] = None

    def __bool__(self) -> bool:
        """Allow using AssertionResult in boolean context."""
        return self.passed

    def __str__(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        s = f"[{status}] {self.message}"
        if not self.passed:
            if self.expected is not None:
                s += f"\n  Expected: {self.expected}"
            if self.actual is not None:
                s += f"\n  Actual: {self.actual}"
            if self.details:
                s += f"\n  Details: {self.details}"
        return s


class BaseAssertion(ABC):
    """
    Base class for all assertions.

    Subclasses must implement:
    - check(): Perform the assertion check
    - description: Human-readable description of the assertion
    """

    @abstractmethod
    def check(self, result: ToolCallResult) -> AssertionResult:
        """
        Check the assertion against a tool call result.

        Args:
            result: The tool call result to check.

        Returns:
            AssertionResult indicating pass/fail with details.
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the assertion."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.description})"


class CompositeAssertion(BaseAssertion):
    """
    Combine multiple assertions with AND/OR logic.

    Usage:
        combined = CompositeAssertion(
            SuccessAssertion(),
            DurationAssertion(30),
            operator="and"
        )
    """

    def __init__(
        self,
        *assertions: BaseAssertion,
        operator: str = "and",
    ):
        """
        Initialize composite assertion.

        Args:
            assertions: Assertions to combine.
            operator: "and" (all must pass) or "or" (any must pass).
        """
        if operator not in ("and", "or"):
            raise ValueError(f"Invalid operator: {operator}. Must be 'and' or 'or'")

        self._assertions = list(assertions)
        self._operator = operator

    def check(self, result: ToolCallResult) -> AssertionResult:
        """Check all contained assertions."""
        results = [a.check(result) for a in self._assertions]

        if self._operator == "and":
            passed = all(r.passed for r in results)
            failed = [r for r in results if not r.passed]
            if passed:
                message = f"All {len(self._assertions)} assertions passed"
            else:
                messages = [f"- {r.message}" for r in failed]
                message = f"{len(failed)} assertion(s) failed:\n" + "\n".join(messages)
        else:  # or
            passed = any(r.passed for r in results)
            if passed:
                passed_results = [r for r in results if r.passed]
                message = f"{len(passed_results)} of {len(self._assertions)} assertions passed"
            else:
                messages = [f"- {r.message}" for r in results]
                message = f"None of {len(self._assertions)} assertions passed:\n" + "\n".join(
                    messages
                )

        return AssertionResult(passed=passed, message=message)

    @property
    def description(self) -> str:
        descs = [a.description for a in self._assertions]
        joiner = f" {self._operator.upper()} "
        return f"({joiner.join(descs)})"

    def add(self, assertion: BaseAssertion) -> "CompositeAssertion":
        """Add an assertion to this composite."""
        self._assertions.append(assertion)
        return self


class AllOf(CompositeAssertion):
    """Shorthand for CompositeAssertion with AND logic."""

    def __init__(self, *assertions: BaseAssertion):
        super().__init__(*assertions, operator="and")


class AnyOf(CompositeAssertion):
    """Shorthand for CompositeAssertion with OR logic."""

    def __init__(self, *assertions: BaseAssertion):
        super().__init__(*assertions, operator="or")
