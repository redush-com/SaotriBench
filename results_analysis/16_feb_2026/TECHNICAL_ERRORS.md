# SaotriBench Technical Errors Report

Infrastructure and technical errors observed during strong-tier model benchmarking (February 15-16, 2026).

## Error Summary

| Error Type | Occurrences | Models Affected |
|-----------|-------------|-----------------|
| Empty Response (token limit) | 9 | GPT-5.2 Codex, Kimi K2.5, GLM 5, MiniMax M2.5 |
| Import Violations | 4 | Claude Opus 4.6, MiniMax M2.5 |
| Syntax Errors | 5 | GPT-5.2 Codex, Kimi K2.5, GLM 5 |
| Extreme Latency | 1 | Grok 4 |

## 1. Empty Response Errors (finish_reason=length)

The most common infrastructure failure. Models hit the `max_tokens` limit (4096), causing the API to return empty content after exhausting retries (MAX_EMPTY_RETRIES=2). This terminates the task with `AGENT ERROR`.

**Root cause:** As conversation history grows (problem description + previous attempts + feedback), the prompt consumes most of the token budget, leaving insufficient space for the response. Complex tasks with long solutions (5000+ chars) are most affected.

| Model | Task | Phase | Notes |
|-------|------|-------|-------|
| GPT-5.2 Codex | task_02_merge_dicts | Phase 3 | Solution ~1366 chars, context overflow |
| GPT-5.2 Codex | task_04_sort_objects | Phase 4 | Solution ~1050 chars, 13 violations in response |
| GPT-5.2 Codex | task_09_schedule_optimizer | Phase 2 | Solution ~5302 chars, context overflow |
| Kimi K2.5 | task_04_sort_objects | Phase 2 | Terminated at attempt 2 |
| Kimi K2.5 | task_06_cache_eviction | Phase 2 | Terminated after 4 attempts |
| Kimi K2.5 | task_11_version_resolver | Phase 2 | Solution ~5600 chars |
| GLM 5 | task_04_sort_objects | Phase 4 | Solution ~1580 chars |
| GLM 5 | task_05_text_processor | Phase 3 | Solution ~1740 chars |
| GLM 5 | task_09_schedule_optimizer | Phase 1 | Terminated at attempt 2 |
| GLM 5 | task_10_data_pipeline | Phase 3 | Solution ~8452 chars |
| GLM 5 | task_11_version_resolver | Phase 2 | Solution ~9995 chars |
| MiniMax M2.5 | task_07_expression_parser | Phase 0 | Early in run, recovered |

**Recommendation:** Increase `max_tokens` to 8192+ for strong models (Gemini 3 Pro already uses 8192 and had zero empty response errors). Alternatively, implement conversation history compression when approaching token limits.

## 2. Import Constraint Violations

Models attempted to use Python imports not in the task's `allowed_imports` list. The sandbox correctly blocked these.

| Model | Task | Attempted Import | Allowed Imports |
|-------|------|-----------------|-----------------|
| Claude Opus 4.6 | task_08_access_control | `re` | `['collections']` |
| Claude Opus 4.6 | task_08_access_control | `copy` | `['collections']` |
| Claude Opus 4.6 | task_10_data_pipeline | `copy` | `['re', 'collections']` |
| MiniMax M2.5 | task_06_cache_eviction | `time` | `['collections']` |

**Assessment:** These are model behavior errors, not infrastructure bugs. The sandbox correctly enforces constraints. Models should read the `allowed_imports` from the task specification more carefully.

## 3. Syntax Errors in Generated Code

Models occasionally produced syntactically invalid Python, usually when generating long solutions near the token limit.

| Model | Task | Phase | Error |
|-------|------|-------|-------|
| GPT-5.2 Codex | task_08_access_control | Phase 4 | `unterminated string literal (line 67)` |
| GPT-5.2 Codex | task_10_data_pipeline | Phase 3 | `unterminated string literal (line 67)` |
| GPT-5.2 Codex | task_10_data_pipeline | Phase 3 | `invalid syntax (line 144)` |
| Kimi K2.5 | task_07_expression_parser | Phase 8 | `'[' was never closed (line 37)` |
| GLM 5 | task_07_expression_parser | Phase 8 | `invalid syntax (line 65)` |

**Note:** The recurring `line 67` truncation in GPT-5.2 Codex strongly suggests token-limit-related truncation of the code block, reinforcing the `max_tokens` issue above.

## 4. Grok 4 Extreme Latency

Grok 4 (`x-ai/grok-4`) exhibited extreme API latency through OpenRouter, making benchmarking impractical.

| Metric | Value |
|--------|-------|
| Average time per API call | ~6 minutes |
| Time for FizzBuzz (1 task) | 46.8 minutes |
| Total tokens for FizzBuzz | 127,832 |
| Tasks completed | 1 of 12 |
| Phases passed | 1 of 3 (Phase 0 only) |

**Root cause:** Grok 4 uses extended thinking/reasoning, producing extremely long internal chains before responding. Through OpenRouter's API, this manifests as very long response times with massive token consumption.

**Impact:** At ~47 minutes per task, completing all 12 tasks would take ~9.4 hours. Given it failed even the easiest task (FizzBuzz Phase 1), the model appears incompatible with this benchmark format through OpenRouter.

## 5. Non-Determinism Between Runs

Multiple runs of the same model on the same task produced different results:

| Model | Task | Run 1 | Run 2 |
|-------|------|-------|-------|
| GLM 5 | task_07_expression_parser | 9/9 PASS | 7/9 FAIL |
| GLM 5 | task_04_sort_objects | 4/6 ERROR | 6/6 PASS |
| GPT-5.2 Codex | task_04_sort_objects | 6/6 PASS | 4/6 ERROR |

**Assessment:** This is expected with temperature=0.1 and non-deterministic API responses. Results should be interpreted as single-run snapshots, not deterministic scores. Multiple runs would be needed for statistical confidence.

## Infrastructure Recommendations

1. **Increase max_tokens to 8192** for all strong models (currently 4096 for most)
2. **Add conversation compression** to keep prompt size manageable for long tasks
3. **Store detailed error info in JSON reports** (currently only in console output)
4. **Add configurable API timeout** for slow models like Grok 4
5. **Consider best-of-N scoring** to account for non-determinism
