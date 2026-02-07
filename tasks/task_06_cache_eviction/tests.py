"""Test cases for task_06_cache_eviction."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — basic put/get/delete
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a", "value": 1},
                {"op": "get", "key": "a"},
                {"op": "get", "key": "missing"},
            ],
            "config": {"capacity": 10},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok", "value": 1},
            {"status": "miss"},
        ],
        phase=0, tags=["basic_operations"],
    ),
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "x", "value": 10},
                {"op": "put", "key": "x", "value": 20},
                {"op": "get", "key": "x"},
                {"op": "delete", "key": "x"},
                {"op": "get", "key": "x"},
            ],
            "config": {"capacity": 10},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok", "value": 20},
            {"status": "ok"},
            {"status": "miss"},
        ],
        phase=0, tags=["basic_operations"],
    ),

    # Phase 1 — LRU eviction when capacity reached
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a", "value": 1},
                {"op": "put", "key": "b", "value": 2},
                {"op": "put", "key": "c", "value": 3},
                {"op": "put", "key": "d", "value": 4},  # evicts "a" (LRU)
                {"op": "get", "key": "a"},
                {"op": "get", "key": "b"},
            ],
            "config": {"capacity": 3},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok"},
            {"status": "miss"},  # "a" was evicted
            {"status": "ok", "value": 2},
        ],
        phase=1, tags=["capacity_eviction"],
    ),
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a", "value": 1},
                {"op": "put", "key": "b", "value": 2},
                {"op": "get", "key": "a"},  # "a" is now most recently used
                {"op": "put", "key": "c", "value": 3},
                {"op": "put", "key": "d", "value": 4},  # evicts "b" (LRU), not "a"
                {"op": "get", "key": "a"},
                {"op": "get", "key": "b"},
            ],
            "config": {"capacity": 3},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok", "value": 1},
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok", "value": 1},
            {"status": "miss"},
        ],
        phase=1, tags=["capacity_eviction"],
    ),

    # Phase 2 — TTL expiry
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a", "value": 1, "ttl": 5, "timestamp": 0},
                {"op": "get", "key": "a", "timestamp": 3},   # still valid
                {"op": "get", "key": "a", "timestamp": 6},   # expired
            ],
            "config": {"capacity": 10},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok", "value": 1},
            {"status": "miss"},  # TTL expired
        ],
        phase=2, tags=["ttl_expiry"],
    ),
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a", "value": 1, "ttl": 10, "timestamp": 0},
                {"op": "put", "key": "b", "value": 2, "ttl": 2, "timestamp": 0},
                {"op": "put", "key": "c", "value": 3, "timestamp": 0},
                # At timestamp 3, b expired. put d should evict expired b first, not LRU a
                {"op": "put", "key": "d", "value": 4, "timestamp": 3},
                {"op": "get", "key": "a", "timestamp": 3},
                {"op": "get", "key": "b", "timestamp": 3},
            ],
            "config": {"capacity": 3},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok", "value": 1},
            {"status": "miss"},  # expired
        ],
        phase=2, tags=["ttl_expiry"],
    ),

    # Phase 3 — priority-based eviction (low priority evicted first)
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a", "value": 1, "priority": 1},
                {"op": "put", "key": "b", "value": 2, "priority": 3},
                {"op": "put", "key": "c", "value": 3, "priority": 2},
                # capacity full; d has priority 2, evicts lowest priority = "a" (priority 1)
                {"op": "put", "key": "d", "value": 4, "priority": 2},
                {"op": "get", "key": "a"},
                {"op": "get", "key": "b"},
            ],
            "config": {"capacity": 3},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok"},
            {"status": "miss"},  # lowest priority evicted
            {"status": "ok", "value": 2},
        ],
        phase=3, tags=["priority_override"],
    ),
    # Same priority -> fall back to LRU within that priority
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a", "value": 1, "priority": 1},
                {"op": "put", "key": "b", "value": 2, "priority": 1},
                {"op": "put", "key": "c", "value": 3, "priority": 1},
                {"op": "get", "key": "a"},  # "a" refreshed
                {"op": "put", "key": "d", "value": 4, "priority": 1},  # evicts "b" (LRU among same prio)
                {"op": "get", "key": "b"},
                {"op": "get", "key": "a"},
            ],
            "config": {"capacity": 3},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok", "value": 1},
            {"status": "ok"},
            {"status": "miss"},
            {"status": "ok", "value": 1},
        ],
        phase=3, tags=["priority_override"],
    ),

    # Phase 4 — dirty eviction tracking
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a", "value": 1, "dirty": True},
                {"op": "put", "key": "b", "value": 2},
                {"op": "put", "key": "c", "value": 3},
                {"op": "put", "key": "d", "value": 4},  # evicts "a" which is dirty
            ],
            "config": {"capacity": 3},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok", "evicted": {"key": "a", "value": 1, "dirty": True}},
        ],
        phase=4, tags=["dirty_eviction"],
    ),
    # Non-dirty eviction: no eviction info
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a", "value": 1},
                {"op": "put", "key": "b", "value": 2},
                {"op": "put", "key": "c", "value": 3},
                {"op": "put", "key": "d", "value": 4},  # evicts "a" which is not dirty
            ],
            "config": {"capacity": 3},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok"},
        ],
        phase=4, tags=["dirty_eviction"],
    ),

    # Phase 5 — tiered capacity (capacity per priority level)
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a1", "value": 1, "priority": 1},
                {"op": "put", "key": "a2", "value": 2, "priority": 1},
                {"op": "put", "key": "a3", "value": 3, "priority": 1},  # tier 1 full (cap 2), evicts a1
                {"op": "put", "key": "b1", "value": 10, "priority": 2},
                {"op": "put", "key": "b2", "value": 20, "priority": 2},  # tier 2 still has room
                {"op": "get", "key": "a1"},
                {"op": "get", "key": "a2"},
                {"op": "get", "key": "b1"},
            ],
            "config": {"capacity": 2, "capacity_per_tier": True},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok"},
            {"status": "ok"},  # evicts a1 from tier 1
            {"status": "ok"},
            {"status": "ok"},
            {"status": "miss"},  # a1 evicted
            {"status": "ok", "value": 2},
            {"status": "ok", "value": 10},
        ],
        phase=5, tags=["tiered_capacity"],
    ),

    # Phase 6 — atomic batch operations
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a", "value": 1},
                {"op": "multi_put", "items": [
                    {"key": "b", "value": 2},
                    {"key": "c", "value": 3},
                ]},
                {"op": "multi_get", "keys": ["a", "b", "c", "d"]},
            ],
            "config": {"capacity": 10},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok", "count": 2},
            {"status": "ok", "results": [
                {"key": "a", "value": 1},
                {"key": "b", "value": 2},
                {"key": "c", "value": 3},
                {"key": "d", "value": None},
            ]},
        ],
        phase=6, tags=["atomicity"],
    ),
    # Atomic batch: if capacity doesn't fit all, entire batch fails
    TestCase(
        input={
            "operations": [
                {"op": "put", "key": "a", "value": 1},
                {"op": "put", "key": "b", "value": 2},
                {"op": "multi_put", "items": [
                    {"key": "c", "value": 3},
                    {"key": "d", "value": 4},
                    {"key": "e", "value": 5},
                ]},  # needs 3 slots but only 1 free after eviction = rollback
                {"op": "get", "key": "c"},
            ],
            "config": {"capacity": 3},
        },
        expected=[
            {"status": "ok"},
            {"status": "ok"},
            {"status": "error", "reason": "insufficient_capacity"},
            {"status": "miss"},  # batch was rolled back
        ],
        phase=6, tags=["atomicity"],
    ),

    # Phase 7 — performance (generated inline)
    TestCase(
        input={
            "operations": [{"op": "put", "key": f"k{i}", "value": i} for i in range(5000)]
                         + [{"op": "get", "key": f"k{i}"} for i in range(5000)],
            "config": {"capacity": 1000},
        },
        expected=[{"status": "ok"} for _ in range(5000)]
                 + [{"status": "miss"} if i < 4000 else {"status": "ok", "value": i} for i in range(5000)],
        phase=7, tags=["large_input"],
    ),
]
