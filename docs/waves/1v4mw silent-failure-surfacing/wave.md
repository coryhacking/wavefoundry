# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1v4mw silent-failure-surfacing`
Title: Silent Failure Surfacing

## Objective

Make two silent failures visible. A malformed `wave:executable-review-evidence` marker currently passes a green docs gate while rendered review-protocol content silently stops updating, and the CoreML probe captures its own failure cause then discards it. Both were found downstream only by reverse engineering.

## Changes

Change ID: `1v4mt-bug rendered-review-protocol-loss-is-ungated`
Change Status: `implemented`

Change ID: `1v4mu-bug coreml-probe-discards-failure-cause`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (validator, renderer, probe logging), qa (fixtures for half-paired markers and failing-probe stderr)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-08-12

## Wave Summary

Wave `1v4mw` (Silent Failure Surfacing) delivered two changes: Rendered Review-Protocol Loss Is Ungated and CoreML Probe Discards Its Own Failure Cause. Notable adjustments during implementation: Rendered Review-Protocol Loss Is Ungated: Reproduced first. A half-paired region (end present, begin removed: the exact field shape) passed before and fails after. Disposition factored into `_check_marker_family_parity`; both families now call it, and the review-policy family's four pinned dispositions still pass unchanged. Registered on the full and incremental docs-lint paths.; Rendered Review-Protocol Loss Is Ungated: **Regression caught by the suite and repaired.** The first implementation of the summary scan imported `wave_lint_lib.core_validators` from `upgrade_wavefoundry.py` to share the gate's logic. That broke the upgrade feature-pack protocol: `upgrade_protocol._validate_imports` walks the WHOLE tree (function-scoped imports included) and admits only top-level pack modules, and `wave_lint_lib` is a package, so the bridge bundle could no longer validate. Four tests failed in `test_upgrade_protocol.py`. Repaired by deriving the finding from `render_agent_surfaces.review_protocol_carriers_skipped_by_render`, an admitted module, rather than by disguising the import behind `importlib` — the guard exists so the bridge bundle runs standalone, and routing around it would have traded a visible failure for exactly the class of silent breakage this wave is about. Both paths still bottom out in one disposition: `_upsert_review_protocol_region` returning `None`.; Rendered Review-Protocol Loss Is Ungated: Delivery review found three defects in this change, all repaired in session. (1) The refactor replaced `REVIEW_POLICY_SURFACE_BLOCKS.get(...)` with a membership test plus indexing, which silently changed the pre-existing disposition for a registry row whose block VALUE is `None`: the old code skipped it, the new code would have handed `None` to the upsert helper. Restored via a walrus on `.get(...) is not None`. (2) The changelog described the new gate as firing only on broken markers, understating it: adopting the shared rule also brings the drift half, so a hand-edited region now fails too. Corrected, including why that case is largely self-correcting during an upgrade. (3) The Decision Log claimed the warning is emitted on a failed phase and outside the major/minor gate, and no test asserted it. Added, with a polarity assertion that the reconciliation prose IS still suppressed on that path, so the test cannot pass merely because everything prints.

**Changes delivered:**

- **Rendered Review-Protocol Loss Is Ungated** (`1v4mt-bug rendered-review-protocol-loss-is-ungated`) — 5 ACs completed. Key decisions: Extend the existing disposition to the second family rather than write a new validator for it.; Derive `renderer_warnings` by re-scanning the tree at summary time rather than capturing the renderer subprocess's stderr.
- **CoreML Probe Discards Its Own Failure Cause** (`1v4mu-bug coreml-probe-discards-failure-cause`) — 5 ACs completed. Key decisions: Ship the diagnostics, not a root-cause fix.
## Watchpoints

- **Watchpoint:** `1v4mt` makes a previously-silent condition BLOCKING. A repository whose markers are already broken will fail its next docs gate rather than pass quietly. That is intended and belongs in the changelog as an operator-visible change.
- **Watchpoint:** neither change alters a decision. `1v4mt` does not auto-repair markers and `1v4mu` does not change what the probe decides. If either starts rewriting content or changing degradation behaviour, scope has slipped.
- The two changes are independent and share no file; they can be implemented in either order.
- **Trust note:** until `1v4mt` lands, a passing docs gate does NOT prove rendered review-protocol content is intact. Do not cite a green gate as evidence for that property in this wave's own review.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-12: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: this wave asks to make a currently-silent condition BLOCKING, so the question is whether a repository with already-broken markers gets a useful failure or a wall; the plan answers it with AC-2 requiring the message to name the file and the marker condition and AC-3 requiring healthy content to still pass, and the change is bounded by an explicit no-auto-repair scope line so the gate reports rather than rewrites operator content; strongest-alternative: a dedicated validator for the second marker family, rejected because a parallel implementation of one rule is precisely how these two families drifted apart, which AC-5 now forbids)

Seat evidence:

- **red-team** — verified code-grounded, both claims independently. `core_validators.py` matches only `review-policy` carriers and no validator under `wave_lint_lib/` references `executable-review-evidence`, so the second family is genuinely ungated rather than gated elsewhere. `accel_embedder` sets `capture_output=True` and then branches solely on `completed.returncode`, confirming the failure cause is captured and discarded. One correction that STRENGTHENS the plan: the upgrade summary already returns three categorized lists including `renderer_provenance_flags`, so AC-4's `renderer_warnings` follows an established pattern rather than inventing a field shape. Verified the two changes share no file, so the wave carries no internal ordering constraint.
- **docs-contract-reviewer** — no blocking finding. One delivery-time obligation recorded rather than raised: the plan's own Affected Architecture Docs section notes that any documentation claiming a passing docs gate guarantees rendered-content integrity is currently too strong. That claim must be located and corrected as part of delivery, not deferred, because shipping the gate while leaving an overstated guarantee in the spec would leave the docs wrong in the opposite direction.

- **Prepare-phase Wave Council [prepare-council] — 2026-08-12: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the readiness receipt superseded after implementation because the change docs gained delivery records, so this re-affirmation asks whether the SCOPE still matches what shipped rather than re-litigating the plan; it does, with one boundary worth naming explicitly: adopting the shared review-policy disposition brings its drift half as well as its malformed half, which is faithful to Requirement 1's "the same disposition" wording but is a wider trigger surface than the Rationale's malformed-marker narrative alone implies; strongest-alternative: gate only the malformed half for the protocol family, rejected because a per-family subset of one rule is the same divergence AC-5 exists to prevent)

Seat evidence (re-affirmation cycle):

- **red-team** — verified code-grounded against the delivered tree, not the plan's prose. `_check_marker_family_parity` exists at `core_validators.py` and is the sole implementation both families call; `check_review_protocol_carrier_parity` is registered on both `cli._run_full_checks` and `cli._run_incremental_checks`; `review_protocol_carriers_skipped_by_render` exists in `render_agent_surfaces` and is the only path `upgrade_wavefoundry` uses, so the feature-pack import boundary holds. One instrument disagreement worth recording rather than hiding: `code_keyword` did NOT return the three new source symbols while returning new test-file lines from the same session, so absence from a single instrument was not treated as evidence; a direct cross-check resolved it as index freshness. No finding blocks readiness.
- **docs-contract-reviewer** — the delivery-time obligation from the first cycle is DISCHARGED, audited rather than assumed: no documentation overstates what a passing docs gate guarantees. `docs/specs/mcp-tool-surface.md` describes `wf_validate_docs` as returning structured pass/fail diagnostics and claims nothing about rendered-content integrity, and `docs/RELIABILITY.md` names it only as a recovery step. The remaining hits are wave records and plans, which are historical and correct for their time. Separately confirmed the changelog now states the drift half of the new trigger surface, which it did not before delivery review.

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
| plan | 12 | 2,312 |
| implement | 53 | 2,085,986 |
| review | 14 | 216,989 |
| **Total** | **79** | **2,305,287** |

<!-- wave:context-efficiency-state {"generation":79,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":53,"content_source_credit":2110197,"derived_artifact_credit":267,"direct_net":2085986,"estimated_tokens_saved":2085986,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3029,"response_debit":23842,"source_credit_count":49,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2393},"plan":{"calls":12,"content_source_credit":16548,"derived_artifact_credit":1037,"direct_net":2312,"estimated_tokens_saved":2312,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2642,"response_debit":16137,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":14,"content_source_credit":236675,"derived_artifact_credit":1031,"direct_net":216989,"estimated_tokens_saved":216989,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2786,"response_debit":19277,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":79,"content_source_credit":2363420,"derived_artifact_credit":2335,"direct_net":2305287,"estimated_tokens_saved":2305287,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8457,"response_debit":59256,"source_credit_count":71,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7245},"wave_id":"1v4mw silent-failure-surfacing"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
