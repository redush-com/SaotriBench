# Fix Dashboard Completion Score Calculation

## Problem Description
The live dashboard currently shows a 100% completion rate (for Weighted Score, Pass Rate, and Phase Rate) for models that have passed all the tests they have been evaluated on, even if they haven't run the entire benchmark suite. 

This occurs because the dashboard calculates the total number of tasks by looking only at the tasks present in the `reports/` directory (the tests that have been executed so far), rather than looking at the entire suite of tasks defined in the benchmark (the `tasks/` directory).

## Expected Behavior
The denominator for calculating the Pass Rate, Phase Rate, and Weighted Score should be the **total number of tasks in the entire benchmark suite**, regardless of how many tasks the model has currently been evaluated against. This ensures that a model that has passed 1 out of 15 tasks shows a ~6.6% completion rate instead of 100%.

## Proposed Solution
There are two ways to approach this:

**Option 1: Backend Fix (Recommended)**
Update `serve_dashboard.py` in the `scan_results()` function. Instead of building the `tasks` dictionary dynamically from the parsed `reports/`, it should use the `get_all_tasks_meta()` function to populate the total list of tasks available in the benchmark suite.
```python
# Instead of inferring from reports:
tasks: dict[str, dict[str, Any]] = {}
for t in get_all_tasks_meta():
    tasks[t["task_id"]] = {
        "task_id": t["task_id"],
        "task_name": t["task_name"],
        "difficulty": t["difficulty"],
        "total_phases": t["total_phases"],
    }
```

**Option 2: Frontend Fix**
In `dashboard.html` and `model.html`, intercept the initial fetch. Make a parallel request to `/api/tasks` and overwrite `data.tasks` with the complete list of tasks before rendering the UI components.

## Acceptance Criteria
- [x] Dashboard shows correct Pass Rate, Phase Rate, and Weighted Score based on the full benchmark size.
- [x] Tasks that haven't been evaluated yet for a specific model appear as "Not tested" or "—" in the Pass / Fail Matrix and Model Detail pages.
- [x] The fix applies to both the main summary page (`dashboard.html`) and the detailed model page (`model.html`).

**Status:** ✅ Completed (2026-02-21)