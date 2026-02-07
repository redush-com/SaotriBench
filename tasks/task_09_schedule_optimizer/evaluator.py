"""Evaluator for task_09_schedule_optimizer."""

from __future__ import annotations

import copy
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the schedule_optimizer task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        if test_case.tags and "deadline_violation" in test_case.tags:
            return RuleResult.success()

        tasks = copy.deepcopy(test_case.input["tasks"])
        constraints = copy.deepcopy(test_case.input["constraints"])

        try:
            result = solution_fn(tasks, constraints)
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
        if test_case.tags and "deadline_violation" not in test_case.tags:
            return RuleResult.success()

        tasks = copy.deepcopy(test_case.input["tasks"])
        constraints = copy.deepcopy(test_case.input["constraints"])

        try:
            solution_fn(tasks, constraints)
            return RuleResult.failed(scope="deadline_violation")
        except ValueError:
            return RuleResult.success()
        except Exception:
            return RuleResult.failed(scope="deadline_violation")

    def check_no_mutation(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        tasks = copy.deepcopy(test_case.input["tasks"])
        constraints = copy.deepcopy(test_case.input["constraints"])
        orig_tasks = copy.deepcopy(tasks)
        orig_constraints = copy.deepcopy(constraints)

        try:
            solution_fn(tasks, constraints)
        except Exception:
            pass

        if tasks == orig_tasks and constraints == orig_constraints:
            return RuleResult.success()
        return RuleResult.failed(scope="direct")

    def check_deterministic(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        if test_case.tags and "deadline_violation" in test_case.tags:
            return RuleResult.success()

        results = []
        for _ in range(3):
            tasks = copy.deepcopy(test_case.input["tasks"])
            constraints = copy.deepcopy(test_case.input["constraints"])
            try:
                results.append(solution_fn(tasks, constraints))
            except Exception as e:
                results.append(str(e))

        if all(r == results[0] for r in results):
            return RuleResult.success()
        return RuleResult.failed(scope="deterministic_tiebreak")
