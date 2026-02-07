"""Evaluator for task_04_sort_objects."""

from __future__ import annotations

import copy
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the sort_objects task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if sorted output matches expected."""
        # For error_handling tests, the expected is an exception
        if test_case.tags and "error_handling" in test_case.tags:
            return RuleResult.success()  # Checked by correct_error

        items_copy = copy.deepcopy(test_case.input["items"])
        key_copy = copy.deepcopy(test_case.input["key"])

        try:
            result = solution_fn(items_copy, key_copy)
        except Exception:
            scope = test_case.tags[0] if test_case.tags else "error"
            return RuleResult.failed(scope=scope)

        if result == test_case.expected:
            return RuleResult.success()

        scope = test_case.tags[0] if test_case.tags else "unknown"
        return RuleResult.failed(scope=scope)

    def check_no_mutation(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if input list was mutated."""
        if test_case.tags and "error_handling" in test_case.tags:
            return RuleResult.success()

        items_copy = copy.deepcopy(test_case.input["items"])
        key_copy = copy.deepcopy(test_case.input["key"])
        solution_fn(items_copy, key_copy)

        if items_copy == test_case.input["items"]:
            return RuleResult.success()

        return RuleResult.failed(scope="direct")

    def check_deterministic(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if function is deterministic."""
        if test_case.tags and "error_handling" in test_case.tags:
            return RuleResult.success()

        results = []
        for _ in range(3):
            items_copy = copy.deepcopy(test_case.input["items"])
            key_copy = copy.deepcopy(test_case.input["key"])
            results.append(solution_fn(items_copy, key_copy))

        if all(r == results[0] for r in results):
            return RuleResult.success()

        return RuleResult.failed(scope="consistency")

    def check_correct_error(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check that invalid keys raise ValueError."""
        if test_case.tags and "error_handling" not in test_case.tags:
            return RuleResult.success()

        items_copy = copy.deepcopy(test_case.input["items"])
        key_copy = copy.deepcopy(test_case.input["key"])

        try:
            result = solution_fn(items_copy, key_copy)
            # For empty_input tests, returning [] is correct
            if test_case.tags and "empty_input" in test_case.tags:
                if result == test_case.expected:
                    return RuleResult.success()
                return RuleResult.failed(scope="empty_input")
            # Should have raised ValueError
            return RuleResult.failed(scope="error_handling")
        except ValueError:
            return RuleResult.success()
        except Exception:
            return RuleResult.failed(scope="error_handling")
