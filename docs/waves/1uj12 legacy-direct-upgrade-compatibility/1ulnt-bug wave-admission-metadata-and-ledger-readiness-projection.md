# Wave admission metadata and ledger readiness projection

Change ID: `1ulnt-bug wave-admission-metadata-and-ledger-readiness-projection`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-05
Wave: 1uj12 legacy-direct-upgrade-compatibility

## Rationale

The normal `wf_new_*` → `wf_create_wave` → `wf_add_change` → `wf_prepare_wave(mode='ready')` path still creates avoidable recordkeeping work.

First, a new change correctly begins with `Wave: [wave-id or TBD]`, but `wf_add_change` relocates it without replacing that exact scaffold value. Documentation validation then fails until an agent manually updates a value the tool already knows.

Second, a declared wave's typed `events.jsonl` approval is its readiness authority, yet `wf_prepare_wave` also reports legacy prose `## Review Checkpoints` fields as absent or invalid. The prose cannot affect the modern gate, so requiring or reporting it as a defect causes duplicate hand-authored state and confusing successful-but-invalid-looking readiness results.

## Requirements

1. On `wf_add_change(mode='create')`, after a successful relocation, replace only an exact scaffold `Wave: [wave-id or TBD]` or `Wave: TBD` field in the admitted change document with the containing wave ID. Never overwrite a non-placeholder, operator-authored `Wave:` value; dry-run remains read-only.
2. For waves declaring `review-evidence-source: events.jsonl`, derive prepare readiness authority and any returned council-readiness status from the current typed `wave-council-readiness` approval and its review-policy receipt. Do not require a manually authored `## Review Checkpoints` verdict or report it as invalid state.
3. Preserve legacy prose-only wave behavior unchanged: its structured `prepare-council` checkpoint remains the readiness authority and retains validation of required fields and seat alignment.
4. Keep `wf_create_wave`'s minimal generic objective/summary/watchpoint scaffold. This change does not add inferred prose or new required MCP arguments for content the tool cannot know.
5. Document the modern typed-ledger versus legacy-prose behavior in the MCP lifecycle contract and add regression coverage for both paths.

## Scope

**Problem statement:** The lifecycle tools leave deterministic metadata stale and expose non-authoritative legacy prose state as if it were a modern readiness defect, forcing unnecessary manual repairs during normal wave creation and preparation.

**In scope:**

- Deterministic `Wave:` field repair during `wf_add_change(create)`.
- Typed-ledger readiness projection in `wf_prepare_wave` for declared waves.
- Legacy compatibility, targeted tests, and MCP lifecycle documentation.

**Out of scope:**

- Auto-generating a wave's Objective, Summary, or substantive Watchpoints.
- Changing the typed review ledger, approval currency rules, or legacy verdict grammar.
- Overwriting operator-authored change metadata.

## Acceptance Criteria

- [x] AC-1: Creating a change with the standard `Wave: [wave-id or TBD]` field and admitting it with `wf_add_change(mode='create')` relocates it and writes the exact destination wave ID; docs lint passes without a manual metadata repair.
- [x] AC-2: `wf_add_change(mode='dry_run')` makes no metadata change, and an admitted document with a non-placeholder `Wave:` value is not overwritten.
- [x] AC-3: A declared `events.jsonl` wave with a current typed readiness approval reports valid current readiness without requiring a prose `## Review Checkpoints` entry; stale/missing typed approval still blocks readiness.
- [x] AC-4: A legacy prose-only wave still requires a syntactically valid, seat-aligned `prepare-council` verdict and fails when it is absent or malformed.
- [x] AC-5: Focused lifecycle regression tests and the MCP tool-surface documentation cover the two authority paths and the admission metadata behavior.

## Tasks

- [x] Add a narrowly scoped placeholder-only `Wave:` updater to the create path of `wf_add_change`.
- [x] Make typed declared-wave readiness projection use ledger authority exclusively; leave legacy prose parsing on the legacy branch.
- [x] Add positive and negative regression tests for admission metadata, typed readiness, and legacy verdict behavior.
- [x] Update the MCP lifecycle contract.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Admission metadata | implementer | — | Repair only known scaffold values during a successful create admission. |
| Readiness projection | implementer | Admission metadata | Separate typed-ledger authority from legacy prose reporting. |
| Regression coverage | qa-reviewer | Readiness projection | Prove both modern and legacy paths, including negative controls. |
| Contract update | docs-contract-reviewer | Readiness projection | Explain modern versus legacy authority without duplicating the ledger. |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/specs/mcp-tool-surface.md`

List real repository-relative paths here. Prepare uses these paths—not Scope, Rationale, or other narrative—to select automatic review lanes. Path scoring is a floor, not a ceiling: ANY lane may also be requested by judgment through the wave's `Requested review lanes` field, and the coordinator is expected to use it. Architecture review especially is usually a judgment call, since an ownership shift or a protocol change can live entirely in files whose paths recruit only the code lane. A requested lane is always honored and costs no receipt churn.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` must describe the lifecycle response and authority distinction. Architecture docs are N/A: this is a local lifecycle projection and deterministic metadata-repair correction, not a new system boundary.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Removes the deterministic post-admission repair. |
| AC-2 | required | Prevents unintended mutation and preserves operator ownership. |
| AC-3 | required | Removes duplicate modern readiness state without weakening the gate. |
| AC-4 | required | Preserves legacy compatibility and fail-closed behavior. |
| AC-5 | important | Prevents future documentation drift and regression. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-05 | Planned after a readied wave required a manual `Wave:` repair and manual council-checkpoint line despite recorded typed approval. | Direct source review of `wf_add_change`, `wf_create_wave`, and typed/legacy prepare branches. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-05 | Automate only deterministic metadata; make the event ledger the sole modern readiness authority; retain prose only for legacy waves. | This removes duplicate tracking while preserving the existing typed gate and legacy compatibility. | Add objective/summary/watchpoint arguments to `wf_create_wave` (rejected: content cannot be safely inferred); remove legacy prose parsing (rejected: breaks unconverted waves); update every `Wave:` field on admission (rejected: overwrites operator content). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Placeholder matching overwrites meaningful metadata. | Match only the exact standard scaffold/TBD values and pin an operator-authored negative test. |
| Typed projection accidentally weakens legacy gates. | Branch on declared external-ledger authority and retain legacy verdict parser/seat-alignment tests unchanged. |
| Response fields become ambiguous across authorities. | State the authority source explicitly in the returned readiness projection and tool documentation. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
