# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-08-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1v0r0 supplier-lineage-compliant-retrieval`
Title: Supplier Lineage Compliant Retrieval

## Objective

Replace the non-compliant BAAI code embedder with Snowflake Arctic S, retain
Arctic XS for documents and MiniLM L6 for reranking, and ship the changed
offline model set as v2 with Wavefoundry `1.16.0`.

## Changes

Change ID: `1v0qz-enh supplier-lineage-compliant-retrieval-models`
Change Status: `planned`

## Participants

- Coordinator: implementation-coordinator
- Write-owning roles: implementer
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, security-reviewer

## Wave Summary

Replace the non-compliant BAAI code embedding default with Snowflake Arctic S,
retain Arctic XS for documents and L6 for reranking, and standardize embedding
execution at FP16 GPU / INT8 CPU with forward batch 32. Update the pinned model
artifacts, safe code re-index, focused verification, and packaged offline model
set from v1 to v2 for the next release.

## Watchpoints

- Activation watchpoint: another session currently owns the single OPEN wave
  slot. Readiness may proceed in parallel and leaves this wave planned; only
  implementation activation must wait until the OPEN slot is released.
- The reranker remains MiniLM L6 at its independent batch 40. L2 is not an
  implementation option in this wave.
- Accurate historical records and unrelated or operator-managed caches are
  preserved, but no active/default/bundled/setup path may select or require
  BAAI. Starting with `1.16.0`, upgrade removes only exact retired BAAI-derived
  artifacts owned by Wavefoundry, and only after verified v2 model and complete
  semantic publication.
- Supplier origin is reviewed manually whenever a model is swapped; no runtime
  jurisdiction validator is part of this wave.
- The next release must publish and select `wavefoundry-models-2.zip`; model set
  v1 remains an immutable historical bundle identity.
- Release version: `1.16.0`, including its exact VERSION stamp and changelog
  heading.

## Review Checkpoints

- **Product-owner acknowledgment — 2026-08-10: ACKNOWLEDGED.** The operator
  approved Arctic XS for documents, Arctic S for code, embedding FP16 GPU /
  INT8 CPU at batch 32, and retained L6 reranking at FP16 GPU / INT8 CPU with
  independent batch 40. The operator also approved model set v2 shipping with
  Wavefoundry `1.16.0`, followed by bounded removal of retired BAAI-derived
  Wavefoundry cache artifacts after successful v2 convergence.
- **Initial red-team primer — 2026-08-10: SUPERSEDED.** Context
  `1v0r0-redteam-20260810-supplier-lineage-01` found an L6 logical-ID/artifact
  conflation, an uncovered background cold-cache acquisition path,
  under-specified lineage validation, and a discretionary retrieval fixture.
  Its expanded-policy repair was later superseded when the operator narrowed
  the wave to the direct model swap, manual supplier review, and bundle v2.
- **Initial docs-contract recheck — 2026-08-10: SUPERSEDED.** Context
  `1v0r0-docs-contract-20260810-final-03` approved the repaired expanded draft;
  a new council review is required for the operator-narrowed plan.
- **Narrowed red-team primer — 2026-08-11: CHANGES REQUESTED, REPAIRED.**
  Context `1v0r0-redteam-20260811-modelswap-02` found that a v2 shared
  fingerprint cannot promise a code-only rebuild and that manual supplier fields
  cannot be appended only to the canonical generated manifest. The plan now
  requires one atomic full semantic rebuild and keeps the manual supplier
  decision in the separate model-selection record. Hardware timing is controlled
  release evidence rather than a portable CI assertion.
- **Architecture rotating seat — 2026-08-11: PASS.** Fresh context
  `1v0r0-architecture-20260811-modelswap-03` verified v1 immutability, complete
  v2 package/setup/upgrade selection, the shared-fingerprint full rebuild,
  generated-manifest equality, unreachable-only legacy BAAI aliases, and the
  controlled timing classification against current source.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-11: PASS**
  (moderator: wave-council; primer-depth: standard; seats: red-team,
  security-reviewer; rotating-seat: security-reviewer;
  strongest-challenge: migrate the shared model-set identity to v2 without
  mixed layers, breaking generated-manifest equality, or trusting a
  self-consistent substitute bundle; strongest-alternative: per-layer
  fingerprints could avoid rebuilding docs but are rejected as a broader
  architecture change than this model swap requires.)
- **QA readiness lane — 2026-08-11: CHANGES REQUESTED, REPAIRED.** Fresh context
  `1v0r0-qa-20260811-modelswap-final-05` found that AC-9 could either overwrite
  the existing 32-query mixed benchmark or create an unnamed fixture. The plan
  now names a separate 28-query input, evaluator, committed result, controlled
  release command, and inference-free CI validator while preserving the
  existing fixture byte-identically. Final QA recheck remains required.
- **QA readiness recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-qa-20260811-modelswap-recheck-06` verified AC-1 through AC-10,
  backward-compatible benchmark/test reuse, deterministic result validation,
  and existing 32-query fixture preservation against current test owners.
- **Code readiness lane — 2026-08-11: CHANGES REQUESTED, REPAIRED.** Fresh
  context `1v0r0-code-recheck-20260811-modelswap-final-06` found the reranker
  success log uses embedding `STATIC_BATCH`; the plan now corrects it to
  `RERANK_STATIC_BATCH`, adds `server_impl.py`, and extends the existing success
  test to assert batch 40.
- **Security readiness lane — 2026-08-11: CHANGES REQUESTED, REPAIRED.** Fresh
  context `1v0r0-security-20260811-modelswap-final-06` found offline
  materialization trusts a self-consistent incoming manifest without comparing
  it to the installed canonical authority. The plan now requires canonical
  equality and a self-consistent substitution mutant before cache publication.
- **Code readiness recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-code-readiness-recheck-20260811-modelswap-07` verified the reranker-log
  repair, model-swap seams, shared-fingerprint rebuild, v2 packaging, and
  backward-compatible benchmark/test reuse against current source.
- **QA readiness final recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-qa-20260811-modelswap-last-07` verified all ACs remain testable using
  existing owners, and executed non-vacuous known-bad probes for the batch-log
  and self-consistent bundle-substitution cases.
- **Security readiness final recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-security-recheck-20260811-modelswap-final-07` executed the current
  self-consistent remanifest substitution, confirmed it is accepted today, and
  approved the bounded canonical-manifest binding and mutation test. No runtime
  jurisdiction validation is introduced.
- **Release readiness lane — 2026-08-11: CHANGES REQUESTED, REPAIRED.** Fresh
  context `CTX-1v0r0-release-final-20260811-A7C4` found that release and
  release-dry-run could still omit the companion model archive and that the
  exact framework version was unresolved. The plan now requires
  `--with-models` for both release modes, asserts the matching
  `wavefoundry-models-2.zip` receipt, and locks the release to `1.16.0`.
- **Release readiness final recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-release-readiness-recheck-20260811-1160-v2-08` verified exact
  `1.16.0` VERSION, changelog, feature-archive, and model-set-v2 agreement;
  traced existing setup/upgrade selection and shared-fingerprint behavior; and
  executed the current feature-only release-dry-run as a non-vacuous known-bad
  control for the new mandatory companion guard.
- **Post-readiness scope revision — 2026-08-11: RE-REVIEW REQUIRED.** The
  operator replaced the prior cache-preservation decision with bounded cleanup
  of retired BAAI-derived Wavefoundry cache artifacts on upgrades to `1.16.0`
  or later. The revision is destructive but narrowly contained: it runs only
  after verified v2 model and complete semantic publication, uses exact paths
  and ownership markers, preserves unrelated/shared caches and historical
  records, and makes failure explicit. The prior readiness receipt and affected
  approvals are superseded pending fresh review.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | pending | no current executed approval | record approval evidence for architecture-reviewer |
| release-reviewer | pending | no current executed approval | record approval evidence for release-reviewer |
| security-reviewer | pending | no current executed approval | record approval evidence for security-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Activation depends only on release of the repository's single OPEN wave slot;
  there is no content dependency on the currently implementing wave.
- The broader retrieval-intent golden-query framework remains owned by planned
  change `1seaw`; this wave commits only the focused migration gate it needs.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 80 | 1,343,585 |
| review | 5 | 0 |
| **Total** | **85** | **1,343,585** |

<!-- wave:context-efficiency-state {"generation":45,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":80,"content_source_credit":1605678,"derived_artifact_credit":1172,"direct_net":1343585,"estimated_tokens_saved":1343585,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5271,"response_debit":261500,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":5,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-3676,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":23,"response_debit":3653,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":85,"content_source_credit":1605678,"derived_artifact_credit":1172,"direct_net":1339909,"estimated_tokens_saved":1343585,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5294,"response_debit":265153,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"wave_id":"1v0r0 supplier-lineage-compliant-retrieval"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
