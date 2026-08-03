# Report historical-memory checkpoint as action required, not upgrade failure

Change ID: `1u9lf-bug memory-checkpoint-reported-as-upgrade-failure`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-08-03
Wave: `1ua8t memory-checkpoint-reporting`

## Rationale

A pghn to pgi7 upgrade that reached the normal historical-memory publication checkpoint exited with the expected action-required code, then reported `ERROR: Upgrade failed during phase 'index_update'` and retained `failed_phase=index_update`. The retained lock is correct, but the failure wording and marker make a routine operator checkpoint indistinguishable from a genuine Phase 4 publication failure.

## Requirements

1. A historical-memory checkpoint requiring receipt-owned publication must report a distinct action-required state, retain its recovery lock, and direct the operator to reload and run `wf_upgrade(phase='resume_after_memory')`.
2. That normal checkpoint must persist a canonical tokenized `action_required` record and exit code `4`. Its public failure state is null, while a temporary private `failed_phase=awaiting_memory_validation`, `failed_at=null` compatibility lease is permitted solely to keep pghn/pgi7 dashboards from auto-clearing the dead-PID lock; it must never claim `index_update` failed and must be cleared after successful resume before cleanup.
3. The bridge must be fail-closed: it may suppress only the known legacy parent's immediate `SystemExit(4)` finalizer when its one-shot, receipt-owned-publication marker is present; other exits, hook errors, malformed/missing markers, and unrecognized parents retain existing failure handling.
4. Both existing Phase 4 contracts remain unchanged: an observed non-memory index-publication refusal completes with its `index_build`/`index_health` guidance and no retained failure lock; a thrown receipt-owned publication failure retains the failure marker and error recovery.
5. The correction must work on the installing upgrade when the parent runner predates the new pack; changing only the freshly extracted runner is insufficient.
6. The installing call's pre-reload MCP envelope is owned by the old server and may retain its validation-oriented label and recommendations. After reload/reconnect, the newly loaded server must expose the distinct publication-ready contract; guidance must disclose this one-transition limitation.

## Scope

**Problem statement:** A normal, resumable checkpoint is currently routed through the generic post-mutation failure handler, producing an error-shaped status and a misleading `index_update` failure marker.

**In scope:**

- A narrowly scoped extension bridge that installs a one-shot wrapper around the known legacy parent's failure finalizer. The extension writes a tokenized action-required record and temporary dashboard-compatibility lease immediately before its documented exit `4`; the wrapper recognizes only that marker and `index_update`, retains the lock without an `index_update` failure claim, and otherwise delegates unchanged.
- Native runner classification of the same persisted discriminator, dashboard retention of action-required locks after reload, and structured MCP/CLI state for both checkpoint variants, with an explicit old-server transition envelope.
- Focused regression coverage for package-loaded legacy-parent upgrades, normal checkpoint recovery, dashboard retention, and both genuine index-publication controls.
- Seed-first upgrade guidance and the rendered/operator-visible contract.

**Out of scope:**

- Changing the historical-memory validation or publication workflow.
- Removing retained-lock safety or changing real index-failure recovery.
- Broad upgrade-summary redesigns or new memory features.

## Acceptance Criteria

- [x] AC-1: A candidate-bearing historical-memory checkpoint from the new package under the exact pghn and pgi7 packaged parents returns exit `4`, retains the tokenized action-required lock as `awaiting_memory_publication` / `memory_publication`, never reports `failed_phase=index_update`, prints no `ERROR`, and names `resume_after_memory`. The temporary `awaiting_memory_validation` compatibility lease is allowed only for old dashboard retention and carries no `failed_at`.
- [x] AC-2: On the installing call under pghn/pgi7 MCP server code, exit `4` returns `status: ok`, no `ERROR`, the canonical action-required lock, and raw publication-ready CLI guidance; its old in-memory `data.state` and recommendations may remain validation-oriented until reload. After reload/reconnect, `wf_upgrade` and `wf_upgrade_status` expose distinct `awaiting_memory_publication` versus `awaiting_memory_validation` states, logical null failure state, current phase, action-required discriminator, and publication-specific `next_tools`, `next_step`, and `usage` without leaking the compatibility lease as an upgrade failure.
- [x] AC-3: The compatibility bridge resolves the parent from the context class and is identity-, token-, root-, phase-, exit-4-, and one-shot-scoped to the known legacy finalizer. Different exit codes, hook exceptions, malformed/missing/stale markers, wrong roots/phases, and unrecognized parents retain the existing failure finalizer. The parent-owned post-docs-gate validation checkpoint provisions the same action record and remains an action-required control.
- [x] AC-4: An observed non-memory docs/graph index-publication refusal still completes without a retained failure lock and directs `index_build` then `index_health`; a thrown receipt-owned publication failure still retains its failure marker and error recovery.
- [x] AC-5: Fresh-process, archive-loaded compatibility fixtures prove the new extension under the exact pghn and pgi7 parents and their old server envelopes, then reload the installed runner, prove pending resume retains the lease, refuse premature cleanup, complete `resume_after_memory`, clear the lease before successful cleanup, and reach healthy index state. The exact old dashboards and current dashboard preserve a dead-PID action-required lock while still clearing an unmarked stale lock.
- [x] AC-6: Seed-first prompt, rendered prompt, MCP help/status documentation, tool-surface spec, and changelog describe the two action-required checkpoint states and their correct recovery steps without calling either an index failure.

## Tasks

- [x] Implement the identity- and marker-scoped legacy finalizer bridge plus native action-required classification and dashboard retention.
- [x] Update MCP response/status state and recovery guidance for validation-required and publication-ready checkpoints, including the one-transition old-server envelope.
- [x] Add package-loaded pghn/pgi7-parent and old-server-envelope, parent-owned-return, malformed-marker, wrong-root/phase/token, hook-error, both Phase 4 controls, dashboard, resume, cleanup, and index-health regressions.
- [x] Update the canonical seed, rendered prompt, MCP/tool-surface docs, and changelog; validate docs, targeted regressions, package contents, and the canonical framework suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Compatibility/state implementation | implementer | — | One owner across extension, runner, lock, dashboard, and MCP contract. |
| Regression verification | QA reviewer | Compatibility/state implementation | Exercise pgi7 archive-loaded parent and both non-checkpoint controls. |
| Package/release verification | release reviewer | Regression verification | Confirm source/package parity and fresh-process recovery. |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_extensions.py`, `upgrade_wavefoundry.py`, and `upgrade_lib.py` share the persisted upgrade-lock transition.
- `dashboard_server.py`, `server_impl.py`, and their tests share the action-required visibility contract.
- The seed, rendered prompt, tool-surface spec, changelog, and package-loaded tests must land after the state vocabulary is final.

## Affected Architecture Docs

N/A initially. This is a bounded correction to an existing upgrade state transition, with no new ownership boundary or service. Update the upgrade prompt/tool contract if its public state vocabulary changes.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Prevents normal work from looking broken. |
| AC-2 | required | Preserves reliable automation and diagnostics across the old-server transition. |
| AC-3 | required | Must not weaken genuine failure detection. |
| AC-4 | required | Preserve the two existing Phase 4 safety contracts. |
| AC-5 | required | The installing package boundary and retained-pause safety are the defect's load-bearing path. |
| AC-6 | important | Keeps recovery guidance trustworthy across shipped surfaces. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-03 | Planned from a second downstream pghn to pgi7 upgrade. | Normal checkpoint returned exit code 4 and later resumed cleanly, but the initial runner reported `failed_phase=index_update`. |
| 2026-08-03 | Implemented and independently re-reviewed the bounded compatibility correction. | Exact pghn/pgi7 archive-loaded parents and old servers, portable seam fixtures, normal and fail-closed checkpoints, resume lease clearing, status/MCP contracts, docs lint, and targeted regressions pass. |
| 2026-08-03 | Built the post-review local package. | `wavefoundry-1.15.0.pgl2.zip` passed ZIP integrity; its embedded `VERSION` and the hashes of `upgrade_extensions.py`, `upgrade_wavefoundry.py`, and `server_impl.py` match source; `test_build_pack.py` passed (108 tests). |
| 2026-08-03 | Clarified runner-freshness reporting after downstream upgrade feedback. | Canonical and rendered upgrade guidance now defines `runner_stale: null` as **unknown**, not evidence that a restart is unnecessary; docs lint passed. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-03 | Treat the report as a bug, not a documentation-only nit. | The current failure marker conflates a routine pause with real publication failure and misleads operators and automation. | Leave wording unchanged; rejected because structured state is also wrong. |
| 2026-08-03 | Keep this as a separate small wave. | The prior wave is verified and ready to close; this changes a public recovery-state contract and needs focused old-parent coverage. | Reopen the memory wave; rejected to keep scopes reviewable. |
| 2026-08-03 | Use a one-shot legacy-parent finalizer wrapper delivered by the incoming extension, with a temporary dashboard-compatibility lease. | The extension is the only new code executing inside the already-running parent; a tokenized marker plus an identity-scoped wrapper corrects the installing run while unrecognized cases fail closed. Old dashboards otherwise auto-delete a dead-PID checkpoint. | New-runner-only handling; rejected because it cannot change the installing run. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A bridge masks a real index failure. | Pin real docs/graph publication failure controls alongside the action-required case. |
| A new-runner-only fix misses the fielded installing upgrade. | Exercise the actual old-parent/new-extension package boundary. |
| The bridge suppresses an unrelated failure. | Require exact marker, phase, one-shot parent identity, and negative controls before bypassing the legacy finalizer. |
| A legacy dashboard deletes the intentional checkpoint after the parent exits. | Keep the temporary truthy compatibility lease until successful resume; fresh reporting maps it to action-required rather than failure. |
| The installing MCP response is serialized by old server code. | Preserve its safe `status: ok` envelope and raw CLI guidance; disclose that the distinct structured state appears only after reload/reconnect. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
