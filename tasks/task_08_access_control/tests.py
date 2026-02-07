"""Test cases for task_08_access_control."""

from saotri_bench.models import TestCase

TEST_CASES = [
    # Phase 0 — basic role check
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["admin"]},
            "resource": {"id": "doc1", "type": "file"},
            "rules": [{"role": "admin", "resource_type": "file", "action": "allow"}],
        },
        expected={"allowed": True},
        phase=0, tags=["basic_role_check"],
    ),
    TestCase(
        input={
            "user": {"id": "u2", "roles": ["viewer"]},
            "resource": {"id": "doc1", "type": "file"},
            "rules": [{"role": "admin", "resource_type": "file", "action": "allow"}],
        },
        expected={"allowed": False},
        phase=0, tags=["basic_role_check"],
    ),

    # Phase 1 — multiple roles: any matching role grants access
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["viewer", "editor"]},
            "resource": {"id": "doc1", "type": "file"},
            "rules": [{"role": "editor", "resource_type": "file", "action": "allow"}],
        },
        expected={"allowed": True},
        phase=1, tags=["multi_role"],
    ),
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["viewer", "commenter"]},
            "resource": {"id": "doc1", "type": "file"},
            "rules": [{"role": "editor", "resource_type": "file", "action": "allow"}],
        },
        expected={"allowed": False},
        phase=1, tags=["multi_role"],
    ),

    # Phase 2 — ownership override: owner always has access
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["viewer"]},
            "resource": {"id": "doc1", "type": "file", "owner": "u1"},
            "rules": [{"role": "admin", "resource_type": "file", "action": "allow"}],
        },
        expected={"allowed": True},  # owner override
        phase=2, tags=["ownership_override"],
    ),
    TestCase(
        input={
            "user": {"id": "u2", "roles": ["viewer"]},
            "resource": {"id": "doc1", "type": "file", "owner": "u1"},
            "rules": [{"role": "admin", "resource_type": "file", "action": "allow"}],
        },
        expected={"allowed": False},  # not owner, not admin
        phase=2, tags=["ownership_override"],
    ),

    # Phase 3 — deny overrides allow
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"]},
            "resource": {"id": "secret1", "type": "file"},
            "rules": [
                {"role": "editor", "resource_type": "file", "action": "allow"},
                {"role": "editor", "resource_id": "secret1", "action": "deny"},
            ],
        },
        expected={"allowed": False},  # deny overrides allow
        phase=3, tags=["deny_priority"],
    ),
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"]},
            "resource": {"id": "public1", "type": "file"},
            "rules": [
                {"role": "editor", "resource_type": "file", "action": "allow"},
                {"role": "editor", "resource_id": "secret1", "action": "deny"},
            ],
        },
        expected={"allowed": True},  # deny is for different resource
        phase=3, tags=["deny_priority"],
    ),

    # Phase 4 — role hierarchy: admin > editor > viewer
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["admin"]},
            "resource": {"id": "doc1", "type": "file"},
            "rules": [
                {"role": "editor", "resource_type": "file", "action": "allow"},
            ],
            "hierarchy": {"admin": ["editor", "viewer"], "editor": ["viewer"]},
        },
        expected={"allowed": True},  # admin inherits editor permissions
        phase=4, tags=["role_inheritance"],
    ),
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["viewer"]},
            "resource": {"id": "doc1", "type": "file"},
            "rules": [
                {"role": "editor", "resource_type": "file", "action": "allow"},
            ],
            "hierarchy": {"admin": ["editor", "viewer"], "editor": ["viewer"]},
        },
        expected={"allowed": False},  # viewer doesn't inherit editor
        phase=4, tags=["role_inheritance"],
    ),

    # Phase 5 — temporal constraints
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"]},
            "resource": {"id": "doc1", "type": "file"},
            "rules": [
                {"role": "editor", "resource_type": "file", "action": "allow",
                 "valid_from": "2025-01-01", "valid_until": "2025-12-31"},
            ],
            "current_time": "2025-06-15",
        },
        expected={"allowed": True},
        phase=5, tags=["temporal_constraint"],
    ),
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"]},
            "resource": {"id": "doc1", "type": "file"},
            "rules": [
                {"role": "editor", "resource_type": "file", "action": "allow",
                 "valid_from": "2025-01-01", "valid_until": "2025-06-30"},
            ],
            "current_time": "2025-09-15",
        },
        expected={"allowed": False},  # expired
        phase=5, tags=["temporal_constraint"],
    ),

    # Phase 6 — audit trail (enriched output)
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"]},
            "resource": {"id": "doc1", "type": "file"},
            "rules": [
                {"role": "editor", "resource_type": "file", "action": "allow"},
            ],
        },
        expected={"allowed": True, "reason": "role_match", "matched_rule": {"role": "editor", "resource_type": "file", "action": "allow"}},
        phase=6, tags=["audit_trail"],
    ),
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["viewer"]},
            "resource": {"id": "doc1", "type": "file"},
            "rules": [
                {"role": "editor", "resource_type": "file", "action": "allow"},
            ],
        },
        expected={"allowed": False, "reason": "no_matching_rule", "matched_rule": None},
        phase=6, tags=["audit_trail"],
    ),

    # Phase 7 — wildcard matching
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"]},
            "resource": {"id": "files/reports/q1.pdf", "type": "file"},
            "rules": [
                {"role": "editor", "resource_pattern": "files/*", "action": "allow"},
            ],
        },
        expected={"allowed": True, "reason": "role_match", "matched_rule": {"role": "editor", "resource_pattern": "files/*", "action": "allow"}},
        phase=7, tags=["wildcard_matching"],
    ),
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"]},
            "resource": {"id": "images/logo.png", "type": "file"},
            "rules": [
                {"role": "editor", "resource_pattern": "files/*", "action": "allow"},
            ],
        },
        expected={"allowed": False, "reason": "no_matching_rule", "matched_rule": None},
        phase=7, tags=["wildcard_matching"],
    ),

    # Phase 8 — specificity resolution: most-specific wins, deny on tie
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"]},
            "resource": {"id": "files/secret.txt", "type": "file"},
            "rules": [
                {"role": "editor", "resource_pattern": "files/*", "action": "allow"},
                {"role": "editor", "resource_id": "files/secret.txt", "action": "deny"},
            ],
        },
        expected={"allowed": False, "reason": "deny_specific", "matched_rule": {"role": "editor", "resource_id": "files/secret.txt", "action": "deny"}},
        phase=8, tags=["specificity_resolution"],
    ),
    # resource_id (exact) is more specific than resource_pattern (wildcard)
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"]},
            "resource": {"id": "files/public.txt", "type": "file"},
            "rules": [
                {"role": "editor", "resource_pattern": "files/*", "action": "deny"},
                {"role": "editor", "resource_id": "files/public.txt", "action": "allow"},
            ],
        },
        expected={"allowed": True, "reason": "role_match", "matched_rule": {"role": "editor", "resource_id": "files/public.txt", "action": "allow"}},
        phase=8, tags=["specificity_resolution"],
    ),
    # Same specificity: deny wins
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"]},
            "resource": {"id": "files/doc.txt", "type": "file"},
            "rules": [
                {"role": "editor", "resource_pattern": "files/*", "action": "allow"},
                {"role": "editor", "resource_pattern": "files/*", "action": "deny"},
            ],
        },
        expected={"allowed": False, "reason": "deny_priority", "matched_rule": {"role": "editor", "resource_pattern": "files/*", "action": "deny"}},
        phase=8, tags=["specificity_resolution"],
    ),

    # Phase 9 — conditional rules
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"], "department": "engineering"},
            "resource": {"id": "doc1", "type": "file", "department": "engineering"},
            "rules": [
                {"role": "editor", "resource_type": "file", "action": "allow",
                 "condition": "user.department == resource.department"},
            ],
        },
        expected={"allowed": True, "reason": "role_match", "matched_rule": {"role": "editor", "resource_type": "file", "action": "allow", "condition": "user.department == resource.department"}},
        phase=9, tags=["conditional_rules"],
    ),
    TestCase(
        input={
            "user": {"id": "u1", "roles": ["editor"], "department": "marketing"},
            "resource": {"id": "doc1", "type": "file", "department": "engineering"},
            "rules": [
                {"role": "editor", "resource_type": "file", "action": "allow",
                 "condition": "user.department == resource.department"},
            ],
        },
        expected={"allowed": False, "reason": "condition_failed", "matched_rule": None},
        phase=9, tags=["conditional_rules"],
    ),
]
