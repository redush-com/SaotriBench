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

## Algorithm Skeleton
To help you focus on inferring evolving step execution constraints rather than designing complex data processing loops, you can start with a generic pipeline iterator that applies steps one by one.

```python
def run_pipeline(data: list[dict], steps: list[dict]) -> dict:
    import copy
    
    current_data = copy.deepcopy(data)
    errors = []
    
    for step in steps:
        step_type = step.get("type")
        new_data = []
        
        for record in current_data:
            rec = copy.deepcopy(record)
            try:
                if step_type == "rename":
                    old_name = step.get("from")
                    new_name = step.get("to")
                    if old_name in rec:
                        rec[new_name] = rec.pop(old_name)
                    new_data.append(rec)
                elif step_type == "filter":
                    # Basic filter logic
                    if rec.get(step.get("field")) == step.get("value"):
                        new_data.append(rec)
                else:
                    new_data.append(rec)
            except Exception as e:
                errors.append({"record": record, "error": str(e)})
                
        current_data = new_data
        
    return {"result": current_data}
```
