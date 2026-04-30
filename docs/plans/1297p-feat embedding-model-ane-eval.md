# Embedding Model Evaluation and ANE Acceleration

Change ID: `1297p-feat embedding-model-ane-eval`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-04-29
Wave: TBD

## Rationale

Wavefoundry currently uses `BAAI/bge-small-en-v1.5` (ONNX INT8) for both docs and code embeddings. It works, but two specific signals motivate revisiting model choice and acceleration path:

**1. The 512-token truncation is invisible.** Markdown sections can exceed 512 tokens; Python AST chunks for long functions also exceed it. The current model silently truncates without warning. Long-context candidates (`nomic-embed-text-v1.5`, `jina-embeddings-v2-small-en`) handle 8192 tokens but were 3–24× slower in initial testing — eliminating jina, leaving nomic as a real candidate if quantization works.

**2. Apple Silicon is not being used.** The benchmark in this session showed CoreML provider via ONNX Runtime is statistically indistinguishable from CPU (1.36s vs 1.38s) because INT8 ONNX ops largely fall back to CPU rather than dispatch to the Neural Engine. The ANE prefers FP16 or Apple's palettized quantization in native Core ML format. The hardware capability is sitting idle; the question is whether the engineering cost to use it is justified.

The naive answer (just convert the model to Core ML) skips two questions: (a) is `bge-small` the right model in the first place, or would a different model be a better target for conversion? (b) what is the actual workload-weighted speedup, given that incremental indexing — the dominant operation — is already sub-second?

This plan establishes a measurement-driven decision before code is written. The output is a documented choice across three axes (model family, format, acceleration path) with reproducible benchmarks and a quality-parity gate.

## Requirements

1. The evaluation must measure three workloads explicitly, not just batched throughput:
  - **Incremental update**: 1–5 changed files, ~5–30 chunks, end-to-end including model load if cold.
  - **Full rebuild**: realistic project-scale corpus (≥1000 chunks), end-to-end.
  - **Query embedding**: single-query latency (P50, P95) — this is the user-facing tool-call critical path.
2. The evaluation must include a quality-parity check on a hand-curated retrieval ground-truth set drawn from this repository (≥20 query/expected-result pairs covering both code and docs).
3. The evaluation must report peak resident memory for each candidate, measured during full rebuild — OOM was a real failure mode and re-introducing it is unacceptable.
4. The evaluation must remain cross-platform: any chosen primary path must work on Linux x86_64 and Linux arm64, not only macOS arm64. Acceleration on Apple Silicon is a layered optimization, not a replacement.
5. Candidate matrix must include at minimum:
  - `BAAI/bge-small-en-v1.5` ONNX INT8 (current baseline)
  - `BAAI/bge-small-en-v1.5` Core ML FP16 (converted via `coremltools`)
  - `BAAI/bge-small-en-v1.5` Core ML palettized (Apple LUT quantization)
  - `nomic-ai/nomic-embed-text-v1.5` Core ML FP16 — only candidate that addresses the 512-token issue
  - One static-embedding option (`model2vec` distillation of bge-small) as an upper-bound speed reference
6. Conversion artifacts must be deterministic and reproducible from a checked-in script — not a one-off notebook. The script must take the upstream model identifier and produce a `.mlpackage` with a recorded SHA-256 of the resulting weights.
7. The chosen Core ML path must coexist with the ONNX path: the indexer continues to load ONNX on non-Apple-Silicon hosts and on Apple Silicon hosts where the Core ML cache is absent. No platform must regress.
8. Any model swap (independent of acceleration) must trigger a full index rebuild via the existing `model_versions` change-detection in `meta.json`. Mixed-model indices are not allowed.
9. The decision criteria must be written down in this doc *before* the benchmark runs, not retrofitted afterward. Threshold values for go/no-go are stated explicitly under Decision Criteria.
10. The benchmark harness itself must be checked in under `.wavefoundry/framework/scripts/benchmarks/` so it is rerunnable when fastembed, coremltools, or hardware changes.

## Scope

**Problem statement:** Embedding model choice and acceleration path were inherited from the MCP foundation feature without explicit comparison. Latency data captured in this session reveals (a) ONNX CoreML provider gives no speedup for our quantized model, (b) the 512-token limit silently truncates real chunks, and (c) we have not measured query-time latency, which is the agent-facing critical path. Without a documented evaluation, future "should we change the model" questions have no anchor.

**In scope:**

- Workload definition and benchmark harness covering incremental, full-rebuild, and query workloads
- Quality-parity ground-truth set authored from this repository
- Conversion script `convert_to_coreml.py` for ONNX → Core ML `.mlpackage` (FP16 and palettized variants)
- Tokenizer parity test (Hugging Face `tokenizers` reproducing fastembed's token IDs exactly for the chosen model)
- Indexer integration: format detection (`onnx` vs `coreml`), provider auto-selection, opt-in conversion command in `setup_index.py`
- `meta.json` extension to record format (`onnx`/`coreml`) alongside model name, so a Core ML cache going stale forces a rebuild
- Tests covering: format detection, conversion-script idempotency, tokenizer parity, fallback to ONNX when `.mlpackage` absent, model-version change triggers rebuild

**Out of scope:**

- MLX-native runtime — fails the cross-platform requirement and is not required to use the ANE
- Re-training or distilling new models — only off-the-shelf candidates considered
- GPU-accelerated indexing on Linux/Windows (CUDA path) — provider detection already routes correctly; explicit benchmarking deferred until we have a CUDA host to measure on
- Rebuilding the framework distribution index (`.wavefoundry/framework/index/`) in Core ML format — that index is consumed read-only and the format choice should match whatever the project-local indexer uses; covered transitively
- Replacing the embedding library entirely (e.g., switching off fastembed) — too large a blast radius for a model-choice decision

## Acceptance Criteria

- AC-1: A benchmark harness at `.wavefoundry/framework/scripts/benchmarks/embed_bench.py` runs each candidate against incremental/full/query workloads and emits a JSON report with P50, P95, peak RSS, and quality scores.
- AC-2: A retrieval ground-truth set at `.wavefoundry/framework/scripts/benchmarks/retrieval_eval.json` with ≥20 (query, expected_paths) entries, covering code and docs in roughly equal proportion.
- AC-3: A conversion script at `.wavefoundry/framework/scripts/convert_to_coreml.py` produces a `.mlpackage` from a fastembed-supported model name, deterministically, with conversion logs and weight SHA-256.
- AC-4: Tokenizer parity test confirms the standalone `tokenizers` pipeline emits identical token IDs to fastembed's internal tokenizer for ≥100 sample inputs spanning English prose, code, and edge cases (long inputs, unicode, code with `<` `>` `&`).
- AC-5: A decision document at `docs/architecture/decisions/embedding-model-and-format.md` captures the chosen model, format, conversion provenance, measured numbers, and explicit rejection reasons for non-chosen candidates.
- AC-6: If Core ML path is adopted: `_get_embedder()` selects format based on cache presence + platform; existing tests still pass; new tests cover format selection logic.
- AC-7: `meta.json` records `format` alongside `model_name` so a model or format change forces a full rebuild via the existing `model_versions` mechanism.
- AC-8: Full-rebuild latency on this repository's corpus does not regress on Linux CI runners (which lack ANE); this is the cross-platform safety check.
- AC-9: Quality regression vs. baseline `bge-small-en-v1.5 ONNX` is ≤5% on top-3 retrieval accuracy; if any candidate violates this, it is rejected even if faster.
- AC-10: Documentation updated: `AGENTS.md` MCP Server section, `docs/architecture/data-and-control-flow.md` Path 5 (Semantic Index Build), and `docs/contributing/build-and-verification.md` to include the conversion command and platform behavior.

## Decision Criteria

These thresholds are fixed before measurement. The benchmark report mechanically produces a recommendation by applying them.


| Criterion                                | Threshold                                            | Action if violated                                |
| ---------------------------------------- | ---------------------------------------------------- | ------------------------------------------------- |
| Quality regression (top-3 retrieval)     | ≤5% vs baseline                                      | Reject candidate                                  |
| Full-rebuild speedup on Apple Silicon    | ≥3× vs current ONNX path to justify Core ML adoption | Stay on ONNX                                      |
| Query embedding speedup on Apple Silicon | ≥5× to justify warmed-model resident process         | Skip warm-process work                            |
| Cross-platform regression                | 0% on Linux/CI                                       | Block adoption regardless of mac speedup          |
| Peak memory growth                       | ≤2× baseline                                         | Reject candidate                                  |
| 512-token truncation rate on this corpus | If <2% of chunks exceed 512 tokens                   | Long-context model is not justified for this repo |


If no candidate meets the speedup threshold *and* quality gate, the recommendation is to **stay on the current model and current path** and revisit when fastembed or coremltools materially change.

## Tasks

**Phase 1 — Methodology (no code changes to runtime):**

- Author retrieval ground-truth set (≥20 query/expected pairs sampled from this repo).
- Build benchmark harness skeleton with the three workloads and the ground-truth scorer.
- Measure baseline (`bge-small-en-v1.5` ONNX INT8) on this repo and record numbers.
- Compute 512-token truncation rate on this repo's chunks (informs whether long-context is needed).

**Phase 2 — Conversion + measurement:**

- Write `convert_to_coreml.py` producing FP16 and palettized variants of `bge-small-en-v1.5`.
- Validate tokenizer parity with standalone `tokenizers`.
- Measure all candidates from Requirement 5 against the harness.
- Produce JSON benchmark report and a human-readable comparison table.

**Phase 3 — Decision and integration (only if criteria are met):**

- Author `docs/architecture/decisions/embedding-model-and-format.md` with the chosen path and rejected alternatives.
- Extend `_get_embedder()` to load Core ML when available, fall back to ONNX otherwise.
- Extend `meta.json` schema to record `format` and force rebuild on format change.
- Add `setup_index.py --convert-coreml` opt-in command.
- Update tests: format selection, fallback behavior, conversion idempotency, tokenizer parity.
- Update documentation per AC-10.

**Phase 4 — Defer or close:**

- If decision is "no change", close this change with the benchmark report archived as the decision evidence and the harness retained for future re-evaluation.

## Agent Execution Graph


| Workstream          | Owner       | Depends On                                         | Notes                                                       |
| ------------------- | ----------- | -------------------------------------------------- | ----------------------------------------------------------- |
| ground-truth-set    | Engineering | —                                                  | Hand-curated; can run independently of any code             |
| bench-harness       | Engineering | ground-truth-set                                   | Pure measurement; no runtime changes                        |
| coreml-conversion   | Engineering | —                                                  | Self-contained; outputs `.mlpackage` artifacts              |
| tokenizer-parity    | Engineering | coreml-conversion                                  | Validates conversion before integration                     |
| measurement-pass    | Engineering | bench-harness, coreml-conversion, tokenizer-parity | Generates the report that feeds the decision                |
| decision-doc        | Engineering | measurement-pass                                   | Mechanical from the report + criteria                       |
| indexer-integration | Engineering | decision-doc                                       | Conditional: only runs if Core ML path is chosen            |
| docs-update         | Engineering | indexer-integration OR decision-doc                | If "no change", docs note the decision and harness location |


## Serialization Points

- `_get_embedder()` in `indexer.py` is a single-author surface for the integration phase; integration changes block other indexer work until merged.
- `meta.json` schema change requires a synchronized update of every reader/writer (`indexer.py`, `server.py`); cannot land piecewise.
- Adding a benchmark harness directory under `.wavefoundry/framework/scripts/benchmarks/` may overlap with the build_pack.py exclusion list; verify benchmarks are excluded from the framework distribution zip.

## Affected Architecture Docs

- `docs/architecture/current-state.md` — embedding model is named in the MCP topology; will need an update if the model or format changes
- `docs/architecture/data-and-control-flow.md` Path 5 (Semantic Index Build) — current text names `BAAI/bge-small-en-v1.5`; would need to reflect format detection if Core ML is adopted
- `docs/architecture/decisions/embedding-model-and-format.md` — new ADR (does not exist yet); records the decision, even if the decision is "stay"
- `docs/contributing/build-and-verification.md` — would need to document the conversion command if Core ML is adopted

## AC Priority

(Populated at Prepare wave.)


| AC    | Priority                                             | Rationale |
| ----- | ---------------------------------------------------- | --------- |
| AC-1  | required / important / nice-to-have / not-this-scope |           |
| AC-2  | required / important / nice-to-have / not-this-scope |           |
| AC-3  | required / important / nice-to-have / not-this-scope |           |
| AC-4  | required / important / nice-to-have / not-this-scope |           |
| AC-5  | required / important / nice-to-have / not-this-scope |           |
| AC-6  | required / important / nice-to-have / not-this-scope |           |
| AC-7  | required / important / nice-to-have / not-this-scope |           |
| AC-8  | required / important / nice-to-have / not-this-scope |           |
| AC-9  | required / important / nice-to-have / not-this-scope |           |
| AC-10 | required / important / nice-to-have / not-this-scope |           |


## Progress Log


| Date       | Update                                                                                                                                                                                                                                                                                        | Evidence                 |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| 2026-04-29 | Plan authored. Baseline numbers captured this session: bge-small ONNX INT8 1.36s for 64×150tok docs, 4.09s for 64×450tok docs; CoreML EP via ONNX statistically equal to CPU; nomic-Q registry entry broken (missing file in HF snapshot); jina-v2-small 24.5s for 64×450tok (disqualifying). | This conversation thread |


## Decision Log


| Date       | Decision                                                                                              | Reason                                                                                                                             | Alternatives                                                                                                                                                                  |
| ---------- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-04-29 | Defer model swap until benchmark methodology is in place                                              | Initial ad-hoc benchmarks are not a sufficient basis for a model decision; need ground-truth retrieval set and consistent harness. | Swap to `nomic-Q` immediately (rejected: registry broken, no quality data); ship Core ML conversion now (rejected: no proof it actually beats current path workload-weighted) |
| 2026-04-29 | Cross-platform constraint: Core ML is an optional acceleration layer, never a replacement             | Wavefoundry must work on Linux x86_64 and arm64. Apple-only paths cannot be the primary code path.                                 | Make MLX/Core ML the default and ship a separate Linux build (rejected: doubles the maintenance surface)                                                                      |
| 2026-04-29 | Static embeddings (`model2vec` etc.) included as upper-bound speed reference, not a primary candidate | Likely too lossy for semantic queries against prose docs, but useful as a sanity ceiling for what's achievable.                    | Exclude entirely (rejected: leaves a question unanswered)                                                                                                                     |


## Risks


| Risk                                                                                                                          | Mitigation                                                                                                                                       |
| ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `coremltools` conversion of attention/transformer ops can fail or silently produce wrong outputs on certain ONNX op patterns. | Tokenizer-parity test plus a numeric-similarity check (cosine ≥ 0.999 between ONNX and Core ML embeddings on a held-out set) before adopting.    |
| Tokenizer parity is hard: fastembed bundles tokenizer config we'd need to extract precisely.                                  | Extract `tokenizer.json` from the same HF snapshot fastembed uses; assert byte-identical token-ID outputs across ≥100 inputs before integration. |
| Apple `coremltools` and `fastembed` evolve independently; conversion script can break on version bumps.                       | Pin both versions in the conversion script; record versions + weight SHA-256 in conversion log; CI re-runs conversion on dependency bump.        |
| Quality regression invisible without a real eval set: synthetic benchmarks (MTEB) don't match wavefoundry's actual queries.   | Hand-curated retrieval set drawn from this repo's actual content is the gating criterion, not MTEB.                                              |
| Core ML cache file format may change between Apple OS versions, invalidating existing `.mlpackage` artifacts.                 | Record macOS major version + coremltools version in `meta.json`; on mismatch, treat the cache as stale and trigger reconversion.                 |
| Adopting Core ML masks the underlying issue if the chosen model is wrong for the workload.                                    | The decision-criteria table forces a comparison against the baseline; if Core ML doesn't deliver ≥3× full-rebuild speedup, we don't take it on.  |
| Benchmarks measured only on this 200-file repo may not generalize to large target repos.                                      | Harness accepts a `--corpus-path` argument so it can be re-run against a target repo before deciding to enable Core ML there.                    |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.