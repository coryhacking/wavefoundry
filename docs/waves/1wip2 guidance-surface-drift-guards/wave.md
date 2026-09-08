# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wip2 guidance-surface-drift-guards`
Title: Guidance Surface Drift Guards

## Objective

Machine-guard the two drift classes that shipped or nearly shipped this release cycle: a mutation-proven byte-parity test for the seed-211 / guru.md Index Scope mirror, and a CHANGELOG version-constants check running Unreleased-scoped in the docs gate and inside the packaging changelog-first gate (the pm1l escape point) — plus the convergence of guru.md's drifted registration passages to seed-211. The council dropped a third planned guard (retired-API scan tokens) by executed falsification.

## Changes

Change ID: `1wgwn-enh guidance-surface-drift-guards`
Change Status: `implemented`

## Participants

- Coordinator: primary Claude Code coordinator / wave-council
- Write-owning roles: implementer (test and lint-library lane), qa-reviewer
  (census, mutation proofs), docs-contract-reviewer (carriers)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-08-29

## Wave Summary

Wave `1wip2` (Guidance Surface Drift Guards) delivered one change: Guidance-Surface Drift Guards. Notable adjustments during implementation: Guidance-Surface Drift Guards: Prepare-council repairs applied before readiness, all falsified by execution. Red-team seat: the planned vocabulary extension site is INERT for API tokens (its consumers interpolate keys into bin-path shapes only, so the scan would search for .wavefoundry/bin/&lt;token&gt;; the module docstring documents the trap); injecting the tokens as content patterns produced 53 false findings on healthy live surfaces including the canonical negation sentences and the retirement ADR; setup_wavefoundry.py and setup_index.py are the LIVE implementation wf dispatches to, not retired surfaces; the changelog check's top-section scoping deadlocked the docs gate in the ordinary post-release state (dated top section plus the next cycle's first constant bump); and the plan's no-existing-parity-test premise was FALSE (GuruCitationContractRenderTests byte-guards the Citation block). Docs-contract seat: AC-3 was internally unsatisfiable as written; live rot found in guru.md's registration passages (setup_wavefoundry.py where seed-211 says wf setup); the follow-up closure step was missing; constant source modules unnamed. Repairs: the retired-token guard is DROPPED (class stays with the upgrade editing pass), the changelog check is Unreleased-scoped in the docs gate and added to the packaging changelog-first gate (the pm1l escape point), the parity premise corrected with the existing-oracle cross-reference, the guru convergence and follow-up closure added as Requirement 3, and the runbook non-edit disposition recorded.; Guidance-Surface Drift Guards: Implemented. Census executed through the real machinery (`evidence/census_drift_guards.py`): parity regions byte-identical (5,672 bytes, matching sha, exactly one heading per twin), the Citation-block oracle confirmed present, the CHANGELOG top section DATED (the docs-gate no-op state live right now) with both top claims matching live constants and zero historical pattern matches (quoted forms immune by construction), guru divergence pinned at lines 746/748 vs seed 757/759. Delivered: GuruIndexScopeParityTests (byte-parity + heading-uniqueness pins; mutation-proven in a scratch tree — a one-byte divergence inside the region fails the test; cross-referenced with the existing Citation-block oracle in both docstrings); the shared claims engine check_changelog_section_constants in docs_constants_validators with check_changelog_unreleased_constants riding the existing check_docs_constants entry (Unreleased-only; dated top section provably a no-op even with a seeded stale claim), and build_pack._check_changelog_claims wired into BOTH packaging preflight paths (release and non-release) against the section being packed — the seeded pm1l phrasing (`CHUNKER_VERSION` to 34) is caught by the engine and refused by the gate with build_zip never called, per the new test_build_pack regressions. Guru.md registration passages converged to seed-211's current text (zero setup_wavefoundry.py mentions remain; the architecture runbooks' setup_index.py commands are legitimate implementation documentation and untouched, per the recorded disposition); the session-handoff parity follow-up bullet closed. Carriers: package-wavefoundry changelog-first sentence, testing-architecture tier row. 10 new regressions green (2 parity, 6 claims-engine, 2 packaging-gate); full suite 7,651 green; docs gate ok.; Guidance-Surface Drift Guards: Record correction (implementation discovery): the changelog-first contract sentence lives in `docs/prompts/package-wavefoundry.prompt.md`, not `docs/contributing/build-and-verification.md` as the scope and AC-4 named; the packaging prompt carrier was updated and build-and-verification needed no edit (it carries no changelog-first sentence). AC-4's carrier list reads with that substitution.

**Changes delivered:**

- **Guidance-Surface Drift Guards** (`1wgwn-enh guidance-surface-drift-guards`) — 4 ACs completed. Key decisions: DROP the mechanical retired-API token guard; the guidance-posture drift class stays with the upgrade editing pass.; The CHANGELOG check runs Unreleased-only in the docs gate and additionally inside the packaging changelog-first gate against the section being packed.
## Watchpoints

- Watchpoint: censuses run through the real machinery (section extraction, the real
  claim-pattern engine over both changelog homes), never grep alone; the census is the
  authority over the plan's enumeration (standing discipline; the council falsified four
  of this plan's own premises by execution before readiness).
- Watchpoint: the docs-gate changelog check is a NO-OP whenever the top section is dated;
  the dated-top-section state is a pinned test case, not an assumption (the post-release
  deadlock the red-team found).
- Watchpoint: one claims engine, two homes — the packaging-gate check and the docs-gate
  check must share the pattern table and constant bindings, never fork.
- Watchpoint: every new guard is mutation-proven (a seeded known-bad fails it) before it
  counts as delivered; the parity test cross-references the existing Citation-block
  oracle in both directions.
- Watchpoint: guru.md edits stay OUTSIDE the Index Scope parity region and converge only
  the census-listed passages to seed-211's current text; no seed edits in this wave.
- Follow-up boundary: the reconciliation scan, retired-token classes, renderer ownership
  of guru.md, and oracle-home consolidation are outside this wave.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-28: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the red-team seat falsified the plan's central third guard by execution — the named vocabulary extension site is inert for API tokens (bin-path interpolation only, per the module's own documented trap), a content-pattern injection produced 53 false findings on healthy live surfaces including the canonical negation sentences the sibling parity guard locks in place, and half the token set is the live implementation behind `wf` rather than a retired surface — and proved the changelog check's top-section scoping deadlocks the docs gate in the ordinary post-release state; the same seat corrected the plan's false no-existing-parity-oracle premise (the Citation block is already byte-guarded). The docs-contract seat proved AC-3 internally unsatisfiable as written and found live guru.md rot (registration passages instructing the retired invocation posture) that every pass this week missed. All repairs were applied before readiness: the token guard DROPPED with its class assigned to the upgrade editing pass, the changelog check re-scoped Unreleased-only plus the packaging changelog-first gate, the parity premise corrected with oracle cross-references, and the guru convergence plus follow-up closure added as Requirement 3; strongest-alternative: negation-aware exemption tuples to save the token guard were rejected as an ever-growing exemption ledger guarding a class that is not mechanically well-defined.)

- **Council seat evidence [docs-contract-reviewer] — 2026-08-28**: five findings recorded and repaired pre-readiness: F-1 AC-3 internally unsatisfiable for the layer token (zero-findings and must-flag on the same corpus); F-2 live-surface census — real rot in guru.md's registration passages (`setup_wavefoundry.py` where seed-211 says `wf setup`) plus the legitimate-reference list a loose pattern would false-fire on; F-3 the recorded parity follow-up had no closure path; F-4 seed-160's vocabulary characterization would need extension (mooted by the guard drop); F-5 constant source modules unnamed. Verified list: serialization targets resolve, vocabulary single-sourcing accurate, parity region reproduced byte-identical (5,672 bytes), AC-2 true on the current tree, archive exclusions mechanical, hygiene clean.
- **Council seat evidence [red-team] — 2026-08-28**: five findings, four blocking, all by execution: the vocabulary extension site inert for API tokens (0 possible hits; bin-path interpolation); 53 false findings from a content-pattern injection on healthy surfaces; setup scripts are the live implementation behind `wf`, not retired; the changelog top-section scoping deadlocks the docs gate post-release (simulated); the no-existing-parity-oracle premise false (GuruCitationContractRenderTests byte-guards the Citation block, executed green). Attacked-and-held: parity extraction well-defined and byte-identical; claims-pattern prototype catches the shipped to-34 phrasing while passing all current and historical text; check_docs_constants wiring live in the real docs gate; config-key exception already implemented in the scan.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DOCS-DEL-1 | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 20 | 66,463 |
| implement | 30 | 0 |
| review | 12 | 61,479 |
| **Total** | **62** | **127,942** |

<!-- wave:context-efficiency-state {"generation":55,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":30,"content_source_credit":450,"derived_artifact_credit":196,"direct_net":-5811,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1593,"response_debit":7230,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2366},"plan":{"calls":20,"content_source_credit":81448,"derived_artifact_credit":2924,"direct_net":66463,"estimated_tokens_saved":66463,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3133,"response_debit":18282,"source_credit_count":27,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":12,"content_source_credit":88240,"derived_artifact_credit":1306,"direct_net":61479,"estimated_tokens_saved":61479,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4997,"response_debit":24416,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":62,"content_source_credit":170138,"derived_artifact_credit":4426,"direct_net":122131,"estimated_tokens_saved":127942,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9723,"response_debit":49928,"source_credit_count":46,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7218},"wave_id":"1wip2 guidance-surface-drift-guards"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
