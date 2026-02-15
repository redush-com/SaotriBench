# SaotriBench Quality Analysis

Analysis of benchmark quality based on strong-tier results from 7 frontier models (Feb 2026).

## Core Question

> Does SaotriBench determine if LLM agents build internal models of projects?

**Short answer:** Partially. The benchmark provides strong signal for **iterative refinement capability** and **violation-driven learning**, but cannot conclusively distinguish genuine internal model building from sophisticated scope-hint pattern matching.

## What the Benchmark Actually Tests

### Phase 0-2: Discovery and Basic Inference
- **Violation scope interpretation** — reading hints like `"divisible_by_7"` and inferring logic
- **Basic iterative refinement** — reading feedback, making targeted adjustments
- All strong models pass these consistently (100% pass rate on easy tasks)

### Phase 3+: Accumulation Under Constraint
- **Phase accumulation** — maintaining ALL prior-phase rules while adding new requirements
- **Implicit evaluation** — adapting to violations on never-seen test cases
- **Multi-rule interaction** — handling rules that conflict or constrain each other
- This is where models diverge significantly

### Hard Tasks (Phase 8+): Algorithmic + Inferential
- **Deep algorithm knowledge** — topological sort, semver resolution, SAT-like backtracking
- **Long-context coherence** — maintaining 5000+ char solutions across 10+ refinement cycles
- No model exceeds 60% completion; most plateau at 15-25%

## Key Finding: Expression Parser vs. Access Control

The most revealing comparison in the benchmark:

**Expression Parser (9/9 by 4 of 6 models):**
- Scope names are highly informative: `"precedence"`, `"unary_operator"`, `"right_associativity"` map directly to features
- Each phase adds exactly one composable feature to a recursive descent parser
- Test scopes are isolated — Phase 8 failures don't impact Phase 7 code

**Access Control (2-4/10 for all models):**
- Scope names are semantically ambiguous: `"deny_priority"` doesn't specify precedence rules
- Phases introduce interacting constraints (role hierarchy + deny rules + temporal conditions)
- Output format evolution (bool → dict with reason/matched_rule) breaks working solutions
- Orthogonal `no_mutation` checks confound the actual access logic testing

**Implication:** Tasks where scope names directly encode the solution (Expression Parser) show ceiling effects. Tasks where inference is genuinely required (Access Control) show significant differentiation.

## Evidence FOR Internal Model Building

1. **Consistent failure points across models:** All models fail Version Resolver Phase 2 (transitive deps) and Text Processor Phase 3+ (escape handling). This indicates phase difficulty is calibrated, not random.

2. **Claude Opus 4.6's Version Resolver (8/15):** Uniquely strong performance requires maintaining a coherent semver resolution algorithm across 8 phase transitions — consistent with genuine model building.

3. **Regression patterns:** Models that pass Phase N sometimes catastrophically fail Phase N+1 (coverage drops from 100% to 0%). This indicates the new phase genuinely disrupts their working model.

4. **Token usage as model complexity proxy:** Models with larger token budgets (Gemini 3 Pro at 8192 tokens) avoid infrastructure failures, suggesting the limitation is contextual — the model needs space to maintain its state representation.

## Evidence AGAINST Internal Model Building

1. **Scope names do too much work:** `"divisible_by_7"` practically reveals the solution. The agent doesn't need an internal model — it needs reading comprehension. This is why Expression Parser achieves 9/9: each scope name IS the implementation requirement.

2. **Hard task failures may be algorithmic, not inferential:** Version Resolver Phase 2 (transitive dependencies) requires graph algorithms. Models fail here because they don't know the algorithm, not because they can't maintain an internal model.

3. **No model demonstrates surprising generalization:** All models follow the same pattern — pass easy tasks, struggle on medium tasks at specific phases, fail hard tasks. No model "figures out" a hard task in an unexpected way that would suggest genuine internal modeling.

4. **Infrastructure confounds:** The `max_tokens=4096` limit kills models on complex tasks. Failures on Schedule Optimizer and Data Pipeline are often EmptyResponseErrors, not reasoning failures.

## Benchmark Quality Assessment

### Strengths

| Aspect | Rating | Notes |
|--------|--------|-------|
| Phase accumulation design | Strong | Genuinely tests non-regression |
| Violation feedback format | Strong | Structured, parseable, informative |
| Task difficulty gradient | Good | Easy/Medium/Hard tiers work as intended |
| Reproducibility | Moderate | JSON reports enable comparison, but run-to-run variance exists |
| Model differentiation | Good | Clear separation between Claude Opus and the pack |

### Weaknesses

| Aspect | Rating | Notes |
|--------|--------|-------|
| Scope name leakage | Significant | Scope names often reveal the solution directly |
| Token limit impact | Significant | 4096 max_tokens causes artificial failures on hard tasks |
| Algorithm vs. inference confound | Moderate | Hard tasks test algorithm recall, not just model building |
| Single-run scoring | Moderate | Non-determinism means results vary 10-20% between runs |
| Limited hard task penetration | Moderate | <25% completion means low signal in the hard tier |

### Task-Level Quality

| Task | Quality | Notes |
|------|---------|-------|
| FizzBuzz | Baseline | Sanity check only — all models pass |
| Transform List | Baseline | Sanity check only — all models pass |
| Merge Dicts | Good | Phase 3 (list_merge) creates real differentiation |
| Validate Brackets | Low signal | All models pass 5/5 — ceiling effect |
| Sort Objects | Good | Tests mutation safety + complex sorting |
| Text Processor | Good | Unicode + escaping creates genuine difficulty |
| Cache Eviction | Good | TTL without `time` import is a clever constraint |
| Expression Parser | Ceiling effect | 4/6 models achieve 9/9 — too easy for frontier models |
| Access Control | Good | Best differentiator in medium tier |
| Schedule Optimizer | Infrastructure-limited | Token limit kills most runs before testing reasoning |
| Data Pipeline | Infrastructure-limited | Same token limit issue |
| Version Resolver | Best hard task | Only task where 1 model significantly outperforms others |

## Recommendations

### Critical (Affects Validity)
1. **Increase `max_tokens` to 8192** for all strong models. The 4096 limit creates artificial failures unrelated to model quality.
2. **Use opaque scope names** for hard tasks (e.g., `violation_A3` instead of `divisible_by_7`) to force genuine inference.

### Important (Improves Signal)
3. **Add regression-only phases** — phases with no new rules but new edge cases for existing rules. Tests robustness, not feature addition.
4. **Separate algorithm and inference testing** — provide algorithm templates for hard tasks, then test model building on policy/rules aspects.
5. **Run best-of-3** — single runs have 10-20% variance. Best-of-3 with median scoring would increase reliability.

### Nice to Have
6. **Store detailed errors in JSON reports** — currently only in console output.
7. **Add conversation compression** — reduce context size for long tasks.
8. **Calibrate Expression Parser and Validate Brackets** — add harder phases to avoid ceiling effects.

## Conclusion

SaotriBench is a **well-designed benchmark for iterative refinement capability** with genuine differentiation between frontier models. However, its ability to specifically test "internal model building" is limited by:

1. Scope names that leak solution requirements
2. Hard tasks that conflate algorithm knowledge with inference ability
3. Infrastructure constraints that truncate complex reasoning

The benchmark answers: **"Can LLM agents iteratively refine solutions under accumulating constraints?"** — and the answer is "yes, with significant capability differences."

It partially answers: **"Do LLM agents build internal models of projects?"** — the phase accumulation mechanism creates conditions where models MUST maintain coherent state, and the results (especially Claude Opus 4.6's 8/15 on Version Resolver) suggest some models do better than others at this. But the benchmark cannot rule out that strong performance comes from better scope-hint interpretation rather than genuine model building.

**Overall benchmark grade: B+** — good task design, needs infrastructure fixes and scope name opacity to reach its full potential as a model-building test.
