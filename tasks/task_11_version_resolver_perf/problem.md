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

## Algorithm Skeleton
To help you focus on inferring the evolving requirements rather than recalling complex graph algorithms from scratch, you may use the following backtracking template as a starting point. Your main task is to adapt this template to handle new features (ranges, peer dependencies, optional dependencies, platforms, etc.) as they are introduced.

```python
def resolve(dependencies: dict, registry: dict, options: dict | None = None) -> dict:
    resolved = {}
    
    def backtrack(deps_to_resolve: list[tuple[str, str]]) -> bool:
        if not deps_to_resolve:
            return True
            
        pkg, constraint = deps_to_resolve[0]
        # Skip if already resolved compatibly (naive check)
        if pkg in resolved:
            return backtrack(deps_to_resolve[1:])
            
        if pkg not in registry:
            return False
            
        # Get versions (in a real implementation, you would filter by constraint and sort)
        versions = registry[pkg].get("versions", [])
        
        for version in reversed(versions): # Try highest first
            # Apply version (naive matching)
            if version == constraint: # Extremely naive! Needs semver logic
                resolved[pkg] = version
                
                # Queue dependencies of this version
                new_deps = []
                pkg_deps = registry[pkg].get("deps", {}).get(version, {})
                for dep_pkg, dep_constraint in pkg_deps.items():
                    new_deps.append((dep_pkg, dep_constraint))
                
                if backtrack(new_deps + deps_to_resolve[1:]):
                    return True
                    
                # Backtrack
                del resolved[pkg]
                
        return False
        
    initial_deps = list(dependencies.items())
    if not backtrack(initial_deps):
        raise ValueError("Cannot resolve dependencies")
        
    return resolved
```
