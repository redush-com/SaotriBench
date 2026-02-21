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

## Algorithm Skeleton
To help you focus on inferring constraints rather than designing complex algorithms from scratch, here is a starting template for processing dependent nodes (e.g., using topological sorting or a simple queue).

```python
def optimize_schedule(tasks: list[dict], constraints: dict) -> list[dict]:
    # Identify dependencies and degrees
    in_degree = {t["id"]: 0 for t in tasks}
    adj_list = {t["id"]: [] for t in tasks}
    task_dict = {t["id"]: t for t in tasks}
    
    # Process constraints (assuming "dependencies" exist in constraints)
    deps = constraints.get("dependencies", [])
    for dep in deps:
        u, v = dep["from"], dep["to"]
        if u in adj_list and v in in_degree:
            adj_list[u].append(v)
            in_degree[v] += 1
            
    # Topological sort (queue for nodes with 0 in-degree)
    import collections
    queue = collections.deque([u for u in in_degree if in_degree[u] == 0])
    
    scheduled = []
    current_time = 0
    
    while queue:
        u = queue.popleft()
        duration = task_dict[u].get("duration", 1)
        
        # Schedule the task sequentially
        scheduled.append({
            "id": u,
            "start": current_time,
            "end": current_time + duration
        })
        current_time += duration
        
        # Release dependencies
        for v in adj_list[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
                
    if len(scheduled) != len(tasks):
        raise ValueError("Circular dependency detected")
        
    return scheduled
```
