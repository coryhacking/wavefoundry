# Upgrade all lint-bound documentation facts during install

Change ID: `1ulnv-bug upgrade-doc-fact-reconciliation`
Change Status: `implemented`
Owner: Wavefoundry maintainers
Status: implemented
Last verified: 2026-08-06
Wave: 1ulnw upgrade-doc-fact-reconciliation

## Rationale

The graph-builder fact already has a safe snapshot/reconcile repair, but the same
docs-vs-code gate still strands upgrades when the state-store schema, chunker, or
embedding/reranker model facts change. A single small reconciliation mechanism
should cover every scalar fact currently enforced by the docs gate.

## Requirements

1. Before extraction, snapshot each supported scalar docs claim only when the
   project contains exactly one claim and it matches the installed code value.
2. Before the docs gate, update a snapshotted claim only when exactly one copy
   still contains the captured old value and the extracted code value changed.
3. Persist snapshots in the upgrade lock so a crash/resume follows the same
   guarded path; retain compatibility with the existing graph-builder state.
4. Leave missing, duplicated, or operator-edited claims untouched so the normal
   docs-constants gate remains fail-safe and actionable.

## Scope

**Problem statement:** A future CHUNKER_VERSION, STATE_STORE_SCHEMA_VERSION, or
model-name bump can fail the upgrade's docs gate even though the framework owns
the exact old claim and could safely advance it.

**In scope:**

- Generalize the existing graph-builder snapshot/reconcile seam to the scalar
  claims in `docs_constants_validators._claims()` (graph builder, state-store,
  chunker, and the three model names).
- Keep the current conservative ownership test and crash-safe upgrade lock.
- Add focused regression coverage for bump, resume, no-op, customization, and
  ambiguity cases.

**Out of scope:**

- Automatic repair of public-contract vocabulary prose; those values are not
  scalar module assignments and remain docs-lint governed.
- Marker regions or broad text replacement in operator-authored documentation.

## Acceptance Criteria

- [x] AC-1: A pre-extract snapshot and post-extract reconciliation advances each
  supported scalar claim when its owning code constant changes, including the
  existing graph-builder claim.
- [x] AC-2: A crash/resume path uses persisted snapshots and produces the same
  result without requiring a second operator edit.
- [x] AC-3: A missing, duplicated, or operator-edited claim is never overwritten;
  docs-lint still reports the actionable failure.
- [x] AC-4: An already-current claim is a no-op and clears stale snapshot state.
- [x] AC-5: Focused upgrade-extension tests cover all supported scalar claim
  families and the repository docs remain docs-lint clean.

## Tasks

- [x] Define one declarative scalar-claim registry shared by snapshot and
  reconciliation logic, preserving the legacy graph-builder lock keys.
- [x] Implement guarded snapshot/reconcile for state-store, chunker, and model
  claims without changing the docs-lint failure behavior.
- [x] Add regression tests for change, resume, no-op, edit, duplicate, and
  missing-claim paths.
- [x] Run focused tests and docs validation; record results and update the
  changelog entry.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| upgrade-hook | code | — | snapshot/reconcile implementation |
| regression-tests | qa | upgrade-hook | focused seam coverage |
| docs-release | docs-contract | regression-tests | lint and release note |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/upgrade_lib.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/docs_constants_validators.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `docs/RELIABILITY.md`
- `docs/architecture/performance-budget.md`
- `CHANGELOG.md`

List real repository-relative paths here. Prepare uses these paths—not Scope, Rationale, or other narrative—to select automatic review lanes. Path scoring is a floor, not a ceiling: ANY lane may also be requested by judgment through the wave's `Requested review lanes` field, and the coordinator is expected to use it. Architecture review especially is usually a judgment call, since an ownership shift or a protocol change can live entirely in files whose paths recruit only the code lane. A requested lane is always honored and costs no receipt churn.

## Affected Architecture Docs

`N/A` — this preserves the existing upgrade/docs-gate boundary and does not
change product architecture or runtime data flow.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Core upgrade repair |
| AC-2 | required | Recovery must be crash-safe |
| AC-3 | required | Prevents destructive doc edits |
| AC-4 | important | Avoids unnecessary writes and churn |
| AC-5 | required | Release gate and regression proof |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-06 | Confirmed graph-builder repair already exists; remaining scalar claims are not covered. | `upgrade_extensions.py:pre_extract`, `docs_constants_validators.py:_claims()` |
| 2026-08-06 | Generalized snapshot/reconcile across scalar facts and preserved retry state; focused upgrade-extension tests passed and docs-lint passed. | `upgrade_extensions.py`, `upgrade_lib.py`, `test_upgrade_wavefoundry.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-06 | Generalize the existing conservative graph-builder seam rather than add marker regions. | Snapshot ownership is already the proven mechanism; markers would broaden the edit surface. | Marker regions; manual-only updates |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Future constant bump strands a docs gate again | Registry covers all currently enforced scalar claims and preserves fail-safe ambiguity handling. |
| Operator customization is overwritten | Reconcile only an exact single old claim captured before extraction. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
