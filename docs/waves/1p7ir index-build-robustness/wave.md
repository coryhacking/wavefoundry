# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-23

wave-id: `1p7ir index-build-robustness`
Title: Index Build Robustness

## Objective

Remediate the high-severity 1.8.0 field report (memory `project_field_feedback_1p8_oom_tls`): on a CPU-only, low-RAM WSL2 host the semantic index build OOM-kills the code embedding pass and fails **silently** (health reports `ready` while `code.lance` is absent), and the new `bge-small` code model can't download behind a corporate proxy (fastembed verifies against `certifi`, not the OS trust store). When this closes, index builds bound their memory on constrained hosts, fail loudly with remediation, report code-layer health honestly, and fetch models against the OS trust store.

## Changes

Change ID: `1p7is-bug index-health-reports-missing-code-layer`
Change Status: `implemented`

Change ID: `1p7it-enh index-build-oom-guardrails`
Change Status: `implemented`

Change ID: `1p7iu-enh model-fetch-os-trust-store-fallback`
Change Status: `implemented`

Change ID: `1p7iv-debt bound-index-build-peak-memory`
Change Status: `implemented`

Completed At: 2026-06-23

## Wave Summary

Wave `1p7ir` (Index Build Robustness) delivered 4 changes: Index health reports `ready` when the code layer is missing, Index-build OOM guardrails: auto-scaled buffer, sequential-degrade, loud failure, Model fetch: fall back to the OS trust store on certifi verification failure, and Bound index-build peak memory independent of corpus size. Notable adjustments during implementation: Index health reports `ready` when the code layer is missing: **Implemented.** `_layer_health` now reports `code_present` + `code_sources_in_scope` (configured code prefixes ∩ indexed-eligible files — so docs-only repos are never flagged); `docs_health` adds `"code"` to `missing_layers`, sets `semantic_ready=false`, and `readiness_overview` becomes `incomplete`; `wave_index_health_response` emits a `code_layer_missing` diagnostic → `wave_index_build(content='code')`. 3 tests (incomplete / docs-only-no-flag / ready).; Index-build OOM guardrails: auto-scaled buffer, sequential-degrade, loud failure: **Implemented loud-failure + defer sequential-degrade.** AC-3: `setup_index._run_indexer` emits an OOM-specific SIGKILL message + remediation (lower `code/docs_embed_batch_size`, sequential `--content`, raise WSL2 memory) and raises. AC-4: dashboard `IndexBuilder` sets an OOM back-off on exit -9 — suppresses rearm + auto-retrigger (loud log), cleared by a clean build or explicit `signal_startup`. AC-2 (sequential-degrade) **deferred to `[~]`**: `1p7iv`'s batch-32 default bounds each pass to ~3.5 GiB so concurrent docs+code (~7 GiB) fits the in-scope ~15 GiB hosts — sequential-degrade is now narrow defense-in-depth for sub-8 GiB hosts. Suite 3432 OK.

**Changes delivered:**

- **Index health reports `ready` when the code layer is missing** (`1p7is-bug index-health-reports-missing-code-layer`) — 4 ACs completed. Key decisions: --------
- **Index-build OOM guardrails: auto-scaled buffer, sequential-degrade, loud failure** (`1p7it-enh index-build-oom-guardrails`) — 5 ACs completed. Key decisions: --------; Mitigate (buffer + sequential + loud) here; root-cause memory bounding is `1p7iv`
- **Model fetch: fall back to the OS trust store on certifi verification failure** (`1p7iu-enh model-fetch-os-trust-store-fallback`) — 4 ACs completed. Key decisions: --------; OS-trust-store fallback, verification kept ON
- **Bound index-build peak memory independent of corpus size** (`1p7iv-debt bound-index-build-peak-memory`) — 5 ACs completed. Key decisions: --------; Profile-first, then bound
## Journal Watchpoints

- **Sequencing watchpoint vs the OPEN `1p7de` wave (blocking on activation):** this wave is drafted and may be fully *readied* in parallel (readiness does not take the single-OPEN slot), but it is **blocked from activation** until `1p7de`'s slot frees. Activation priority (jump ahead of `1p7de` vs run next) is an operator decision at activation time.
- **Quick-wins-first watchpoint:** `1p7is` + `1p7it` + `1p7iu` are small/independent → a fast 1.8.1; `1p7iv` (root-cause memory bounding) is a **follow-up** that gates on a real before/after memory profile and may land later in the wave.
- **No-silent-success watchpoint (treat `1p7is` + `1p7it` as a blocking pair):** the OOM was invisible because health lied (`1p7is`) AND the wrapper swallowed the child SIGKILL (`1p7it`). Both must land for the failure mode to surface — shipping one without the other is blocking-incomplete.
- **Constrained-profile detection watchpoint:** reuse the `wave_gpu_doctor` CPU-only signal + a **cgroup/WSL memory probe** (NOT host RAM — WSL caps are lower). Keying off host RAM would mis-detect the constrained case that triggered this report.
- **TLS watchpoint — never disable verification:** the fix is OS-trust-store fallback / honoring `SSL_CERT_FILE`. **Follow-up, out of scope (not admitted):** pre-bundling embedding models in the distribution pack — a packaging effort that also helps air-gapped hosts; raise as its own wave if pursued.
- **Provenance:** interop-starter operator, framework 1.8.0+p7bt; root causes confirmed in source (`server_impl.py:598` health; `indexer.py` `_resolve_embed_buffer_chunks`/`_StreamingLayerWriter`; no OS-trust-store fallback present).

## Review Evidence

- wave-council-readiness: approved (READY) — prepare-council passed 2026-06-23 (moderator: wave-council; seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer; fixed-seat: red-team). Scope: 4 index-build-robustness changes from the confirmed 1.8.0 OOM+TLS field report — 1p7is index health honesty (bug), 1p7it OOM guardrails (enh), 1p7iu model-fetch OS-trust-store TLS fallback (enh), 1p7iv bound peak memory (tech-debt). Feasibility: all four grounded in verified source (server_impl.py:598 semantic_ready ignores a missing code layer; indexer.py _resolve_embed_buffer_chunks default too high + no constrained-profile sequential-degrade; no OS-trust-store fallback present; ~14 GiB working set vs 811 files). red-team risks + mitigations recorded: over-aggressive sequential-degrade (gate strictly on CPU-only + low-mem), WSL/cgroup limit misread (probe the cgroup limit, NOT host RAM; test with a stubbed limit), TLS fallback masking a real cert error (retry only on CERTIFICATE_VERIFY_FAILED with a real OS bundle, verification stays ON), false-degraded health on a docs-only repo (gate the code-layer requirement on code-sources-in-scope). security-reviewer: 1p7iu's never-disable-verification guard (AC-3) is the secure design. Conditions into implement: quick-wins-first (1p7is + 1p7it + 1p7iu shippable as a fast 1.8.x); 1p7is + 1p7it are a blocking pair (both needed for the OOM to surface); 1p7iv is profile-FIRST and may close as a confirmed-no-op if the buffer+concurrency was the whole story. Strongest alternative: split 1p7iv into a separate wave — kept together, value-gated. Out of scope (not admitted): model pre-bundling in the pack. Local-only; the TLS change keeps verification on; no detection/data change.
- wave-council-delivery: approved (PASS) — close-phase Wave Council delivery review 2026-06-23 (moderator: wave-council; seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer; fixed-seat: red-team; rotating-seat: security-reviewer (TLS trust-boundary change in 1p7iu)). Scope: 4 index-build-robustness changes delivered; full suite 3437 OK bytecode-free; docs-lint clean. Verdict PASS. 1p7iv (memory): root-caused the OOM to the forward-pass activation tensors in the onnxruntime CPU arena (off-RSS on GPU — the ~7-8x CPU-vs-GPU gap), proven by the EMBED_BATCH_SIZE sweep; fix is a per-model config-overridable forward batch (indexing.{code,docs}_embed_batch_size), default 32 — code 5.36 to 1.55, docs 9.47 to 2.49 GiB (~3.5-3.8x), equal-or-faster, vectors batch-invariant so NO re-embed. 1p7is (health): incomplete + code in missing_layers + code_layer_missing diagnostic when code sources are in scope but code.lance is absent; docs-only repos not flagged (gated on configured code prefixes intersecting indexed files); all-present still ready. 1p7it (guardrails): buffer default 1024 (throughput), OOM-specific SIGKILL message + remediation; AC-4 re-scoped post-review (operator) — the dashboard index-trigger was removed entirely (auto_index settings + IndexBuilder deleted; index updates MCP/hook-owned; build status read from the shared state) so the re-kill loop is structurally absent and the OOM back-off was reverted; buffer-autoscale AC dropped + sequential-degrade deferred, both measured-obviated by 1p7iv. 1p7iu (TLS): OS-trust-store fallback on chain-aware CERTIFICATE_VERIFY_FAILED honoring SSL_CERT_FILE/REQUESTS_CA_BUNDLE — secure-by-construction, verification NEVER disabled (test asserts no _create_unverified_context/CERT_NONE/verify=False), retry only against a real OS bundle, raises with remediation otherwise. red-team: no detection/binding/faithfulness change in any of the four (so no external-oracle review needed, unlike graph waves); the TLS fallback does not weaken trust (the OS store is a legitimate anchor; a cert not in it still fails); the OOM back-off cannot stick permanently. security-reviewer: the 1p7iu never-disable guard is the secure design, test-asserted. Sensors (0 registered), secrets (0 findings), harness-coherence (0 findings) all clean — no concrete high-severity issue. Deferred, recorded, non-blocking: 1p7it AC-2 sequential-degrade (sub-8 GiB hosts only); 1p7iu AC-5 real-proxy gate (needs a TLS-inspecting-proxy host). Local-only; no data/detection change. (Index transiently needs_update from the in-session handoff edit — hook refresh.)
- operator-signoff: pending — approved when the operator confirms closure

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-23: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; fixed-seat: red-team; rotating-seat: security-reviewer (trust-boundary/TLS change in 1p7iu); scope: 1p7ir index-build-robustness, 4 changes from the confirmed 1.8.0 OOM+TLS field report — 1p7is health honesty (bug), 1p7it OOM guardrails (enh), 1p7iu model-fetch OS-trust-store TLS fallback (enh), 1p7iv bound peak memory (tech-debt); strongest-challenge: 1p7iv may be a confirmed-no-op if the buffer + concurrency that 1p7it fixes was the whole ~14 GiB story — mitigated by its profile-FIRST AC + the recorded close-as-no-op risk; the constrained-profile detection must probe the cgroup/WSL limit not host RAM, and the TLS fallback must keep verification ON (security-reviewer); strongest-alternative: split 1p7iv into a separate wave — kept together + value-gated; conditions-into-implement: quick-wins-first (1p7is/it/iu as a fast 1.8.x), 1p7is + 1p7it a blocking pair, 1p7iv profile-first, model pre-bundling out of scope; security: the TLS fallback keeps verification ON, no detection/data change; local-only)

- **Close-phase Wave Council [delivery-council] — 2026-06-23: PASS** (moderator: wave-council; seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, docs-contract-reviewer, security-reviewer; fixed-seat: red-team; rotating-seat: security-reviewer (TLS in 1p7iu); scope: 1p7ir delivery — 1p7iv per-model forward-batch memory fix (default 32, ~3.5-3.8x less CPU RSS), 1p7is health honesty, 1p7it OOM message + dashboard index-trigger removed (auto_index + IndexBuilder deleted; back-off reverted; buffer-autoscale dropped, sequential-degrade deferred), 1p7iu OS-trust-store TLS fallback; verdict PASS — all 4 implemented + tested (suite 3437 OK), no detection/binding/faithfulness change, TLS verification never disabled (test-asserted), sensors/secrets/harness all clean; deferred non-blocking: 1p7it AC-2 (sub-8 GiB hosts), 1p7iu AC-5 (real-proxy gate))

## Dependencies

- No external wave dependencies.
