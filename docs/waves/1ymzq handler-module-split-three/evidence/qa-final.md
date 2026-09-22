# QA/release final delivery follow-up — 1ymzq

Owner: Engineering
Status: active
Last verified: 2026-09-22

Verdict: **APPROVE QA final delivery. APPROVE release final delivery within this wave's code-distribution scope. Index AC-5 is verified and reconciled.** No remaining blocker in these lanes. This does not certify a newly published zip or authorize closure/commit.

This focused follow-up supersedes only the R2 withholding in `/private/tmp/1ymzq-qa-delivery.md`; its independent implementation review, mutation results, platform limitations, and current 9,508-test receipt remain applicable. Reviewer `/root/split3_qa_delivery` did not implement or repair this wave. QA, release, and rotating docs-contract are correlated perspectives of this one worker, not three independent reviewers.

## Independently verified R2

- Raw receipt: `docs/reports/retrieval-quality-1ymzq-after.json`, file SHA256 `68cceba17dd3eea64a46813685588f5b7140a5e614c1f71b645cc6a8cac1768b`.
- Verdict `baseline`; run `f9e00315a3cbb68ff01ce6bb06bc1af300e249d2dbc01b0c5be3932ec3e8a45e`; UTC 2026-09-22T14:50:27Z–14:56:12Z, 345.422s.
- Start/end token exactly equal: attempt `3adce80c426f406bbb846336967687c3`, `complete`, generation1914. Invalidation and operator-review reasons empty; no comparison object.
- Evaluator source SHA256 independently computed from disk equals `25bb941502b84a29c9e8899640dfa2e31e1776218e2554ac881491c1f8d16832`.
- Recomputed production identity and every module hash equal receipt: digest `cb382d900be670500cfa824c78b6505f7c50fccb68c1f5c966b86626f2ee18d6`; index_handlers.py explicitly present. Receipt records end_digest_verified true. Current recomputation confirms reviewed bytes still match, rather than relying solely on that declaration.
- Fixture corpus loaded through canonical validation; independently recomputed canonical fixture digest equals `e5567e76515684fd7908b737923c83d62091ee3ecaf5253ae3fe17e8674275de`.
- All35 fixture IDs occur in140 tool cases;55 applicable fixture/tool cases each contain3 repetitions. Inapplicable rows remain explicitly classified, not silent skips. Corpus nonempty and ready, vector/FTS counts code13672/docs31282. Disposable degraded-mode probe passed for all three recorded tools.
- All22 raw-report symbol declaration spans independently match current AST declarations, including `_reap_dashboard_child_pids` in index_handlers.py. Existing golden symbol/content anchor test additionally passed its stale-path negative controls.

R2 deliberately has different evaluator and fixture identities from R0/R1. It is a new baseline, **not** a no-regression comparison across the final index extraction. Earlier independently verified R1/R0 comparison remains the evidence for the preceding adoption window.

## Pointers, AC5, and executed checks

Read final Standing artifact prose in `docs/contributing/review-and-evals.md`, standing-baseline table/command in `docs/architecture/testing-architecture.md`, exact literal pins in `test_docs_lint.EvaluatorEditBaselinePolicyPinTests`, wave retrieval-evidence.md and retention record. The three baseline references resolve to the now-existing R2; narrative identifies generation1914 and the identity-boundary limitation. Index AC5's checked state now has concrete receipt/membership/identity/pointer evidence. Historical handoff paragraphs recording when R2 was pending are historical sequence, not evidence used for approval.

Five focused tests passed, zero skips: three EvaluatorEditBaselinePolicyPinTests, golden symbol/content anchors with stale-path controls, and independent index-handler production identity test. No implementation suite repetition was necessary because framework bytes are unchanged. Initial review already demonstrated known-bad identity membership, manifest omission, reload eviction, containment filesystem-operation and fallback faults.

Framework hash independently recomputed: `23beca55d485bce9f4ed5e7097dac6df7e9bbbc6b374f8e6334c8380daae317e`; canonical cache hit true, result ok/test_count9508. v2 packet comparison shows only the announced finalized contributing prose drift; no code/test/fixture or other packet path changed. New R2/evidence documents were directly reviewed as this follow-up's added scope. No repository edits performed.

## Rotating docs-contract perspective

Following the fixed-seat findings, the strongest alternative remains retaining local containment comparisons and composition-root handlers to avoid migration/reload risk. The delivered design is justified by verified exception preservation, unchanged resolution counts, complete ownership identities and actual registered reload mutation checks; local copies offer little further protection after those checks. Documentation accurately distinguishes ownership changes from behavior changes and R1 comparison evidence from new-baseline R2. Approve clarified readiness receipt `review-policy-94b63f24a5c63152fa15` and final docs-contract judgment within this correlated perspective.

## Exact integrity declarations

fresh_context=true (initial independent delivery context); independent=true (no implementation/repair participation); followup_same_reviewer_context=true; same_worker_qa_release_docs=true; checks_executed=true; zero_unintended_skips=true; production_path_reached=true (initial registered reload/extension/CE/wrapper proofs); fixture_state_reachable=true; assertions_nonvacuous=true; known_bad_detected=true (initial mutations and replayed stale-anchor controls); evaluator_identity_verified=true; production_identity_verified=true; fixture_identity_verified=true; report_anchor_spans_verified=true; framework_receipt_current=true; reviewed_code_unchanged=true; R0_R1_verified=true; R2_verified=true; index_AC5_verified=true; final_qa_approval=true; final_release_approval=true.

Limits: no new benchmark rerun, cryptographic attestation of evaluator execution, native-Windows qualification, or published-package certification. Approval relies on independently validated persisted report content/current hashes plus the earlier executable implementation and mutation evidence, not the coordinator's summary alone. New baseline does not claim comparative retrieval quality across the changed identity boundary.
