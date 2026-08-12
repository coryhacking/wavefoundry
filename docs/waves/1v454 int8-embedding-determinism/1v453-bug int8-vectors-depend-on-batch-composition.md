# INT8 Embedding Vectors Depend On Batch Composition

Change ID: `1v453-bug int8-vectors-depend-on-batch-composition`
Change Status: `implementing`
Owner: Engineering
Status: planned
Last verified: 2026-08-11
Wave: 1v454 int8-embedding-determinism

## Rationale

On a CPU-bound host the semantic index is built with the INT8 export, and that export quantizes
activations with 48 `DynamicQuantizeLinear` operators. Per the ONNX operator contract, that operator
emits a **scalar** scale derived from `ReduceMin` / `ReduceMax` taken over the whole input tensor with
no axis restriction, so one scale is computed across the entire batch. Every row's quantized values
therefore depend on the most extreme activation anywhere in its batch.

`accel_embedder.StaticShapeEmbedder.embed` groups 32 rows per inference call, and pads with empty
strings only when the group is short. Three consequences follow, all measured on this repository's
shipped `model_int8.onnx`:

1. **A chunk's stored vector depends on which other chunks shared its batch.** Holding the text and
   its position fixed and varying only the neighbours moves the vector:

   | Batch content (target text at row 0) | cos vs `1 real + 31 empty` |
   | --- | --- |
   | 1 real + 31 empty | 1.00000000 |
   | 1 real + 30 real + 1 empty | 0.99630791 |
   | 1 real + 16 real + 15 empty | 0.99551839 |
   | 1 real + 31 real | 0.99467921 |
   | 1 real alone | 0.99694288 |

2. **Re-indexing the same corpus is not reproducible.** Chunk ordering, or any change in chunk count
   that moves batch boundaries, reassigns neighbours and changes vectors. Position *within* a batch is
   stable (verified at cos 1.00000000), so this is batch membership, not nondeterminism.

3. **Queries and the index sit in different regimes.** A full 32-chunk batch carries no empty rows,
   while a query is encoded as 1 real row plus 31 empties. Measured through the production
   `StaticShapeEmbedder` on the same text: query shape versus bulk-index shape is **cos 0.996160**.
   The current declared fallback (full-precision fastembed against an INT8 index) is cos 0.990245, so
   the shipped query path is closer than the fallback but still does not match the index it queries.

Batch size is not the cause and was ruled out: batches of 2, 8 and 32 that all contain empty rows
agree at cos 1.00000000. The cause is batch composition.

The FP paths are unaffected, as the mechanism predicts. `model_fp16.onnx` carries zero quantization
operators, and both it and fastembed return cos 1.0 under the identical composition test. This is a
CPU-bound / `int8`-class defect only. GPU hosts embed and query at `full` class and are out of scope.

Batching is also not buying anything on the CPU path it compromises. The static graph pads every row
to 512 tokens, so a 32-row batch performs the same token work as 32 single-row calls. Measured on
64 realistic 512-token chunks: batch-32 33.7 ms/chunk versus batch-1 32.4 ms/chunk, a ratio of 0.96.
Encoding one row per call is marginally *faster* while removing the defect, and drops the CPU-bound
query path's peak resident memory substantially. (Planning estimated roughly 161 MiB from a bare
session probe; the implemented path measured 245 MiB against the 1353 MiB pinned baseline. See the
Progress Log for the as-built figure, which is the one to cite.)

## Requirements

1. On the INT8 path, every inference call carries exactly one real row, at index build time and at
   query time, so a text's vector is a function of that text alone.
2. The sequence-padding policy on the INT8 path is fixed and identical at index time and query time.
3. Query vectors and index vectors for identical text agree exactly on an INT8 index.
4. Embedding a corpus twice with different chunk ordering produces equal vectors.
5. The GPU / `full`-class path keeps its existing batching unchanged.
6. An existing INT8 index re-embeds exactly once when this lands, and does not re-embed on
   subsequent builds. The re-embed must be **scoped to `int8`-class layers**: a `full`-class index is
   not affected by this defect and must not be re-embedded. Note that
   `EMBEDDING_MODEL_SET_FINGERPRINT` is explicitly an all-layer compatibility boundary
   (`indexer.py`, the scoped-update guard above `_stale_model_layers`), so bumping it is the **wrong
   lever**: it would force every GPU host to re-embed both layers for a defect they do not have. The
   trigger must instead ride on the recorded precision-class token that
   `_precision_class_from_version` already parses, so only `int8` layers compare unequal.
7. The retrieval effect of the change is measured on a gold-labelled set before it is adopted, to the
   standard ADR `1p92d` set for the original INT8 decision. A recall regression blocks adoption.
8. A regression test fails if single-row encoding on the INT8 path is ever reverted to a batched form.

## Scope

**Problem statement:** INT8 index vectors are a function of batch composition rather than of the text
alone, which makes re-indexing non-reproducible and leaves every query systematically mismatched
against the index it searches.

**In scope:**

- Single-row encoding for the INT8 embedder at index and query time.
- Fixed, shared sequence-padding policy across both.
- Retiring the pinned 32x512 INT8 static graph for the CPU path in favour of the shipped dynamic
  `model_int8.onnx`, if single-row encoding makes the pin unnecessary.
- The one-time re-embed of existing INT8 indexes.
- The gold-set retrieval evaluation that gates adoption.
- Regression coverage for the composition property.

**Out of scope:**

- The GPU / FP16 path and its batching.
- The reranker (`StaticShapeReranker`), which has the same class of exposure but is a separate
  surface with its own candidate-pool shape. Investigate separately.
- Replacing dynamic quantization with a calibrated static export. Considered and rejected for now
  (see Decision Log); revisit only if the eval shows single-row encoding is insufficient.
- The `embedding-fastembed` bundle component and any change to the model set.
- Model-set version or fingerprint changes beyond what Requirement 6 needs.

## Acceptance Criteria

- [x] AC-1: On the INT8 path, each inference call contains exactly one real row, at index build time and at query time, asserted by a test that inspects the batch dimension actually submitted to the session.
- [x] AC-2: A text encoded on the INT8 path yields an identical vector regardless of what other texts are encoded before, after, or alongside it, asserted with the neighbour sets from the Rationale table.
- [x] AC-3: Embedding the same corpus twice with different chunk ordering produces equal vectors on the INT8 path.
- [x] AC-4: On an INT8 index, a query vector and the index vector for identical text agree at cos >= 0.999999.
- [x] AC-5: The GPU / `full`-class path still batches exactly as before, asserted by a test that fails if its batch dimension changes.
- [x] AC-6: An existing INT8 index re-embeds exactly once when this change lands, and a subsequent build with no content change re-embeds nothing.
- [x] AC-10: A `full`-class (GPU) index does **not** re-embed when this change lands, proven by building an existing `full`-class index across the change and asserting zero re-embedded chunks.
- [~] AC-7: A gold-labelled retrieval comparison of the current batched encoding against single-row encoding on an INT8 index is recorded in the Progress Log with per-query results, and shows no recall regression. **Status note (deferred by operator direction, 2026-08-12):** no gold-labelled eval set exists in this repository, so the comparison cannot be run as written. The operator accepted the accumulated executed evidence instead: real-graph composition invariance, reorder invariance, query-versus-index agreement, three killed mutants, and the full suite. The retrieval-quality question this AC was written to answer therefore remains formally unmeasured, and that is a known, accepted gap rather than a satisfied criterion. If a gold set is built later, run this comparison against it; the calibrated-export alternative in the Decision Log is the fallback if it regresses.
- [x] AC-8: The CPU-bound INT8 query path's peak resident memory is measured before and after, and recorded in the Progress Log.
- [x] AC-9: Single-row INT8 throughput is confirmed on a genuinely CPU-bound host, not only on a GPU-capable host driving the CPU execution provider. **Basis note (operator judgment, 2026-08-12):** measurement was taken on a GPU-capable host driving `CPUExecutionProvider`, which is literally the case this AC was written to exclude. The operator accepted it on field experience that this configuration is representative of what CPU-only deployments actually exhibit. Recorded explicitly so the evidence is not later mistaken for a measurement on GPU-less hardware.

## Tasks

- [x] Reproduce the composition dependence as a failing test before changing behaviour, using the neighbour sets in the Rationale.
- [x] Decide and record the fixed sequence-padding policy for the INT8 path, native length or 512, with the measurement behind the choice.
- [x] Route INT8 index-time encoding through single-row inference calls.
- [x] Route INT8 query-time encoding through the same single-row path, replacing the current padded 32-row query encode.
- [x] Determine whether the pinned `cpu_int8_static_32x512.onnx` is still needed once encoding is single-row; retire it for the CPU path if not.
- [x] Add an `int8`-scoped re-embed trigger riding the recorded precision-class token, NOT a bump of the all-layer `EMBEDDING_MODEL_SET_FINGERPRINT`; prove a `full`-class index is untouched.
- [x] Add the regression test required by AC-5 pinning the GPU path's batching.
- [~] Run the gold-set retrieval comparison and record per-query results. Deferred with AC-7: no gold set exists in this repository.
- [x] Measure peak RSS and throughput before and after, on a CPU-bound host.
- [x] Record the composition-dependence constraint in an ADR and cross-reference ADR `1p92d`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reproduce | implementer | — | Failing test for the composition property first; this is the oracle the fix is judged against. |
| encode-single-row | implementer | reproduce | `accel_embedder` index-time and `server_impl` query-time paths must move together, or query and index land in different regimes again. |
| reembed-trigger | implementer | encode-single-row | Fingerprint bump; verify exactly-once by building twice. |
| gpu-pin | qa | reproduce | Independent of the INT8 work; guards against collateral change to the `full` path. |
| eval | qa | encode-single-row | Gold-set recall comparison. Gates adoption, so it must be run by someone who did not author the encoding change. |
| adr | implementer | eval | Records the constraint and the measured outcome. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/accel_embedder.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_accel_embedder.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`

## Affected Architecture Docs

**Done:** `1v22e-adr int8-encoding-is-batch-composition-sensitive` records the constraint that INT8
activation scales are computed per-tensor across the batch, making single-row encoding a correctness
requirement rather than a performance choice, and cross-references ADR `1p92d` (whose recall-parity
result stands; it did not consider activation-scale scope). Indexed in
`docs/architecture/decisions/README.md`.

**Not done, deliberately:** `docs/architecture/data-and-control-flow.md` was NOT edited. It carries
three pre-existing drifts already tracked in the session handoff, and touching it here would mix this
wave's change into unrelated drift repair. Its description of the embedding path does not contradict
this change; it is simply less specific than the new ADR. Route that repair through the existing
follow-up rather than this wave.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The mechanism of the fix. |
| AC-2 | required | The defect itself; without this the change is unproven. |
| AC-3 | required | Reproducible re-indexing is the user-visible consequence. |
| AC-4 | required | Query and index agreeing is the second user-visible consequence. |
| AC-5 | required | The GPU path is the majority path and must not be disturbed. |
| AC-6 | required | Without an exactly-once re-embed, existing indexes hold mixed-regime vectors indefinitely. |
| AC-7 | required | Gates adoption per Requirement 7 and the ADR `1p92d` precedent. |
| AC-8 | important | Quantifies a claimed benefit; does not gate correctness. |
| AC-9 | important | Removes the single-host caveat on the throughput claim. |
| AC-10 | required | Without it, the obvious implementation (bump the all-layer fingerprint) silently re-embeds every GPU host for a defect they do not have. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-11 | Mechanism established and defect measured during a release session; no code changed. Composition dependence confirmed on the production `StaticShapeEmbedder`; batch size ruled out; FP16 and fastembed confirmed unaffected; single-row throughput measured at 0.96x of batched on 512-token chunks. | Probe transcripts in session; ONNX `DynamicQuantizeLinear` operator contract; 48 `DynamicQuantizeLinear` ops in the shipped `model_int8.onnx`. |
| 2026-08-11 | **Reproduction first.** Added `test_int8_cpu_embed_submits_one_real_row_per_call` and `test_gpu_path_still_batches_to_static_batch` before any behaviour change. The INT8 test failed non-vacuously against the shipped code (`[32] != [1, 1, 1, 1, 1]`) and the GPU test passed, so the oracle distinguishes the two paths. | `tests/test_accel_embedder.py`; pre-fix run recorded `AssertionError: Lists differ: [32] != [1, 1, 1, 1, 1]`. |
| 2026-08-11 | **Fix implemented (AC-1, AC-5).** `StaticShapeEmbedder.embed` submits one real row per call and never pads the batch when `provider == CPUExecutionProvider`; the GPU branch keeps `STATIC_BATCH`. The CPU branch of `__init__` now loads the shipped dynamic `model_int8.onnx` instead of building the batch-pinned `cpu_int8_static_32x512.onnx`, because a pinned graph cannot accept a single row. Session input dims confirmed dynamic: `['batch_size', 'sequence_length']`. The query path needed no separate edit: `server_impl._get_embedder` constructs this same class. | `accel_embedder.py` `StaticShapeEmbedder.__init__` CPU branch and `StaticShapeEmbedder.embed`; both new tests pass. |
| 2026-08-11 | **Verified on the real graph, not mocks (AC-2, AC-3, AC-4).** Same text, varying batch context: alone vs in-32-real-batch cos 1.00000012, vs in-5-batch 1.00000012, vs moved to position 10 in a full batch 1.00000012 (was 0.996160 / 0.99630791 / 0.99694288 before the fix). Reorder invariance across a 40-chunk corpus in two different orders: worst cos 1.00000000. Query shape vs index shape for identical text: cos 1.00000012. | Real `StaticShapeEmbedder` on the shipped `model_int8.onnx`, CPUExecutionProvider. |
| 2026-08-11 | **Re-embed trigger scoped to int8 (AC-6, AC-10).** Added `INT8_ENCODING_REVISION` and `_identity_fingerprint_for_class`, routed both compare sites (`build_index` docs/code `model_changed`) and the scoped-update guard and both write sites through it. A `full` layer keeps the unsuffixed fingerprint so GPU hosts do not re-embed; an `int8` layer carries the revision so it re-embeds exactly once. Deliberately NOT a bump of the all-layer `EMBEDDING_MODEL_SET_FINGERPRINT`, per the council finding. Census of literal `"int8"` comparisons ran first (`indexer._predicted_precision_class`, `server_impl._get_embedder`, `upgrade_wavefoundry`'s class allowlist); the class token is unchanged, so none of them needed edits. The upgrade validator compares the manifest to the constant, not recorded versions, so it is unaffected. | `indexer.py`; `test_int8_encoding_revision_scopes_reembed_to_int8_layers` asserts both directions. |
| 2026-08-11 | **Peak resident memory (AC-8).** CPU-bound INT8 query path drops to 245 MiB peak against a 1353 MiB batch-32 pinned baseline measured before the change. Throughput on 64 realistic 512-token chunks: 31.8 ms/chunk versus the 33.7 ms/chunk batched baseline, so determinism cost nothing. | Session probe transcripts, same host and method for both measurements. |
| 2026-08-12 | **ADR recorded.** `1v22e-adr int8-encoding-is-batch-composition-sensitive` documents the mechanism, the decision, and four constraints it imposes, and cross-references ADR `1p92d`, whose recall-parity result stands but which did not consider activation-scale scope. Added to the decisions README index. The ADR also records the open reranker exposure so it is not lost when this wave closes, and states plainly that the retrieval-quality effect was never measured. | `docs/architecture/decisions/1v22e-adr int8-encoding-is-batch-composition-sensitive.md`; docs-lint ok. |
| 2026-08-12 | **AC-6 satisfied end to end.** New operator-run validation builds a real int8-class index, seeds the pre-change identity through the canonical `write_build_bookkeeping` producer, and builds twice: 5 chunks re-embedded on the first pass, **0 on the next with no content change**, settling on `Snowflake/snowflake-arctic-embed-s@int8@wf-model-set-2-20260811-arctic-s-int8enc2`. The second half is the load-bearing one, because a compare/write disagreement would re-embed the corpus on every incremental build forever. The int8 class comes from forcing provider selection, NOT from patching `_predicted_precision_class`, since patching the predicate under test would make the run vacuous; a precondition check aborts with exit 2 rather than reporting green if the machine fails to classify as int8. | `.wavefoundry/framework/scripts/tests/acceptance_ac6_int8_reembed.py`, exit 0. |
| 2026-08-12 | **Why AC-6's validation is deliberately outside the standard suite.** Operator direction: this must not run on every suite pass. It is excluded by FILENAME rather than by `skipUnless`, because `run_tests.py` discovers `test_*.py` only, so the file is never collected and the suite count and runtime are unchanged. A skipped test inside the suite would be indistinguishable from an UNINTENDED skip, which is exactly what the evidence contract's `test_ran_without_unintended_skip` field exists to catch. `scripts/tests` is already excluded from the shipped pack, so it does not reach target repositories. Run it deliberately when touching the int8 identity or the re-embed trigger. | `run_tests.py` `_TESTS_DIR.glob("test_*.py")`; `build_pack.py` `EXCLUDED_REL_PATHS`. |
| 2026-08-12 | **Gapfill: implement-stage retrieval bypassed the MCP tools, and it cost something.** Instrumented retrieval calls during implementation were zero against six changed non-docs files. Early investigation did use `code_search`, `code_references` and `code_constants`, but the implementation and census work ran through shell `grep`/`sed` out of habit. This is not being recorded as justified fallback: it is the deviation the posture directive exists to prevent, and it had a concrete consequence here. The census that missed `upgrade_wavefoundry._semantic_epoch_matches_active_models` was a shell grep over the constant identifier and the literal `"int8"`; the site compares against a local variable unpacked from the authority tuple, so it matched neither pattern. `code_references` on the symbol, or `code_keyword` with multiple queries, would have been the better instrument. The miss was caught later only because an unrelated question about model repackaging led back into that file. | This entry; `wf_review_wave(phase='implementation')` `retrieval_posture_gap` advisory. |
| 2026-08-12 | **DECLARED SCOPE WIDENED, and why.** A question about whether the model asset needed repackaging (it does not; `model_int8.onnx` is already shipped and no packaging file changed) surfaced a defect this change had introduced. `upgrade_wavefoundry._semantic_epoch_matches_active_models` validates the RECORDED fingerprint against the manifest constant, so the class-scoped int8 identity would have failed it on every CPU-bound host. That predicate gates `_run_retired_model_cleanup`, so a CPU-bound host would have silently retained the retired BAAI components forever, defeating wave 1v0r0's supplier-lineage cleanup. Fail-safe in direction (nothing wrongly deleted) but contrary to intent. The original census missed it because that site uses a local `fingerprint` variable rather than the constant name that was grepped. Fixed by deriving the expectation per class from the AUTHORITY fingerprint, taking only the revision token from `indexer` so there is one source of truth, with a fallback preserving old behaviour for a framework predating the constant. `Serialization Points` now declares the two upgrade files; this supersedes the review-policy receipt and lapses the readiness approvals by design, and they must be re-recorded. | `upgrade_wavefoundry.py`; `test_stable_epoch_requires_both_layers_and_canonical_composites` extended. |
| 2026-08-12 | **Existing test updated, disclosed.** That test pinned the pre-change contract (`@int8@fp-v2` against authority `fp-v2`). The contract genuinely moved, so the int8 rows now carry the revision. To avoid merely relaxing an assertion to fit the change, a NEGATIVE case was added: an int8 layer still carrying the pre-revision bare fingerprint must be REJECTED, which is the guard that forces the one-time re-embed before retired-model cleanup may proceed. | `tests/test_upgrade_wavefoundry.py`; suite 7184 OK. |
| 2026-08-11 | **Suite green: 7184 tests across 62 files, OK** (7181 before, plus the three new tests). Four existing `test_indexer` sites that built `model_versions` with the bare fingerprint while deriving the class dynamically were updated to route through `_identity_fingerprint_for_class`; left alone, they would have looked stale on a CPU-bound machine and forced re-embeds unrelated to their assertions. Two other sites were correct as written (one pins `@full@` explicitly, one is a pure parser test). | `run_tests.py`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-11 | Encode one real row per inference call on the INT8 path. | Removes the dependence at its source with no measured throughput cost (0.96x), requires no new redistributable artifact, and cuts the CPU-bound query path's peak RSS roughly eightfold. | **Calibrated static quantization export** (rejected for now): fixes the cause most directly and keeps batching, but requires producing, validating and redistributing a new INT8 artifact plus a calibration set, bumping the model set, and expanding the supply-chain surface the current wave just narrowed. **Drop INT8 and run FP on CPU** (rejected): removes the entire defect class and would simplify the model set, but roughly doubles CPU embedding cost, discards the INT8 recall parity ADR `1p92d` established, and still forces a re-embed. **Pad every batch to include an empty row** (rejected, falsified): tested directly on the hypothesis that pad tokens clamp the activation range; a batch of 1 real + 30 real + 1 empty still drifted to cos 0.99630791, so it does not stabilise the scale. |
| 2026-08-11 | Gate adoption on a gold-set retrieval evaluation rather than on cosine similarity. | Cosine drift of 0.004 to 0.005 does not establish whether ranked results change. ADR `1p92d` set the precedent by clearing INT8 on gold-labelled recall, not on similarity. | Adopt on the cosine evidence alone (rejected: measures the wrong thing). Document and accept without changing behaviour (rejected unless the eval shows no impact, in which case reproducibility alone still argues for the fix). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Single-row throughput was measured on a GPU-capable host driving the CPU execution provider, which may not represent a genuinely CPU-bound machine. | AC-9 requires confirmation on real CPU-bound hardware before adoption. |
| The change alters stored vectors, so every CPU-bound repository re-embeds once on upgrade. | AC-6 pins exactly-once behaviour; disclose the re-embed in the changelog as an operator-visible upgrade cost, following the model-set v2 precedent. |
| The reranker uses the same dynamic-quantization mechanism and may carry the same defect, but is out of scope here. | Investigate under its own change; note in the ADR so the exposure is recorded rather than forgotten. |
| Retiring the pinned 32x512 INT8 graph could disturb the GPU path if the two share resolution code. | AC-5 pins GPU batching with a test that fails on change; keep the FP16 pin untouched. |
| The eval may show the current mismatch is harmless, making the correctness argument the only justification. | Acceptable: reproducible re-indexing and exact query/index agreement stand on their own, and the fix costs no throughput. Record the outcome either way. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
