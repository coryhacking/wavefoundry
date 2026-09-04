# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-04
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1x4ol index-build-cost-and-scanner-bounds`
Title: Index Build Cost And Scanner Bounds

## Objective

Make a graph rebuild cost what the graph costs, without changing what the secrets scanner detects. Today the command takes about 203 seconds, of which 198.5 are a full secrets re-scan the graph rebuild has no reason to trigger, and 173.6 of those come from one file meeting a regex that is linear upstream and quadratic here. This wave scopes the flag and collapses the redundant pattern shape in the engine, two transformations that are provably detection-preserving, then measures where that leaves the full scan. No time bound: operator decision, 2026-09-04.

## Changes

Change ID: `1x4oj-bug graph-rebuild-forces-full-secrets-scan`
Change Status: `complete`

Change ID: `1x4ok-enh secrets-scan-cost-bounds`
Change Status: `complete`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: performance-reviewer, code-reviewer, qa-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer, security-reviewer
- Product-owner admission review: operator-approved on 2026-09-04 by the instruction to plan the optimization wave after the measured diagnosis was presented.

Completed At: 2026-09-04

## Wave Summary

Wave `1x4ol` (Index Build Cost And Scanner Bounds) delivered two changes: Scope the Secrets Scan to Content Changes on a Graph Rebuild and Remove the Secrets Scanner's Super-Linear Cost Without Changing What It Detects.

**Changes delivered:**

- **Scope the Secrets Scan to Content Changes on a Graph Rebuild** (`1x4oj-bug graph-rebuild-forces-full-secrets-scan`) — 7 ACs completed. Key decisions: Scope the `full` flag rather than skip the scan for graph builds.
- **Remove the Secrets Scanner's Super-Linear Cost Without Changing What It Detects** (`1x4ok-enh secrets-scan-cost-bounds`) — 8 ACs completed. Key decisions: Rewrite in the engine shim at load, never in the ruleset data.; Prove equivalence differentially, not by fixture alone.
## Watchpoints

- **This is a security scanner. A performance change here must not cost detection.** Every pattern edit is judged against true-positive and false-positive fixtures frozen BEFORE the edit, never against the edited pattern's own output. The repository's findings ledger holds zero entries, so parity judged on live findings would pass vacuously.
- **No new skip condition of any kind.** The operator declined a time bound on 2026-09-04. `1x4ok` must scan every file it scanned before; AC-5 asserts the scanned set is identical over the real repository. The pre-existing byte and binary guard skips are invisible to the close gate today, and that is parked as `1x4om`, not addressed here.
- **Do not narrow the scan set to buy speed.** Excluding the expensive evidence artifacts would make the numbers look right by scanning less of the committed tree. Both changes keep the same files eligible.
- **`1x4oj` before `1x4ok`.** The scoping fix removes the cost from the common path in one line; the scanner work is then measured against the rare full scan rather than against a number the flag fix was going to erase anyway.
- **Freeze detection fixtures before any engine edit.** The differential test judges the rewrite against inputs recorded BEFORE it exists. A fixture written after the rewrite proves nothing about what stopped matching.
- Both changes touch the secrets path, so they share one production write owner and land in the order above.

### Measured but not admitted

Two further costs were measured during diagnosis and are deliberately left out, recorded here so a later wave does not re-derive them.

- **Graph extraction worker sizing.** 335 code files fall in the `< 500` tier, which caps at 3 workers on a machine with 8 performance cores. Only about 18 seconds of the 46.6 second graph phase is parallelisable, because the incremental merge is 25.3 of it, so the ceiling on this is modest.
- **The incremental merge.** 25.3 seconds for 719 files, 127,225 symbols and 93,415 re-resolved edges is the single largest graph-side cost and the more promising target of the two. It has not been profiled, so it is named rather than scoped.

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
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Follows closed wave `1wpih index-quality-evaluation-and-ranking`, which did not cause this cost but made it frequent: it bumped the graph builder twice, and every bump forces a full graph rebuild that drags a full secrets scan behind it.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-04: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the security seat found that this wave was about to add a THIRD way for a file to go unscanned while the close-time secrets gate can see none of them, because it reasons only over findings that exist and a never-scanned file produces none; strongest-alternative: make the time bound a hard failure rather than a reported skip, rejected because stopping a build on a performance property is worse than a visible skip, so the repair makes the skip accountable instead of fatal)
  - security-reviewer seat: `_check_secrets_gate` loads only `docs/scan-findings.json`. `_record_scan_skip` writes a stderr line and appends to `_SCANNER_SKIPS`, which is reset at the start of every `check_hardcoded_secrets` run, and `scan-state.json` persists counts with no paths. The gap is not theoretical: the current build log shows `Wavefoundry_Executive_Presentation.pptx` skipped by the binary guard, and that skip reached close with no signal. Repaired into `1x4ok` as Requirement 9 and AC-9, scoped to cover the pre-existing byte and binary guards as well as the new bound, with `server_impl.py` added as a review target.
  - red-team seat, first finding: `1x4ok` AC-1 and AC-5 referenced "the time bound" and "a stated ceiling" with no values, so both were satisfiable by whatever the implementation produced. Repaired as Requirement 7, which declares 30 s per file and 60 s for the full-repository scan from the measured distribution (slowest legitimate file 2.63 s, next two 11.2 s and 13.7 s, outlier 173.6 s, current full scan 198.5 s), and Requirement 8, which forbids the bound tripping on any committed file after the prefix fix.
  - red-team seat, second finding: `1x4oj`'s safety rested on an unstated property. The incremental branch of `update_secrets_scan` returns early when `changed` and `removed` are both empty, reporting `up_to_date: True` and printing no completion line; the change is safe only because the full-rebuild branch populates the candidate set with every file. Repaired as Requirement 6 and AC-6 so a later narrowing cannot turn the scan into a silent no-op that still reports success.
  - Every claim was checked against the tree rather than the plans' prose. The three repairs were applied before this verdict was recorded, so the approval binds the repaired documents.
- **Scope revision after readiness — 2026-09-04: operator declined the time bound.** The security seat's repair had made a skip accountable at close because the wave was adding a new skip route; with no time bound there is no new route, so that requirement was withdrawn from `1x4ok` and parked as `1x4om-bug scanner-guard-skips-invisible-at-close`, since the gap for the pre-existing byte and binary guards is real and live today. The red team's two findings stand: the thresholds it flagged as undeclared no longer exist rather than being declared, and the non-empty candidate set in `1x4oj` is still pinned. `1x4ok` now lands only the load-time prefix collapse, proven language-preserving by differential test (0 mismatches over 100,000 random strings; 5 of 5 real true positives with identical spans and groups), plus a per-rule cost report; the full-scan result is a measurement, not a gate. The receipt rotates on these edits and a fresh readiness approval is recorded below against the revised documents.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 30 | 20,842 |
| implement | 64 | 0 |
| review | 17 | 134,720 |
| **Total** | **111** | **155,562** |

<!-- wave:context-efficiency-state {"generation":110,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":64,"content_source_credit":9971,"derived_artifact_credit":221,"direct_net":-4203,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2689,"response_debit":15371,"source_credit_count":2,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3665},"plan":{"calls":30,"content_source_credit":49120,"derived_artifact_credit":4980,"direct_net":20842,"estimated_tokens_saved":20842,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5984,"response_debit":37350,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10076},"review":{"calls":17,"content_source_credit":163513,"derived_artifact_credit":1536,"direct_net":134720,"estimated_tokens_saved":134720,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4701,"response_debit":27517,"source_credit_count":34,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":111,"content_source_credit":222604,"derived_artifact_credit":6737,"direct_net":151359,"estimated_tokens_saved":155562,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13374,"response_debit":80238,"source_credit_count":52,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":15630},"wave_id":"1x4ol index-build-cost-and-scanner-bounds"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
