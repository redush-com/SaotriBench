# Technical Issues from Audit 2026-02-21 (#2)

**Source:** `benchmark_audit/2026-02-21_2_audit.md`
**Date:** 2026-02-22
**Status:** Open

---

## Issue 1: No Retry on Network Errors in LLM Client

**Severity:** P0
**File:** `agents/llm_client.py` (lines 119-128)
**Verified:** Yes — confirmed in code

### Problem
The `OpenRouterClient._request()` method only catches `httpx.TimeoutException`. Network errors such as `httpx.RemoteProtocolError` (server disconnected), `httpx.ConnectError`, and `httpx.ReadError` are not caught and propagate as unrecoverable crashes, immediately terminating the benchmark run for that model.

The existing retry logic (lines 76-89) only retries on `EmptyResponseError`. Network-level failures bypass it entirely.

```python
# Current code — only catches timeout, not connection errors
try:
    with httpx.Client(timeout=request_timeout) as client:
        response = client.post(self.BASE_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
except httpx.TimeoutException:
    raise ResponseTimeoutError(...)
# httpx.RemoteProtocolError, httpx.ConnectError — NOT caught → crash
```

### Evidence from Audit
- 8+ instances of `RemoteProtocolError: Server disconnected`
- 18 runs ended with `error` status (16% of all runs)
- Disproportionately affected slow providers (Gemini 3.1 Pro: 5 errors, Kimi K2.5)

### Proposed Fix
Extend the retry loop in `chat()` to also catch transient `httpx` network errors with exponential backoff:

```python
RETRYABLE_ERRORS = (EmptyResponseError, httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError)

for attempt in range(1 + self.MAX_RETRIES):
    if attempt > 0:
        delay = self.RETRY_BACKOFF_BASE ** attempt
        time.sleep(delay)
    try:
        return self._request(model, messages)
    except RETRYABLE_ERRORS as e:
        last_error = e
        continue
```

### Acceptance Criteria
- [ ] `httpx.ConnectError`, `httpx.RemoteProtocolError`, `httpx.ReadError` are caught and retried with backoff
- [ ] Non-retryable errors (4xx status codes, auth failures) still fail immediately
- [ ] Retry count and delay are logged for observability

---

## Issue 2: New httpx.Client Created Per Request (No Connection Reuse)

**Severity:** P1
**File:** `agents/llm_client.py` (line 120)
**Verified:** Yes — confirmed in code

### Problem
Every API call creates a new `httpx.Client` instance inside a `with` block, discarding it after one request. This prevents TCP connection reuse, HTTP Keep-Alive, and connection pooling.

```python
# Current: new client per request
with httpx.Client(timeout=request_timeout) as client:
    response = client.post(self.BASE_URL, json=payload, headers=headers)
```

Under parallel execution (14 models simultaneously), this causes excessive TCP connection churn, contributing to the `RemoteProtocolError` disconnections observed in the audit.

### Proposed Fix
Create the `httpx.Client` once in `__init__` and reuse it across requests. Use a connection pool for parallel runs:

```python
def __init__(self, ...):
    self._client = httpx.Client(
        timeout=self.timeout,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
```

### Acceptance Criteria
- [ ] `httpx.Client` is reused across requests within the same `OpenRouterClient` instance
- [ ] Connection pool limits are configured
- [ ] Per-request timeout can still be overridden (model-specific timeouts)

---

## Issue 3: Task Feedback Signals Insufficient for "Easy" Tasks

**Severity:** P1
**Files:** `tasks/task_01_transform_list/tests.py`, `tasks/task_02_merge_dicts/tests.py`
**Verified:** Yes — confirmed in code and task test files

### Problem
Tasks labeled "easy" (task_01, task_02) have 0% completion across all 14 models, including the top performer (Claude Opus 4.6). The feedback provided to agents contains only scope names (e.g., `negative_handling`, `numeric_conflict`) without input/output examples.

**task_01_transform_list:**
- Phase 1 violation `negative_handling` — agents must infer `abs()` is needed before doubling, but feedback only says the test named "negative_handling" failed
- Phase 2 violation `cap_overflow` — agents must discover the output cap value (100) with no numeric hints

**task_02_merge_dicts:**
- Phase 1 violations `numeric_conflict` / `string_conflict` — agents must infer "numbers sum, strings concatenate" merge semantics from scope names alone
- This is semantic inference, not discoverable from the violation name

**Contrast with successful tasks:**
- task_00_fizzbuzz: violation `divisible_by_7` directly hints at the solution → 36% completion
- task_03_validate_brackets: `error_position` maps to specific code changes → 92% completion

### Proposed Fix (per audit section 8.2)
Enrich feedback for failing tasks by including input/output example pairs in violation details. This preserves the hidden-requirement philosophy while making feedback actionable:

| Task | Current Feedback | Suggested Enhancement |
|------|-----------------|----------------------|
| task_01 | `negative_handling: FAIL` | Add example: `input=[-3] → expected=[6]` |
| task_02 | `numeric_conflict: FAIL` | Add example: `a={x:10}, b={x:5} → expected={x:15}` |

### Acceptance Criteria
- [ ] task_01 feedback includes at least one input/output example per failing scope
- [ ] task_02 feedback includes at least one input/output example per failing scope
- [ ] Examples are added to the feedback structure (not the prompt), preserving hidden-requirement design
- [ ] Re-run at least 3 strong models to verify improved completion rates

---

## Issue 4: task_06_cache_eviction Phase 2 Difficulty Cliff

**Severity:** P2
**File:** `tasks/task_06_cache_eviction/tests.py`
**Verified:** Yes — confirmed in code

### Problem
All 13 models that reached task_06 get stuck at phase 2 (`ttl_expiry` — 54 violations). Phase 2 requires models to reverse-engineer TTL mechanics (expiry_time = put_timestamp + ttl) from only the scope name `ttl_expiry`.

The test expects models to understand timestamp-based TTL logic, but the feedback doesn't include timing info.

### Proposed Fix
Include timing context in ttl_expiry feedback: `key="x" expired at t=5, accessed at t=6`.

### Acceptance Criteria
- [ ] Phase 2 feedback includes timing context for ttl_expiry violations
- [ ] Verify at least 1 strong model can advance past phase 2 with enriched feedback

---

## Issue 5: Difficulty Labels Mismatch

**Severity:** P2
**Files:** `tasks/task_01_transform_list/task.yaml`, `tasks/task_02_merge_dicts/task.yaml`
**Verified:** Yes — labels confirmed as "easy" in config files

### Problem
task_01 and task_02 are labeled "easy" but have 0% completion, while task_03 (labeled "medium") has 92% completion. This creates a credibility issue for the benchmark's difficulty taxonomy.

### Proposed Fix
Two options (dependent on Issue 3 resolution):
1. **If feedback is enriched (Issue 3):** Keep "easy" labels and re-validate after feedback improvements
2. **If feedback stays as-is:** Relabel task_01 and task_02 to "medium"

### Acceptance Criteria
- [ ] After Issue 3 is resolved and models re-tested, re-evaluate difficulty labels
- [ ] Update labels if completion rates remain below 20% for "easy" tasks

---

## Issue 6: task_05_text_processor Tests Domain Knowledge Over Feedback Literacy

**Severity:** P2 (design concern, not a bug)
**File:** `tasks/task_05_text_processor/tests.py`, `tasks/task_05_text_processor/task.yaml`
**Verified:** Yes — confirmed in code

### Problem
Phase 1 requires Unicode NFC normalization (`unicode_combining` — 47 violations). This is specialized domain knowledge not discoverable from feedback scope names. The task config includes `allowed_imports: ["unicodedata"]` as a partial hint, but agents cannot infer which normalization form to use.

This task measures prior domain knowledge rather than SAOTRI feedback literacy — a valid benchmark dimension but inconsistent with the "medium" label if feedback-driven discovery is the primary goal.

### Proposed Fix
Either:
1. Add a feedback hint: `"hint": "combining characters should be normalized"` (preserves discovery aspect)
2. Accept this as a domain-knowledge task and document it accordingly in benchmark metadata

### Acceptance Criteria
- [ ] Decision made on whether task_05 is a feedback-literacy or domain-knowledge task
- [ ] Task metadata updated to reflect the assessment

---

## Summary

| # | Issue | Severity | Type | Status |
|---|-------|----------|------|--------|
| 1 | No retry on network errors | P0 | Infrastructure | Verified — fix required |
| 2 | No connection reuse (httpx.Client per request) | P1 | Infrastructure | Verified — fix required |
| 3 | Insufficient feedback signals (task_01, task_02) | P1 | Task Design | Verified — enrichment needed |
| 4 | task_06 phase 2 difficulty cliff | P2 | Task Design | Verified — enrichment recommended |
| 5 | Difficulty labels mismatch | P2 | Task Design | Verified — reassess after Issue 3 |
| 6 | task_05 domain knowledge vs feedback | P2 | Task Design | Verified — design decision needed |

**Note:** The audit also recommended separating `error` (infrastructure) from `failed` (model) in status reporting. The code already distinguishes these as separate `final_status` values (`"error"`, `"failed"`, `"timeout"`, `"completed"`), and the dashboard renders them differently (`ERR` vs `FAIL`). This issue is **not confirmed** as a bug — the separation already exists.

**Note:** The audit recommended changing `--parallel` default from unlimited to 5. The actual default is already 1 (sequential). The real issue is not the default but the lack of network resilience when users set high parallelism — covered by Issues 1 and 2.
