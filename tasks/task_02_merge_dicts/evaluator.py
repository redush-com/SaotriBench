"""Evaluator for task_02_merge_dicts."""

from __future__ import annotations

import copy
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the merge_dicts task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if merged output matches expected."""
        a_copy = copy.deepcopy(test_case.input["a"])
        b_copy = copy.deepcopy(test_case.input["b"])
        result = solution_fn(a_copy, b_copy)

        if result == test_case.expected:
            return RuleResult.success()

        scope = test_case.tags[0] if test_case.tags else "unknown"
        return RuleResult.failed(scope=scope)

    def check_no_mutation(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if input dicts were mutated."""
        a_copy = copy.deepcopy(test_case.input["a"])
        b_copy = copy.deepcopy(test_case.input["b"])
        solution_fn(a_copy, b_copy)

        a_mutated = a_copy != test_case.input["a"]
        b_mutated = b_copy != test_case.input["b"]

        if not a_mutated and not b_mutated:
            return RuleResult.success()

        return RuleResult.failed(scope="direct")

    def check_deterministic(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if function is deterministic."""
        results = []
        for _ in range(3):
            a_copy = copy.deepcopy(test_case.input["a"])
            b_copy = copy.deepcopy(test_case.input["b"])
            results.append(solution_fn(a_copy, b_copy))

        if all(r == results[0] for r in results):
            return RuleResult.success()

        return RuleResult.failed(scope="consistency")
