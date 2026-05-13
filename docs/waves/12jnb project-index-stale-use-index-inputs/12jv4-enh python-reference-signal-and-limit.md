# Python Reference Signal and Result Limits

Change ID: `12jv4-enh python-reference-signal-and-limit`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

`code_references` is now bucketed and filterable, but Python still leans on text heuristics for most non-call-site references. A tighter Python pass should identify actual call sites structurally, and the tool should expose an optional result cap so agents can get the top signal faster without changing the default broad mode.

## Requirements

1. Python reference search should distinguish real call sites structurally before falling back to broader text matches.
2. `code_references` should accept an optional `limit` argument to cap returned hits after ordering and filtering.
3. The response should report both the full matched set and the returned subset so evidence-complete mode remains explicit.
4. Existing broad behavior must remain available when no filters or limit are passed.

## Scope

**Problem statement:** the current response is useful, but Python-heavy repos still benefit from a more precise call-site signal and a way to trim noisy broad result sets without hiding the full match set.

**In scope:**

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

**Out of scope:**

- Changing the chunker or semantic index pipeline
- Removing the existing broad `code_references` mode
- Reworking `code_definition`

## Acceptance Criteria

- Python call sites are detected structurally where possible and appear ahead of broader mentions.
- `code_references(limit=N)` returns at most `N` hits while preserving the default broad mode when `limit` is omitted.
- The response exposes both returned and matched counts so agents can see what was truncated.
- Tests cover a noisy Python symbol plus a bounded-limit query.

## Tasks

- Add an AST-backed Python call-site pass
- Add the `limit` parameter and response fields
- Add regressions for a short/common Python symbol
- Add regressions for capped result output

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Structural Python call-site detection is the core signal improvement |
| AC-2 | required | Result capping is the user-visible usability gain |
| AC-3 | required | Returned vs matched counts preserve evidence-complete behavior |
| AC-4 | required | Broad-mode compatibility must not regress |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| AST classification misses some Python call patterns | Keep a text fallback for non-call-site mentions and preserve the broad response |
| `limit` hides useful evidence | Keep counts for both matched and returned hits, and leave the default unlimited |
| Short symbol tests become flaky as classification evolves | Add a dedicated regression with a common symbol and assert ordering rather than exact totals |
