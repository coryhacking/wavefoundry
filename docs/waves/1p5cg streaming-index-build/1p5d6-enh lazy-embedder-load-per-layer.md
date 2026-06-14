# Load a layer's embedder only when that layer has chunks to embed

Change ID: `1p5d6-enh lazy-embedder-load-per-layer`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-13
Wave: `1p5cg streaming-index-build`

## Rationale

`build_index` loads both the docs (arctic) and code (bge) embedders whenever the corresponding
`--content` flag is set, regardless of whether that layer actually has changes. On an incremental
update this is wasteful: a docs-only edit still constructs the bge code embedder (its CoreML
static-shape session + ~compile), which is then never used (`table=code unchanged=0`). The hook
reindex spawns `indexer.py` directly (no `setup_index` prewarm), so this load happens on every
save — paying a model init for a layer with no work.

`_lance_incremental_write` only touches an embedder when the layer has chunks to embed (it reuses
vectors by content hash and embeds only the delta), so a layer with no new/changed chunks can
safely receive `None`. Gating the embedder load on "this layer has work" removes the wasted init.

## Requirements

1. On an incremental update, load the docs embedder only when there are new/changed doc chunks,
   and the code embedder only when there are new/changed code chunks.
2. A full rebuild still loads both embedders (both layers always have all chunks).
3. No behavior change: a layer that receives `None` (no chunks) performs its existing no-op /
   delete-only incremental write correctly.

## Scope

**Problem statement:** an incremental reindex loads the unused layer's embedder (CoreML
session/compile) even when only the other layer changed.

**In scope:**

- The two `_get_embedder(...)` call sites in `build_index`: gate each on `full or <layer has new chunks>`.

**Out of scope:**

- The `setup_index` launcher prewarm (runs before change detection, so it can't know which layer
  changed — a separate concern; the direct-spawn hook path is the one this fixes).
- Embedding/model/provider behavior, the streaming full-rebuild path, retrieval.

## Acceptance Criteria

- [x] AC-1: an incremental update with only doc changes does not construct the code embedder
  (and vice versa); asserted by a test that patches `_get_embedder` and checks which models load.
- [x] AC-2: a full rebuild still loads both embedders, and incremental writes for a layer with no
  new chunks remain correct (existing incremental/full tests green).

## Tasks

- [x] Gate the docs/code `_get_embedder` calls in `build_index` on `full or new_<layer>_chunks`.
- [x] Test: docs-only incremental update loads only the docs model; full rebuild loads both.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- Shares `indexer.py` `build_index` with `1p5ch`/`1p5cx`; same wave, no concurrent-edit conflict.

## Affected Architecture Docs

`N/A` — a load-gating micro-optimization in `build_index`; no boundary/flow/verification change.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Not loading the unused model is the whole point of the change. |
| AC-2 | required  | Must not regress the full rebuild or a delete-only incremental write. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-13 | Gated the two `_get_embedder` calls in `build_index` on `full or new_<layer>_chunks`. Added 3 tests (docs-only skips code embedder; code-only skips docs embedder; full loads both). Updated one existing test (`test_incremental_line_window_shift_reembeds_affected_chunks`) whose ordered-list embedder mock assumed both layers load — `notes.custom` is pure code, so it now maps embedder by model name. | `indexer.py`, `test_indexer.py` |
| 2026-06-13 | Full suite **3107 OK**. Live: a docs-only incremental (`indexer.py --content all`) loaded only `Snowflake/snowflake-arctic-embed-xs`; no bge code-model line; code layer was a clean no-op. | `project-index-build.log` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-13 | Gate the eager `_get_embedder` calls on per-layer work | Minimal, safe — the incremental writer already no-ops without an embedder when a layer has no chunks | A lazy-proxy embedder (defers load to first `embed()`) — more general but heavier; unnecessary since the per-layer chunk counts are already known at the load site |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A layer with removals-but-no-new-chunks needs the embedder | It doesn't — deletes don't embed; `_lance_incremental_write` only embeds when chunks are present (verified) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.

