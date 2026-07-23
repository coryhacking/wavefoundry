# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-22
review-evidence-source: events.jsonl

wave-id: `1t9tk changelog-first-packaging`
Title: Changelog First Packaging

## Objective

Make changelog-first packaging structural after the 1.14.0 release shipped a zip whose internal CHANGELOG was one revision behind the repo: every versioned pack build now refuses to run without a `## [version]` changelog section, and the packaging prompt pins the completeness and rebuild-after-amendment rules the guard cannot decide mechanically.

## Changes

Change ID: `1t9tj-enh changelog-first-pack-builds`
Change Status: `implemented`

Completed At: 2026-07-22

## Wave Summary

Wave `1t9tk` (Changelog First Packaging) delivered one change: Changelog-First Pack Builds. Notable adjustments during implementation: Changelog-First Pack Builds: Implemented: the plain build path's pre-flight refuses without the `## [version]` section (else-branch of the release preflight, before the docs gate, before any stamping), message says to create the entry first; four tests added (refusal with side-effect assertions, missing-file refusal, success-once-present, release-path source pin); packaging prompt now carries the mechanical-enforcement note plus the completeness and rebuild-after-amendment rules with a preference for --release on publishes. Module 101 OK; known-bad probe (guard vacuously satisfied = pre-fix plain path) flipped both refusal tests.

**Changes delivered:**

- **Changelog-First Pack Builds** (`1t9tj-enh changelog-first-pack-builds`) — 4 ACs completed. Key decisions: Hard fail with a create-the-entry-first message; no bypass flag.; Prompt-level rule for completeness and rebuild-after-amendment.
## Journal Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 5 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Prepare Review Evidence

Readiness council pass, 2026-07-22 (single change, build-tool pre-flight scope; claims verified against the tree):

- reality-checker: the asymmetry is exactly as planned — the release preflight requires the `## [version]` section (build_pack.py main, release branch, via `_extract_changelog_section`) while the plain `--version` path runs docs gate → collision warning → `build_zip` with no changelog consultation; `_extract_changelog_section` returns an empty string for a missing section AND a missing file, so one truthiness check covers both; `main()` performs no stamping before `build_zip`, so a pre-gate refusal leaves the tree untouched.
- red-team: strongest challenge — could the hard fail block a legitimate flow? Every supported release flow already requires the section (the `--release` preflight), test builds gain a one-minute skeleton-entry cost by design (that IS the directive), and the failure message names the exact remedy; no bypass flag, because an ignorable guard would not have changed the 1.14.0 outcome. Second challenge — double-reporting on `--release`: the new check is scoped to the non-release path only.
- qa-reviewer: main()-level tests follow the existing argv-patch idiom; the refusal test asserts exit code, message, and that neither `check_docs_gate` nor `build_zip` ran; the success test asserts the identical invocation proceeds once the section exists; release-path preservation is pinned.
- docs-contract-reviewer: the completeness and rebuild-after-amendment rules land in the repo-local packaging prompt (no owning seed — packaging runs only in the framework source repo, verified by seed grep); requirements, ACs, and decisions are consistent.

Synthesis verdict: READY.

## Review Checkpoints

- **Delivery-phase Wave Council [delivery-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: mocked-main fixtures could vacuously pass — refuted by the known-bad probe flipping both refusal tests when the guard is neutered; strongest-alternative: hooking a zip-vs-repo changelog comparison at release time — rejected, no owned release step exists outside --release to hook, and --release already builds fresh from the clean tree.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a hard fail with no bypass could block a legitimate build — resolved because every supported release flow already requires the section and the message names the one-line remedy; strongest-alternative: warning-only — rejected as ignorable, per the Decision Log.)

## Delivery Review Evidence

Delivery council pass, 2026-07-22, over the landed diff (build_pack.py pre-flight else-branch; four tests in test_build_pack.py; packaging-prompt rules):

- reality-checker: the guard sits in the else-branch of the release-mode preflight, runs before `check_docs_gate` and before any stamping (the refusal test asserts neither the docs gate nor `build_zip` ran), and reuses `_extract_changelog_section` as the single detection authority, covering both a missing section and a missing CHANGELOG.md with one truthiness check.
- red-team: strongest challenge — could the guard and the release preflight interact badly? They are mutually exclusive branches, pinned by the source-order test; `--release-dry-run` takes the release branch and is untouched. Second challenge — does the mocked-main test fixture prove the real path? The mocks stub only downstream effects (build_zip, docs gate, repo-root discovery, build suffix); the guard itself runs real code against a real temp CHANGELOG file, and the known-bad probe (guard vacuously satisfied) flipped both refusal tests, proving the assertions bind to the guard.
- qa-reviewer: four tests — refusal with side-effect assertions, missing-file refusal, success-once-present, and the release-path source pin; module 101 OK; full suite 6,122/6,122 OK on the final tree.
- docs-contract-reviewer: the prompt's step 4 now states the mechanical enforcement, the completeness-before-final-pack rule, the rebuild-after-amendment rule with the ship-what-you-tested rationale, and the --release preference for publishes; docs lint clean; no seed involved (repo-local prompt, verified).

Synthesis verdict: PASS. Zero findings.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

operator-signoff: approved (2026-07-22, operator requested review and close in the current session)
- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 11 | 15,200 |
| implement | 9 | 383,413 |
| review | 4 | 2,734 |
| **Total** | **24** | **401,347** |

<!-- wave:context-efficiency-state {"generation":23,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":9,"content_source_credit":398871,"derived_artifact_credit":662,"direct_net":383413,"estimated_tokens_saved":383413,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":918,"response_debit":15202,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":11,"content_source_credit":24672,"derived_artifact_credit":662,"direct_net":15200,"estimated_tokens_saved":15200,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":860,"response_debit":12471,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3197},"review":{"calls":4,"content_source_credit":4336,"derived_artifact_credit":131,"direct_net":2734,"estimated_tokens_saved":2734,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":374,"response_debit":2448,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1089}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":24,"content_source_credit":427879,"derived_artifact_credit":1455,"direct_net":401347,"estimated_tokens_saved":401347,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2152,"response_debit":30121,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4286},"wave_id":"1t9tk changelog-first-packaging"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
