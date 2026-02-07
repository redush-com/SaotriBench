"""Test cases for task_04_sort_objects."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — basic ascending sort by key
    TestCase(
        input={
            "items": [{"name": "Charlie"}, {"name": "Alice"}, {"name": "Bob"}],
            "key": "name",
        },
        expected=[{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}],
        phase=0,
        tags=["basic_sort"],
    ),
    TestCase(
        input={
            "items": [{"age": 30}, {"age": 10}, {"age": 20}],
            "key": "age",
        },
        expected=[{"age": 10}, {"age": 20}, {"age": 30}],
        phase=0,
        tags=["basic_sort"],
    ),
    TestCase(
        input={
            "items": [{"score": 100}],
            "key": "score",
        },
        expected=[{"score": 100}],
        phase=0,
        tags=["basic_sort"],
    ),

    # Phase 1 — stable sort: equal elements preserve original order
    TestCase(
        input={
            "items": [
                {"name": "Alice", "id": 1},
                {"name": "Bob", "id": 2},
                {"name": "Alice", "id": 3},
                {"name": "Bob", "id": 4},
            ],
            "key": "name",
        },
        expected=[
            {"name": "Alice", "id": 1},
            {"name": "Alice", "id": 3},
            {"name": "Bob", "id": 2},
            {"name": "Bob", "id": 4},
        ],
        phase=1,
        tags=["stability"],
    ),
    TestCase(
        input={
            "items": [
                {"grade": "A", "student": "X"},
                {"grade": "B", "student": "Y"},
                {"grade": "A", "student": "Z"},
            ],
            "key": "grade",
        },
        expected=[
            {"grade": "A", "student": "X"},
            {"grade": "A", "student": "Z"},
            {"grade": "B", "student": "Y"},
        ],
        phase=1,
        tags=["stability"],
    ),

    # Phase 2 — missing keys: objects without the key go to the end
    TestCase(
        input={
            "items": [
                {"name": "Charlie"},
                {"age": 25},
                {"name": "Alice"},
            ],
            "key": "name",
        },
        expected=[
            {"name": "Alice"},
            {"name": "Charlie"},
            {"age": 25},
        ],
        phase=2,
        tags=["missing_key"],
    ),
    TestCase(
        input={
            "items": [
                {"x": 3},
                {"y": 1},
                {"x": 1},
                {"z": 5},
            ],
            "key": "x",
        },
        expected=[
            {"x": 1},
            {"x": 3},
            {"y": 1},
            {"z": 5},
        ],
        phase=2,
        tags=["missing_key"],
    ),

    # Phase 3 — descending with "-" prefix
    TestCase(
        input={
            "items": [
                {"name": "Alice"},
                {"name": "Charlie"},
                {"name": "Bob"},
            ],
            "key": "-name",
        },
        expected=[
            {"name": "Charlie"},
            {"name": "Bob"},
            {"name": "Alice"},
        ],
        phase=3,
        tags=["descending"],
    ),
    TestCase(
        input={
            "items": [{"v": 1}, {"v": 3}, {"v": 2}],
            "key": "-v",
        },
        expected=[{"v": 3}, {"v": 2}, {"v": 1}],
        phase=3,
        tags=["descending"],
    ),
    # Descending with missing keys: missing still go to end
    TestCase(
        input={
            "items": [
                {"name": "Alice"},
                {"age": 25},
                {"name": "Charlie"},
            ],
            "key": "-name",
        },
        expected=[
            {"name": "Charlie"},
            {"name": "Alice"},
            {"age": 25},
        ],
        phase=3,
        tags=["descending"],
    ),

    # Phase 4 — multi-key sort: "name,age" or "-name,age"
    TestCase(
        input={
            "items": [
                {"name": "Bob", "age": 30},
                {"name": "Alice", "age": 25},
                {"name": "Alice", "age": 20},
                {"name": "Bob", "age": 20},
            ],
            "key": "name,age",
        },
        expected=[
            {"name": "Alice", "age": 20},
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 20},
            {"name": "Bob", "age": 30},
        ],
        phase=4,
        tags=["multi_key"],
    ),
    TestCase(
        input={
            "items": [
                {"name": "Alice", "age": 25},
                {"name": "Alice", "age": 20},
                {"name": "Bob", "age": 30},
            ],
            "key": "name,-age",
        },
        expected=[
            {"name": "Alice", "age": 25},
            {"name": "Alice", "age": 20},
            {"name": "Bob", "age": 30},
        ],
        phase=4,
        tags=["multi_key"],
    ),
    TestCase(
        input={
            "items": [
                {"a": 1, "b": 2},
                {"a": 1, "b": 1},
                {"a": 2, "b": 1},
            ],
            "key": "a,b",
        },
        expected=[
            {"a": 1, "b": 1},
            {"a": 1, "b": 2},
            {"a": 2, "b": 1},
        ],
        phase=4,
        tags=["multi_key"],
    ),

    # Phase 5 — error handling & empty input
    TestCase(
        input={
            "items": [],
            "key": "name",
        },
        expected=[],
        phase=5,
        tags=["empty_input"],
    ),
    TestCase(
        input={
            "items": [{"name": "Alice"}],
            "key": "",
        },
        expected="ValueError",
        phase=5,
        tags=["error_handling"],
    ),
    TestCase(
        input={
            "items": [{"name": "Alice"}],
            "key": ",",
        },
        expected="ValueError",
        phase=5,
        tags=["error_handling"],
    ),
    TestCase(
        input={
            "items": [{"name": "Alice"}],
            "key": ",,name",
        },
        expected="ValueError",
        phase=5,
        tags=["error_handling"],
    ),
]
