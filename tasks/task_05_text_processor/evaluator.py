"""Evaluator for task_05_text_processor."""

from __future__ import annotations

import copy
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the text_processor task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        input_text = copy.deepcopy(test_case.input["text"])
        options = copy.deepcopy(test_case.input.get("options"))

        try:
            result = solution_fn(input_text, options)
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
        input_text = test_case.input["text"]
        options = copy.deepcopy(test_case.input.get("options"))
        original = input_text  # strings are immutable in Python, but test the principle

        try:
            solution_fn(input_text, options)
        except Exception:
            pass

        if input_text == original:
            return RuleResult.success()
        return RuleResult.failed(scope="direct")

    def check_deterministic(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        results = []
        for _ in range(3):
            input_text = copy.deepcopy(test_case.input["text"])
            options = copy.deepcopy(test_case.input.get("options"))
            try:
                results.append(solution_fn(input_text, options))
            except Exception as e:
                results.append(str(e))

        if all(r == results[0] for r in results):
            return RuleResult.success()
        return RuleResult.failed(scope="consistency")
