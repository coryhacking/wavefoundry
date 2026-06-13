# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-13

wave-id: `1p4wz embedding-retrieval-architecture`
Title: Embedding Retrieval Architecture

## Objective

Simplify and improve the docs retrieval stack: fold the separate shipped framework index into the single core docs index, split the embedding model so docs use `arctic-embed-xs` (the bake-off-measured docs winner) while code keeps `bge-small`, and turn hardware-aware provider *selection* into actual FP16 execution with an on-disk pre-compiled CoreML cache under `~/.wavefoundry/`. When this wave closes there is one docs index built locally with the best-per-kind model, and capable machines run the GPU fast path instead of always running the slower dynamic-shape CPU path. (Precision note, verified 2026-06-12: the deployed weights are FP — code/bge-small is FP16, docs/arctic is FP32 — not INT8 as earlier framing assumed.)

## Changes

Change ID: `1p4ww-ref fold-framework-index-into-core-docs`
Change Status: `implemented`

Change ID: `1p4wx-enh docs-code-embedding-model-split`
Change Status: `implemented`

Change ID: `1p4wy-enh local-embedding-acceleration-and-cache`
Change Status: `implemented`

Change ID: `1p517-enh fp16-coreml-embedding-acceleration`
Change Status: `implemented`

Change ID: `1p52p-enh fp16-coreml-reranker-acceleration`
Change Status: `implemented`

Completed At: 2026-06-13

## Wave Summary

Wave `1p4wz` (Embedding Retrieval Architecture) delivered 5 changes: Fold the framework index into the core docs index, Docs/code embedding model split (arctic-embed-xs for docs), Local FP16 embedding acceleration + on-disk compile cache, FP16 + CoreML-cached embedding acceleration (bespoke ORT session), and FP16/CoreML reranker acceleration. Notable adjustments during implementation: Fold the framework index into the core docs index: Scoped (doc-first). Two-layer surface mapped; coupling with `1p4wx` and migration/self-hosting wrinkles captured.; Fold the framework index into the core docs index: **Stage 1 (source + reads) IMPLEMENTED + green.** Scope narrowed (operator): fold ONLY framework SEEDS + README (the rest of `.wavefoundry/framework/` is framework-internal) → no framework code folded, no dedup needed; README + seeds tagged `seed`.; Fold the framework index into the core docs index: **Stage 4 (cleanup) STARTED — read path removed, green.**

**Changes delivered:**

- **Fold the framework index into the core docs index** (`1p4ww-ref fold-framework-index-into-core-docs`) — 7 ACs completed. Key decisions: --------; Eliminate the framework layer (fold into project docs index).
- **Docs/code embedding model split (arctic-embed-xs for docs)** (`1p4wx-enh docs-code-embedding-model-split`) — 6 ACs completed. Key decisions: --------; `DOCS_MODEL = arctic-embed-xs`.
- **Local FP16 embedding acceleration + on-disk compile cache** (`1p4wy-enh local-embedding-acceleration-and-cache`) — 7 ACs completed. Key decisions: --------; Cache the static ONNX + compiled CoreML model under `~/.wavefoundry/`.
- **FP16 + CoreML-cached embedding acceleration (bespoke ORT session)** (`1p517-enh fp16-coreml-embedding-acceleration`) — 7 ACs completed. Key decisions: --------; **Feed the models' existing weights + static-shape pin; let CoreML compile FP16. NO pre-conversion. (Empirically confirmed.)**
- **FP16/CoreML reranker acceleration** (`1p52p-enh fp16-coreml-reranker-acceleration`) — 7 ACs completed. Key decisions: --------; Accelerate the reranker with the Xenova FP16 export on CoreML.
## Journal Watchpoints

- **Sequencing (load-bearing):** `1p4ww` (fold) must land before or with `1p4wx` (split) — switching the docs model while a separately-shipped framework index still holds old-model vectors mixes two vector spaces in `docs_search`. `1p4wy` (acceleration) composes with whatever model is chosen.
- **Framework-edit gate:** implementation touches core framework scripts (`server_impl.py`, `indexer.py`, `chunker.py`, `build_pack.py`, `setup_index.py`, `provider_policy.py`); open `framework_edit_allowed` before edits and close immediately after.
- **Open forks to decide at Prepare/council:** (1) FP16-ONNX offline sourcing — ship in the pack vs. download-and-cache at setup vs. convert locally; (2) static-shape strategy — fixed batch + remainder handling vs. a small bucket set.
- **Migration:** existing installs have a shipped `.wavefoundry/framework/index/`; the fold must remove it and re-index framework docs into the project docs index on upgrade.
- **Self-hosting dedup:** this repo's `.wavefoundry/framework/docs/**` can duplicate `docs/**` — the fold must not double-index the same content.
- **Blast radius:** `1p4ww` refactors the search path (~20 `server_impl.py` sites); change the layer paths together and gate on the full suite. None of these are graph reads-edge/binding-faithfulness changes.
- **Principle:** model = global quality (pinned, CPU-floor-bounded, shipped index); provider/format = per-machine speed (INT8 CPU / FP16 CoreML+CUDA, vectors cos≈1.0 interchangeable).

## Review Evidence

- wave-council-readiness: READY-WITH-NOTES — readiness sign-off recorded 2026-06-11. The three changes (1p4ww fold, 1p4wx split, 1p4wy acceleration) are coherent, well-sequenced, and implementable; readiness granted with notes. Notes: (1) decide three open forks before implementation begins — 1p4wy FP16-ONNX offline sourcing (ship vs download-and-cache vs convert), 1p4wy static-shape strategy (fixed batch+remainder vs bucket set), and 1p4ww self-hosting dedup rule (which copy of duplicated framework docs to index); (2) implement fold (1p4ww) before the model split (1p4wx) so the docs vector space stays single-model; (3) the fold's server-layer removal (~20 server_impl sites) plus framework-layer test migration is the main sequencing risk — change the layer paths together and gate on the full suite. No security/secrets/binding-faithfulness concerns across the three changes.
- wave-council-delivery: READY-WITH-FIXES-APPLIED — delivery review recorded 2026-06-13. Review found one resolved fresh-install/runtime-contract issue and one docs-contract drift, both fixed before signoff: CPU-only installs now plan `onnx` so the INT8 static-shape reranker can build, and active `code_ask`/Guru/spec/ADR guidance now states the actual single ranking path (`reranked=true` when the cross-encoder runs on GPU FP16 or CPU INT8; `reranked=false` only when disabled/unbuildable). Full framework suite passed after fixes: `python3 .wavefoundry/framework/scripts/run_tests.py` → 3154 tests OK; `wave_validate` → docs-lint ok.
- operator-signoff: approved — operator authorized closure 2026-06-13 (after the full-path code review + fixes; suite green at 3153 OK, docs-lint ok).

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-11: PASS WITH NOTES** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat: architecture-reviewer; strongest-challenge: the 1p4ww framework-index fold is a high-blast-radius search-path refactor (~20 server_impl sites) carrying upgrade-migration and self-hosting-dedup obligations, and three design decisions remain unmade (1p4wy FP16-ONNX sourcing; 1p4wy static-shape strategy; 1p4ww self-hosting dedup rule) that must be settled before implementation rather than during; strongest-alternative: ship the docs-model split alone by rebuilding and shipping the framework index with arctic-xs and defer the fold, rejected because it perpetuates the shipping/version/model-pinning complexity this wave exists to remove and the operator explicitly chose to eliminate the framework index.)
- **Prepare-phase Wave Council [prepare-council] — 2026-06-12: PASS WITH NOTES** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; scope: re-run for the newly-admitted `1p52p` reranker FP16/CoreML acceleration; strongest-challenge: dropping the BAAI FP32 reranker removes the only CPU fallback model, so a failed FP16 load could blind the search ranker — MITIGATED: `_get_reranker()` already returns `None` on any load failure and every `_rerank` path degrades to vector order, and the CPU-FP16 path is our own ORT session (no CoreML dependency); the per-query feasibility delta (FP16 logits vs BAAI FP32) was measured at max 0.0154 / mean 0.0067 and the main `_rerank` min-max-normalizes per query, so the score scale is preserved. Required strengthening folded into ACs: AC-1 score-parity must span MULTIPLE queries (FP16 rounding is weight-precision, input-magnitude-independent, but test ≥3 queries) and doubles as a supply-chain integrity gate on the `Xenova` re-export (a tampered export would not match BAAI within tolerance). strongest-alternative: keep BAAI FP32 as the CPU fallback (two models/formats, +750 MB cache), rejected by operator for the single-code-path + cache savings since FP16 ranking and scale are identical.)
- **Delivery Wave Council [delivery-council] — 2026-06-13: READY-WITH-FIXES-APPLIED** (moderator: wave-council; primer-depth: full; seats: red-team, code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer; rotating-seat: performance-reviewer. Strongest challenge: the wave's final claim is hardware-adaptive retrieval quality across CoreML/CUDA/GPU/CPU, so the review must prove CPU-only installs retain the reranker and agents receive correct `code_ask` contract guidance, not just that this Apple-Silicon checkout runs fast. Findings resolved: **F1 resolved install/runtime issue / qa+performance** — CPU-only fresh installs did not plan `onnx`, but `StaticShapeReranker` needs `onnx` to pin the CPU INT8 model; patched `setup_index._should_plan_gpu_accel_dependencies()` and added `test_planned_required_imports_respects_forced_cpu` plus the explicit disable case. **F2 docs-contract drift** — active `code_ask`, Guru, MCP spec, ADR, and change-doc text still described the pre-1p52p GPU-only or no-cross-encoder agent path; corrected all active contract surfaces. **F3 reliability drift** — `_get_reranker()` mutated `HF_HUB_OFFLINE` while building the reranker, causing a parallel FastMCP settings read to fail; removed that unnecessary global env mutation. Verification: full framework suite 3154 tests OK; docs-lint ok. Material disagreements: performance-reviewer accepted the added CPU `onnx` dependency because CPU INT8 reranking is a required quality floor; docs-contract-reviewer required active docs to be fixed now while preserving clearly superseded progress-log history.)

## Dependencies

- No external wave dependencies.
