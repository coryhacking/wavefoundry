# Readiness Council — Upgrade Profile Qualification

Owner: Engineering
Status: active
Last verified: 2026-10-08

## Packet and allocation

Wave 203ha; admitted change 203h9; receipt review-policy-3cdfb987b811a7d574be. Review concerns plan feasibility, not unimplemented delivery. Standard primer: three stances, two questions. Isolated fresh agents use the inherited host-selected model for scoped Python fixture review; actual model identity is not exposed. Fixed seats do not receive each other's outputs. MCP tools were discovered and used for live code inspection; no unavailable-MCP fallback was required.

Shared evidence: admitted plan, current test owner and relevant production contracts, reported profile baselines (second: 2 failures/681/2 existing skips; prompt-names: 2 failures and 1 error/681/2 existing skips). Reported baselines are not counted as each seat's execution. Root's prospective implementation supplies manifests only to two positive fixtures, literal profile API calls for expected destination identifiers, and paired quote matching with alternate-container subtests.

## Red-team primer

Adversarial: expectations could reproduce migration defects. Constructive: model complete historical installation fixtures. Simplicity: repair the existing owner without production changes or generic fixture infrastructure. Strongest challenge: green tests could become self-confirming, and added manifests could mask refusal. Best alternative: literal historical inputs and bytes, declared-profile destination identifiers only, exact output assertions, retained missing-manifest refusal and unwired-before-index controls. Medium implementation watchpoint; no readiness blocker.

Questions: (1) How will wrong destinations, retained legacy files, changed bytes, and incorrect manifest entries still fail? (2) Which controls prove invalid-profile rejection before phase 2c and protocol rendering before indexing?

## Code-reviewer required lane

Independent code-readiness-203ha-independent: approve readiness, no blocker. Current tree confirms quote-specific mutation, hard-coded destination oracles, and two missing positive-fixture manifests. Keep real rendering, extensions, idempotence and before-index checks. Executed public tests PublicUpgradeReviewProtocolIntegrationTests.test_full_upgrade_known_bad_unwired_surface_phase_is_detected_before_index and ChangePromptRenameInstallingUpgradeTests.test_installing_upgrade_moves_prompts_rewrites_manifest_and_replaces_skills using unittest: 2 tests, OK, zero skips. Injected unwired renderer failed as intended before indexing; adjacent shipped rename passed. All five integrity booleans true for this bounded readiness check. No delivery qualification claimed.

## Architecture fixed seat

Approve; medium implementation risk, no boundary change. Expected paths come only from declared profile: wrong destinations miss expected files; exact payload and full manifest equality reject corruption; literal legacy absence catches stale artifacts. Both missing-manifest refusal and existing unwired-before-index control should remain. An explicit phase-2c sentinel strengthens ordering proof if needed. Live MCP reads support the judgment; stale semantic search was not used as proof. No tests executed by this seat. Alternative: independent identifiers plus literal inputs is stronger than duplicating full static profile tables or resetting to shipped names.

## Chair known-bad control

Public wf_review_event dry-run deliberately paired council-chair actor with code-reviewer signoff. Expected rejection; observed invalid_review_event: approval actor must be code-reviewer for that signoff. No mutation. This readiness-safe control checks lane authority rather than claiming delivery behavior.

## Security fixed seat

Approve with notes; no security finding or authority expansion. Literal historical sources and payloads plus destination identifiers from the declared profile preserve independent assertions. Require exactly one paired-quote substitution, preserve cause/message/class identity, and assert downstream phase nonexecution. Add manifests only to two positive fixtures. Preserve separate refusal and unwired-render controls and existing containment controls. Live MCP reads; no execution claim.

## QA fixed seat and required lane

Independent qa-readiness-203ha-independent: approve readiness, no blocker. Exact expected path reads, byte equality, entire manifest-list equality and legacy absence can fail independently of migration output. Preserve real-main before-index callback, exception identity and invalid-profile diagnostics. Add explicit downstream sentinel and retain a distinct missing-manifest refusal check under prompt-names.

Independently executed four current-tree tests using python3 -B -m unittest with scripts/tests on PYTHONPATH: PostExtractStaleLeafRefreshTests.test_ac9_invalid_replacement_profile_stops_before_phase_2c; PostExtractStaleLeafRefreshTests.test_ac9_invalid_profile_under_another_container_name_stops_before_phase_2c; PublicUpgradeReviewProtocolIntegrationTests.test_full_upgrade_known_bad_unwired_surface_phase_is_detected_before_index; PublicUpgradeReviewProtocolIntegrationTests.test_full_upgrade_main_reaches_real_surface_phase_for_missing_carriers. Result: 4 tests, OK, zero skips. Known-bad unwired behavior reached the index callback and raised the expected assertion; real rendering produced required carriers first. Invalid-profile tests retained guarded exception and class identity. All five integrity booleans true for this bounded readiness evidence; method injected-old-behavior. Shipped baseline only; repaired profiles/full canonical suite remain delivery work.

## Reality-checker fixed seat

Approve with medium implementation watchpoint; no blocking plan defect. AC-2 remains detecting with literal historical inputs and payloads, exact manifests and explicit absence checks. AC-1 and AC-3 require pre-phase2c rejection and carriers before indexing. Adding manifests only to two positives avoids repairing the negative control accidentally. Both missing-manifest refusal and unwired-render controls are the concrete implementation commitment. Plan review only; baseline counts were reported, not executed by this seat.

## Rotating docs-contract best-alternative seat

Approve with medium watchpoints. Strongest alternative: a literal expected-output table for shipped, second and prompt-names, independent of profile getters, catches a wrong mapping shared by renderer and oracle. Cost: duplicated vocabulary, maintenance drift, and no automatic support for arbitrary future distributions. Prefer the planned declared-profile approach for this bounded repair, with literal stable command IDs, independent historical payloads and exact output checks. Never obtain expectations from generated outputs or migration internals. Missing-manifest refusal and unwired rendering prove different boundaries and both remain. No tests executed by this seat.

## Anonymized first synthesis

Convergence was assessed before reattaching identities, with the primer still attributed. No blocking required-lane finding existed to exempt from anonymization.

- Seat 1: medium setup-masking risk is addressed by manifests in two positives only; exact assertions and distinct controls make the scope feasible.
- Seat 2: alternative static table catches shared-getter bugs, but duplicates vocabulary and limits arbitrary-profile support. Keep that residual coverage limit explicit.
- Seat 3: no authority expansion; exact-one quote mutation and downstream nonexecution strengthen the planned rejection evidence.
- Seat 4: independent public-path controls executed successfully, with the known-bad renderer raising at the expected index boundary. Delivery profiles remain unproved.
- Seat 5: test-only scope preserves boundaries; profile declaration supplies identifiers while literal inputs and full equality assertions test migration independently.

Merit assessment: all support bounded readiness; medium risks are implementation watchpoints, not demonstrated plan defects. The alternative exposes a real common-mode coverage limit but does not make the chosen integration test design invalid. No split or high/critical disputed finding, so no challenge round.

Reattached identities: Seat 1 reality-checker; Seat 2 docs-contract-reviewer; Seat 3 security-reviewer; Seat 4 qa-reviewer; Seat 5 architecture-reviewer. Code-reviewer required-lane approval is additional independent evidence.

## Fixed-seat weighing of rotating alternative

Architecture: table improves getter independence but duplicates vocabulary; prefer declared API for destination names and leave getter correctness to profile-contract tests. Security: same tradeoff; no security blocker, do not claim shared-getter correctness is independently covered. QA: same tradeoff; arbitrary-profile qualification and exact migration assertions favor declared APIs for this scope. Both distinct negative controls and explicit downstream nonexecution remain. No extra probes were run during alternative weighing.

Reality-checker final weighing: static table improves shared-getter detection but duplicates vocabulary and only covers enumerated profiles; prefer declared API for this scope and disclose getter-correctness limitation. Final verdict unchanged. The root commits to ast.literal_eval/ repr for captured literal values, exact-one replacement, single/double-quote alternate-name subtests, downstream enforce_index_guard_handoff.assert_not_called(), two positive manifests only, and a separate bounded missing-manifest refusal probe under prompt-names.

## Final readiness synthesis

Verdict: approve readiness. Seat agreement: unanimous. Maximum severity: medium implementation watchpoints; zero blocking findings. Primer's oracle-coupling and manifest-masking risks were confirmed and bounded by independent inputs, exact outputs, localized fixture setup and distinct negative controls. Strongest alternative is the literal profile table; each fixed seat weighed it and preferred the declared-profile path for this scope. Improvements: explicit downstream nonexecution, exact-one robust quote mutation, separate refusal probe, preserved unwired renderer control, and honest profile-getter/qualification limits. Required code/QA lanes independently approve the current plan. No code edited, wave readied/opened, delivery approved, commit made or closure performed by the council.
