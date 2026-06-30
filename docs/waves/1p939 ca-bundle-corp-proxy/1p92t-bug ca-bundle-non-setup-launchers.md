# Apply CA trust bundle on non-setup model-download launchers

Change ID: `1p92t-bug ca-bundle-non-setup-launchers`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-30
Wave: `1p939 ca-bundle-corp-proxy`

## Rationale

Field report (macOS, Zscaler TLS-intercepting corporate proxy, Claude Code host agent, 1.9.8,
2026-06-30): `wf setup` completes successfully, but a code-index build triggered afterward via the
MCP `wave_index_build(content='code')` tool fails downloading `BAAI/bge-small-en-v1.5` with
`httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED]`. On the surface this looks like a GPU/accel
failure; it is a CA-trust gap.

`setup_index._merged_trust_bundle()` / `_apply_ca_bundle()` / `_host_agent_ca_bundle()` (the full
host-agent → operator → OS trust-store → certifi ladder, `setup_index.py:416-639`) already resolve
this correctly — but only inside `_warm_model()`, which only `prewarm_models()` calls
(`setup_index.py:1009`), which only `wf setup` invokes (`setup_index.py:1368`). Every other launcher
that can trigger a model download — the MCP `wave_index_build` tool, the dashboard's file-watcher,
and the server's background index refresh — calls into `accel_embedder._hf_download_cached_first()`
(`accel_embedder.py:97-110`, plain `hf_hub_download`) and
`accel_embedder._ensure_fastembed_model_cached()` (`accel_embedder.py:131-153`, plain
`fastembed.TextEmbedding(...)`), neither of which applies any CA bundle. Both already carry a docstring
acknowledging this exact bypass set for a related cold-cache concern
(`accel_embedder.py:131-138`: "...whenever a launcher spawns the indexer WITHOUT first running
`setup_index.prewarm_models` — most notably the dashboard's file-watcher").

Two host-specific factors make this concrete rather than theoretical: on macOS the OS-trust-store
rung yields nothing (system roots live in a binary keychain, not a PEM file), so the corporate root
is reachable only via `NODE_EXTRA_CA_CERTS` — a variable Claude Code (a Node host) sets for itself
but that Python never reads outside the setup-only ladder.

**Scope correction (pre-implementation MCP exploration, 2026-06-30):** the original Decision Log
claim that all non-setup launchers funnel through `accel_embedder` is incomplete.
`server_impl.py::_ensure_model_cached()` (the embedding branch, `server_impl.py:456-476`) makes its
own raw `TextEmbedding(model_name=model_name, local_files_only=False)` call that does not route
through `accel_embedder` at all. `_ensure_model_cached`'s docstring ("Download model files to cache
without loading into server working memory... so subsequent `_get_embedder()` calls succeed
offline") and its failure shape (an online HF metadata round-trip via `hf_api.py`) match the field
report's traceback more closely than the `accel_embedder` paths do — this is plausibly the literal
call site the report's `wave_index_build(content='code')` repro hit. Scope is expanded below to
cover it.

`WaveIndex._get_embedder()` (`server_impl.py:892-929`, the query-time lazy embedder loader) was
initially flagged alongside it but, on full read, is **out of scope**: every `TextEmbedding(...)`
call inside it passes `local_files_only=True` within `self._offline_model_env()` (which also forces
`HF_HUB_OFFLINE=1`) — it never attempts an online download, and raises a clear
`SemanticModelUnavailableOfflineError` directing the operator to run setup when the model isn't
cached. There is no TLS call to fix here.

**Delivery-phase scope correction (Wave Council delivery review, 2026-06-30):** the "exhaustive
`code_keyword` sweep" claimed in the readiness-phase Decision Log below was incomplete. A literal
search for the token `TextEmbedding(` cannot match `indexer.py::_text_embedding_cached_first()`
(`indexer.py:2105-2119`, reached via `_get_embedder()`), whose constructor call is invoked through
the `text_embedding_cls` parameter, not the literal class-name token. This is the embedder-
construction fallback used whenever `accel_embedder.make_embedder()` returns `None` (no GPU/CoreML/
CUDA/ROCm/DML offload — the common case on CPU-only/Linux/WSL2/CI hosts, and the fallback even on
GPU-capable hosts), and it is the path every one of this wave's three named launchers
(`wave_index_build(content='code'|'docs')`, the dashboard watcher, background refresh) actually hits
on that hardware class — `wave_index_build`'s routing only sends `content='all'`/`'graph'` through
the already-protected `setup_index.py` path (`server_impl.py:3467-3475`); `content='code'`/`'docs'`
go straight to bare `indexer.py`. Scope is expanded to cover it (AC-7).

Separately, the delivery review found that `ensure_ca_bundle_applied()` only mirrored
`_warm_model()`'s *proactive* host-agent-CA-var pre-config step, never its *reactive*
`_os_trust_store_candidates()` retry-on-cert-failure ladder — so a corporate-proxy environment whose
only working trust rung was an OS-bundle file (not a host-agent env var) remained broken for
non-setup launchers even though `wf setup` succeeded there. A new `retry_with_ca_bundle_ladder()`
helper closes this gap (see Tasks/Decision Log), making Requirement 1's "same resolved CA trust
bundle ... regardless of which launcher" claim accurate rather than aspirational.

## Requirements

1. Every code path that can trigger a Hugging Face Hub model download (`hf_hub_download` or
   `fastembed.TextEmbedding(...)`) must apply the same resolved CA trust bundle that
   `setup_index.prewarm_models()` already applies, regardless of which launcher (MCP tool, dashboard
   watcher, background index refresh, `wf setup` itself) initiated the download.
2. The fix must reuse the existing trust-resolution logic in `setup_index.py`
   (`_host_agent_ca_bundle`, `_merged_trust_bundle`, `_apply_ca_bundle`) rather than duplicating CA
   discovery in `accel_embedder.py` or `server_impl.py`.
3. Applying the bundle must be idempotent and cheap on a plain (non-corporate) environment — no
   behavior change, no added latency, no network call when no host-agent/operator CA var is set.
4. TLS certificate verification must remain ON in all cases; the fix only widens which trust anchor
   is used, never disables verification.
5. A `CERTIFICATE_VERIFY_FAILED` failure that still occurs after the bundle is applied (e.g. no
   resolvable corporate root) must surface a diagnostic that points the operator at the CA env vars,
   not a raw `httpx`/`huggingface_hub` traceback.

## Scope

**Problem statement:** model downloads triggered outside `wf setup` (MCP `wave_index_build`,
dashboard file-watcher, background index refresh) bypass the CA trust-bundle resolution that setup
already performs, causing `CERTIFICATE_VERIFY_FAILED` behind TLS-intercepting corporate proxies.

**In scope:**

- Applying the existing `setup_index` CA-resolution ladder at the model-download call sites in
  `accel_embedder.py` (`_hf_download_cached_first`, `_ensure_fastembed_model_cached`).
- Applying the same ladder at the embedding branch of `server_impl.py::_ensure_model_cached()`
  (`server_impl.py:456-476`) — an independent raw `TextEmbedding(...)` call site discovered during
  pre-implementation MCP exploration; not part of the original choke-point theory.
- Applying the same ladder at `indexer.py::_text_embedding_cached_first()` (`indexer.py:2105-2119`,
  reached via `_get_embedder()`) — the CPU/no-GPU embedder-construction fallback, a fourth raw
  call site discovered during the delivery-phase Wave Council review (AC-7).
- A REACTIVE candidate-iteration fallback (`setup_index.retry_with_ca_bundle_ladder()`) on top of the
  proactive `ensure_ca_bundle_applied()` step, so a confirmed `CERTIFICATE_VERIFY_FAILED` retries
  through `_os_trust_store_candidates()` the same way `_warm_model()` already does for `wf setup` —
  closing the ladder-parity gap found during the delivery-phase review.
- A clear diagnostic on a `CERTIFICATE_VERIFY_FAILED` failure that survives the applied bundle and the
  reactive ladder, operator-visible at every call site (including a log line at the two
  `accel_embedder.py` swallow points — `_resolve_clean_onnx`, `_resolve_reranker_cpu_files` — that
  previously discarded the diagnostic silently).
- Regression coverage proving a non-setup download path picks up a host-agent/operator CA var and the
  reactive ladder, for all four call sites (`accel_embedder` ×2, `server_impl`, `indexer.py`), via the
  real production call graph (`_get_embedder` -> `_text_embedding_cached_first`), not just the inner
  constructor in isolation.

**Out of scope:**

- The `uv` / `pip` install-time TLS handling — already covered by
  `_uv_install_env`/`_pip_tls_env` and the separate `field_feedback_uv_ssl_cert_file_conflict` line
  of work.
- Reworking the OS trust-store discovery itself (e.g. reading the macOS keychain natively) — the
  host-agent CA var rung already covers this report's repro.
- Any change to `_warm_model()`'s retry/candidate-iteration behavior during `wf setup` — that path
  already works correctly.

## Acceptance Criteria

- [x] AC-1: A code-index build triggered via `wave_index_build(content='code')` (no prior `wf setup`
      model warm in this process) succeeds when a host-agent CA var (`CODEX_CA_CERTIFICATE` /
      `CLAUDE_CODE_CERT_STORE` / `NODE_EXTRA_CA_CERTS`) points at a valid corporate root and the
      default certifi bundle would otherwise fail. **Delivery-phase correction:** the originally-cited
      evidence exercised `server_impl.py::_ensure_model_cached`, which is reachable only from the
      server's background-download worker thread, NOT from `wave_index_build(content='code')`'s real
      path (a subprocess spawn of bare `indexer.py`) — the literal repro went through the unfixed
      `indexer.py::_text_embedding_cached_first()` (AC-7) instead. Evidence (corrected): the real call
      graph is now covered by `test_falls_back_to_fastembed_cache_miss_applies_ca_bundle`
      (`test_accel_embedder.py`, exercises `_get_embedder` -> `_text_embedding_cached_first`) +
      `test_ensure_model_cached_embedding_download_applies_ca_bundle` (`test_server_tools.py`,
      background-download-worker path) + `test_applies_host_agent_bundle_when_stack_env_unset`
      (`test_setup_index.py`, the underlying proactive helper).
- [x] AC-2: The same CA-resolution behavior applies to the dashboard file-watcher's direct
      `indexer.py --content all` spawn and the server's background index refresh — not just the MCP
      tool path. **Delivery-phase correction:** the original evidence text ("the shared functions
      every such launcher already calls") was false — those launchers' CPU/no-GPU embedder path goes
      through `indexer.py::_text_embedding_cached_first()`, not `accel_embedder`, whenever
      `accel_embedder.make_embedder()` returns `None` (AC-7). Evidence (corrected): the fix is applied
      at all four call sites the named launchers can reach —
      `test_applies_ca_bundle_before_online_attempt_on_cache_miss`,
      `test_cached_first_applies_ca_bundle_on_cert_verify_failure` (`test_accel_embedder.py`,
      GPU-accel paths) + `test_falls_back_to_fastembed_cache_miss_applies_ca_bundle` (same file,
      CPU/no-GPU fallback path, AC-7).
- [x] AC-3: With no host-agent/operator CA var set, the new call adds no observable behavior change
      (no new network calls, no measurable latency regression) versus current behavior. Evidence:
      `test_no_op_in_plain_env`, `test_idempotent_single_application_per_process`
      (`test_setup_index.py`); `test_cached_first_no_ca_call_when_already_cached`,
      `test_no_ca_call_when_already_cached`, `test_falls_back_to_fastembed_no_ca_call_when_cached`
      (`test_accel_embedder.py`); `test_returns_on_first_success_no_candidates_tried`,
      `test_passes_through_non_cert_error_without_retry` (`test_setup_index.py`, the reactive ladder
      adds no extra work on success or on a non-cert error).
- [x] AC-4: A `CERTIFICATE_VERIFY_FAILED` that persists after the bundle is applied raises a
      diagnostic naming the CA env vars to set, instead of a bare `httpx`/`huggingface_hub`
      traceback. **Delivery-phase correction:** the diagnostic was reachable in isolation but was
      being silently swallowed (zero logging) by `accel_embedder.py`'s callers of
      `_hf_download_cached_first()` (`_resolve_clean_onnx`, `_resolve_reranker_cpu_files`) — fixed
      with a log line at both swallow points so the diagnostic text is operator-visible there even
      though those functions correctly keep their best-effort "never raises" contract.
      **Re-review correction (2026-06-30):** the structurally-identical third swallow point in
      `_ensure_fastembed_model_cached` (not wired to the ladder at all in the first pass — see Tasks)
      was missed; now also logged before its own pre-existing swallow. Evidence:
      `test_raise_with_ca_bundle_diagnostic_wraps_cert_verify_error`,
      `test_raises_diagnostic_when_all_candidates_exhausted` (`test_setup_index.py`);
      `test_ensure_model_cached_embedding_cert_failure_wraps_diagnostic` (`test_server_tools.py`);
      `test_resolve_clean_logs_before_degrading_on_failure`,
      `test_resolve_reranker_cpu_files_logs_before_degrading_on_failure`,
      `test_falls_back_to_fastembed_cert_failure_routes_through_diagnostic`,
      `test_swallows_persisting_failure_without_raising` (`test_accel_embedder.py`, now asserts the
      log line fires for the `_ensure_fastembed_model_cached` swallow point too).
- [x] AC-5: TLS verification is never disabled by the fix (no `verify=False` / equivalent introduced
      anywhere in the changed paths). Evidence: manual review of the diff — every changed call site
      only swaps which CA env vars are set (`SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`), no `verify=`
      parameter is introduced or touched anywhere; confirmed independently by the delivery-phase
      security-reviewer seat (fixed and rotating) — unanimous, no security regression.
- [x] AC-6: `server_impl.py::_ensure_model_cached()`'s embedding branch applies the same resolved CA
      trust bundle as the `accel_embedder` paths — an independent raw `TextEmbedding(...)` call site
      discovered during pre-implementation exploration. (`WaveIndex._get_embedder()` was considered
      and excluded — see Rationale: it is offline-only and never attempts a network call.)
      **Delivery-phase correction:** this call site is correctly wired and tested, but is reachable
      only from the server's background-download worker thread, not from `wave_index_build`'s
      subprocess-spawn path — it is no longer claimed to be "the literal repro path" (see AC-1/AC-7).
      Evidence: `server_impl.py:456-485`;
      `test_ensure_model_cached_embedding_download_applies_ca_bundle`,
      `test_ensure_model_cached_embedding_cert_failure_wraps_diagnostic` (`test_server_tools.py`).
- [x] AC-7 (added delivery-phase, required): `indexer.py::_text_embedding_cached_first()`
      (`indexer.py:2105-2119`, reached via `_get_embedder()`) — the CPU/no-GPU embedder-construction
      fallback used whenever `accel_embedder.make_embedder()` returns `None` — applies the same CA
      ladder (proactive + reactive) as the other three call sites. This is the literal path
      `wave_index_build(content='code'|'docs')`, the dashboard watcher, and background refresh all
      hit on any host without active GPU offload, and is plausibly the actual repro site for the
      original field report. Evidence:
      `test_falls_back_to_fastembed_cache_miss_applies_ca_bundle`,
      `test_falls_back_to_fastembed_cert_failure_routes_through_diagnostic`,
      `test_falls_back_to_fastembed_no_ca_call_when_cached` (`test_accel_embedder.py`,
      `IndexerAccelDispatchTests` — exercises the real `_get_embedder` ->
      `_text_embedding_cached_first` call graph, not the inner constructor in isolation).

## Tasks

- [x] Factor a small, idempotent `ensure_ca_bundle_applied()` (or equivalent) out of
      `setup_index`'s existing ladder (`_host_agent_ca_bundle` → `_merged_trust_bundle` →
      `_apply_ca_bundle`) that can be called cheaply and repeatedly without re-deriving the bundle
      each call. Done: `setup_index.py` (`ensure_ca_bundle_applied`, after `_apply_ca_bundle`).
- [x] Call it from `accel_embedder._hf_download_cached_first()` and
      `accel_embedder._ensure_fastembed_model_cached()` before the first download attempt
      (function-local import of `setup_index`, matching the existing `setup_index` ↔ `accel_embedder`
      import direction at `setup_index.py:1032`). Done: `accel_embedder.py`.
- [x] Wrap the resulting `CERTIFICATE_VERIFY_FAILED` (when it still occurs) with the same operator
      guidance message pattern already used in `_warm_model`'s `ModelPrewarmError`
      (`setup_index.py` ~line 685). Done: `setup_index.raise_with_ca_bundle_diagnostic()`.
- [x] Add a unit test exercising a non-setup download path (e.g. `_ensure_fastembed_model_cached`)
      with a host-agent CA var set against a mocked/forced cert-verify failure, asserting the bundle
      gets applied before the call succeeds. Done: `EnsureFastembedModelCachedCaTests`,
      `HfDownloadCachedFirstTests` (`test_accel_embedder.py`).
- [x] Add/confirm a no-corporate-env regression test asserting zero behavior change when no CA var is
      set. Done: `test_no_ca_call_when_already_cached`,
      `test_cached_first_no_ca_call_when_already_cached` (`test_accel_embedder.py`);
      `test_no_op_in_plain_env` (`test_setup_index.py`).
- [x] Make the bundle resolution a true one-time-per-process cache (module-level cache var on first
      call, not re-derived on every `_hf_download_cached_first`/`_ensure_fastembed_model_cached`
      invocation) — Wave Council prepare-review finding: enforces AC-3 explicitly rather than leaving
      "idempotent and cheap" to implementer judgment. Done: `_ca_bundle_apply_attempted` module flag
      in `setup_index.py`; `test_idempotent_single_application_per_process`.
- [x] State explicitly in the implementation (comment, not narration) whether `os.environ`
      (`SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`) mutation from `_apply_ca_bundle()` needs restore-on-exit
      at this call site — Wave Council prepare-review finding: `_warm_model()` always restores via
      try/finally because `wf setup` later shells out to `uv`/`pip` in the same process;
      `accel_embedder`/indexer launcher processes are short-lived and do not subsequently invoke
      `uv`/`pip`, so a one-way mutation is expected to be safe here, but the code must say so rather
      than rely on that being obvious. Done: stated in `ensure_ca_bundle_applied()`'s docstring.
- [x] Call the same `ensure_ca_bundle_applied()` helper from `server_impl.py::_ensure_model_cached()`'s
      embedding branch, before the download `TextEmbedding(...)` attempt
      (`server_impl.py:456-476`); wrap the resulting failure with
      `setup_index.raise_with_ca_bundle_diagnostic()`. Done: `server_impl.py:456-481`.
- [x] Open `wave_gate_open(gate='framework_edit_allowed')` before editing `setup_index.py`,
      `accel_embedder.py`, or `server_impl.py` (edit governance reports the gate closed by default)
      and close it immediately after all edits in this change are complete, per AGENTS.md Key
      Guardrails. Done: opened before the `server_impl.py` edit, closed immediately after.
- [x] Extend the unit test coverage (positive host-agent-CA-var case, negative no-corporate-env case)
      to also exercise `_ensure_model_cached()`'s embedding branch, not just the `accel_embedder` call
      sites. Done: `test_ensure_model_cached_embedding_download_applies_ca_bundle`,
      `test_ensure_model_cached_embedding_cert_failure_wraps_diagnostic` (`test_server_tools.py`).
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`. Done: 3,715 tests across 39 files,
      OK (2026-06-30).
- [x] **Delivery-phase fixes (Wave Council delivery review, 2026-06-30):**
- [x] Wire `ensure_ca_bundle_applied()` into `indexer.py::_text_embedding_cached_first()` (AC-7), the
      fourth raw call site missed by the original `code_keyword` sweep. Done: `indexer.py:2105-2129`.
- [x] Add `setup_index.retry_with_ca_bundle_ladder()`: a reactive fallback that walks
      `_os_trust_store_candidates()` on a confirmed cert-verify failure (mirroring `_warm_model`'s
      retry loop minus its `print()`s and restore-on-exit), closing the ladder-parity gap between
      `ensure_ca_bundle_applied()`'s proactive-only coverage and `_warm_model`'s full ladder. Done:
      `setup_index.py` (`retry_with_ca_bundle_ladder`, after `raise_with_ca_bundle_diagnostic`).
      **Re-review correction (2026-06-30):** the first pass wired this into only 3 of the 4 named call
      sites (`accel_embedder._hf_download_cached_first`, `server_impl._ensure_model_cached`,
      `indexer._text_embedding_cached_first`) — `accel_embedder._ensure_fastembed_model_cached` had
      only gained the proactive `ensure_ca_bundle_applied()` call, with no ladder fallback, found by
      the required code-reviewer lane during re-review. Fixed: now wired into all four call sites.
      Done: `accel_embedder.py:162-178`.
- [x] Add a log line at the `accel_embedder.py` swallow points (`_resolve_clean_onnx`,
      `_resolve_reranker_cpu_files`) so a persisting CA-trust diagnostic is operator-visible instead
      of silently discarded before the resident-model-path fallback. Done: `accel_embedder.py`.
      **Re-review correction (2026-06-30):** extended to the third, structurally-identical swallow
      point in `_ensure_fastembed_model_cached` (same code-reviewer finding as above) — logged before
      that function's own pre-existing best-effort `except Exception: pass` degrades to the CPU path.
      Done: `accel_embedder.py:174-178`.
- [x] Lock-protect `ensure_ca_bundle_applied()`'s check-then-set on `_ca_bundle_apply_attempted`
      (code-reviewer Level1 finding: the long-lived MCP server process can reach this helper from more
      than one worker thread). Done: `setup_index.py` (`_ca_bundle_apply_lock`).
- [x] Re-run a broader call-site sweep (not just the literal `TextEmbedding(` token that missed
      `indexer.py`) to rule out a fifth gap before closing — council action item. Swept
      `TextEmbedding(`, `text_embedding_cls`, `TextCrossEncoder(`, `hf_hub_download(`,
      `snapshot_download(`, `fastembed.TextEmbedding`, `from fastembed import` across
      `.wavefoundry/framework/scripts/**/*.py` (production files only). Found two additional
      `TextEmbedding(` sites beyond the four already covered, both confirmed offline-only by direct
      read — no fifth gap: `setup_index.py::_probe_embedding_provider()` (`wave_gpu_doctor`'s bounded
      provider-comparison probe, both calls pass `local_files_only=True`) and
      `server_impl.py::WaveIndex._get_embedder()` (the query-time lazy loader already excluded in
      Rationale — both its `TextEmbedding(...)` calls run inside `_offline_model_env()`, which forces
      `HF_HUB_OFFLINE=1` for the duration regardless of whether `local_files_only` is passed
      explicitly). Done.
- [x] Extend test coverage for all delivery-phase fixes, including exercising the real production call
      graph (`_get_embedder` -> `_text_embedding_cached_first`) rather than only the inner constructor
      in isolation per the council's explicit finding that the original tests didn't catch the AC-1/
      AC-2 gap. Done: `RetryWithCaBundleLadderTests` (`test_setup_index.py`, 5 tests);
      `IndexerAccelDispatchTests` +3 tests, `AccelEmbedderTests` +2 tests, `HfDownloadCachedFirstTests`
      updated (`test_accel_embedder.py`).
- [x] Re-run `python3 .wavefoundry/framework/scripts/run_tests.py` after the delivery-phase fixes.
      Done: 3,726 tests across 39 files, OK (2026-06-30).
- [x] **Re-review (independent code-reviewer + qa-reviewer lanes, 2026-06-30):** code-reviewer found
      `accel_embedder._ensure_fastembed_model_cached` was wired to `ensure_ca_bundle_applied()` but NOT
      to `retry_with_ca_bundle_ladder()` — the wave's "wired into all four call sites" claim was false
      for this one site; qa-reviewer independently verified AC-1/AC-2/AC-3/AC-4/AC-6/AC-7 are otherwise
      genuinely supported (re-ran tests, re-traced the `wave_index_build` routing, re-checked the
      no-fifth-gap claim firsthand) and rendered READY. Fixed the one gap: wired the ladder into
      `_ensure_fastembed_model_cached`, added its logging point, updated/re-ran tests
      (`test_swallows_persisting_failure_without_raising` now asserts the log line). Done:
      `accel_embedder.py:162-178`; full suite re-confirmed 3,726 tests OK.

## Agent Execution Graph

| Workstream     | Owner        | Depends On | Notes                                          |
| -------------- | ------------ | ---------- | ----------------------------------------------- |
| [workstream-1] | implementer  | —          | Single-lane fix; no parallelizable sub-scope.   |

## Serialization Points

- `accel_embedder.py`, `setup_index.py`, and `server_impl.py` are all touched by this change; no other
  in-flight work is known to touch any of the three, so no cross-change serialization is currently
  required. `server_impl.py` edits require the `framework_edit_allowed` gate (see Tasks/Risks).

## Affected Architecture Docs

N/A — confined to the existing indexing/CA-resolution module pair (`setup_index.py`,
`accel_embedder.py`); no module-boundary, integration-contract, or primary data/control-flow change.

## AC Priority

| AC   | Priority      | Rationale |
| ---- | ------------- | --------- |
| AC-1 | required      | The actual repro from the field report — the wave has no purpose without this. |
| AC-2 | required      | Without this, only the MCP-tool path is fixed and the dashboard/background-refresh paths (already named in the bug's own root-cause trace) keep failing — leaves the fix incomplete for its stated scope. |
| AC-3 | required      | A regression here would break the plain (non-corporate) environment, which is every other operator — unacceptable trade for a corp-proxy-only fix. |
| AC-4 | important     | Materially improves operator triage (raw traceback currently reads as a GPU/accel failure per the field report), but the underlying fix works without it. |
| AC-5 | required      | Non-negotiable security invariant — verified explicitly by the council's security-reviewer seat; no code path may disable TLS verification. |
| AC-6 | required      | Server-side embedding-cache call site; wave does not actually close the reported gap without it. |
| AC-7 | required      | Discovered during delivery-phase Wave Council review to be the literal call path every named launcher hits on any host without GPU offload — without it the wave does not close the reported gap on that hardware class, which falsified AC-1/AC-2 as originally evidenced. |

## Progress Log

| Date       | Update                                   | Evidence |
| ---------- | ----------------------------------------- | -------- |
| 2026-06-30 | Change doc authored from field report.    | This doc; `project_corporate_proxy_ca_bundle_setup_only` memory |
| 2026-06-30 | Scope expanded after pre-implementation MCP exploration found `server_impl.py` raw `TextEmbedding` call sites not covered by the original plan (Level 3 finding); change doc and wave record updated before any code edit. | `code_keyword(query='TextEmbedding(')`, `code_read` of `server_impl.py:400-476` and `:895-925` |
| 2026-06-30 | Implemented: `ensure_ca_bundle_applied()` / `raise_with_ca_bundle_diagnostic()` added to `setup_index.py`; called from `accel_embedder.py`'s two download functions and `server_impl.py::_ensure_model_cached()`'s embedding branch. All tasks and ACs complete. | `setup_index.py`, `accel_embedder.py`, `server_impl.py` diffs; 22 new/updated tests across `test_setup_index.py`, `test_accel_embedder.py`, `test_server_tools.py`; full suite 3,715 tests OK |
| 2026-06-30 | Delivery-phase Wave Council review (red-team primer + 4 fixed seats + rotating seat + synthesis, plus a separate code-reviewer lane) found a fourth unfixed call site (`indexer.py`) falsifying AC-1/AC-2/AC-6, plus a ladder-parity gap and a swallowed-diagnostic gap — NEEDS REVISION verdict, qa-reviewer NOT READY. Fixed: wired `indexer.py::_text_embedding_cached_first` (AC-7); added `setup_index.retry_with_ca_bundle_ladder()` reactive fallback wired into all four call sites; added logging at the two `accel_embedder.py` swallow points; lock-protected `_ca_bundle_apply_attempted`. Corrected AC-1/AC-2/AC-4/AC-6 evidence text. Extended test coverage to exercise the real production call graph, not just the inner constructor in isolation. | Wave record `## Review Checkpoints`/`## Review Evidence` delivery-council entries; `setup_index.py`, `accel_embedder.py`, `server_impl.py`, `indexer.py` diffs; new tests: `RetryWithCaBundleLadderTests` (5), `IndexerAccelDispatchTests` +3, `AccelEmbedderTests` +2, `HfDownloadCachedFirstTests` updated (`test_accel_embedder.py`, `test_setup_index.py`) |
| 2026-06-30 | Independent re-review (code-reviewer + qa-reviewer lanes, run separately rather than a full council re-pass). qa-reviewer independently re-verified all corrected ACs against code/tests firsthand (re-ran the suite, re-traced `wave_index_build` routing, re-confirmed the no-fifth-gap claim) and rendered READY — qa-reviewer required lane now satisfied. code-reviewer found one residual gap the qa-reviewer checklist didn't cover: `_ensure_fastembed_model_cached` had the proactive `ensure_ca_bundle_applied()` call but was never wired to `retry_with_ca_bundle_ladder()`, contradicting the "wired into all four call sites" claim — fixed (wired + logged), tests updated, full suite re-confirmed 3,726 tests OK. | This Progress Log entry; `accel_embedder.py:162-178` diff; `test_accel_embedder.py` `EnsureFastembedModelCachedCaTests` updated |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------- |
| 2026-06-30 | Apply the CA bundle at the model-download choke point inside `accel_embedder` (`_hf_download_cached_first` / `_ensure_fastembed_model_cached`), reusing `setup_index`'s existing resolution functions. | All non-setup launchers (MCP tool, dashboard watcher, background refresh) already funnel through these two functions, so fixing the choke point covers every launcher without touching each entrypoint. Reuses proven logic instead of duplicating CA discovery. | (A) Call `_apply_ca_bundle` at every process entrypoint (`server.py`, `indexer.py`, dashboard watcher) — rejected: scatters near-duplicate startup calls across multiple files for no added coverage over the choke point, and risks missing a future launcher. (B) Persist the resolved bundle to a cache file during `wf setup` and have other processes read it at startup — rejected: introduces a staleness/invalidation problem if the corporate CA var changes or rotates between setup and a later launcher run, with no clear invalidation trigger. |
| 2026-06-30 | Accept a one-way (non-restoring) `os.environ` mutation from `_apply_ca_bundle()` at the new `accel_embedder` call site, documented inline rather than wrapped in `_warm_model`'s try/finally restore discipline. | Wave Council prepare-review (red-team primer + security-reviewer seat) flagged that `_warm_model()` always restores because `wf setup` later shells out to `uv`/`pip` in the same process — a leaked corp-only `SSL_CERT_FILE` would break that. `accel_embedder`/indexer launcher processes (MCP tool, dashboard watcher, background refresh) are short-lived workers that do not subsequently invoke `uv`/`pip`, so the leak risk does not apply to this call site — but the code must state this explicitly (see Tasks) rather than leave it implicit. | (A) Reuse `_warm_model()`'s full retry+restore path directly instead of a new thinner helper — considered as the council's "best alternative not taken," rejected because it pulls in `_warm_model`'s candidate-iteration/print-diagnostics behavior that's tuned for the interactive `wf setup` flow, not a background indexer call. |
| 2026-06-30 | **Correction:** the original claim "all non-setup launchers funnel through `accel_embedder`" was false. Expand the fix to also cover `server_impl.py::_ensure_model_cached()`'s embedding branch — an independent raw `TextEmbedding(...)` call site discovered via pre-implementation MCP exploration (`code_keyword` for `TextEmbedding(`), before any code edit. | The earlier scope was based on tracing only `accel_embedder`'s own call graph; it never checked for sibling raw download call sites elsewhere in the codebase. `_ensure_model_cached`'s failure shape (online HF metadata round-trip) matches the field report's traceback more closely than the `accel_embedder` paths, making it plausibly the literal repro site. | None — this is a correction of a factual claim discovered through evidence, not a design trade-off between alternatives. |
| 2026-06-30 | **Second correction:** `WaveIndex._get_embedder()`, initially flagged alongside `_ensure_model_cached()` in the first correction, is excluded from scope after a full read of the function. | Every `TextEmbedding(...)` call inside it passes `local_files_only=True` within `self._offline_model_env()` (which also forces `HF_HUB_OFFLINE=1`) — it never attempts an online download and already raises a clear `SemanticModelUnavailableOfflineError` when the model isn't cached, directing the operator to run setup. There is no TLS call to fix; including it would have been a no-op edit to a function that doesn't have this bug. | None — corrects an over-inclusion from the first correction, caught by reading the full function body before editing rather than acting on the earlier partial read. |
| 2026-06-30 | **Third correction (delivery-phase):** the "exhaustive `code_keyword` sweep" claim was incomplete — `indexer.py::_text_embedding_cached_first()` is a fourth raw call site, invisible to a literal `TextEmbedding(` token search because the constructor is invoked via the `text_embedding_cls` parameter name. Expand scope to cover it (AC-7). | Discovered independently during delivery-phase review by the qa-reviewer seat (AC-by-AC call-graph tracing), the reality-checker seat (independent call-graph trace), and the separate required code-reviewer lane (evidence-table audit) — three different methods, zero counter-evidence. It is the path every named launcher actually hits whenever GPU acceleration is unavailable, which falsified AC-1/AC-2 as originally evidenced. | None — a correction of a factual claim discovered through evidence, not a design trade-off. |
| 2026-06-30 | Add a reactive candidate-iteration fallback (`retry_with_ca_bundle_ladder()`) to the proactive-only `ensure_ca_bundle_applied()`, walking `_os_trust_store_candidates()` on a confirmed cert-verify failure. | Delivery-phase red-team primer (constructive stance) and the rotating security-reviewer seat independently converged on the same alternative: `ensure_ca_bundle_applied()` mirrored only `_warm_model`'s proactive pre-config, never its reactive retry ladder, leaving any corporate-proxy environment whose only working trust rung was an OS-bundle file (not a host-agent env var) broken for non-setup launchers even though `wf setup` succeeded there. The fallback is additive (only engages on a confirmed cert-verify failure) and reuses `_warm_model`'s proven candidate logic minus its interactive `print()`s and restore-on-exit (already separately justified as unnecessary at these call sites). | (A) Reword Requirement 1/the Objective to scope explicitly to the proactive host-agent-var rung instead of fixing the gap — considered and rejected: the fallback is low-risk and additive, and actually closing the gap is stronger than downgrading the promise to match a narrower delivery. |
| 2026-06-30 | Add a log line at `accel_embedder.py`'s two `_hf_download_cached_first()` callers (`_resolve_clean_onnx`, `_resolve_reranker_cpu_files`) rather than changing their "never raises" contract. | Both delivery-phase findings (red-team primer first-principles stance; architecture-reviewer seat) confirmed `raise_with_ca_bundle_diagnostic`'s exception was being silently discarded by these two callers' blanket `except Exception: return None`, making AC-4's diagnostic operator-invisible at those call sites. Logging before degrading preserves the existing, separately-correct best-effort/graceful-degradation contract (these functions must never raise) while still surfacing the diagnostic text. | (A) Change the callers to re-raise instead of swallow — rejected: would regress the existing graceful-degradation behavior these functions are designed for (falling back to the resident-model/CPU path), which is correct and unrelated to this wave's scope. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Calling CA resolution on every download attempt could add latency in a hot path (background index refresh runs repeatedly). | Resolution must be cached/memoized per-process (AC-3); only the first call in a process does real work. |
| Reusing `setup_index` internals from `accel_embedder` could introduce a circular import. | `setup_index.py:1032` already imports `accel_embedder` function-locally inside `prewarm_models`; mirror that direction (function-local import in `accel_embedder`, not module-level) to avoid a cycle. |
| `server_impl.py` is a large framework script with edit-governance enforcement (`framework_edit_allowed` gate, currently closed); editing it without opening the gate first would be blocked or improperly out-of-policy. | Open `wave_gate_open(gate='framework_edit_allowed')` immediately before the edits and close it immediately after all three files are done, per AGENTS.md Key Guardrails (see Tasks). |
| `_ensure_model_cached()`'s embedding branch runs inside the long-lived MCP server process, not a short-lived subprocess like the `accel_embedder`/indexer launchers — a different lifetime than the rest of this change's call sites. | The one-way `os.environ` mutation is still safe here: `_apply_ca_bundle()` only widens trust (never narrows or disables verification), and the server process does not itself shell out to `uv`/`pip`. Confirmed for completeness, not because the original analysis (accel_embedder/indexer processes) directly covered this site. |
| (Delivery-phase) The new reactive `retry_with_ca_bundle_ladder()` could add latency on a confirmed cert-verify failure by retrying once per untried OS-trust-store candidate. | Only engages after the first attempt already failed a cert-verify check — a plain (non-corporate) environment never reaches it (AC-3 unaffected). Each candidate is tried at most once; the candidate list is short (a handful of platform paths + certifi default). |
| (Delivery-phase) `_ca_bundle_apply_attempted`'s lock-protected check-then-set could itself become a contention point if many threads race on first call. | The lock is held only for the cheap proactive-application path (env-var checks + at most one file-write-free `_apply_ca_bundle` call); the long-lived MCP server reaches this from at most two worker-thread call sites, not a high-concurrency hot path. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
