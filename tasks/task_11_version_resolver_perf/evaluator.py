"""Evaluator for task_11_version_resolver."""

from __future__ import annotations

import copy
import time
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the version_resolver task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        if test_case.tags and any(t in test_case.tags for t in ["version_conflict", "circular_dependency"]):
            return RuleResult.success()

        deps = copy.deepcopy(test_case.input["dependencies"])
        registry = copy.deepcopy(test_case.input["registry"])
        options = copy.deepcopy(test_case.input.get("options"))

        try:
            result = solution_fn(deps, registry, options)
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
        if test_case.tags and not any(t in test_case.tags for t in ["version_conflict", "circular_dependency"]):
            return RuleResult.success()

        deps = copy.deepcopy(test_case.input["dependencies"])
        registry = copy.deepcopy(test_case.input["registry"])
        options = copy.deepcopy(test_case.input.get("options"))

        try:
            solution_fn(deps, registry, options)
            tag = test_case.tags[0] if test_case.tags else "error"
            return RuleResult.failed(scope=tag)
        except ValueError:
            return RuleResult.success()
        except Exception:
            tag = test_case.tags[0] if test_case.tags else "error"
            return RuleResult.failed(scope=tag)

    def check_no_mutation(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        deps = copy.deepcopy(test_case.input["dependencies"])
        registry = copy.deepcopy(test_case.input["registry"])
        options = copy.deepcopy(test_case.input.get("options"))
        orig_deps = copy.deepcopy(deps)
        orig_registry = copy.deepcopy(registry)

        try:
            solution_fn(deps, registry, options)
        except Exception:
            pass

        if deps == orig_deps and registry == orig_registry:
            return RuleResult.success()
        return RuleResult.failed(scope="direct")

    def check_deterministic(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        if test_case.tags and any(t in test_case.tags for t in ["version_conflict", "circular_dependency"]):
            return RuleResult.success()

        results = []
        for _ in range(3):
            deps = copy.deepcopy(test_case.input["dependencies"])
            registry = copy.deepcopy(test_case.input["registry"])
            options = copy.deepcopy(test_case.input.get("options"))
            try:
                results.append(solution_fn(deps, registry, options))
            except Exception as e:
                results.append(str(e))

        if all(r == results[0] for r in results):
            return RuleResult.success()
        return RuleResult.failed(scope="deterministic_resolve")

    def check_performance(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        deps = copy.deepcopy(test_case.input["dependencies"])
        registry = copy.deepcopy(test_case.input["registry"])
        options = copy.deepcopy(test_case.input.get("options"))

        start = time.perf_counter()
        try:
            solution_fn(deps, registry, options)
        except Exception:
            return RuleResult.failed(scope="large_registry")

        elapsed = time.perf_counter() - start
        if elapsed < 5.0:
            return RuleResult.success()
        return RuleResult.failed(scope="large_registry")
