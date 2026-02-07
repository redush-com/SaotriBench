# Data Pipeline

## Problem
Implement a function that executes a data transformation pipeline on a list of records.

## Input
- `data`: list of record dicts
- `steps`: list of step dicts defining pipeline operations

## Output
- A dict with pipeline results

## Example
```python
data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
steps = [{"type": "rename", "from": "name", "to": "full_name"}]
run_pipeline(data, steps)
# {"result": [{"full_name": "Alice", "age": 30}, {"full_name": "Bob", "age": 25}]}
```

## Notes
- Requirements become stricter in later phases
- New step types and pipeline features may be introduced
- Output format may evolve
