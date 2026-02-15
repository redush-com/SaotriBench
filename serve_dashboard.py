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

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
DASHBOARD_FILE = ROOT / "dashboard.html"
DASHBOARD_CSS = ROOT / "dashboard.css"
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


class DashboardHandler(SimpleHTTPRequestHandler):
    """Custom handler for dashboard routes."""

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self._serve_file(DASHBOARD_FILE, "text/html")
        elif self.path == "/dashboard.css":
            self._serve_file(DASHBOARD_CSS, "text/css")
        elif self.path == "/logo-32.png":
            self._serve_file(LOGO_FILE, "image/png")
        elif self.path == "/favicon.ico":
            self._serve_file(FAVICON_FILE, "image/x-icon")
        elif self.path == "/favicon-32x32.png":
            self._serve_file(FAVICON_PNG, "image/png")
        elif self.path == "/api/results":
            self._serve_json(scan_results())
        else:
            self.send_error(404)

    def _serve_file(self, path: Path, content_type: str) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            self.send_error(500, f"Cannot read {path}")
            return
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
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
