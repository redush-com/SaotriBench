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
- **Non-destructive.** Task files are never modified during validation.
- **Incremental.** Levels 1-3 are useful independently. Level 4 is optional.
- **Provides evidence, not just verdicts.** Reports include raw data (violations, coverage, scopes) so a human reviewer can override heuristic scores.

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

For each phase transition (N to N+1), determine whether the feedback generated by running golden solution N against phase N+1 tests contains enough information for an agent to discover the solution changes needed.

This is the critical level. The audit identified a pattern:
- **Effective feedback** (`divisible_by_7` in task_00): Scope name maps to solution. 36% completion.
- **Insufficient feedback** (`negative_handling` in task_01): Scope name identifies category but not fix. 0% completion.

### 5.2 Algorithm

```
Input: task_dir, level_1_results
Output: list[FeedbackAdequacyResult]

For each transition N -> N+1:
    1. From level_1_results, get violations_next_phase for golden solution N
       (already computed in Level 1, step 5-6)

    2. Build the Feedback object as Runner would:
       - violations: from evaluator output
       - coverage: from evaluator output
       - summary: rules_total, rules_passed, rules_failed

    3. Apply scope obfuscation (replicate Runner._obfuscate_feedback_dict):
       For each violation:
           if scope in ["error", "unknown", "consistency", "direct", "ordering", "nested"]:
               keep as-is  (structural scopes are transparent)
           else:
               scope = f"scope_{md5(scope)[:6]}"  (domain scopes are obfuscated)

    4. Compute metrics:
       - violation_count: total violations
       - distinct_scopes: unique scope values (pre-obfuscation)
       - obfuscated_scopes: what the agent actually sees
       - information_density: distinct_scopes / violation_count
       - scope_actionability: heuristic rating (see 5.3)

    5. Generate human-readable reasoning
```

### 5.3 Feedback Actionability Rating

The framework assigns a heuristic actionability score to each phase transition. This is the most subjective part of the framework and should be supplemented by human review.

**Rating scale:**

| Rating | Definition | Example | Expected Impact |
|--------|-----------|---------|-----------------|
| **high** | Scope name directly suggests the fix. A competent developer reading the scope name would know what to change. | `error_position` → include position in error message | Agent solves in 1-2 attempts |
| **medium** | Scope name identifies the domain. Multiple plausible fixes, but enumerable (< 5 candidates). | `divisible_by_7` → add divisor-7 handling, but what's the output word? | Agent solves in 2-4 attempts |
| **low** | Scope name names a category, but the fix requires semantic inference. 5+ plausible interpretations. | `negative_handling` → abs? filter? flip? zero? skip? | Agent likely stuck (5+ attempts, may exhaust budget) |
| **none** | Scope is fully opaque or there are no violations. Agent has zero actionable information. | Obfuscated scope with no distinguishing pattern | Agent cannot progress |

**Heuristic classification logic:**

The initial implementation uses keyword-based heuristics. Each scope name (pre-obfuscation) is analyzed:

1. **Check if scope is in the transparent set** (`error`, `unknown`, `consistency`, `direct`, `ordering`, `nested`). If yes, the agent sees the real name. Rate based on how informative the name is.

2. **Check if scope contains a numeric or domain-specific keyword** that maps to a single fix pattern. Examples: `divisible_by_7` (contains a number and operation), `error_position` (describes the output contract). Rate: **high** or **medium**.

3. **Check if scope names a broad category** without specifying the behavior. Examples: `negative_handling` (what handling?), `string_conflict` (what resolution?). Rate: **low**.

4. **After obfuscation, check what remains.** If the scope is obfuscated to `scope_XXXXXX`, the agent sees only the hash. The violation's `rule_id` (e.g., `correct_output`) and `count` are the only remaining signal. Rate: at most **low**, often **none**.

**Override mechanism:** The `metadata.yaml` file can include an explicit `feedback_actionability` rating per transition that overrides the heuristic. This allows human reviewers to correct the automated assessment.

### 5.4 Obfuscation Impact Analysis

A key insight: scope obfuscation fundamentally limits what the agent can infer. The framework reports both the pre-obfuscation and post-obfuscation state so reviewers can assess:

```
Transition 0 -> 1:
  Raw violations:      correct_output/negative_handling (4 tests)
  Obfuscated:          correct_output/scope_a1b2c3 (4 tests)
  Agent sees:          "4 tests failed on rule 'correct_output', scope 'scope_a1b2c3'"
  Information content: Rule name + failure count. No hint about negatives or abs().
  Rating:              LOW
```

Compare with a well-designed transition:

```
Transition 2 -> 3 (task_03_validate_brackets):
  Raw violations:      correct_error/error_position (4 tests)
  Obfuscated:          correct_error/scope_f7e8d9 (4 tests)
  But also:            correct_output/round_only — these are in transparent set? No.
  However:             The NEW rule "correct_error" appears in violations.
                       A new rule_id is a strong signal that the contract changed.
  Agent sees:          New rule "correct_error" with description "Raises ValueError
                       with position for invalid input"
  Information content: Rule description tells agent exactly what to do.
  Rating:              HIGH
```

The key difference: task_03's feedback works because the **rule description** in `phase.json` (visible to the agent) says "Raises ValueError with position". The scope is a secondary signal. Task_01's feedback fails because the rule description ("Output matches expected") is generic and identical across all phases — the scope is the primary signal, and it's obfuscated.

### 5.5 Structural Signal Analysis

Beyond scopes, the framework analyzes other signals available to the agent:

| Signal | Source | Information Content |
|--------|--------|---------------------|
| New rule_id appears | `phase.json` rules list | High — agent knows a new constraint type was added |
| Rule description | `phase.json` rules list | Varies — can be specific or generic |
| Violation count | `feedback.json` violations[].count | Low — tells scale, not nature |
| Coverage delta | `feedback.json` delta.coverage_change | Low — tells direction, not cause |
| New failures vs fixed | `feedback.json` delta.new_failures | Medium — tells which rules regressed |

The framework should compute a composite "information budget" per transition:
- Does the transition introduce a new rule_id? (+2 points)
- Does the new rule have a specific description? (+2 points)
- Is the scope transparent (in the non-obfuscated set)? (+1 point)
- Does the scope name contain a keyword suggesting the fix? (+1 point)
- Is violation count > 1 (provides some hypothesis testing signal)? (+0.5 point)

A score of 4+ suggests **high** actionability. 2-3.5 suggests **medium**. 1-1.5 suggests **low**. 0 suggests **none**.

### 5.6 Pass/Fail Criteria

| Check | Pass | Fail |
|-------|------|------|
| All transitions rated medium or high | Feedback is adequate | — |
| Any transition rated low | — | Feedback may be insufficient (warning) |
| Any transition rated none | — | Feedback is insufficient (error) |

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

    2. Get feedback_actionability from Level 2 results

    3. Apply adjustment multiplier:
       adjusted_min = base_min * multiplier
       where multiplier = {high: 1.0, medium: 1.5, low: 3.0, none: 5.0}

    4. Compute per-phase buffer:
       buffer_ratio = max_attempts_per_phase / adjusted_min
       adequate = buffer_ratio >= 2.0

Compute total budget:
    total_adjusted_min = sum(adjusted_min for all transitions) + len(phases)
    (the +len(phases) accounts for 1 "pass" attempt per phase)
    total_buffer = max_total_attempts / total_adjusted_min
    adequate = total_buffer >= 1.5
```

### 6.3 Adjustment Multipliers

The multipliers account for the empirical reality that low-actionability feedback requires more trial-and-error:

| Feedback Rating | Multiplier | Rationale |
|----------------|-----------|-----------|
| high | 1.0x | Agent can fix in minimum steps |
| medium | 1.5x | Agent may need 1-2 extra attempts to disambiguate |
| low | 3.0x | Agent must try multiple hypotheses (abs? filter? flip?) |
| none | 5.0x | Agent is essentially brute-forcing |

### 6.4 Example: task_01_transform_list

```
Phase 0: min_steps=1, feedback=N/A (first phase), adjusted=1
Phase 0->1: min_steps=2, feedback=low, adjusted=2*3.0=6
Phase 1->2: min_steps=1, feedback=low, adjusted=1*3.0=3

Per-phase:
  Phase 1 budget: max_attempts_per_phase=5, adjusted_min=6, buffer=0.83x  FAIL
  Phase 2 budget: max_attempts_per_phase=5, adjusted_min=3, buffer=1.67x  WARN

Total:
  total_adjusted_min = 1 + 6 + 3 + 3 (pass attempts) = 13
  max_total_attempts = 15
  buffer = 1.15x  WARN
```

This analysis mechanically confirms the audit's concern: task_01's budget is insufficient given the low feedback actionability.

### 6.5 Example: task_03_validate_brackets

```
Phase 0: min_steps=1, adjusted=1
Phase 0->1: min_steps=1, feedback=high (new bracket types obvious), adjusted=1
Phase 1->2: min_steps=1, feedback=medium (whitespace handling), adjusted=1.5
Phase 2->3: min_steps=2, feedback=high (new rule "correct_error"), adjusted=2
Phase 3->4: min_steps=1, feedback=medium (edge cases), adjusted=1.5

Per-phase: all budgets have buffer >= 2.0x  OK

Total:
  total_adjusted_min = 1 + 1 + 1.5 + 2 + 1.5 + 5 = 12
  max_total_attempts = 25
  buffer = 2.08x  OK
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
1. If no golden/ directory exists:               → NO_GOLDEN
2. If any golden solution is missing:             → NO_GOLDEN
3. If any golden fails its own phase:             → LIKELY_BROKEN
4. If any golden does NOT break on next phase:    → LIKELY_BROKEN
5. If any transition rated "none" actionability:  → FEEDBACK_INSUFFICIENT
6. If any transition rated "low" actionability:   → FEEDBACK_INSUFFICIENT
7. If any per-phase budget ratio < 1.0:           → BUDGET_TOO_TIGHT
8. If total budget ratio < 1.0:                   → BUDGET_TOO_TIGHT
9. Otherwise:                                     → SOLVABLE
```

**Additional flags** (non-blocking):
- `FEEDBACK_WARN`: Any transition rated "low" (if not already INSUFFICIENT)
- `BUDGET_WARN`: Any per-phase buffer between 1.0x and 2.0x

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
class FeedbackAdequacyResult:
    """Result of analyzing feedback quality for a phase transition."""
    from_phase: int
    to_phase: int
    violation_count: int
    distinct_scopes: list[str]                 # Pre-obfuscation
    obfuscated_scopes: list[str]               # Post-obfuscation (what agent sees)
    information_density: float                 # distinct_scopes / violation_count
    new_rule_ids: list[str]                    # Rules appearing for first time in to_phase
    feedback_actionability: str                # "high" | "medium" | "low" | "none"
    information_score: float                   # Composite score (see 5.5)
    reasoning: str


@dataclass
class BudgetPhaseResult:
    """Budget analysis for a single phase transition."""
    from_phase: int
    to_phase: int
    base_min_steps: int
    feedback_multiplier: float
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
    feedback_adequate: bool

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
    Violations: correct_output/negative_handling (x4)
    Agent sees: correct_output/scope_a1b2c3 (x4)
    New rules: none
    Score: 0.5/6.0 | Rating: LOW
    Reason: Scope obfuscated. No new rule. Agent cannot infer abs() from "scope_a1b2c3".
  Transition 1 -> 2:
    Violations: correct_output/cap_overflow (x4)
    Agent sees: correct_output/scope_d4e5f6 (x4)
    New rules: correct_type (description: "Return is list")
    Score: 2.5/6.0 | Rating: LOW
    Reason: correct_type rule is new but doesn't help with cap. Cap threshold (100)
            not discoverable from feedback.
  Result: INSUFFICIENT (2 transitions rated LOW)

--- Level 3: Budget Adequacy ---
  Phase 0->1: min=2, adjusted=6.0 (x3.0 for LOW feedback), budget=5  FAIL (0.8x)
  Phase 1->2: min=1, adjusted=3.0 (x3.0 for LOW feedback), budget=5  WARN (1.7x)
  Total: adjusted_min=12.0, budget=15  WARN (1.2x)
  Result: TIGHT (1 phase below 1.0x buffer)

=== VERDICT: FEEDBACK_INSUFFICIENT ===
Issues:
  1. Transition 0->1: actionability=LOW — scope 'negative_handling' obfuscated to
     'scope_a1b2c3', agent cannot infer abs() transformation
  2. Transition 1->2: actionability=LOW — cap threshold (100) not discoverable
  3. Phase 1 budget (5 attempts) below adjusted minimum (6.0) for LOW feedback
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

from pathlib import Path
from .loader import load_task, load_evaluator, load_tests
from .sandbox import execute_code
from .models import TaskConfig, Phase, TestCase, Violation, Feedback

class SolvabilityValidator:
    """Validates that a benchmark task is solvable within its constraints."""

    def __init__(self, task_dir: Path):
        self.task_dir = Path(task_dir)
        self.golden_dir = self.task_dir / "golden"

        self.task_config = load_task(self.task_dir)
        self.evaluator = load_evaluator(self.task_dir)
        self.test_cases = load_tests(self.task_dir)

        self.golden_solutions: dict[int, str] = {}    # phase_id -> source code
        self.golden_metadata: dict | None = None

    def has_golden_solutions(self) -> bool:
        """Check if golden/ directory exists with all required files."""
        ...

    def load_golden_solutions(self) -> bool:
        """Load all golden solution source code files."""
        ...

    def load_golden_metadata(self) -> dict | None:
        """Load metadata.yaml if present."""
        ...

    def validate_level_1(self) -> list[GoldenSolutionResult]:
        """Level 1: Static solvability — golden solutions pass and break correctly."""
        ...

    def validate_level_2(self, l1_results: list[GoldenSolutionResult]) -> list[FeedbackAdequacyResult]:
        """Level 2: Feedback adequacy — analyze what agents see at each transition."""
        ...

    def validate_level_3(self, l2_results: list[FeedbackAdequacyResult]) -> BudgetAdequacyResult:
        """Level 3: Budget adequacy — verify step limits are sufficient."""
        ...

    def validate_level_4(self) -> EmpiricalValidationResult | None:
        """Level 4: Empirical validation — run strategies (optional)."""
        ...

    def validate(self, max_level: int = 3) -> TaskSolvabilityReport:
        """Run the full validation pipeline up to max_level."""
        ...

    def determine_verdict(self, l1, l2, l3, l4) -> tuple[str, list[str], list[str]]:
        """Determine verdict, flags, and issues from level results."""
        ...

    @staticmethod
    def obfuscate_scope(scope: str) -> str:
        """Replicate Runner._obfuscate_feedback_dict scope hashing."""
        import hashlib
        if scope in ("error", "unknown", "consistency", "direct", "ordering", "nested"):
            return scope
        return f"scope_{hashlib.md5(scope.encode()).hexdigest()[:6]}"

    @staticmethod
    def create_golden_stubs(task_dir: Path) -> list[Path]:
        """Create golden/ directory with stub files for a task."""
        ...
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
- Implement `validate_level_2()` with obfuscation replication and actionability scoring
- Implement the information score composite (Section 5.5)
- Create golden solutions for task_00_fizzbuzz and task_02_merge_dicts

**Verification:**
```
saotri-bench validate-solvability --task tasks/task_01_transform_list --level 2
# Expected: FEEDBACK_INSUFFICIENT

saotri-bench validate-solvability --task tasks/task_03_validate_brackets --level 2
# Expected: SOLVABLE (or feedback warnings only)
```

The framework should produce different verdicts for task_01 vs task_03, matching the audit's findings.

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
| **Issue 3 (P1):** Insufficient feedback for task_01, task_02 | Level 2 mechanically confirms actionability=LOW for these transitions. Report provides evidence for feedback enrichment decisions. |
| **Issue 4 (P2):** task_06 phase 2 difficulty cliff | Level 2 analyzes `ttl_expiry` scope actionability. Level 3 flags if budget is tight given the cliff. |
| **Issue 5 (P2):** Difficulty labels mismatch | Level 1 proves solvability exists. Level 2 shows the problem is feedback, not inherent difficulty. Decision: fix feedback (keep "easy") or relabel (accept low actionability). |
| **Issue 6 (P2):** task_05 domain knowledge vs feedback | Level 2 rates `unicode_combining` actionability. If rated "none" (domain knowledge required), this confirms the task tests prior knowledge rather than feedback literacy. |

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

- [ ] `saotri-bench validate-solvability --task <path>` runs Levels 1-3 and produces human-readable output
- [ ] `saotri-bench validate-solvability --task <path> --json` produces valid JSON matching the schema in Section 9
- [ ] `saotri-bench validate-solvability --all` validates all tasks with aggregate summary
- [ ] `--create-golden` generates correct stub files and metadata template
- [ ] Level 1 correctly detects golden solutions that fail their own phase
- [ ] Level 1 correctly detects golden solutions that do NOT break on the next phase
- [ ] Level 2 rates task_03 transitions as medium/high actionability
- [ ] Level 2 rates task_01 transitions as low actionability
- [ ] Level 2 correctly applies scope obfuscation matching `Runner._obfuscate_feedback_dict()`
- [ ] Level 3 flags task_01 phase 1 budget as insufficient
- [ ] Level 3 passes task_03 budget check
- [ ] Golden solutions exist for at least task_00, task_01, task_02, task_03
- [ ] Validation runs in < 30 seconds per task (no LLM calls, no network)
- [ ] Non-destructive — no task files modified during validation
- [ ] All new code in `saotri_bench/solvability.py` — no changes to core `evaluator.py`, `runner.py`, `models.py`
- [ ] CLI extension is minimal — only `cli.py` gains the new subcommand
