# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-16
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1vk4c field-feedback-1p17p1-seed-scan-gaps`
Title: Field Feedback from the 1.17.1 Test Upgrade: Seed and Scan Gaps

## Objective

Close two framework-caused gaps surfaced by the first 1.17.1 field upgrades before 1.17.1 ships: seed-100 points consumers at a `platform-mapping.md` Skills section no seed tells them to write, and the retired-surface reconciliation scan flags the `## Resolved / closed` archive row that seed-230 tells repos to write (while seed-150/160 still say to remove it). Both recur on every consumer upgrade; both are small and structural.

## Changes

Change ID: `1vk4a-bug platform-mapping-skills-section-unauthored`
Change Status: `implemented`

Change ID: `1vk4b-bug reconcile-scan-flags-mandated-resolved-closed-archive`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-08-16

## Wave Summary

Wave `1vk4c` (Field Feedback from the 1.17.1 Test Upgrade: Seed and Scan Gaps) delivered two changes: Seed-100 Points at a platform-mapping Skills Section No Seed Authors and Reconciliation Scan Flags the Archive Row Seed-230 Tells the Repo to Write. Notable adjustments during implementation: Seed-100 Points at a platform-mapping Skills Section No Seed Authors: Implemented under `seed_edit_allowed`: seed-050's platform-mapping section gained the "Skills subsection (wave 1vk4c)" specification (activation predicate = host root exists; host skill directories; rendered set listed from disk, never from a seed; gating rules incl. `wf-guru`/`wf-package`/`wf-code-cleanup` doc-gating and independence from `enabled_agent_roles`; written after the task-20 render pass; re-verified on upgrade); seed-160's post-upgrade checklist gained the Skills bullet next to the auto-Guru routing bullet (add or refresh from disk when missing or stale, never from the seed's example list); the rendered `docs/prompts/upgrade-wavefoundry.prompt.md` gained the sibling verify item next to its Auto-Guru routing item; seed-100's "§ Skills" pointer needed no change (this repo's `### Skills (...)` heading resolves under the any-level, begins-with-`Skills` contract). AC-5: this repo's section listed 14 skill directories per host and the doc-gated set correctly, but lacked two of the specified gating rules (render on setup/upgrade; independence from `enabled_agent_roles`), so one sentence was added rather than the planned no-edit; noted here as the deviation. docs-lint ok.; Reconciliation Scan Flags the Archive Row Seed-230 Tells the Repo to Write: Planned from the Aceiss field report (two upgrades, same single finding). Every claim re-verified against the tree: seed-230 §6 heading and instruction, seed-220 canonical path, path-shaped exclusions, `_LIVE_JOURNAL_MIGRATION` as the only journals exemption, `disposition_key` shape and fail-open store, the 1v7a1 comment naming the collision. Section-aware allowlist chosen over a line-scoped wording exemption because seed-230 mandates the heading but not the note's wording.; Reconciliation Scan Flags the Archive Row Seed-230 Tells the Repo to Write: Readiness council (red-team fixed seat, docs-contract rotating seat, code and qa readiness lanes) corrected the plan: disposition semantics restated from an executed probe (matched-text key; over-suppression of the live table), table-row scope, pattern-agnostic exemption, pinned heading contract, seed-150/160 reconciliation, CHANGELOG AC, concrete non-Markdown control, no rendered mirror for seed-230.

**Changes delivered:**

- **Seed-100 Points at a platform-mapping Skills Section No Seed Authors** (`1vk4a-bug platform-mapping-skills-section-unauthored`) — 5 ACs completed. Key decisions: Keep the section agent-authored and specify it in seed-050 (plus a seed-160 checklist bullet) rather than rendering it.
- **Reconciliation Scan Flags the Archive Row Seed-230 Tells the Repo to Write** (`1vk4b-bug reconcile-scan-flags-mandated-resolved-closed-archive`) — 5 ACs completed. Key decisions: Readiness council corrections adopted: exempt TABLE ROWS under the heading, not the whole span (seed-230 mandates a table; parked prose still reports); apply to every producer; pin the ATX/fence/EOF contract; keep the exclusion structural in `scan_repo`; reconcile seed-150/160 wording; make dropping the stopgap disposition an operator step.; Section-aware exclusion keyed on an exact (file, H2 heading) allowlist, initially only `docs/missing-docs.md` / `Resolved / closed`.
## Watchpoints

- Watchpoint: both changes edit seeds; open `seed_edit_allowed` per edit window and close it after.
- `reconcile_scan.py` carries fragile-file memory `1u43m`: exclusions must fail toward reporting; vary the LOCATION in fixtures (same string in another section, another file, an H3), not only the string.
- Watchpoint: the receipt selects a delivery council (`wave-council-delivery`) for this wave.
- Follow-up: intended to ride the 1.17.1 release; commit and release only after close.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the 1vk4b rationale claimed a stopgap disposition is invalidated by any reword, but `disposition_key` hashes the regex MATCH, so an executed probe showed the field stopgap survives rewording and also silences the same path in the live High table (over-suppression, the dangerous direction per memory 1u43m); adopted as a plan correction with a new AC-3 and an operator step in the CHANGELOG; strongest-alternative: exempt only TABLE ROWS under the exact heading rather than the whole H2 span, since seed-230 mandates a table and whole-span exemption leaves a park-live-prose vector; adopted. Red-team seat: executed field fixture (both the archive row and the High-table row report today; a literal `.wavefoundry/bin/docs-lint` in the archive row reports too, so the exclusion is pattern-agnostic), pinned the ATX/fence/EOF heading contract, surfaced that seed-150/160 still say resolved rows are removed (reconciled in requirement 4), placement stays structural in `scan_repo`. Docs-contract seat: every cited seed heading and scanner symbol resolves; corrected 1vk4a AC-5 (14 skill directories per host incl. `.agents/skills/`), the doc-gated set (`wf-guru` too), the activation predicate (host root exists), the rendered upgrade prompt not carrying seed-160's checklist (requirement 4 now adds one sibling verify item), no rendered mirror for seed-230; both plans consistent with the wave record. Code and qa readiness (coordinator, in-thread after the seat agent was stopped): every `scan_repo` producer carries a match offset (literal, retired-content, prompt-extension, qualified and bare tool patterns), so one archive predicate covers all; seed-content censuses live in six test files and run in the full suite; each AC in both docs has a named falsifier.)

- **Delivery review — 2026-08-16: APPROVE.** Three fresh lanes (code, qa, docs-contract) approved the mechanism and the seed prose and returned one aggregated low finding (`archive-exclusion-hardening-and-suite-evidence`: fence-length and empty-heading edge shapes, two surviving mutants, key-equality and end-to-end test gaps, seed/CHANGELOG precision, unrecorded suite evidence). Repaired in one pass; a fresh reverifier confirmed it with four executed known-bads and the post-repair full suite (7267 tests across 63 files OK). Delivery council (required by the receipt): APPROVE; strongest residual risk is design-inherent (rows parked under the archive heading are silenced by construction) and accepted because the exemption is an exact (path, ATX H2) allowlist scoped to table rows, fails toward reporting, and is pinned to one entry by test.
- **Memory pass:** see the close checkpoint.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| archive-exclusion-hardening-and-suite-evidence | do_now | no | completed | — |

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
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 74 | 1,517,307 |
| implement | 47 | 0 |
| review | 31 | 254,498 |
| **Total** | **152** | **1,771,805** |

<!-- wave:context-efficiency-state {"generation":148,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":47,"content_source_credit":9985,"derived_artifact_credit":0,"direct_net":-2043,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2117,"response_debit":13737,"source_credit_count":1,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3826},"plan":{"calls":74,"content_source_credit":1671473,"derived_artifact_credit":2944,"direct_net":1517307,"estimated_tokens_saved":1517307,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5037,"response_debit":155579,"source_credit_count":53,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":31,"content_source_credit":306854,"derived_artifact_credit":2371,"direct_net":254498,"estimated_tokens_saved":254498,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7988,"response_debit":48085,"source_credit_count":35,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":152,"content_source_credit":1988312,"derived_artifact_credit":5315,"direct_net":1769762,"estimated_tokens_saved":1771805,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15142,"response_debit":217401,"source_credit_count":89,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8678},"wave_id":"1vk4c field-feedback-1p17p1-seed-scan-gaps"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 2 | 799,295 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":799295,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
