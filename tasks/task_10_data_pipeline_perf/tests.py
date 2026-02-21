"""Test cases for task_10_data_pipeline_perf."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — performance
    TestCase(
        input={
            "data": [{"id": i, "value": i * 10, "group": f"g{i % 5}"} for i in range(3000)],
            "steps": [
                {"type": "filter", "field": "value", "op": ">=", "value": 100},
                {"type": "rename", "from": "group", "to": "category"},
            ],
        },
        expected={"result": [{"id": i, "value": i * 10, "category": f"g{i % 5}"} for i in range(10, 3000)]},
        phase=0, tags=["large_pipeline"],
    ),
]
