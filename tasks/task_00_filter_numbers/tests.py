"""Test cases for task_00_filter_numbers."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 - basic filtering only
    TestCase(
        input=[1, 2, 3],
        expected=[1, 2, 3],
        phase=0,
        tags=["basic"],
    ),
    TestCase(
        input=[1, -2, 3],
        expected=[1, 3],
        phase=0,
        tags=["basic"],
    ),
    TestCase(
        input=[5, 10, 15],
        expected=[5, 10, 15],
        phase=0,
        tags=["basic"],
    ),
    TestCase(
        input=[-1, -2, -3],
        expected=[],
        phase=0,
        tags=["basic"],
    ),
    # Phase 1 - zeros and negatives
    TestCase(
        input=[0, 1, 2],
        expected=[1, 2],
        phase=1,
        tags=["zeros"],
    ),
    TestCase(
        input=[-1, 0, 3],
        expected=[3],
        phase=1,
        tags=["negatives"],
    ),
    TestCase(
        input=[0, 0, 0],
        expected=[],
        phase=1,
        tags=["zeros"],
    ),
    TestCase(
        input=[-5, -3, 0, 2, 4],
        expected=[2, 4],
        phase=1,
        tags=["negatives"],
    ),
    # Phase 2 - duplicates and ordering
    TestCase(
        input=[3, 1, 3, 2],
        expected=[3, 1, 3, 2],
        phase=2,
        tags=["duplicates"],
    ),
    TestCase(
        input=[1, 1, 1, 1],
        expected=[1, 1, 1, 1],
        phase=2,
        tags=["duplicates"],
    ),
    TestCase(
        input=[5, -1, 5, 0, 5],
        expected=[5, 5, 5],
        phase=2,
        tags=["duplicates"],
    ),
    TestCase(
        input=[10, 20, 10, 30, 20],
        expected=[10, 20, 10, 30, 20],
        phase=2,
        tags=["duplicates"],
    ),
]
