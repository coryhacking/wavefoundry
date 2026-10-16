# post_index_update reports an old parent's recovered publication as failure

Change ID: `20p5k-bug post-index-update-old-parent-false-failure`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-15
Wave: `20ppj rerun-reliability-review-follow-ups`

## Rationale

Commit `43621e07` made `post_index_update` in `upgrade_extensions.py` exit 1 whenever `ctx.index_published` is not `True`. For older coordinators that have no `index_published` attribute, `_observe_parent_index_outcome` wraps the parent's `phase_index_update` so the outcome is observed when that function is called. But an old parent's `phase_index_update_parent_owned` early-recovery path can finalize a verified child staging receipt through `_finalize_existing()` and return without ever calling `phase_index_update`. `ctx.index_published` stays `None`, the unconditional post-index hook raises `SystemExit(1)`, and the old parent records a failed upgrade with `index_publication_failed` even though the index was published.

## Requirements

1. Preserve the current coordinator contract: `index_published is True` passes and `is False` records `index_publication_failed` and exits 1. An absent attribute or `None` is unobserved, not success; absent, ambiguous or mismatched durable proof also records failure and exits 1.
2. For an unobserved old-parent outcome, use only the current root's validated retained checkpoint `memory_backfill_run_id` and that run's existing publication authority. Reuse `memory_backfill.reconcile_index_publication` and require its current run to be `indexed`: success was either recorded by `record_publication_success` for the authorized run/attempt after epoch compare-and-set, or recovered by existing exact attempt-ID, generation and current inventory-digest checks. Do not infer success from a generic upgrade flag, latest completed build, timestamp, or staging receipt existence; early recovery can remove staging evidence. No new receipt or snapshot.
3. An absent run ID, unknown/wrong run, stale inventory, mismatched attempt or generation, unreadable proof, or non-indexed result fails closed. Current explicit False must not be overridden by any durable record. Current True remains trusted as before.
4. Drive the actual historical parent's `phase_index_update_parent_owned` early-recovery path and incoming hook in an isolated fixture, not just a hand-built `index_published=True` context. Keep memory validation and publication gates intact.
5. Windows, macOS, Linux and WSL2 share this contract; fixture qualification does not claim native platform execution.

## Scope

**Problem statement:** an unobserved outcome is treated as a failed one.

**In scope:**

- `post_index_update` and `_observe_parent_index_outcome` in `.wavefoundry/framework/scripts/upgrade_extensions.py`
- A regression that drives an old-parent context through the early-recovery path

**Out of scope:**

- Changing `phase_index_update_parent_owned` in the old parent (it is installed code on targets and cannot be patched retroactively)
- The current-coordinator contract

## Acceptance Criteria

- [x] AC-1: An old-parent context (no `index_published` attribute) whose index phase completed through early recovery without calling `phase_index_update`, with current checkpoint-bound authorized run publication proved by the existing reconciler, passes `post_index_update` without `SystemExit` and without `index_publication_failed` being written.
- [x] AC-2: The same context with absent proof/run, wrong run, stale inventory, or mismatched attempt/generation exits 1 and records `index_publication_failed`; an unrelated completed build never authorizes success.
- [x] AC-3: A current coordinator with `index_published = False` still exits 1; with `True` still passes.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Reuse current checkpoint-bound memory publication authority and replay actual historical-parent early recovery with its incoming hook.
- [x] Add failing regressions for AC-1 and AC-2.
- [x] Separate the unobserved case from the observed-failure case in `post_index_update`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fix and tests | Implementer | Readiness | Single write owner |
| Delivery review | QA and required reviewers | Fix and tests | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A. The old-parent/new-child seam is already described from `20qvm`; this change corrects one hook's interpretation inside that seam without moving it.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The false failure |
| AC-2 | required | Must not weaken the real failure signal |
| AC-3 | required | Current-coordinator contract unchanged |
| AC-4 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned from the code review of `43621e07` | Review finding 4 |

| 2026-10-15 | PPJ-R1 bounded readiness repair: named exact existing publication authority, corrected failure semantics, and required real old-parent recovery plus stale/mismatched negative controls. | Requirements 1–5 and AC-1/2; no source edit |

| 2026-10-15 | Implementer preflight readback: Current hook fails every unobserved outcome, including old-parent early recovery. Reuse only the validated retained checkpoint run and existing publication reconciler; explicit failure remains authoritative. Verify actual historical recovery plus absent, unrelated, stale and mismatched controls before accepting the fix. | Admitted Requirements and AC read before code edits; focused failing reproduction then repair |

| 2026-10-15 | Implemented old-parent proof fallback with contained checkpoint read, retained-target/root compatibility and current checkpoint memory run; explicit True/False retain precedence. Actual unchanged v1.22 parent fixture drives early recovery through real memory authorization and staged epoch CAS, bypasses ordinary phase, removes staging receipt, then runs incoming hook. Original source reproduced two false failures; repaired 9-test suite passes, including exact interrupted-CAS reconciliation and absent/unknown/wrong run, unreadable, root, stale inventory, attempt and generation controls. Three in-memory guard mutants detected (indexed verdict, explicit False and root validation). | test_old_parent_publication.py: 9 tests; /private/tmp/ppj-extensions-mutants.py; no native Windows/WSL qualification or new receipt/snapshot |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Resolve an unobserved outcome through the current checkpoint-bound memory run and existing authorized publication reconciler | Keeps fail-closed semantics while covering the recovery path the observer cannot see | (a) Treat unobserved as success: silently masks a real unobserved failure. (b) Wrap `phase_index_update_parent_owned` too: that function is in the installed old parent, so observing it from the new child is fragile and not guaranteed to exist. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Durable state is ambiguous on some old versions | AC-2 keeps the fail branch; any ambiguity fails closed |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
