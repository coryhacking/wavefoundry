# Server Startup: Background Model Download

Change ID: `12mhv-enh server-startup-model-download`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12mc3 agent-detail-panel-blank-section-mismatch`

## Rationale

`setup_index.py` is the designated path for prewarming all model caches, but it is not guaranteed to have been run — users can start the MCP server directly from source, use a distribution that lags a setup run, or have their cache cleared. When embedding models are absent at query time, `_get_embedder()` raises `SemanticModelUnavailableOfflineError` and search fails entirely. When the reranker is absent, `_get_reranker()` falls back silently to RRF. In both cases the models stay uncached for the lifetime of the server session even when a network connection is available. The server should detect missing models at startup and begin a background download immediately so that subsequent requests recover without requiring a manual `setup_index.py` run — all without loading any model into memory at startup.

## Requirements

1. `_get_reranker()` on `WaveIndex` must **not** cache failure — `self._reranker` must remain `None` when the offline load fails, so that subsequent calls retry and pick up a completed background download without requiring a server restart. (`_get_embedder()` already re-instantiates on every call and raises on failure without caching; no change required there.)
2. `WaveIndex` must expose a `_start_background_model_downloads()` method that spawns a single daemon background thread. The thread's sole responsibility is populating the on-disk model cache — it must **not** set `self._reranker`, `self._docs_embedder`, or `self._code_embedder`. For each model (`DOCS_MODEL`, `CODE_MODEL`, `RERANKER_MODEL`, deduplicated), the thread: (a) checks whether the model files are already cached using a file-existence check that does not instantiate an ONNX or cross-encoder session (e.g. `huggingface_hub.try_to_load_from_cache()` or equivalent fastembed cache-path API); (b) if already cached, skips that model; (c) if not cached, downloads the model files to disk without creating an inference session; (d) logs `"[wavefoundry] Model cached: {model_name}"` on each success, `"[wavefoundry] Background download failed for {model_name}: {e}"` on failure. The thread never raises; a failure on one model does not abort downloads for remaining models.
3. `build_server()` must call `index._start_background_model_downloads()` unconditionally after constructing `WaveIndex`. `build_server()` does not probe model availability and does not call `_get_embedder()`, `_get_reranker()`, or any method that instantiates a model. No model is loaded into the process's working memory at startup.
4. The background thread must be a daemon thread (`thread.daemon = True`) so it does not prevent server exit.
5. The background thread must not block server startup or any request handler — `build_server()` returns and the MCP server begins accepting requests before any download completes.
6. If `_start_background_model_downloads()` is called again while the thread is already running, a second thread must not be spawned. Guard with an instance-level boolean flag set before the thread starts.
7. If the `HF_HUB_OFFLINE` environment variable is set to `"1"` when `_start_background_model_downloads()` is called, no thread must be spawned — downloads are explicitly suppressed by the operator. Log `"[wavefoundry] HF_HUB_OFFLINE set; skipping background model download"` and return.

## Scope

**Problem statement:** Embedding and reranker models may not be cached when the server starts. Missing embedders cause hard search failures; a missing reranker causes silent quality degradation. Both persist for the entire server session with no recovery mechanism.

**In scope:**

- `_get_reranker()` non-caching-on-failure behavior — coordinated with `12mha-enh`
- `_start_background_model_downloads()` background thread on `WaveIndex` — file-only download for all three models (DOCS_MODEL, CODE_MODEL, RERANKER_MODEL), never sets any model fields
- Unconditional thread spawn in `build_server()` — no in-memory model probe at startup
- Daemon thread + double-spawn guard

**Out of scope:**

- Retry logic for a failed download within the thread
- Exposing download status or progress via an MCP tool
- Detecting or re-downloading a stale or corrupted cached model
- `_docs_embedder` / `_code_embedder` fields on `WaveIndex` — confirmed dead (set to `None` in `__init__`, never written elsewhere); removal is a code-reviewer task in this change's review lane, not an implementer task

## Acceptance Criteria

- AC-1: `build_server()` returns without waiting for any download to complete — the server is ready to accept requests immediately.
- AC-2: After the background thread completes downloading a missing embedding model, the next `_get_embedder()` call from a search handler succeeds without a server restart.
- AC-3: After the background thread completes downloading the reranker, the next `_get_reranker()` call from a search handler returns a live `TextCrossEncoder` instance without a server restart.
- AC-4: If a background download fails for one model, the thread continues attempting remaining models — a single failure does not abort the batch.
- AC-5: When all models are already cached on disk, the thread exits without downloading anything and without loading any model into memory.
- AC-6: The background thread is a daemon thread and does not prevent the server process from exiting cleanly.
- AC-7: No model is loaded into the server's working memory at startup — instantiation occurs only when a search handler first calls `_get_embedder()` or `_get_reranker()`.
- AC-8: When `HF_HUB_OFFLINE=1` is set, no background thread is spawned and no download is attempted.

## Tasks

- [ ] Modify `_get_reranker()` in `server.py` (coordinated with `12mha-enh` task): on offline load failure, return `None` without setting `self._reranker` — do not cache `None`; only set `self._reranker` on successful load
- [ ] Add `_model_downloads_started: bool = False` to `WaveIndex.__init__` as a double-spawn guard
- [ ] In `_start_background_model_downloads()`: check `os.environ.get("HF_HUB_OFFLINE") == "1"` before the flag check; if set, log the suppression message and return immediately without spawning
- [ ] Before coding: verify the correct file-existence check API — confirm whether `huggingface_hub.try_to_load_from_cache(repo_id, filename)` covers both `TextEmbedding` and `TextCrossEncoder` cached artifacts, or whether fastembed exposes a cache-path helper; the check must not instantiate any session
- [ ] Before coding: confirm the download-without-instantiation path — verify whether `huggingface_hub.snapshot_download(repo_id, local_files_only=False)` reliably downloads all files that `TextEmbedding` and `TextCrossEncoder` require, or whether a fastembed-internal download method is needed
- [ ] Add `_start_background_model_downloads()` to `WaveIndex`: check `self._model_downloads_started`; if already started, return immediately; set flag; read `DOCS_MODEL`, `CODE_MODEL`, `RERANKER_MODEL` via `self._indexer_constant()`; dedup model names; spawn `threading.Thread(target=..., daemon=True)` whose body iterates each model, file-checks, downloads if missing, logs per-model result, never raises, never sets any model field on `self`
- [ ] Update `build_server()` in `server.py`: after `index = WaveIndex(root)`, call `index._start_background_model_downloads()` unconditionally
- [ ] Add tests in `test_server_tools.py`: thread skips models already cached; thread downloads missing models; failure on one model does not skip remaining models; double-spawn guard prevents second thread; `HF_HUB_OFFLINE=1` suppresses thread spawn entirely; `_get_reranker()` does not cache `None` and succeeds on retry after simulated download; no model field (`_reranker`, `_docs_embedder`, `_code_embedder`) is set by the thread

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| reranker-no-cache-failure | implementer | `12mha-enh` wave-index-reranker | Modify `_get_reranker()` — must coordinate with 12mha |
| startup-download | implementer | reranker-no-cache-failure | `_start_background_model_downloads()` + `build_server()` update |
| tests | implementer | startup-download | test_server_tools.py |
| dead-code-review | code-reviewer | tests | Remove `_docs_embedder` and `_code_embedder` fields from `WaveIndex.__init__` (server.py:128-129) — confirmed dead; verify no reads or writes exist anywhere in server.py before removing |

## Serialization Points

- `framework_edit_allowed` gate required for `server.py` and `test_server_tools.py`.
- This change must be implemented after `12mha-enh` lands — it depends on `_get_reranker()` and `RERANKER_MODEL` being in place.

## Affected Architecture Docs

`docs/architecture/search-architecture.md` — add a note that the server self-heals missing model caches via background download at startup; update the "model availability" section after `12mha-enh` arch doc updates are written.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Non-blocking startup is the core requirement — blocking would be worse than no-download behavior |
| AC-2 | required | Embedding recovery is the highest-value outcome — missing embedders cause hard search failures |
| AC-3 | required | Reranker recovery has no value unless the downloaded model is picked up |
| AC-4 | required | A single bad model must not block recovery of the others |
| AC-5 | required | Thread must not re-download or do unnecessary work on the happy path |
| AC-6 | required | Daemon thread is non-negotiable — a non-daemon thread would block server exit |
| AC-7 | required | Eager memory load at startup increases baseline footprint for all users; lazy-load contract must be preserved |
| AC-8 | required | `HF_HUB_OFFLINE=1` is an explicit operator opt-out; ignoring it would violate the offline contract that the rest of the server upholds |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Change scoped to reranker only; extended to embedding models | `build_server()` (server.py:6913), `WaveIndex.__init__` (server.py:119) — no startup prewarming; `_docs_embedder`/`_code_embedder` confirmed dead fields (set to `None` in `__init__`, never written elsewhere in server.py) |
| 2026-05-14 | Wave Council readiness review — 1 blocking finding resolved | `HF_HUB_OFFLINE=1` suppression added as Requirement 7, AC-8, task, and test |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Single background thread for all models | Simpler; models download sequentially with per-model error isolation; avoids thread-per-model complexity | One thread per model — more parallel but harder to guard against double-spawns and concurrent cache writes |
| 2026-05-14 | Background thread, not subprocess | Simpler; model download is pure I/O with no isolation requirement; fastembed writes to its own cache dir | Subprocess — heavier, requires IPC to signal completion |
| 2026-05-14 | Daemon thread | Server must not be kept alive by an in-progress download | Non-daemon — would prevent clean exit if download is still running at shutdown |
| 2026-05-14 | Startup call in `build_server()`, not `WaveIndex.__init__` | `__init__` runs in test contexts without a live network; startup download semantics belong at the server entry point | `__init__` — pollutes construction with network-side-effect behavior |
| 2026-05-14 | Thread downloads files only — never sets model fields | Preserves lazy-load contract: models enter working memory only when a search handler first needs them; eager load at startup increases memory footprint for all users | Store downloaded model in `self._reranker` from thread — correct but loads model even when reranking may never be used in that session |
| 2026-05-14 | Unconditional spawn in `build_server()` — cache check internal to thread | Avoids probing model availability in `build_server()` via instantiation, which would load models into memory; thread self-checks with a file-existence test | Probe first then conditionally spawn — probing via `_get_embedder()`/`_get_reranker()` instantiates the model, violating the no-eager-load constraint |
| 2026-05-14 | `_get_reranker()` must not cache `None` | If failure is cached, background download completion is never observed and RRF fallback becomes permanent for the session | Cache `None` after first failure — breaks the retry-after-download contract |
| 2026-05-14 | No change to `_get_embedder()` caching behavior | `_get_embedder()` already re-instantiates on every call and raises on failure without caching — the retry-after-download contract is already satisfied | Change `_get_embedder()` to cache `None` — would break retries |

## Risks

| Risk | Mitigation |
|------|------------|
| File-existence check API is not stable across fastembed versions | Verify against the installed fastembed version; fall back to a direct cache-dir path check if `huggingface_hub.try_to_load_from_cache()` is unavailable |
| Download runs over a metered or slow connection unexpectedly | `HF_HUB_OFFLINE=1` env var prevents all downloads if set — explicit opt-out already exists; document in arch notes |
| Cache dir write contention if `setup_index.py` runs concurrently with the server | fastembed/HF Hub write atomically by file hash; concurrent writes to the same model are idempotent |
| Flag race: two callers of `_start_background_model_downloads()` before flag is set | Flag is set synchronously before the thread is spawned; both callers share the same `WaveIndex` instance |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
