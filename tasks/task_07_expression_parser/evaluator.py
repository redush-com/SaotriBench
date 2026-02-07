"""Evaluator for task_07_expression_parser."""

from __future__ import annotations

import copy
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the expression_parser task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        if test_case.tags and any(t in test_case.tags for t in ["undefined_variable", "zero_division_context"]):
            return RuleResult.success()  # checked by correct_error

        expr = copy.deepcopy(test_case.input["expression"])
        variables = copy.deepcopy(test_case.input.get("variables"))

        try:
            result = solution_fn(expr, variables)
        except Exception:
            scope = test_case.tags[0] if test_case.tags else "error"
            return RuleResult.failed(scope=scope)

        # Compare with tolerance for floats
        expected = test_case.expected
        if isinstance(expected, (int, float)) and isinstance(result, (int, float)):
            if abs(result - expected) < 1e-9:
                return RuleResult.success()

        scope = test_case.tags[0] if test_case.tags else "unknown"
        return RuleResult.failed(scope=scope)

    def check_correct_error(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        if test_case.tags and not any(t in test_case.tags for t in ["undefined_variable", "zero_division_context"]):
            return RuleResult.success()

        expr = copy.deepcopy(test_case.input["expression"])
        variables = copy.deepcopy(test_case.input.get("variables"))

        try:
            solution_fn(expr, variables)
            return RuleResult.failed(scope=test_case.tags[0])
        except ValueError as e:
            error_msg = str(e)
            if "zero_division_context" in test_case.tags:
                # Must mention the offending sub-expression or position
                if "/" in error_msg or "division" in error_msg.lower() or "zero" in error_msg.lower():
                    return RuleResult.success()
                return RuleResult.failed(scope="zero_division_context")
            return RuleResult.success()
        except Exception:
            return RuleResult.failed(scope=test_case.tags[0])

    def check_deterministic(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        if test_case.tags and any(t in test_case.tags for t in ["undefined_variable", "zero_division_context"]):
            return RuleResult.success()

        results = []
        for _ in range(3):
            expr = copy.deepcopy(test_case.input["expression"])
            variables = copy.deepcopy(test_case.input.get("variables"))
            try:
                results.append(solution_fn(expr, variables))
            except Exception as e:
                results.append(str(e))

        if all(r == results[0] for r in results):
            return RuleResult.success()
        return RuleResult.failed(scope="consistency")
