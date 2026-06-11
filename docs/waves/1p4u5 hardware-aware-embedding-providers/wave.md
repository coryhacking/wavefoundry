# Wave Record

Owner: Engineering
Status: implementing
Last verified: 2026-06-11

wave-id: `1p4u5 hardware-aware-embedding-providers`
Title: Hardware Aware Embedding Providers

## Objective

Make Wavefoundry setup choose the best verified local embedding execution provider instead of silently defaulting to CPU on capable hardware. The wave covers NVIDIA/CUDA and Apple Silicon/CoreML as distinct provider paths, with CPU as the safe fallback when provider installation, correctness, or performance checks do not pass.

## Changes

Change ID: `1p4u0-enh hardware-aware-embedding-provider-selection`
Change Status: `implemented`
Change ID: `1p4u1-enh coreml-available-is-acceptable`
Change Status: `planned`

## Wave Summary

This wave adds hardware-aware embedding provider evaluation to setup and indexing. It should close with setup logs that clearly explain why CPU, CUDA, or CoreML was selected, tests that cover provider decisions without physical GPU hardware, docs that tell operators how to verify or remediate provider selection, and a narrower Apple Silicon policy that accepts CoreML when it is available and CPU fallback remains correct.

## Journal Watchpoints

- **Framework edit gate:** implementation touches `.wavefoundry/framework/scripts/setup_index.py` and likely `indexer.py`; open `framework_edit_allowed` before code edits and close it immediately after.
- **Provider availability is not enough:** CUDA/CoreML must be selected only after package/provider verification and a bounded active-model correctness/performance probe; otherwise fall back to CPU with an explicit reason.
- **No system mutation:** do not install NVIDIA drivers, CUDA toolkit packages, Homebrew packages, or OS-level dependencies; setup remains Python-tool-venv-local.
- **Package-risk watchpoint:** `fastembed-gpu` / `onnxruntime-gpu` compatibility with Python version, OS, and the `uv --exclude-newer` age guard must be discovered before implementation locks the dependency plan.
- **Apple Silicon is separate from CUDA:** `CoreMLExecutionProvider` is evaluated independently and must not be treated as a generic GPU equivalent.

## Review Evidence

- wave-council-readiness: READY-WITH-NOTES — readiness sign-off recorded 2026-06-11. Single-change wave `1p4u0` is coherent and implementable: it targets setup/index provider selection without changing retrieval ranking, chunking, graph indexing, or embedding model selection. Required guardrails for implementation: CPU remains the safe fallback; CUDA and CoreML are evaluated as distinct provider paths; provider availability alone is insufficient without package/provider verification and a bounded active-model correctness/performance probe; no OS-level driver/toolkit/package-manager mutation is in scope; CI coverage must use mocks rather than requiring physical NVIDIA or Apple Neural Engine hardware. Architecture/docs updates are required because setup topology and indexing-provider diagnostics become part of the operator contract.
- implementation: PASS — 2026-06-11. Implemented shared provider policy (`provider_policy.py`), setup-time CUDA dependency planning and provider diagnostics, bounded active-model provider probe, runtime provider reuse in `indexer.py`, named secondary provider handling, operator override support, and docs updates. Verification: focused setup tests OK; provider-selection tests OK; `wave_validate` docs-lint OK; full framework suite `python3 .wavefoundry/framework/scripts/run_tests.py` ran 3137 tests across 29 files OK.
- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-11: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, architecture-reviewer; rotating-seat: architecture-reviewer; strongest-challenge: hardware/provider detection can become brittle or misleading if CUDA/CoreML availability is treated as proof of faster correct embeddings, or if setup mutates system-level drivers/toolkits outside Wavefoundry's local-only contract; strongest-alternative: document manual provider installation instead of changing setup, rejected because the observed failure mode is silent CPU fallback on capable hardware and docs alone would not make setup choose or explain the best verified local provider.)

## Dependencies

- No external wave dependencies.
