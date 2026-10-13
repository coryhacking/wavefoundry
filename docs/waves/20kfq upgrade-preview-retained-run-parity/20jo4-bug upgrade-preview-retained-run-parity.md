# Keep upgrade preview consistent with retained-run handling

Change ID: `20jo4-bug upgrade-preview-retained-run-parity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-12
Wave: 20kfq upgrade-preview-retained-run-parity

## Rationale

Field testing confirms the completed guide notice is gone and that real apply refuses an invalid copied checkpoint before pack discovery, preserving the lock. That field probe does not prove valid pending-run continuation guidance. Dry run still predicts stale-lock deletion for the same retained state. Current source confirms main dispatches dry run before _pending_upgrade, while phase_dry_run uses PID staleness alone. The operator needs preview to describe the decision apply will actually make.

## Requirements

1. Share a read-only retained-state decision between dry run and ordinary apply before candidate-pack discovery. Preserve the existing identity, explicit-pack and phase-authority rules; do not weaken invalid-checkpoint refusal.
2. Dry run must distinguish valid pending continuation, invalid/unreadable retained state, active work, and legacy stale state under the existing apply authority. PID death alone grants no disposal authority; an ambiguous legacy lock stays preserved/refused. Never predict deletion where apply preserves or refuses the checkpoint.
3. For retained-state refusal or continuation, preview must not restore receipts, clear checkpoints, extract packs or run unrelated incoming preview hooks. Preserve existing disclosed preview-log behavior for ordinary no-retained-run previews.
4. Keep explicit verified recovery and no-checkpoint upgrade paths compatible; expose consistent meaning through CLI preview, the internal handler preview branch and registered MCP apply, without inventing a second recovery state machine or a new public MCP preview API.

### Compatibility decision table

| Input | Preview and ordinary apply decision |
| --- | --- |
| No checkpoint, pending receipt or retained manifest snapshot | Continue ordinary pack selection and preview/apply respectively |
| Valid recognized retained run, live or dead PID | Preserve state; report existing continuation and CLI exit 5; handler reports action_required |
| Invalid, unreadable or ambiguous retained state, including legacy stale state | Preserve state and refuse before discovery with exit 3; never promise stale cleanup |
| Explicit CLI pack, optionally confirmed hosts stopped | Pass the same inputs to _pending_upgrade; its existing verified storage/manifest/guard exceptions may permit ordinary processing, with preview using that explicit pack |
| Explicit apply recovery phase | Keep its existing phase-owned validation and execution; no new pending guard in that route |
| CLI dry run with a recovery phase flag | Preview only; report retained state without executing the phase |
| Internal handler dry_run | Preserve existing ignored phase semantics, forward existing host confirmation, translate retained exit 5 consistently; public wf_upgrade remains apply-only |
| Explicit detect-zip/list-zips | Keep intentional discovery-only behavior unchanged |

## Scope

Retained-run preview/apply parity, bounded shared decision logic, regression tests and matching guidance. No live retained lock manipulation, fabricated field evidence, automatic resume, broad upgrade refactor or runtime reload implementation.

## Acceptance Criteria

- [x] AC-1: Paired CLI preview/apply, internal handler preview and registered MCP apply controls agree on retained-state decisions and lock preservation for both a valid pending run and an invalid copied identity; the valid fixture exercises explicit continuation guidance.
- [x] AC-2: Dead-PID retained, live-owner, malformed/unreadable, ambiguous legacy-stale and no-lock controls distinguish authorized outcomes. Refused/retained previews never reach archive discovery or recovery mutations.
- [x] AC-3: Explicit verified recovery and ordinary dry-run migration preview keep their established behavior, exit/status contracts and truthful write disclosures.

## Tasks

- [x] T-1: Derive the shared read-only decision from existing _pending_upgrade and checkpoint readers; document phase/explicit-pack compatibility before readiness.
- [x] T-2: Route preview through that decision and remove the contradictory PID-only prediction.
- [x] T-3: Add paired registered-path tests and independent QA/security/code review; update canonical preview guidance and changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation and focused tests | implementer | admission and readiness | Single write owner |
| Independent phase review | code, QA, security, architecture and docs-contract lanes as selected | phase-specific evidence | Read-only review |

## Serialization Points

One implementer owns shared upgrade code and seed/rendered guidance; coordinate those paths with the runtime-reload plan. Reviewers are read-only. Root CHANGELOG.md is also an intended edit. Preserve published/local pack bytes and all consumer diagnostic artifacts. No code edit before admission and readiness.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_failure_surfacing.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

Update docs/architecture/data-and-control-flow.md and docs/specs/mcp-tool-surface.md for the changed decision/scope boundary; canonical seed 160 and rendered upgrade guidance must agree.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Preserves the requested behavior and its safety/compatibility boundary |
| AC-2 | required | Preserves the requested behavior and its safety/compatibility boundary |
| AC-3 | required | Preserves the requested behavior and its safety/compatibility boundary |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Planned from field feedback; no repository code changed. | Live reads of phase_dry_run and main confirm the split. Invalid-lock behavior is user-reported field evidence; no independent full pending-run replay performed during planning. |
| 2026-10-12 | Corrected SECURITY-READINESS-1 through the owning requirements, ACs and compatibility table; no source edit. | Live _pending_upgrade refuses ambiguous legacy state and permits verified explicit continuations without a new decision engine. Public wf_upgrade has phase/confirmation/storage arguments only; preview exists in CLI/internal handler. Baseline PendingUpgradeTests: seven passed. Independent security reverification pending. |
| 2026-10-12 | Readback: satisfy AC-1 through AC-3 by sharing retained-state reporting between ordinary apply and phase_dry_run; preserve existing validation and explicit recovery ownership. Before: an invalid dead-PID checkpoint lets preview predict clearing and discover a pack. After: preview returns the same refusal as apply before discovery; valid retained state returns its existing continuation. | Expected files: upgrade runner, handler, focused upgrade tests, seed 160, rendered upgrade guidance, MCP spec, control-flow architecture and changelog. No live checkpoint changes or public MCP argument addition. Existing DryRunTests: eleven passed after supplying the required scripts PYTHONPATH; initial bare discovery failed import before tests ran. |
| 2026-10-12 | Implemented shared retained reporting, setup ownership refusal, explicit preview-pack selection and internal handler pending translation/confirmation forwarding. Updated canonical and local guidance. | Before fix, paired test_default_memory_pause_precedes_newer_pack_and_stale_cleanup failed all three pack-choice controls with pack discovery reached. After fix: 30 upgrade failure-surfacing tests and 12 DryRunTests pass, including registered MCP apply plus a real CLI child, internal preview, copied identity, phase suppression and explicit manifest retry. Full qualification and delivery review remain pending. |
| 2026-10-12 | Landing controls detected each new guard removal in memory; repository source was not mutated for probes. | Shared retained-report bypass: default pending test failed at checkpoint restoration; deleted setup checkpoint refusal: setup-owned paired test lost storage_setup_resume_required; deleted explicit missing-pack guard: DryRunTests.test_missing_explicit_pack_refuses_without_ambient_discovery failed. No skipped controls; ordinary preview-log disclosure tests pass. |

| 2026-10-12 | Implementation and scoped independent code/security/architecture review passed; QA and release qualification remain pending while this wave is paused for the scanner wave. | Canonical suite completed 12,422 tests/185 files/12 skips, red in five files: sandbox denied local sockets, process inspection and user-local fixture writes; runner also flagged a wave-record update during qualification. All 30 upgrade-failure tests and all 12 dry-run controls passed. Preserve the failed log; rerun the canonical suite with required host permissions after both waves settle, with no concurrent record updates. No timing inference, threshold change or waiver. |

| 2026-10-12 | Final combined canonical qualification and all required independent specialist delivery reviews passed; all ACs and tasks are complete. | 12,430 tests across 185 files, 12 skips, exit 0. Fresh green framework receipt matches current inputs hash e4821ce2fb674828b350dd4b0f1048c2707714a34d65b55f3536078520a90345. No source or record movement during qualification; no waiver, timing conclusion or package claim. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-12 | Select one shared read-only retained-state decision. Copy the apply condition into dry run: duplicates recovery authority and can drift again. Merely reword the stale warning: leaves pack-selection and continuation parity unproven. | Correct behavior at the shared boundary with bounded work | Alternatives and weaknesses stated with the selected approach |

## Risks

| Risk | Mitigation |
| --- | --- |
| Shared validation could accidentally execute recovery writes; keep observation and execution separate and verify non-reachability of mutations. | Verify the change's own public-path controls before delivery approval |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
