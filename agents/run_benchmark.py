"""Main entry point for running LLM agent benchmarks.

Usage:
    # Run all models on all tasks
    python -m agents.run_benchmark

    # Run specific model tier on specific task
    python -m agents.run_benchmark --tier strong --task task_00_fizzbuzz

    # Run all models on one task
    python -m agents.run_benchmark --task task_00_fizzbuzz

    # Run selected models
    python -m agents.run_benchmark --models claude-opus,gpt,deepseek

    # Run models in parallel (up to 4 at a time)
    python -m agents.run_benchmark --models claude-opus,gpt,deepseek --parallel 4

    # List available models
    python -m agents.run_benchmark --list-models
"""

from __future__ import annotations

import argparse
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Auto-load .env from agents/ directory
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from agents.config import get_model, list_models, MODELS
from agents.bench_runner import run_agent_on_task, RunResult
from agents.reports import ReportManager


def find_tasks(tasks_dir: Path) -> list[Path]:
    """Find all valid task directories."""
    tasks = []
    for d in sorted(tasks_dir.iterdir()):
        if d.is_dir() and (d / "task.yaml").exists():
            tasks.append(d)
    return tasks


def _run_single(
    model,
    task_dir: Path,
    workspace_base: Path,
    api_key: str,
    verbose: bool,
) -> RunResult | None:
    """Run a single model on a single task with an isolated workspace."""
    model_slug = model.id.replace("/", "_").replace(":", "_")
    workspace_dir = workspace_base / f"{task_dir.name}_{model_slug}"

    try:
        result = run_agent_on_task(
            model_config=model,
            task_dir=task_dir,
            workspace_dir=workspace_dir,
            api_key=api_key,
            verbose=verbose,
        )
        return result
    except Exception as e:
        print(f"\n  ERROR running {model.label} on {task_dir.name}: {e}")
        traceback.print_exc()
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run LLM agents against Saotri Bench tasks"
    )
    parser.add_argument(
        "--tier",
        choices=list(MODELS.keys()),
        help="Run only this model tier (default: all)",
    )
    parser.add_argument(
        "--models",
        help="Comma-separated list of model tier keys to run (e.g. claude-opus,gpt,deepseek)",
    )
    parser.add_argument(
        "--task",
        help="Run only this task (directory name, e.g. task_00_fizzbuzz)",
    )
    parser.add_argument(
        "--tasks-dir",
        default=str(PROJECT_ROOT / "tasks"),
        help="Path to tasks directory",
    )
    parser.add_argument(
        "--reports-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Path to reports output directory",
    )
    parser.add_argument(
        "--api-key",
        help="OpenRouter API key (or set OPENROUTER_API_KEY env var)",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Max parallel model runs per task (default: 1 = sequential)",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List configured models and exit",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity",
    )

    args = parser.parse_args()

    # List models
    if args.list_models:
        print("\nConfigured models:")
        for m in list_models():
            print(f"  [{m.tier}] {m.label}")
            print(f"         ID: {m.id}")
            print(f"         Temperature: {m.temperature}")
            print()
        return 0

    # Validate mutually exclusive options
    if args.tier and args.models:
        parser.error("--tier and --models are mutually exclusive")

    # Resolve API key
    api_key = args.api_key
    if not api_key:
        import os
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("Error: OpenRouter API key required.", file=sys.stderr)
        print("  Set OPENROUTER_API_KEY env var or use --api-key", file=sys.stderr)
        return 1

    # Resolve tasks
    tasks_dir = Path(args.tasks_dir)
    if not tasks_dir.exists():
        print(f"Error: Tasks directory not found: {tasks_dir}", file=sys.stderr)
        return 1

    if args.task:
        task_path = tasks_dir / args.task
        if not task_path.exists():
            print(f"Error: Task not found: {task_path}", file=sys.stderr)
            return 1
        task_dirs = [task_path]
    else:
        task_dirs = find_tasks(tasks_dir)
        if not task_dirs:
            print("Error: No tasks found.", file=sys.stderr)
            return 1

    # Resolve models
    if args.tier:
        models = [get_model(args.tier)]
    elif args.models:
        model_keys = [k.strip() for k in args.models.split(",")]
        for k in model_keys:
            if k not in MODELS:
                print(
                    f"Error: Unknown model key: {k}. "
                    f"Choose from: {', '.join(MODELS.keys())}",
                    file=sys.stderr,
                )
                return 1
        models = [get_model(k) for k in model_keys]
    else:
        models = list_models()

    # Setup reports
    reports_dir = Path(args.reports_dir)
    report_manager = ReportManager(reports_dir)

    verbose = not args.quiet
    max_workers = max(1, args.parallel)

    mode = "parallel" if max_workers > 1 else "sequential"
    print(f"\nSaotri Bench — LLM Agent Benchmark")
    print(f"Models:   {', '.join(m.label for m in models)}")
    print(f"Tasks:    {', '.join(t.name for t in task_dirs)}")
    print(f"Mode:     {mode}" + (f" (max {max_workers} workers)" if max_workers > 1 else ""))
    print(f"Reports:  {reports_dir}")

    # Run benchmarks
    all_results: list[RunResult] = []
    workspace_base = PROJECT_ROOT / "workspace"

    for task_dir in task_dirs:
        task_results: list[RunResult] = []

        if max_workers <= 1:
            # Sequential mode
            for model in models:
                result = _run_single(model, task_dir, workspace_base, api_key, verbose)
                if result:
                    report_path = report_manager.save_run_result(result)
                    if verbose:
                        print(f"  Report saved: {report_path}")
                    task_results.append(result)
        else:
            # Parallel mode
            print(f"\n  Running {len(models)} models in parallel (max {max_workers} workers)...")
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(
                        _run_single, m, task_dir, workspace_base, api_key, verbose
                    ): m
                    for m in models
                }
                for future in as_completed(futures):
                    model = futures[future]
                    result = future.result()
                    if result:
                        report_path = report_manager.save_run_result(result)
                        if verbose:
                            print(f"  Report saved ({model.label}): {report_path}")
                        task_results.append(result)

        all_results.extend(task_results)

        # Save per-task comparison
        if len(task_results) > 1:
            comp_path = report_manager.save_comparison_report(
                task_results, task_dir.name
            )
            if verbose:
                print(f"\n  Comparison report: {comp_path}")

    # Save full report
    if all_results:
        full_path = report_manager.save_full_report(all_results)
        report_manager.print_summary(all_results)
        print(f"\nFull report: {full_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
