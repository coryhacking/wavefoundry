# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-22
review-evidence-source: events.jsonl

wave-id: `1t87f relocated-journal-naming`
Title: Relocated Journal Naming

## Objective

Give relocated historical wave journals the lifecycle type suffix: the 1t9wa migration and the local 16 relocated journals converge on `<prefix>-jrnl <slug>.md`, consistent with every other typed artifact in a wave folder (operator directive following the 1t9wa close).

## Changes

Change ID: `1t76w-enh relocated-journal-jrnl-naming`
Change Status: `implemented`

Completed At: 2026-07-22

## Wave Summary

Wave `1t87f` (Relocated Journal Naming) delivered one change: Relocated Wave Journals Carry the -jrnl Type Suffix. Notable adjustments during implementation: Relocated Wave Journals Carry the -jrnl Type Suffix: Implemented: `_migrate_journals` destination = `<prefix>-jrnl <slug>.md` (partition on first space; report line now names the destination); relocation tests updated with a bare-name-absence pin (8/8 OK); seed 210 step 2 names the form; 16 local journals renamed via the identical split rule; pre- and post-rename censuses found zero live bare-name references; docs gate clean. Note: `wf_create_wave` for this wave itself ran on a stale pre-retirement server session and scaffolded a journal — removed, heading fixed, `wf_reload_mcp` applied (impl now matches disk).

**Changes delivered:**

- **Relocated Wave Journals Carry the -jrnl Type Suffix** (`1t76w-enh relocated-journal-jrnl-naming`) — 3 ACs completed. Key decisions: Destination form `<prefix>-jrnl <slug>.md` (space form).; No old-name compatibility pass in the hook.
## Watchpoints

- Watchpoint: the local rename must mirror the hook's exact naming output — implement the hook first and derive the 16 names from the same split rule; follow-up in-wave if any live doc references a relocated journal by its bare name.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 5 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Delivery-phase Wave Council [delivery-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: hook/local naming divergence — resolved by deriving both from the same partition rule with the destination form pinned in tests; strongest-alternative: none material — the bare-name compatibility pass stays correctly out of scope since the relocation hook never shipped.)

- **Prepare-phase Wave Council [prepare-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: bare-name references breaking on rename — resolved by the before/after reference census and docs-gate link integrity; strongest-alternative: dash-only destination form — rejected, inconsistent with the space-form `<prefix>-<type> <slug>` grammar of every sibling artifact.)

## Prepare Review Evidence

Readiness council pass, 2026-07-22 (single small change; claims verified against the tree):

- reality-checker: the target state is decidable — 16 relocated journals currently sit at `docs/waves/<wave-id>/<wave-id-with-dashes>.md`; the destination form `<prefix>-jrnl <slug>.md` derives mechanically from splitting the wave id on its first space; `check_wave_docs` was read and its non-wave.md checks are content-driven (Change ID/Item ID header lines), so no lint grammar change is needed.
- red-team: strongest challenge — a live doc referencing a relocated journal by its bare name breaks on rename; answered by a repository-wide reference census before and after the rename plus the docs gate's link integrity. Second — hook/local divergence in naming; answered by the watchpoint: hook first, local names derived from the same split rule, and the regression test pins the destination form. Old-name compatibility is correctly out of scope: the relocation hook has never shipped.
- qa-reviewer: ACs are falsifiable (fixture relocation to the typed name with re-run no-op; zero bare-name local journals; seed 210 wording; full suite). `VALID_CHANGE_KINDS` is untouched, so no creation-tool surface changes.
- docs-contract-reviewer: the operator directive and the space-form grammar decision are recorded in the Decision Log with rejected alternatives; the 1t9w8-era "moot" ruling is scoped correctly (moot for live journals, not for relocated history).

Synthesis verdict: READY.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

Delivery council pass, 2026-07-22 (single change; claims verified against the tree and the suite):

- reality-checker: the postcondition is real — 0 bare-name relocated journals remain and 16 `-jrnl` files exist, each verified at `docs/waves/<wave-id>/<prefix>-jrnl <slug>.md`; the hook's report line now names the destination; the local rename used the identical partition rule the hook ships.
- red-team: strongest challenge — hook/local naming divergence; answered by deriving both from the same split rule and pinning the destination form in the relocation test with an explicit bare-name-absence assertion. Second — broken references; the before/after censuses found zero live bare-name references and the docs gate's link integrity passed. The stale-server journal scaffold during this wave's own creation was caught, removed, and resolved with wf_reload_mcp (impl matches disk).
- qa-reviewer: `JournalMigrationTests` 8/8 OK with the updated destination expectations; full suite 6,138 tests across 59 files OK in a single run; `VALID_CHANGE_KINDS` untouched.
- docs-contract-reviewer: seed 210 step 2 now names the `<prefix>-jrnl <slug>.md` form so prompt-path migrations converge with the hook; tracking is real-time with all ACs checked and evidence recorded.

Synthesis verdict: PASS.
- operator-signoff: approved 2026-07-22 (operator independently verified naming derivation, collision safety, tests, seed 210, census, and suite, then instructed close in session)

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 8 | 380,925 |
| implement | 11 | 10,472 |
| review | 16 | 593,191 |
| **Total** | **35** | **984,588** |

<!-- wave:context-efficiency-state {"generation":28,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":11,"content_source_credit":14500,"derived_artifact_credit":769,"direct_net":10472,"estimated_tokens_saved":10472,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1584,"response_debit":3213,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":8,"content_source_credit":383327,"derived_artifact_credit":527,"direct_net":380925,"estimated_tokens_saved":380925,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":182,"response_debit":5938,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3191},"review":{"calls":16,"content_source_credit":615823,"derived_artifact_credit":0,"direct_net":593191,"estimated_tokens_saved":593191,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":541,"response_debit":23186,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1095}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":35,"content_source_credit":1013650,"derived_artifact_credit":1296,"direct_net":984588,"estimated_tokens_saved":984588,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2307,"response_debit":32337,"source_credit_count":39,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4286},"wave_id":"1t87f relocated-journal-naming"} -->
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
