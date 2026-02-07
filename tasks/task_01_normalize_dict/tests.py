"""Test cases for task_01_normalize_dict."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 - basic normalization
    TestCase(
        input={"Name": "John", "AGE": 30},
        expected={"name": "john", "age": 30},
        phase=0,
        tags=["flat"],
    ),
    TestCase(
        input={"A": "B", "C": "D"},
        expected={"a": "b", "c": "d"},
        phase=0,
        tags=["flat"],
    ),
    TestCase(
        input={},
        expected={},
        phase=0,
        tags=["empty"],
    ),
    TestCase(
        input={"User": {"Name": "Alice", "Email": "ALICE@EXAMPLE.COM"}},
        expected={"user": {"name": "alice", "email": "alice@example.com"}},
        phase=0,
        tags=["nested"],
    ),
    TestCase(
        input={"Level1": {"Level2": {"Level3": "VALUE"}}},
        expected={"level1": {"level2": {"level3": "value"}}},
        phase=0,
        tags=["nested"],
    ),
    # Phase 1 - edge cases
    TestCase(
        input={"Key": 123, "Other": 45.67},
        expected={"key": 123, "other": 45.67},
        phase=1,
        tags=["special_values"],
    ),
    TestCase(
        input={"Bool": True, "List": [1, 2, 3]},
        expected={"bool": True, "list": [1, 2, 3]},
        phase=1,
        tags=["special_values"],
    ),
    TestCase(
        input={"A": {"B": {"C": {"D": {"E": "DEEP"}}}}},
        expected={"a": {"b": {"c": {"d": {"e": "deep"}}}}},
        phase=1,
        tags=["large_depth"],
    ),
    TestCase(
        input={"Mixed": {"Num": 42, "Str": "HELLO", "Nested": {"X": "Y"}}},
        expected={"mixed": {"num": 42, "str": "hello", "nested": {"x": "y"}}},
        phase=1,
        tags=["nested"],
    ),
    # Phase 2 - None values
    TestCase(
        input={"Key": None, "Other": "VALUE"},
        expected={"key": None, "other": "value"},
        phase=2,
        tags=["none_values"],
    ),
    TestCase(
        input={"Nested": {"Inner": None}},
        expected={"nested": {"inner": None}},
        phase=2,
        tags=["none_values"],
    ),
    TestCase(
        input={"A": None, "B": {"C": None, "D": "E"}},
        expected={"a": None, "b": {"c": None, "d": "e"}},
        phase=2,
        tags=["none_values"],
    ),
]
