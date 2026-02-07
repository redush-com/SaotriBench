"""Evaluator for task_10_data_pipeline."""

from __future__ import annotations

import copy
import time
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the data_pipeline task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        data = copy.deepcopy(test_case.input["data"])
        steps = copy.deepcopy(test_case.input["steps"])

        try:
            result = solution_fn(data, steps)
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
        data = copy.deepcopy(test_case.input["data"])
        steps = copy.deepcopy(test_case.input["steps"])
        orig_data = copy.deepcopy(data)

        try:
            solution_fn(data, steps)
        except Exception:
            pass

        if data == orig_data:
            return RuleResult.success()
        return RuleResult.failed(scope="direct")

    def check_deterministic(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        results = []
        for _ in range(3):
            data = copy.deepcopy(test_case.input["data"])
            steps = copy.deepcopy(test_case.input["steps"])
            try:
                results.append(solution_fn(data, steps))
            except Exception as e:
                results.append(str(e))

        if all(r == results[0] for r in results):
            return RuleResult.success()
        return RuleResult.failed(scope="idempotent")

    def check_performance(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        data = copy.deepcopy(test_case.input["data"])
        steps = copy.deepcopy(test_case.input["steps"])

        start = time.perf_counter()
        try:
            solution_fn(data, steps)
        except Exception:
            return RuleResult.failed(scope="large_pipeline")

        elapsed = time.perf_counter() - start
        if elapsed < 3.0:
            return RuleResult.success()
        return RuleResult.failed(scope="large_pipeline")
