# Report pending upgrades before selecting another pack

Change ID: `20h8g-bug pending-upgrade-before-pack-selection`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-12
Wave: 20h6q combined-log-tail-check

## Rationale

A field report describes a no-argument wf_upgrade call choosing a newer pack while an earlier upgrade was paused for memory validation, then failing with index_guard_checkpoint_invalid. Current source confirms that the default MCP phase invokes ordinary preflight and that preflight discovers a pack independently of the retained run; the exact field checkpoint has not been replayed. Make the pending operation and its next action clear before new-pack discovery, preserving the existing recovery and validation boundaries.

## Requirements

1. Before default apply-mode pack discovery, inspect the existing checkpoint through canonical readers. For a recognized non-terminal upgrade awaiting an existing action or recovery phase, report that run and the phase-specific next command without choosing a different pack or starting extraction.
2. Derive recognized pending states and guidance from the existing checkpoint/action-required contracts. Cover memory validation/publication, docs-gate recovery, index/storage continuation and terminal cleanup where those contracts apply; do not create a competing state machine.
3. Validate retained identity and pack authority using existing safeguards. An unreadable, invalid or ambiguous checkpoint must be refused with an actionable diagnosis; it cannot fall through to latest-pack selection or be cleared as an ordinary stale lock merely because its PID has exited.
4. Keep explicit recovery phases and a fresh no-checkpoint upgrade working. No-argument calls report pending work rather than automatically validating memory, publishing an index or clearing a checkpoint. Explicit pack selection must not silently replace a valid pending run.
5. Keep MCP and CLI behavior consistent through the canonical runner, with bounded structured diagnostics and unchanged validation/publication gates. Existing read-only discovery and dry-run modes keep their documented semantics.

## Scope

**In scope:** Default-run checkpoint routing and refusal/guidance in upgrade_wavefoundry.py; MCP response mapping only as needed; focused temporary-repository recovery tests; upgrade seed/prompt, tool contract and control-flow documentation; implementation changelog entry.

**Out of scope:** Automatic recovery/publication, checkpoint schema redesign, bypassing memory review, new resume ledgers, broad pack-selection redesign, live target upgrades, and changes to the already-published 1.29.0 assets.

## Acceptance Criteria

- [x] AC-1: With a valid retained memory checkpoint and a newer discoverable pack, the real default runner/MCP path reports the retained run and next action before pack discovery; project content, retained pack and checkpoint authority remain unchanged.
- [x] AC-2: A checkpoint-state fixture matrix derived from the existing contract preserves recovery/refusal distinctions, including invalid or unreadable state and a stopped initiating process; none silently starts another upgrade.
- [x] AC-3: Explicit supported continuation still consumes the verified retained pack and preserves all applicable memory, index and cleanup gates; a fresh no-checkpoint invocation retains ordinary pack selection.
- [x] AC-4: Affected CLI/MCP tests pass, diagnostics and guidance agree, edited docs validate, and the repair creates no extra persistent state or upgrade-wide scan.

## Tasks

- [x] T-1: Prepare the plan; map the canonical pending-state contracts and reproduce the reported selection failure in a bounded scratch fixture.
- [x] T-2: Add the early pending-run decision using existing readers and guidance; preserve explicit phase behavior and pack integrity checks.
- [x] T-3: Exercise default and explicit public routes, newer-pack collision, stale-PID and invalid-state controls; obtain independent code, QA and architecture review, with security review of retained identity.
- [x] T-4: Update seed-owned continuation guidance, rendered prompt, tool contract and concise wave evidence; record any unreproduced field detail explicitly.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Checkpoint routing | implementer | readiness | One writer across runner and handler |
| Boundary review | code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer | implementation | Review existing authority, not a new resume protocol |

## Serialization Points

Readiness precedes implementation. Implementer owns the named runner/handler/tests and seed guidance; reviewers are read-only. Existing upgrade_lib, sqlite_storage_migration and upgrade_extensions contracts are read-only dependencies initially; any necessary edit there must be made explicit in the plan before implementation. Seed 160 is canonical; synchronize its rendered prompt rather than editing only local guidance.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_failure_surfacing.py`
- `.wavefoundry/framework/scripts/tests/test_storage_upgrade_resume.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

Update docs/architecture/data-and-control-flow.md and docs/specs/mcp-tool-surface.md for default-call pending-run routing and action-required responses. Reuse existing recovery authority; no new ADR or state store.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Eliminate wrong-pack selection for the reported state |
| AC-2 | required | Preserve checkpoint ownership and fail-closed behavior |
| AC-3 | required | Retain functional explicit recovery and fresh upgrade |
| AC-4 | required | Keep diagnostics usable without upgrade overhead |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Implementation/disposition and independent delivery reviews completed. Original planning handoff below is historical; current completion and local-pack limitations are recorded in wave.md and the session handoff. | Matching green framework qualification and typed review ledger |
| 2026-10-12 | Source investigation supports the report: no-argument MCP invokes preflight, whose pack selection is independent of the retained run. Exact field failure remains to be reproduced; no live upgrade ran. | wf_server.upgrade_handlers.wf_upgrade_response; upgrade_wavefoundry.phase_preflight, main and _clear_stale_upgrade_lock_for_preflight |
| 2026-10-12 | Readback: AC-1–3 require ordinary apply calls to inspect retained checkpoint/receipt authority before archive discovery, receipt restoration or stale-PID cleanup. A memory-validation pause plus a newer pack must return the retained run and existing continuation guidance without writes. Explicit phase gates, verified original-pack storage continuation and fresh pack selection remain functional. Runner/handler and their scoped regression tests are implementation-owned; dependencies remain read-only and shared guidance is coordinator-owned. | Canonical checkpoint resume flag, resume guidance, durable-pack/handoff validators and receipt readers inspected through callable MCP structural tools. |
| 2026-10-12 | Implemented the early read-only pending decision before restoration, locator loading and archive discovery. Exit 5 reports the retained run through the existing summary sentinel; MCP returns action_required with upgrade_pending, retained state, bounded continuation guidance and no reload. Exact original-pack storage continuation remains available; phase-owned memory/docs/index/cleanup resumes retain their gates. No dependency module or persistent-state schema changed. | upgrade_wavefoundry._pending_upgrade/main; wf_server.upgrade_handlers.wf_upgrade_response |
| 2026-10-12 | 99 focused tests pass: 25 failure-surfacing tests (6.717s), 70 named existing upgrade seam tests (13.301s), and four native storage process tests (33.431s). Coverage includes newer-pack collision, stopped PID, invalid/null/unreadable/unknown state, durable root/token/target/file/hash proof, terminal archive absence, receipt-only reporting without restoration, actual original/relocated storage continuation and four receipt states proving pack+confirmation cannot bypass memory. The incoming upgrade preview also stays quiet for an already-moved unmanaged lifecycle target. | PendingUpgradeTests; ResumeAfterGateTests, HistoricalMemoryUpgradeGateTests, ArchivedLegacyMemoryCheckpointCompatibilityTests, CurrentLineageMemoryCheckpointPauseTests, BoundedMigrationPreviewTests, PhaseCleanupLockStateTests; StorageUpgradeProcessResumeTests four named default/continuation tests |
| 2026-10-12 | Landing-rule mutants fail their intended named tests: deleting the runner pending decision reaches forbidden checkpoint restoration; deleting the MCP pending classification returns error instead of action_required; bypassing canonical retained authority validation accepts invalid proof. Mutants ran in isolated Python memory outside the repository. Exact field checkpoint remains unreplayed; these are representative scratch/source fixtures, not live target or native Windows qualification. Source/tests frozen for coordinator integration and delivery review. | test_default_memory_pause_precedes_newer_pack_and_stale_cleanup; test_real_cli_and_registered_mcp_default_path_report_pending; test_durable_pack_identity_digest_and_terminal_absence_are_canonical |
| 2026-10-12 | Full qualification exposed four real compatibility failures in UpgradeManifestRecoveryTests: explicit same-pack retries after partial extraction, surface failure and unproven pruning were incorrectly refused/reported by the new pending guard. AC-3 reopened while restoring the supported explicit manifest repair. Default calls remain read-only; original pack/target and snapshot authority must remain bound. Delivery review has not started. | /private/tmp/wf-20h6q-full-suite.log lines 2642–2685; test_failed_prune_retains_authority_and_retry_recovers, test_fresh_process_staged_runner_retries_an_unfixed_destination, test_full_retry_after_surface_failure_skips_extract_and_prunes_original, test_partial_manifest_write_before_version_then_retry |
| 2026-10-12 | Restored the supported explicit manifest repair only when its target-bound original snapshot records an early extract/surface/prune failure or unproven pruning after observed successful index publication. Existing action, receipt and terminal ownership retain priority. Explicit archive target and bytes must match retained authority; a canonical handoff digest can authenticate the original when a private locator disappeared. Defaults remain read-only, including snapshot-only recovery. 116 corrected focused tests pass: 87 named upgrade seams including all 17 manifest tests (13.538s), 25 failure-surfacing tests (3.226s), and four native storage process tests (29.019s). All four qualification failures pass; source/tests frozen again. | UpgradeManifestRecoveryTests plus the prior six seam classes; PendingUpgradeTests/failure-surfacing file; four original storage process tests. Canonical qualification remains coordinator-owned. |
| 2026-10-12 | Manifest landing-rule mutants fail their intended oracles: deleting the manifest repair exception makes the supported surface-failure retry return 3; loosening explicit target/digest matching lets a changed same-target archive reach forbidden checkpoint restoration. New refusal controls also cover no-argument calls, a changed target, receipt-free snapshot recovery, typed memory coexistence and an old snapshot whose pruning already completed. | test_full_retry_after_surface_failure_skips_extract_and_prunes_original; test_manifest_retry_requires_explicit_identical_pack_and_default_stays_read_only; test_manifest_snapshot_cannot_override_typed_memory_or_completed_pruning; test_manifest_retry_uses_retained_guard_digest_when_private_locator_is_missing |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-12 | Return a clear pending-run continuation before discovery | Resolves ambiguity without silently executing validation or publication | Automatically resume: expands effects and requires handling every pending gate. Discover latest then explain rejection: preserves wrong-target selection and misleading low-level errors. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Duplicate state classification diverges from recovery | Reuse canonical readers and derive the fixture matrix from their contract |
| Early shortcut bypasses retained-pack validation | Preserve invalid-state refusal and explicit continuation integrity checks |
| Recovery output falsely claims no writes | Assert protected content/authority remains unchanged and disclose any ordinary diagnostic logging |

## Session Handoff

Planned only. Prefer this repair before the cosmetic notice repair; no hard dependency on the log fixture or timing task.
