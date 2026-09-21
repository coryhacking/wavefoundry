# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ym4h waveforge-merge-prep`
Title: Waveforge Merge Prep

## Objective

When this wave closes, the two Wavefoundry-side items the fork audit left open before the Waveforge merge are settled: the `dashboard.terminology` key has a stated vocabulary (Wavefoundry tier names as keys), a real consumer and a visible advisory for a wrong-vocabulary map, and the author-facing marker namespace alternation lives in one module constant that already includes `waveforge`. Now, because the five-wave modularity plan is closed and these were the last unscoped recommendations in the audit.

## Changes

Change ID: `1yk1m-enh terminology-label-contract`
Change Status: `implemented`

Change ID: `1ym4g-enh shared-marker-prefix-constant`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (dashboard library and script, marker module and the three rewired sites, tests), technical-writer (dashboard reference docs, CHANGELOG)
- Requested review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-09-21

## Wave Summary

Wave `1ym4h` (Waveforge Merge Prep) delivered two changes: Terminology Label Contract For The Dashboard and Shared Marker Namespace Constant. Notable adjustments during implementation: Terminology Label Contract For The Dashboard: Implementation complete for dashboard labels: real config normalization and snapshot field, per-snapshot label register, dynamic lifecycle table (rebuilt at render, including selected dialog), all scoped label surfaces, and header advisory. Contract docs checked against shipped behavior.; Terminology Label Contract For The Dashboard: Scoped checks passed; literal census has six exact justified exceptions and no stale entries, and its appended Prepare Wave mutant reports exactly one new hit. Rendered default/custom/reset labels and advisory presence/absence pass.

**Changes delivered:**

- **Terminology Label Contract For The Dashboard** (`1yk1m-enh terminology-label-contract`) — 5 ACs completed. Key decisions: Keys are Wavefoundry tier names; values are display labels.; Scope is the dashboard label register only.
- **Shared Marker Namespace Constant** (`1ym4g-enh shared-marker-prefix-constant`) — 5 ACs completed. Key decisions: One module constant, not configuration.; Include `waveforge` now.
## Watchpoints

- Watchpoint: the two changes share no files; they may be implemented in either order or in parallel by separate workers.
- Watchpoint: `1ym4g` adds a sibling import to `server_impl.py`; the reload purge list must gain the module or the import-derived purge test fails.
- Watchpoint: operator-approved revision after readiness keeps the `CHUNKER_VERSION` bump deferred to the Waveforge merge, which must verify index invalidation. The new module now must enter `_SOURCE_NAMES` with stale-runtime detection tests. The revised plans were re-prepared before implementation (readiness-delta and currency contexts, 2026-09-21); the earlier approval describes the earlier scope.
- Watchpoint: `1ym4g` pins three intended behavior changes on existing input (stripper boundary, named ends closing chunker regions, annotated begins recognized); the stripper has no test today, so its baseline is pinned before rewiring.
- Watchpoint: `1yk1m` changes `dashboard.js`, which has no default-on JavaScript harness; the Python literal census is the gate, node-gated slice tests are evidence, and the implementer must use a plain `import` in `server_impl.py` so the purge census sees it.
- Follow-up: Waveforge owns the version bump and verification that the merged version re-chunks affected documents; this wave does not prove downstream integration.
- Follow-up: Waveforge's own remap of `set` to `wave` and `wave` to `change` happens in their tree at merge time, not here.

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
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

Delivery complete: code, QA and docs-contract approved; see [delivery review](docs-delivery-review.md). Full suite green: 9,468 tests / 119 files, 21 skipped, current receipt independently verified. All ACs/tasks met; memory proposal yielded no candidates. Downstream version invalidation and terminology remap stay outside scope. Operator closure/signoff and commit are pending; no terminal close performed.

Review allocation limitation: the host refused a new reviewer thread and a prior-session reviewer activation with `agent thread limit reached`. The existing independent docs reviewer, which implemented neither change, will assess code, QA and docs contracts in its fresh review context. Lane verdicts are separate judgments from one reviewer context, not three independent passes. Coordinator still verifies integration and the full-suite receipt.

Implementation allocation: Ordered sequence: (1) parallel generic implementer for marker plumbing and UI implementer for dashboard code/tests, with coordinator owning reference docs and CHANGELOG; (2) coordinator integration and full suite; (3) fresh code, QA and docs-contract delivery review. Workers own disjoint source/test paths and their respective change progress logs. Host-default model/effort requested for bounded implementation with cross-module reasoning; observed runtime identity unknown.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: both plans rested on claims the tree refutes, an invented reader symbol and a chunker end regex that is bare-only today; strongest-alternative: keep the chunker's bare-only end and derive only the begin alternation, rejected as preserving a known defect). Both seats blocked on plan text, one bounded repair pass resolved every finding, and two focused verifiers approved; per-seat evidence and the repair summary are in [readiness review](readiness-review.md).

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 78 | 5,220,692 |
| implement | 104 | 2,035,212 |
| review | 23 | 62,423 |
| **Total** | **205** | **7,318,327** |

<!-- wave:context-efficiency-state {"generation":174,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":104,"content_source_credit":2237667,"derived_artifact_credit":957,"direct_net":2035212,"estimated_tokens_saved":2035212,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6413,"response_debit":198902,"source_credit_count":89,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1903},"plan":{"calls":78,"content_source_credit":5344604,"derived_artifact_credit":4206,"direct_net":5220692,"estimated_tokens_saved":5220692,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4852,"response_debit":135400,"source_credit_count":188,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12134},"review":{"calls":23,"content_source_credit":89325,"derived_artifact_credit":901,"direct_net":62423,"estimated_tokens_saved":62423,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3746,"response_debit":26373,"source_credit_count":13,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":205,"content_source_credit":7671596,"derived_artifact_credit":6064,"direct_net":7318327,"estimated_tokens_saved":7318327,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15011,"response_debit":360675,"source_credit_count":290,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":16353},"wave_id":"1ym4h waveforge-merge-prep"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 9 | 0 | 7 | 7,284,957 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":7284957,"surfaced_events":9} -->
<!-- wave:exploration-avoided end -->
