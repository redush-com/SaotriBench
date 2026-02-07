"""Evaluator for task_08_access_control."""

from __future__ import annotations

import copy
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the access_control task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        user = copy.deepcopy(test_case.input["user"])
        resource = copy.deepcopy(test_case.input["resource"])
        rules = copy.deepcopy(test_case.input["rules"])

        try:
            result = solution_fn(user, resource, rules)
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
        user = copy.deepcopy(test_case.input["user"])
        resource = copy.deepcopy(test_case.input["resource"])
        rules = copy.deepcopy(test_case.input["rules"])
        orig_user = copy.deepcopy(user)
        orig_resource = copy.deepcopy(resource)
        orig_rules = copy.deepcopy(rules)

        try:
            solution_fn(user, resource, rules)
        except Exception:
            pass

        if user == orig_user and resource == orig_resource and rules == orig_rules:
            return RuleResult.success()
        return RuleResult.failed(scope="direct")

    def check_deterministic(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        results = []
        for _ in range(3):
            user = copy.deepcopy(test_case.input["user"])
            resource = copy.deepcopy(test_case.input["resource"])
            rules = copy.deepcopy(test_case.input["rules"])
            try:
                results.append(solution_fn(user, resource, rules))
            except Exception as e:
                results.append(str(e))

        if all(r == results[0] for r in results):
            return RuleResult.success()
        return RuleResult.failed(scope="consistency")
