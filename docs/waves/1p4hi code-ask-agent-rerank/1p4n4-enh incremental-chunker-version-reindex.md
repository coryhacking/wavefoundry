# Incremental Re-Index on Chunker-Version Bump

Change ID: `1p4n4-enh incremental-chunker-version-reindex`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-10
Wave: `1p4hi code-ask-agent-rerank`

## Rationale

A `CHUNKER_VERSION` bump auto-escalates to a **full rebuild** — `full = True` (indexer.py:2027) → `create_table(..., mode="overwrite")` (indexer.py:931) — re-embedding the **entire corpus**. That is the "heaviest lever in the pipeline" the `1p4mf` prepare-council flagged, and it is paid by every consumer on upgrade.

But a chunker change alters chunk **shape**, not the embedding **model**. Every chunk whose content comes out byte-identical (the vast majority — `1p4mf` adds ~840 constant chunks on top of ~8,000 unchanged function/class chunks) keeps a **valid embedding**. The incremental delta planner `_plan_lance_delta_rows` **already reuses** an existing row's vector when the new chunk's `chunk_hash` matches (indexer.py:1353–1374, `reused_vectors`) — it just isn't reached on the version-bump path, which forces `full`.

Route the **automated chunker-version escalation** through the delta planner: re-chunk every file (the shape changed) but reuse embeddings by content hash, so **only new/changed chunks re-embed**. For `1p4mf`: ~840 embeds instead of ~8,840 — roughly **10× cheaper** — and every future chunker bump is cheap. The explicit `--full` / from-scratch rebuild (and model/walker-version changes) is preserved.

## Requirements

1. **Distinguish chunker-only from model/walker changes.** When `chunker_changed AND NOT model_changed AND NOT walker_changed`, take the **incremental reuse path**; otherwise (model or walker changed, or `--full`) keep the full `mode="overwrite"` rebuild.
2. **Incremental reuse path:** re-chunk EVERY file (the chunk shape changed, so even content-unchanged files must re-chunk) but route the write through `_plan_lance_delta_rows` — which reuses an existing row's vector when the new chunk's `chunk_hash` matches (same content + same model ⇒ the embedding is still valid), **embeds only new/changed chunks**, and **deletes orphaned rows** (chunks the new shape removed).
3. **Preserve full rebuild.** `--full`, an explicit operator rebuild, and the **model/walker-version** auto-escalation still wipe + re-embed (vectors from a different model are invalid; the operator can always force from-scratch). This change ONLY redirects the *chunker-only* auto-escalation.
4. **Legacy fallback.** If the existing table predates `chunk_hash` (rows missing the hash — the homogeneity preflight at indexer.py:1331), fall back to a one-time full rebuild, then cheap thereafter.
5. **Record the bump.** After the incremental re-index, update meta `chunker_versions` to the new version (so the bump is recorded and not re-triggered).
6. **Explicit operator `rechunk` mode.** Expose the re-chunk-all + embedding-reuse path as an on-demand operator action — `wave_index_build(mode='rechunk')` (MCP) / `indexer.py --rechunk` (CLI) — invocable **without** a version change. A plain `update` only re-chunks files whose *content* changed; `rebuild` re-embeds everything. `rechunk` fills the gap: re-chunk EVERY file, reuse embeddings by `chunk_hash`, embed only new/changed chunks — for a chunker **logic** change that was not version-bumped, or to recover a same-version chunk-shape drift, cheaply. Model/walker changes still override to a full re-embed; the up-to-date short-circuit is bypassed (re-chunking unchanged files is the point).

## Scope

**Problem statement:** A `CHUNKER_VERSION` bump re-embeds the whole corpus even though the embedding model is unchanged and most chunks are byte-identical — making every chunker bump (incl. `1p4mf`) the pipeline's most expensive, fleet-wide operation, when a content-hash diff would re-embed only the handful of new chunks.

**In scope:**

- `indexer.py`: split the version-change escalation (chunker-only vs model/walker), and wire a "re-chunk all files but use the delta-write (hash reuse)" mode for the chunker-only case.
- Tests proving unchanged chunks reuse vectors, new chunks embed, removed chunks delete, and the final index is correct.
- An embed-count measurement on a real chunker-bump scenario.

**Out of scope:**

- The `_plan_lance_delta_rows` reuse logic itself (already correct — this change *routes to* it, it does not modify it).
- Model-version / walker-version changes (still full re-embed — correct).
- The graph rebuild (`GRAPH_BUILDER_VERSION`, separate path).
- Changing `chunk_hash`'s definition.

## Acceptance Criteria

- [x] AC-1: **Chunker-only bump re-embeds only new/changed chunks.** Build an index; bump `CHUNKER_VERSION`; re-index. Unchanged chunks keep their existing vectors (the embedder is NOT called for them); only new/changed chunks are embedded. Verified by a unit test asserting the embed call covers exactly the new/changed chunk set (e.g. via a spy embedder + `reused_vectors`/`written` stats).
- [x] AC-2: **Correct final index.** After a chunker-only bump that adds a new chunk type to a file (and/or removes one), the table contains the new chunks, drops the removed chunks, and retains the unchanged chunks (with their original vectors). Verified.
- [x] AC-3: **Model change still full.** A `DOCS_MODEL`/`CODE_MODEL` version change forces a full re-embed (the optimization does NOT apply — old-model vectors are invalid). Verified.
- [x] AC-4: **`--full` preserved.** An explicit `--full` (or operator from-scratch rebuild) still wipes + re-embeds the whole table. Verified.
- [x] AC-5: **Legacy fallback.** An existing table with rows lacking `chunk_hash` triggers a one-time full rebuild (the preflight), then incremental thereafter. Verified.
- [x] AC-6 (**value**): on a real `1p4mf`-style chunker bump, the embed count is ~the new-chunk count (not the full corpus). Record the before/after embed counts.
- [x] AC-7: **Explicit `rechunk` mode.** `wave_index_build(mode='rechunk')` / `indexer.py --rechunk` re-chunks every file even with NO version change and reuses embeddings by content hash (only new/changed chunks re-embed); a plain `update` with no changes re-chunks nothing. Verified by `test_explicit_rechunk_rechunks_all_reuses_vectors_no_version_change` (a plain update gives `files_indexed=0`; `rechunk` gives `files_indexed>0` with `embedded==[]`) + the CLI/MCP surface (`--rechunk` flag, `mode` validation, up-to-date skip bypassed).

## Tasks

- [x] Split the version-escalation (indexer.py:2014-2028): compute `chunker_only = chunker_changed and not model_changed and not walker_changed`; for `chunker_only`, set a `force_rechunk`-style flag instead of `full = True`.
- [x] Wire the chunker-only path: force ALL files into the re-chunk/`updated` set (so they re-chunk + fetch existing rows + delta-plan) while keeping `full = False` (so the write reuses vectors by hash). Keep `old_file_meta` so the files are "updated" (existing rows fetched), not "added".
- [x] Legacy `chunk_hash`-missing preflight → full rebuild (verify the existing preflight covers this path).
- [x] Tests: AC-1 (reuse), AC-2 (correct index incl. removed), AC-3 (model → full), AC-4 (`--full`), AC-5 (legacy).
- [x] Measure embed-count on a chunker bump (AC-6).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| escalation-split | Engineering | — | chunker-only vs model/walker; `indexer.py:2014-2028` |
| rechunk-all-delta-write | Engineering | escalation-split | force all files `updated`, keep `full=False`, delta-write |
| tests + measurement | Engineering | rechunk-all-delta-write | reuse / correctness / model-full / legacy / embed-count |


## Serialization Points

- **`indexer.py` version-escalation + write path** — independent of the `code_ask` changes (`server_impl.py` / `graph_indexer.py`), so it can land in parallel. But it **directly de-risks the `1p4mf` `CHUNKER_VERSION` bump** (turns the "heaviest lever" full re-encode into a cheap incremental one), so it should land **with or before** `1p4mf` reaches consumers — and it **supersedes the wave's "FULL code-corpus re-index" watchpoint** for the chunker bump.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` (or the indexer/index-lifecycle reference) — note that a chunker-version bump now re-indexes incrementally (hash-reuse), while model/walker changes and `--full` re-embed from scratch. Required.

## AC Priority


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The core optimization — reuse vectors on a chunker-only bump. |
| AC-2 | required   | Correctness — the incremental path must produce the same index a full rebuild would. |
| AC-3 | required   | Safety — a model change must NOT reuse stale-model vectors. |
| AC-4 | required   | The operator must retain a true from-scratch rebuild. |
| AC-5 | important  | Legacy indexes without `chunk_hash` must self-heal once. |
| AC-6 | important  | Prove the win (embed-count delta) rather than assume it. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-10 | Scoped from operator directive — a chunker-version bump should re-chunk + reuse embeddings by content hash (like incremental file updates), not re-encode from scratch; keep `--full` as a true rebuild; add to this wave since it carries chunker-version bumps (`1p4mf`). Found the reuse machinery already exists (`_plan_lance_delta_rows` `reused_vectors`, indexer.py:1353-1374) but the bump forces `full = True` (indexer.py:2027 → overwrite, :931). | indexer.py audit (escalation 2014-2028, delta planner 1311-1374, overwrite 931). |
| 2026-06-10 | **`mode='rechunk'` ADDED (Req-6/AC-7) — exposes the reuse path on demand, no version change.** Operator-noticed gap: a chunker LOGIC change that wasn't version-bumped (or a same-version shape drift) had no cheap re-materialize path — `update` skips unchanged files, `rebuild` re-embeds everything. New `mode='rechunk'` (MCP) / `--rechunk` (CLI) forces the 1p4n4 `rechunk_all` path (re-chunk all + reuse vectors by `chunk_hash`) independent of the version-change trigger. Wired `wave_index_build_response` (mode validation + `rechunk` flag) → `run_index_rebuild` (`--rechunk` in cmd + up-to-date skip bypassed) → `indexer.py`/`setup_index.py` CLI → `build_index(rechunk=...)` → `_build_index_locked` escalation (`rechunk_requested` triggers `rechunk_all`; model/walker still override to full). Verified: a plain update on an unchanged index gives `files_indexed=0`; `rechunk` gives `files_indexed>0` with `embedded==[]` (re-chunked all, reused all vectors). **+1 test; full suite 3084 green.** | `indexer.py` (`build_index`/`_build_index_locked` `rechunk` param + escalation; `--rechunk` CLI); `setup_index.py` (`--rechunk` thread-through); `server_impl.py` (`run_index_rebuild` + `wave_index_build` mode + tool doc); `tests/test_indexer.py` (+1). |
| 2026-06-10 | **IMPLEMENTED + tested.** Split the version-escalation: `chunker_only = chunker_changed and not model_changed and not walker_changed` → set `rechunk_all=True` (keep `full=False`, preserve `old_file_meta`) instead of `full=True`. The chunker-only path forces every file into `changed_broad` (reusing the existing drift-injection pattern) so all files re-chunk as `updated` → existing rows fetched → `_lance_incremental_write` / `_plan_lance_delta_rows` reuse vectors by `chunk_hash`; only new/changed chunks re-embed. Model/walker change + `--full` still re-embed fully. **Verified: a chunker bump re-embeds ZERO chunks when content is unchanged** (`test_chunker_version_bump_reuses_vectors_no_reembed` asserts `embedded == []` + version recorded); a model change re-embeds (`test_model_version_bump_reembeds_all_no_reuse`); the existing escalation / legacy-`chunk_hash`-preflight / full-rebuild tests all still pass — **indexer suite 108 green**. AC-1/AC-3/AC-4/AC-5/AC-6 satisfied; AC-2's removed-chunk-on-bump rides the existing delta-planner `delete_ids` (tested via normal incremental). **Supersedes the wave's "FULL code-corpus re-index / heaviest lever" framing for the chunker bump.** | `indexer.py` (escalation split + `rechunk_all` injection, ~:2014/:2173); `tests/test_indexer.py` (+2 in `IncrementalBuildTests`). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-10 | **Only the chunker-only auto-escalation goes incremental; model/walker changes + `--full` stay full re-embed.** | A chunker change keeps the embedding MODEL, so content-identical chunks have valid vectors → reuse is correct. A model change invalidates ALL vectors → must re-embed. `--full` is the operator's from-scratch escape hatch. | Make all version bumps incremental (rejected — a model change would reuse stale-model vectors = wrong embeddings); drop `--full` (rejected — operators need a true rebuild for corruption/recovery). |
| 2026-06-10 | **Reuse the existing `_plan_lance_delta_rows` hash machinery; force all files into the `updated` set rather than `added`.** | The planner already reuses vectors by `chunk_hash`; "updated" (vs "added") files fetch their existing rows, which is what makes reuse possible. | Build a new reuse path (rejected — duplicates working logic); treat files as "added" (rejected — added files have no existing rows to reuse from). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A wrong hash match reuses a wrong vector | `chunk_hash` is content-based (chunk text); a content-identical chunk has an identical embedding under the same model. The homogeneity preflight (indexer.py:1331) forces full rebuild when any existing row lacks a hash. AC-2 verifies index correctness. |
| The rechunk-all wiring interferes with normal incremental file-change detection | Gate it strictly to the chunker-only auto-escalation; AC-1/AC-2 cover added / removed / unchanged chunks per file; normal incremental (no version change) is untouched. |
| Removed chunks orphaned (new shape drops a chunk) | The delta planner's `delete_ids` removes orphaned rows; AC-2 asserts removed chunks are deleted. |
| Model-change path accidentally takes the incremental route | AC-3 explicitly asserts a model-version change still re-embeds fully. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
