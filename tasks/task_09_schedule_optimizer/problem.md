# Schedule Optimizer

## Problem
Implement a function that schedules tasks given dependencies and resource constraints.

## Input
- `tasks`: list of task dicts (each has `"id"`, `"duration"`, and optional fields)
- `constraints`: dict with scheduling constraints

## Output
- Scheduled tasks with start/end times

## Example
```python
tasks = [
    {"id": "A", "duration": 3},
    {"id": "B", "duration": 2},
]
constraints = {}
# [{"id": "A", "start": 0, "end": 3}, {"id": "B", "start": 3, "end": 5}]
```

## Notes
- Requirements become stricter in later phases
- Scheduling constraints and output format may evolve
- Error handling requirements may change
