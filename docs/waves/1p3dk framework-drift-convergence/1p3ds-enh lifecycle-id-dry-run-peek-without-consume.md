# Lifecycle ID Dry-Run Peek Without Consume

Change ID: `1p3ds-enh lifecycle-id-dry-run-peek-without-consume`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-04
Wave: `1p3dk framework-drift-convergence`

## Rationale

Lifecycle IDs are a finite, monotonically-issued resource — each generated prefix is a permanent claim on the wall-clock-derived counter. They appear in filenames, in branch names, in git history, and in every cross-reference between waves and changes. Burning IDs unnecessarily creates two real costs:

1. **Discontinuous prefixes are confusing.** When an operator sees a wave at `1p3dj` followed by `1p3dk` followed by another at `1p3do`, they reasonably wonder what happened to `1p3dk`-through-`1p3dn`. The gap suggests something was deleted, rejected, or hidden. In reality, the gap is artifact of internal dry-run + apply ceremony that the operator never asked for.

2. **Each call to `lifecycle_id.next_available_prefix()` mutates module-level state.** Every dry-run consumption is permanent for the lifetime of the MCP process. This is the exact dual-state pattern this wave is closing elsewhere: the framework permits state mutation in a code path the operator believes is "preview only."

Observed in this session (wave 1p3dk's own opening):

- `wave_create_wave(slug='framework-drift-convergence', mode='dry_run')` returned `1p3dj` and burned it
- `wave_create_wave(slug='framework-drift-convergence', mode='apply')` returned `1p3dk`
- `wave_new_enhancement(slug='align-scaffolded-templates-with-lint-contract')` returned `1p3do`, skipping `1p3dn`
- `wave_new_enhancement(slug='auto-lint-at-wave-mcp-gates')` returned `1p3dq`, skipping `1p3dp`
- `wave_new_enhancement(slug='lifecycle-id-dry-run-peek-without-consume')` returned `1p3ds`, skipping `1p3dr`

Two distinct defects:

**Defect A (operator's primary observation):** `wave_create_wave` with `mode='dry_run'` calls `next_available_prefix()`, which mutates `_last_assigned_prefix` even though no file is written. The `mode='apply'` call that follows must therefore advance past the dry-run-burned prefix.

**Defect B:** `wave_new_*` tools (no `mode` parameter — single-call scaffold) burn 2 prefixes per call. The likely cause is that the implementation calls `next_available_prefix()` once internally for a dry-check then again for the actual write, or the prefix scan happens twice. Investigation during implementation will confirm the exact path.

The cleanest fix is **peek-without-consume semantics**: `next_available_prefix()` gains a `commit: bool = True` parameter (or a companion `peek_next_available_prefix()` helper). When `commit=False`, the function returns the prefix that *would* be returned but does NOT advance `_last_assigned_prefix`. `dry_run` modes call peek; `apply` modes call commit. Defect B is fixed by removing the second internal call (or making the first one a peek).

Race condition note: between a peek and a subsequent commit, another concurrent call could claim the same prefix. The MCP tool model is effectively serial against a single repo, so the practical race window is zero in normal operation. The filesystem scan in `_existing_prefixes` is the final arbiter — if a concurrent process did claim the prefix in between, the commit call detects it from the directory scan and advances.

## Requirements

1. `lifecycle_id.next_available_prefix()` accepts a `commit: bool = True` parameter. When `commit=True` (default, current behavior), it mutates `_last_assigned_prefix`. When `commit=False`, it returns the same prefix it would have returned but does NOT mutate module state.
2. All MCP tools with explicit `mode` parameters (`wave_create_wave`, `wave_add_change`, `wave_remove_change`, `wave_prepare`, `wave_implement`, `wave_pause`, `wave_reopen`, `wave_close`, `wave_set_handoff`, `wave_sync_surfaces`) call `next_available_prefix(commit=False)` in their `dry_run` branch and `next_available_prefix(commit=True)` in their `apply`/`create` branch.
3. Tools without an explicit mode parameter (`wave_new_enhancement`, `wave_new_feature`, `wave_new_bug`, `wave_new_refactor`, `wave_new_documentation`, `wave_new_maintenance`, `wave_new_operations`, `wave_new_tech_debt`, `wave_new_change`, `wave_new_task`) call `next_available_prefix()` exactly once with `commit=True`. Defect B's second consumption is removed.
4. Backward compatibility: callers that do not pass `commit` see the existing behavior (`commit=True`). The change is purely additive at the lifecycle_id surface.
5. Idempotency: a peek followed by a peek on the same in-process state returns the same prefix. A commit followed by a commit advances. A peek followed by a commit returns the same prefix the peek returned (assuming no concurrent process claimed it via the filesystem scan).
6. Cross-process safety: the `_existing_prefixes` filesystem scan still happens on both peek and commit, so external claims (another MCP process, manual file creation) are honored regardless of mode.

## Scope

**Problem statement:** Dry-run MCP tool calls and the no-mode `wave_new_*` tools burn lifecycle-ID prefixes that no operator-visible artifact consumes. The result is discontinuous prefix sequences in `docs/plans/` and `docs/waves/` that suggest lost or hidden work.

**In scope:**

- `lifecycle_id.next_available_prefix()` — add `commit: bool = True` parameter
- All wave-lifecycle MCP tools with `mode` parameters — branch on mode for peek vs commit
- `wave_new_*` family (no mode) — audit and remove the second internal consumption (defect B)
- Tests in `test_lifecycle_id.py` (or equivalent) confirming peek does not mutate state and commit does
- Tests confirming each affected MCP tool's `dry_run` path does not advance the lifecycle counter

**Out of scope:**

- Reclaiming previously-burned prefixes (irreversible; the gaps in `1p3dj`-`1p3ds` stay)
- Cross-process locking around the counter (current single-process MCP model is sufficient)
- Restructuring the prefix encoding scheme

## Acceptance Criteria

- [x] AC-1: `next_available_prefix(commit=False)` returns the same prefix as `commit=True` would, but does NOT mutate `_last_assigned_prefix`.
- [x] AC-2: Two consecutive `next_available_prefix(commit=False)` calls in the same process return the same prefix (assuming no filesystem change between them).
- [x] AC-3: `next_available_prefix(commit=False)` followed by `next_available_prefix(commit=True)` returns the same prefix on both calls; only the second mutates state.
- [x] AC-4: `wave_create_wave(mode='dry_run')` does not advance the lifecycle counter. Sequence: `dry_run` → `apply` returns the same wave_id, not consecutive ones.
- [x] AC-5: `wave_add_change(mode='dry_run')` does not advance the lifecycle counter. (Currently `wave_add_change` does not generate new prefixes, so this is a no-op check — keeps the regression guard in place.)
- [x] AC-6: `wave_new_enhancement(slug='<x>')` advances the counter exactly once, not twice. Verify by reading `_last_assigned_prefix` before and after.
- [x] AC-7: Same as AC-6 for each of: `wave_new_feature`, `wave_new_bug`, `wave_new_refactor`, `wave_new_documentation`, `wave_new_maintenance`, `wave_new_operations`, `wave_new_tech_debt`, `wave_new_change`, `wave_new_task`.
- [x] AC-8: Backward compatibility: any code path calling `next_available_prefix()` without arguments still sees the prior behavior (commit semantics).
- [x] AC-9: Cross-process safety: when an external file appears at the peeked prefix between peek and commit, the commit advances past it via the filesystem scan (regression guard for the race window).
- [x] AC-10: End-to-end test: `wave_create_wave(slug='<x>', mode='dry_run')` followed by `wave_create_wave(slug='<x>', mode='apply')` returns the same wave_id.
- [x] AC-11: CHANGELOG entry under `## [1.5.0]` describes the counter-conservation behavior change.
- [x] AC-12: Full framework test suite passes.
- [x] AC-13: docs-lint clean.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `commit: bool = True` parameter to `next_available_prefix()` in `lifecycle_id.py`
- [x] Identify all `next_available_prefix()` callsites in `server_impl.py` (and any tool helpers); wire `commit=False` into `dry_run` branches, `commit=True` into `apply` branches
- [x] Audit `wave_new_*` family for defect B (the second consumption); patch to a single call
- [x] Add tests covering peek, commit, peek-then-commit, and concurrent-claim-detection behaviors in `test_lifecycle_id.py`
- [x] Add per-tool tests confirming `dry_run` does not advance the counter
- [x] Update CHANGELOG bullet under `## [1.5.0]`
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Close `framework_edit_allowed` gate

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| peek-api | implementer | — | `commit: bool` parameter on `next_available_prefix` |
| call-site-audit | implementer | peek-api | Wire peek into all dry_run branches; fix defect B in `wave_new_*` |
| tests | qa-reviewer | peek-api, call-site-audit | Counter-conservation and behavioral tests |

## Serialization Points

- Single-file API change (`lifecycle_id.py`) is the foundation; the call-site audit edits `server_impl.py` in many places but can be done in one pass after the API lands.

## Affected Architecture Docs

`N/A` — internal counter behavior change; no architectural boundary or data-flow change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Peek semantics is the core of the fix. |
| AC-2 | required | Idempotency of peek — without this, the operator's "preview" mental model breaks. |
| AC-3 | required | Peek-then-commit consistency — the critical happy path. |
| AC-4 | required | Operator's primary observation. |
| AC-5 | important | Regression guard for tools that already don't generate prefixes. |
| AC-6 | required | Defect B fix for the no-mode tools. |
| AC-7 | required | Coverage across the entire `wave_new_*` family. |
| AC-8 | required | Backward compatibility is the contract this wave is honoring everywhere. |
| AC-9 | required | Race window safety. |
| AC-10 | required | End-to-end validation of operator-visible behavior. |
| AC-11 | required | CHANGELOG. |
| AC-12 | required | Suite must pass. |
| AC-13 | required | docs-lint must pass. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-04 | Change scaffolded and admitted to wave `1p3dk`; defect observed live during this session (1p3dj→1p3dk wave jump, 1p3dm→1p3do→1p3dq→1p3ds scaffold jumps) | This doc; wave_current output showing admitted changes |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-04 | Add `commit: bool` parameter rather than a separate `peek_next_available_prefix()` helper | One function with one semantic axis is simpler to reason about than two parallel APIs. The peek/commit choice maps cleanly to the dry_run/apply choice in the caller. | Separate peek function — rejected; doubles the API surface and requires keeping two functions in sync. |
| 2026-06-04 | Cross-process safety preserved via filesystem scan, not via file locking | The MCP tool model is single-process; the filesystem scan in `_existing_prefixes` already covers external file appearance. File locking would add coordination cost for zero gain in the current model. | File-lock-around-counter — rejected; over-engineered for the single-process MCP context. |
| 2026-06-04 | Previously-burned prefixes (the 1p3dl/1p3dn/1p3dp/1p3dr gaps in this wave's session) are not reclaimed | The lifecycle counter is monotonic by design; reclaiming would require re-issuing prefixes, which conflicts with the wall-clock-derived encoding. Accept the gaps as one-time cost of having lived without this fix. | Reclaim gaps via backfill — rejected; breaks monotonic encoding. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Existing callers depend on `next_available_prefix()` always mutating state, even when called for inspection only | Backward compatibility: `commit=True` is the default. Callers that don't pass the parameter see the current behavior unchanged. AC-8 enforces this. |
| A peek-then-commit race could allow a concurrent process to claim the peeked prefix | AC-9 covers this. The filesystem scan in `_existing_prefixes` runs on every call, so the commit will advance past any prefix that materialized between peek and commit. The peek/commit window is also typically <100ms in MCP-tool flow. |
| Defect B's audit may reveal more than one extra consumption per `wave_new_*` call | The audit task is explicit; once the actual call graph is known, the fix may be larger or smaller than estimated. ACs are per-tool so coverage stays explicit regardless of the underlying cause. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
