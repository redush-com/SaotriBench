# Merge Dictionaries

## Problem
Implement a function that merges two dictionaries into one. When both dictionaries have the same key, the conflict must be resolved according to specific rules.

## Input
- `a`: first dictionary
- `b`: second dictionary

## Output
- A new merged dictionary

## Examples
```python
merge({"a": 1}, {"b": 2})          # {"a": 1, "b": 2}
merge({}, {"a": 1})                 # {"a": 1}
merge({"a": 1, "b": 2}, {})        # {"a": 1, "b": 2}
```

## Notes
- Always return a new dictionary
- Do not modify the input dictionaries
- Conflict resolution rules may become more complex in later phases
