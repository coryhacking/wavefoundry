# Index health reports `ready` when the code layer is missing

Change ID: `1p7is-bug index-health-reports-missing-code-layer`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-23
Wave: `1p7ir index-build-robustness`

## Rationale

`wave_index_health` reports `semantic_ready: true` / `readiness_overview: ready` when only `docs.lance` exists and the code layer (`code.lance`) is silently absent. In the 1.8.0 field report the code embedding pass was OOM-killed mid-build, leaving no code layer, yet health still read `ready` — so `code_ask`/`code_search` had no code layer while the operator believed the index was complete.

Root cause (confirmed, `server_impl.py:598`): `semantic_ready = has_any_index and not stale_layers and compatible_chunks`, where `compatible_chunks` is true if the docs **or** code Lance table exists, and `missing_layers` only checks docs/meta presence. So a present-but-codeless index passes every gate. `_code_lance_table` (`server_impl.py:572`) is already available to detect the gap.

## Requirements

1. **Detect a missing code layer.** When the repo has code sources in scope (the same include-prefixes the code pass uses) but `_code_lance_table` is absent, `wave_index_health` must classify the index as **not fully ready** — `readiness_overview: degraded` (the state already exists in the readiness vocabulary) and `semantic_ready: false` (or a distinct honest signal), with the code layer listed in `missing_layers`.
2. **Symmetry.** The same honesty applies if docs sources exist but `docs.lance` is absent (today’s logic already half-covers this via `docs_present`; keep it consistent).
3. **Do not regress the all-present case.** A fully-built index (docs + code both present, fresh, compatible) still reports `ready`/`semantic_ready: true`.
4. **Surface the remediation.** The degraded report’s diagnostics should name the missing layer and point at `wave_index_build(content='code')`.

## Scope

**Problem statement:** Health over-reports readiness, masking a silently-absent code layer — the failure that let the OOM (`1p7it`) go unnoticed.

**In scope:**

- The `docs_health()` readiness computation in `server_impl.py` (`semantic_ready`, `missing_layers`, `readiness_overview`, diagnostics).
- Tests locking the degraded-on-missing-code-layer behavior and the all-present `ready` case.

**Out of scope:**

- The OOM itself (`1p7it`) and the wrapper SIGKILL surfacing (`1p7it`).
- Any change to how the index is built.

## Acceptance Criteria

- [ ] AC-1: with code sources in scope and `code.lance` absent, `wave_index_health` returns `readiness_overview: degraded`, `semantic_ready: false`, and lists the code layer in `missing_layers`.
- [ ] AC-2: a fully-built index (docs + code present, fresh, compatible) still returns `ready` / `semantic_ready: true` — no regression.
- [ ] AC-3: the degraded report’s diagnostics name the missing code layer and point at `wave_index_build(content='code')`.
- [ ] AC-4: framework tests cover the missing-code-layer degraded case, the docs-missing case, and the all-present case, bytecode-free; `wave_validate` clean.

## Tasks

- [ ] Add a code-layer-present probe to `docs_health()` (reuse `_code_lance_table` + the code-source-in-scope check).
- [ ] Fold it into `missing_layers` / `readiness_overview` / `semantic_ready` and the diagnostics.
- [ ] Tests (degraded-on-missing-code, docs-missing, all-present) bytecode-free.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                  |
| ---------- | ----------- | ---------- | -------------------------------------- |
| health-fix | implementer | —          | `docs_health()` readiness computation  |
| tests      | implementer | health-fix | degraded / docs-missing / all-present  |


## Serialization Points

- Pairs with `1p7it` (the loud-SIGKILL surfacing) — together they convert the silent OOM into a visible, diagnosable failure. Independent files; no shared-edit gate.

## Affected Architecture Docs

- N/A — confined to the `wave_index_health` readiness computation; no boundary/flow/verification-architecture change. Confirm at Prepare.

## AC Priority

(Populated at Prepare wave — proposed below.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The missing-code-layer honesty is the deliverable. |
| AC-2 | required  | No-regression on the fully-built case. |
| AC-3 | important | Actionable remediation in the report. |
| AC-4 | required  | Behavior must be test-locked, bytecode-free. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-23 | Drafted from the 1.8.0 field report. Root cause confirmed at `server_impl.py:598` (`compatible_chunks` = docs OR code; `missing_layers` ignores code). | memory `project_field_feedback_1p8_oom_tls` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A repo with genuinely no code sources (docs-only) would be wrongly marked degraded | Gate the code-layer requirement on code sources actually being in scope (include-prefixes), not on the repo unconditionally. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
