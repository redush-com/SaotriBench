"""Evaluator for task_06_cache_eviction."""

from __future__ import annotations

import copy
import time
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the cache_eviction task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        ops = copy.deepcopy(test_case.input["operations"])
        config = copy.deepcopy(test_case.input["config"])

        try:
            result = solution_fn(ops, config)
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
        ops = copy.deepcopy(test_case.input["operations"])
        config = copy.deepcopy(test_case.input["config"])
        original_ops = copy.deepcopy(ops)

        try:
            solution_fn(ops, config)
        except Exception:
            pass

        if ops == original_ops:
            return RuleResult.success()
        return RuleResult.failed(scope="direct")

    def check_performance(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        ops = copy.deepcopy(test_case.input["operations"])
        config = copy.deepcopy(test_case.input["config"])

        start = time.perf_counter()
        try:
            solution_fn(ops, config)
        except Exception:
            return RuleResult.failed(scope="large_input")

        elapsed = time.perf_counter() - start
        if elapsed < 2.0:
            return RuleResult.success()
        return RuleResult.failed(scope="large_input")
