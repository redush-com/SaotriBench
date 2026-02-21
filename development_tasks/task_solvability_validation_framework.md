# Task Solvability Validation Framework

## Technical Specification

**Date:** 2026-02-22
**Status:** Draft
**Source:** `benchmark_audit/2026-02-21_2_audit.md`, `development_tasks/audit_2_technical_issues.md` (Issues 3, 4, 5)

---

## 1. Problem Statement

### 1.1 Motivation

SaotriBench evaluates LLM agents on hidden requirement discovery through iterative feedback. An audit of the first benchmark run (115 results, 14 models, 12 tasks) revealed a credibility gap:

| Task | Difficulty Label | Completion Rate | Verdict |
|------|-----------------|-----------------|---------|
| task_03_validate_brackets | medium | 92% (12/13) | Reference — well-calibrated |
| task_00_fizzbuzz | easy | 36% (5/14) | Good discriminator |
| task_04_sort_objects | medium | 7% (1/14) | Hard but solvable |
| task_01_transform_list | easy | 0% (0/14) | Suspect |
| task_02_merge_dicts | easy | 0% (0/10) | Suspect |
| task_05_text_processor | medium | 0% (0/14) | Domain knowledge issue |
| task_06_cache_eviction | medium | 0% (0/13) | Difficulty cliff at phase 2 |

When 0/14 models — including Claude Opus 4.6 (the top performer with 62% phase rate) — cannot complete a task labeled "easy", the question is: **is the task broken, or are all models weak?**

Currently there is no systematic way to answer this. The existing `saotri-bench validate` command (`saotri_bench/cli.py:102-217`) only checks structural validity: files load, phases are sequential, evaluator methods exist, tests cover all phases. It does not verify that tasks are actually solvable within their constraints, or that feedback provides enough signal for iterative discovery.

### 1.2 What This Framework Adds

A four-level validation pipeline that mechanically proves (or disproves) each task is solvable, that its feedback is adequate for discovery, and that its step budget provides reasonable margin. This transforms "we think these tasks work" into "we have verified these tasks work."

### 1.3 Design Principles

- **Reuse existing infrastructure.** The framework builds on `BaseEvaluator.evaluate()`, `execute_code()`, and `load_*()` functions. No parallel evaluation engine.
- **No LLM calls.** All validation is deterministic and runs in seconds, suitable for CI.
- **Implementation-aware, not model-based.** The validator uses privileged access to test cases, golden solutions, and expected values — information that models never see during the benchmark. This means the validation measures a **structural property of the task** (is it solvable given its feedback design?), not a property of any particular model. Using an LLM-as-judge would create circular bias where the judging model performs best on its own test.
- **Fully automatic.** No manual review or human overrides. All metrics are computed deterministically from code, test cases, and golden solutions.
- **Non-destructive.** Task files are never modified during validation.
- **Incremental.** Levels 1-3 are useful independently. Level 4 is optional.
- **Provides evidence, not just verdicts.** Reports include raw metrics and per-test-case analysis, not just aggregate scores.

---

## 2. Validation Levels Overview

```
Level 1: Static Solvability     — "Does a correct solution exist for each phase?"
Level 2: Feedback Adequacy      — "Can an agent discover the next solution from feedback?"
Level 3: Budget Adequacy        — "Does the agent have enough attempts?"
Level 4: Empirical Validation   — "Can a mechanical strategy solve it?" (optional)
```

Each level depends on the previous:

```
Level 1  ──►  Level 2  ──►  Level 3
                                │
                                ▼
                           Level 4 (optional)
```

---

## 3. Golden Solutions

### 3.1 Concept

Each task gains a `golden/` subdirectory containing **reference solutions** — one per phase. A golden solution for phase N is a Python file implementing the target function that passes ALL tests through phase N (cumulative).

Golden solutions serve three purposes:
1. **Proof of solvability** — the task is solvable in principle
2. **Phase break verification** — the golden solution for phase N must FAIL on phase N+1 tests (proving phases actually progress)
3. **Feedback generation** — running golden solution N against phase N+1 produces the exact feedback an agent would see at the transition point

### 3.2 File Structure

```
tasks/task_01_transform_list/
  task.yaml
  problem.md
  evaluator.py
  tests.py
  golden/                        # NEW
    phase_0.py                   # Simplest correct solution for phase 0
    phase_1.py                   # Handles phases 0-1
    phase_2.py                   # Handles phases 0-2 (final)
    metadata.yaml                # Step estimates, transition descriptions
```

### 3.3 Golden Solution File Format

Each `phase_N.py` is a standalone Python file containing only the target function. The function name MUST match `TaskConfig.interface.function_name`. Imports MUST be within `TaskConfig.interface.allowed_imports`.

```python
# golden/phase_0.py
"""Golden solution for task_01_transform_list, phase 0.

Handles: Basic doubling of all numbers.
"""


def transform(numbers: list[int]) -> list[int]:
    return [x * 2 for x in numbers]
```

```python
# golden/phase_1.py
"""Golden solution for task_01_transform_list, phase 1.

Handles: Phase 0 + absolute value before doubling for negatives.
"""


def transform(numbers: list[int]) -> list[int]:
    return [abs(x) * 2 for x in numbers]
```

```python
# golden/phase_2.py
"""Golden solution for task_01_transform_list, phase 2.

Handles: Phase 0 + Phase 1 + cap results at 100.
"""


def transform(numbers: list[int]) -> list[int]:
    return [min(abs(x) * 2, 100) for x in numbers]
```

**Constraints enforced during validation:**
- File contains a function matching `interface.function_name`
- No imports outside `interface.allowed_imports`
- Function executes within `execution.timeout_seconds`
- Loaded via `sandbox.execute_code()` (same restrictions as agent code)

### 3.4 Metadata File Format

`golden/metadata.yaml` contains human-annotated data about each phase transition that cannot be derived automatically.

```yaml
task_id: "task_01_transform_list"
author: "benchmark-maintainer"
created: "2026-02-22"

phases:
  - phase_id: 0
    file: "phase_0.py"
    description: "Double all numbers"
    min_discovery_steps: 1
    key_insight: "Basic doubling: x * 2"

  - phase_id: 1
    file: "phase_1.py"
    description: "Handle negatives with abs()"
    min_discovery_steps: 2
    key_insight: "Apply abs() before doubling"
    transition_from: 0
    expected_breaking_scopes: ["negative_handling"]

  - phase_id: 2
    file: "phase_2.py"
    description: "Cap results at 100"
    min_discovery_steps: 1
    key_insight: "min(result, 100)"
    transition_from: 1
    expected_breaking_scopes: ["cap_overflow"]
```

**Field definitions:**

| Field | Type | Description |
|-------|------|-------------|
| `phase_id` | int | Phase number (matches task.yaml) |
| `file` | str | Filename within `golden/` |
| `description` | str | What this phase adds |
| `min_discovery_steps` | int | Minimum attempts a competent agent needs for this phase (1 = trivial, 2 = needs one feedback cycle, 3+ = needs multiple iterations) |
| `key_insight` | str | The core discovery the agent must make |
| `transition_from` | int | Previous phase ID (absent for phase 0) |
| `expected_breaking_scopes` | list[str] | Scope names expected to fail when running the previous golden solution against this phase's tests |

`min_discovery_steps` is a human estimate. It represents the fewest attempts needed assuming the agent correctly interprets feedback. It is used in Level 3 budget analysis.

### 3.5 Security Considerations

Golden solutions are benchmark infrastructure — they must NOT be accessible to agents during benchmark runs. This is already guaranteed by the agent architecture: `agents/bench_runner.py` restricts the agent's file view to workspace files (`problem.md`, `task.json`, `phase.json`, `feedback.json`, `solution.py`). The `golden/` directory is never copied to workspace.

Golden solutions SHOULD be committed to the repository as part of benchmark integrity.

---

## 4. Level 1: Static Solvability Check

### 4.1 Purpose

Verify that a known-correct solution exists for each phase and that phases actually progress (each phase breaks the previous solution).

### 4.2 Algorithm

```
Input: task_dir (Path)
Output: list[GoldenSolutionResult]

Load: task_config, evaluator, test_cases via loader functions
Load: golden solutions from task_dir/golden/

For each phase N in task_config.phases:
    1. Read golden/phase_N.py source code
    2. Load function via sandbox.execute_code(
           code=source,
           function_name=task_config.interface.function_name,
           allowed_imports=task_config.interface.allowed_imports,
           timeout=task_config.execution.timeout_seconds
       )
    3. Run evaluator.evaluate(solution_fn, test_cases, phase=phases[N])
    4. Record: coverage_own_phase, violations (expect: coverage=1.0, violations=[])

    If N < len(phases) - 1:
        5. Run evaluator.evaluate(solution_fn, test_cases, phase=phases[N+1])
        6. Record: coverage_next_phase, violations_next_phase
        7. Expect: coverage < 1.0 and violations non-empty
```

### 4.3 Integration with Existing Code

The entire evaluation pipeline is reused as-is:

- **`loader.load_task(task_dir)`** — returns `TaskConfig` with phases, rules, limits
- **`loader.load_evaluator(task_dir)`** — returns the task's `Evaluator` instance
- **`loader.load_tests(task_dir)`** — returns `TEST_CASES` list
- **`sandbox.execute_code(code, function_name, allowed_imports, timeout)`** — returns callable, same sandbox used for agent solutions
- **`BaseEvaluator.evaluate(solution_fn, test_cases, phase)`** — filters tests by `tc.phase <= phase.id` (line 37 of `evaluator.py`), returns `(violations, coverage)`

Golden solution loading follows the same pattern as `loader.load_tests()` — dynamic file loading via `sandbox.execute_code()` rather than `importlib`, because golden solutions must be sandboxed (validates they don't use disallowed imports).

### 4.4 Pass/Fail Criteria

| Check | Pass | Fail |
|-------|------|------|
| Golden solution exists for phase N | `golden/phase_N.py` file present | File missing |
| Golden passes own phase | `coverage == 1.0` and `violations == []` | Any violations or coverage < 1.0 |
| Golden breaks on next phase | `coverage < 1.0` or `violations != []` | No violations (phase doesn't add difficulty) |
| No execution errors | `execute_code()` succeeds | Syntax error, import violation, timeout |

### 4.5 Failure Implications

- **Golden fails own phase:** Either the golden solution has a bug, or the test cases have a bug. Both must be fixed.
- **Golden does NOT break on next phase:** The phase transition does not actually introduce new difficulty. The phase may be redundant or its test cases may not exercise the new rules.

---

## 5. Level 2: Feedback Adequacy Analysis

### 5.1 Purpose

For each phase transition (N to N+1), determine whether the task structure provides enough information for an agent to discover the required code changes through iterative feedback.

This is the critical level. The audit identified a pattern:
- **Effective feedback** (`divisible_by_7` in task_00): 36% completion.
- **Insufficient feedback** (`negative_handling` in task_01): 0% completion.

### 5.2 Core Principle: Implementation-Aware Analysis

The validator has **privileged access** that the model never gets during the benchmark:

| | Model During Benchmark | Validator |
|---|---|---|
| Sees test cases? | No | Yes — full (input, expected) |
| Sees golden solutions? | No | Yes — knows the correct answer |
| Sees AST diff between phases? | No | Yes — knows exactly what must change |
| Sees actual output of failing code? | No | Yes — runs golden_N on phase N+1 tests |
| Method | Infer from obfuscated feedback | Analyze (input, actual, expected) triples |

This means the validator answers a different question than the model: not "can I solve this?" but **"does the structure of this task admit iterative discovery?"** — a property of the task, not of any model.

### 5.3 Algorithm

```
Input: task_dir, level_1_results (golden solutions + their violations on next phase)
Output: list[FeedbackAdequacyResult]

For each transition N -> N+1:
    1. Load golden_N function via sandbox.execute_code()
    2. Get failing test cases: all tests where tc.phase == N+1
       that golden_N does not pass
    3. For each failing test, compute the triple:
       (input, actual_output, expected_output)
       where actual_output = golden_N(test_case.input)

    4. Compute 5 automatic metrics (see 5.4-5.8):
       A. Failure Pattern Coherence
       B. Transformation Catalog Match
       C. Solution Delta Complexity
       D. Incremental Testability
       E. Coverage Drop Severity

    5. Compute composite solvability_score (see 5.9)
    6. Derive rating: high / medium / low / none
```

### 5.4 Metric A: Failure Pattern Coherence

**Question:** Do all failing tests fail for the **same reason**, or for different reasons?

High coherence means one root cause — one fix needed. Low coherence means the agent must discover multiple things simultaneously.

**Algorithm:**

```
1. For each failing test, compute an error signature:
   - Element-wise comparison of actual vs expected
   - Classify each difference: sign_flip, magnitude_change, type_change,
     missing_element, extra_element, value_substitution, structural_change

2. Group tests by their error signature

3. coherence = 1.0 / number_of_distinct_signatures
   (1 signature = coherence 1.0, 2 signatures = 0.5, etc.)
```

**Example — task_01 transition 0→1:**

```
golden_0 = [x * 2 for x in numbers]

Test: input=[-3, 2]    → actual=[-6, 4]  expected=[6, 4]   → sign_flip at index 0
Test: input=[-1,-2,-3] → actual=[-2,-4,-6] expected=[2,4,6] → sign_flip at all indices
Test: input=[4,-5,6]   → actual=[8,-10,12] expected=[8,10,12] → sign_flip at index 1
Test: input=[-10,10]   → actual=[-20,20]  expected=[20,20]  → sign_flip at index 0

Distinct signatures: 1 (sign_flip on negative inputs)
Coherence: 1.0 / 1 = 1.0 (maximum)
```

**Example — hypothetical bad task with 3 different failure patterns:**

```
Test 1: wrong sign      → signature A
Test 2: wrong magnitude → signature B
Test 3: wrong type      → signature C

Distinct signatures: 3
Coherence: 1.0 / 3 = 0.33 (poor — agent must discover 3 things at once)
```

**Error signature classification:**

```python
def classify_error(actual, expected) -> str:
    """Classify the difference between actual and expected output."""
    if type(actual) != type(expected):
        return "type_change"

    if isinstance(expected, (list, tuple)):
        if len(actual) != len(expected):
            return "length_change"
        diffs = []
        for a, e in zip(actual, expected):
            if a != e:
                diffs.append(classify_element_diff(a, e))
        # Return the dominant diff pattern
        return most_common(diffs) if diffs else "unknown"

    return classify_element_diff(actual, expected)


def classify_element_diff(actual, expected) -> str:
    """Classify difference between two scalar values."""
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        if actual == -expected:
            return "sign_flip"
        if abs(actual) == abs(expected):
            return "sign_flip"
        if expected != 0 and actual / expected == int(actual / expected):
            return "scale_change"
        if actual > expected:
            return "over_value"
        return "under_value"

    if isinstance(actual, str) and isinstance(expected, str):
        if actual.lower() == expected.lower():
            return "case_change"
        if actual.strip() == expected.strip():
            return "whitespace_change"
        return "string_diff"

    return "value_substitution"
```

### 5.5 Metric B: Transformation Catalog Match

**Question:** How many standard Python transformations can explain the observed failures? Fewer matches = more constrained = easier to discover.

A fixed catalog of ~30 common transformations is applied to each failing test's actual output. A transformation "matches" if it converts actual into expected for **all** failing tests.

**Catalog:**

```python
TRANSFORM_CATALOG = [
    # Numeric transforms
    ("abs",             lambda x: abs(x)),
    ("negate",          lambda x: -x),
    ("floor_zero",      lambda x: max(x, 0)),
    ("cap_50",          lambda x: min(x, 50)),
    ("cap_100",         lambda x: min(x, 100)),
    ("cap_255",         lambda x: min(x, 255)),
    ("cap_1000",        lambda x: min(x, 1000)),
    ("double",          lambda x: x * 2),
    ("halve",           lambda x: x // 2),
    ("square",          lambda x: x ** 2),
    ("increment",       lambda x: x + 1),
    ("decrement",       lambda x: x - 1),
    ("modulo_wrap",     lambda x: x % 100),

    # String transforms
    ("lower",           lambda x: x.lower()),
    ("upper",           lambda x: x.upper()),
    ("strip",           lambda x: x.strip()),
    ("title",           lambda x: x.title()),
    ("reverse_str",     lambda x: x[::-1]),

    # Collection transforms
    ("sort_asc",        lambda x: sorted(x)),
    ("sort_desc",       lambda x: sorted(x, reverse=True)),
    ("reverse_list",    lambda x: list(reversed(x))),
    ("unique",          lambda x: list(dict.fromkeys(x))),
    ("flatten",         lambda x: [i for sub in x for i in (sub if isinstance(sub, list) else [sub])]),

    # Type transforms
    ("to_str",          lambda x: str(x)),
    ("to_int",          lambda x: int(x)),
    ("to_list",         lambda x: list(x)),
    ("to_bool",         lambda x: bool(x)),
]
```

**Algorithm:**

```
1. For each failing test, get (actual_element, expected_element) pairs
   - For list outputs: zip element-wise
   - For scalar outputs: single pair
   - For dict outputs: compare values per key

2. For each transformation in CATALOG:
   matched = True
   for each (actual_element, expected_element) in failing_pairs:
       if transform(actual_element) != expected_element:
           matched = False
           break
   if matched: catalog_matches.append(transform_name)

3. catalog_match_count = len(catalog_matches)
```

**Example — task_01 transition 0→1:**

```
Failing pairs: [(-6, 6), (-2, 2), (-4, 4), (-6, 6), (-10, 10), (-20, 20)]

abs(-6)=6 ✓, abs(-2)=2 ✓, abs(-4)=4 ✓, ... → abs MATCHES (all pairs)
negate(-6)=6 ✓, negate(-2)=2 ✓, ... → negate also MATCHES
floor_zero(-6)=0 ≠ 6 → NO
cap_100(-6)=-6 ≠ 6 → NO

catalog_matches = ["abs", "negate"]  → count = 2
```

Note: both `abs` and `negate` match because for negative inputs `abs(x) == -x`. This is expected — the metric measures ambiguity. With 2 matches, the task is still reasonably constrained. With 8+ matches, it's ambiguous.

**Scoring:**

```
catalog_specificity = 1.0 / max(catalog_match_count, 1)

1 match  → specificity = 1.0  (unambiguous)
2 matches → specificity = 0.5
3 matches → specificity = 0.33
0 matches → specificity = 0.0  (transformation not in catalog — domain-specific)
```

`catalog_match_count == 0` is a special case: it means the required transformation is non-standard (e.g., Unicode NFC normalization). This does not necessarily mean the task is broken — it means the task tests domain knowledge rather than feedback-driven discovery. The metric flags it for attention.

### 5.6 Metric C: Solution Delta Complexity

**Question:** How much code must change between golden_N and golden_N+1?

Smaller deltas are easier to discover. A single `abs()` wrapper is simpler than restructuring the entire function.

**Algorithm:**

```python
import ast

def compute_delta_complexity(golden_n_code: str, golden_n1_code: str) -> DeltaComplexity:
    tree_n = ast.parse(golden_n_code)
    tree_n1 = ast.parse(golden_n1_code)

    nodes_n = collect_ast_nodes(tree_n)
    nodes_n1 = collect_ast_nodes(tree_n1)

    added = nodes_n1 - nodes_n
    removed = nodes_n - nodes_n1
    total_delta = len(added) + len(removed)

    # Categorize changes
    categories = categorize_changes(added, removed)
    # e.g., ["added_call:abs", "added_call:min", "changed_literal:100"]

    # Normalize: delta_simplicity is inverse of complexity
    # Scale: 1-3 nodes = simple, 4-8 = moderate, 9+ = complex
    delta_simplicity = max(0.0, 1.0 - (total_delta - 1) / 10.0)

    return DeltaComplexity(
        total_changed_nodes=total_delta,
        categories=categories,
        delta_simplicity=delta_simplicity,
    )
```

**AST node collection** uses a normalized representation to enable meaningful comparison:

```python
def collect_ast_nodes(tree: ast.AST) -> set[str]:
    """Collect normalized string representations of all AST nodes."""
    nodes = set()
    for node in ast.walk(tree):
        # Skip module/function wrapper nodes
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.arguments)):
            continue
        nodes.add(ast.dump(node, annotate_fields=True))
    return nodes
```

**Example — task_01 transition 0→1:**

```
golden_0: return [x * 2 for x in numbers]
golden_1: return [abs(x) * 2 for x in numbers]

AST diff:
  Added: Call(func=Name(id='abs'), args=[Name(id='x')])
  Removed: Name(id='x')  (as direct argument to BinOp)
  Total: 2 nodes changed
  Categories: ["added_call:abs"]
  delta_simplicity = max(0.0, 1.0 - (2-1)/10.0) = 0.9
```

**Example — task_03 transition 2→3:**

```
golden_2: return True/False
golden_3: raise ValueError(f"...position {pos}...") for invalid inputs

AST diff: ~8 nodes (new If, Raise, Call, JoinedStr, etc.)
  delta_simplicity = max(0.0, 1.0 - (8-1)/10.0) = 0.3
  But this is compensated by high structural signals (new rule with explicit description)
```

### 5.7 Metric D: Incremental Testability

**Question:** If the agent applies a **partial** fix, does coverage improve? Tasks that support incremental progress are more solvable than "all-or-nothing" tasks.

**Algorithm:**

```
1. Parse the AST diff between golden_N and golden_N+1
2. Decompose into atomic changes (each added/modified node independently)
3. For each atomic change:
   a. Apply ONLY this change to golden_N code
   b. Execute via sandbox
   c. Run evaluator against phase N+1 tests
   d. Record coverage improvement vs golden_N's coverage on phase N+1

4. incremental_score = fraction of atomic changes that improve coverage
```

**Example — task_01 transition 0→1:**

```
golden_0: return [x * 2 for x in numbers]
golden_1: return [abs(x) * 2 for x in numbers]

Only 1 atomic change: wrap x in abs()
Applying it: coverage goes from 0.50 to 1.00
incremental_score = 1.0 (the single change fully fixes it)
```

**Example — hypothetical "all-or-nothing" task:**

```
golden_N: return sorted(items)
golden_N+1: return sorted(items, key=lambda x: (x.priority, -x.timestamp, x.name))

Atomic changes:
  1. Add key= parameter → syntax error without lambda → no improvement
  2. Add lambda body → depends on change 1 → no improvement alone

incremental_score = 0.0 (all changes must be applied together)
```

**Practical consideration:** AST-level atomic decomposition may not always produce valid Python when changes are interdependent. When a partial application causes a syntax error or execution error, that change scores 0 (no improvement). This is intentional — it captures the "all-or-nothing" nature of some transitions.

### 5.8 Metric E: Coverage Drop Severity

**Question:** How clear is the signal that something broke? A large coverage drop is a strong signal; a tiny drop might be lost in noise.

**Algorithm:**

```
coverage_drop = coverage_at_phase_N - coverage_at_phase_N+1
(where both are measured using golden_N solution)

signal_strength = min(coverage_drop / 0.3, 1.0)
```

Normalization: a drop of 0.30 or more = maximum signal (1.0). Smaller drops scale linearly.

**Example — task_01 transition 0→1:**

```
golden_0 on phase 0 tests: coverage = 1.0
golden_0 on phase 1 tests: coverage = 0.50 (4 of 8 tests fail)
coverage_drop = 0.50
signal_strength = min(0.50 / 0.30, 1.0) = 1.0 (maximum)
```

### 5.9 Composite Solvability Score

The five metrics combine into a single score per transition:

```
solvability_score = (
    w_coherence     * coherence            +   # 0..1, higher = one root cause
    w_catalog       * catalog_specificity  +   # 0..1, higher = fewer matching transforms
    w_delta         * delta_simplicity     +   # 0..1, higher = smaller code change
    w_incremental   * incremental_score    +   # 0..1, higher = supports partial progress
    w_signal        * signal_strength          # 0..1, higher = clear coverage drop
)
```

**Default weights:**

| Weight | Value | Rationale |
|--------|-------|-----------|
| `w_coherence` | 0.25 | Most important: single root cause is prerequisite for discovery |
| `w_catalog` | 0.30 | Key metric: if the transformation is standard and unambiguous, the task is solvable |
| `w_delta` | 0.15 | Smaller changes are easier but this is secondary to discoverability |
| `w_incremental` | 0.15 | Partial progress support helps but isn't strictly required |
| `w_signal` | 0.15 | Clear signal helps but a weak signal with good coherence is still solvable |

Weights sum to 1.0. They are calibrated against known outcomes:
- task_03 transitions (92% completion) should score >= 0.7
- task_00 transition 0→1 (36% completion) should score 0.4-0.7
- task_01 transitions (0% completion) should score < 0.4

**Rating derivation:**

| Score Range | Rating | Meaning |
|-------------|--------|---------|
| >= 0.70 | **high** | Task transition is clearly solvable through iterative feedback |
| 0.40 — 0.69 | **medium** | Solvable but requires multiple hypotheses; some models will struggle |
| 0.15 — 0.39 | **low** | Feedback structure is weak; most models will exhaust budget |
| < 0.15 | **none** | Feedback provides no useful signal for this transition |

### 5.10 Structural Signal Bonus

In addition to the 5 core metrics, the framework checks structural signals from the feedback protocol itself. These are additive bonuses to the composite score:

| Signal | Bonus | Condition |
|--------|-------|-----------|
| New rule_id in phase N+1 | +0.10 | A rule appears in phase N+1 that was not in phase N |
| Specific rule description | +0.05 | New rule's description is > 20 chars and contains a verb (action hint) |
| Transparent scope | +0.05 | Scope is in the non-obfuscated set (`error`, `direct`, `ordering`, etc.) |

The bonus is capped: `final_score = min(solvability_score + bonus, 1.0)`

This captures cases where the agent gets strong guidance from the phase.json rules list, independent of the test case analysis. For example, task_03 transition 2→3 introduces rule `correct_error` with description "Raises ValueError with position for invalid input" — this is a +0.15 bonus that elevates the score regardless of catalog matching.

### 5.11 Worked Examples

**task_01 transition 0→1 (expected: LOW)**

```
Failing tests: 4
Error signatures: all "sign_flip" → coherence = 1.0
Catalog matches: ["abs", "negate"] → specificity = 0.5
AST delta: 2 nodes → simplicity = 0.9
Incremental: 1 atomic change, fixes all → incremental = 1.0
Coverage drop: 0.50 → signal = 1.0
Structural bonus: no new rules → +0.00

score = 0.25*1.0 + 0.30*0.5 + 0.15*0.9 + 0.15*1.0 + 0.15*1.0 = 0.685

Wait — this scores MEDIUM, not LOW. Why?
Because from the implementation's perspective, the task IS solvable — abs() clearly
fixes it, and the pattern is unambiguous from (input, actual, expected) triples.

The problem is not the task structure. The problem is that the AGENT never sees these
triples. The agent sees obfuscated feedback: "correct_output/scope_a1b2c3 (x4)".

This is correct behavior: Level 2 measures whether the task structure ADMITS discovery.
Score 0.685 means: "If the agent had reasonable feedback, this would be solvable."
The gap between this score and the actual 0% completion rate proves the feedback
delivery mechanism (obfuscation) is the bottleneck, not the task design.
```

This reveals an important distinction. The solvability score should be computed in **two modes**:

**Mode 1: Structural solvability** (with implementation knowledge)
- Uses (input, actual, expected) triples
- Answers: "Is the task structurally solvable?"
- task_01 scores ~0.69 → YES, it's solvable

**Mode 2: Agent-visible solvability** (with only what the agent sees)
- Replaces catalog matching with scope analysis (obfuscated)
- Replaces test triple analysis with violation-only analysis
- Answers: "Can an agent solve this given the feedback it receives?"
- task_01 scores much lower because the agent sees none of the diagnostic triples

The **delta** between Mode 1 and Mode 2 quantifies the **feedback gap**: how much information is lost between what exists in the tests and what reaches the agent.

```
feedback_gap = structural_solvability - agent_visible_solvability

task_01: gap = 0.69 - 0.15 = 0.54 → LARGE GAP → feedback needs enrichment
task_03: gap = 0.85 - 0.80 = 0.05 → SMALL GAP → feedback works well
task_00: gap = 0.75 - 0.50 = 0.25 → MODERATE GAP → some info lost but manageable
```

### 5.12 Mode 2: Agent-Visible Solvability

For agent-visible scoring, the 5 metrics are modified to use only information available to the agent:

| Metric | Mode 1 (Structural) | Mode 2 (Agent-Visible) |
|--------|---------------------|------------------------|
| **A. Coherence** | From (input, actual, expected) triples | From violation scope grouping: are all violations in one scope or spread across many? |
| **B. Catalog** | Transform catalog on actual→expected | Scope name analysis: is the obfuscated scope in the transparent set? Does the rule_id have a specific description? |
| **C. Delta** | AST diff (unchanged — same golden solutions) | Same as Mode 1 |
| **D. Incremental** | Partial fix coverage (unchanged) | Same as Mode 1 |
| **E. Signal** | Coverage drop (unchanged) | Same as Mode 1 |

**Agent-visible replacements for A and B:**

```python
def agent_coherence(violations: list[Violation]) -> float:
    """How focused is the failure signal the agent sees?"""
    distinct_scopes = len(set(v.scope for v in violations))
    distinct_rules = len(set(v.rule_id for v in violations))
    # Agent sees fewer distinct categories → easier to focus
    return 1.0 / max(distinct_scopes * distinct_rules, 1)


def agent_catalog_proxy(violations: list[Violation], phase_n: Phase, phase_n1: Phase) -> float:
    """How much guidance does the agent get from feedback structure?"""
    score = 0.0

    # New rule_id introduced?
    old_rules = {r.id for r in phase_n.rules}
    new_rules = {r.id for r in phase_n1.rules} - old_rules
    if new_rules:
        score += 0.4  # New rule is a strong signal

    # Are scopes in the transparent set?
    transparent = {"error", "unknown", "consistency", "direct", "ordering", "nested"}
    for v in violations:
        if v.scope in transparent:
            score += 0.2
            break

    # Rule descriptions specificity (length + verb presence)
    for rule in phase_n1.rules:
        if rule.id in new_rules and len(rule.description) > 20:
            score += 0.3
            break

    return min(score, 1.0)
```

### 5.13 Final Output Per Transition

Each transition produces:

```
TransitionAnalysis:
  from_phase: 0
  to_phase: 1
  failing_tests: 4
  error_signatures: ["sign_flip"]

  structural_solvability: 0.69    # Mode 1
    coherence: 1.0
    catalog_specificity: 0.5 (matches: abs, negate)
    delta_simplicity: 0.9
    incremental_score: 1.0
    signal_strength: 1.0
    structural_bonus: 0.0

  agent_visible_solvability: 0.15  # Mode 2
    agent_coherence: 1.0     (1 scope)
    agent_catalog_proxy: 0.0 (no new rules, scope obfuscated)
    delta_simplicity: 0.9    (same)
    incremental_score: 1.0   (same)
    signal_strength: 1.0     (same)
    structural_bonus: 0.0

  feedback_gap: 0.54              # Mode 1 - Mode 2
  rating: LOW                     # Based on agent_visible_solvability
  structural_rating: MEDIUM       # Based on structural_solvability
```

### 5.14 Pass/Fail Criteria

| Check | Pass | Fail |
|-------|------|------|
| All transitions: agent_visible >= 0.70 | Feedback is adequate | — |
| Any transition: agent_visible 0.40-0.69 | — | Warning: some models will struggle |
| Any transition: agent_visible < 0.40 | — | Feedback insufficient |
| Any transition: feedback_gap > 0.30 | — | Warning: feedback delivery loses significant information |
| Any transition: structural < 0.40 | — | Task itself may be broken (not just feedback) |

---

## 6. Level 3: Budget Adequacy Analysis

### 6.1 Purpose

Verify that `max_attempts_per_phase` and `max_total_attempts` provide enough room for iterative discovery, accounting for feedback quality.

### 6.2 Algorithm

```
Input: task_config, metadata.yaml, level_2_results
Output: BudgetAdequacyResult

For each transition N -> N+1:
    1. Get base min_discovery_steps from metadata.yaml
       (default: 2 if metadata absent — one attempt to see failure, one to fix)

    2. Get agent_visible_solvability from Level 2 results

    3. Derive adjustment multiplier from solvability score:
       multiplier = interpolate(agent_visible_solvability)

    4. adjusted_min = base_min * multiplier

    5. Compute per-phase buffer:
       buffer_ratio = max_attempts_per_phase / adjusted_min
       adequate = buffer_ratio >= 2.0

Compute total budget:
    total_adjusted_min = sum(adjusted_min for all transitions) + len(phases)
    (the +len(phases) accounts for 1 "pass" attempt per phase)
    total_buffer = max_total_attempts / total_adjusted_min
    adequate = total_buffer >= 1.5
```

### 6.3 Adjustment Multipliers

The multiplier is derived from the Level 2 `agent_visible_solvability` score:

| Agent-Visible Score | Rating | Multiplier | Rationale |
|--------------------|--------|-----------|-----------|
| >= 0.70 | high | 1.0x | Agent can fix in minimum steps |
| 0.40 — 0.69 | medium | 1.5x | Agent may need extra attempts to disambiguate |
| 0.15 — 0.39 | low | 3.0x | Agent must try multiple hypotheses |
| < 0.15 | none | 5.0x | Agent is essentially brute-forcing |

Alternatively, as a continuous function:

```python
def score_to_multiplier(agent_visible_score: float) -> float:
    """Convert solvability score to budget multiplier. Lower score = higher multiplier."""
    if agent_visible_score >= 0.70:
        return 1.0
    elif agent_visible_score >= 0.40:
        # Linear interpolation: 0.70 → 1.0x, 0.40 → 1.5x
        return 1.0 + (0.70 - agent_visible_score) / 0.30 * 0.5
    elif agent_visible_score >= 0.15:
        # Linear interpolation: 0.40 → 1.5x, 0.15 → 3.0x
        return 1.5 + (0.40 - agent_visible_score) / 0.25 * 1.5
    else:
        # Linear interpolation: 0.15 → 3.0x, 0.0 → 5.0x
        return 3.0 + (0.15 - agent_visible_score) / 0.15 * 2.0
```

### 6.4 Example: task_01_transform_list

```
Phase 0: min_steps=1, agent_visible=N/A (first phase), adjusted=1
Phase 0->1: min_steps=2, agent_visible=0.15 (LOW), multiplier=3.0x, adjusted=6
Phase 1->2: min_steps=1, agent_visible=0.18 (LOW), multiplier=2.7x, adjusted=2.7

Per-phase:
  Phase 1 budget: max_attempts_per_phase=5, adjusted_min=6.0, buffer=0.83x  FAIL
  Phase 2 budget: max_attempts_per_phase=5, adjusted_min=2.7, buffer=1.85x  WARN

Total:
  total_adjusted_min = 1 + 6.0 + 2.7 + 3 (pass attempts) = 12.7
  max_total_attempts = 15
  buffer = 1.18x  WARN
```

This analysis mechanically confirms the audit's concern: task_01's budget is insufficient given the low agent-visible solvability.

### 6.5 Example: task_03_validate_brackets

```
Phase 0: min_steps=1, adjusted=1
Phase 0->1: min_steps=1, agent_visible=0.75 (HIGH), multiplier=1.0x, adjusted=1.0
Phase 1->2: min_steps=1, agent_visible=0.60 (MEDIUM), multiplier=1.2x, adjusted=1.2
Phase 2->3: min_steps=2, agent_visible=0.80 (HIGH), multiplier=1.0x, adjusted=2.0
Phase 3->4: min_steps=1, agent_visible=0.55 (MEDIUM), multiplier=1.3x, adjusted=1.3

Per-phase: all budgets have buffer >= 2.0x  OK

Total:
  total_adjusted_min = 1 + 1.0 + 1.2 + 2.0 + 1.3 + 5 = 11.5
  max_total_attempts = 25
  buffer = 2.17x  OK
```

### 6.6 Pass/Fail Criteria

| Check | Pass | Fail |
|-------|------|------|
| All per-phase buffers >= 2.0x | Adequate | — |
| Any per-phase buffer < 1.5x | — | Budget too tight (warning) |
| Any per-phase buffer < 1.0x | — | Budget insufficient (error) |
| Total buffer >= 1.5x | Adequate | — |
| Total buffer < 1.0x | — | Total budget insufficient (error) |

---

## 7. Level 4: Empirical Validation (Optional)

### 7.1 Purpose

Run deterministic strategy scripts (no LLMs) against tasks. If no strategy can solve the task, it provides strong evidence the task is broken. If at least one strategy succeeds, the task is empirically validated.

### 7.2 Strategy Interface

```python
class Strategy(ABC):
    """Deterministic strategy for solving a task."""

    @abstractmethod
    def next_solution(
        self,
        current_code: str,
        feedback: Feedback,
        task_config: TaskConfig,
        phase: Phase,
    ) -> str:
        """Given the current code and feedback, produce the next solution attempt.

        Returns: Python source code string containing the target function.
        """
```

### 7.3 Strategies

**Strategy 1: GoldenGuidedStrategy**

The simplest strategy. After each failure, peek at the golden solution diff and apply it incrementally. This strategy always succeeds (by construction) but measures the minimum number of steps needed — useful for calibrating `min_discovery_steps`.

```
Algorithm:
    1. Start with golden/phase_0.py
    2. On phase transition to N+1:
       a. Read golden/phase_{N+1}.py
       b. Submit it as the next solution
    3. Should complete in exactly len(phases) attempts (1 per phase)
```

**Strategy 2: ScopeKeywordStrategy**

Maps scope names to common code transformations using a lookup table. Simulates what a strong model might infer from unobfuscated scope names.

```
Lookup table:
    "negative_handling" -> try: abs(x), then: max(x, 0), then: -x if x < 0
    "cap_overflow"      -> try: min(result, 100), then: min(result, 1000)
    "divisible_by_7"    -> try: add 7 divisor check
    "ttl_expiry"        -> try: add timestamp-based expiry
    ...

Algorithm:
    1. Start with a naive solution matching the problem signature
    2. On each violation, look up the scope in the table
    3. Apply the first untried transformation for that scope
    4. If no match in table, skip (strategy cannot solve)
```

This strategy tests whether the scope names are informative enough — if even a deterministic keyword matcher can solve the task, the feedback is adequate.

**Strategy 3: BruteForcePatternStrategy**

The most aggressive strategy. For each violation, tries a fixed set of common Python patterns (abs, min, max, type checking, exception handling) applied to the current solution. Tests whether the solution space is small enough to enumerate.

### 7.4 Empirical Runner

The empirical runner uses the evaluator directly (no workspace, no file I/O):

```
Algorithm:
    current_code = ""  # empty or stub
    phase_idx = 0

    for attempt in range(max_total_attempts):
        phase = task_config.phases[phase_idx]

        # Execute and evaluate
        solution_fn = sandbox.execute_code(current_code, function_name, ...)
        violations, coverage = evaluator.evaluate(solution_fn, test_cases, phase)

        # Build feedback
        feedback = build_feedback(violations, coverage, phase, attempt)

        if coverage == 1.0 and not violations:
            # Phase passed
            phase_idx += 1
            if phase_idx >= len(phases):
                return StrategyResult(success=True, ...)
            continue

        # Ask strategy for next solution
        current_code = strategy.next_solution(current_code, feedback, task_config, phase)

    return StrategyResult(success=False, stuck_at_phase=phase_idx, ...)
```

### 7.5 Pass/Fail Criteria

| Check | Pass | Fail |
|-------|------|------|
| At least one strategy completes all phases | Empirically validated | — |
| GoldenGuidedStrategy completes in N steps (N = phase count) | Evaluation infrastructure is correct | Evaluator or test bug |
| ScopeKeywordStrategy succeeds | Feedback scopes are informative | Scopes may need enrichment |
| No strategy succeeds | — | Task likely needs redesign |

---

## 8. Verdict Logic

The final verdict for each task follows this precedence:

```
 1. If no golden/ directory exists:                         → NO_GOLDEN
 2. If any golden solution is missing:                      → NO_GOLDEN
 3. If any golden fails its own phase:                      → LIKELY_BROKEN
 4. If any golden does NOT break on next phase:             → LIKELY_BROKEN
 5. If any transition structural_solvability < 0.40:        → STRUCTURALLY_BROKEN
 6. If any transition agent_visible_solvability < 0.15:     → FEEDBACK_INSUFFICIENT
 7. If any transition agent_visible_solvability < 0.40:     → FEEDBACK_INSUFFICIENT
 8. If any per-phase budget ratio < 1.0:                    → BUDGET_TOO_TIGHT
 9. If total budget ratio < 1.0:                            → BUDGET_TOO_TIGHT
10. Otherwise:                                              → SOLVABLE
```

Verdict `STRUCTURALLY_BROKEN` (step 5) is distinct from `FEEDBACK_INSUFFICIENT` (steps 6-7): it means the task itself is poorly designed (not just the feedback delivery). A structural score < 0.40 indicates that even with full knowledge of test cases, the transition is complex and ambiguous.

**Additional flags** (non-blocking):
- `FEEDBACK_GAP_WARN`: Any transition with `feedback_gap > 0.30` (significant information loss in feedback delivery)
- `BUDGET_WARN`: Any per-phase buffer between 1.0x and 2.0x
- `DOMAIN_KNOWLEDGE`: Any transition with `catalog_match_count == 0` (transformation not in standard catalog — task may test domain expertise rather than feedback literacy)

---

## 9. Data Model

### 9.1 Report Dataclasses

New dataclasses for the validation report. These should live in a new module `saotri_bench/solvability.py` to keep separation from the core `models.py`.

```python
@dataclass
class GoldenSolutionResult:
    """Result of validating a single golden solution."""
    phase_id: int
    golden_file: str
    passes_own_phase: bool
    breaks_on_next_phase: bool | None    # None for last phase
    coverage_own_phase: float
    coverage_next_phase: float | None
    violations_next_phase: list[dict] | None   # Serialized Violation dicts
    error: str | None


@dataclass
class FailingTestTriple:
    """A single failing test case with its diagnostic triple."""
    test_input: Any
    actual_output: Any
    expected_output: Any
    error_signature: str           # e.g., "sign_flip", "over_value", "type_change"
    tags: list[str]


@dataclass
class DeltaComplexity:
    """AST diff analysis between two golden solutions."""
    total_changed_nodes: int
    categories: list[str]          # e.g., ["added_call:abs", "changed_literal:100"]
    delta_simplicity: float        # 0..1, higher = simpler change


@dataclass
class FeedbackAdequacyResult:
    """Result of analyzing feedback quality for a phase transition."""
    from_phase: int
    to_phase: int

    # Raw data
    failing_tests: list[FailingTestTriple]
    violations: list[dict]                     # Serialized Violation dicts
    obfuscated_violations: list[dict]          # What agent sees after MD5 obfuscation

    # Metric A: Failure Pattern Coherence
    error_signatures: list[str]                # Distinct failure patterns
    coherence: float                           # 1/distinct_patterns, 0..1

    # Metric B: Transformation Catalog Match
    catalog_matches: list[str]                 # Names of matching transforms
    catalog_match_count: int
    catalog_specificity: float                 # 1/match_count, 0..1

    # Metric C: Solution Delta Complexity
    delta: DeltaComplexity

    # Metric D: Incremental Testability
    incremental_score: float                   # Fraction of atomic changes that help

    # Metric E: Coverage Drop Severity
    coverage_drop: float
    signal_strength: float                     # min(drop/0.3, 1.0)

    # Structural bonus
    new_rule_ids: list[str]
    structural_bonus: float

    # Composite scores
    structural_solvability: float              # Mode 1: with implementation knowledge
    agent_visible_solvability: float           # Mode 2: with only agent-visible info
    feedback_gap: float                        # Mode 1 - Mode 2

    # Derived rating
    structural_rating: str                     # "high" | "medium" | "low" | "none"
    agent_rating: str                          # "high" | "medium" | "low" | "none"


@dataclass
class BudgetPhaseResult:
    """Budget analysis for a single phase transition."""
    from_phase: int
    to_phase: int
    base_min_steps: int
    agent_visible_score: float                 # From Level 2
    feedback_multiplier: float                 # Derived from agent_visible_score
    adjusted_min_steps: float
    budget: int                                # max_attempts_per_phase
    buffer_ratio: float
    adequate: bool


@dataclass
class BudgetAdequacyResult:
    """Budget analysis for the entire task."""
    total_phases: int
    per_phase: list[BudgetPhaseResult]
    total_adjusted_min: float
    max_total_attempts: int
    total_buffer_ratio: float
    adequate: bool


@dataclass
class StrategyResult:
    """Result of running one strategy against a task."""
    strategy_name: str
    phases_completed: int
    total_attempts: int
    stuck_at_phase: int | None
    final_coverage: float
    success: bool


@dataclass
class EmpiricalValidationResult:
    """Result of running all strategies."""
    strategies_run: list[StrategyResult]
    any_strategy_solved: bool
    best_strategy: str | None
    best_phases_completed: int


@dataclass
class TaskSolvabilityReport:
    """Complete solvability report for a single task."""
    task_id: str
    task_name: str
    difficulty: str
    total_phases: int
    timestamp: str

    # Level 1
    golden_solutions_exist: bool
    golden_results: list[GoldenSolutionResult]
    static_solvability: bool

    # Level 2
    feedback_results: list[FeedbackAdequacyResult]
    feedback_adequate: bool                    # All agent_visible >= 0.40

    # Level 3
    budget_result: BudgetAdequacyResult
    budget_adequate: bool

    # Level 4 (optional)
    empirical_result: EmpiricalValidationResult | None

    # Verdict
    verdict: str
    flags: list[str]
    issues: list[str]

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        ...
```

### 9.2 Aggregate Report

```python
@dataclass
class AggregateValidationReport:
    """Solvability report across all tasks."""
    timestamp: str
    tasks_validated: int
    summary: dict[str, int]        # verdict -> count
    task_reports: list[TaskSolvabilityReport]

    def to_dict(self) -> dict:
        ...
```

---

## 10. CLI Interface

### 10.1 New Subcommand

Extend `saotri_bench/cli.py` with a `validate-solvability` subcommand:

```
saotri-bench validate-solvability --task <path>              # Single task
saotri-bench validate-solvability --all --tasks-dir ./tasks   # All tasks
saotri-bench validate-solvability --task <path> --level 2     # Up to level 2 only
saotri-bench validate-solvability --task <path> --json        # JSON output
saotri-bench validate-solvability --task <path> --output report.json
saotri-bench validate-solvability --task <path> --create-golden  # Scaffold stubs
```

### 10.2 Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--task`, `-t` | path | — | Path to a specific task directory |
| `--all` | flag | false | Validate all tasks |
| `--tasks-dir`, `-d` | path | `./tasks` | Tasks directory (with `--all`) |
| `--level`, `-l` | 1-4 | 3 | Maximum validation level |
| `--json`, `-j` | flag | false | JSON-only output |
| `--output`, `-o` | path | stdout | Write report to file |
| `--create-golden` | flag | false | Create `golden/` stub files |

### 10.3 Human-Readable Output Format

```
=== Solvability Validation: task_01_transform_list ===
Task: Transform List (easy, 3 phases)

--- Level 1: Static Solvability ---
  Phase 0: golden/phase_0.py ... PASS (coverage=100%)
    Breaks on phase 1? YES (coverage=50.0%, scopes: negative_handling)
  Phase 1: golden/phase_1.py ... PASS (coverage=100%)
    Breaks on phase 2? YES (coverage=75.0%, scopes: cap_overflow)
  Phase 2: golden/phase_2.py ... PASS (coverage=100%)
  Result: VERIFIED

--- Level 2: Feedback Adequacy ---
  Transition 0 -> 1:
    Failing tests: 4 | Error patterns: 1 (sign_flip)
    Catalog matches: abs, negate (2 matches)
    AST delta: 2 nodes (added_call:abs) | Incremental: 1.0
    Coverage drop: 0.50 | Signal: 1.0

    Structural solvability:    0.69 (MEDIUM) — task is structurally sound
    Agent-visible solvability: 0.15 (LOW)    — agent sees only scope_a1b2c3
    Feedback gap:              0.54          — feedback loses 54% of available info

  Transition 1 -> 2:
    Failing tests: 4 | Error patterns: 1 (over_value)
    Catalog matches: cap_100 (1 match)
    AST delta: 3 nodes (added_call:min, added_literal:100) | Incremental: 0.5
    Coverage drop: 0.33 | Signal: 1.0

    Structural solvability:    0.78 (HIGH)   — unambiguous from test triples
    Agent-visible solvability: 0.22 (LOW)    — cap value (100) not in feedback
    Feedback gap:              0.56          — feedback loses 56% of available info

  Result: FEEDBACK_INSUFFICIENT
    Both transitions: agent-visible < 0.40
    Both transitions: feedback_gap > 0.30

--- Level 3: Budget Adequacy ---
  Phase 0->1: min=2, agent_vis=0.15, mult=3.0x, adjusted=6.0, budget=5  FAIL (0.8x)
  Phase 1->2: min=1, agent_vis=0.22, mult=2.7x, adjusted=2.7, budget=5  WARN (1.9x)
  Total: adjusted_min=12.7, budget=15  WARN (1.2x)
  Result: TIGHT (1 phase below 1.0x buffer)

=== VERDICT: FEEDBACK_INSUFFICIENT ===
Issues:
  1. Transition 0->1: agent-visible=0.15 (LOW). Structural=0.69 (MEDIUM).
     Gap=0.54 — task IS solvable but feedback delivery loses critical info.
     Agent sees "scope_a1b2c3" instead of (input=[-3,2], actual=[-6,4], expected=[6,4]).
  2. Transition 1->2: agent-visible=0.22 (LOW). Structural=0.78 (HIGH).
     Gap=0.56 — cap threshold value (100) exists in tests but never reaches agent.
  3. Phase 1 budget (5 attempts) below adjusted minimum (6.0) for LOW feedback.
Flags:
  - FEEDBACK_GAP_WARN: Both transitions lose >30% of structural information.
```

### 10.4 --create-golden Output

When `--create-golden` is passed and `golden/` does not exist:

```
$ saotri-bench validate-solvability --task tasks/task_01_transform_list --create-golden

Created golden solution stubs:
  tasks/task_01_transform_list/golden/phase_0.py  (stub)
  tasks/task_01_transform_list/golden/phase_1.py  (stub)
  tasks/task_01_transform_list/golden/phase_2.py  (stub)
  tasks/task_01_transform_list/golden/metadata.yaml  (template)

Next steps:
  1. Implement each golden/phase_N.py with the correct solution
  2. Fill in metadata.yaml with min_discovery_steps and key_insight
  3. Run: saotri-bench validate-solvability --task tasks/task_01_transform_list
```

Each stub file:

```python
"""Golden solution for task_01_transform_list, phase 0.

Phase description: Basic transformation
Rules: correct_output

TODO: Implement the correct solution that passes all tests through phase 0.
"""


def transform(numbers: list[int]) -> list[int]:
    raise NotImplementedError("Golden solution not yet implemented")
```

---

## 11. Implementation Architecture

### 11.1 New Module: `saotri_bench/solvability.py`

```python
"""Task solvability validation for Saotri Bench."""

import ast
import copy
import hashlib
from pathlib import Path
from typing import Any, Callable

from .loader import load_task, load_evaluator, load_tests
from .sandbox import execute_code
from .models import TaskConfig, Phase, TestCase, Violation

# --- Transformation Catalog ---

TRANSFORM_CATALOG: list[tuple[str, Callable]] = [
    # Numeric
    ("abs",         lambda x: abs(x)),
    ("negate",      lambda x: -x),
    ("floor_zero",  lambda x: max(x, 0)),
    ("cap_100",     lambda x: min(x, 100)),
    ("cap_255",     lambda x: min(x, 255)),
    ("cap_1000",    lambda x: min(x, 1000)),
    ("double",      lambda x: x * 2),
    ("halve",       lambda x: x // 2),
    ("increment",   lambda x: x + 1),
    ("decrement",   lambda x: x - 1),
    # String
    ("lower",       lambda x: x.lower()),
    ("upper",       lambda x: x.upper()),
    ("strip",       lambda x: x.strip()),
    ("reverse_str", lambda x: x[::-1]),
    # Collection
    ("sort_asc",    lambda x: sorted(x)),
    ("sort_desc",   lambda x: sorted(x, reverse=True)),
    ("reverse_list",lambda x: list(reversed(x))),
    ("unique",      lambda x: list(dict.fromkeys(x))),
    # Type
    ("to_str",      lambda x: str(x)),
    ("to_int",      lambda x: int(x)),
    ("to_list",     lambda x: list(x)),
]


class SolvabilityValidator:
    """Validates that a benchmark task is solvable within its constraints."""

    def __init__(self, task_dir: Path):
        self.task_dir = Path(task_dir)
        self.golden_dir = self.task_dir / "golden"

        self.task_config = load_task(self.task_dir)
        self.evaluator = load_evaluator(self.task_dir)
        self.test_cases = load_tests(self.task_dir)

        self.golden_solutions: dict[int, str] = {}    # phase_id -> source code
        self.golden_fns: dict[int, Callable] = {}      # phase_id -> loaded function
        self.golden_metadata: dict | None = None

    # --- Loading ---

    def has_golden_solutions(self) -> bool: ...
    def load_golden_solutions(self) -> bool: ...
    def load_golden_metadata(self) -> dict | None: ...

    # --- Level 1 ---

    def validate_level_1(self) -> list[GoldenSolutionResult]: ...

    # --- Level 2: Core metrics ---

    def validate_level_2(self, l1_results: list[GoldenSolutionResult]) -> list[FeedbackAdequacyResult]:
        """Level 2: Compute all 5 metrics + dual-mode solvability for each transition."""
        ...

    def _compute_failing_triples(
        self, golden_fn: Callable, phase_n1: Phase
    ) -> list[FailingTestTriple]:
        """Run golden_N on phase N+1 tests, collect (input, actual, expected) triples."""
        results = []
        relevant_tests = [tc for tc in self.test_cases if tc.phase <= phase_n1.id]
        for tc in relevant_tests:
            input_copy = copy.deepcopy(tc.input)
            try:
                actual = golden_fn(input_copy)
            except Exception as e:
                actual = f"<exception: {type(e).__name__}: {e}>"
            if actual != tc.expected:
                sig = classify_error(actual, tc.expected)
                results.append(FailingTestTriple(
                    test_input=tc.input,
                    actual_output=actual,
                    expected_output=tc.expected,
                    error_signature=sig,
                    tags=tc.tags,
                ))
        return results

    def _metric_coherence(self, triples: list[FailingTestTriple]) -> float:
        """Metric A: Failure pattern coherence."""
        if not triples:
            return 1.0
        distinct = len(set(t.error_signature for t in triples))
        return 1.0 / distinct

    def _metric_catalog(self, triples: list[FailingTestTriple]) -> tuple[list[str], float]:
        """Metric B: Transformation catalog match. Returns (matching_names, specificity)."""
        ...

    def _metric_delta(self, golden_n_code: str, golden_n1_code: str) -> DeltaComplexity:
        """Metric C: AST diff complexity."""
        ...

    def _metric_incremental(
        self, golden_n_code: str, golden_n1_code: str, phase_n1: Phase
    ) -> float:
        """Metric D: Incremental testability."""
        ...

    def _metric_signal(self, coverage_own: float, coverage_next: float) -> float:
        """Metric E: Coverage drop severity."""
        drop = coverage_own - coverage_next
        return min(drop / 0.3, 1.0)

    def _compute_structural_score(self, coherence, catalog_spec, delta_simp, incr, signal, bonus) -> float:
        """Mode 1: Structural solvability composite score."""
        return min(
            0.25 * coherence
            + 0.30 * catalog_spec
            + 0.15 * delta_simp
            + 0.15 * incr
            + 0.15 * signal
            + bonus,
            1.0,
        )

    def _compute_agent_visible_score(self, violations, phase_n, phase_n1, delta_simp, incr, signal, bonus) -> float:
        """Mode 2: Agent-visible solvability composite score."""
        ...

    # --- Level 3 ---

    def validate_level_3(self, l2_results: list[FeedbackAdequacyResult]) -> BudgetAdequacyResult: ...

    # --- Level 4 ---

    def validate_level_4(self) -> EmpiricalValidationResult | None: ...

    # --- Orchestration ---

    def validate(self, max_level: int = 3) -> TaskSolvabilityReport: ...
    def determine_verdict(self, l1, l2, l3, l4) -> tuple[str, list[str], list[str]]: ...

    # --- Utilities ---

    @staticmethod
    def obfuscate_scope(scope: str) -> str:
        """Replicate Runner._obfuscate_feedback_dict scope hashing."""
        if scope in ("error", "unknown", "consistency", "direct", "ordering", "nested"):
            return scope
        return f"scope_{hashlib.md5(scope.encode()).hexdigest()[:6]}"

    @staticmethod
    def create_golden_stubs(task_dir: Path) -> list[Path]: ...


# --- Standalone helpers ---

def classify_error(actual: Any, expected: Any) -> str:
    """Classify the difference between actual and expected output."""
    ...

def classify_element_diff(actual: Any, expected: Any) -> str:
    """Classify difference between two scalar values."""
    ...

def score_to_multiplier(agent_visible_score: float) -> float:
    """Convert solvability score to budget multiplier."""
    ...

def score_to_rating(score: float) -> str:
    """Convert numeric score to rating string."""
    if score >= 0.70:
        return "high"
    elif score >= 0.40:
        return "medium"
    elif score >= 0.15:
        return "low"
    return "none"
```

### 11.2 CLI Extension in `saotri_bench/cli.py`

Add to the existing `main()` function's subparser setup:

```python
# validate-solvability command
solvability_parser = subparsers.add_parser(
    "validate-solvability",
    help="Validate task solvability within constraints",
)
# ... arguments as defined in Section 10.2
solvability_parser.set_defaults(func=cmd_validate_solvability)
```

New handler function:

```python
def cmd_validate_solvability(args: argparse.Namespace) -> int:
    """Validate task solvability."""
    # Handle --all vs --task
    # For each task:
    #   Create SolvabilityValidator
    #   Run validate(max_level=args.level)
    #   Print human-readable or JSON output
    # Return 0 if all SOLVABLE, 1 if any issues
```

### 11.3 Optional Module: `saotri_bench/strategies.py`

Only needed for Level 4. Contains `Strategy` ABC and concrete implementations.

---

## 12. Implementation Phases

### Phase 1: Foundation + Level 1 (Priority: HIGH)

**Scope:**
- Create `saotri_bench/solvability.py` with dataclasses and `SolvabilityValidator` skeleton
- Implement `validate_level_1()`
- Implement `create_golden_stubs()`
- Extend `saotri_bench/cli.py` with `validate-solvability` command
- Create golden solutions for task_01_transform_list (simplest, 3 phases)
- Create golden solutions for task_03_validate_brackets (reference task, 5 phases)

**Verification:**
```
saotri-bench validate-solvability --task tasks/task_01_transform_list --level 1
saotri-bench validate-solvability --task tasks/task_03_validate_brackets --level 1
```

Both should report `VERIFIED` at Level 1.

### Phase 2: Level 2 — Feedback Analysis (Priority: HIGH)

**Scope:**
- Implement `_compute_failing_triples()` — run golden_N on phase N+1 tests, collect (input, actual, expected)
- Implement `classify_error()` and `classify_element_diff()` — error signature classification
- Implement `_metric_coherence()` — failure pattern grouping
- Implement `_metric_catalog()` — transformation catalog matching with `TRANSFORM_CATALOG`
- Implement `_metric_delta()` — AST diff between golden solutions
- Implement `_metric_signal()` — coverage drop severity
- Implement `_metric_incremental()` — partial fix testing
- Implement `_compute_structural_score()` (Mode 1) and `_compute_agent_visible_score()` (Mode 2)
- Implement `obfuscate_scope()` — replicate Runner obfuscation for Mode 2
- Implement composite score, feedback_gap, and rating derivation
- Create golden solutions for task_00_fizzbuzz and task_02_merge_dicts

**Verification:**
```
saotri-bench validate-solvability --task tasks/task_01_transform_list --level 2
# Expected: FEEDBACK_INSUFFICIENT (agent_visible < 0.40, feedback_gap > 0.30)

saotri-bench validate-solvability --task tasks/task_03_validate_brackets --level 2
# Expected: SOLVABLE (agent_visible >= 0.70 for most transitions)
```

The framework should produce different verdicts for task_01 vs task_03, matching the audit's findings. Additionally, the structural scores should show that task_01 IS structurally sound — the problem is feedback delivery, not task design.

### Phase 3: Level 3 — Budget Analysis (Priority: MEDIUM)

**Scope:**
- Implement `validate_level_3()` with adjustment multipliers
- Implement `--all` batch mode
- Implement `--json` and `--output` options
- Complete `metadata.yaml` for tasks with golden solutions

**Verification:**
```
saotri-bench validate-solvability --all --tasks-dir tasks
# Expected: task_01 and task_02 fail, task_03 passes, others NO_GOLDEN
```

### Phase 4: Golden Solutions for Remaining Tasks (Priority: MEDIUM)

**Scope:**
- Create golden solutions for all 12 tasks (task_00 through task_11)
- Run full validation suite

**Note:** Hard tasks (task_09 through task_11, 12-15 phases each) require significant implementation effort for golden solutions. Prioritize easy and medium tasks first.

### Phase 5: Level 4 — Empirical Validation (Priority: LOW)

**Scope:**
- Create `saotri_bench/strategies.py`
- Implement GoldenGuidedStrategy and ScopeKeywordStrategy
- Implement `validate_level_4()` and empirical runner
- Wire into CLI with `--level 4`

### Phase 6: CI Integration (Priority: LOW)

**Scope:**
- Add validation to CI pipeline (GitHub Actions or pre-commit)
- Validation gate: new/modified tasks must pass `validate-solvability --level 3`

---

## 13. Relationship to Audit Issues

| Audit Issue | How Framework Addresses It |
|-------------|---------------------------|
| **Issue 3 (P1):** Insufficient feedback for task_01, task_02 | Level 2 dual-mode analysis: structural_solvability ~0.7 (task IS sound) but agent_visible ~0.15 (feedback delivers almost nothing). The feedback_gap of 0.5+ quantifies exactly how much information is lost. This provides concrete evidence for feedback enrichment — enriching feedback should close the gap and raise agent_visible toward the structural score. |
| **Issue 4 (P2):** task_06 phase 2 difficulty cliff | Level 2 analyzes `ttl_expiry` transition: catalog_match_count likely = 0 (TTL not in standard catalog), flagging DOMAIN_KNOWLEDGE. Level 3 flags budget as tight given low agent-visible score. |
| **Issue 5 (P2):** Difficulty labels mismatch | Level 1 proves solvability exists. Level 2 structural score shows task_01 IS appropriate for "easy" — the structural complexity is low. The low agent_visible score proves the problem is feedback delivery, not task difficulty. Decision: fix feedback (keep "easy") rather than relabel. |
| **Issue 6 (P2):** task_05 domain knowledge vs feedback | Level 2 catalog_match_count = 0 for `unicode_combining` transition triggers DOMAIN_KNOWLEDGE flag. This mechanically confirms the task tests prior knowledge (Unicode NFC normalization is not in the standard transformation catalog) rather than feedback literacy. |

### Post-Framework Workflow

1. Run `validate-solvability --all` to get baseline report
2. For tasks with `FEEDBACK_INSUFFICIENT` verdict:
   - Option A: Enrich feedback (add input/output examples to violation messages)
   - Option B: Make scope names more descriptive
   - Option C: Add a new rule with an informative description
   - Option D: Accept as domain-knowledge task and update difficulty
3. Re-run validation to confirm improvement
4. Integrate into CI to prevent regression

---

## 14. Acceptance Criteria

### Functional
- [ ] `saotri-bench validate-solvability --task <path>` runs Levels 1-3 and produces human-readable output
- [ ] `saotri-bench validate-solvability --task <path> --json` produces valid JSON matching the schema in Section 9
- [ ] `saotri-bench validate-solvability --all` validates all tasks with aggregate summary
- [ ] `--create-golden` generates correct stub files and metadata template

### Level 1: Static Solvability
- [ ] Correctly detects golden solutions that fail their own phase
- [ ] Correctly detects golden solutions that do NOT break on the next phase
- [ ] Golden solutions loaded via `sandbox.execute_code()` (same restrictions as agent code)

### Level 2: Feedback Adequacy (Automatic Metrics)
- [ ] Metric A (Coherence): correctly groups error signatures from (input, actual, expected) triples
- [ ] Metric B (Catalog): transformation catalog contains >= 25 entries and correctly matches transforms
- [ ] Metric C (Delta): AST diff computes correct node counts between golden solutions
- [ ] Metric D (Incremental): partial fix testing correctly measures per-change coverage improvement
- [ ] Metric E (Signal): coverage drop correctly computed from evaluator results
- [ ] Dual-mode scoring: structural_solvability and agent_visible_solvability computed independently
- [ ] feedback_gap = structural - agent_visible, correctly identifies information loss
- [ ] Scope obfuscation in Mode 2 matches `Runner._obfuscate_feedback_dict()` exactly
- [ ] task_03 transitions score agent_visible >= 0.60 (medium/high)
- [ ] task_01 transitions score agent_visible < 0.40 (low)
- [ ] task_01 transitions score structural >= 0.60 (proving task is sound, feedback is the issue)
- [ ] Fully automatic — no manual input or LLM calls required

### Level 3: Budget Adequacy
- [ ] Budget multipliers derived from agent_visible_solvability scores
- [ ] task_01 phase 1 flagged as insufficient (buffer < 1.0x)
- [ ] task_03 passes budget check (all buffers >= 2.0x)

### Calibration
- [ ] Weight calibration: task_03 (92% completion) scores >= 0.70 agent_visible on most transitions
- [ ] Weight calibration: task_00 (36% completion) scores 0.40-0.70 on transition 0→1
- [ ] Weight calibration: task_01 (0% completion) scores < 0.40 on transitions
- [ ] DOMAIN_KNOWLEDGE flag triggered when catalog_match_count == 0

### Infrastructure
- [ ] Golden solutions exist for at least task_00, task_01, task_02, task_03
- [ ] Validation runs in < 30 seconds per task (no LLM calls, no network)
- [ ] Non-destructive — no task files modified during validation
- [ ] All new code in `saotri_bench/solvability.py` — no changes to core `evaluator.py`, `runner.py`, `models.py`
- [ ] CLI extension is minimal — only `cli.py` gains the new subcommand
