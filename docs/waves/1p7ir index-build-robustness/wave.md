# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-06-23

wave-id: `1p7ir index-build-robustness`
Title: Index Build Robustness

## Objective

Remediate the high-severity 1.8.0 field report (memory `project_field_feedback_1p8_oom_tls`): on a CPU-only, low-RAM WSL2 host the semantic index build OOM-kills the code embedding pass and fails **silently** (health reports `ready` while `code.lance` is absent), and the new `bge-small` code model can't download behind a corporate proxy (fastembed verifies against `certifi`, not the OS trust store). When this closes, index builds bound their memory on constrained hosts, fail loudly with remediation, report code-layer health honestly, and fetch models against the OS trust store.

## Changes

Change ID: `1p7is-bug index-health-reports-missing-code-layer`
Change Status: `planned`

Change ID: `1p7it-enh index-build-oom-guardrails`
Change Status: `planned`

Change ID: `1p7iu-enh model-fetch-os-trust-store-fallback`
Change Status: `planned`

Change ID: `1p7iv-debt bound-index-build-peak-memory`
Change Status: `planned`

## Wave Summary

Four changes, quick-wins first. `1p7is` (bug) makes `wave_index_health` honest about a missing code layer. `1p7it` (enh) adds OOM guardrails — auto-scaled embed buffer + sequential-degrade on a constrained profile + loud SIGKILL/OOM surfacing. `1p7iu` (enh) adds an OS-trust-store TLS fallback for model fetch. `1p7iv` (tech-debt) bounds peak build memory at the root by profiling the working set. The first three are small, independent, and faithfulness-safe — shippable together as a 1.8.1; `1p7iv` is the deeper follow-on, value-gated on a real memory profile.

## Journal Watchpoints

- **Sequencing watchpoint vs the OPEN `1p7de` wave (blocking on activation):** this wave is drafted and may be fully *readied* in parallel (readiness does not take the single-OPEN slot), but it is **blocked from activation** until `1p7de`'s slot frees. Activation priority (jump ahead of `1p7de` vs run next) is an operator decision at activation time.
- **Quick-wins-first watchpoint:** `1p7is` + `1p7it` + `1p7iu` are small/independent → a fast 1.8.1; `1p7iv` (root-cause memory bounding) is a **follow-up** that gates on a real before/after memory profile and may land later in the wave.
- **No-silent-success watchpoint (treat `1p7is` + `1p7it` as a blocking pair):** the OOM was invisible because health lied (`1p7is`) AND the wrapper swallowed the child SIGKILL (`1p7it`). Both must land for the failure mode to surface — shipping one without the other is blocking-incomplete.
- **Constrained-profile detection watchpoint:** reuse the `wave_gpu_doctor` CPU-only signal + a **cgroup/WSL memory probe** (NOT host RAM — WSL caps are lower). Keying off host RAM would mis-detect the constrained case that triggered this report.
- **TLS watchpoint — never disable verification:** the fix is OS-trust-store fallback / honoring `SSL_CERT_FILE`. **Follow-up, out of scope (not admitted):** pre-bundling embedding models in the distribution pack — a packaging effort that also helps air-gapped hosts; raise as its own wave if pursued.
- **Provenance:** interop-starter operator, framework 1.8.0+p7bt; root causes confirmed in source (`server_impl.py:598` health; `indexer.py` `_resolve_embed_buffer_chunks`/`_StreamingLayerWriter`; no OS-trust-store fallback present).

## Review Evidence

- operator-signoff: pending — approved when the operator confirms closure

## Dependencies

- No external wave dependencies.
