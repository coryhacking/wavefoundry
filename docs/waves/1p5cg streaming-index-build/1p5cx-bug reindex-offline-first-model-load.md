# Load reindex embedders offline-first, falling back to online

Change ID: `1p5cx-bug reindex-offline-first-model-load`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-13
Wave: `1p5cg streaming-index-build`

## Rationale

Every `build_index` run reconstructs the docs + code embedders from scratch, and the build
path does not run against the local HF cache only. So each model init makes an HF Hub
metadata round-trip (revision/etag check) — not a re-download, the model is cached — which
emits `Warning: You are sending unauthenticated requests to the HF Hub` once per embedder per
build. Because the post-edit hook spawns a fresh reindex subprocess on every file save, a
short editing session produces a stream of these warnings and pays needless network latency on
every cold start.

`setup_index.py` already provisions and warms the models offline (`local_files_only=True`), so
the reindex path can assume the cache is present and load from it with no network. Only when a
model genuinely isn't cached (setup was skipped) should it reach the Hub — downloading and
caching once, then loading from cache thereafter.

**Where the warning actually originates (warm cache):** not `build_index` — on a no-change
incremental build it embeds nothing. The launcher prewarms models on every spawn via
`setup_index._prewarm_gpu_accel`, which calls `accel_embedder.make_reranker` / `make_embedder`.
Those resolve a clean ONNX export through `_resolve_clean_onnx` / `_resolve_reranker_cpu_files`,
which call `hf_hub_download` **unconditionally** — a Hub revision/etag round-trip even when the
file is cached. `huggingface_hub` emits the unauthenticated-request warning once per process on
the first online request, so this single un-gated path is enough to produce the warning every
build. (The setup provider-probe already uses `local_files_only=True`, so it is not a source.)

**Mechanism:** use the first-class `local_files_only=True` parameter of `hf_hub_download` and
fastembed's `TextEmbedding` — try cached-first, fall back to a normal (downloading) call only on
a cache miss. This is preferred over toggling global offline state: in `huggingface_hub` 1.16.x
`constants.is_offline_mode()` returns the module-level `HF_HUB_OFFLINE` captured at import, so an
env toggle is a silent no-op and mutating the constant directly is fragile (import-order
sensitive — an early prototype that did so stranded a cold-cache process permanently offline).
`local_files_only` is explicit, import-order-immune, and precisely distinguishes cached from
must-download.

## Requirements

1. `accel_embedder` resolves clean-ONNX / reranker files **cached-first** (`local_files_only=True`),
   downloading only on a genuine cache miss — covering the reranker + GPU embedder prewarm (the
   warning source) and the build/server GPU paths in one place.
2. `indexer._get_embedder`'s fastembed CPU fallback loads **cached-first**, with an online
   fallback on a cache miss.
3. When models are cached (the normal case), a reindex makes no HF Hub request and emits no
   unauthenticated-request warning.
4. Vectors are unchanged — cached vs downloaded load the same weights, so the produced index is
   identical (no parity impact).

## Scope

**Problem statement:** the reindex path pings the HF Hub (unauthenticated-request warning +
latency) on every model init even though the models are already cached.

**In scope:**

- `accel_embedder._hf_download_cached_first` helper, used by `_resolve_clean_onnx`,
  `_resolve_reranker_cpu_files`, and `_ensure_fastembed_model_cached` (the GPU embedder +
  reranker download chokepoints).
- `indexer._text_embedding_cached_first` helper, used by `_get_embedder`'s fastembed CPU path.

**Out of scope:**

- The model set, provider selection, chunker, or any retrieval behavior.
- The eager both-embedders load when only one layer changed (separate efficiency follow-up).
- The setup provider-probe (already `local_files_only=True`).

## Acceptance Criteria

- [x] AC-1: `accel_embedder._hf_download_cached_first` returns the cached file with
  `local_files_only=True` and falls back to a downloading call only on a cache miss; asserted by
  test (cached → one call; miss → two calls).
- [x] AC-2: `indexer._text_embedding_cached_first` (and `_get_embedder`'s fastembed path) loads
  `local_files_only=True` first and falls back to an online construct on a miss; asserted by test.
- [x] AC-3: a real incremental reindex on a warm cache emits no `unauthenticated requests to the
  HF Hub` warning (verified live in the build log).

## Tasks

- [x] Add `_hf_download_cached_first` to `accel_embedder.py`; route `_resolve_clean_onnx`,
  `_resolve_reranker_cpu_files`, and `_ensure_fastembed_model_cached` through it.
- [x] Add `_text_embedding_cached_first` to `indexer.py`; use it on `_get_embedder`'s fastembed path.
- [x] Tests: cached-first/online-fallback for both helpers + the fastembed `_get_embedder` path.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- Shares `indexer.py` with `1p5ch`; both land in the same wave, no concurrent-edit conflict.

## Affected Architecture Docs

`N/A` — confined to the indexer's embedder-construction helper; no boundary, data-flow, or
verification-architecture change (offline and online load the same cached weights).

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The accel download chokepoint is the actual warning source; cached-first with download-fallback must not strand a cold cache. |
| AC-2 | required  | The fastembed CPU path must also load cached-first so non-GPU machines get the same fix. |
| AC-3 | required  | The user-visible symptom is the warning; a live warm-cache reindex with zero warnings is the real acceptance. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-13 | Implemented cached-first model loads: `accel_embedder._hf_download_cached_first` (used by `_resolve_clean_onnx`, `_resolve_reranker_cpu_files`, `_ensure_fastembed_model_cached`) and `indexer._text_embedding_cached_first` (used by `_get_embedder`'s fastembed path). | `accel_embedder.py`, `indexer.py` |
| 2026-06-13 | Diagnosed the true source: the warning is from the launcher prewarm (`_prewarm_gpu_accel` → accel `hf_hub_download`), not `build_index` (a no-change incremental embeds nothing). An early `_hf_offline()` constant-toggle prototype stranded a cold-cache process offline (import-order bug, caught by test) → abandoned for `local_files_only`. | build log analysis |
| 2026-06-13 | Live verified: incremental reindex on warm cache prewarms reranker + both GPU embedders with **zero** `unauthenticated requests to the HF Hub` warnings. Full suite **3104 OK**; docs-lint clean. | `project-index-build.log` (pid 11497) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-13 | Cached-first via `local_files_only=True`, online fallback on miss | First-class HF param; explicit, import-order-immune, precisely distinguishes cached vs must-download; a cold cache still self-heals by downloading once | Toggle global offline state (env-only is a silent no-op post-import; mutating `constants.HF_HUB_OFFLINE` is import-order-fragile and stranded a cold cache in a prototype); set `HF_TOKEN` (still pings every load — wrong fix) |
| 2026-06-13 | Fix at the `accel_embedder` download chokepoint, not only `indexer` | The warm-cache warning comes from prewarm's unconditional `hf_hub_download`, which `build_index` never reaches on a no-change build; one chokepoint covers prewarm + build + server | Fix only `_get_embedder` (leaves the prewarm warning, the actual symptom, in place) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Forcing offline strands a machine that never ran setup | Online fallback downloads + caches once on the offline attempt's failure |
| Future `huggingface_hub` changes the constant's name/location | `_hf_offline()` guards the import/attr access; env var remains set as a second signal |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
