# Consolidate related memory, then archive only retired evidence

Change ID: `1u8r1-enh memory-retention-archive-cleanup`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-02
Wave: `1u8r2 memory-consolidation-and-drift-parser`

## Rationale

Rejected backfill candidates and superseded records currently remain as full markdown bodies in `docs/agents/memory/` until an operator invokes one `memory_reconcile(..., status="archived")` call per record. Related active records likewise remain split into overlapping fragments. The result is a working folder that grows indefinitely and an index that carries more low-value material than the next action needs. The framework needs a bounded consolidation-first path that replaces related lessons with one actionable playbook, a compact searchable metadata-only archive register for material worth preserving in project history, and a deliberate purge route for retired records with no such value.

## Requirements

1. Provide one bounded consolidation workflow that previews related records targeting the same canonical file or decision seam, proposes one concise replacement playbook, and never merges unrelated records merely because they are old.
2. The workflow must default to a dry run, return the exact source records, proposed replacement, and reasons it would skip a group, and limit each apply invocation. It must not alter an `active` or `candidate` record without an explicit reviewed consolidation decision.
3. When a consolidation is applied, create the replacement first, mark each source record superseded by it, then archive the source bodies through the existing state-derived archive transaction. The resulting active folder should retain the one replacement, not every historical fragment.
4. Replace `docs/agents/memory/pointers/` with one compact, atomically updated `docs/agents/memory-archive.md` register. It must carry only the archived record's stable ID, title, kind, targets, archive date, successor when present, and archive path needed for explicit lookup; it must not carry the archived summary, evidence, or keywords.
5. Finalized rejected backfill candidates have no durable lesson to consolidate: make them leave the active memory directory through the bounded retention decision, preserving source-event duplicate suppression whether the reviewed result is archive or purge.
6. Preserve existing protected-kind safeguards: decisions, operator preferences, and fragile-file records require explicit current-review eligibility confirmation before archival. Do not treat age alone as permission to archive.
7. Exclude archived bodies from ordinary semantic indexing, action-time briefings, active-memory counts, and graph extraction. Keep the compact archive register searchable as the explicit history router without loading every archive body. Keep the existing single-record `memory_reconcile(..., status="archived")` behavior and crash-recovery guarantees unchanged.
8. Render every new memory record with a blank line between its frontmatter/header block and `## Summary`, so the generated template is CommonMark-compliant and consistent with the repository documentation style.
9. Make archive versus purge an explicit reviewed retention decision for stale, superseded, and rejected memories: archive only when it remains important to project history; otherwise provide a dry-run-first permanent purge. Purge must remove the body and its register entry, refuse active/candidate records, retain the existing extra confirmation for protected kinds, and make the destructive nature and irreversibility clear in its response and documentation.
10. When an upgrade adds memory tools, reload reporting must distinguish server-side re-registration, notification dispatch state, and client adoption. A notification queued on an active event loop must not be described as completed delivery, and failure to resolve a newly added tool during the same model turn must not by itself be diagnosed as a host defect. Recovery guidance must check a fresh turn first, then reconnect, then restart the host if the tool list remains stale.
11. When this change advances `GRAPH_BUILDER_VERSION`, the installing upgrade must reconcile an existing `docs/RELIABILITY.md` graph-version claim before docs-lint only when the pre-extract claim exactly matched the pre-extract code constant and remains unchanged. Missing, ambiguous, or customized claims must not be overwritten.

## Scope

**Problem statement:** The memory lifecycle records rejection and supersession correctly, but leaves fragmented lessons and retired full bodies in the live directory. The folder—and potentially the index—ages indefinitely instead of converging on one useful record per related concern.

**In scope:**

- A dry-run-first, bounded consolidation path owned by the current memory mutation fence.
- Reuse of `archive_memory_record` while replacing pointer publication with a single archive-manifest update for every archival mutation.
- Backfill-finalization integration, retention eligibility reporting, and focused regression coverage.
- A documented one-time/periodic consolidation-and-cleanup procedure for existing related and retired records.
- A reviewed, explicitly destructive purge route for retired records that have been judged not important to project history, including records already archived after prior reconciliation.

**Out of scope:**

- Automatic archive/purge decisions based on age or status alone.
- Automatic age-based deletion or automatic archival of active/candidate records.
- Merging unrelated active records merely to meet the active-memory cap.
- Changing semantic search ranking beyond excluding archive bodies while retaining the compact register as a searchable history router.

## Acceptance Criteria

- [x] AC-1: A dry-run consolidation returns a deterministic, capped list of related memory groups, the exact source records, one proposed replacement, and skip reasons; it performs no filesystem mutation and does not group unrelated records.
- [x] AC-2: Applying a reviewed group creates one replacement playbook before superseding and archiving its sources via the existing atomic rename-and-manifest transaction; active and candidate records outside the selected group remain untouched, and an interrupted archive remains recoverable through the existing retry route.
- [x] AC-3: A finalized rejected backfill candidate is queued for bounded cleanup and, after the required eligibility judgment, moves out of `docs/agents/memory/` into `archive/` with one compact manifest entry instead of remaining as a full live body.
- [x] AC-4: Archived records remain discoverable through the searchable archive manifest and explicit history queries and continue to suppress duplicate backfill proposals, while ordinary memory loads, briefings, active-budget counts, semantic indexing, and graph extraction exclude archive bodies.
- [x] AC-5: Existing `memory_reconcile(status="archived")` single-record behavior, protected-kind checks, consolidation source links, archive-manifest recovery, and archive crash-recovery tests remain green.
- [x] AC-6: Documentation names the preview/apply procedure and makes explicit that consolidation is preferred for related actionable lessons, while retention review—not elapsed age—authorizes archival.
- [x] AC-7: A newly rendered memory record contains a blank line immediately before `## Summary`; its round-trip and docs-lint coverage remain green.
- [x] AC-8: The archive register contains only compact lookup metadata and remains searchable as the history router; archived bodies stay excluded from ordinary semantic indexing, and `memory_search` derives archive pointers from the register rather than scanning archive bodies.
- [x] AC-9: A reviewed retention decision archives only historically important stale/superseded/rejected records; a confirmed purge deletes those judged non-historic (including already archived records), removes their archive-register entry, refuses active/candidate records, preserves protected-kind confirmation, and reports an explicit irreversible-action warning.
- [x] AC-10: MCP reload output reports whether the tool-list notification was completed or only queued, does not equate dispatch with client adoption, and upgrade guidance requires a fresh-turn probe before reconnect/restart fallback; focused tests pin both completed and queued paths.
- [x] AC-11: A `GRAPH_BUILDER_VERSION` transition updates the exact pre-extract code-matched `docs/RELIABILITY.md` claim on the installing upgrade before docs-lint, including direct resume or a same-target full retry after interruption between extraction and the docs gate, while a customized or previously mismatched claim remains byte-for-byte unchanged and a different target cannot inherit the observation.

## Tasks

- [x] Trace `memory_validate`, `memory_reconcile_response`, `memory_backfill`, and `archive_memory_record`; define the smallest request/response shape for a bounded consolidation workflow.
- [x] Implement the dry-run and apply paths under the existing mutation lock/fence, creating a reviewed replacement before reusing archive eligibility and atomically updating the single archive manifest for sources.
- [x] Integrate finalized backfill rejections with the cleanup worklist without blocking source-event disposition or duplicate suppression.
- [x] Add focused tests for grouping correctness, preview purity, cap/pagination, protected-kind refusal, replacement-before-source archival, manifest update/recovery, and backfill/index exclusion behavior.
- [x] Correct the canonical memory-record renderer/template and add a focused formatting assertion for the blank line before `## Summary`.
- [x] Update the MCP tool surface and memory lifecycle documentation; render any affected prompt surfaces from canonical source.
- [x] Run focused tests, docs lint, and a small end-to-end fixture that verifies retired bodies leave the live directory and are absent from ordinary retrieval.
- [x] Compact the archive register, make it the searchable archive-pointer lookup source, and exclude only archive bodies from ordinary indexing.
- [x] Implement and document the reviewed archive-versus-purge decision with focused active/archived, protected-kind, and refusal coverage.
- [x] Correct tool-list notification reporting and upgrade recovery guidance, with focused completed-versus-queued regression coverage.
- [x] Reconcile the lint-bound graph-builder claim through the incoming `pre_docs_gate` extension, retain the guarded observation in the existing upgrade lock across recovery, and add exact-transition, interruption/retry, customization, and mismatch controls.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Consolidation contract and tests | implementer | — | `memory_records.py`, `memory_backfill.py`, memory tests |
| MCP surface and docs | implementer | lifecycle contract | `server_impl.py`, tool spec, memory README |
| Verification | qa-reviewer | both | mutation, recovery, and retrieval-exclusion probes |

## Serialization Points

- `memory_records.py` archive transaction, the cross-process mutation lock/memory fence, and `docs/agents/memory-archive.md` are shared write boundaries; cleanup and single-record reconciliation must not move the same record or rewrite the manifest concurrently.
- `server_impl.py` is the public MCP registration surface; add or alter a tool contract there only after the lifecycle shape is finalized.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — memory mutation and archival control path.
- `docs/architecture/testing-architecture.md` — retention batch and interrupted-archive coverage.
- `docs/specs/mcp-tool-surface.md` — new or extended bounded retention-cleanup contract.
- `docs/agents/memory/README.md` — operator procedure and archive semantics.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevents accidental or unrelated consolidation. |
| AC-2 | required | Preserves history and transaction safety while reducing active records. |
| AC-3 | required | Stops rejected backfill records from accumulating in the live folder. |
| AC-4 | required | Preserves retrieval without a per-record pointer directory or archive-body indexing. |
| AC-5 | required | Protects the established archive/recovery contract. |
| AC-6 | important | Makes the cleanup usable without hidden procedure. |
| AC-7 | important | Keeps generated memory records valid, readable Markdown. |
| AC-8 | required | Archived knowledge must not remain in the normal semantic corpus or require full-body scans. |
| AC-9 | required | Retired records need a deliberate history-retention decision rather than indefinite archival. |
| AC-10 | required | Newly shipped memory tools must surface through an honest, actionable upgrade contract. |
| AC-11 | required | The wave's graph-version bump must not make the installing upgrade fail its own docs gate. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-02 | Planned after observing 101 rejected upgrade-backfill candidates remain as full live files despite completed validation; revised to consolidation-first and one archive manifest by operator direction. | `memory_backfill` run `571d8ffe33a5d51e10c0c6639b6820fe`; `memory_reconcile` archive behavior; docs lint. |
| 2026-08-02 | Expanded by operator direction: archive register must be compact and non-semantic; a reviewed retention decision must archive only history-worthy records and purge the rest. | Archive run produced 117 entries and a 1,297-line register; targeted search still scanned archive bodies. |
| 2026-08-02 | Field-ran `Review memories`: consolidated the exact runner-identity decision pair into `1uamr-mem runner-identity-capture-and-testing-contract`, then purged both non-historic superseded source bodies. Repaired protected consolidation so `eligibility_confirmed` reaches each source archive transaction. | Active 66→65; live bytes 118,176→113,311; archive bodies unchanged at 13; focused memory suite 183/183 passed. |
| 2026-08-02 | Upgrade feedback showed two newly added memory tools were re-registered server-side but not callable in the same Claude Code turn. Follow-up established that current reload output can label an active-loop `create_task(...)` as sent before completion and cannot prove client adoption; fold an honest dispatch-state and fresh-turn recovery contract into this change before delivery review. | `perform_mcp_reload`; Claude Code 2.1.128+ changelog support for MCP `list_changed`; local Claude Code 2.1.220. |
| 2026-08-02 | Corrected reload reporting to distinguish queued, completed, failed, and not-needed dispatch states; made client adoption explicitly unobservable; and changed upgrade recovery to fresh turn, reconnect, then restart. | `WaveMcpReloadTests`: 13 tests passed, including completed and active-loop queued paths. |
| 2026-08-02 | Repaired final review findings: consolidation now preflights every source before mutation, protected refusal is byte-pure, bulk retired archival was removed, and automatic upgrade reload diagnostics reach the caller. | Known-bad consolidation probes pass; full framework suite: 6,741 tests across 61 files passed; final package `wavefoundry-1.15.0.pggr.zip`. |
| 2026-08-02 | Repaired current-receipt code, QA, and architecture findings: purge dispositions now survive deletion; consolidation previews are detailed and capped at five sources, replacement content uses canonical validation, and caught partial applies roll back for retry; purge carries destructive MCP metadata; archive-register indexing docs and ADRs now match the implementation. | Fresh known-bad probes pass for purge resurrection/refusal/protection, 12-record bounds and continuation, secret refusal, second-source rollback/retry, tool annotations, and semantic/graph archive boundaries; canonical suite: 6,748 tests across 61 files passed. |
| 2026-08-02 | Closed the index-reset/fresh-clone review gap with one repo-visible, non-indexed, SHA-256-only purge-disposition authority; setup and upgrade preserve it byte-for-byte. Rebuilt and byte-verified the repaired local 1.15.0 package. | Index-reset known-bad now remains suppressed; memory file 191/191 and canonical suite 6,748/6,748 passed; `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.15.0.pgh2.zip` (`1.15.0+pgh2`), SHA-256 `72c76857ad1907122215abe5eec6a39a252093b76f872d661d10f727fb53dde7`; packaged `server_impl.py`, `memory_records.py`, `indexer.py`, `index_state_store.py`, and `VERSION` match the working source byte-for-byte. |
| 2026-08-02 | Tightened the purge-disposition authority after independent QA and architecture re-review: schema version must be the exact JSON integer `1`, and every digest must already be a lowercase 64-character string. | Boolean/float schema versions and numeric digest entries now fail closed; all three independent reviewers passed the final bytes; canonical suite: 6,750 tests across 61 files passed. Final package `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.15.0.pgh7.zip` (`1.15.0+pgh7`), SHA-256 `3874c6f23fa088a441b5e2f158417a5007dce5676dd10754f3b0ec41cd6452a2`; critical runtime files and `VERSION` match source byte-for-byte. |
| 2026-08-02 | Closed the final legacy-pointer review gaps: migration preflights every entry before deletion, rejects symlinks and unrecognized residue without mutation, semantic and graph direct-input seams exclude the retired path, lint catches any residual entry type, and current retrieval terminology is archive-register based. | Focused integration pass: 2,377 tests; canonical suite: 6,758 tests across 61 files, all passing; `wf_validate_docs`: clean. Final package `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.15.0.pghf.zip` (`1.15.0+pghf`), SHA-256 `7ba959bb13f44c109937111ebfddd8aa6967c2cd453bd2259e75cb3bd39c80e5`; 11 critical runtime, prompt, and version files match source byte-for-byte. |
| 2026-08-02 | Repaired the final red-team purge failure: a body now stages under the index-excluded archive tree, register publication failure rolls it back, and either staging interruption window converges on retry; an error response no longer hides irreversible body loss. | Known-bad publication-failure probe now preserves the body and reports a purge retry route; 199 memory tests and canonical suite 6,761 tests across 61 files passed. Final package `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.15.0.pghk.zip` (`1.15.0+pghk`), SHA-256 `25ae44cd92c05116bcb2c0b48f15db32edc698ae0085aeacc1a88bb4554abf41`; 11 critical runtime, prompt, and version files match source byte-for-byte. |
| 2026-08-02 | Closed the staged-retry authorization/finality gap found by final independent review: normal and recovery purges now share one source resolver that rejects ambiguous, ineligible, protected-unconfirmed, malformed, and symlink bodies before deletion; staged evidence-derived records persist source-event finality first. | Public-path staged active/candidate, protected, malformed, symlink, and source-event counterexamples pass; memory suite 202/202 and canonical suite 6,764 tests across 61 files passed. Final package `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.15.0.pghn.zip` (`1.15.0+pghn`), SHA-256 `e9b09a535de88cfde6362f57ad02c852d522f410db3ed9644416b4c04c264465`; packaged purge implementation files match source byte-for-byte. |
| 2026-08-02 | Field upgrade pgg9 → pghn exposed that the wave's graph-builder bump made docs-lint reject the still-44 `docs/RELIABILITY.md` claim. Repaired the installing-upgrade path in the incoming extension: snapshot only a unique pre-extract code/doc match, then advance it before docs-lint only if the claim remains unchanged. | `HistoricalMemoryUpgradeExtensionBootstrapTests`: 12/12 passed; complete upgrade module: 433/433; canonical suite: 6,767 tests across 61 files, all passing; `wf_validate_docs`: clean. Repaired package `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.15.0.pghx.zip` (`1.15.0+pghx`), SHA-256 `547260159febdc52f055c9b71346f588fde82aa9a7981707ad550def94d1bdb0`; packaged `upgrade_extensions.py` matches source byte-for-byte. |
| 2026-08-02 | Architecture retry review found the pre-extract graph-version observation was process-local, then found a full retry reinitialized the lock and discarded the newly durable value. Persisted the guarded observation in the existing upgrade lock, retain snapshot-bearing stale state until the requested target is known, carry it through lock reinitialization only for the identical target version and verified package digest, load it directly during recovery, and clear it after successful reconciliation. | Added a full-retry interruption regression using real stale-lock handling, lock reinitialization, a fresh context, and two distinct temporary paths for identical package bytes, plus different-version and different-package rejection controls. Complete upgrade module: 435/435; canonical suite: 6,769 tests across 61 files; docs validation clean. Final package `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.15.0.pgi7.zip` (`1.15.0+pgi7`), SHA-256 `11addd3cb22050ee8449c7725938c99bdc6be0ac753757d258273d82ed13f22e`; packaged extension, lock library, upgrade runner, and version marker match source byte-for-byte. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- |
| 2026-08-02 | Keep full archive bodies, but replace the per-record pointer directory with one searchable archive manifest. | Full bodies are required for explicit history retrieval, duplicate-suppression provenance, and recoverable archive transactions; one compact metadata-only manifest provides ordinary discovery without indexing every body or keeping one pointer file per record. | (a) Delete archive bodies: rejected because it discards history and requires a redesign of source-event duplicate suppression and recovery. (b) Keep one pointer per record: rejected because it creates avoidable file and index clutter. (c) Archive every non-active record immediately: rejected because related active records would remain fragmented and protected records need review. |
| 2026-08-02 | Use the archive register only as an explicit lookup index; archive only reviewed history-worthy records and purge the rest. | A summary-rich manifest re-indexes retired content. Status alone is not a retention decision: historical importance determines archive versus purge, while protected kinds retain an extra confirmation safeguard. | (a) Keep summaries/evidence in the register: rejected because it defeats index exclusion. (b) Archive every retired record: rejected because Git already preserves repository history and low-value records should not accumulate. (c) Purge automatically by age/status: rejected because historical importance requires review. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A group merges unrelated lessons. | Canonical-target/seam grouping, dry-run output, explicit reviewed replacement, and small apply cap. |
| Archive/manifest transaction regression loses discoverability. | Reuse `archive_memory_record`; atomically rewrite the manifest under the existing fence and extend recovery tests. |
| One shared manifest becomes a merge/conflict hotspot. | Keep entries deterministically ordered, update under the existing mutation lock, and make every retry derive the manifest from archive bodies. |
| Cleanup changes duplicate suppression or normal retrieval. | Pin ordinary versus history retrieval and source-event duplicate tests. |
| Backfill repeatedly creates then archives low-value candidates. | Keep cleanup bounded and use the observed candidate volume as an input to later proposal-quality work; do not expand this change into generator redesign. |
| Purge removes a record that later proves useful. | Require a reviewed non-historic decision, preserve protected-kind confirmation, use a dry run, and make the action irreversible in the response. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
