# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-13

wave-id: `1p4u5 hardware-aware-embedding-providers`
Title: Hardware Aware Embedding Providers

## Objective

Make Wavefoundry setup choose the best verified local embedding execution provider instead of silently defaulting to CPU on capable hardware. The wave covers NVIDIA/CUDA and Apple Silicon/CoreML as distinct provider paths, with CPU as the safe fallback when provider installation, correctness, or performance checks do not pass.

## Changes

Change ID: `1p4u0-enh hardware-aware-embedding-provider-selection`
Change Status: `implemented`
Change ID: `1p4u1-enh coreml-available-is-acceptable`
Change Status: `implemented`

Change ID: `1p4up-enh member-access-constant-reads`
Change Status: `implemented`

Change ID: `1p4uq-bug phase4b-background-build-reliability`
Change Status: `implemented`

Change ID: `1p4w9-enh docs-chunk-context-injection`
Change Status: `implemented`

Completed At: 2026-06-11

## Wave Summary

Wave `1p4u5` (Hardware Aware Embedding Providers) delivered 5 changes: Hardware-Aware Embedding Provider Selection, CoreML Available Is Acceptable, Member-access constant reads (graph `reads` for `A.B.C` qualified constant access), Phase 4b background code re-embed silently fails (status `idle`, no trace), and Docs-chunk section-breadcrumb context injection. Notable adjustments during implementation: Hardware-Aware Embedding Provider Selection: Added Apple Silicon/CoreML as an evaluated provider path, with correctness/performance gates before enablement.; Member-access constant reads (graph `reads` for `A.B.C` qualified constant access): Implemented after reverting the unfaithful `_simple_name` rsplit one-liner (a review found it over-binds calls + reads, incl. dropping 5 correct `external::url` import-reads on a real file). Member-access PATH approach: exact-qname, const-gated, never widens bare-leaf resolution. **Two adversarial faithfulness reviews:** the first found F1 (minor over-fire) + F2 (nit) + F4 (qualifier-shadow major) — all fixed; the final review found a **blocker** (`_ts_is_member_property_leaf` used `is` on tree-sitter wrappers → blanket-skip → dropped object/array const HEAD reads like `FRAMEWORK_FLOW.length`) — fixed `is`→`==`. Final state CLEAN: false-suppress + residual-over-fire dimensions clean, regression LOST=NONE (incl. real dashboard.js), calls unchanged. Full suite **3138 green**.

**Changes delivered:**

- **Hardware-Aware Embedding Provider Selection** (`1p4u0-enh hardware-aware-embedding-provider-selection`) — 10 ACs completed. Key decisions: --------; Prefer setup-time hardware-aware provider evaluation with verified fallback.
- **CoreML Available Is Acceptable** (`1p4u1-enh coreml-available-is-acceptable`) — 4 ACs completed
- **Member-access constant reads (graph `reads` for `A.B.C` qualified constant access)** (`1p4up-enh member-access-constant-reads`) — 5 ACs completed. Key decisions: --------; Resolve member-access reads by EXACT QUALIFIED PATH (not bare-leaf widening).
- **Phase 4b background code re-embed silently fails (status `idle`, no trace)** (`1p4uq-bug phase4b-background-build-reliability`) — 4 ACs completed. Key decisions: --------; Stamp the launcher's own pid early (overwritten by the real code-build pid on success).
- **Docs-chunk section-breadcrumb context injection** (`1p4w9-enh docs-chunk-context-injection`) — 6 ACs completed. Key decisions: --------; Implement as a CHUNKER change (breadcrumb in chunk `text` + `CHUNKER_VERSION` bump), not an indexer embed-step change.
## Journal Watchpoints

- **Framework edit gate:** implementation touches `.wavefoundry/framework/scripts/setup_index.py` and likely `indexer.py`; open `framework_edit_allowed` before code edits and close it immediately after.
- **Provider availability is not enough:** CUDA/CoreML must be selected only after package/provider verification and a bounded active-model correctness/performance probe; otherwise fall back to CPU with an explicit reason.
- **No system mutation:** do not install NVIDIA drivers, CUDA toolkit packages, Homebrew packages, or OS-level dependencies; setup remains Python-tool-venv-local.
- **Package-risk watchpoint:** `fastembed-gpu` / `onnxruntime-gpu` compatibility with Python version, OS, and the `uv --exclude-newer` age guard must be discovered before implementation locks the dependency plan.
- **Apple Silicon is separate from CUDA:** `CoreMLExecutionProvider` is evaluated independently and must not be treated as a generic GPU equivalent.

## Review Evidence

- wave-council-readiness: READY-WITH-NOTES — readiness sign-off recorded 2026-06-11. Single-change wave `1p4u0` is coherent and implementable: it targets setup/index provider selection without changing retrieval ranking, chunking, graph indexing, or embedding model selection. Required guardrails for implementation: CPU remains the safe fallback; CUDA and CoreML are evaluated as distinct provider paths; provider availability alone is insufficient without package/provider verification and a bounded active-model correctness/performance probe; no OS-level driver/toolkit/package-manager mutation is in scope; CI coverage must use mocks rather than requiring physical NVIDIA or Apple Neural Engine hardware. Architecture/docs updates are required because setup topology and indexing-provider diagnostics become part of the operator contract.
- implementation: PASS — 2026-06-11. Implemented shared provider policy (`provider_policy.py`), setup-time CUDA dependency planning and provider diagnostics, bounded active-model provider probe, runtime provider reuse in `indexer.py`, named secondary provider handling, operator override support, and docs updates. Verification: focused setup tests OK; provider-selection tests OK; `wave_validate` docs-lint OK; full framework suite `python3 .wavefoundry/framework/scripts/run_tests.py` ran 3137 tests across 29 files OK.
- wave-council-delivery: PASS (approved) — delivery sign-off recorded 2026-06-11. Delivery-phase Wave Council reviewed all five admitted changes (1p4u0 provider selection, 1p4u1 CoreML-acceptable, 1p4up member-access constant reads, 1p4uq Phase-4b reliability, 1p4w9 docs-chunk breadcrumb). Seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker. Strongest challenge: the 1p4up function-to-constant reads-edge binding change could silently mis-bind, and the 1p4w9 docs +10pp was measured pre-merge. Resolution: 1p4up binding faithfulness was adversarially verified during implementation (3 passes; a wrong-binding blocker found and fixed; regression diff vs baseline showed no lost edges); 1p4w9 is docs-gated and idempotent so it can only help docs and cannot regress code, the gain was measured on the identical section-prepend transform, and live re-confirmation is intentionally deferred to an operator-owned re-index. Verification: full suite 3145 green; docs-lint OK; no change_status_drift across the five changes and their change docs. No over-claim: the separate FP16/CoreML acceleration finding is scoped as plans 1p4ww/1p4wx/1p4wy, not claimed here.
- operator-signoff: approved — 2026-06-11, operator requested closure.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-11: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, architecture-reviewer; rotating-seat: architecture-reviewer; strongest-challenge: hardware/provider detection can become brittle or misleading if CUDA/CoreML availability is treated as proof of faster correct embeddings, or if setup mutates system-level drivers/toolkits outside Wavefoundry's local-only contract; strongest-alternative: document manual provider installation instead of changing setup, rejected because the observed failure mode is silent CPU fallback on capable hardware and docs alone would not make setup choose or explain the best verified local provider.)
- **Delivery-phase Wave Council [delivery-council] — 2026-06-11: PASS** (moderator: wave-council; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; scope: all five admitted changes; strongest-challenge: the 1p4up function→constant reads-edge binding change could silently mis-bind, and the 1p4w9 docs +10pp was measured pre-merge rather than on a live re-index; resolution: 1p4up was adversarially faithfulness-verified during implementation (3 passes, a wrong-binding blocker found+fixed, regression diff vs baseline LOST=NONE), and 1p4w9 is docs-gated + idempotent so it cannot regress code, with the gain measured on the identical transform and live re-validation intentionally deferred [~]; full suite 3145 green, docs-lint OK, no change_status_drift.)

## Dependencies

- No external wave dependencies.
