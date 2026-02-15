"""Lightweight HTTP server for the Saotri Bench real-time dashboard.

Serves dashboard.html at / and exposes /api/results which scans
reports/**/*.json to build aggregated benchmark data.

Usage:
    python serve_dashboard.py [--port 8050]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
TASKS_DIR = ROOT / "tasks"
DASHBOARD_FILE = ROOT / "dashboard.html"
DASHBOARD_CSS = ROOT / "dashboard.css"
MODEL_FILE = ROOT / "model.html"
LOGO_FILE = ROOT / "logo-32.png"
FAVICON_FILE = ROOT / "favicon.ico"
FAVICON_PNG = ROOT / "favicon-32x32.png"


def scan_results() -> dict[str, Any]:
    """Walk reports/ and read every run_*.json, returning aggregated data."""
    runs: list[dict[str, Any]] = []

    for dirpath, _dirnames, filenames in os.walk(REPORTS_DIR):
        for fname in filenames:
            if not fname.startswith("run_") or not fname.endswith(".json"):
                continue
            fpath = Path(dirpath) / fname
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                # Extract timestamp from filename for sorting: run_YYYYMMDD_HHMMSS.json
                m = re.search(r"run_(\d{8}_\d{6})", fname)
                data["_sort_key"] = m.group(1) if m else ""
                runs.append(data)
            except (json.JSONDecodeError, OSError):
                continue

    # Deduplicate: keep latest run per (model_label, task_id)
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for run in runs:
        key = (run.get("model_label", ""), run.get("task_id", ""))
        existing = latest.get(key)
        if existing is None or run["_sort_key"] > existing["_sort_key"]:
            latest[key] = run

    # Build structured response
    models: set[str] = set()
    tasks: dict[str, dict[str, Any]] = {}  # task_id -> task meta

    results: list[dict[str, Any]] = []
    for run in latest.values():
        model = run.get("model_label", "unknown")
        task_id = run.get("task_id", "unknown")
        models.add(model)

        if task_id not in tasks:
            tasks[task_id] = {
                "task_id": task_id,
                "task_name": run.get("task_name", task_id),
                "difficulty": run.get("difficulty", "unknown"),
                "total_phases": run.get("total_phases", 0),
            }

        # Strip internal sort key before sending
        clean = {k: v for k, v in run.items() if not k.startswith("_")}
        results.append(clean)

    # Sort tasks by task_id, models alphabetically
    sorted_tasks = sorted(tasks.values(), key=lambda t: t["task_id"])
    sorted_models = sorted(models)

    return {
        "models": sorted_models,
        "tasks": sorted_tasks,
        "results": results,
    }


def load_task_yaml(task_id: str) -> dict[str, Any] | None:
    """Load and parse a task.yaml file, returning phase descriptions."""
    yaml_path = TASKS_DIR / task_id / "task.yaml"
    if not yaml_path.exists():
        return None
    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        return data
    except (yaml.YAMLError, OSError):
        return None


def get_all_tasks_meta() -> list[dict[str, Any]]:
    """Load metadata + phase descriptions for all tasks from task.yaml files."""
    tasks = []
    if not TASKS_DIR.exists():
        return tasks
    for d in sorted(TASKS_DIR.iterdir()):
        if not d.is_dir() or not (d / "task.yaml").exists():
            continue
        data = load_task_yaml(d.name)
        if not data:
            continue
        phases = []
        for p in data.get("phases", []):
            phases.append({
                "id": p.get("id"),
                "description": p.get("description", ""),
                "rules": [
                    {"id": r.get("id", ""), "description": r.get("description", "")}
                    for r in p.get("rules", [])
                ],
            })
        tasks.append({
            "task_id": data.get("id", d.name),
            "task_name": data.get("name", d.name),
            "description": data.get("description", ""),
            "difficulty": data.get("difficulty", "unknown"),
            "total_phases": len(phases),
            "phases": phases,
            "interface": data.get("interface", {}),
            "limits": data.get("limits", {}),
        })
    return tasks


def get_model_detail(model_label: str) -> dict[str, Any]:
    """Get all run data for a specific model, enriched with task phase info."""
    all_data = scan_results()
    tasks_meta = get_all_tasks_meta()
    task_phases = {t["task_id"]: t for t in tasks_meta}

    model_results = [
        r for r in all_data["results"] if r.get("model_label") == model_label
    ]

    enriched = []
    for r in model_results:
        tid = r.get("task_id", "")
        task_info = task_phases.get(tid, {})
        phase_descs = {p["id"]: p for p in task_info.get("phases", [])}

        enriched_phases = []
        for pr in r.get("phase_results", []):
            pid = pr.get("phase_id")
            desc = phase_descs.get(pid, {})
            enriched_phases.append({
                **pr,
                "phase_description": desc.get("description", ""),
                "rules": desc.get("rules", []),
            })

        enriched.append({
            **r,
            "task_description": task_info.get("description", ""),
            "phase_results": enriched_phases,
        })

    enriched.sort(key=lambda r: r.get("task_id", ""))

    return {
        "model_label": model_label,
        "model_id": model_results[0].get("model_id", "") if model_results else "",
        "model_tier": model_results[0].get("model_tier", "") if model_results else "",
        "results": enriched,
        "all_tasks": all_data["tasks"],
        "all_models_data": all_data,
    }


class DashboardHandler(SimpleHTTPRequestHandler):
    """Custom handler for dashboard routes."""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._serve_file(DASHBOARD_FILE, "text/html")
        elif path == "/model":
            self._serve_file(MODEL_FILE, "text/html")
        elif path == "/dashboard.css":
            self._serve_file(DASHBOARD_CSS, "text/css")
        elif path == "/logo-32.png":
            self._serve_file(LOGO_FILE, "image/png")
        elif path == "/favicon.ico":
            self._serve_file(FAVICON_FILE, "image/x-icon")
        elif path == "/favicon-32x32.png":
            self._serve_file(FAVICON_PNG, "image/png")
        elif path == "/api/results":
            self._serve_json(scan_results())
        elif path == "/api/tasks":
            self._serve_json(get_all_tasks_meta())
        elif path == "/api/model":
            name = qs.get("name", [""])[0]
            if not name:
                self.send_error(400, "Missing ?name= parameter")
                return
            self._serve_json(get_model_detail(name))
        else:
            self.send_error(404)

    def _serve_file(self, path: Path, content_type: str) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            self.send_error(500, f"Cannot read {path}")
            return
        self.send_response(200)
        ct = f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _serve_json(self, obj: Any) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:
        # Quieter logging — only log errors
        if args and isinstance(args[0], str) and args[0].startswith("GET /api"):
            return  # suppress poll noise
        super().log_message(format, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Saotri Bench Dashboard Server")
    parser.add_argument("--port", type=int, default=8050, help="Port (default: 8050)")
    args = parser.parse_args()

    if not DASHBOARD_FILE.exists():
        print(f"Error: {DASHBOARD_FILE} not found", file=sys.stderr)
        sys.exit(1)

    server = HTTPServer(("0.0.0.0", args.port), DashboardHandler)
    print(f"Dashboard running at http://localhost:{args.port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
