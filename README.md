# SaotriBench

<p align="center">
  <img src="assets/saotri-logo.png" alt="SaotriBench" width="400">
</p>

A coding benchmark for evaluating LLM agents on multi-phase programming tasks. Tests three critical capabilities:

- **Hidden requirement discovery** — inferring undisclosed constraints from structured feedback
- **Long-context retention** — maintaining state and hypotheses across many iterations  
- **Iterative refinement** — systematically improving solutions based on violation signals

```
+-----------------------------------------------------------+
|                    SaotriBench Flow                      |
+-----------------------------------------------------------+
|                                                           |
|  +-------+   +------------+   +--------+   +-----------+  |
|  | Agent |-->| solution.py|-->| Runner |-->| Evaluator |  |
|  +-------+   +------------+   +--------+   +-----------+  |
|      ^                            |              |        |
|      |                            |              v        |
|      |       +-------------+      |        +----------+   |
|      +-------|feedback.json|<-----+        |Test Cases|   |
|              +-------------+               | (hidden) |   |
|                    |                       +----------+   |
|                    v                                      |
|              +-------------+                              |
|              |  Violations |                              |
|              |  + Coverage |                              |
|              +-------------+                              |
|                                                           |
+-----------------------------------------------------------+
|  Phase 0     Phase 1     Phase 2     ...     Phase N      |
|  +------+    +------+    +------+            +------+     |
|  | Rule |    | Rule |    | Rule |            | Rule |     |
|  |  A   | +  |  A   | +  |  A   | + ... +    |  A   |     |
|  +------+    |  B   |    |  B   |            |  B   |     |
|              +------+    |  C   |            | ...  |     |
|                          +------+            |  Z   |     |
|                                              +------+     |
|  <------- Rules accumulate across phases ----------->     |
+----------------------------------------------------------+
```

## Core Concept

The agent receives only minimal initial information (input/output types, basic problem description). The actual correctness constraints are **not fully disclosed** — the agent must infer them from structured feedback on failed attempts.

Key properties:
- Agent starts with incomplete specification
- Hidden constraints are revealed indirectly through violation feedback
- Each phase introduces new undisclosed requirements that **break the previous solution**
- Success requires systematic exploration, not just code generation

## Installation

```bash
pip install -e .
```

After installation, the `saotri-bench` command becomes available. Alternatively, you can run without installing:

```bash
python -m saotri_bench.cli <command>
```

## Available Tasks

| Task | Difficulty | Phases | Description |
|------|-----------|--------|-------------|
| `task_00_fizzbuzz` | Easy | 3 | FizzBuzz with hidden divisor rules (`%7`, combinations) |
| `task_01_transform_list` | Easy | 3 | List transformation with evolving number handling |
| `task_02_merge_dicts` | Easy | 4 | Dict merge with type-aware conflict resolution |
| `task_03_validate_brackets` | Medium | 5 | Bracket validation with changing contract (bool → exception) |
| `task_04_sort_objects` | Medium | 6 | Object sorting with evolving key format and edge cases |
| `task_05_text_processor` | Medium | 7 | Text processing with unicode, quoting, and escape handling |
| `task_06_cache_eviction` | Medium | 8 | LRU cache with TTL, priority, and dirty-write tracking |
| `task_07_expression_parser` | Medium | 9 | Math expression parser with variables, implicit multiply, right-associativity |
| `task_08_access_control` | Medium | 10 | RBAC system with ownership, deny-priority, and role inheritance |
| `task_09_schedule_optimizer` | Hard | 12 | Task scheduler with dependencies, parallelism, and resource constraints |
| `task_10_data_pipeline` | Hard | 12 | Data transformation pipeline with filtering, aggregation, and joins |
| `task_11_version_resolver` | Hard | 15 | Semver dependency resolver with ranges, transitive deps, and conflicts |

## Quick Start

> All examples below use `saotri-bench` (requires `pip install -e .`).  
> Without installing, replace `saotri-bench` with `python -m saotri_bench.cli`.

### List available tasks

```bash
saotri-bench list --tasks-dir tasks
```

### Validate a task

```bash
saotri-bench validate --task tasks/task_00_fizzbuzz
```

### Run a task (interactive mode — for agents)

```bash
saotri-bench run --task tasks/task_00_fizzbuzz --workspace ./workspace --poll-interval 2
```

### Run a task (single evaluation)

```bash
saotri-bench run --task tasks/task_00_fizzbuzz --workspace ./workspace --single
```

## How It Works

### For agents (automated)

1. The runner starts and creates the workspace with `problem.md`, `task.json`, `phase.json`, and an empty `solution.py`
2. The agent reads `problem.md` to understand the task and `phase.json` to see current rules
3. The agent writes its solution to `workspace/solution.py`
4. The runner detects the file change and evaluates the solution
5. The runner writes structured feedback to `workspace/feedback.json`
6. The agent reads feedback, identifies violations, and refines its solution
7. Steps 3–6 repeat until all phases pass or attempt limits are reached

### For manual testing

You can simulate an agent by manually editing `workspace/solution.py` while the runner is active:

```bash
# Terminal 1: Start the runner
saotri-bench run --task tasks/task_00_fizzbuzz --workspace ./workspace --poll-interval 2

# Terminal 2: Write your solution
# Edit workspace/solution.py with your code
# The runner will auto-detect changes and evaluate
```

**Stopping the runner:**
- Type `q` + Enter in the runner terminal
- Or press `Ctrl+C`

### Example walkthrough (task_00_fizzbuzz)

**Phase 0** — You read `problem.md` and write classic FizzBuzz:

```python
def fizzbuzz(n):
    if n % 15 == 0: return "FizzBuzz"
    if n % 3 == 0: return "Fizz"
    if n % 5 == 0: return "Buzz"
    return str(n)
```

Feedback: `status: "valid"` — Phase 0 passes, runner advances to Phase 1.

**Phase 1** — Implicit evaluation runs. Feedback shows violations:
```json
{"rule_id": "correct_output", "scope": "divisible_by_7", "count": 3}
```

You infer: there's a hidden rule for multiples of 7. You add `"Bazz"` handling:

```python
def fizzbuzz(n):
    result = ""
    if n % 3 == 0: result += "Fizz"
    if n % 5 == 0: result += "Buzz"
    if n % 7 == 0: result += "Bazz"
    return result if result else str(n)
```

Phase 1 passes. Phase 2 reveals combination violations (`divisible_by_21`, `divisible_by_35`, `divisible_by_105`). Your Phase 1 solution already handles these — Phase 2 passes too. Task complete!

## Workspace Protocol

When running a task, the runner creates a workspace directory with:

| File | Description |
|------|-------------|
| `problem.md` | Problem description (agent-visible) |
| `task.json` | Task metadata, interface, and limits |
| `phase.json` | Current phase info, rules, and previous feedback |
| `solution.py` | Agent writes solution here (runner watches for changes) |
| `feedback.json` | Evaluation feedback after each attempt |
| `report.json` | Final metrics report (written on session end) |

> **Note:** The `workspace/` directory is gitignored. Each run starts fresh — delete old workspace files before starting a new session if needed.

## Feedback Format

Each evaluation returns structured JSON feedback:

```json
{
  "phase_id": 1,
  "attempt_id": 5,
  "status": "partially_valid",
  "status_reason": "Fails checks: no_mutation",
  "violations": [
    {"rule_id": "no_mutation", "scope": "direct", "count": 2}
  ],
  "summary": {
    "rules_total": 3,
    "rules_passed": 2,
    "rules_failed": 1,
    "coverage": 0.85
  },
  "delta": {
    "coverage_change": 0.15,
    "new_failures": [],
    "fixed_failures": ["correct_output"]
  }
}
```

**Status values:**
- `valid` — all rules pass, phase advances
- `partially_valid` — some rules pass, some fail
- `invalid` — no rules pass
- `error` — code failed to execute (syntax error, timeout, import violation)

**Violation scopes** hint at what went wrong without revealing test cases. For example, `"scope": "divisible_by_7"` tells the agent that something related to sevens is failing.

## Task Structure

Each task is a directory with 4 files:

```
tasks/task_00_fizzbuzz/
├── task.yaml       # Task metadata, phases, rules, limits
├── problem.md      # Agent-visible problem description
├── evaluator.py    # Evaluation logic (check_* methods)
└── tests.py        # Test cases with expected values (hidden from agent)
```

## Creating New Tasks

1. Create a new directory under `tasks/` (convention: `task_XX_name`)
2. Define `task.yaml` with phases and rules
3. Write `problem.md` (what the agent sees — keep it minimal for harder tasks)
4. Implement `evaluator.py` with a class `Evaluator(BaseEvaluator)` and `check_{rule_id}` methods
5. Create `tests.py` with a `TEST_CASES` list of `TestCase` objects
6. Validate with `saotri-bench validate --task tasks/your_task`

### Design principles

- **Each phase must break the previous solution** — a naive solution passing Phase N should fail on Phase N+1
- **Violation scopes are hints, not answers** — they tell the agent *what area* failed, not *what the answer is*
- **Expected values must be consistent across all phases** — the evaluator runs ALL prior-phase tests on the current solution
- **Easy tasks** include examples in `problem.md`; **harder tasks** give only the function signature

### Example task.yaml

```yaml
id: "task_00_fizzbuzz"
name: "FizzBuzz Extended"
description: "Implement FizzBuzz with evolving divisor rules"
difficulty: "easy"

interface:
  function_name: "fizzbuzz"
  signature: "def fizzbuzz(n: int) -> str"
  allowed_imports: []

execution:
  timeout_seconds: 10

phases:
  - id: 0
    description: "Classic FizzBuzz"
    rules:
      - id: "correct_output"
        description: "Output matches expected string"
        scopes: ["divisible_by_3", "divisible_by_5", "divisible_by_15", "plain_number"]

  - id: 1
    description: "New divisor rule"
    rules:
      - id: "correct_output"
        description: "Output matches expected string"
        scopes: ["divisible_by_3", "divisible_by_5", "divisible_by_15", "plain_number", "divisible_by_7"]
      - id: "correct_type"
        description: "Return value must be a string"
        scopes: ["type_check"]

limits:
  max_attempts_per_phase: 5
  max_total_attempts: 15
```

## Sandbox & Security

Solutions run in a sandboxed environment:
- **Restricted imports** — only explicitly allowed modules can be imported
- **Restricted builtins** — dangerous functions (`eval`, `exec`, `open`, `__import__`) are blocked or controlled
- **Timeout enforcement** — code execution is killed after the configured timeout
- **Input immutability** — evaluators use deep copies to prevent test case corruption

## Difficulty Tiers

| Tier | Phases | Description |
|------|--------|-------------|
| Easy | 3–5 | Basic transformations, simple rules |
| Medium | 5–15 | Moderate complexity, multiple interacting rules |
| Hard | 16–30 | Complex algorithms, many edge cases |
| Expert | 31–50 | Deep challenges, extensive hidden states |

## CLI Reference

```bash
# List all tasks
saotri-bench list [--tasks-dir PATH] [--json]

# Validate a task definition
saotri-bench validate --task PATH

# Run interactively (watch for file changes)
saotri-bench run --task PATH [--workspace PATH] [--agent-id ID] [--poll-interval SEC]

# Run single evaluation
saotri-bench run --task PATH --workspace PATH --single
```

## LLM Agent Benchmark

The `agents/` module provides automated benchmarking of LLM models against SaotriBench tasks via [OpenRouter](https://openrouter.ai/).

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set your OpenRouter API key
cp agents/.env.example agents/.env
# edit agents/.env with your key
```

### Run benchmark

```bash
# Run all models on all tasks (sequential)
python -m agents.run_benchmark

# Run a specific model tier on a specific task
python -m agents.run_benchmark --tier strong --task task_00_fizzbuzz

# Run selected models
python -m agents.run_benchmark --models claude-opus,gpt,deepseek

# Run models in parallel (up to 4 at a time)
python -m agents.run_benchmark --models claude-opus,gpt,deepseek --parallel 4

# Run all models in parallel
python -m agents.run_benchmark --parallel 5

# List configured models
python -m agents.run_benchmark --list-models
```

### Configured models

| Tier | Model | OpenRouter ID |
|------|-------|---------------|
| `medium` | Llama 3.3 70B | `meta-llama/llama-3.3-70b-instruct` |
| `claude-opus` | Claude Opus 4.6 | `anthropic/claude-opus-4.6` |
| `kimi` | Kimi K2.5 | `moonshotai/kimi-k2.5` |
| `gpt` | GPT-5.2 Codex | `openai/gpt-5.2-codex` |
| `minimax` | MiniMax M2.5 | `minimax/minimax-m2.5` |
| `glm` | GLM 5 | `z-ai/glm-5` |
| `claude-sonnet` | Claude Sonnet 4.6 | `anthropic/claude-sonnet-4.6` |
| `gemini-3.1` | Gemini 3.1 Pro | `google/gemini-3.1-pro-preview` |
| `deepseek` | DeepSeek V3.2 | `deepseek/deepseek-v3.2` |
| `grok` | Grok 4.1 Fast | `x-ai/grok-4.1-fast` |
| `trinity` | Trinity Large | `arcee-ai/trinity-large-preview` |

### Benchmark Results (Strong Tier, Feb 2026)

12 tasks, 94 total phases. Each model runs all tasks sequentially with up to 5-8 refinement attempts per phase.

#### Overall Ranking

| # | Model | Tasks Passed | Phases Completed | Phase % |
|---|-------|-------------|-----------------|---------|
| 1 | **Claude Opus 4.6** | **6/12** | **53/94** | **56%** |
| 2 | GPT-5.2 Codex | 4/12 | 45/94 | 48% |
| 3 | GLM 5 | 4/12 | 41/94 | 44% |
| 4 | MiniMax M2.5 | 4/12 | 40/94 | 43% |
| 5 | Kimi K2.5 | 4/12 | 37/94 | 39% |

#### Per-Task Results (phases completed / total phases)

| Task | Difficulty | Claude Opus | GPT-5.2 | GLM 5 | MiniMax | Kimi K2.5 |
|------|-----------|-------------|---------|-------|---------|-----------|
| FizzBuzz | Easy | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| Transform List | Easy | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| Merge Dicts | Easy | **4/4** | 3/4 | 3/4 | 3/4 | 3/4 |
| Validate Brackets | Medium | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| Sort Objects | Medium | **6/6** | 4/6 | **6/6** | 3/6 | 2/6 |
| Text Processor | Medium | **4/7** | 3/7 | 3/7 | 2/7 | 2/7 |
| Cache Eviction | Medium | **4/8** | **4/8** | 2/8 | 2/8 | 2/8 |
| Expression Parser | Medium | **9/9** | **9/9** | 7/9 | **9/9** | **9/9** |
| Access Control | Medium | 2/10 | **4/10** | 3/10 | **4/10** | 3/10 |
| Schedule Optimizer | Hard | 2/12 | 2/12 | 1/12 | 2/12 | 1/12 |
| Data Pipeline | Hard | 3/12 | 3/12 | 3/12 | 2/12 | 2/12 |
| Version Resolver | Hard | **8/15** | 2/15 | 2/15 | 2/15 | 2/15 |

**Bold** = best result for that task.

#### Key Observations

- **Easy tasks (3-4 phases):** All models pass FizzBuzz, Transform List, and Validate Brackets. These serve as baseline sanity checks.
- **Medium tasks (5-10 phases):** Significant differentiation begins. Expression Parser is the standout — 4 of 6 models achieve 9/9 phases, indicating strong recursive parsing ability across frontier models.
- **Hard tasks (12-15 phases):** All models struggle. Only Claude Opus 4.6 reaches 8/15 on Version Resolver; all others plateau at 2-3 phases.
- **Common failure points:** `list_merge` in Merge Dicts (Phase 3), `escape_handling` in Text Processor, `ttl_expiry` in Cache Eviction, `transitive` dependencies in Version Resolver.
- **EmptyResponseError** is the dominant infrastructure issue — models hit `max_tokens=4096` on complex tasks. See [TECHNICAL_ERRORS.md](TECHNICAL_ERRORS.md) for details.

Reports are saved to `reports/` as JSON files. See [`TECHNICAL_ERRORS.md`](TECHNICAL_ERRORS.md) for infrastructure errors and [`BENCHMARK_ANALYSIS.md`](BENCHMARK_ANALYSIS.md) for quality analysis.

See [`agents/README.md`](agents/README.md) for full documentation.

### Live Dashboard

A real-time web dashboard shows benchmark progress as results come in:

```bash
python serve_dashboard.py
# Opens at http://localhost:8050
```

The dashboard auto-refreshes every 10 seconds and displays:
1. **Completion Summary** — models ranked by pass rate with token/duration stats
2. **Pass/Fail Matrix** — every task x model result at a glance
3. **By Difficulty** — easy/medium/hard breakdown per model

To use a different port:

```bash
python serve_dashboard.py --port 9000
```

## Benchmark Quality Analysis

### Does SaotriBench measure "internal model building"?

The benchmark's stated goal is to determine whether LLM agents build internal models of projects — inferring hidden structure from feedback rather than just pattern-matching. Results from 7 strong-tier models (Feb 2026) suggest:

**What the benchmark successfully measures:**

1. **Hidden requirement discovery (Phases 0-2 across all tasks):** All models demonstrate the ability to read violation feedback and adjust code accordingly. The Phase 0→1 transition reliably differentiates models — weaker models fail to infer the meaning of scopes like `divisible_by_7`, while stronger ones update their mental model of the problem.

2. **Iterative refinement under constraints:** The benchmark clearly separates models that can iteratively refine from those that thrash. Claude Opus 4.6 achieves 8/15 on Version Resolver by systematically addressing violations, while most models plateau at 2/15 — unable to maintain all prior constraints while adding new ones.

3. **Phase accumulation stress-testing:** The core design — rules accumulate across phases, so Phase N solutions must satisfy all Phase 0..N-1 rules — is effective. This is where models break: they can add new behavior but often regress on previously-passing tests.

**Where results are less conclusive:**

1. **Hard tasks may test algorithmic knowledge more than model-building.** Version Resolver Phase 2 (`transitive` dependencies) blocks every model except Claude Opus. This requires implementing a specific graph algorithm, not inferring requirements from feedback. Similarly, Schedule Optimizer Phase 2 (`parallelism`) requires topological sort knowledge.

2. **The `max_tokens` ceiling creates a confound.** 5 of 7 models hit EmptyResponseError on complex tasks, terminating them prematurely. It's impossible to know if GLM 5 would have passed Expression Parser Phase 8 without the token limit (it achieved 9/9 in one run but 7/9 when constrained). The benchmark may be measuring token efficiency as much as reasoning ability.

3. **Medium tasks show ceiling effects.** Expression Parser is fully solved by 4 of 6 models (9/9), yet the task has 9 phases — this suggests the phases aren't calibrated to differentiate top-tier models on this task type.

**Relevance to the "internal model" question:**

The benchmark provides *indirect* evidence. Models that score higher demonstrate behavior consistent with maintaining an internal model:
- They don't regress when adding new features (phase accumulation test)
- They infer correct semantics from scope names (`divisible_by_7` → "add Bazz for multiples of 7")
- They maintain architectural coherence across refinements

However, the benchmark cannot definitively prove internal model building vs. sophisticated pattern matching. A model could pass by:
- Memorizing common patterns (FizzBuzz variants, bracket validators)
- Using the violation scope name as a direct hint (the scope name often reveals the solution)
- Applying generic "add a conditional" strategies without deeper understanding

**Recommendations for improving benchmark signal:**
1. **Increase `max_tokens` to 8192+** for all models to remove the token ceiling confound
2. **Add obfuscated scope names** — use codes like `violation_A3` instead of `divisible_by_7` to test whether models can infer meaning from test case patterns alone
3. **Add regression-detection phases** — phases that don't add new rules but test whether the model's solution is robust to edge cases of existing rules
4. **Run multiple trials per model** to account for LLM non-determinism (GLM 5 scored 9/9 and 7/9 on the same task across two runs)

## The Name: SAOTRI

**SAOTRI** is an acronym that captures the core dimensions of the benchmark evaluation model:

| Letter | Stands for | Description |
|--------|-----------|-------------|
| **S** | Hidden **S**tate | The concealed environment state — infrastructure, load, constraints invisible to the agent |
| **A** | **A**ctions | The agent's actions, manifested as code patches submitted each attempt |
| **O** | **O**bservations | What the agent perceives — logs, metrics, error signals, structured feedback |
| **T** | Non-stationary **T**ransitions | The environment dynamics that shift across phases — rules accumulate, constraints tighten |
| **R** | **R**esilience function | The reward signal measuring solution robustness and survival under evolving requirements |
| **I** | **I**nvariants | The safety and correctness guarantees — state integrity, data safety, behavioral contracts |

Learn more at [saotri.com](https://saotri.com)

## License

MIT
