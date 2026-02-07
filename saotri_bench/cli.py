"""Command-line interface for Saotri Bench."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .loader import load_task, load_problem, load_evaluator, load_tests
from .runner import Runner


def cmd_run(args: argparse.Namespace) -> int:
    """Run a task interactively."""
    task_dir = Path(args.task)
    workspace_dir = Path(args.workspace)

    if not task_dir.exists():
        print(f"Error: Task directory not found: {task_dir}", file=sys.stderr)
        return 1

    try:
        runner = Runner(
            task_dir=task_dir,
            workspace_dir=workspace_dir,
            agent_id=args.agent_id,
            poll_interval=args.poll_interval,
        )

        if args.single:
            # Single pass mode
            feedback = runner.run_single_pass()
            print(json.dumps(feedback.to_dict(), indent=2))
        else:
            # Interactive mode
            report = runner.run_interactive()
            print("\n" + "=" * 50)
            print("FINAL REPORT")
            print("=" * 50)
            print(json.dumps(report.to_dict(), indent=2))

            # Write report to file
            report_file = workspace_dir / "report.json"
            report_file.write_text(
                json.dumps(report.to_dict(), indent=2), encoding="utf-8"
            )
            print(f"\nReport saved to: {report_file}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List available tasks."""
    tasks_dir = Path(args.tasks_dir)

    if not tasks_dir.exists():
        print(f"Error: Tasks directory not found: {tasks_dir}", file=sys.stderr)
        return 1

    tasks = []
    for task_dir in sorted(tasks_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        task_yaml = task_dir / "task.yaml"
        if not task_yaml.exists():
            continue

        try:
            config = load_task(task_dir)
            tasks.append(
                {
                    "id": config.id,
                    "name": config.name,
                    "difficulty": config.difficulty.value,
                    "phases": len(config.phases),
                    "path": str(task_dir),
                }
            )
        except Exception as e:
            print(f"Warning: Failed to load {task_dir}: {e}", file=sys.stderr)

    if args.json:
        print(json.dumps(tasks, indent=2))
    else:
        print(f"Found {len(tasks)} task(s):\n")
        for task in tasks:
            print(f"  {task['id']}")
            print(f"    Name: {task['name']}")
            print(f"    Difficulty: {task['difficulty']}")
            print(f"    Phases: {task['phases']}")
            print(f"    Path: {task['path']}")
            print()

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a task definition."""
    task_dir = Path(args.task)

    if not task_dir.exists():
        print(f"Error: Task directory not found: {task_dir}", file=sys.stderr)
        return 1

    errors = []
    warnings = []

    # Check task.yaml
    try:
        config = load_task(task_dir)
        print(f"[OK] task.yaml loaded: {config.id}")

        # Validate phase count
        phase_count = len(config.phases)
        if phase_count < 3:
            errors.append(f"Task must have at least 3 phases (has {phase_count})")

        # Validate difficulty tier matches phase count
        difficulty = config.difficulty.value
        if difficulty == "easy" and not (3 <= phase_count <= 5):
            warnings.append(
                f"Easy tasks should have 3-5 phases (has {phase_count})"
            )
        elif difficulty == "medium" and not (6 <= phase_count <= 15):
            warnings.append(
                f"Medium tasks should have 6-15 phases (has {phase_count})"
            )
        elif difficulty == "hard" and not (16 <= phase_count <= 30):
            warnings.append(
                f"Hard tasks should have 16-30 phases (has {phase_count})"
            )
        elif difficulty == "expert" and not (31 <= phase_count <= 50):
            warnings.append(
                f"Expert tasks should have 31-50 phases (has {phase_count})"
            )

        # Validate phase IDs are sequential
        phase_ids = [p.id for p in config.phases]
        expected_ids = list(range(len(config.phases)))
        if phase_ids != expected_ids:
            errors.append(
                f"Phase IDs must be sequential starting from 0: {phase_ids}"
            )

        # Validate each phase has rules
        for phase in config.phases:
            if not phase.rules:
                warnings.append(f"Phase {phase.id} has no rules")

    except Exception as e:
        errors.append(f"Failed to load task.yaml: {e}")

    # Check problem.md
    try:
        problem = load_problem(task_dir)
        print(f"[OK] problem.md loaded ({len(problem)} chars)")
    except Exception as e:
        errors.append(f"Failed to load problem.md: {e}")

    # Check evaluator.py
    try:
        evaluator = load_evaluator(task_dir)
        print(f"[OK] evaluator.py loaded: {type(evaluator).__name__}")

        # Check that evaluator has required methods
        if config:
            for phase in config.phases:
                for rule in phase.rules:
                    method_name = f"check_{rule.id}"
                    if not hasattr(evaluator, method_name):
                        errors.append(
                            f"Evaluator missing method: {method_name}"
                        )
    except Exception as e:
        errors.append(f"Failed to load evaluator.py: {e}")

    # Check tests.py
    try:
        tests = load_tests(task_dir)
        print(f"[OK] tests.py loaded ({len(tests)} test cases)")

        # Validate test cases cover all phases
        if config:
            test_phases = set(tc.phase for tc in tests)
            expected_phases = set(p.id for p in config.phases)
            missing_phases = expected_phases - test_phases
            if missing_phases:
                warnings.append(
                    f"No test cases for phases: {sorted(missing_phases)}"
                )

    except Exception as e:
        errors.append(f"Failed to load tests.py: {e}")

    # Print results
    print()
    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  [WARN] {w}")
        print()

    if errors:
        print("Errors:")
        for e in errors:
            print(f"  [ERROR] {e}")
        print()
        print("Validation FAILED")
        return 1

    print("Validation PASSED")
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="saotri-bench",
        description="Saotri Bench: Dynamic Coding Problems Benchmark",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    run_parser = subparsers.add_parser("run", help="Run a task")
    run_parser.add_argument(
        "--task",
        "-t",
        required=True,
        help="Path to task directory",
    )
    run_parser.add_argument(
        "--workspace",
        "-w",
        default="./workspace",
        help="Path to workspace directory (default: ./workspace)",
    )
    run_parser.add_argument(
        "--agent-id",
        "-a",
        default="unknown",
        help="Agent identifier (default: unknown)",
    )
    run_parser.add_argument(
        "--poll-interval",
        "-p",
        type=float,
        default=1.0,
        help="Poll interval in seconds (default: 1.0)",
    )
    run_parser.add_argument(
        "--single",
        "-s",
        action="store_true",
        help="Single pass mode (evaluate once and exit)",
    )
    run_parser.set_defaults(func=cmd_run)

    # list command
    list_parser = subparsers.add_parser("list", help="List available tasks")
    list_parser.add_argument(
        "--tasks-dir",
        "-d",
        default="./tasks",
        help="Path to tasks directory (default: ./tasks)",
    )
    list_parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )
    list_parser.set_defaults(func=cmd_list)

    # validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate a task definition"
    )
    validate_parser.add_argument(
        "--task",
        "-t",
        required=True,
        help="Path to task directory",
    )
    validate_parser.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
