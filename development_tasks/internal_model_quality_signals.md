# Internal Model Quality Signals & Predictive Element

## Technical Specification

**Date:** 2026-02-22
**Status:** Draft
**Priority:** HIGH
**Depends on:** None (independent of solvability validation framework)
**Source:** Audit analysis — benchmark currently measures training data contamination, not internal model quality

---

## 1. Problem Statement

### 1.1 What the Benchmark Claims to Measure

SaotriBench evaluates LLM agents on **hidden requirement discovery through iterative feedback** (SAOTRI: State, Actions, Observations, Transitions, Resilience, Invariants). The core claim is that the benchmark measures the quality of the agent's **internal model** — its ability to build, maintain, and update a coherent understanding of an evolving system.

### 1.2 What the Benchmark Actually Measures

Analysis of task_00_fizzbuzz reveals the current benchmark primarily measures:

| Claimed | Actual |
|---------|--------|
| Hidden invariant discovery | Training data recall ("FizzBuzzBazz" is a known variant) |
| Feedback literacy | Ability to guess from obfuscated scope names |
| Internal model quality | Task completion (binary pass/fail) |
| Iterative refinement skill | Reactive debugging (fix what broke) |

The current feedback loop is **purely reactive**: code breaks → agent sees violation → agent fixes code. This tests **iterative debugging skill**, not **internal model quality**. An agent can achieve 100% completion by reactively patching without ever building a coherent model of the system.

### 1.3 The Missing Signal

A quality internal model has a defining property: **predictive power**. An agent that truly understands the system can predict what will happen before it happens. An agent that is merely patching cannot.

Additionally, an internal model manifests through several **behavioral signals** observable in the solution trajectory: consistency, generalization, abstraction level, and convergence pattern. These signals are currently not tracked.

### 1.4 What This Specification Adds

Two capabilities:

1. **Predictive Element** — a protocol extension that asks the agent to make predictions at key checkpoints, measuring whether the agent has built a genuine model or is merely reactive.

2. **Internal Model Quality Score (IMQS)** — a composite metric computed from behavioral signals during the benchmark run, providing a second axis of evaluation orthogonal to task completion.

```
Current scoring:
  Model → Task Completion Score (0-100%)

New scoring:
  Model → Task Completion Score (0-100%)
        → Internal Model Quality Score (0-100%)

A model can score high on completion but low on IMQS (reactive patcher)
A model can score medium on completion but high on IMQS (genuine understanding, ran out of budget)
```

---

## 2. Part I: Predictive Element

### 2.1 Core Concept

At phase transition boundaries, **before** the agent sees the implicit evaluation results for the new phase, ask the agent to predict:
1. What rules will its current solution violate in the next phase?
2. What coverage does it expect?
3. How confident is it?

Then compare predictions against actual results. Prediction accuracy directly measures internal model quality — an agent cannot predict behavior it doesn't understand.

### 2.2 Why Phase Transitions?

Phase transitions are the natural checkpoint because:
- The agent has just achieved VALID on phase N (full context available)
- Phase N+1 rules are about to be applied to the current code
- The implicit evaluation already runs at this point (`runner.py:457-461`)
- Predictions are non-blocking — they don't affect the benchmark flow
- The agent has maximum information (problem, all prior rules, violation history)

### 2.3 Protocol Extension

**Current flow** (`agents/bench_runner.py:185-264`):

```
Agent achieves Status.VALID on phase N
  → Runner calls runner._advance_phase()
  → Runner calls runner.run_implicit_evaluation()
  → Runner writes phase.json with implicit results
  → Agent reads phase.json, sees new rules + implicit feedback
  → Agent refines solution for phase N+1
```

**Extended flow:**

```
Agent achieves Status.VALID on phase N
  → Runner writes prediction_request.json with new phase rules (NO implicit results yet)
  → Agent reads prediction_request.json
  → Agent writes prediction.json with its predictions
  → Runner calls runner.run_implicit_evaluation()
  → Runner writes phase.json with implicit results (as before)
  → Runner writes prediction_result.json comparing prediction vs actual
  → Agent reads phase.json (normal flow continues)
```

### 2.4 Workspace Files

**New file: `prediction_request.json`** (Runner → Agent)

Written after phase N completion, before implicit evaluation results are shared.

```json
{
  "type": "phase_transition_prediction",
  "completed_phase": 1,
  "next_phase": 2,
  "next_phase_rules": [
    {"id": "correct_output", "description": "Output matches expected string"},
    {"id": "correct_type", "description": "Return value must be a string"},
    {"id": "deterministic", "description": "Same input always produces same output"}
  ],
  "your_current_solution_hash": "sha256:abc123...",
  "prompt": "Your solution passed phase 1. Phase 2 adds the rules listed above. WITHOUT modifying your code, predict how your current solution will perform against the new rules."
}
```

**New file: `prediction.json`** (Agent → Runner)

Agent writes its predictions before seeing implicit evaluation results.

```json
{
  "completed_phase": 1,
  "next_phase": 2,
  "predicted_coverage": 0.75,
  "predicted_violations": [
    {
      "rule_id": "correct_output",
      "expected_scope": "combined_divisors",
      "reason": "My solution handles individual divisors but not combinations like 21=3*7"
    }
  ],
  "predicted_new_rules_impact": "The deterministic rule should pass since my function is pure. The correct_output rule will likely fail for numbers divisible by multiple new divisors since I haven't handled combined outputs.",
  "confidence": 0.6
}
```

**New file: `prediction_result.json`** (Runner → Agent, for metrics only)

```json
{
  "completed_phase": 1,
  "next_phase": 2,
  "prediction_accuracy": {
    "coverage_error": 0.07,
    "rules_predicted_correctly": ["deterministic"],
    "rules_missed": ["correct_output"],
    "rules_false_alarm": [],
    "violation_count_predicted": 1,
    "violation_count_actual": 3,
    "overall_score": 0.65
  }
}
```

### 2.5 Prediction Scoring Algorithm

```python
def score_prediction(prediction: dict, actual_feedback: Feedback) -> PredictionScore:
    """Compare agent's predictions against actual implicit evaluation."""

    # 1. Coverage accuracy (0..1, higher = more accurate)
    coverage_error = abs(prediction["predicted_coverage"] - actual_feedback.summary.coverage)
    coverage_accuracy = max(0, 1.0 - coverage_error / 0.5)
    # Error of 0 → 1.0, error of 0.5+ → 0.0

    # 2. Rule-level accuracy (precision + recall on violated rules)
    predicted_rules = {v["rule_id"] for v in prediction["predicted_violations"]}
    actual_rules = {v.rule_id for v in actual_feedback.violations}

    if not actual_rules and not predicted_rules:
        rule_accuracy = 1.0  # Both correctly predicted no violations
    elif not actual_rules or not predicted_rules:
        rule_accuracy = 0.0  # One side is empty, the other isn't
    else:
        precision = len(predicted_rules & actual_rules) / len(predicted_rules)
        recall = len(predicted_rules & actual_rules) / len(actual_rules)
        rule_accuracy = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # 3. Status prediction (did agent predict pass vs fail correctly?)
    predicted_pass = prediction["predicted_coverage"] >= 0.95  # Threshold for "I think it will pass"
    actual_pass = actual_feedback.status == Status.VALID
    status_accuracy = 1.0 if predicted_pass == actual_pass else 0.0

    # 4. Calibration (is confidence aligned with accuracy?)
    confidence = prediction.get("confidence", 0.5)
    actual_accuracy = (coverage_accuracy + rule_accuracy) / 2
    calibration = 1.0 - abs(confidence - actual_accuracy)

    # Composite
    overall = (
        0.30 * coverage_accuracy +
        0.35 * rule_accuracy +
        0.20 * status_accuracy +
        0.15 * calibration
    )

    return PredictionScore(
        coverage_accuracy=coverage_accuracy,
        rule_accuracy=rule_accuracy,
        status_accuracy=status_accuracy,
        calibration=calibration,
        overall=overall,
    )
```

### 2.6 Integration with Agent

The agent (`agents/agent.py`) needs a new method to generate predictions. This is a prompt engineering task — the agent's LLM is asked to reason about its own code before seeing test results.

```python
# In CodingAgent class

def generate_prediction(self, prediction_request: dict) -> dict:
    """Generate predictions for the next phase based on current understanding."""
    prompt = self._build_prediction_prompt(prediction_request)
    response = self.llm_client.chat(self.model, self.conversation + [{"role": "user", "content": prompt}])
    return self._parse_prediction_response(response)

def _build_prediction_prompt(self, request: dict) -> str:
    return f"""Your solution just passed phase {request['completed_phase']}.

Phase {request['next_phase']} adds these rules:
{json.dumps(request['next_phase_rules'], indent=2)}

Your current solution will now be evaluated against ALL rules (old + new)
WITHOUT any changes to your code.

Analyze your current solution and predict:
1. What coverage do you expect? (0.0 to 1.0)
2. Which rules will your current solution violate, and why?
3. How confident are you in this prediction? (0.0 to 1.0)

Think step by step about what your code does and how the new rules might
expose gaps in your implementation. Be specific about which aspects of
your solution might fail.

Respond in JSON format:
{{
  "predicted_coverage": <float>,
  "predicted_violations": [
    {{"rule_id": "<id>", "expected_scope": "<description>", "reason": "<why>"}}
  ],
  "predicted_new_rules_impact": "<analysis>",
  "confidence": <float>
}}"""
```

### 2.7 Non-Prediction Mode (Backward Compatibility)

Predictions are **optional**. The protocol supports three modes:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `--predict=off` (default) | No prediction files created. Standard flow. | Backward compatibility, fast runs |
| `--predict=passive` | prediction_request.json written, agent MAY respond. Scored if present. | Gradual adoption |
| `--predict=required` | Agent MUST write prediction.json before phase advances. Timeout = 60s. | Full IMQS measurement |

### 2.8 What Predictions Reveal

**High prediction accuracy (>0.7):**
- Agent understands its own code
- Agent understands the rule structure
- Agent has built a model that extends beyond seen test cases
- The agent can reason about *consequences* of its design choices

**Low prediction accuracy (<0.3):**
- Agent is coding reactively without understanding
- Agent cannot reason about its own code's behavior
- Success (if any) comes from trial-and-error or training data recall

**Overconfident predictions (high confidence, low accuracy):**
- Agent has a *wrong* internal model — believes it understands but doesn't
- This is actually the most concerning pattern for real-world deployment

**Underconfident predictions (low confidence, high accuracy):**
- Agent understands more than it thinks — good model, poor calibration

---

## 3. Part II: Behavioral Quality Signals

Beyond predictions, an agent's solution trajectory reveals internal model quality through observable behavioral patterns. These signals are computed from data already collected (or collectible with minimal changes) during the benchmark run.

### 3.1 Signal Taxonomy

Signals are organized into three tiers by implementation effort:

```
Tier 1 — ZERO COST (computable from existing report data)
Tier 2 — LOW COST (requires AST analysis of final solution.py)
Tier 3 — MEDIUM COST (requires storing per-attempt solution snapshots)
```

### 3.2 Tier 1 Signals: From Existing Data

These signals can be computed TODAY from existing report JSON files and error_log data.

#### Signal 1.1: Implicit Evaluation Pass Rate

**What it measures:** Does the agent's solution pass new phase rules WITHOUT seeing them?

**Why it matters:** This is the single strongest existing signal. When an agent's code passes phase N+1 tests at phase transition — before any feedback — it means the agent built a solution that generalizes beyond what was tested. This is unambiguous evidence of a quality internal model.

**Data source:** `phase.json` → `implicit_evaluation.status` at each transition. Already recorded by `runner.run_implicit_evaluation()` (runner.py:358-367).

**Metric:**
```python
implicit_pass_rate = phases_where_implicit_coverage_eq_1 / total_phase_transitions
implicit_avg_coverage = mean(implicit_coverage_at_each_transition)
```

**Existing evidence:** Audit data shows Claude Sonnet 4.6 on task_00_fizzbuzz achieved `attempts=0` on phase 2 — the solution for phase 1 already handled phase 2 combinations. This is strong evidence of a model that understood "divisibility rules compose."

#### Signal 1.2: Oscillation Detection

**What it measures:** Does the agent cycle between fixing rule A and breaking rule B?

**Why it matters:** Oscillation is the clearest signal of *no internal model*. An agent that understands the constraint system would never regress on something it already fixed. Pass-fail-pass cycles on the same rule indicate blind patching.

**Data source:** `feedback.json` violation history across attempts within a phase. `Delta.new_failures` and `Delta.fixed_failures` (models.py:148-154).

**Metric:**
```python
def detect_oscillation(violation_history: list[set[str]]) -> float:
    """Track rule_id sets across attempts, detect cycles."""
    oscillating_rules = set()
    for rule_id in all_rules_seen:
        states = [rule_id in v for v in violation_history]  # True=failing, False=passing
        # Detect A-B-A pattern (fail-pass-fail or pass-fail-pass)
        for i in range(len(states) - 2):
            if states[i] == states[i+2] and states[i] != states[i+1]:
                oscillating_rules.add(rule_id)
                break
    oscillation_rate = len(oscillating_rules) / max(len(all_rules_seen), 1)
    return oscillation_rate  # 0 = no oscillation (good), 1 = all rules oscillate (bad)
```

#### Signal 1.3: Monotonic Convergence

**What it measures:** Does coverage only go up, or does it fluctuate?

**Why it matters:** True understanding produces monotonic improvement. Reactive patching produces noisy, non-monotonic coverage trajectories.

**Data source:** `feedback.summary.coverage` per attempt.

**Metric:**
```python
def monotonicity_score(coverages: list[float]) -> float:
    """1.0 = coverage never decreases, 0.0 = decreases every step."""
    if len(coverages) < 2:
        return 1.0
    decreases = sum(1 for i in range(1, len(coverages)) if coverages[i] < coverages[i-1])
    return 1.0 - decreases / (len(coverages) - 1)
```

#### Signal 1.4: Stagnation Detection

**What it measures:** Does the agent get stuck repeating the same failed approach?

**Why it matters:** An agent with self-awareness would change strategy after repeated failures. Stagnation (same violations across multiple attempts) indicates the agent cannot form new hypotheses.

**Data source:** Violation sets per attempt.

**Metric:**
```python
def stagnation_index(violation_sets: list[set[str]]) -> float:
    """Fraction of consecutive attempt pairs with identical violation sets."""
    if len(violation_sets) < 2:
        return 0.0
    identical = sum(1 for i in range(1, len(violation_sets)) if violation_sets[i] == violation_sets[i-1])
    return identical / (len(violation_sets) - 1)
```

#### Signal 1.5: Convergence Velocity

**What it measures:** How quickly does coverage improve? Does the first fix close most of the gap?

**Why it matters:** An agent with a genuine model makes one large, correct fix (high first-attempt ratio). An agent doing trial-and-error makes many small, noisy improvements.

**Data source:** Coverage sequence per phase.

**Metric:**
```python
def convergence_velocity(coverages: list[float]) -> float:
    """What fraction of total coverage gain comes from the first attempt?"""
    if len(coverages) < 2 or coverages[-1] == coverages[0]:
        return 1.0
    first_gain = coverages[1] - coverages[0]
    total_gain = coverages[-1] - coverages[0]
    return first_gain / total_gain if total_gain > 0 else 0.0
```

#### Signal 1.6: Attempt Efficiency Trend Across Phases

**What it measures:** Does the agent get faster (learning) or slower (accumulating confusion)?

**Why it matters:** An agent building a genuine model should accelerate as it internalizes the task's pattern. An agent doing reactive patching slows down as constraint space grows.

**Data source:** `phase_results[i].attempts` in report JSON. Already stored.

**Metric:**
```python
def learning_curve_slope(attempts_per_phase: list[int]) -> float:
    """Negative = agent is learning, positive = agent is struggling more."""
    if len(attempts_per_phase) < 2:
        return 0.0
    x = list(range(len(attempts_per_phase)))
    slope = np.polyfit(x, attempts_per_phase, 1)[0]
    return slope  # <0 is good, >0 is bad
```

### 3.3 Tier 2 Signals: From Solution AST Analysis

These require parsing the final `solution.py` but no protocol changes.

#### Signal 2.1: Literal Density (Hard-Coding Detection)

**What it measures:** Does the solution contain hard-coded test case values, or general patterns?

**Why it matters:** This is the most revealing automated signal for distinguishing "genuine understanding" from "fitting to feedback." If the solution contains `if n == 7 or n == 14 or n == 49: return "Bazz"` instead of `if n % 7 == 0`, the agent has no model — it memorized examples.

**Metric:**
```python
import ast

def literal_density(solution_code: str, test_cases: list[TestCase]) -> dict:
    """Detect hard-coded test values in solution."""
    tree = ast.parse(solution_code)

    # Collect all literals from solution
    solution_literals = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value not in (True, False, None, 0, 1, "", -1):
            solution_literals.add(node.value)

    # Collect test case input values
    test_inputs = set()
    for tc in test_cases:
        if isinstance(tc.input, (int, float, str)):
            test_inputs.add(tc.input)
        # Flatten nested inputs as needed

    # How many test inputs appear as literals in the solution?
    hard_coded = solution_literals & test_inputs
    hard_coding_ratio = len(hard_coded) / max(len(test_inputs), 1)

    # Total literal density
    total_nodes = sum(1 for _ in ast.walk(tree))
    literal_count = len(solution_literals)
    density = literal_count / max(total_nodes, 1)

    return {
        "hard_coding_ratio": hard_coding_ratio,    # 0 = good (general), 1 = bad (hard-coded)
        "literal_density": density,                 # lower = more abstract
        "hard_coded_values": list(hard_coded),      # specific values
    }
```

#### Signal 2.2: Cyclomatic Complexity Ratio

**What it measures:** Is the solution's branching complexity proportional to the rule space, or disproportionately large?

**Why it matters:** General solutions have branching proportional to the number of rules. Over-specific solutions have excessive branching (one branch per test case rather than per rule).

**Metric:**
```python
def complexity_ratio(solution_code: str, phase: Phase) -> float:
    """Compare code complexity to rule/scope count."""
    tree = ast.parse(solution_code)
    branches = sum(1 for node in ast.walk(tree)
                   if isinstance(node, (ast.If, ast.IfExp, ast.Match)))
    rule_scope_count = sum(len(r.scopes) for r in phase.rules)
    return branches / max(rule_scope_count, 1)
    # ~1.0 = proportional (good), >>1.0 = over-specific (bad)
```

#### Signal 2.3: Domain Vocabulary Alignment

**What it measures:** Do variable/function names reflect domain understanding?

**Why it matters:** Naming reflects comprehension. An agent that names a variable `role_hierarchy` instead of `temp_dict` has internalized the domain model.

**Metric:**
```python
def domain_vocabulary_score(solution_code: str, task_config: TaskConfig) -> float:
    """Check if solution identifiers use domain-relevant terms."""
    tree = ast.parse(solution_code)

    # Extract identifiers from solution
    identifiers = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            identifiers.add(node.id.lower())
        elif isinstance(node, ast.FunctionDef):
            identifiers.add(node.name.lower())

    # Extract domain terms from task description + rule descriptions + scope names
    domain_terms = set()
    for word in task_config.description.lower().split():
        if len(word) > 3:  # Skip short words
            domain_terms.add(word)
    for phase in task_config.phases:
        for rule in phase.rules:
            for word in rule.description.lower().split():
                if len(word) > 3:
                    domain_terms.add(word)
            for scope in rule.scopes:
                domain_terms.add(scope.lower())

    overlap = identifiers & domain_terms
    return len(overlap) / max(len(domain_terms), 1)
```

### 3.4 Tier 3 Signals: Requiring Per-Attempt Solution Snapshots

These require storing `solution.py` at each attempt (not just the final version). This is a small infrastructure change: copy solution.py to `solution_attempt_{N}.py` before each evaluation.

#### Signal 3.1: Fix Precision

**What it measures:** How many violations are fixed per code change? Surgical fixes vs. scattered rewrites.

**Why it matters:** An agent with a model makes targeted, minimal edits. An agent without a model rewrites large sections hoping something works.

**Metric:**
```python
def fix_precision(ast_changes: int, violations_fixed: int) -> float:
    """Violations fixed per AST node changed. Higher = more precise."""
    if ast_changes == 0:
        return 0.0
    return violations_fixed / ast_changes
```

#### Signal 3.2: Phase Transition Churn

**What it measures:** How much code is rewritten at each phase transition?

**Why it matters:** A good internal model produces extensible code. Adding a new requirement should be a small addition, not a rewrite. High churn means the architecture can't accommodate new rules.

**Metric:**
```python
def phase_churn(solution_before: str, solution_after: str) -> float:
    """Fraction of AST nodes changed at phase transition."""
    nodes_before = set(ast.dump(n) for n in ast.walk(ast.parse(solution_before)))
    nodes_after = set(ast.dump(n) for n in ast.walk(ast.parse(solution_after)))
    changed = len(nodes_before.symmetric_difference(nodes_after))
    total = len(nodes_before | nodes_after)
    return changed / max(total, 1)  # 0 = no change (ideal), 1 = complete rewrite (bad)
```

#### Signal 3.3: Strategy Shift Detection

**What it measures:** When stuck, does the agent try fundamentally different approaches or keep tweaking the same thing?

**Why it matters:** Self-aware agents recognize when their approach is failing and pivot. Non-self-aware agents continue minor tweaks indefinitely.

**Metric:**
```python
def detect_strategy_shifts(solutions: list[str], coverages: list[float]) -> dict:
    """Detect if agent changes approach after stagnation."""
    shifts_after_stagnation = 0
    stagnation_periods = 0

    for i in range(2, len(solutions)):
        # Stagnation: 2+ consecutive attempts with <1% coverage change
        if abs(coverages[i-1] - coverages[i-2]) < 0.01:
            stagnation_periods += 1
            # Major rewrite: >30% of AST nodes changed
            churn = phase_churn(solutions[i-1], solutions[i])
            if churn > 0.30:
                shifts_after_stagnation += 1

    return {
        "stagnation_periods": stagnation_periods,
        "strategy_shifts": shifts_after_stagnation,
        "adaptability": shifts_after_stagnation / max(stagnation_periods, 1),
    }
```

### 3.5 Tier 4 Signal: Generalization (Requires Held-Out Tests)

#### Signal 4.1: Held-Out Test Set Performance

**What it measures:** Does the solution work on inputs the agent never received feedback about?

**Why it matters:** This is the gold standard for generalization. An agent that only fixes specific test cases will fail on unseen inputs. An agent with a genuine model will pass them naturally.

**Implementation:** Each task gains a second test case list tagged `holdout=True`. These tests are NEVER used during the feedback loop — only evaluated silently after the agent's final submission.

```python
# In tests.py for each task:
HOLDOUT_CASES = [
    TestCase(input=77, expected="Bazz", phase=1, tags=["divisible_by_7"], holdout=True),
    TestCase(input=343, expected="Bazz", phase=1, tags=["divisible_by_7"], holdout=True),
    # ... inputs that test the RULE, not the specific VALUES seen in feedback
]
```

**Metric:**
```python
generalization_score = holdout_coverage / feedback_coverage
# 1.0 = perfect generalization
# <1.0 = overfitting to feedback test cases
```

---

## 4. Internal Model Quality Score (IMQS) — Composite Metric

### 4.1 Score Composition

The IMQS combines all signals into a single 0-100 score:

```python
def compute_imqs(signals: dict) -> float:
    """Compute Internal Model Quality Score (0-100)."""

    # Tier 1: Behavioral trajectory (available now)
    trajectory_score = weighted_mean([
        (0.25, signals["implicit_pass_rate"]),          # 1.1
        (0.20, 1.0 - signals["oscillation_rate"]),      # 1.2 (inverted)
        (0.15, signals["monotonicity_score"]),           # 1.3
        (0.15, 1.0 - signals["stagnation_index"]),      # 1.4 (inverted)
        (0.15, signals["convergence_velocity"]),         # 1.5
        (0.10, max(0, -signals["learning_curve_slope"])),# 1.6 (negative is good)
    ])

    # Tier 2: Code quality (from solution AST)
    code_score = weighted_mean([
        (0.50, 1.0 - signals["hard_coding_ratio"]),     # 2.1 (inverted)
        (0.30, min(signals["complexity_ratio"], 2.0) / 2.0),  # 2.2 (capped)
        (0.20, signals["domain_vocabulary_score"]),       # 2.3
    ])

    # Tier 3: Solution evolution (from snapshots, if available)
    evolution_score = weighted_mean([
        (0.40, signals.get("fix_precision", 0.5)),        # 3.1
        (0.30, 1.0 - signals.get("avg_phase_churn", 0.5)),# 3.2 (inverted)
        (0.30, signals.get("adaptability", 0.5)),         # 3.3
    ]) if signals.get("has_snapshots") else None

    # Tier 4: Generalization (from held-out tests, if available)
    generalization_score = signals.get("generalization_score")  # 4.1

    # Predictive element (if available)
    prediction_score = signals.get("prediction_accuracy")  # §2.5

    # Composite with tier availability weighting
    components = [
        (0.30, trajectory_score),
        (0.20, code_score),
    ]
    if evolution_score is not None:
        components.append((0.15, evolution_score))
    if generalization_score is not None:
        components.append((0.15, generalization_score))
    if prediction_score is not None:
        components.append((0.20, prediction_score))

    # Normalize weights to sum to 1.0
    total_weight = sum(w for w, _ in components)
    imqs = sum(w * s for w, s in components) / total_weight

    return round(imqs * 100, 1)  # Scale to 0-100
```

### 4.2 Score Interpretation

| IMQS | Interpretation |
|------|---------------|
| 80-100 | Strong internal model — agent understands the system, generalizes, predicts accurately |
| 60-79 | Moderate model — agent has partial understanding, some reactive patterns |
| 40-59 | Weak model — agent mostly reacts to feedback, limited understanding |
| 20-39 | Minimal model — agent is pattern matching / trial-and-error |
| 0-19 | No model — agent is guessing or has fundamental comprehension issues |

### 4.3 Two-Axis Evaluation

The IMQS and Task Completion Score together create a 2D evaluation space:

```
IMQS (Internal Model Quality)
100 │
    │  Understands but      Genuine mastery
    │  ran out of budget    (goal)
    │        ◆                    ◆
 50 │
    │  No understanding     Reactive patcher
    │  (worst)              (inflated score)
    │        ◆                    ◆
  0 │──────────────────────────────── Task Completion
    0                50               100
```

| Quadrant | Completion | IMQS | Diagnosis |
|----------|-----------|------|-----------|
| Top-right | High | High | Genuine mastery — the model truly understands |
| Top-left | Low | High | Understands but ran out of budget or hit a guessing barrier |
| Bottom-right | High | Low | **Reactive patcher** — dangerous: appears competent but brittle |
| Bottom-left | Low | Low | No understanding — expected for weak models |

The **bottom-right quadrant** is the most interesting finding this framework can produce: models that score well on task completion but poorly on IMQS are likely relying on training data or aggressive trial-and-error. These models would fail on novel tasks outside their training distribution.

---

## 5. Implementation Architecture

### 5.1 New Module: `saotri_bench/model_quality.py`

Contains all signal computation functions and the IMQS calculator.

```python
"""Internal Model Quality Score computation for Saotri Bench."""

from dataclasses import dataclass

@dataclass
class TrajectorySignals:
    """Tier 1 signals computed from run trajectory."""
    implicit_pass_rate: float
    oscillation_rate: float
    monotonicity_score: float
    stagnation_index: float
    convergence_velocity: float
    learning_curve_slope: float

@dataclass
class CodeQualitySignals:
    """Tier 2 signals computed from solution AST."""
    hard_coding_ratio: float
    hard_coded_values: list
    literal_density: float
    complexity_ratio: float
    domain_vocabulary_score: float

@dataclass
class EvolutionSignals:
    """Tier 3 signals computed from per-attempt snapshots."""
    avg_fix_precision: float
    avg_phase_churn: float
    adaptability: float

@dataclass
class PredictionSignals:
    """Prediction accuracy from predictive element."""
    per_phase_scores: list[float]
    avg_coverage_accuracy: float
    avg_rule_accuracy: float
    avg_calibration: float
    overall: float

@dataclass
class IMQSReport:
    """Complete Internal Model Quality Score report."""
    task_id: str
    agent_id: str
    imqs: float                      # 0-100 composite score

    trajectory: TrajectorySignals
    code_quality: CodeQualitySignals
    evolution: EvolutionSignals | None
    prediction: PredictionSignals | None
    generalization_score: float | None

    # Diagnostic flags
    is_reactive_patcher: bool        # High completion, low IMQS
    is_hard_coder: bool              # hard_coding_ratio > 0.3
    is_oscillator: bool              # oscillation_rate > 0.2
    has_genuine_model: bool          # IMQS > 70 AND completion > 50%
```

### 5.2 Changes to Existing Modules

**`saotri_bench/runner.py`:**
- Add solution snapshot saving (copy solution.py to `snapshots/attempt_{N}.py` before each evaluation)
- Add prediction protocol files at phase transitions (when `--predict` mode is enabled)

**`saotri_bench/metrics.py`:**
- Store per-attempt violation sets (for oscillation/stagnation analysis)
- Store per-attempt coverage values (for monotonicity/convergence)
- Store implicit evaluation coverage at each transition

**`agents/bench_runner.py`:**
- Handle prediction_request.json / prediction.json exchange
- Store prediction results for scoring

**`agents/agent.py`:**
- Add `generate_prediction()` method
- Add `_build_prediction_prompt()` method

**Dashboard (`dashboard/`):**
- Add IMQS column to model comparison table
- Add 2D scatter plot (Completion vs IMQS)
- Add per-model IMQS breakdown page

### 5.3 CLI Extensions

```
# Run with prediction enabled
saotri-bench run --model <model> --predict required

# Compute IMQS from existing reports
saotri-bench analyze-quality --report <path>
saotri-bench analyze-quality --all --reports-dir reports/

# Show 2D ranking
saotri-bench ranking --include-imqs
```

---

## 6. Implementation Phases

### Phase 1: Tier 1 Signals (Priority: HIGH, Effort: LOW)

**Scope:**
- Implement `TrajectorySignals` computation from existing report data
- Compute for all existing 115 benchmark results
- Add to dashboard as a new column
- No protocol changes needed

**Deliverables:**
- `saotri_bench/model_quality.py` with Tier 1 functions
- `saotri-bench analyze-quality` CLI command
- Dashboard column for Tier 1 IMQS

**Verification:** Run against existing data. Expect Claude Sonnet 4.6 (highest completion) to also score highest on implicit_pass_rate. Expect models with many error runs to show high stagnation.

### Phase 2: Tier 2 Signals (Priority: HIGH, Effort: LOW)

**Scope:**
- Add `CodeQualitySignals` (AST analysis of final solution.py)
- Integrate into IMQS composite
- Store in extended report format

**Deliverables:**
- AST analysis functions in `model_quality.py`
- `hard_coding_ratio` for all existing reports that have solution.py stored
- Updated IMQS computation

### Phase 3: Predictive Element (Priority: HIGH, Effort: MEDIUM)

**Scope:**
- Implement prediction protocol (prediction_request.json, prediction.json)
- Add prediction prompt to agent
- Implement prediction scoring
- Add `--predict` flag to runner
- Integrate prediction scores into IMQS

**Deliverables:**
- Protocol files and runner changes
- Agent prediction method
- PredictionSignals computation
- CLI flag `--predict off|passive|required`

### Phase 4: Tier 3 Signals + Solution Snapshots (Priority: MEDIUM, Effort: MEDIUM)

**Scope:**
- Add per-attempt solution snapshot saving
- Implement EvolutionSignals (fix precision, phase churn, strategy shifts)
- Requires re-running benchmarks with snapshots enabled

**Deliverables:**
- Snapshot infrastructure in runner
- AST diff analysis functions
- `--save-snapshots` flag

### Phase 5: Held-Out Generalization Tests (Priority: MEDIUM, Effort: MEDIUM)

**Scope:**
- Create held-out test cases for all tasks
- Add silent post-run evaluation against held-out tests
- Compute generalization_score

**Deliverables:**
- `HOLDOUT_CASES` in each task's tests.py
- Post-run evaluation in runner
- generalization_score in IMQS

### Phase 6: Dashboard & Reporting (Priority: LOW, Effort: MEDIUM)

**Scope:**
- 2D scatter plot (Completion vs IMQS) on dashboard
- Per-model IMQS breakdown page
- Diagnostic flags visualization
- Quadrant classification in model ranking

---

## 7. Relationship to Other Development Tasks

| Task | Relationship |
|------|-------------|
| **Solvability Validation Framework** | Independent but complementary. Solvability validates TASKS; IMQS validates MODELS. Both improve benchmark credibility. |
| **Audit Issue 3 (feedback enrichment)** | Enriched feedback (input/output pairs) will change IMQS patterns: models should show higher convergence velocity and lower oscillation. IMQS provides the measurement to validate that enrichment actually helps. |
| **Audit Issue 1-2 (network resilience)** | Infrastructure issues inflate stagnation_index and reduce apparent IMQS for affected models. Fix these first for clean IMQS data. |

---

## 8. Acceptance Criteria

### Tier 1 Signals
- [ ] Compute 6 trajectory signals from existing report data
- [ ] `saotri-bench analyze-quality --report <path>` produces JSON with all Tier 1 signals
- [ ] Implicit pass rate correctly computed from phase transition data
- [ ] Oscillation detection identifies pass-fail-pass cycles
- [ ] Claude Sonnet 4.6 (top performer) has highest Tier 1 IMQS among tested models

### Tier 2 Signals
- [ ] Hard-coding detection correctly flags solutions with test input values as literals
- [ ] Complexity ratio computed from AST branch count vs rule scope count
- [ ] Domain vocabulary overlap computed from identifiers vs task description terms

### Predictive Element
- [ ] `--predict required` mode: agent writes prediction.json at each phase transition
- [ ] Prediction scoring: coverage accuracy, rule accuracy, calibration computed
- [ ] Predictions are non-blocking: benchmark runs normally if agent fails to predict
- [ ] Backward compatible: `--predict off` (default) runs standard protocol

### Composite IMQS
- [ ] IMQS computed as weighted composite of available signal tiers
- [ ] Score on 0-100 scale with documented interpretation bands
- [ ] Diagnostic flags: is_reactive_patcher, is_hard_coder, is_oscillator, has_genuine_model
- [ ] Two-axis evaluation: Completion x IMQS scatter plot on dashboard

### Calibration
- [ ] Model with highest task completion also has highest IMQS (validates signals are not adversarial)
- [ ] Models with known issues (error status, timeout) score low IMQS
- [ ] IMQS distinguishes models beyond what completion score alone shows
