# Setup reconciles the local checkout

Change ID: `1y3hc-enh setup-local-index-reconciliation`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-09-15
Wave: `1y3og setup-local-reconciliation`

## Rationale

Developers pull committed framework updates while their gitignored local indexes and running hosts remain older. Plain `wf setup` must make the installed checkout usable, from an empty clone or an existing index, without ZIP discovery or manual deletion. Core search should become usable while historical memory curation remains explicitly pending. The user chose one ordinary command, retaining forward recovery, host-stop and publication safeguards. The check makes that remedy discoverable: developers and agent hosts use a fast, read-only `wf setup --check` after startup or pulled framework changes, with precise setup/restart/resume guidance. The repair and detection implementations are complete; verification evidence and platform limits are recorded below.

## Requirements

1. Plain `wf setup` provisions compatible dependencies, reconciles existing generated surfaces, and builds/updates the local index using installed framework code only. No separate public command or reconcile flag; `wf setup --check` is the read-only companion; existing-style host confirmation/rebuild recovery flags are allowed only for explicit recovery; no ambient package selection or broad authored-doc upgrade.
2. Classify local storage: missing creates; current updates with existing producer-version rebuild rules; supported obsolete storage uses existing staged migration machinery. Reuse vectors where possible; legacy unreadable/duplicate-vector rebuild remains an explicit supported recovery choice, never silent data loss. Unknown/newer/ambiguous authority refuses without deleting data.
3. Setup-owned recovery binds repository and source identities plus an installed-framework content fingerprint, persists exact setup continuation, requires old-host quiescence/confirmation before incompatible cutover and retains current writer compatibility checks. A pending archive-owned upgrade remains owned by its original continuation; setup never substitutes ownership or deletes locks/receipts.
4. Migration publishes and verifies through existing semantic/graph epoch and fresh-process integrity checks before owned legacy cleanup. Failures retain source, candidate and recovery state for retry. Preserve auxiliary SQLite data, separate memory state, and unknown content. No ordinary purge workflow.
5. Pending historical memory validation permits normal core indexing without memory-publication authority. Preserve pending candidate labels and the durable run; report core readiness separately from incomplete memory adoption. Existing validated run publication/CAS remains required before claiming memory indexed; preserve crash recovery and handle source requeue with at most one core-only fallback pass. Do not change which candidate statuses are retrieved.
6. Repeated setup on a ready checkout performs existing incremental/no-op work; never re-embed solely because setup was rerun. Errors remain actionable/nonzero; expected host handoff is distinguished from failure. POSIX and native Windows receive shell-correct commands; supported Python versions remain compatible.

7. Add `wf setup --check [--root PATH] [--json]`, sharing one read-only assessment function with MCP startup, background monitoring and health diagnostics. Return a versioned structured result with status, observed reasons, scope/limitations and ordered recommended actions. Statuses are `ready`, `action_required`, and `indeterminate`; CLI exit codes are 0, 1 and 2 respectively. Invalid CLI usage remains exit 2. Check mode rejects repair/build flags and cannot enter normal setup or its mutating session.
8. Inspect the effective interpreter/tool environment, installed dependency metadata against canonical requirements, index presence/schema and producer-version markers, pending setup/upgrade ownership, and setup-relevant configuration/surface state. Missing dependencies must be diagnosable using a stdlib-only bootstrap path. Do not import embedding/reranking models, download anything, enumerate/hash the source corpus, perform integrity scans, acquire a write lock, repair checkpoints or create a database. Normal SQLite-managed WAL/SHM coordination is allowed by operator direction; no database updates, WAL transaction-content writes, checkpoint requests, recovery or explicit sidecar removal. Unsupported, corrupt, busy or unreadable observations are not healthy results.
9. Distinguish actionable causes: missing dependencies/index or obsolete setup state recommends plain setup; stale loaded code recommends host restart; pending recovery recommends its validated owning continuation; newer/ambiguous storage preserves data and reports the existing diagnostic. Return multiple ordered actions when needed, rather than hiding setup work behind restart or recommending setup over a pending archive-owned upgrade. Ordinary source edits remain the existing incremental refresher's responsibility; historical memory awaiting validation is advisory and does not alone require setup.
10. Run the bounded check before heavyweight MCP imports and reuse it in the existing quiet-period monitor when setup-relevant inputs change. Cover framework/configuration/venv changes regardless of Git command, including merge, rebase, checkout and uncommitted same-version edits; do not use HEAD or VERSION alone as proof. Rate-limit repeated notices by observed signature, and clear them after successful reassessment. A stale running host must not use cached old rules to declare updated files ready: use a bounded fresh installed-code probe where needed, or report restart/indeterminate. Never auto-run setup, stop hosts, or perform migration from the check.
11. Track setup-relevant changes with a small, versioned local assessment stamp written only by successful ordinary setup, plus an in-process assessment cache. The stamp is an optimization/hint, not storage authority or proof of current dependencies: cheap live checks still apply. Missing/old stamps trigger assessment rather than force a rebuild. Explicit checks write no cache. Define the bounded input census from canonical setup/dependency/rendering contracts during Prepare; include same-version edits, effective environment identity and configuration changes. Exclude transient files and unrelated source edits. Existing migration fingerprints and receipts remain authoritative and unchanged.
12. Keep work bounded: no recursive product-source walk, full index health scan or embedding work; one time-bounded bootstrap child at most per assessment when required, with timeout reported as indeterminate. Measure cold/warm CLI and startup overhead on representative fixtures and the local project, recording hardware and cost by phase. Initial engineering targets are warm p95 under 100 ms and cold p95 under 500 ms on the measured local machine; report any miss and its cause instead of asserting portable timing guarantees. Cache-hit monitor ticks should inspect bounded signals without full reassessment.

## Scope

**In scope:** read-only setup assessment and CLI mode, startup/monitor/health integration, a non-authoritative successful-setup stamp, bounded detection and command-format tests; setup orchestration and a bounded helper for storage lifecycle ownership; shared storage migration/restart seams and any necessary compatibility/publication hooks; tests; canonical setup/upgrade guidance and project reconciliation; concise user-facing changelog entry.

**Out of scope:** new storage schema, model changes, automatic framework downloading/upgrading, graph/retrieval ranking changes, bypassing pending archive receipts, new candidate exclusion policy, shared-venv redesign, Git hooks, automatic process termination, release packaging/commit/closure. The reported unrelated Windows-path test already passes here and is not bundled without a reproduced attributable failure.

## Acceptance Criteria

- [x] AC-1: Fresh/current setup reaches core readiness without archive discovery, preserving existing incremental and version-triggered rebuild behavior.
- [x] AC-2: Setup reconciles supported legacy/schema-7 storage to the current store using installed source, preserving vectors/auxiliary/memory data and proving cleanup only after fresh-process verification.
- [x] AC-3: Setup restart/resume binds source and root identity, refuses source drift/live old hosts/foreign pending receipts/newer or ambiguous stores, and preserves retryable state on failures.
- [x] AC-4: Pending historical memory setup completes core indexing with an explicit pending-memory advisory; later validation completes the same run through the guarded publication path, including crash recovery and bounded source-requeue handling.
- [x] AC-5: Two-checkout and retry fixtures exercise post-pull old storage with an unrelated ZIP present, repeated setup, phase interruption, missing models/build failure, and Windows continuation rendering; source/ownership guard mutations are detected by named tests.
- [x] AC-6: Canonical and local guidance describes `wf upgrade` as installing a release and `wf setup` as readiness for the current checkout; no destructive purge runbook or unconditional overall-ready claim while memory remains pending.

- [x] AC-7: Check mode produces documented text/JSON statuses and exit codes for ready, setup-required, restart-required, pending recovery and indeterminate fixtures, including simultaneous causes; ordinary setup behavior remains unchanged.
- [x] AC-8: Missing dependencies and old storage are diagnosed before heavyweight imports. Public CLI/startup probes prove no setup execution, network/model loading, checkpoint/index-data mutation or new application cache files (SQLite-managed coordination sidecars are allowed); failures preserve existing data and ownership.
- [x] AC-9: Startup and the existing monitor consume the same result contract; same-version framework/config/venv changes trigger reassessment, ordinary source edits do not request setup, repeated notices are coalesced, and stale loaded code cannot report readiness from obsolete rules. MCP stdout remains valid protocol traffic; pre-handshake diagnostics use stderr.
- [x] AC-10: Adversarial tests cover stamp absence/tampering/staleness, changed dependencies despite an unchanged stamp, concurrent setup, malformed/newer/ambiguous storage, bounded-probe timeout, and Windows/POSIX root and recovery-command forms. Weakened readiness/ownership guards are detected by named regressions.
- [x] AC-11: Recorded cold/warm measurements and call-count controls establish bounded assessment cost without a product-source walk; docs explain that setup readiness is not a full search-quality/integrity/freshness audit and show `wf setup --check` followed by plain setup only when recommended.

## Tasks

- [x] Implement setup-owned storage reconciliation with reusable migration/publication seams and identity-bound resume.
- [x] Decouple pending historical memory from core setup readiness without weakening guarded memory completion.
- [x] Add/run bounded migration, setup, memory and command-rendering regressions with guard controls.
- [x] Update canonical guidance, project docs and changelog; reconcile local carriers.
- [x] Run integration smoke checks, framework suite and docs validation; record outcomes and limits.

- [x] Prepare/review the expanded detection scope and bounded input census before new code edits.
- [x] Implement the bootstrap-safe shared assessor, text/JSON check mode and successful-setup stamp without entering mutating setup in check mode.
- [x] Integrate startup, existing monitor and health guidance with stale-host handling and coalesced notices.
- [x] Exercise read-only/ownership controls, cold/warm cost and cross-platform command fixtures; reconcile command docs and record limits.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Storage coordinator | senior-data-engineer / coordinator | readiness | One writer for helper and shared migration hooks |
| Setup memory orchestration | implementer | readiness, agreed helper API | Separate setup module/tests owner; no shared migration edits |
| Integration/guidance | coordinator | both implementations | Serialized final integration and docs |
| Verification | qa-reviewer and required independent lanes | implemented tree | Fresh review evidence; no implementer self-approval |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/setup_reconciliation.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/sqlite_storage_migration.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/index_compatibility.py`
- `.wavefoundry/framework/scripts/publication_control.py`
- `.wavefoundry/framework/scripts/memory_backfill.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/011-install-wavefoundry-phase-1.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/README.md`
- `docs/prompts/install-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/agents/memory/README.md`

Additional review targets for the planned check: `.wavefoundry/framework/scripts/setup_readiness.py` (proposed new stdlib-safe assessor), `server.py`, `server_impl.py`, `venv_bootstrap.py`, `render_platform_surfaces.py`, `wf_cli.py`, proposed `setup_requirements.py`, corresponding tests, `docs/architecture/layering-rules.md`, `docs/architecture/domain-map.md`, `docs/specs/mcp-tool-surface.md`, and `docs/contributing/build-and-verification.md`. Confirm actual ownership of CLI dispatch during Prepare; avoid changing launchers if their existing argument forwarding is sufficient. Coordinator owns shared assessment/result contract; a bounded implementer owns CLI/bootstrap; monitoring integration follows that contract; independent QA/security/docs reviewers are read-only. Seeds/README and local command guidance are write-owning documentation surfaces; generated host files remain protected and are regenerated only if necessary.

Root CHANGELOG.md is a serialized coordinator-owned release-note surface. Protected generated host surfaces are regenerated only when necessary; no manual policy edits there. Tests-directory declaration is review coverage, not permission for unrelated rewrites.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` (setup/storage/memory ownership), `docs/agents/memory/README.md` (core-ready versus adoption-pending); packaged README and setup/upgrade prompt contracts. No schema ADR needed: reuse existing storage decisions. The check also affects startup/monitor control flow, MCP diagnostics and operator command documentation in the additional targets above.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | One-command user contract |
| AC-2 | required | Safe post-pull storage transition |
| AC-3 | required | Recovery cannot be bypassed |
| AC-4 | required | Core search independent of curation |
| AC-5 | required | Exercise actual failure boundaries |
| AC-6 | required | Operators need accurate recovery guidance |
| AC-7 | required | Stable read-only command contract |
| AC-8 | required | Bootstrap and non-mutation safety |
| AC-9 | required | Automatic discovery without noisy or stale advice |
| AC-10 | required | Failure and ownership boundaries |
| AC-11 | required | Bounded cost and honest readiness claim |

## Progress Log

Readback / Thought: after a pull, `wf setup --check` reports setup, restart or the owning recovery command without repairing anything. AC-7–11 cover a stdlib shared assessor and canonical dependency registry, explicit CLI/bootstrap dispatch, existing-monitor/health integration and measured bounded checks. Senior-data-engineer owns assessor/requirements/setup_index and their tests; implementer owns setup/server integration and separate tests; coordinator owns documentation and integration verification. No Git hooks, storage-format changes or new public command.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-15 | Final Observe: implementation and verification complete. Full framework suite passed 9,090 tests across 94 modules (21 skipped), and its green receipt independently matches current framework bytes. Full wf_validate_docs passed with no errors/warnings; diff whitespace clean. Four assessor guard mutants re-detected on final code. Both edit gates closed and framework bytecode caches removed. Formal delivery review, closure, commit and packaging remain separate. | test-cache.json 2026-09-15T23:25:04.980403+00:00, inputs_hash 11e623eb48a857c0f658ffd7633e32b4b76b3c63fd082726d2c91fc91ce72c5e; /private/tmp/wf-setup-check-final.log; /private/tmp/wf-check-mutants-final.log |
| 2026-09-15 | Reflect: broad suite ran 9,090 tests and caught duplicated tool-environment path resolution plus legacy test doubles missing the new assessment contract. Reuse the existing stdlib venv_bootstrap resolver instead of weakening the architecture scanner; update focused server/health fixtures without weakening public startup checks. Full docs validation passed with no errors or warnings. Final suite will rerun after these repairs. | /private/tmp/wf-setup-check-full.log; wf_validate_docs |
| 2026-09-15 | Observe: expanded assessor suite passes 30 tests, including malformed/tampered stamps, concurrent ownership, busy/malformed storage, live WAL invalidation, no product walk, one isolated child, POSIX/PowerShell quoting and actual setup restart-command bindings. Independent check_council reverified its three concrete findings as resolved. Full suite and docs validation remain running. | test_setup_readiness; check_council final verification |
| 2026-09-15 | Cost evidence: ready fixture with current metadata, real installed dependency metadata and shipped finite source census: 100 in-process checks p50/p95/p99 54.51/59.58/63.36 ms; 30 fresh CLI processes 133.31/176.02/186.72 ms. Both p95 targets pass on macOS ARM64/Python 3.13.5 while suite work ran concurrently. Fresh processes do not mean flushed OS caches; not a cross-platform bound or native-import/model proof. | /private/tmp/wf-check-perf-ready-final.json; /private/tmp/wf-check-perf-ready.py |
| 2026-09-15 | Observe: shared assessor and public integration implemented. 21 assessor, 11 integration, 45 setup and 163 setup-index focused tests pass; subprocess isolation guard passes. Public copied-entry fixtures begin with bytecode enabled and tripwire activation, heavy imports, network and setup; application-file census is unchanged. A ready metadata fixture uses one real isolated SQLite reader; no parent SQLite binding. Full suite running. | test_setup_readiness; test_setup_readiness_integration; test_setup_wavefoundry; test_setup_index |
| 2026-09-15 | Mutation evidence: deleting stale-loaded-code guard, bypassing pending-owner validation, treating stamp as authority and switching live WAL reads to immutable each fail their named unchanged regression with assertions (no error-only detections). Activation-before-check mutant is also caught by public bootstrap test. | test_stale_loaded_assessor_returns_restart_without_sql_or_setup; test_malformed_ownership_suppresses_setup; test_missing_dependency_checked_despite_matching_stamp; test_wal_snapshot_sees_newer_schema_before_checkpoint; /private/tmp/wf-check-mutants.log |
| 2026-09-15 | Integration review repaired false-ready cache/ownership gaps: compare actual interpreter identity, validate checkpoint root binding, invalidate on environment executable/site changes, retain exact owning continuation and suppress setup on unproven storage. Public checks remain observational only. | check_council disposable probes; test_valid_recorded_archive_continuation_preserved; test_venv_executable_removal_invalidates_signature |
| 2026-09-15 | Observe: typed readiness refreshed and implementation opened. Check only returns status/recommended action; operator reaffirmed no automatic setup or application writes. CLI/bootstrap integration draft passes five isolated public-entry probes, including activation-before-check mutation; shared-assessor tests await the new module. Documentation contract updated. | wf_prepare_wave ready; wf_implement_wave create; test_setup_readiness_integration.PublicBootstrapTests |
| 2026-09-15 | Extension plan review: full red-team primer and isolated architecture, security, QA and reality-checker seats agree on pre-activation dispatch, canonical bounded census, stale-code refusal and honest deadlines. Native disposable probes show SQLite mode=ro can create both WAL/SHM; operator subsequently authorized ordinary SQLite coordination; final council readiness approved after closing reconciliation. No extension implementation claimed. | check_primer; check_arch; check_security; check_qa; check_reality |
| 2026-09-15 | Review findings resolved in implementation: publication-lock deadlock, partial-option abbreviation, duplicate roots, macOS disposable-file fingerprinting, inherited parent-finalization authority and legacy fence/checkpoint continuity. Independent QA reran native legacy cutover and ordinary repeat successfully. Full docs validation passed with no errors or warnings. | setup/helper tests; independent setup_readiness_qa recheck; wf_validate_docs |
| 2026-09-15 | Verification: 26 helper/storage, 43 setup, 46 memory and 163 setup-index tests pass. Native SQLite fixtures exercise schema-7 and schema-6/legacy cutovers, byte-identical vectors, auxiliary/separate memory preservation, two checkouts with unrelated ZIP, failed verification retry, both interrupted receipt supersession paths and fresh child verification. Broad full suite running. | test_setup_reconciliation; test_setup_wavefoundry; test_memory_backfill; test_setup_index |
| 2026-09-15 | Mutation evidence: cached-fingerprint and foreign-owner bypasses detected by unchanged regression tests; inherited memory authority controls detected. A single validator bypass remains blocked by the independent checkpoint fingerprint check. Limits: model-free migration fixture simulates the final incremental no-op; no native Windows/Linux execution or live project migration claimed. | test_same_version_source_drift_refuses_without_changing_receipt; test_foreign_checkpoint_preserved_before_any_setup_write; memory tests |
| 2026-09-15 | Reflect: migration primitives are reusable, but receipt ownership and environment authority must remain explicit across every entry point. Expanded interruption tests cover old-to-new receipt handoffs and completed upgrade ancestry; no new recovery bypass or public reconcile flag added. | independent QA native reproducer and fixes |
| 2026-09-15 | Gapfill: initial MCP outline/read evidence grounded planning and readiness; direct working-tree diffs and new-file reads verified concurrent unindexed implementation changes and test failures. | git diff; setup_reconciliation.py; focused regression output |
| 2026-09-15 | Observe: implementation complete. Full framework suite passed 9,047 tests across 92 modules (12 skipped), current green receipt independently hash-matched. Full wf_validate_docs passed, no errors/warnings; git diff --check clean. First sandbox run exposed process-inspection restrictions in dashboard tests; final run with authorized local process access passed. Both edit gates closed. Formal delivery review and closure remain separate. | test-cache.json ran_at 2026-09-15T15:08:34.965139+00:00; /private/tmp/wf-1y3og-tests-final.log; wf_validate_docs |
| 2026-09-15 | Readback / Thought: implement plain setup readiness for fresh/current/obsolete local storage. Before: git pull plus old index refuses setup; after: setup owns safe staged reconciliation and exact host-confirmed setup retry, core search remains usable with memory pending. Storage helper/shared seams and setup-memory writer work independently; coordinator integrates docs/tests. Gates open after typed readiness and all prepare lanes. | wf_prepare_wave ready; wf_implement_wave create; memory_brief |
| 2026-09-15 | Observe: setup/memory implementation passes 41 setup and 46 memory tests; inherited-memory-authority mutation detected. Real finalizer source requeue completes one unscoped fallback epoch and retains awaiting-validation state. | test_setup_wavefoundry; test_memory_backfill; setup-memory-mutant.log |
| 2026-09-15 | Observe: canonical setup/upgrade, packaged README, local install/upgrade, memory/architecture and tight changelog guidance updated. Existing carrier suite passed 5 tests; docs changed-set lint passed. Runtime-specific wording will be reconciled after integration. | seed011/160; local prompts; test_render_agent_surfaces.HostNeutralOrchestrationCarrierTests |
| 2026-09-15 | Discovery: current-tree upgrade already exists but ambient archive discovery wins; setup early memory gate blocks core build. Selected direct reuse of migration primitives, not full upgrade execution. | upgrade_wavefoundry.phase_preflight/main; sqlite_storage_migration.prepare_upgrade; setup_wavefoundry.main; MCP outline/read |
| 2026-09-15 | Independent memory design confirms normal unscoped publication keeps checkpoint checks; candidate status is not synonymous with unvalidated. | setup_memory_design read-only findings; index_state_store.finalize_build_epoch; memory_records.DEFAULT_SURFACED_STATUSES |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-15 | Extend the existing change with shared read-only setup assessment. | Operator chose `wf setup --check`; startup and background detection need one contract. | Full index_health performs a corpus hash scan and is too broad for startup; Git hooks miss non-Git edits and were deliberately retired; a shared bounded check reuses existing monitoring without another public command. |
| 2026-09-15 | Make plain setup reconcile installed source through shared storage primitives. | Matches operator command simplicity while preserving lifecycle fences. | Separate sync/flag adds friction; call full upgrade introduces archive discovery/authored-doc changes; purge-first loses authority/recovery state. |
| 2026-09-15 | Keep existing candidate retrieval/labels, separate core readiness from backfill completion. | Operator requests usable search without falsely claiming validated memories. | Filtering all candidates changes existing semantics and incorrectly excludes validated retained candidates. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Source changes between pause and resume | Fingerprint actual installed producer/migration code; refuse drift and preserve evidence |
| Existing package receipt is hijacked | Detect/refuse before setup-owned lifecycle mutations |
| Old host recreates retired database | Quiescence, publication lock, existing compatibility checks and retained receipt fence |
| Memory requeue leaves core unavailable | One bounded ordinary core pass; never mark pending memory indexed |
| Shared environment dependency changes affect other projects | Reuse existing dependency setup; no uninstall/venv redesign |
| Windows sharing failures or unexpected files | Existing typed cutover refusal and owned cleanup inventory; platform fixtures, no unrun native qualification claim |

## Implementation constraints from readiness primer

- Persist explicit setup ownership in receipt/checkpoint; absent owner means legacy upgrade. Restore, restart and publication paths dispatch through this owner without duplicating migration mechanics. Foreign checkpoints are refused before defaults, surfaces or memory migrations write.
- Fingerprint installed framework scripts and shipped behavior inputs, excluding transient caches, bytecode, generated MANIFEST/VERSION outputs only where content identity is separately bound. Validate before advancing recovery and final publication. Changed source requires restoring the recorded framework; preserve data.
- A missing database is fresh only when no incompatible repository host is positively identified; preserve existing no-index old-host fence and test it. Explicit host confirmation is retained in the generated setup continuation and consumed before lower-level argument forwarding.
- Setup-owned migration forces synchronous docs, code and graph completion plus existing migration-specific proof and fresh-process verification. A failed graph/publication/verification cannot authorize cleanup.
- Core-only memory fallback clears inherited memory publication authority in a scoped way, preserves pending metadata, and does not claim adoption complete.

## Setup-check readiness decisions

The operator reaffirmed that the check only returns status and a recommended action to the local agent. No assessment consumer may automatically invoke setup, installation, rebuild or recovery from that result. The separate ordinary setup success path owns the advisory stamp; check mode never writes it.

- Public entry: intercept check mode in explicit `main(argv)` parsing before tool-venv activation, mutating setup sessions or heavy imports. Suppress framework bytecode before the first local import. MCP startup must resolve its root and assess before activation/importing server_impl. Normal Python interpreter startup customization predates this boundary and is not controlled by the assessor.
- Canonical dependencies: extract setup dependency constants into a bootstrap-safe shared module (`setup_requirements.py`) consumed by setup and the assessor. Include extras, ranges and provider-selected requirements; unsupported expressions produce indeterminate. Do not duplicate pins or execute package `.pth` hooks to inspect metadata.
- Finite input census: assessment/bootstrap/CLI/setup modules, canonical requirements, index_compatibility and schema/producer constant owners (index_state_store, sqlite_vector_store, chunker, indexer, graph_indexer), renderer contracts (render_platform_surfaces/render_agent_surfaces), VERSION, install workflow defaults, relevant workflow/platform/provider configuration, enabled launcher/MCP surface files, effective interpreter/ABI/tool-venv path and pyvenv.cfg, required distribution metadata, owned receipt/checkpoint identities and bounded database metadata. Exact paths/limits are named constants in the assessor; no recursive product-source enumeration. Missing/oversized/unparseable inputs never silently disappear from the census.
- Layering: database metadata observations use one isolated `-I -S -B` stdlib child with a hard deadline, avoiding a second SQLite binding inside the APSW runtime. Query exact metadata keys and the singleton build-state record in one bounded read transaction; no vectors, counts or integrity scans. Document the standalone diagnostic exception in layering-rules/domain-map.
- Stale loaded code: changed captured assessor/producer/bootstrap identity returns restart plus indeterminate; do not hot-load new code to obtain a green result. Preserve this distinction alongside other independently provable actions. Startup/storage refusals do not authorize mutation or substitute for writer guards.
- Stamp/cache: successful ordinary full-core setup writes the advisory stamp; check mode never does. Live requirements/ownership observations remain mandatory despite a matching stamp. Stamp absence on older valid installs means assessment, not a forced rebuild. Monitor cache hits use bounded stat/environment signals; dependency metadata changes and same-version source changes invalidate.
- Startup behavior: fatal environment findings print concise stderr diagnostics and exit before heavy imports; index/setup advisories do not automatically disable otherwise usable non-index tools. Keep MCP stdout protocol-only. Concurrent ownership/input changes produce indeterminate; never merge incompatible observation generations.
- Cost claims: byte/count bounds apply to all reads; the child deadline covers the isolated database probe, not arbitrary parent filesystem stalls. Report measured whole-assessment latency and explicit limits rather than claim an unenforced global deadline.
- Operator decision, 2026-09-15: allow normal SQLite-managed WAL/SHM coordination files and read marks, which may remain after the check. Prohibit database updates, existing WAL transaction-content writes, checkpoints, migration, recovery, receipt changes and explicit sidecar deletion. Use mode=ro, query_only and a bounded read transaction; never immutable/main-file-only reading of live WAL state. Check mode remains read-only with respect to application data, not byte-for-byte filesystem immutability.

## Plan Review

**Detection extension, reviewed 2026-09-15:** fresh typed readiness for AC-7 through AC-11 was recorded and Prepare/activation passed before implementation. The input census, bootstrap path and timeout handling were explicit readiness review targets. Command naming and SQLite-managed coordination-file allowance are settled by the operator; performance targets are proposed engineering budgets to validate, not measured claims.

Self-answered: use migration primitives rather than full upgrade; retain explicit --confirm-hosts-stopped in generated setup continuation because empty host discovery is not proof; keep candidate visibility/labels rather than introduce new retrieval filtering; preserve pending package ownership. No operator questions remain. Stop condition: Requirements, AC and Scope branches resolved from request and current code; readiness council remains required.

## Guard mutation evidence

| Weakened guard | Detecting regression | Result |
| --- | --- | --- |
| Cached source fingerprint | test_same_version_source_drift_refuses_without_changing_receipt | killed |
| Foreign checkpoint owner | test_foreign_checkpoint_preserved_before_any_setup_write | killed |
| Host confirmation | test_current_runner_still_requires_explicit_confirmation | killed |
| Host liveness | test_no_database_old_host_requires_handoff_and_refuses_live_resume | killed |
| Verification failure | test_failed_fresh_verification_retains_source_and_checkpoint | killed; independent cleanup guard also refuses |
| Receipt root | test_pack_relocation_retains_target_root_and_live_host_fences | killed; independent target guard also refuses |
| Checkpoint migration id | test_checkpoint_migration_id_cannot_be_removed | killed |
| Checkpoint root | test_checkpoint_root_identity_mismatch_refuses_without_mutation | killed after direct regression added |
| Completed-parent digest | test_completed_parent_digest_mismatch_refuses_interrupted_handoff | killed after direct regression added |

Mutations ran in memory, leaving production source unchanged. The last two initially survived the broader fixtures; direct adversarial tests now prove both refusals preserve checkpoint, receipt and source bytes.

## Session Handoff

See `docs/agents/session-handoff.md`; all eleven ACs and tasks are implemented and verified. Expanded scope passed fresh Prepare before implementation; final delivery rechecks resolve all three findings.

Operator acknowledgment: “allow them it's fine” resolves the WAL/SHM coordination question. The user requests continued implementation of the reviewed extension.

### Post-Git readiness guidance refinement — 2026-09-15

Readback / Thought: Operator requested that agents check index status after Git operations that update the local checkout. This refines AC-6/AC-11 guidance using the existing index_health setup_readiness result; no new hook, runtime writer or automatic repair. Coordinator owns seed-050, seed-160, root AGENTS.md and existing operator guidance. Implement the canonical instruction, reconcile local carriers, then validate documentation and the framework receipt. Thin host pointers continue to route through AGENTS.md.

Observe: Seed 050 now owns the post-Git instruction, with identical text in AGENTS.md; seed 160 and the local upgrade prompt require its merge on upgrade, and build-and-verification points to the canonical section. A direct parity check passed; existing Claude, Copilot, Cursor and Warp entry files retain AGENTS.md pointers. Full docs validation passed with no errors/warnings. No renderer code or host-specific hooks changed; this establishes guidance propagation, not proof of host compliance. Full framework suite rerun is in progress because seed edits invalidate the prior receipt.

Observe / verification: Post-Git guidance parity and full docs validation passed. Final full-suite run exercised 9,090 tests across 94 modules; sole failure was test_techdocs_audit_lib.TechdocsAuditBoundaryAgreementTests.test_a_segment_local_pattern_skips_the_ancestor_walk (183 ms against 150 ms under parallel load). Isolated TechDocs module rerun passed all 86 tests in 8.553 s; no threshold or runtime code changed. Earlier runs were invalidated by Xcode Git license/PATH and sandbox process-visibility issues; final run used Homebrew Python, Command Line Tools Git and host process access. Logs: /private/tmp/wf-post-git-guidance-tests-final.log and /private/tmp/wf-post-git-techdocs-recheck.log. No new green whole-suite receipt was produced; the prior receipt is stale after seed edits, so closure still requires a clean full-suite run. Seed gate closed; no commit or closure.

### Delivery review and repair cycle 1 — 2026-09-15

Thought / Readback: Independent code/QA, architecture/security and docs/release lanes reviewed frozen snapshot 04b26a6f5145443697a086114dbef331b338aa64334d9757bec03b02dcd1f746. They reproduced three required-AC defects: canonical rendered MCP entries rejected (SETUP-SURFACE-001), setup-owned conversion diagnostics naming upgrade (SETUP-OWNER-002, including false architecture restriction), and supported saved setup arguments rejected (SETUP-ARGS-003). Typed initial delivery and repair-start records precede mutations. Repair uses actual renderer forms, a shared bootstrap-safe setup parser, and owner-preserving diagnostics; no new feature scope or authority. Coordinator owns diagnostic/doc repair; assessor implementer owns configuration/parser/tests. Frozen reviewers do not author repairs.

Observe: Owner guidance repaired across shared migration, forward recovery, publication, verification and cleanup messages. Package-specific require_ready dispatch remains owner-aware. New SetupReceiptTests.test_setup_preflight_recovery_keeps_recorded_owner executes runtime/WAL failures through setup.session; source and setup receipt preserved. Setup reconciliation module passed 28 tests; archive-native cached-runtime test passed. Injecting the old wf_upgrade message at migrate_legacy makes the new setup-session regression fail by assertion (no errors), proving the control detects the defect. Architecture legacy-reader restriction now includes supported setup-owned conversion.

Observe / final verification: The initial architecture replacement missed a line-wrapped sentence; independent recheck caught it. Both architecture paragraphs were corrected and independently reverified against final snapshot 33c78644dbfe56d34e7a7adb9dcb3980ee2ca58931ec4d2a555d99bf05299b2e. All six delivery lanes approve. Full suite passed 9,096 tests across 94 modules (21 intentional skips), with no threshold changes. Prior timing failure is superseded by this green run. Runtime repairs are covered by actual renderer/parser producer tests and restored-defect mutation controls. Native Windows/Linux execution remains unclaimed.
