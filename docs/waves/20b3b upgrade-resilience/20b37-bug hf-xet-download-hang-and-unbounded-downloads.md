# Embedding Model Downloads Cannot Hang: Disable Xet By Default And Bound Every Download Path

Change ID: `20b37-bug hf-xet-download-hang-and-unbounded-downloads`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-10
Wave: 20b3b upgrade-resilience

## Rationale

**Brief.** Goal: a model download during setup, upgrade or an index build either completes or fails with a clear error within a bounded time. Consumer: an operator on a machine where the Hugging Face `hf_xet` backend stalls. Constraints: no new network dependency (the no-network principle covers the framework, and downloads already happen only when a model is missing; this is not a query-time network call), the operator can opt back in to xet, the already-cached fast path stays fast, behavior is the same on Windows, macOS, Linux and WSL2. Success: the model that hung in the field downloads, and any download that still stalls is abandoned at a deadline with a message.

**Precondition.** Do not Prepare or Implement this change until wave `20b3a upgrade-failure-surfacing` is implemented, fully delivery-reviewed and PAUSED under the operator-approved sequence (it also edits `wf_server/server_impl.py`). Re-derive every cited line anchor against the post-`20b3a` tree; line numbers in this document are advisory and symbols are the anchors. Re-Prepare these amended plans against that source before activation; all framework code edits require the root Stage Gate and applicable framework-edit authorization. Closure is not required or authorized.

Field report: the 1.28 upgrade switched the embedding model to `snowflake/snowflake-arctic-embed-s`, which was not cached. With `huggingface_hub` 1.18.0 and `hf_xet` the download wrote only `refs/main` and then idled for hours (0 CPU, no network, Ctrl+C ignored because the child runs windowless). Pre-downloading with `HF_HUB_DISABLE_XET=1` took 4 seconds. Verified at HEAD: no `.py` file mentions `HF_HUB_DISABLE_XET`, `hf_xet`, `xet` or `HF_HUB_ENABLE_HF_TRANSFER`. The setup path is partly bounded: `prewarm_models` (`setup_index.py` about 2107-2117) runs `_warm_model` (1417) inside `_hf_hub_timeout_scope()` (1048-1078, 30 second `HF_HUB_DOWNLOAD_TIMEOUT` and `HF_HUB_ETAG_TIMEOUT`, configurable via `setup.hf_hub_*_timeout_seconds`) and `_run_in_process_with_deadline` (2504-2526, 1800 second wall clock, daemon thread abandoned on timeout). INFERRED, NOT PROVEN IN THIS REPO: those socket timeouts do not govern a native `hf_xet` transfer. Unbounded sites outside that path: `accel_embedder.py:269-312` `_hf_download_cached_first` (`hf_hub_download` at 309, reached through the CA ladder `setup_index.retry_with_ca_bundle_ladder`) and `accel_embedder.py:383-416` `_ensure_fastembed_model_cached` (swallows all exceptions, with a caller at about 446). `_prewarm_gpu_accel` is at `setup_index.py:2125` and catches `Exception`; it calls the same helpers with no deadline wrapper (from a read of surrounding code, not traced line by line; tracing it is a task). Launchers that skip `prewarm_models` (MCP `index_build`, the dashboard watcher) use these cache-miss fallbacks directly; MCP `index_handlers.run_index_rebuild` launches `indexer.py` directly for docs/code builds without prewarming. `indexer._get_embedder` can bypass acceleration entirely and reach a third online route, `_text_embedding_cached_first`; the operator explicitly included this route under the same deadline.

**Import-time evidence.** Official Hugging Face Hub [1.18.0 constants.py](https://raw.githubusercontent.com/huggingface/huggingface_hub/v1.18.0/src/huggingface_hub/constants.py) defines import-time `HF_HUB_DISABLE_XET` and a default download timeout of 10 seconds; the [environment-variable documentation](https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables) confirms import-time reads and the xet-disable switch. In [1.18.0 `file_download.py`, `xet_get`](https://raw.githubusercontent.com/huggingface/huggingface_hub/v1.18.0/src/huggingface_hub/file_download.py), native `hf_xet.download_files` receives no Python socket/download-timeout argument. This supports the inference that our Python socket patch does not bound that native call; it is not a live Windows hang reproduction or proof for every dependency version. The repository's `_hf_hub_timeout_scope` already patches imported constants because late environment changes alone are ineffective. Early defaults plus a scoped patch remain necessary for long-lived processes; absent constants retain the warning/deadline fallback.

## Requirements

1. Two mechanisms, both required. (a) `os.environ.setdefault("HF_HUB_DISABLE_XET", "1")` as early as possible in each entry that can import `huggingface_hub`, so a fresh import sees it. (b) A scoped patch in the style of `_hf_hub_timeout_scope`, setting `huggingface_hub.constants.HF_HUB_DISABLE_XET` to true around the download helpers, added through `hasattr` like the existing constants (best-effort by contract), so the default holds even when the module was imported earlier in the same process. An operator-set `HF_HUB_DISABLE_XET=0` wins in both: it is read from the live environment at scope entry, never from the cached constant. When the constant does not exist in the installed `huggingface_hub`, the scope logs a warning that the xet default cannot be applied and relies on the deadline. `_offline_env` (`setup_index.py` about 1001) is confirmed not to touch `HF_HUB_DISABLE_XET`.
2. The environment default (a) is applied in the tool-venv bootstrap (`venv_bootstrap.py`) and at the top of `setup_index.py`, `accel_embedder.py`, `wf_server/server_impl.py` and `indexer.py`, ahead of their `huggingface_hub` and `fastembed` imports. The implementer enumerates any further entry by searching for imports of `huggingface_hub` and `fastembed`.
3. Apply the same configured model-download deadline and scoped xet/socket patch to all four online routes: `accel_embedder._hf_download_cached_first`, `accel_embedder._ensure_fastembed_model_cached`, `indexer._text_embedding_cached_first`, and `wf_server.server_impl._ensure_model_cached` (optional background warm-up). Wrap the whole `retry_with_ca_bundle_ladder` invocation, not individual attempts. Local-only/cached branches stay outside threads and deadlines; GPU prewarm is covered by these helpers without another wrapper. Direct CPU/indexer entry does not require prewarm. Honor existing `setup` deadline/socket settings for the known repository root in every route (defaults 1800 and 30 seconds); importing `setup_index` without its `main` is not configuration initialization. Root-less helper use retains documented defaults.
4. `_run_in_process_with_deadline` returns `None` (it discards `fn`'s result), but `_hf_download_cached_first` returns the cached file path. The change adds a returning variant (or a result box) and uses it for the online branch.
5. A distinct deadline exception names model, cache directory, elapsed time and opt-out/pre-download remedies. Re-raise it through `_ensure_fastembed_model_cached`, `_resolve_clean_onnx`, `_resolve_embedder_cpu_files`, `make_embedder` and `indexer._get_embedder` ahead of broad best-effort catches, so expiry cannot restart an independent online fallback. Ordinary non-deadline errors preserve existing fallback behavior; the direct CPU online branch is independently bounded when entered initially.
6. Actual indexer/MCP docs/code builds surface a deadline and fail when the required model cannot load. Optional `_prewarm_gpu_accel` logs the error and may continue toward CPU loading, which is itself bounded; optional reranker behavior remains explicit in the caller trace. Optional `_start_background_model_downloads` logs a deadline from `_ensure_model_cached` and continues its existing optional warm-up loop; query `_get_embedder` remains offline. No additional model, download pass or query-time network fallback is added. Enumerate required versus optional consumers without converting optional acceleration into a fatal setup requirement.
7. A daemon deadline cannot interrupt native work. Reserve an in-process in-flight slot keyed by canonical cache directory and model repository before starting the worker; release it only in that worker's `finally`, using its ownership token. Parent timeout never clears it. A same-model/cache retry fails fast while the worker lives and cannot start another writer. Preserve process-global scope restoration on success/error/timeout, and record the existing overlapping-different-model constants limitation honestly; the per-model guard is not a global isolation claim.
8. Never delete/quarantine partial cache files while the abandoned worker is alive. After worker exit, validate the actual model resolver/required weight files; an `.incomplete` blob or snapshot lacking weights must not count as a cached model and must reach the bounded online branch. Preserve cache layout/model choice.
9. The operator can restore xet by setting `HF_HUB_DISABLE_XET=0`. `docs/architecture/embedding-model.md` (which already justifies `HF_HUB_OFFLINE=1` and allows network only in setup) gains a short paragraph stating the cross-cutting rule: all four online routes run under a scoped constants patch plus the same configured deadline, with the `HF_HUB_DISABLE_XET=0` opt-out, and this is not a query-time network call. The deadline settings are noted in the `setup` notes of `docs/workflow-config.json`, and a `CHANGELOG.md` `[Unreleased]` bullet exists.
10. The deadline/error behavior has the same contract on Windows, macOS, Linux and WSL2; test with bounded blocking stubs and simulated Windows attributes where necessary. Do not claim native Windows or reboot qualification from off-Windows fixtures.

## Scope

**Problem statement:** A stalled native xet transfer is not covered by the existing socket timeouts, and four online download routes lack a complete deadline, so a model download can hang indefinitely.

**In scope:**

- The environment default and its placement before the import.
- The scoped constants patch, a returning deadline variant, and deadlines on the online branch of all four routes (including direct CPU builds and GPU prewarm consumers).
- The deadline error, its per-caller behavior, and documentation of the opt-out.
- Tests.

**Out of scope:**

- Changing the model choice or cache layout.
- Adding retries or mirrors.
- Making downloads non-blocking for the MCP server beyond the deadline.
- Putting the `local_files_only=True` cached path behind a thread.

## Acceptance Criteria

- [x] AC-1: Each framework entry module is imported in its own clean subprocess with `HF_HUB_DISABLE_XET` removed from the child environment, and `huggingface_hub.constants.HF_HUB_DISABLE_XET` is true after import; separately, with `huggingface_hub` imported first (the "imported earlier" case) the constant is true inside the scoped patch; when the live environment sets `HF_HUB_DISABLE_XET=0` the operator value wins in both cases. If `huggingface_hub` is not installed in the test environment the test skips with an explicit reason and a stub-based variant of the scope logic still runs.
- [x] AC-2: All four online routes abandon a blocking stub within a sub-second configured deadline and surface the distinct error. The helper/model-resolution catches re-raise it; every cached local-only path starts no thread. Tests release the worker on teardown and verify no leaked worker.
- [x] AC-3: Actual `_prewarm_gpu_accel` logs an optional deadline and preserves its documented CPU continuation; actual MCP/indexer docs/code entry without prewarm and initial direct-CPU entry surface bounded errors. A deadline through acceleration does not enter a second online fallback; ordinary non-deadline degradation remains tested. The actual optional background warm-up consumer logs an `_ensure_model_cached` deadline and continues; query loading stays offline.
- [x] AC-4: An ordinary non-deadline failure in `_ensure_fastembed_model_cached` keeps its prior best-effort behavior.
- [x] AC-5: The opt-out environment variable is documented in `docs/architecture/embedding-model.md` with the cross-cutting rule, the deadline settings are in the `docs/workflow-config.json` `setup` notes, and a `CHANGELOG.md` bullet exists.
- [x] AC-6: Record the exact official 1.18.0 import-time constant/native-call evidence and its limits; historical Windows hang causation remains inference unless measured. A stub lacking the constant warns and still enforces the deadline. Do not assert verification of every version in the dependency range.
- [x] AC-7: After the released timed-out worker exits, real model resolution rejects a pre-seeded `.incomplete` blob or missing weight file and invokes bounded re-download. While the worker lives, no cache deletion/quarantine occurs.
- [x] AC-8: A live timed-out worker retains its in-flight ownership: a same-model/cache retry fails fast without a second download. After worker exit the slot is released and retry succeeds; token-safe release cannot clear a newer owner. Constants restore on success/error/timeout, and different-model overlap limits are recorded.
- [x] AC-9: `_run_in_process_with_deadline`'s returning variant returns the helper's file path on success and the existing `None`-returning callers are unchanged.
- [x] AC-10: A direct CPU/indexer fixture launched without setup `main` honors the actual repository `setup` timeout overrides for the same four-route primitive; a root-less helper uses documented defaults. No new network/model download is used by tests.

## Tasks

- [x] Enumerate every module and child entry that imports `huggingface_hub` or `fastembed`.
- [x] Trace `_prewarm_gpu_accel` (`setup_index.py:2125`), the `make_embedder` call at `accel_embedder.py` about 446, the indexer launch paths, and the direct MCP docs/code launch without prewarm; record the result and confirm or amend Requirement 6.
- [x] Confirm `_offline_env` does not touch the variable, and record the official 1.18.0 constant/native-call evidence and missing-constant fallback without claiming every supported version was inspected; record the result.
- [x] Add the environment default ahead of those imports (single shared helper if the import order allows).
- [x] Extend the `_hf_hub_timeout_scope` style patch to set the xet constant through `hasattr`, reading the live environment at scope entry and warning when it cannot apply.
- [x] Add the returning deadline variant and wrap all four online routes in the same configured scope and deadline, leaving the cached fast path outside.
- [x] Write the deadline error class and message and propagate it through all named required-model catches; implement the worker-owned in-flight guard and record scoped-constant limitations.
- [x] Verify cache re-validation after an abandoned download (AC-7).
- [x] Add tests for AC-1 to AC-4 and AC-7 to AC-10 in `tests/test_setup_index.py`, `tests/test_accel_embedder.py` and the actual indexer/server entry and optional background warm-up fixtures.
- [x] Document the opt-out and cross-cutting rule in `docs/architecture/embedding-model.md` and the deadline settings in the `docs/workflow-config.json` setup notes; add a `CHANGELOG.md` bullet.
- [x] Verify root-specific settings outside setup `main`, real partial-cache resolver revalidation and all timeout/fallback consumers; keep historical Windows causation and different-model scope limits explicit (AC-6 through AC-10).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| import-site enumeration and env default | implementer | none | import order is the risk |
| deadlines on the online branch of the helpers | implementer | none | reuse existing primitives, add the returning variant |
| tests and docs | implementer | both | blocking stub, env cases, partial cache |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`, `.wavefoundry/framework/scripts/accel_embedder.py`, `.wavefoundry/framework/scripts/venv_bootstrap.py`, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`, `.wavefoundry/framework/scripts/tests/test_accel_embedder.py`, `.wavefoundry/framework/scripts/tests/test_indexer.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/architecture/embedding-model.md`, `docs/workflow-config.json`

`CHANGELOG.md` also changes (root-level file, so not a declared target). `server_impl.py` is also edited by the upgrade-failure-surfacing wave; that wave is implemented, delivery-reviewed and paused first.

## Affected Architecture Docs

Update: `docs/architecture/embedding-model.md` gains the opt-out note and the cross-cutting rule (all four online routes run under a scoped constants patch, the same configured deadline and the `HF_HUB_DISABLE_XET=0` opt-out; not a query-time network call, which preserves the no-network principle). No new boundary or flow: the change reuses existing timeout primitives inside the setup and embedding helpers.

## AC Priority


| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | Removes the observed hang. |
| AC-2 | required     | Bounds paths that currently have no limit. |
| AC-3 | required     | Required-model deadlines must propagate through real consumers. |
| AC-4 | important    | Do not regress best-effort caching. |
| AC-5 | important    | Operators need the opt-out. |
| AC-6 | nice-to-have | Pins inspected-version evidence and preserves unmeasured limits. |
| AC-7 | important    | An abandoned download must not poison the cache. |
| AC-8 | required     | Worker-owned retry suppression prevents concurrent cache writers. |
| AC-9 | required     | The helper returns a path; the deadline wrapper must carry it. |
| AC-10 | required | Operator explicitly included the third route and existing configuration. |


## Progress Log

Delivery numeric repair — 2026-10-10: the typed `QA-NUMERIC-DEADLINE` finding and cycle-2 implementer repair-start preceded edits. Both the shared downloader and existing setup-prewarm wrapper preserve accepted finite settings, including `1e20`, with platform-representable waits against one original monotonic budget. Nonfinite workflow settings use the existing default before ownership or worker launch. Setup retains its original return, exception and timeout semantics. Twenty deadline tests pass in 5.460 seconds without skips; real-parser direct indexing and setup prewarm controls pass with default, normal and oversized finite settings. The original numeric assertions fail on preserved old source; unbounded-join and budget-restart variants fail named assertions and are restored. Source changes stay in the existing setup script and deadline test module. Independent focused reverification and fresh canonical qualification remain pending.

Qualification repair verified — 2026-10-10: the optional background fixture accepts the actual root keyword, preserves its original continuation assertion, and asserts all three model/type/root calls plus worker completion. The exact inner ONNX scope expectation now has public delegation proof. Removing telemetry disabling fails both AST and dynamic controls; removing root forwarding and stopping after the first failed model each fail the named background test. All variants are restored. The integrated 80-test run passes in 13.954 seconds without skips; the actual four-route deadline and optional-consumer controls are included. No production download change or deadline/wait-budget exemption was required.

Readback, qualification repair — 2026-10-10: extraction of the inner embedder builder changed the exact ONNX import scope while the public path still disables telemetry. Update that one scope expectation and assert public delegation. The optional background worker now forwards its repository root; adapt its old two-argument test double while preserving continuation assertions and checking all model/type/root calls and worker completion. No download behavior, deadline, wait budget, skip or telemetry opt-out is loosened. Deleted-helper, missing-root and stop-after-failure controls must detect the corresponding broken behavior before qualification.


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-10 | Planned from upgrade field feedback; absence of xet handling and the unbounded helpers verified read-only; timeout ineffectiveness against native xet is inferred. | file:line citations in Rationale |
| 2026-10-10 | Confirming-round repair: citation corrected (`_prewarm_gpu_accel` is at `setup_index.py:2125`); returning deadline variant, online-branch-only wrapping, per-caller end behavior, in-flight guard, version caveat and test mechanics added. Product Intent: waived (bug fix, no product scope). | confirming readiness reviews of all six lanes |
| 2026-10-10 | Plan amended for all four routes, actual required-model catches/configuration, worker ownership and real partial-cache resolution; corrected 1.18.0 primary-source citation without claiming native Windows reproduction. | Named live owners/callers; official Hugging Face 1.18.0 sources above; operator direction |
| 2026-10-10 | Readback: previously a cold direct CPU or clean/resident/background download could wait indefinitely; now all four online routes share the configured whole-ladder deadline and live Xet opt-out. Cached local reads stay synchronous. A timed-out native worker retains its model/cache ownership and scoped constants until exit; required embedder catches propagate the distinct deadline, optional consumers log. | AC-1 through AC-10; assigned setup_index, accel_embedder, venv_bootstrap, indexer, server_impl hunks, focused tests and existing embedding/setup docs; no model/cache-layout/retry changes or native Windows claim. |
| 2026-10-10 | Thought: implement the common worker-owned primitive first so every online route shares configuration and retry ownership before consumer integration. | Current live MCP reads; readiness consumed by coordinator. |

| 2026-10-10 | Observe: four online routes use `download_with_deadline`, known roots resolve existing settings via `model_download_root`, and cached constructors never start workers. Distinct deadline survives every required model catch; optional GPU/reranker prewarm and background consumers log and continue. Actual full docs/code builds without prewarm expire at the configured deadline. Bench entry imports venv_bootstrap first; inline CoreML children import accel_embedder; all production Hub/fastembed imports therefore receive the early default. `_offline_env` does not change Xet. | `test_model_download_deadline`13 tests green5.384s; accelerator module and earlier12 scoped tests98green12.522s/one existing native-CoreML-cache skip; `test_setup_index`200green35.238s with temporary tool-venv fixture writes; `test_tree_kill_routing` + `test_lifecycle_gates_structure`48green48.418s. |
| 2026-10-10 | Observe: actual registered public `wf_reload_mcp` in a fresh fixture process preserves canonical setup_index identity, flat/package server aliases and the live worker owner. Timeout leaves constants and cache untouched until worker exit; token-specific release cannot clear another owner. Real resolver rejects missing weights/incomplete blob, performs bounded retry after release, and preserves the partial blob. Scoped constants restore on success/error and after timed-out worker exit. | Named scoped reload/ownership/resolver tests; zero real model/network fetches. Root-less defaults1800/30 retained. Different-model constants overlap remains an admitted limitation. |
| 2026-10-10 | Landing proof: disabling same-model reservation, loosening token-specific release, deleting indexer deadline propagation, and disabling resident missing-weight re-download each fails its named test; original sources restored. | `test_same_model_guard_survives_timeout_alias_and_owner_release` fails both reservation/token mutants; `test_required_accel_timeout_never_starts_cpu_fallback`; `test_partial_repo_real_resolver_redownloads_after_worker_exit`. |
| 2026-10-10 | Limits: official Hub1.18.0 sources already recorded above are the inspected-version evidence; native Windows historical causation and every dependency release remain unproved. Initial mixed-module/in-flight-source-edit diagnostic run is not qualification; setup's first isolated run had two sandbox-blocked mocked UV writes, resolved by temporary tool-venv override without weakening assertions or claiming a source fix. | Focused tests use release Events and join every worker; coordinator owns final canonical qualification and independent review. |
| 2026-10-10 | Observe: isolated current-source indexer suite passes407 tests209.433s; all37 ACs/tasks proved and implementation complete. | Current source frozen for this per-change computational checkpoint; coordinator retains whole-wave qualification/review/closure authority. |
| 2026-10-10 | Final landing proof: forcing Xet enabled despite live opt-out, deleting worker-scope restoration, and deleting the wall-clock timeout guard each failed a named assertion; restored source then passed all13 scoped consumer tests5.428s. | Live opt-out/error/default test and all-four-route root/socket/worker-finally test. Together with the four earlier mutants this proves seven rejected download mutants. Full-suite qualification remains coordinator-owned. |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-10 | Divergent pre-plan. Approach A: default-disable xet and add deadlines to the unbounded helpers. Approach B: deadlines only, leave xet enabled. Approach C: pre-download the model in a separate bounded step before long index phases. Selected A, delivered by both an early environment default and a scoped constant patch, wrapping only the online branch of all three routes. | A avoids the backend implicated by the report and bounds the residual risk; B leaves the hang to be detected only after the deadline, which is up to 30 minutes of idle; C helps setup but not the helpers that skip prewarm. The environment default alone is a no-op once `huggingface_hub` is imported (the repository's own documented hazard, `setup_index.py:1013-1019`), so the constant patch is required for long-lived processes such as the MCP server. Wrapping only the online branch keeps the cached fast path free of a thread on every launcher spawn. | B is slower to recover; C is incomplete alone and could be added later. Trade-off accepted: xet's faster transfers are lost by default, restorable via `HF_HUB_DISABLE_XET=0`. The operator chose the same deadline for all three routes; a worker-owned per-model/cache in-flight guard is required. |
| 2026-10-10 | Operator selected the same deadline for all three online routes, including direct CPU/indexer; require worker-owned in-flight suppression and deadline propagation. | Direct MCP docs/code builds do not necessarily prewarm or use acceleration. | A follow-up leaving the third route unbounded was rejected. |
| 2026-10-10 | Coordinator includes a fourth existing online route, optional MCP background warm-up in `_ensure_model_cached`, under the stated coverage assumption after the optional preference question received no answer. This is not an additional operator decision. | Live preflight found a direct online CA ladder beyond the original three-route inventory. The same primitive meets the bounded-download objective within the declared server file. | Narrower three-route coverage remains available if directed; cached branches and query loading remain offline. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The variable is set after `huggingface_hub` is imported and has no effect. | Requirement 1(b) patches the constant; AC-1 asserts both a fresh import and the scoped patch. |
| An operator `HF_HUB_DISABLE_XET=0` is overridden by the cached constant. | The scope reads the live environment at entry (AC-1). |
| The constant is missing or differs in another installed hub version; 1.18.0 presence is sourced. | `hasattr` guard, a warning when it cannot apply, the deadline as backstop, and AC-6. |
| A deadline error turns today's CPU degradation into an index failure. | Requirement 6 states the per-caller behavior; non-deadline errors keep the old path; AC-3 and AC-4. |
| Slower downloads for operators who benefited from xet. | Documented opt-out. |
| An abandoned daemon thread keeps a half-written cache file or races a retry. | Deadline error names the cache directory; AC-7 requires re-validation; AC-8 covers the retry. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
