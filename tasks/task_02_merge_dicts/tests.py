"""Test cases for task_02_merge_dicts.

Rules (cumulative):
  Phase 0: merge two dicts (no overlapping keys in these tests)
  Phase 1: numeric conflicts -> sum, string conflicts -> concat, else b overrides.
           Plus no_mutation.
  Phase 2: nested dicts merged recursively. Nested numeric conflicts still sum.
  Phase 3: list conflicts -> merge without duplicates, preserve order from a then b.

Expected values reflect FINAL correct behavior. Earlier phases use inputs
that don't trigger later rules (no key conflicts in phase 0, no nested/list
in phase 1, etc.).
"""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — non-overlapping merge (no conflicts at all)
    # Simple {**a, **b} passes these and so does the final solution.
    TestCase(
        input={"a": {"a": 1}, "b": {"b": 2}},
        expected={"a": 1, "b": 2},
        phase=0,
        tags=["basic"],
    ),
    TestCase(
        input={"a": {}, "b": {"a": 1}},
        expected={"a": 1},
        phase=0,
        tags=["basic"],
    ),
    TestCase(
        input={"a": {"a": 1, "b": 2}, "b": {}},
        expected={"a": 1, "b": 2},
        phase=0,
        tags=["basic"],
    ),
    TestCase(
        input={"a": {"x": 10}, "b": {"y": 20}},
        expected={"x": 10, "y": 20},
        phase=0,
        tags=["basic"],
    ),
    TestCase(
        input={"a": {}, "b": {}},
        expected={},
        phase=0,
        tags=["basic"],
    ),

    # Phase 1 — type-aware conflict resolution
    # numeric + numeric => sum
    TestCase(
        input={"a": {"x": 10}, "b": {"x": 5}},
        expected={"x": 15},
        phase=1,
        tags=["numeric_conflict"],
    ),
    TestCase(
        input={"a": {"v": 100, "w": 200}, "b": {"v": 50, "w": 30}},
        expected={"v": 150, "w": 230},
        phase=1,
        tags=["numeric_conflict"],
    ),
    # string + string => concatenate
    TestCase(
        input={"a": {"name": "hello"}, "b": {"name": " world"}},
        expected={"name": "hello world"},
        phase=1,
        tags=["string_conflict"],
    ),
    TestCase(
        input={"a": {"s": "foo"}, "b": {"s": "bar"}},
        expected={"s": "foobar"},
        phase=1,
        tags=["string_conflict"],
    ),
    # different types => b overrides
    TestCase(
        input={"a": {"x": 10}, "b": {"x": "override"}},
        expected={"x": "override"},
        phase=1,
        tags=["override"],
    ),
    TestCase(
        input={"a": {"x": "text"}, "b": {"x": 42}},
        expected={"x": 42},
        phase=1,
        tags=["override"],
    ),

    # Phase 2 — nested dicts merged recursively
    TestCase(
        input={
            "a": {"config": {"debug": True, "level": 1}},
            "b": {"config": {"level": 2, "verbose": False}},
        },
        expected={"config": {"debug": True, "level": 3, "verbose": False}},
        phase=2,
        tags=["nested_merge"],
    ),
    TestCase(
        input={
            "a": {"db": {"host": "localhost", "port": 5432}},
            "b": {"db": {"port": 3306}},
        },
        expected={"db": {"host": "localhost", "port": 8738}},
        phase=2,
        tags=["nested_merge"],
    ),
    TestCase(
        input={
            "a": {"a": {"b": {"c": 1}}},
            "b": {"a": {"b": {"d": 2}}},
        },
        expected={"a": {"b": {"c": 1, "d": 2}}},
        phase=2,
        tags=["nested_merge"],
    ),
    TestCase(
        input={
            "a": {"outer": {"inner": "hello"}},
            "b": {"outer": {"inner": " world"}},
        },
        expected={"outer": {"inner": "hello world"}},
        phase=2,
        tags=["nested_merge"],
    ),

    # Phase 3 — list conflicts: merge without duplicates, preserve order (a then b)
    TestCase(
        input={
            "a": {"tags": [1, 2, 3]},
            "b": {"tags": [3, 4, 5]},
        },
        expected={"tags": [1, 2, 3, 4, 5]},
        phase=3,
        tags=["list_merge"],
    ),
    TestCase(
        input={
            "a": {"items": ["a", "b"]},
            "b": {"items": ["b", "c", "a"]},
        },
        expected={"items": ["a", "b", "c"]},
        phase=3,
        tags=["list_merge"],
    ),
    TestCase(
        input={
            "a": {"ids": []},
            "b": {"ids": [1, 2]},
        },
        expected={"ids": [1, 2]},
        phase=3,
        tags=["list_merge"],
    ),
    TestCase(
        input={
            "a": {"data": [10, 20]},
            "b": {"data": [20, 30, 10]},
        },
        expected={"data": [10, 20, 30]},
        phase=3,
        tags=["list_merge"],
    ),
]
