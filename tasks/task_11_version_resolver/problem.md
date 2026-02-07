# Version Resolver

## Problem
Implement a function that resolves package version dependencies.

## Input
- `dependencies`: dict mapping package names to version requirements (e.g. `{"A": "1.0.0"}`)
- `registry`: dict mapping package names to available version information
- `options`: optional dict with resolution options

## Output
- A dict mapping package names to resolved version strings

## Example
```python
deps = {"A": "1.0.0"}
registry = {"A": {"versions": ["1.0.0", "2.0.0"]}}
resolve(deps, registry)
# {"A": "1.0.0"}
```

## Notes
- Requirements become stricter in later phases
- Dependency semantics may evolve
- Error handling and output format may change
