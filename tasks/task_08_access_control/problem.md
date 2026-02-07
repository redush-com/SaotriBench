# Access Control

## Problem
Implement a function that evaluates access control rules for a user on a resource.

## Input
- `user`: dict with user information (e.g. `{"id": "u1", "roles": ["editor"]}`)
- `resource`: dict with resource information (e.g. `{"id": "doc1", "type": "file"}`)
- `rules`: list of rule dicts defining access policies

## Output
- A dict with the access decision

## Example
```python
user = {"id": "u1", "roles": ["admin"]}
resource = {"id": "doc1", "type": "file"}
rules = [{"role": "admin", "resource_type": "file", "action": "allow"}]
check_access(user, resource, rules)
# {"allowed": True}
```

## Notes
- Requirements become stricter in later phases
- Access policies may evolve and interact
- Later phases may change output format
