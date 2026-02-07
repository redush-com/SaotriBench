"""Evaluator for task_01_transform_list."""

from __future__ import annotations

import copy
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the transform_list task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if output matches expected."""
        input_copy = copy.deepcopy(test_case.input)
        result = solution_fn(input_copy)

        # Convert to list if it's a generator/iterator
        if not isinstance(result, list):
            result = list(result)

        if result == test_case.expected:
            return RuleResult.success()

        scope = test_case.tags[0] if test_case.tags else "unknown"
        return RuleResult.failed(scope=scope)

    def check_no_mutation(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if input was mutated."""
        input_copy = copy.deepcopy(test_case.input)
        solution_fn(input_copy)

        if input_copy == test_case.input:
            return RuleResult.success()

        return RuleResult.failed(scope="direct")

    def check_correct_type(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if return value is a list (not generator)."""
        input_copy = copy.deepcopy(test_case.input)
        result = solution_fn(input_copy)

        if isinstance(result, list):
            return RuleResult.success()

        return RuleResult.failed(scope="type_check")
