"""Task loader for Saotri Bench."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .models import (
    Difficulty,
    Execution,
    Interface,
    Limits,
    Phase,
    Rule,
    TaskConfig,
    TestCase,
)

if TYPE_CHECKING:
    from .evaluator import BaseEvaluator


def load_task(task_dir: Path) -> TaskConfig:
    """Load task configuration from task.yaml."""
    task_file = task_dir / "task.yaml"
    if not task_file.exists():
        raise FileNotFoundError(f"task.yaml not found in {task_dir}")

    with open(task_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return _parse_task_config(data)


def _parse_task_config(data: dict[str, Any]) -> TaskConfig:
    """Parse raw YAML data into TaskConfig."""
    # Parse interface
    interface_data = data.get("interface", {})
    interface = Interface(
        function_name=interface_data.get("function_name", ""),
        signature=interface_data.get("signature", ""),
        allowed_imports=interface_data.get("allowed_imports", []),
    )

    # Parse execution
    execution_data = data.get("execution", {})
    execution = Execution(
        timeout_seconds=execution_data.get("timeout_seconds", 30),
    )

    # Parse limits
    limits_data = data.get("limits", {})
    limits = Limits(
        max_attempts_per_phase=limits_data.get("max_attempts_per_phase", 10),
        max_total_attempts=limits_data.get("max_total_attempts", 50),
    )

    # Parse phases
    phases = []
    for phase_data in data.get("phases", []):
        rules = []
        for rule_data in phase_data.get("rules", []):
            rules.append(
                Rule(
                    id=rule_data.get("id", ""),
                    description=rule_data.get("description", ""),
                    scopes=rule_data.get("scopes", []),
                )
            )
        phases.append(
            Phase(
                id=phase_data.get("id", 0),
                description=phase_data.get("description", ""),
                rules=rules,
            )
        )

    return TaskConfig(
        id=data.get("id", ""),
        name=data.get("name", ""),
        description=data.get("description", ""),
        difficulty=Difficulty(data.get("difficulty", "easy")),
        interface=interface,
        execution=execution,
        phases=phases,
        limits=limits,
    )


def load_problem(task_dir: Path) -> str:
    """Load problem description from problem.md."""
    problem_file = task_dir / "problem.md"
    if not problem_file.exists():
        raise FileNotFoundError(f"problem.md not found in {task_dir}")

    with open(problem_file, encoding="utf-8") as f:
        return f.read()


def load_evaluator(task_dir: Path) -> BaseEvaluator:
    """Dynamically load evaluator from evaluator.py."""
    evaluator_file = task_dir / "evaluator.py"
    if not evaluator_file.exists():
        raise FileNotFoundError(f"evaluator.py not found in {task_dir}")

    # Create a unique module name
    module_name = f"saotri_bench_task_{task_dir.name}_evaluator"

    # Load the module dynamically
    spec = importlib.util.spec_from_file_location(module_name, evaluator_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load evaluator from {evaluator_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    # Get the Evaluator class
    if not hasattr(module, "Evaluator"):
        raise ImportError(f"Evaluator class not found in {evaluator_file}")

    evaluator_class = module.Evaluator
    return evaluator_class()


def load_tests(task_dir: Path) -> list[TestCase]:
    """Dynamically load test cases from tests.py."""
    tests_file = task_dir / "tests.py"
    if not tests_file.exists():
        raise FileNotFoundError(f"tests.py not found in {task_dir}")

    # Create a unique module name
    module_name = f"saotri_bench_task_{task_dir.name}_tests"

    # Load the module dynamically
    spec = importlib.util.spec_from_file_location(module_name, tests_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load tests from {tests_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    # Get TEST_CASES
    if not hasattr(module, "TEST_CASES"):
        raise ImportError(f"TEST_CASES not found in {tests_file}")

    return module.TEST_CASES
