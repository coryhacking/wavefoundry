# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-03
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1u95o model-bundle-distribution`
Title: Model Bundle Distribution

## Objective

Deliver two unambiguous release assets: the existing small, source-only
framework ZIP and an independently versioned model-set asset that can populate validated
embedding and reranker sources offline. The model companion must be directly
redistributable, safe to materialize, idempotent, and unable to interfere with
ordinary framework upgrade discovery.

## Changes

Change ID: `1uat8-enh model-bundle-distribution`
Change Status: `implemented`

## Participants

- Coordinator: Engineering / wave coordinator
- Write-owning roles: framework-engineer, test-engineer, docs-contract-reviewer
- Requested review lanes: architecture-reviewer, security-reviewer, qa-reviewer, release-reviewer, performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-08-03

## Wave Summary

Wave `1u95o model-bundle-distribution` (Model Bundle Distribution) delivered one change: Direct-Distribution Model Bundle. Notable adjustments during implementation: Direct-Distribution Model Bundle: Added versioned model-set upgrade behavior for companion and standard-package upgrades.; Direct-Distribution Model Bundle: Added semantic-index provenance and targeted re-embedding requirement for model-set updates.

**Changes delivered:**

- **Direct-Distribution Model Bundle** (`1uat8-enh model-bundle-distribution`) — 11 ACs completed. Key decisions: Use a paired, non-selectable model companion rather than two interchangeable framework packs.; Pin model artifacts and evaluate latest compatible candidates; do not dynamically download or silently upgrade models.
## Watchpoints

- The direct-redistribution decision is conditional on retaining complete
  upstream license, attribution, revision, and hash evidence in the delivered
  model-set asset; absent evidence blocks that component.
- Treat the model-set asset as an archive trust boundary: no path traversal, links,
  undeclared files, partial cache publication, or compiled host-specific cache
  files may cross it.
- The release remains deferred until this wave completes; do not publish the
  stale normal-only package or build release assets before all reviews finish.
- The "latest" evaluation is a dated compatibility decision, not an unpinned
  installation-time model lookup. A candidate that needs an embedding-dimension
  or runtime migration opens a separate change.
- A standard-only upgrade with no network must retain its working verified
  model set and clearly report the independently versioned asset required to reach the
  release-pinned newer set.

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
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-03: PASS after
  plan repair** (moderator: wave-council; primer-depth: standard; seats:
  red-team, security-reviewer; rotating-seat: security-reviewer;
  strongest-challenge: a same-name embedding artifact replacement would evade
  the current index comparison, which records only the public model name in
  `model_versions`; it could therefore mix old and new vectors while reporting
  current; strongest-alternative: never upgrade model assets automatically,
  which avoids the integrity risk but defeats offline fleet patching and leaves
  vulnerable/obsolete artifacts installed.)
- **Red-team primer:** verified the normal upgrade selector accepts only the
  canonical feature ZIP (`upgrade_wavefoundry.py:285-390`) while packaging
  enforces a single public package (`build_pack.py:1044-1081`). A companion
  must therefore be deliberately non-selectable and bound by an allowlisted,
  hash-verified manifest; a second interchangeable feature ZIP is rejected.
- **Security-reviewer:** treated companion intake as an archive trust boundary.
  The planned validator must reject traversal, links, undeclared files, hash
  or version mismatch, and partial publication; host-compiled caches stay out
  of the artifact. No implementation begins until those rejection cases have
  fixture coverage.
- **Plan repair and recheck:** `indexer.py:61-64` and
  `indexer.py:4021-4040` show that existing semantic invalidation compares
  model names and precision class. The plan now requires a declared embedding
  compatibility fingerprint and targeted full re-embedding (AC-7); this is
  required before a newer artifact may replace a cache. The council agrees the
  companion plus release-pinned standard-upgrade path is the smallest design
  that preserves deterministic upgrades.
- **Code-reviewer:** the change is correctly limited to the existing packaging,
  setup/acceleration, upgrade, and index-state boundaries; no independent
  second framework selector is permitted.
- **QA-reviewer:** every required behavior has a synthetic-fixture AC,
  including cold/offline extraction, idempotence, standard-path download,
  version upgrade, index invalidation, and rejection/rollback. Large real
  models are explicitly excluded from repository tests.
- **Architecture-reviewer:** approved the paired artifact boundary: package
  construction declares identity and provenance; setup materializes it; the
  index owns semantic compatibility; upgrade orchestrates the standard
  download/index path. This avoids leaking cache or selection logic across
  unrelated modules.
- **Release-reviewer:** approved only if the public feature ZIP remains the
  sole match for automatic discovery and release publication explicitly
  attaches the companion. A companion name collision is a release blocker.
- **Performance-reviewer:** approved the cache-first, once-per-version
  materialization path. Compiled CoreML/static caches remain host-local; model
  artifact validation must occur at intake rather than query/index hot paths.

## Dependencies

- No external wave dependencies. This planned wave intentionally precedes the
  deferred official 1.15.0 release.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 2 | 0 |
| review | 108 | 631,092 |
| **Total** | **110** | **631,092** |

<!-- wave:context-efficiency-state {"generation":115,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":2,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-2573,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":24,"response_debit":2549,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"review":{"calls":108,"content_source_credit":833443,"derived_artifact_credit":2616,"direct_net":631092,"estimated_tokens_saved":631092,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7991,"response_debit":200401,"source_credit_count":58,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3425}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":110,"content_source_credit":833443,"derived_artifact_credit":2616,"direct_net":628519,"estimated_tokens_saved":631092,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8015,"response_debit":202950,"source_credit_count":58,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3425},"wave_id":"1u95o model-bundle-distribution"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 7 | 0 | 3 | 4,468,207 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":3,"estimated_exploration_avoided":4468207,"surfaced_events":7} -->
<!-- wave:exploration-avoided end -->
