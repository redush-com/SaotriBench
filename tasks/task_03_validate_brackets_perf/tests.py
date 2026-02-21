"""Test cases for task_03_validate_brackets_perf."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — large input performance
    TestCase(
        input="()" * 5000,
        expected=True,
        phase=0,
        tags=["large_input"],
    ),
    TestCase(
        input="(" * 5000 + ")" * 5000,
        expected=True,
        phase=0,
        tags=["large_input"],
    ),
    TestCase(
        input="{[" * 2500 + "]}" * 2500,
        expected=True,
        phase=0,
        tags=["large_input"],
    ),
    TestCase(
        input="(" * 10000,
        expected=False,
        phase=0,
        tags=["large_input", "error_position"],
    ),
]
