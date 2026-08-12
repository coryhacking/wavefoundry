# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1v454 int8-embedding-determinism`
Title: Int8 Embedding Determinism

## Objective

Make INT8 embedding vectors a function of their own text rather than of whichever chunks shared their inference batch, so that re-indexing a corpus is reproducible and a query matches the index it searches. Measured today on a CPU-bound host: the query encoding regime differs from the bulk-index regime at cos 0.996160, and chunk neighbours move a vector by up to 0.005.

## Changes

Change ID: `1v453-bug int8-vectors-depend-on-batch-composition`
Change Status: `implementing`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (encoding paths, re-embed trigger), qa (eval, GPU-path pin)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-08-12

## Wave Summary

Wave `1v454 int8-embedding-determinism` (Int8 Embedding Determinism) delivered one change: INT8 Embedding Vectors Depend On Batch Composition. Notable adjustments during implementation: INT8 Embedding Vectors Depend On Batch Composition: **Reproduction first.** Added `test_int8_cpu_embed_submits_one_real_row_per_call` and `test_gpu_path_still_batches_to_static_batch` before any behaviour change. The INT8 test failed non-vacuously against the shipped code (`[32] != [1, 1, 1, 1, 1]`) and the GPU test passed, so the oracle distinguishes the two paths.; INT8 Embedding Vectors Depend On Batch Composition: **Re-embed trigger scoped to int8 (AC-6, AC-10).** Added `INT8_ENCODING_REVISION` and `_identity_fingerprint_for_class`, routed both compare sites (`build_index` docs/code `model_changed`) and the scoped-update guard and both write sites through it. A `full` layer keeps the unsuffixed fingerprint so GPU hosts do not re-embed; an `int8` layer carries the revision so it re-embeds exactly once. Deliberately NOT a bump of the all-layer `EMBEDDING_MODEL_SET_FINGERPRINT`, per the council finding. Census of literal `"int8"` comparisons ran first (`indexer._predicted_precision_class`, `server_impl._get_embedder`, `upgrade_wavefoundry`'s class allowlist); the class token is unchanged, so none of them needed edits. The upgrade validator compares the manifest to the constant, not recorded versions, so it is unaffected.; INT8 Embedding Vectors Depend On Batch Composition: **ADR recorded.** `1v22e-adr int8-encoding-is-batch-composition-sensitive` documents the mechanism, the decision, and four constraints it imposes, and cross-references ADR `1p92d`, whose recall-parity result stands but which did not consider activation-scale scope. Added to the decisions README index. The ADR also records the open reranker exposure so it is not lost when this wave closes, and states plainly that the retrieval-quality effect was never measured.

**Changes delivered:**

- **INT8 Embedding Vectors Depend On Batch Composition** (`1v453-bug int8-vectors-depend-on-batch-composition`) — 9 ACs completed. Key decisions: Encode one real row per inference call on the INT8 path.; Gate adoption on a gold-set retrieval evaluation rather than on cosine similarity.
## Watchpoints

- The `int8` blast radius is CPU-bound hosts only. FP16 and fastembed were both measured clean under the identical composition test, so the GPU path must be left alone and proven untouched (AC-5, AC-10).
- `EMBEDDING_MODEL_SET_FINGERPRINT` is an all-layer boundary and is the WRONG re-embed lever here; bumping it would re-embed every GPU host for a defect they do not have. Use the recorded precision-class token instead.
- **Follow-up (deferred, do not expand this wave):** the reranker (`StaticShapeReranker`) uses the same dynamic-quantization mechanism and may carry the same exposure. Defer to its own change; this wave must not grow to cover it.
- **Watchpoint:** adoption blocks on the gold-set recall comparison. If the eval regresses, the encoding change does not land and the wave should retry against the calibrated-export alternative recorded in the Decision Log.
- Adoption is gated on the gold-set recall comparison, not on cosine. Cosine established the mechanism; it cannot establish retrieval impact.
- Throughput parity (0.96x) was measured on a GPU-capable host driving the CPU execution provider. AC-9 requires confirmation on genuinely CPU-bound hardware.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-11: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: Requirement 6 as drafted routed the one-time re-embed through `EMBEDDING_MODEL_SET_FINGERPRINT`, which `indexer.py` documents as an all-layer compatibility boundary, so the obvious implementation would have re-embedded both layers on every GPU host for a defect confined to `int8`-class indexes; the plan was amended to require an `int8`-scoped trigger on the recorded precision-class token and AC-10 was added to prove a `full`-class index is untouched; strongest-alternative: a calibrated static-quantization INT8 export, which removes the runtime scale dependence at its source and preserves batching, rejected because it requires producing, validating and redistributing a new model artifact plus a calibration set and bumping the model set immediately after wave 1v0r0 narrowed that surface, and it is recorded in the Decision Log for revisit if the gold-set eval shows single-row encoding insufficient)

- **Prepare-phase Wave Council [prepare-council] — 2026-08-12: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the implementation introduced a defect the first council could not have seen, because it did not exist at plan time: the class-scoped int8 identity fails `upgrade_wavefoundry._semantic_epoch_matches_active_models`, which compares the RECORDED fingerprint to the manifest constant and gates `_run_retired_model_cleanup`, so every CPU-bound host would have silently retained the retired BAAI components and defeated wave 1v0r0's supplier-lineage cleanup; the original census missed it because that site compares against a local variable rather than the constant identifier that was grepped, the declared scope has been widened to cover the upgrade runner and its test, and the widening recruited `release-reviewer`, which had never run; strongest-alternative: encode the revision in the precision-class token instead of the fingerprint, rejected because the token is compared against literal `"int8"` at three sites including an upgrade validity allowlist, giving a materially larger blast radius than the fingerprint slot)

- **Prepare-phase Wave Council [prepare-council] — 2026-08-12: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the AC table now reads nine met and one deferred, which is exactly the shape that invites a reader to conclude the change was fully validated, so the council's job this round was to check that the two dispositions moved on evidence rather than on convenience; AC-6 was upgraded from an identity-level assertion to an executed end-to-end validation that re-embeds 5 chunks once and 0 on the next build, and whose precondition aborts with exit 2 rather than passing vacuously on a GPU host, while AC-7 and AC-9 each carry an inline note stating plainly what was NOT done, so neither reads as a satisfied criterion it is not; strongest-alternative: hold the wave open until a gold-labelled eval set is built and AC-7 can be satisfied literally, declined by operator direction on the strength of the accumulated executed evidence, with the unmeasured retrieval question recorded in both the AC note and the ADR rather than closed over)

Seat evidence (round 3, 2026-08-12):

- **red-team** — attacked the completeness of the green column rather than the code, since the code was unchanged this round. Confirmed AC-9's `[x]` is accompanied by a note admitting the measurement came from precisely the host class its own text excludes, so the record does not overstate itself. Confirmed the AC-6 validation cannot pass on a machine that fails to classify as int8. Confirmed no AC or task is left silently blank: all ten ACs and all tasks are `[x]` or `[~]`, with every `[~]` carrying a rationale.
- **security-reviewer** — no code, packaging, manifest or upgrade surface changed in this round; the additions are an ADR and its index row. Verified the ADR does not leak absolute filesystem paths and records the open `StaticShapeReranker` exposure rather than dropping it at close. No finding.

Seat evidence (round 2, 2026-08-12):

- **red-team** — the interesting failure was that a passing suite and a clean census both said the change was complete while a silent cleanup regression sat one file outside the declared boundary. Verified the repair is not merely additive: the epoch predicate now derives its expectation per class from the AUTHORITY fingerprint rather than the module constant, so it stays correct for any authority the caller established, and a pre-revision int8 identity is rejected. Confirmed the rejection is the desired behaviour and not a new bug: retired components must not be deleted on the strength of an epoch built with the superseded encoding.
- **security-reviewer** — reassessed with the upgrade runner in scope. The change deletes nothing new and gates deletion more strictly than before, so the movement is toward caution on a destructive path. No new supply-chain surface, no manifest change, no download. Confirmed the model asset needs no re-cut: `model_int8.onnx` is already a shipped component and no packaging file is in the diff. No finding.

Seat evidence (round 1, 2026-08-11):

- **red-team** — verified code-grounded, not against plan prose. All five declared review targets resolve on disk. The re-embed mechanism cited by Requirement 6 exists (`_model_set_fingerprint_from_version` compared against `EMBEDDING_MODEL_SET_FINGERPRINT` in the scoped-update guard), which is how the all-layer scope defect was found. Confirmed the rejected padding alternative was actually falsified by measurement rather than argued away (1 real + 30 real + 1 empty still drifts to cos 0.99630791), so the Decision Log records a tested rejection.
- **security-reviewer** — no new supply-chain surface: the change introduces no download, no new model artifact, and no change to `model-set-verification-manifest.json`. Retiring the pinned `cpu_int8_static_32x512.onnx` in favour of the shipped `model_int8.onnx` mildly *improves* integrity posture, because the shipped artifact is hash-verified against the canonical manifest while the pinned graph is a locally generated derivative that is not. No finding.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 40 | 214,485 |
| implement | 22 | 15,548 |
| review | 22 | 82,669 |
| **Total** | **84** | **312,702** |

<!-- wave:context-efficiency-state {"generation":69,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":22,"content_source_credit":28310,"derived_artifact_credit":1036,"direct_net":15548,"estimated_tokens_saved":15548,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2974,"response_debit":11528,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":704},"plan":{"calls":40,"content_source_credit":269838,"derived_artifact_credit":1675,"direct_net":214485,"estimated_tokens_saved":214485,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3434,"response_debit":57100,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":22,"content_source_credit":112039,"derived_artifact_credit":2066,"direct_net":82669,"estimated_tokens_saved":82669,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5084,"response_debit":27698,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":84,"content_source_credit":410187,"derived_artifact_credit":4777,"direct_net":312702,"estimated_tokens_saved":312702,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11492,"response_debit":96326,"source_credit_count":50,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5556},"wave_id":"1v454 int8-embedding-determinism"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
