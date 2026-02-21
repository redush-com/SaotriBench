"""Test cases for task_11_version_resolver_perf."""

from saotri_bench.models import TestCase

def _large_registry():
    """Generate a large registry for performance testing."""
    registry = {}
    for i in range(50):
        pkg = f"pkg{i}"
        versions = [f"{major}.{minor}.0" for major in range(1, 4) for minor in range(5)]
        deps = {}
        if i > 0:
            deps[f"pkg{i-1}"] = f">={1}.0.0, <3.0.0"
        registry[pkg] = {
            "versions": versions,
            "deps": {v: deps for v in versions},
        }
    return registry

TEST_CASES = [
    # Phase 0 — performance with large registry
    TestCase(
        input={
            "dependencies": {"pkg49": ">=1.0.0, <3.0.0"},
            "registry": _large_registry(),
        },
        expected={f"pkg{i}": "2.4.0" for i in range(50)},  # highest in range for each
        phase=0, tags=["large_registry"],
    ),
]
