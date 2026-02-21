"""Test cases for task_10_data_pipeline."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — basic rename transform
    TestCase(
        input={
            "data": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
            "steps": [{"type": "rename", "from": "name", "to": "full_name"}],
        },
        expected={"result": [{"full_name": "Alice", "age": 30}, {"full_name": "Bob", "age": 25}]},
        phase=0, tags=["basic_transform"],
    ),

    # Phase 1 — step chaining
    TestCase(
        input={
            "data": [{"name": "Alice", "age": 30}],
            "steps": [
                {"type": "rename", "from": "name", "to": "user"},
                {"type": "rename", "from": "age", "to": "years"},
            ],
        },
        expected={"result": [{"user": "Alice", "years": 30}]},
        phase=1, tags=["step_chaining"],
    ),

    # Phase 2 — filter
    TestCase(
        input={
            "data": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 17},
                {"name": "Carol", "age": 25},
            ],
            "steps": [{"type": "filter", "field": "age", "op": ">=", "value": 18}],
        },
        expected={"result": [{"name": "Alice", "age": 30}, {"name": "Carol", "age": 25}]},
        phase=2, tags=["filter_records"],
    ),

    # Phase 3 — aggregation
    TestCase(
        input={
            "data": [
                {"dept": "eng", "salary": 100},
                {"dept": "eng", "salary": 120},
                {"dept": "sales", "salary": 90},
            ],
            "steps": [{"type": "aggregate", "group_by": "dept", "field": "salary", "op": "sum"}],
        },
        expected={"result": [{"dept": "eng", "salary_sum": 220}, {"dept": "sales", "salary_sum": 90}]},
        phase=3, tags=["aggregation"],
    ),
    TestCase(
        input={
            "data": [
                {"dept": "eng", "salary": 100},
                {"dept": "eng", "salary": 120},
                {"dept": "sales", "salary": 90},
            ],
            "steps": [{"type": "aggregate", "group_by": "dept", "field": "salary", "op": "count"}],
        },
        expected={"result": [{"dept": "eng", "salary_count": 2}, {"dept": "sales", "salary_count": 1}]},
        phase=3, tags=["aggregation"],
    ),

    # Phase 4 — schema mismatch detection
    TestCase(
        input={
            "data": [{"name": "Alice", "age": 30}],
            "steps": [
                {"type": "rename", "from": "name", "to": "user"},
                {"type": "filter", "field": "name", "op": "==", "value": "Alice"},  # "name" no longer exists!
            ],
        },
        expected={"result": [], "errors": [{"step": 1, "error": "field_not_found", "field": "name"}]},
        phase=4, tags=["schema_mismatch"],
    ),

    # Phase 5 — null handling
    TestCase(
        input={
            "data": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": None},
                {"name": None, "age": 25},
            ],
            "steps": [{"type": "filter", "field": "age", "op": ">=", "value": 18}],
        },
        expected={"result": [{"name": "Alice", "age": 30}, {"name": None, "age": 25}]},  # null age skipped in filter
        phase=5, tags=["null_semantics"],
    ),
    TestCase(
        input={
            "data": [
                {"dept": "eng", "salary": 100},
                {"dept": "eng", "salary": None},
                {"dept": "sales", "salary": 90},
            ],
            "steps": [{"type": "aggregate", "group_by": "dept", "field": "salary", "op": "sum"}],
        },
        expected={"result": [{"dept": "eng", "salary_sum": 100}, {"dept": "sales", "salary_sum": 90}]},  # null skipped
        phase=5, tags=["null_semantics"],
    ),

    # Phase 6 — error partitioning
    TestCase(
        input={
            "data": [
                {"name": "Alice", "age": 30},
                {"name": "Bob"},  # missing "age"
                {"name": "Carol", "age": 25},
            ],
            "steps": [{"type": "filter", "field": "age", "op": ">=", "value": 18}],
        },
        expected={
            "result": [{"name": "Alice", "age": 30}, {"name": "Carol", "age": 25}],
            "errors": [{"record": {"name": "Bob"}, "step": 0, "error": "missing_field", "field": "age"}],
        },
        phase=6, tags=["error_partition"],
    ),

    # Phase 7 — conditional step execution
    TestCase(
        input={
            "data": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
            "steps": [
                {"type": "filter", "field": "age", "op": ">=", "value": 18},
                {"type": "rename", "from": "name", "to": "user", "condition": {"min_records": 2}},
            ],
        },
        expected={"result": [{"user": "Alice", "age": 30}, {"user": "Bob", "age": 25}]},
        phase=7, tags=["conditional_execution"],
    ),
    TestCase(
        input={
            "data": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 15}],
            "steps": [
                {"type": "filter", "field": "age", "op": ">=", "value": 18},
                {"type": "rename", "from": "name", "to": "user", "condition": {"min_records": 2}},
            ],
        },
        expected={"result": [{"name": "Alice", "age": 30}]},  # condition not met, rename skipped
        phase=7, tags=["conditional_execution"],
    ),

    # Phase 8 — cross-step reference
    TestCase(
        input={
            "data": [
                {"name": "Alice", "score": 80},
                {"name": "Bob", "score": 60},
                {"name": "Carol", "score": 90},
            ],
            "steps": [
                {"type": "aggregate", "group_by": None, "field": "score", "op": "avg", "save_as": "avg_score"},
                {"type": "add_field", "name": "above_avg", "expression": "record.score > steps.avg_score"},
            ],
        },
        expected={"result": [
            {"name": "Alice", "score": 80, "above_avg": True},
            {"name": "Bob", "score": 60, "above_avg": False},
            {"name": "Carol", "score": 90, "above_avg": True},
        ]},
        phase=8, tags=["cross_step_reference"],
    ),

    # Phase 9 — idempotency tested via deterministic rule (no extra test needed)

    # Phase 10 — observability (metadata in output)
    TestCase(
        input={
            "data": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
            "steps": [
                {"type": "rename", "from": "name", "to": "user"},
                {"type": "filter", "field": "age", "op": ">=", "value": 28},
            ],
        },
        expected={
            "result": [{"user": "Alice", "age": 30}],
            "metadata": {
                "steps": [
                    {"step": 0, "type": "rename", "records_in": 2, "records_out": 2},
                    {"step": 1, "type": "filter", "records_in": 2, "records_out": 1},
                ],
                "total_records_in": 2,
                "total_records_out": 1,
            },
        },
        phase=10, tags=["observability"],
    ),
]
