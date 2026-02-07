"""Test cases for task_09_schedule_optimizer."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — sequential scheduling
    TestCase(
        input={
            "tasks": [{"id": "A", "duration": 3}, {"id": "B", "duration": 2}],
            "constraints": {},
        },
        expected=[{"id": "A", "start": 0, "end": 3}, {"id": "B", "start": 3, "end": 5}],
        phase=0, tags=["sequential"],
    ),
    TestCase(
        input={
            "tasks": [{"id": "X", "duration": 1}, {"id": "Y", "duration": 1}, {"id": "Z", "duration": 1}],
            "constraints": {},
        },
        expected=[{"id": "X", "start": 0, "end": 1}, {"id": "Y", "start": 1, "end": 2}, {"id": "Z", "start": 2, "end": 3}],
        phase=0, tags=["sequential"],
    ),

    # Phase 1 — dependency ordering
    TestCase(
        input={
            "tasks": [{"id": "A", "duration": 2}, {"id": "B", "duration": 3, "depends_on": ["A"]}],
            "constraints": {},
        },
        expected=[{"id": "A", "start": 0, "end": 2}, {"id": "B", "start": 2, "end": 5}],
        phase=1, tags=["dependency_order"],
    ),
    TestCase(
        input={
            "tasks": [
                {"id": "C", "duration": 1, "depends_on": ["A", "B"]},
                {"id": "A", "duration": 2},
                {"id": "B", "duration": 3},
            ],
            "constraints": {},
        },
        expected=[
            {"id": "A", "start": 0, "end": 2},
            {"id": "B", "start": 2, "end": 5},
            {"id": "C", "start": 5, "end": 6},
        ],
        phase=1, tags=["dependency_order"],
    ),

    # Phase 2 — parallel execution
    TestCase(
        input={
            "tasks": [
                {"id": "A", "duration": 3},
                {"id": "B", "duration": 2},
                {"id": "C", "duration": 4, "depends_on": ["A"]},
            ],
            "constraints": {},
        },
        expected=[
            {"id": "A", "start": 0, "end": 3},
            {"id": "B", "start": 0, "end": 2},  # runs parallel with A
            {"id": "C", "start": 3, "end": 7},
        ],
        phase=2, tags=["parallelism"],
    ),

    # Phase 3 — resource constraints
    TestCase(
        input={
            "tasks": [
                {"id": "A", "duration": 3, "resource": "cpu"},
                {"id": "B", "duration": 2, "resource": "cpu"},
                {"id": "C", "duration": 4, "resource": "gpu"},
            ],
            "constraints": {"max_per_resource": 1},
        },
        expected=[
            {"id": "A", "start": 0, "end": 3},
            {"id": "B", "start": 3, "end": 5},  # waits for cpu
            {"id": "C", "start": 0, "end": 4},  # different resource, parallel
        ],
        phase=3, tags=["resource_conflict"],
    ),

    # Phase 4 — priority scheduling
    TestCase(
        input={
            "tasks": [
                {"id": "A", "duration": 3, "resource": "cpu", "priority": 1},
                {"id": "B", "duration": 2, "resource": "cpu", "priority": 3},  # higher priority
                {"id": "C", "duration": 1, "resource": "cpu", "priority": 2},
            ],
            "constraints": {"max_per_resource": 1},
        },
        expected=[
            {"id": "B", "start": 0, "end": 2},  # highest priority first
            {"id": "C", "start": 2, "end": 3},
            {"id": "A", "start": 3, "end": 6},
        ],
        phase=4, tags=["priority_scheduling"],
    ),

    # Phase 5 — deadline violation
    TestCase(
        input={
            "tasks": [
                {"id": "A", "duration": 5, "deadline": 3},
            ],
            "constraints": {},
        },
        expected=None,  # ValueError
        phase=5, tags=["deadline_violation"],
    ),
    TestCase(
        input={
            "tasks": [
                {"id": "A", "duration": 2, "deadline": 5},
            ],
            "constraints": {},
        },
        expected=[{"id": "A", "start": 0, "end": 2}],
        phase=5, tags=["priority_scheduling"],
    ),

    # Phase 6 — priority inversion detection (warning in output)
    TestCase(
        input={
            "tasks": [
                {"id": "LOW", "duration": 5, "resource": "cpu", "priority": 1},
                {"id": "HIGH", "duration": 2, "resource": "cpu", "priority": 3},
            ],
            "constraints": {"max_per_resource": 1},
        },
        expected=[
            {"id": "HIGH", "start": 0, "end": 2},
            {"id": "LOW", "start": 2, "end": 7},
        ],
        phase=6, tags=["priority_scheduling"],  # no inversion here
    ),
    TestCase(
        input={
            "tasks": [
                {"id": "LOW", "duration": 5, "resource": "lock", "priority": 1},
                {"id": "MED", "duration": 2, "priority": 2},
                {"id": "HIGH", "duration": 2, "resource": "lock", "priority": 3, "depends_on": ["LOW"]},
            ],
            "constraints": {"max_per_resource": 1, "detect_inversion": True},
        },
        expected=[
            {"id": "LOW", "start": 0, "end": 5, "inversion_warning": True},
            {"id": "MED", "start": 0, "end": 2},
            {"id": "HIGH", "start": 5, "end": 7},
        ],
        phase=6, tags=["priority_inversion"],
    ),

    # Phase 7 — preemption
    TestCase(
        input={
            "tasks": [
                {"id": "LOW", "duration": 6, "resource": "cpu", "priority": 1},
                {"id": "HIGH", "duration": 2, "resource": "cpu", "priority": 3, "arrives_at": 2},
            ],
            "constraints": {"max_per_resource": 1, "preemption": True},
        },
        expected=[
            {"id": "LOW", "start": 0, "end": 2, "resumed_at": 4, "final_end": 8},
            {"id": "HIGH", "start": 2, "end": 4},
        ],
        phase=7, tags=["preemption_resume"],
    ),

    # Phase 8 — changeover time between different task types on same resource
    TestCase(
        input={
            "tasks": [
                {"id": "A", "duration": 2, "resource": "machine", "task_type": "drill"},
                {"id": "B", "duration": 3, "resource": "machine", "task_type": "cut"},
            ],
            "constraints": {"max_per_resource": 1, "changeover_time": 1},
        },
        expected=[
            {"id": "A", "start": 0, "end": 2},
            {"id": "B", "start": 3, "end": 6},  # 1 unit changeover
        ],
        phase=8, tags=["changeover_time"],
    ),
    # Same type = no changeover
    TestCase(
        input={
            "tasks": [
                {"id": "A", "duration": 2, "resource": "machine", "task_type": "drill"},
                {"id": "B", "duration": 3, "resource": "machine", "task_type": "drill"},
            ],
            "constraints": {"max_per_resource": 1, "changeover_time": 1},
        },
        expected=[
            {"id": "A", "start": 0, "end": 2},
            {"id": "B", "start": 2, "end": 5},  # no changeover
        ],
        phase=8, tags=["changeover_time"],
    ),

    # Phase 9 — rich output format
    TestCase(
        input={
            "tasks": [
                {"id": "A", "duration": 2, "resource": "cpu"},
                {"id": "B", "duration": 3, "resource": "cpu"},
            ],
            "constraints": {"max_per_resource": 1},
        },
        expected={
            "schedule": [
                {"id": "A", "start": 0, "end": 2},
                {"id": "B", "start": 2, "end": 5},
            ],
            "warnings": [],
            "makespan": 5,
        },
        phase=9, tags=["rich_output"],
    ),

    # Phase 10 — optimization (minimize makespan)
    TestCase(
        input={
            "tasks": [
                {"id": "A", "duration": 3, "resource": "r1"},
                {"id": "B", "duration": 2, "resource": "r2"},
                {"id": "C", "duration": 4, "resource": "r1"},
                {"id": "D", "duration": 1, "resource": "r2"},
            ],
            "constraints": {"max_per_resource": 1},
        },
        expected={
            "schedule": [
                {"id": "A", "start": 0, "end": 3},
                {"id": "B", "start": 0, "end": 2},
                {"id": "C", "start": 3, "end": 7},
                {"id": "D", "start": 2, "end": 3},
            ],
            "warnings": [],
            "makespan": 7,
        },
        phase=10, tags=["optimization"],
    ),

    # Phase 11 — determinism (multiple valid schedules, pick consistent one)
    TestCase(
        input={
            "tasks": [
                {"id": "B", "duration": 1},
                {"id": "A", "duration": 1},
                {"id": "C", "duration": 1},
            ],
            "constraints": {},
        },
        expected={
            "schedule": [
                {"id": "A", "start": 0, "end": 1},
                {"id": "B", "start": 0, "end": 1},
                {"id": "C", "start": 0, "end": 1},
            ],
            "warnings": [],
            "makespan": 1,
        },
        phase=11, tags=["deterministic_tiebreak"],
    ),
]
