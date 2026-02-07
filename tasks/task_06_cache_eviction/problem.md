# Cache Eviction

## Problem
Implement a function that processes a sequence of cache operations and returns results.

## Input
- `operations`: list of operation dicts, each with `"op"` key (`"get"`, `"put"`, `"delete"`)
- `config`: dict with cache configuration (e.g. `{"capacity": 3}`)

## Output
- A list of result dicts, one per operation

## Example
```python
ops = [
    {"op": "put", "key": "a", "value": 1},
    {"op": "get", "key": "a"},
    {"op": "get", "key": "b"},
]
config = {"capacity": 10}
# [{"status": "ok"}, {"status": "ok", "value": 1}, {"status": "miss"}]
```

## Notes
- Requirements become stricter in later phases
- Eviction policies may evolve
- Cache behavior may change based on configuration
