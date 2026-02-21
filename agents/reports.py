"""Report generation and storage for benchmark results."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bench_runner import RunResult


def _is_better(new: dict, old: dict) -> bool:
    """Return True if *new* result is better than *old* for the same pair."""
    if new["phases_completed"] != old["phases_completed"]:
        return new["phases_completed"] > old["phases_completed"]
    return new["timestamp"] > old["timestamp"]


def _get(r, field):
    """Get field from RunResult or dict."""
    if isinstance(r, dict):
        return r[field]
    return getattr(r, field)


class ReportManager:
    """Manages saving and loading benchmark reports."""

    def __init__(self, reports_dir: Path):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def load_all_results(self) -> list[dict]:
        """Load best result for each (model_id, task_id) from existing reports."""
        all_runs: dict[tuple[str, str], dict] = {}

        for path in sorted(self.reports_dir.glob("*/*/run_*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            key = (data["model_id"], data["task_id"])

            existing = all_runs.get(key)
            if existing is None or _is_better(data, existing):
                all_runs[key] = data

        return list(all_runs.values())

    def get_completed_pairs(self) -> set[tuple[str, str]]:
        """Return (model_id, task_id) pairs that have completed status."""
        return {
            (d["model_id"], d["task_id"])
            for d in self.load_all_results()
            if d["final_status"] == "completed"
        }

    def save_run_result(self, result: RunResult) -> Path:
        """Save a single run result to a JSON file.

        Returns:
            Path to the saved report file
        """
        # Create directory structure: reports/<task_id>/<model_tier>/
        task_dir = self.reports_dir / result.task_id
        model_dir = task_dir / result.model_tier
        model_dir.mkdir(parents=True, exist_ok=True)

        # Filename with timestamp
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"run_{ts}.json"
        filepath = model_dir / filename

        filepath.write_text(
            json.dumps(result.to_dict(), indent=2), encoding="utf-8"
        )
        return filepath

    def save_comparison_report(
        self, results: list, task_id: str
    ) -> Path:
        """Save a comparison report across models for one task.

        Accepts both RunResult objects and dicts loaded from JSON.

        Returns:
            Path to the comparison report
        """
        task_dir = self.reports_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        comparison = {
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "models_compared": len(results),
            "results": [],
        }

        for r in results:
            total_phases = _get(r, "total_phases")
            phases_completed = _get(r, "phases_completed")
            comparison["results"].append({
                "model": _get(r, "model_label"),
                "tier": _get(r, "model_tier"),
                "model_id": _get(r, "model_id"),
                "phases_completed": phases_completed,
                "total_phases": total_phases,
                "completion_rate": (
                    phases_completed / total_phases if total_phases > 0 else 0
                ),
                "total_attempts": _get(r, "total_attempts"),
                "final_status": _get(r, "final_status"),
                "token_usage": _get(r, "token_usage"),
                "duration_seconds": _get(r, "total_duration_seconds"),
                "phase_details": _get(r, "phase_results"),
            })

        # Sort by completion rate descending
        comparison["results"].sort(
            key=lambda x: (x["completion_rate"], -x["total_attempts"]),
            reverse=True,
        )

        filepath = task_dir / "comparison.json"
        filepath.write_text(
            json.dumps(comparison, indent=2), encoding="utf-8"
        )
        return filepath

    def save_full_report(self, all_results: list) -> Path:
        """Save a full benchmark report across all tasks and models.

        Accepts both RunResult objects and dicts loaded from JSON.

        Returns:
            Path to the full report
        """
        # Group by task
        by_task: dict[str, list] = {}
        for r in all_results:
            by_task.setdefault(_get(r, "task_id"), []).append(r)

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_runs": len(all_results),
            "tasks": {},
            "model_summary": {},
        }

        # Per-task breakdown
        for task_id, results in by_task.items():
            first = results[0]
            task_data = {
                "task_name": _get(first, "task_name"),
                "difficulty": _get(first, "difficulty"),
                "total_phases": _get(first, "total_phases"),
                "models": {},
            }
            for r in results:
                total_phases = _get(r, "total_phases")
                phases_completed = _get(r, "phases_completed")
                task_data["models"][_get(r, "model_label")] = {
                    "tier": _get(r, "model_tier"),
                    "phases_completed": phases_completed,
                    "total_attempts": _get(r, "total_attempts"),
                    "final_status": _get(r, "final_status"),
                    "completion_rate": (
                        phases_completed / total_phases
                        if total_phases > 0
                        else 0
                    ),
                    "tokens": _get(r, "token_usage")["total_tokens"],
                    "duration": _get(r, "total_duration_seconds"),
                }
            report["tasks"][task_id] = task_data

        # Per-model summary
        by_model: dict[str, list] = {}
        for r in all_results:
            by_model.setdefault(_get(r, "model_label"), []).append(r)

        for model_label, results in by_model.items():
            total_phases = sum(_get(r, "total_phases") for r in results)
            completed_phases = sum(_get(r, "phases_completed") for r in results)
            total_tokens = sum(
                _get(r, "token_usage")["total_tokens"] for r in results
            )
            total_duration = sum(
                _get(r, "total_duration_seconds") for r in results
            )
            tasks_completed = sum(
                1 for r in results if _get(r, "final_status") == "completed"
            )

            report["model_summary"][model_label] = {
                "tier": _get(results[0], "model_tier"),
                "model_id": _get(results[0], "model_id"),
                "tasks_run": len(results),
                "tasks_completed": tasks_completed,
                "task_completion_rate": (
                    tasks_completed / len(results) if results else 0
                ),
                "total_phases_completed": completed_phases,
                "total_phases": total_phases,
                "phase_completion_rate": (
                    completed_phases / total_phases if total_phases > 0 else 0
                ),
                "total_tokens": total_tokens,
                "total_duration": total_duration,
                "avg_duration_per_task": (
                    total_duration / len(results) if results else 0
                ),
            }

        filepath = self.reports_dir / "benchmark_report.json"
        filepath.write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        return filepath

    def print_summary(self, all_results: list) -> None:
        """Print a human-readable summary to stdout.

        Accepts both RunResult objects and dicts loaded from JSON.
        """
        print("\n" + "=" * 70)
        print("  BENCHMARK RESULTS SUMMARY")
        print("=" * 70)

        # Group by task
        by_task: dict[str, list] = {}
        for r in all_results:
            by_task.setdefault(_get(r, "task_id"), []).append(r)

        for task_id, results in by_task.items():
            first = results[0]
            task_name = _get(first, "task_name")
            difficulty = _get(first, "difficulty")
            total_phases = _get(first, "total_phases")

            print(f"\n  Task: {task_name} [{difficulty}] ({total_phases} phases)")
            print(f"  {'Model':<20} {'Tier':<8} {'Phases':<12} {'Attempts':<10} {'Status':<10} {'Tokens':<10} {'Time':<8}")
            print(f"  {'-'*20} {'-'*8} {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")

            # Sort by tier strength
            tier_order = {"strong": 0, "medium": 1, "weak": 2}
            results.sort(key=lambda r: tier_order.get(_get(r, "model_tier"), 99))

            for r in results:
                phases_completed = _get(r, "phases_completed")
                r_total = _get(r, "total_phases")
                phases_str = f"{phases_completed}/{r_total}"
                tokens_str = str(_get(r, "token_usage")["total_tokens"])
                time_str = f"{_get(r, 'total_duration_seconds'):.1f}s"
                status_map = {"completed": "PASS", "timeout": "TIME"}
                status_icon = status_map.get(_get(r, "final_status"), "FAIL")

                print(
                    f"  {_get(r, 'model_label'):<20} {_get(r, 'model_tier'):<8} {phases_str:<12} "
                    f"{_get(r, 'total_attempts'):<10} {status_icon:<10} {tokens_str:<10} {time_str:<8}"
                )

        print("\n" + "=" * 70)

    def load_report(self, path: Path) -> dict[str, Any]:
        """Load a report from a JSON file."""
        return json.loads(path.read_text(encoding="utf-8"))
