# Events-Only Review Evidence Authority

Change ID: `1to8f-enh events-only-review-evidence-authority`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-27
Wave: `1tomw events-only-review-evidence-authority`

## Rationale

`docs/waves/<wave>/events.jsonl` already contains the complete canonical review ledger, while `docs/waves/review-evidence-adoptions.json` stores a second per-wave count and prefix hash solely to remember the last accepted ledger prefix. The one-time self-hosting conversion also left `docs/waves/review-evidence-migration.json`, a migration manifest for a transition that has already completed and whose migrator will be removed by this change. These project-global sidecars create shared churn and retain authority/migration machinery after the canonical per-wave representation is established.

The extra state does not provide tamper-proof history. It can detect a ledger rollback only while the separate receipt survives unchanged; source control or backups are the appropriate historical authority when rollback investigation is required. Wavefoundry remains usable without Git, but a non-Git project will receive structural, transactional, and relationship integrity—not detection that a structurally valid older copy of the entire local ledger was restored.

Make the contract proportional and explicit: `events.jsonl` is the sole machine authority; `review-evidence-source: events.jsonl` identifies waves using that authority; canonical parsing, schema/relationship validation, atomic writes, locking, and idempotent replay protect ordinary corruption, interruption, and concurrency. Do not add an in-ledger checksum or hash chain: a checksum stored in the same log cannot prove that its own tail was not deleted.

## Requirements

1. **One review authority.** Treat the fixed sibling `docs/waves/<wave>/events.jsonl` as the only canonical review-evidence state. Keep the exact `review-evidence-source: events.jsonl` declaration as the applicability marker and keep `wave.md` projections non-authoritative. Remove the project-wide adoption ledger and every count/hash receipt.
2. **No replacement checksum scheme.** Do not add terminal checkpoint records, per-event hashes, prefix hashes, Merkle state, or a receipt in `wave.md`. Document that a same-log hash cannot detect valid tail deletion and that Git/backups may be used for historical rollback analysis without becoming a Wavefoundry runtime dependency.
3. **Fail closed on the authority that remains.** A wave carrying the source declaration must fail lifecycle validation when its fixed ledger is missing, unreadable, noncanonical, malformed, schema-invalid, or relationship-invalid. Remove the external-receipt-only diagnostics (`proof ahead`, `prefix mismatch`, `unadopted suffix`, durable-adoption downgrade) and do not manufacture equivalent state elsewhere.
4. **Preserve transactional correctness.** Keep typed event creation, canonical serialization, atomic ledger replacement, project-local cross-process serialization, request identity, and exact-replay recovery. Rename surviving Python symbols and APIs around their actual purpose (review-event mutation), but preserve the existing physical lock pathname `.wavefoundry/locks/review-evidence-adoptions.lock` as a cross-version coordination ABI: an already-running 1.14/1.15 process and the upgraded process must still contend on the same OS lock. After the ledger authority commit, projection failure must remain visible and replayable without appending duplicate events.
5. **Delete the adoption and completed-migration subsystems completely.** Remove adoption-ledger constants, readers, writers, path guards, proof helpers used only by adoption, validators, persistence calls, response fields, diagnostics, exports, compatibility shims, and migration-only inline/adoption helpers. Delete `docs/waves/review-evidence-adoptions.json`, `docs/waves/review-evidence-migration.json`, the obsolete `migrate_self_host_review_events.py` migrator and its dedicated tests/package assertions. Do not retain aliases, fallbacks, dual writes, dormant feature flags, v1/v2 branches, migration-manifest readers, or completed-migration resumability code. The retained legacy-named lock *file* is not adoption authority and is the sole explicit residue exemption; its code symbols and documentation describe review-event mutation.
6. **Close every live consumer.** Reconcile server lifecycle handlers, dashboard projection/status reads, wave lint/CLI validators, index inclusion/exclusion logic, runtime-lock handling, upgrade/setup/install/package paths, renderers, generated prompts, seeds, architecture/spec/contributing docs, codebase-map generation, and tests. Canonical wave `events.jsonl` files remain excluded from semantic indexing by their fixed wave-folder role rather than by consulting retained adoption state.
7. **One-way install and upgrade behavior.** New installs create only the source declaration, an empty `events.jsonl`, and generated projections. Upgrade removes both obsolete project-global JSON files (`review-evidence-adoptions.json` and `review-evidence-migration.json`) without reading either as authority or migration input, leaves each existing `wave.md` and `events.jsonl` byte-for-byte untouched, renders the new carriers, and reloads/restarts affected processes through the established upgrade path. The temporary typed-inline format never shipped: 1.14.0 introduced the external ledger, while supported earlier releases have prose-only historical waves. Therefore remove `externalize_adopted_inline_wave_locked` and the general-upgrade inline bridge rather than carrying a fallback. Upgrade fixtures must prove a leap from a representative pre-1.14 release preserves prose history and a 1.14+ upgrade preserves external ledgers. Keep using the stable physical lock pathname so old and new processes cannot split coordination during cutover.
8. **Historical records remain historical.** Do not rewrite closed wave narratives merely because they describe the design that existed when they were executed. Residue checks distinguish live product/contracts from archived wave evidence. Current architecture, specs, prompts, seeds, generated surfaces, and active plans must state only the events-only contract.
9. **Prove the retained guarantees and the removed boundary.** Tests must cover canonical success, declared-but-missing authority, malformed/noncanonical bytes, schema and relationship failures, concurrent writers, interrupted projection plus exact replay, duplicate-request idempotency, install/upgrade/package output, index exclusion, and absence of adoption-only runtime behavior. A negative control must demonstrate that restoring a complete older but internally valid ledger is no longer locally detectable without Git/backups, matching the documented boundary rather than overstating protection.
10. **Executable deletion census.** Add or extend a focused census test that fails if live shipped code, current seeds/rendered carriers, install/upgrade/package assets, or current architecture/spec docs retain the removed adoption file name, adoption-only API symbols, adoption-only diagnostics, or the old lock name. The census may explicitly exclude archived closed-wave records and this change's decision history.

## Scope

**Problem statement:** Review evidence has one substantive authority but also maintains a second global receipt ledger whose only unique guarantee is detection of a valid ledger rollback while the receipt independently survives. That guarantee is disproportionate to the local review-ledger threat model and creates avoidable shared state and maintenance surface.

**In scope:**

- Remove `docs/waves/review-evidence-adoptions.json` and `docs/waves/review-evidence-migration.json`, plus their creation, mutation, validation, upgrade, dashboard, lint, indexing, packaging, and documentation paths.
- Remove bounded prefix-proof/hash computation when no remaining independent consumer requires it.
- Remove the completed self-host inline/adoption migration path, its manifest, dedicated script/tests, and package-presence assertions; Git retains the historical implementation if forensic analysis is ever needed.
- Rename the retained lock's Python symbols and public description around review-event mutation while deliberately keeping its physical pathname stable as the cross-version coordination ABI.
- Simplify lifecycle transaction ordering to ledger commit followed by generated Markdown projection, retaining exact-replay recovery.
- Update canonical seeds first, regenerate owned surfaces, and update hand-authored architecture/spec/contributing documentation.
- Add install, upgrade, package, concurrency, failure-recovery, index-exclusion, and residue-census coverage.

**Out of scope:**

- Making Git mandatory or invoking Git during ordinary review validation.
- Building a Git-history audit tool in this change; existing Git tooling can investigate rollback when needed.
- Cryptographic signatures, remote transparency logs, trusted timestamps, Merkle trees, or hostile-local-operator tamper resistance.
- Rewriting closed historical wave records to erase descriptions of the former design.
- Changing the semantic review record schema, actionability model, lane freshness, independence rules, or projection content except where adoption-only wording/state is removed.
- Renaming the existing physical project-global lock path or replacing it with per-wave locking; either change requires a separately designed all-writer quiescence/versioning protocol.

## Acceptance Criteria

- [ ] AC-1: A newly created wave contains the exact source declaration, an exactly empty sibling `events.jsonl`, and generated review projections, and neither creates nor references `review-evidence-adoptions.json` or `review-evidence-migration.json`.
- [ ] AC-2: Prepare/review/event/close/dashboard/lint paths derive review state only from the declared fixed sibling ledger and reject missing, unreadable, noncanonical, schema-invalid, and relationship-invalid ledgers without consulting any receipt state.
- [ ] AC-3: Typed append remains serialized and atomic; a real two-process writer race proves no lost append through the retained physical lock pathname, and a process-termination/fault-injection matrix around ledger replacement and projection followed by exact replay proves recovery without duplicate records. The contract explicitly claims atomic visibility and replay recovery, not power-loss durability or `fsync` guarantees.
- [ ] AC-4: No event, `wave.md` marker, SQLite row, or replacement sidecar stores a ledger count/hash checkpoint or hash chain.
- [ ] AC-5: Upgrade deletes both obsolete project-global review-evidence JSON files without parsing or migrating them; removes the never-shipped inline bridge; preserves every existing `wave.md` and `events.jsonl` byte-for-byte; proves representative pre-1.14 prose-only and 1.14+ external-ledger leap upgrades; and keeps old/new writers serialized on the stable physical lock path with no compatibility reader or fallback.
- [ ] AC-6: Canonical wave-folder `events.jsonl` files remain excluded from semantic indexing without adoption-state lookup; unrelated JSONL outside that fixed role retains the documented indexing behavior.
- [ ] AC-7: The obsolete adoption APIs, diagnostics, constants, exports, migration-only helpers/script, migration-manifest code, dedicated dead tests, generated guidance, and packaging references are removed rather than left dormant; neither obsolete JSON sidecar exists and the executable live-surface census is clean except for the one documented stable lock-path literal.
- [ ] AC-8: Seed 209 and every current rendered/hand-authored contract explicitly state the events-only authority and the honest boundary: valid whole-ledger rollback is detectable only through an external history source such as Git or backups, which remains optional.
- [ ] AC-9: A negative control restores an older internally valid ledger and proves local structural validation accepts it, while corruption, partial writes, invalid relationships, and declared missing authority remain rejected.
- [ ] AC-10: Focused review-evidence, lifecycle, dashboard, lint, indexer, renderer, install/upgrade, and packaging tests pass; the full canonical framework suite and docs lint pass after the deletion.

## Tasks

- [ ] Inventory every live producer, reader, validator, diagnostic, response field, lock, upgrade hook, migration helper, package asset, seed/rendered carrier, architecture/spec statement, and test tied to adoption state.
- [ ] Reduce `review_evidence.py` to direct declared-ledger validation and event/projection mutation; delete adoption proof and migration-only code and reconcile exports.
- [ ] Reconcile all server, dashboard, lint, CLI, indexer, runtime-lock, setup/install/upgrade/package, and renderer call sites.
- [ ] Rename the retained review mutation lock's symbols/descriptions, preserve its physical path, and add one-way cleanup for both obsolete project-global JSON files with no fallback or manifest parsing.
- [ ] Update seeds 100/209 first, regenerate owned prompts/agent surfaces, and reconcile current architecture/spec/contributing docs plus generated codebase map.
- [ ] Delete obsolete migration scripts/tests and replace adoption-oriented fixtures with events-only authority, concurrency, crash-replay, upgrade-preservation, index-exclusion, and boundary controls.
- [ ] Add the executable live-surface residue census with an explicit historical-record exclusion.
- [ ] Run focused suites, mutation/negative controls, the canonical full suite, docs lint, and `git diff --check`; record exact evidence before delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Authority simplification | implementer | — | Remove proof/validator/migration core while preserving direct ledger validation and append transaction. |
| Runtime consumer reconciliation | implementer | Authority simplification | Server, dashboard, lint/CLI, indexer, lock, setup/upgrade/package. |
| Canonical contracts and rendering | docs-contract-reviewer + implementer | Authority simplification | Seeds first; regenerate owned surfaces; preserve archived history. |
| Verification and deletion census | qa-reviewer | Runtime consumer reconciliation; contracts | Independent controls for retained guarantees, removed rollback boundary, and zero live residue. |
| Delivery review | wave-council | all workstreams | Focus on concurrency/replay preservation and whether any second authority survived under a new name. |

## Serialization Points

- `review_evidence.py` API deletion and server/lint/dashboard import reconciliation must land as one coherent edit; intermediate missing imports are not a valid checkpoint.
- Seed 100/209 changes precede regeneration of prompts and agent carriers.
- Upgrade cleanup must retain the existing physical lock path across old/new process generations; only symbols and descriptions change in this wave.
- Both obsolete project-global JSON files and the migration script are deleted only after no live producer/consumer/package assertion requires them; final residue census runs after generated surfaces and codebase map are refreshed and permits only the documented lock-path literal plus archived history.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — remove the adoption authority/lock and document direct ledger commit → projection ordering.
- `docs/architecture/domain-map.md` — remove the adoption-ledger write boundary and rename the retained coordination lock.
- `docs/architecture/testing-architecture.md` — document the rollback-boundary negative control and deletion census if the review-evidence verification matrix is described there.
- `docs/architecture/cross-cutting-concerns.md` — update only if it currently promises retained-prefix or Git-independent rollback detection.
- `docs/specs/mcp-tool-surface.md` — remove adoption persistence/diagnostic fields and state the direct ledger contract.
- `docs/contributing/review-and-evals.md` — update the canonical verification/evidence table.
- `docs/ARCHITECTURE.md` — regenerate/update only if child summaries or current-state text mention the removed authority.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | New-wave creation must stop recreating the removed state. |
| AC-2 | required | Direct authority validation is the retained safety boundary. |
| AC-3 | required | Simplification may not regress concurrency or crash recovery. |
| AC-4 | required | Prevents recreating the same second-authority problem under another name. |
| AC-5 | required | Install/upgrade/package paths must converge existing projects cleanly. |
| AC-6 | required | Machine ledgers must remain out of semantic retrieval without the old lookup. |
| AC-7 | required | Operator explicitly requires complete old-code removal. |
| AC-8 | required | The reduced guarantee must be stated honestly across canonical contracts. |
| AC-9 | required | An executable negative control prevents future overclaiming. |
| AC-10 | required | Cross-cutting deletion requires full verification. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-27 | Planned the events-only authority and performed an initial exact-token deletion census across framework runtime, tests, seeds, install assets, current docs, and historical records. No implementation started. | Current implementation uses `review_event_prefix_proof`, `record_protocol_state_locked`, and `validate_adopted_protocol_state`; exact search found live consumers in review evidence, server, dashboard, lint, indexer, upgrade, renderers, packaging/tests, seeds, architecture, and specs. The census also found the completed self-host migrator as the sole live producer/consumer of `review-evidence-migration.json`, plus dedicated migration and package-presence tests. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-27 | Make `events.jsonl` the sole review authority and remove receipt hashes entirely. | It is the simplest contract matching the local threat model; Git/backups are the appropriate optional history authority, while runtime validation remains Git-independent. | **Receipt inside `wave.md`: rejected** because it preserves second-state choreography and rolls back with the wave. **Checkpoint/hash chain inside `events.jsonl`: rejected** because a same-log proof cannot detect deletion of its own tail. |
| 2026-07-27 | Keep the existing source declaration as the applicability marker. | It distinguishes an adopted wave from historical waves without duplicating review facts or hashes. | Infer adoption solely from file presence: rejected because an empty/missing file would make applicability ambiguous. |
| 2026-07-27 | Preserve a project-global mutation lock but rename it around review-event mutation. | The lock prevents real concurrent lost-update risk and is independent of the removed rollback receipt. | Delete all locking: rejected because concurrency protection is still load-bearing. Per-wave locks: not selected absent measured contention requiring added machinery. |
| 2026-07-27 | Do not rewrite closed historical wave narratives during the cleanup. | They are evidence of decisions made under the prior implementation, not live product contracts. | Repo-wide textual erasure: rejected because it would falsify history and create noisy archive churn. |
| 2026-07-27 | Delete `review-evidence-migration.json` together with its completed one-time migrator. | The migration already established canonical per-wave ledgers; retaining its resumability manifest and executable only preserves dead transitional state. Git retains the exact former code and manifest history if the migration ever needs forensic reconstruction. | Keep the manifest as an audit artifact: rejected because it is global churn and duplicates facts now embodied by the per-wave ledgers and repository history. Move its facts into `wave.md`: rejected because closed migration history already documents the transition and no runtime consumer needs another projection. |
| 2026-07-27 | Remove the general typed-inline upgrade bridge, but prove both sides of the released-version boundary. | Wave `1slep` records that the typed-inline protocol never shipped and 1.14.0 introduced external `events.jsonl`; supported earlier releases therefore carry prose history, not migration-compatible typed-inline authority. Representative pre-1.14 and 1.14+ leap-upgrade fixtures make this premise executable. | Keep a version-gated compatibility reader: rejected because it preserves a never-shipped format and conflicts with the operator's no-fallback direction. Raise the whole upgrade floor: rejected as unnecessary when released history has no typed-inline state to migrate. |
| 2026-07-27 | Preserve `.wavefoundry/locks/review-evidence-adoptions.lock` as a physical coordination ABI while deleting adoption semantics. | An old MCP process and upgraded process must contend on one OS lock. Renaming the file without an all-host quiescence mechanism creates two independent writer domains. | Rename/delete during upgrade: rejected because `wf_reload_mcp` cannot prove every host process stopped. Dual-lock acquisition: rejected as extra transitional machinery when a stable opaque pathname is sufficient. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A valid older ledger is restored in a non-Git project and local validation cannot detect it. | State this boundary explicitly; preserve canonical/relationship validation; use Git or backups when historical rollback detection matters. Do not imply cryptographic protection. |
| Removing adoption calls accidentally removes serialization or idempotent replay. | Keep the physical mutation lock, rename only its code meaning, and pin a real subprocess append race plus post-commit projection-replay fixtures before deleting old tests. |
| Upgrade deletes an artifact still needed by an old process. | Coordinate through the established upgrade reload/restart boundary; converge to the new implementation with no dual-format fallback. |
| Adoption terminology survives in generated or rarely used paths. | Run an executable census over shipped code/assets/current contracts, with explicit exclusions only for archived history and the stable physical lock-path literal. |
| A skipped-version upgrade silently needs the never-shipped inline bridge. | Pin released-version fixtures: pre-1.14 prose waves are byte-preserved; 1.14+ external ledgers are byte-preserved; no target history is inferred or rewritten. |
| Fixed-path event-ledger indexing changes unintentionally. | Add positive canonical-wave exclusion and negative unrelated-JSONL controls without consulting removed state. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
