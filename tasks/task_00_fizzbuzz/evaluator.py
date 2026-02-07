"""Evaluator for task_00_fizzbuzz."""

from __future__ import annotations

import copy
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the fizzbuzz task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if output matches expected."""
        input_copy = copy.deepcopy(test_case.input)
        result = solution_fn(input_copy)

        if result == test_case.expected:
            return RuleResult.success()

        scope = test_case.tags[0] if test_case.tags else "unknown"
        return RuleResult.failed(scope=scope)

    def check_correct_type(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if return value is a string."""
        input_copy = copy.deepcopy(test_case.input)
        result = solution_fn(input_copy)

        if isinstance(result, str):
            return RuleResult.success()

        return RuleResult.failed(scope="type_check")

    def check_deterministic(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if function is deterministic."""
        results = []
        for _ in range(3):
            input_copy = copy.deepcopy(test_case.input)
            results.append(solution_fn(input_copy))

        if all(r == results[0] for r in results):
            return RuleResult.success()

        return RuleResult.failed(scope="consistency")
