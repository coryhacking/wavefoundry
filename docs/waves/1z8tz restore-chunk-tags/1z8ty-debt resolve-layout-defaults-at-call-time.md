# Restore Chunk Tags and Resolve Layout Defaults at Call Time

Change ID: `1z8ty-debt resolve-layout-defaults-at-call-time`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-28
Wave: 1z8tz restore-chunk-tags

## Rationale

**Chunk tags have been empty since 2026-05-17.** `docs_search` and `code_search` accept a `tags` filter (`wave`, `agent`, `lifecycle`, `reference`, `journal`, `prompt`, `seed`, `framework`, `test`, `config`), and their tool descriptions advertise it. Commit `28ca7657` moved tag filtering from an in-memory index, built at load time by calling `_infer_tags` on each chunk path, to a `tags LIKE` clause on the stored `tags` column. Nothing writes that column: the indexer stores `chunk.get("tags") or []`, and the chunker never sets it. In this repository's index, 0 of 32,817 doc chunks and 0 of 14,839 code chunks carry a tag, and `docs_search(query="wave record objective", tags=["wave"])` returns no results. As a result, tag inference is not called anywhere in production: `chunker.py` imports `infer_tags` only as a test alias, and `server_impl._infer_tags` is called only by tests.

**Layout defaults are captured at import.** Three modules compute a default from the record-layout constants when imported and bake it into a default argument: `_tag_utils._DEFAULT_WAVES_PREFIX`, `retrieval_eval._DEFAULT_WAVES_PREFIX` and `reconcile_scan.EXCLUDED_DIRS`. The census behind that list was a module-level search of non-test scripts for assignments from the `record_paths` layout constants. Whichever test imports such a module first decides its default for the rest of the interpreter, under whatever layout that test had patched. Wave `1z8tx` fixed the tests that failed because of this, but left the capture in place.

**Dead defaults and dead code nearby.**
- `reconcile_scan.is_excluded`'s only caller passes `excluded_dirs` explicitly.
- `retrieval_eval.classify_carrier` and `carrier_rows` have no caller outside `tests/test_retrieval_eval.py` anywhere in the repository.

## Requirements

1. **Tags are written at index time.** Tags are set on every chunk-production path through `indexer._chunks_for_file`, which gains keyword arguments `waves_prefix` and `archive_prefix`. Its three callers pass prefixes resolved once per build or search:
   - `_run_streaming_full_rebuild` and the incremental loop in `build_index` pass `record_paths.load_record_roots(root)`, falling back to `unvalidated_record_roots` as `server_impl._record_prefixes` does;
   - `WaveIndex._live_docs_chunks` passes `_record_prefixes(self.root)`.

   A relocated or nested layout tags its own waves root. When an archive root is configured, paths under it also get the `wave` tag through `infer_tags(..., archive_prefix=...)`.
2. **Existing indexes pick the tags up without re-embedding.**
   - `indexer._chunk_hash` keeps its payload shape byte-identical, with a constant `"tags": []`. Tags are metadata, not embedded text, and stored hashes stay valid, so embedding reuse still matches.
   - On the rechunk paths (`rechunk_all` or `rechunk_requested`), stale paths are exempt from the registry fast path (`_skip_exempt`). The delta planner then reaches `_row_metadata_matches_current`, which already compares `tags`, and rewrites each row with its existing vector.
   - `chunker.CHUNKER_VERSION` goes from 42 to 43. That triggers the rechunk-with-reuse upgrade path; `WALKER_VERSION` is not bumped, because that forces a full rebuild.
3. **The `tags` filter works end to end.** The dense and FTS paths of `docs_search` and `code_search`, and the lexical/live fallback (`search_docs_lexical` over `_live_docs_chunks`), return only chunks carrying the tag. The advertised vocabulary matches what `infer_tags` emits, adding the missing `memory` tag in:
   - the `docs_search` and `code_search` descriptions;
   - seed `211-guru.prompt.md`, edited under `seed_edit_allowed`;
   - `docs/agents/guru.md`.
4. **`_tag_utils.infer_tags` reads its default at call time.** It takes `waves_prefix: str | None = None` and `archive_prefix: str | None = None`. With no `waves_prefix`, it reads the current `record_paths` via a function-level import (`unvalidated_record_roots(Path(".")).waves_prefix`, matching `_record_prefixes`' normalization). It does not use a module reference bound at import: importing `server_impl` evicts `record_paths` from `sys.modules`, so such a reference can be a copy `patch_layout` never reaches. `_DEFAULT_WAVES_PREFIX` is removed.
5. **`reconcile_scan.is_excluded` requires `excluded_dirs`.** It becomes a required keyword argument, and `EXCLUDED_DIRS` is removed; the only caller, `_iter_scannable_files`, already passes `excluded_dirs_for(root)`.
6. **The `retrieval_eval` carrier apparatus is kept.** That is `classify_carrier`, `carrier_rows`, `carrier_contamination_violations` and their constants, delivered by `1wscp` Requirement 4. Only its default becomes call-time: `waves_prefix: str | None = None`, resolved as in Requirement 4, with `_DEFAULT_WAVES_PREFIX` removed. It has no production caller, but removing it would retract a delivered requirement, which is out of scope here.
7. **Tag tests use `_tag_utils` directly.** `chunker.py`'s unused `infer_tags` import is removed, and `tests/test_chunker.py` (the `_infer_tags` cases), `tests/test_record_layout_nested.py` and `tests/test_record_layout_cold_sites.py` call `_tag_utils.infer_tags` instead.
8. **The cold-site tests follow the current layout.** The tests that read `_DEFAULT_WAVES_PREFIX` assert against the current layout, and the same-module comparison added in `1z8tx` reverts to the public `_tag_utils`. The pins in `tests/test_record_layout_census.py` that name `_tag_utils` and `reconcile_scan EXCLUDED_DIRS` are updated.
9. **Tags follow the layout constants, not file content.** Changing `WAVES_ROOT` or `ARCHIVE_ROOT` without moving files does not re-tag existing chunks. The CHANGELOG and the tool text name `index_build(mode='rechunk')` as the remedy, which works once Requirement 2 is in.

## Scope

**Problem statement:** the advertised tag filter matches nothing, and layout defaults captured at import make test results depend on import order.

**In scope:**

- Tag writing on all three chunk-production paths; the hash shape; the rechunk registry exemption; the version bump; the tool descriptions, guru seed and guru doc.
- `_tag_utils.py`, `reconcile_scan.py`, `retrieval_eval.py` defaults; `chunker.py` alias; `server_impl._infer_tags` (kept as the server's root-aware wrapper; its callers are tests).
- Tests: tags present after a build and after a rechunk upgrade, the filter end to end (dense, FTS, lexical fallback), relocated and archive tagging, the call-time default, cold-site and census updates.

**Out of scope:**

- New tags or vocabulary changes beyond documenting `memory`.
- Query-time tag computation (see Decision Log).
- Removing the `retrieval_eval` carrier apparatus.

## Acceptance Criteria

- [x] AC-1: after an index build on a fixture repository, chunks carry the tags `infer_tags` gives their paths. The `tags` filter on `docs_search` and `code_search` returns only matching chunks on the dense, FTS and lexical-fallback paths, and a query that returned nothing before now returns results.
- [x] AC-2: under a relocated waves root, wave records under that root are tagged `wave` and files under `docs/waves/` are not. With an archive configured, archived records are tagged `wave`.
- [x] AC-3: on an index built before this change, the `CHUNKER_VERSION` upgrade path calls the encoder zero times, and afterwards `chunks_docs.tags` and `chunks_code.tags` are non-empty for tagged paths.
- [x] AC-4: with no argument, `infer_tags` and the `retrieval_eval` helpers follow the layout current at call time, and a module first imported under a patched layout returns the shipped default once the patch is gone.
- [~] AC-5: `is_excluded` without `excluded_dirs` is a `TypeError`. A non-test census finds no module-level assignment from a `record_paths` layout constant. *is_excluded without excluded_dirs is a TypeError (met). The census clause is narrowed by one documented exception: review_policy.SCAFFOLD_DOCS is still built from record_paths.PLANS_ROOT at import because the upgrade reads it across versions (upgrade_extensions) and test_upgrade_wavefoundry pins it; the census test enforces the rule with that single listed exception.*
- [x] AC-6: `test_record_layout_nested` then `test_record_layout_cold_sites`, and `test_archive_root` then `test_record_layout_cold_sites`, pass in one interpreter, as does each alone.
- [x] AC-7: the change's own suites pass, and the documents it edits validate. The CHANGELOG `[Unreleased]` notes the tag fix, the one-time rechunk (no re-embed) and the rechunk remedy after a layout change.

## Tasks

- [x] Tags: the `_chunks_for_file` prefixes and its three callers; the constant hash shape; the rechunk `_skip_exempt`; `CHUNKER_VERSION` 43; the `archive_prefix` in `infer_tags`.
- [x] Vocabulary: the `docs_search`/`code_search` descriptions, seed 211 (gate) and `docs/agents/guru.md`.
- [x] Call-time defaults (`_tag_utils`, `retrieval_eval`); `is_excluded` required; remove the chunker alias.
- [x] Tests: build tags, the rechunk upgrade with a zero encoder count, the filter on three paths, relocated and archive tagging, the call-time default; update the cold-site, chunker, nested and census tests; pairwise single-process ordering sweep.
- [x] CHANGELOG `[Unreleased]`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Tags | implementer | readiness | Indexer, server live path, hash, version |
| Defaults and cleanup | implementer | readiness | `_tag_utils`, `reconcile_scan`, `retrieval_eval`, chunker alias |
| Tests | implementer | both | Includes the ordering sweep |
| Review | combined reviewer | Tests | Code, QA, docs contract |

## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/chunker.py`, `.wavefoundry/framework/scripts/_tag_utils.py`, `.wavefoundry/framework/scripts/reconcile_scan.py`, `.wavefoundry/framework/scripts/retrieval_eval.py`
- `.wavefoundry/framework/scripts/wf_server/`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/211-guru.prompt.md`
- `docs/agents/guru.md`
- `CHANGELOG.md`

## Affected Architecture Docs

`N/A`: `docs/architecture/data-and-control-flow.md` does not describe tag inference (confirmed in readiness).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The broken feature |
| AC-2 | required | Tags must follow the configured layout |
| AC-3 | required | Upgrading must not re-embed, and must actually write tags |
| AC-4 | required | Removes the import-order hazard |
| AC-5 | important | Cleanup that keeps the pattern from returning |
| AC-6 | required | The orderings that motivated the follow-up |
| AC-7 | required | Verification and release notes |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Implemented (implementer agent, coordinator doc edits). `_tag_utils.infer_tags(path, *, waves_prefix=None, archive_prefix=None)` with a call-time `default_waves_prefix()`; `indexer._tag_prefixes` resolves once per build and `_chunks_for_file` tags every chunk on the full, incremental and server live paths; `_chunk_hash` hashes a constant `tags: []`; `_skip_exempt` covers stale paths on rechunk; `CHUNKER_VERSION` 43 (the `performance-budget.md` pin updated with it); `is_excluded` requires `excluded_dirs`; `retrieval_eval` defaults at call time; chunker alias removed; tool descriptions list `memory` and name the rechunk remedy; seed 211 and `guru.md` gain `memory` (`guru.md` also had drifted: its `journal` row pointed at the memory directory and its example used `journal` for memory records, both corrected). New `tests/test_chunk_tags.py` (15 tests). `test_fts_lexical_layer.test_metadata_only_difference_changes_the_map` pinned the old tags-in-hash contract and now tests a `section`-only change, with a new test pinning the tags-only contract. Mutants (hash with real tags, no rechunk exemption, no live-path tags, import-time default) each fail. Census exception: `review_policy.SCAFFOLD_DOCS` is still built from `record_paths.PLANS_ROOT` at import because the upgrade reads it across versions (`upgrade_extensions`) and `test_upgrade_wavefoundry` pins it; the census test lists it as the one known exception. Found in passing: `_live_docs_chunks` reads only `docs/` and `.wavefoundry/framework/`, so a waves root relocated outside `docs/` never reaches the live fallback (pre-existing, unchanged). Gapfill: none for retrieval (MCP code tools used); edits by Edit tool | `test_chunk_tags` 15 OK; focused suites; single-process ordering sweep |
| 2026-09-28 | Readiness confirmation round: B1 resolved; R3 wording fixed. Considered and not adopted: fingerprinting the layout constants into the build meta to trigger a rechunk automatically (the documented remedy suffices for a rare configuration change), and generating the vocabulary table from one list (a larger docs-generation change) | readiness confirmation |
| 2026-09-28 | Readiness review. B1 (blocking) adopted: excluding tags from the hash would let the registry fast path skip every file on a rechunk, writing no tags while AC-3 passed; the hash keeps a constant `tags` field, rechunk paths are exempt from the registry skip, and AC-3 asserts both zero encoder calls and stored tags. N1: the third chunk-production caller (`_live_docs_chunks`) added. N2: layout-change remedy documented. N3: `archive_prefix` named. N4: `memory` added to the advertised vocabulary. N5: the `retrieval_eval` apparatus is kept with a call-time default instead of removed. N6: test and census pins named | readiness review |
| 2026-09-28 | Rescoped at the operator's direction ("Restore"). While tracing `_tag_utils` callers, found that no production path calls tag inference and the stored `tags` column is empty; traced the regression to `28ca7657`. Also found the unused `is_excluded` default and the test-only `retrieval_eval` helpers | index census (0 tagged chunks); `docs_search(tags=["wave"])` empty; `git log -S"infer_tags("` |
| 2026-09-28 | Planned as the follow-up to `1z8tx`, whose reviewers named the import-time capture in two `_tag_utils` copies as the remaining hazard | module-level assignment census |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | Keep stored tags and fix the rechunk path, rather than compute tags at query time | The vector store's filter parser (`sqlite_vector_store._predicate`) deliberately allows only column comparisons with `LIKE`/`IN` and rejects arbitrary SQL, and several `infer_tags` rules are regexes (`test`, `config`) that path `LIKE` clauses cannot express; query-time tags would need a new SQL function in a grammar built to refuse them | Register a sqlite function over `infer_tags(path)` (readiness red-team alternative); translate tags into path predicates (duplicates the rules) |
| 2026-09-28 | Constant `"tags": []` in `_chunk_hash` plus a registry-skip exemption on rechunk | Keeps stored hashes and embedding reuse valid while forcing the metadata rewrite; dropping the key would change every hash and re-embed everything | Drop tags from the hash (re-embed all); keep tags in the hash (re-embed every tagged chunk) |
| 2026-09-28 | Restore tags rather than remove the filter | The filter is advertised on two tools and the vocabulary exists; the regression was an omission when filtering moved to the stored column | Remove the `tags` parameter and `_tag_utils` (tool-surface change) |
| 2026-09-28 | Read the default at call time through the current `record_paths` | Removes the import-order hazard where it originates; production behaviour is unchanged | Have `patch_layout` evict cached copies; fix each leaking test |
| 2026-09-28 | Make `is_excluded`'s argument required; keep the `retrieval_eval` apparatus with a call-time default | `is_excluded` has one caller that passes it; removing the carrier apparatus would retract `1wscp` Requirement 4 | Remove the carrier apparatus |

## Risks

| Risk | Mitigation |
| --- | --- |
| The upgrade re-embeds, or writes no tags | AC-3 asserts both a zero encoder count and stored tags |
| Consumers see a one-time rechunk after upgrading | CHANGELOG operator note; embeddings are reused |
| Stored tags go stale after a layout constant changes without moving files | Documented `index_build(mode='rechunk')` remedy |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
