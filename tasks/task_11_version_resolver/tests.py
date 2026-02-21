"""Test cases for task_11_version_resolver."""

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
    # Phase 0 — exact version match
    TestCase(
        input={
            "dependencies": {"A": "1.0.0"},
            "registry": {"A": {"versions": ["1.0.0", "2.0.0"]}},
        },
        expected={"A": "1.0.0"},
        phase=0, tags=["exact_match"],
    ),
    TestCase(
        input={
            "dependencies": {"A": "2.0.0", "B": "1.0.0"},
            "registry": {
                "A": {"versions": ["1.0.0", "2.0.0"]},
                "B": {"versions": ["1.0.0"]},
            },
        },
        expected={"A": "2.0.0", "B": "1.0.0"},
        phase=0, tags=["exact_match"],
    ),

    # Phase 1 — semver ranges
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0, <2.0.0"},
            "registry": {"A": {"versions": ["0.9.0", "1.0.0", "1.5.0", "2.0.0"]}},
        },
        expected={"A": "1.5.0"},  # highest in range
        phase=1, tags=["range_matching"],
    ),
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0"},
            "registry": {"A": {"versions": ["0.9.0", "1.0.0", "1.5.0", "2.0.0"]}},
        },
        expected={"A": "2.0.0"},
        phase=1, tags=["range_matching"],
    ),

    # Phase 2 — transitive deps
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0"},
            "registry": {
                "A": {
                    "versions": ["1.0.0", "1.1.0"],
                    "deps": {
                        "1.0.0": {"B": ">=1.0.0"},
                        "1.1.0": {"B": ">=1.0.0"},
                    },
                },
                "B": {"versions": ["1.0.0", "2.0.0"]},
            },
        },
        expected={"A": "1.1.0", "B": "2.0.0"},
        phase=2, tags=["transitive"],
    ),

    # Phase 3 — version conflict
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0", "C": ">=1.0.0"},
            "registry": {
                "A": {
                    "versions": ["1.0.0"],
                    "deps": {"1.0.0": {"B": ">=2.0.0"}},
                },
                "B": {"versions": ["1.0.0", "2.0.0"]},
                "C": {
                    "versions": ["1.0.0"],
                    "deps": {"1.0.0": {"B": "<2.0.0"}},
                },
            },
        },
        expected=None,  # ValueError: A needs B>=2.0.0, C needs B<2.0.0
        phase=3, tags=["version_conflict"],
    ),

    # Phase 4 — maximize version (pick highest compatible)
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0, <3.0.0"},
            "registry": {"A": {"versions": ["1.0.0", "1.5.0", "2.0.0", "2.5.0", "3.0.0"]}},
        },
        expected={"A": "2.5.0"},
        phase=4, tags=["maximize_version"],
    ),

    # Phase 5 — pre-release handling
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0"},
            "registry": {"A": {"versions": ["1.0.0", "1.1.0-beta", "1.1.0"]}},
        },
        expected={"A": "1.1.0"},  # pre-release excluded by default
        phase=5, tags=["prerelease_handling"],
    ),
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0"},
            "registry": {"A": {"versions": ["1.0.0", "1.1.0-beta", "1.1.0"]}},
            "options": {"include_prerelease": True},
        },
        expected={"A": "1.1.0"},  # 1.1.0 > 1.1.0-beta, so 1.1.0 is still picked
        phase=5, tags=["prerelease_handling"],
    ),
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0"},
            "registry": {"A": {"versions": ["1.0.0", "1.1.0-beta"]}},
            "options": {"include_prerelease": True},
        },
        expected={"A": "1.1.0-beta"},  # only pre-release available above 1.0.0
        phase=5, tags=["prerelease_handling"],
    ),

    # Phase 6 — circular dependency
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0"},
            "registry": {
                "A": {
                    "versions": ["1.0.0"],
                    "deps": {"1.0.0": {"B": ">=1.0.0"}},
                },
                "B": {
                    "versions": ["1.0.0"],
                    "deps": {"1.0.0": {"A": ">=1.0.0"}},
                },
            },
        },
        expected=None,  # ValueError: circular A -> B -> A
        phase=6, tags=["circular_dependency"],
    ),

    # Phase 7 — optional dependencies
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0"},
            "registry": {
                "A": {
                    "versions": ["1.0.0"],
                    "deps": {"1.0.0": {}},
                    "optional_deps": {"1.0.0": {"B": ">=1.0.0"}},
                },
                "B": {"versions": ["1.0.0", "2.0.0"]},
            },
        },
        expected={"A": "1.0.0"},  # B not included (optional, not requested)
        phase=7, tags=["optional_deps"],
    ),
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0", "B": ">=1.0.0"},
            "registry": {
                "A": {
                    "versions": ["1.0.0"],
                    "deps": {"1.0.0": {}},
                    "optional_deps": {"1.0.0": {"B": ">=1.0.0"}},
                },
                "B": {"versions": ["1.0.0", "2.0.0"]},
            },
        },
        expected={"A": "1.0.0", "B": "2.0.0"},  # B explicitly requested
        phase=7, tags=["optional_deps"],
    ),

    # Phase 8 — peer dependencies (must match parent's version)
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0"},
            "registry": {
                "A": {
                    "versions": ["1.0.0"],
                    "deps": {"1.0.0": {"B": ">=1.0.0"}},
                },
                "B": {
                    "versions": ["1.0.0", "2.0.0"],
                    "peer_deps": {"1.0.0": {"C": "1.0.0"}, "2.0.0": {"C": "2.0.0"}},
                },
                "C": {"versions": ["1.0.0", "2.0.0"]},
            },
        },
        expected={"A": "1.0.0", "B": "2.0.0", "C": "2.0.0"},  # B=2.0.0 requires C=2.0.0
        phase=8, tags=["peer_constraint"],
    ),

    # Phase 9 — backtracking (greedy first choice fails, must try next)
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0"},
            "registry": {
                "A": {
                    "versions": ["1.0.0", "2.0.0"],
                    "deps": {
                        "2.0.0": {"B": ">=2.0.0"},  # greedy picks A=2.0.0
                        "1.0.0": {"B": ">=1.0.0"},
                    },
                },
                "B": {"versions": ["1.0.0", "1.5.0"]},  # B>=2.0.0 fails -> must backtrack to A=1.0.0
            },
        },
        expected={"A": "1.0.0", "B": "1.5.0"},  # backtracked
        phase=9, tags=["backtrack_resolution"],
    ),

    # Phase 10 — lock file preference
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0, <3.0.0"},
            "registry": {"A": {"versions": ["1.0.0", "1.5.0", "2.0.0", "2.5.0"]}},
            "options": {"lock": {"A": "1.5.0"}},
        },
        expected={"A": "1.5.0"},  # prefer locked even though 2.5.0 is higher
        phase=10, tags=["lock_preference"],
    ),
    # Lock version out of range -> ignore lock, pick best
    TestCase(
        input={
            "dependencies": {"A": ">=2.0.0"},
            "registry": {"A": {"versions": ["1.0.0", "1.5.0", "2.0.0", "2.5.0"]}},
            "options": {"lock": {"A": "1.5.0"}},
        },
        expected={"A": "2.5.0"},  # lock 1.5.0 doesn't satisfy >=2.0.0
        phase=10, tags=["lock_preference"],
    ),

    # Phase 11 — platform constraints
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0"},
            "registry": {
                "A": {
                    "versions": ["1.0.0", "2.0.0"],
                    "platforms": {"1.0.0": ["linux", "windows"], "2.0.0": ["linux"]},
                },
            },
            "options": {"platform": "windows"},
        },
        expected={"A": "1.0.0"},  # 2.0.0 not available on windows
        phase=11, tags=["platform_filter"],
    ),

    # Phase 12 — resolution metadata
    TestCase(
        input={
            "dependencies": {"A": ">=1.0.0"},
            "registry": {
                "A": {
                    "versions": ["1.0.0", "1.1.0"],
                    "deps": {"1.0.0": {"B": "1.0.0"}, "1.1.0": {"B": "1.0.0"}},
                },
                "B": {"versions": ["1.0.0"]},
            },
        },
        expected={
            "resolved": {"A": "1.1.0", "B": "1.0.0"},
            "tree": {
                "A": {"version": "1.1.0", "deps": {"B": "1.0.0"}},
                "B": {"version": "1.0.0", "deps": {}},
            },
            "warnings": [],
        },
        phase=12, tags=["resolution_metadata"],
    ),

    # Phase 13 — deterministic (tested via rule, no extra test case needed)
]
