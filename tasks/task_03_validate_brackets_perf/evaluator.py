"""Evaluator for task_03_validate_brackets."""

from __future__ import annotations

import copy
import time
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the validate_brackets task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if output matches expected for valid inputs."""
        # For phases 3+, invalid inputs are checked by correct_error rule
        # This rule only checks cases where expected is True
        # or cases from phases 0-2 (before error contract change)
        if test_case.phase >= 3 and test_case.expected is False:
            # In phase 3+, invalid inputs should raise ValueError, not return False
            # This is checked by correct_error rule
            return RuleResult.success()

        input_copy = copy.deepcopy(test_case.input)
        try:
            result = solution_fn(input_copy)
        except ValueError:
            # If in phase 3+ and result should be True, raising ValueError is wrong
            if test_case.expected is True:
                scope = test_case.tags[0] if test_case.tags else "unknown"
                return RuleResult.failed(scope=scope)
            # In phase 3+ for invalid inputs, ValueError is acceptable
            return RuleResult.success()
        except Exception:
            scope = test_case.tags[0] if test_case.tags else "error"
            return RuleResult.failed(scope=scope)

        if result == test_case.expected:
            return RuleResult.success()

        scope = test_case.tags[0] if test_case.tags else "unknown"
        return RuleResult.failed(scope=scope)

    def check_correct_error(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check that invalid inputs raise ValueError with position info."""
        # Only relevant for test cases that should be invalid
        if test_case.expected is True:
            return RuleResult.success()

        input_copy = copy.deepcopy(test_case.input)

        try:
            result = solution_fn(input_copy)
            # Should have raised ValueError, but returned a value instead
            return RuleResult.failed(scope="error_position")
        except ValueError as e:
            error_msg = str(e)
            # Check that error message contains a position number
            # The position should be mentioned as a digit in the message
            has_position = any(char.isdigit() for char in error_msg)
            if has_position:
                return RuleResult.success()
            return RuleResult.failed(scope="error_position")
        except Exception:
            return RuleResult.failed(scope="error_position")

    def check_performance(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check that solution handles large inputs efficiently."""
        input_copy = copy.deepcopy(test_case.input)
        start = time.perf_counter()

        try:
            solution_fn(input_copy)
        except ValueError:
            pass  # Expected for invalid large inputs
        except Exception:
            return RuleResult.failed(scope="large_input")

        elapsed = time.perf_counter() - start

        # Should handle 10000 chars well under 1 second for O(n)
        if elapsed < 1.0:
            return RuleResult.success()

        return RuleResult.failed(scope="large_input")
