# Remove operational evidence from default retrieval

Change ID: `20aqf-debt operational-evidence-index-scope`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: `2087n workflow-overhead-reduction`

## Rationale

The audit found about 9008 code chunks and 1443 docs chunks from ten waves' operational evidence; source Q&A surfaced report payloads ahead of implementation. A walker version bump currently forces a full rebuild, so this exclusion also needs a bounded removal-only transition.

Evidence: the recent-ten-wave audit and final cleanup are summarized in `docs/waves/2071p bounded-reconciliation-reporting/wave.md` and `docs/waves/2071n profile-skip-qualification/wave.md`. Existing unique proof and ledger citations remain available. This plan does not claim future implementation tests passed.

## Requirements

1. Derive operational evidence paths from discovered wave records under configured live and archive roots, including supported nested layouts: descendants of a wave's evidence directory and owned evidence-* directories. Do not exclude every directory named evidence or every wave document.
2. Apply the boundary consistently to docs/code discovery, explicit indexing inputs and graph extraction. Preserve wave.md, admitted change docs, project source and curated proof outside operational evidence under existing eligibility rules. Direct file reads and typed ledger tools remain available; machine authority remains excluded.
3. On an existing compatible index, remove formerly indexed operational rows from vectors, lexical state, file hashes and graph publication with truthful freshness. Publish consistent state without re-embedding or re-extracting unchanged eligible source. Recompute graph-derived membership when actually required by removals.
4. Handle the exact removal-only policy transition selectively; do not disguise incompatible model/chunker/walker state as compatible or silently retain stale rows. Older unknown metadata and independently incompatible states keep their existing safe recovery. Report one-time removal work and bounded measured counts rather than promise universal upgrade speed.
5. Do not use .aiignore to hide direct review reads, introduce a separate index, scan unrelated evidence folders, or require full consumer suites on upgrade. Preserve unreadable-path protection and failed-publication recovery.
6. Keep operational evidence classification separate from machine_authority exclusions so reconciliation scanning and direct tool reads do not inherit the retrieval-only rule.

## Scope

**Problem statement:** The audit found about 9008 code chunks and 1443 docs chunks from ten waves' operational evidence; source Q&A surfaced report payloads ahead of implementation. A walker version bump currently forces a full rebuild, so this exclusion also needs a bounded removal-only transition.

**In scope:** the named behavior, its existing module owners, finite contract regressions and affected documentation. Canonical seeds are edited first; generated lifecycle/role surfaces are regenerated from those seeds, not patched as a substitute.

The compatible transition accepts only the immediately prior known walker policy with unchanged model, chunker, include flags and other configuration identities. It enumerates formerly indexed paths to derive removals, rather than trusting a version label alone. Graph extraction and embedding reuse are separate from recomputation of graph-derived communities. Unknown prior policies retain existing recovery. A missing/unreadable configured wave root must not authorize deletion of its old rows.

**Out of scope:** graph-query provenance wave2071o, unrelated scanner repairs, mandatory-lane removal, weakening full lifecycle gates, rewriting ledger history, release/tag/publish, new broad maintenance during consumer upgrades and product-wide refactoring. No implementation is authorized by this planning pass.

## Acceptance Criteria

- [x] AC-1: Configured live/archive and nested wave operational evidence is omitted from default docs/code/graph results while wave summaries, admitted docs, eligible project source and near-miss evidence directories remain available. Oracle: real indexed mixed-corpus fixture and query results.
- [x] AC-2: Incremental upgrade of a previously populated compatible index removes stale operational rows across publication stores and retains correct remaining queries. Oracle: seeded-old-index to current-publication transition with exact row/path checks.
- [x] AC-3: An exclusion-only transition makes zero unchanged-source embedding/extraction calls; necessary derived graph recomputation is counted separately. Incompatible identities and failed/unreadable publication retain safe existing behavior. Oracle: instrumented update and failure controls, with bounded timing/count observations.
- [x] AC-4: Direct review file reads and typed event-history access still reach retained evidence; no separate index or consumer qualification pass is introduced. Oracle: public read/ledger controls alongside default-search exclusion.

## Tasks

- [x] Implement the scoped requirements in the existing owning modules and canonical instructions.
- [x] Execute the finite positive and known-bad controls named in the ACs through actual public/registered paths; record observations and limits in wave.md.
- [x] Update affected architecture and operator contracts; regenerate affected local surfaces from canonical seeds.
- [x] Run required independent delivery review and fresh framework qualification after source edits; consolidate useful long-run evidence and current handoff without routine per-seat files.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| implementation | implementer | readied wave and later operator activation | Existing module owners; no code edit during readiness. |
| focused verification | qa-reviewer | implementation | AC-scoped real controls; preserve independent judgment. |
| delivery lanes | required specialists | verified implementation | Existing selected authority, no new roster. |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/graph_indexer.py`
- `docs/architecture/chunking-and-indexing-pipeline.md`
- `docs/architecture/search-architecture.md`
- `docs/architecture/graph-index-system.md`

One implementer owns shared server_impl.py, seed190, build-and-verification and generated outputs. Qualification, memory and advisory changes settle their APIs before the compact-workflow instructions describe them. Index work may be isolated; final integration and canonical receipt run are serialized after all framework edits. Reviewer contexts do not edit source or plans.

## Affected Architecture Docs

- `docs/architecture/chunking-and-indexing-pipeline.md`
- `docs/architecture/search-architecture.md`
- `docs/architecture/graph-index-system.md`
- `docs/architecture/performance-budget.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | All four ACs are required because discovery, stale-row removal, bounded upgrade work and direct-evidence access form one retrieval contract. |
| AC-2 | required | All four ACs are required because discovery, stale-row removal, bounded upgrade work and direct-evidence access form one retrieval contract. |
| AC-3 | required | All four ACs are required because discovery, stale-row removal, bounded upgrade work and direct-evidence access form one retrieval contract. |
| AC-4 | required | All four ACs are required because discovery, stale-row removal, bounded upgrade work and direct-evidence access form one retrieval contract. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-09 | Consolidated plan; implementation and delivery ACs remain unmet. | Current requirements and named AC oracles; operator requested create/prepare/review. |

| 2026-10-09 | Readback: Exclude only record-owned operational evidence from default semantic/graph retrieval, retaining direct reads and summaries; compatible prior-policy removal reuses unchanged source work (AC-1–4). Update indexer/graph discovery, tests and indexing contracts. Before: operational captures compete with source; after: removed rows without unrelated embeddings/extraction. | Operator implementation request; admitted ACs unchanged. |
| 2026-10-09 | Implemented retrieval-only record discovery, walker 17 exclusion, exact known walker 16 transition and graph fragment reuse; preserved existing dirty source. Missing/unreadable roots protect actual prior rows, including subsequent restoration under walker 17. Previously absent semantic layers stay absent unless explicitly requested. | `operational_evidence.py`, `indexer.py`, `graph_indexer.py`; policy helper registered in immutable loaded-source compatibility checks. No machine-authority, reconciliation, ignore policy or consumer qualification changes. |
| 2026-10-09 | AC-1–4 focused proof complete: mixed live/archive nested corpus, explicit semantic and graph inputs, populated old index resident removal, zero source work, model/chunker/config/include/unknown-walker rejection, failed-publication retry, absent/unreadable/restored roots, zero-removal metadata publication, independent graph builder identity and docs/code/graph-only layer controls. Registered `code_read`, `wf_review_event` create/list and `docs_search` paths retain direct evidence access and exclude default retrieval. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_indexer.py -k OperationalEvidencePolicyTests`: 9 tests OK, 13.802s. Real canonical SQLite vector/lexical/graph publication with deterministic embedding spies; only `index.sqlite` is created. Local capture `/private/tmp/wf-20aqf-final-focused.log` is routine scratch, not required durable proof. |
| 2026-10-09 | Compatibility protection verified, including same-stat helper replacement before lazy import and old compiled helper after source installation. Eight guard mutants were rejected by named tests. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_index_compatibility.py`: 19 tests OK, 4.812s. Mutants removing exclusion, accepting unknown walker/config, removing root protection or graph carveout, accepting changed graph builder, omitting source registration, or omitting loaded-helper registration each fail the matching `OperationalEvidencePolicyTests` or `ProcessBarrierTests` oracle. |
| 2026-10-09 | Named known-bad oracles: disabled exclusion fails `test_mixed_corpus_and_explicit_inputs_exclude_only_record_owned_evidence`; accepting unknown walker or changed config/flags fails `test_unknown_or_changed_policy_does_not_take_removal_transition`; disabled root protection fails `test_missing_and_unreadable_wave_roots_preserve_previously_indexed_rows`; disabled graph compatibility exception fails `test_compatible_prior_policy_removes_all_residents_without_source_work`; accepting changed graph builder fails `test_independent_graph_identity_change_requires_fresh_extraction`. | Final runtime-injection mutants each produced the intended assertion failure; no source file was modified while coordinator qualification was starting. |
| 2026-10-09 | Immutable helper guard oracles: omitting helper from the source registry fails `test_operational_evidence_source_replacement_is_stale_before_lazy_import`; omitting helper loaded-source registration fails `test_compiled_old_evidence_policy_cannot_capture_new_installed_bytes`. | Both isolated temporary-source mutants changed the expected stale-runtime refusal into acceptance and failed their named `ProcessBarrierTests` assertion. |
| 2026-10-09 | Bounded old-index observation: 3 operational paths removed, 0 embedding calls, 0 source extraction calls, derived graph communities recomputed separately; elapsed 0.359s. Initial broad indexer run exposed absent roots being exported as physical walk errors; fixed and all five named failing controls passed. | Actual populated fixture run, not a universal performance claim. `StorageRebuildSourceTests.test_strict_census_hashes_current_sources_and_allows_empty_layers`, ignored denied rebuild entry, rootless walk error, unreadable walk directory and denied env symlink controls: 5 tests OK, 0.640s. Prior frozen graph suite: 549 tests OK, 71.863s; final integrated qualification remains coordinator-owned. |
| 2026-10-09 | Updated owned chunking, search and graph architecture contracts. Source frozen for coordinator integration; delivery review and fresh canonical framework qualification remain open. | Owned-path `git diff --check` passed. No commit, close, push or actual self-host index rebuild. Full qualification and shared performance/operator docs remain with the coordinator. |
| 2026-10-09 | Coordinator qualification exposed a fixture precision mismatch in the model-incompatibility control: hard-coded full precision also requested an implicit conversion under an int8 provider. Repaired only the test to retain actual recorded precision while changing model/fingerprint identity; production precision-conversion refusal remains intact. Source frozen again after this scoped repair. | Named `test_unknown_or_changed_policy_does_not_take_removal_transition`: 1 test OK, 5.484s; all `OperationalEvidencePolicyTests`: 9 tests OK. Captures `/private/tmp/wf-20aqf-precision-control.log` and `/private/tmp/wf-20aqf-precision-scope.log`; no broad suite or root documentation edited by this worker. |

| 2026-10-09 | Historical readiness handoff below is retained byte-identical to its approved plan. Current implementation status is superseded by this Progress Log and active wave/session handoff; a worker status rewrite there moved the policy digest and was restored without changing scope. | Stage authority and admitted requirements preserved; no new readiness obligations or source edit. |

| 2026-10-10 | Implementation complete; all tasks and ACs met. Required independent delivery lanes approved and current canonical qualification passed. | wave.md retains consolidated proof and limits; events.jsonl holds typed authority. Fresh source receipt bfdf8d1ecb910925f9633f3ff215385ca38110310d77faf1bc9f74114695f7af; 12,108 tests/181 files/13 skips; no closure or commit authorized. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-09 | Adopt the scoped approach above for readiness review. | Concrete ten-wave waste and current source owners support a bounded repair; retain quality and authority boundaries. | Selected narrow record-owned evidence filtering with selective removal publication. Rejected excluding all waves because decisions and plans remain valuable. Rejected .aiignore-only rules because they can block direct agent reads, and a bare walker-version bump because it forces unrelated rebuilding. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Saving work conceals missing proof or stale authority. | Required negative controls, exact input identities, retained unique evidence and unchanged full gates. |
| Cross-change source ownership causes conflicting edits. | Shared-file serialization; canonical seeds first; focused independent integration review. |
| Upgrade performs unrelated maintenance. | Consumer upgrade trace and explicit no-source-suite/no-extra-evidence boundary in every applicable contract. |

## Session Handoff

Planned for readiness review only. See `docs/agents/session-handoff.md`; no code edited under this wave, no AC marked complete and no OPEN slot taken.
