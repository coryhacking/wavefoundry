# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-22
review-evidence-source: events.jsonl

wave-id: `1t9wa retire-wave-journals`
Title: Retire Wave Journals

## Objective

Retire the per-wave journal class in favor of the memory system: wave creation stops scaffolding journals, seeds and prompts route in-flight and close-time capture to memory candidates, the distill prompt becomes an opt-in migration, and this repository's journals are fully migrated (scaffolds deleted, content-bearing wave journals moved into their wave folders, role journals folded into role docs and memory records). Census evidence: 100 of 121 journals are the untouched scaffold; nothing has been journaled since the memory system landed.

## Changes

Change ID: `1t9w9-ref retire-wave-journals-for-memory`
Change Status: `implemented`

Completed At: 2026-07-22

## Wave Summary

Wave `1t9wa` (Retire Wave Journals) delivered one change: Retire Wave Journals in Favor of the Memory System. Notable adjustments during implementation: Retire Wave Journals in Favor of the Memory System: Operator directive: add the upgrade path — mechanical field migration (provable-scaffold deletion + wave-journal relocation) added as requirement 4 with AC-4; the prompt narrows to the judgment-requiring remainder; ACs renumbered.; Retire Wave Journals in Favor of the Memory System: Creation path retired: `wf_create_wave` scaffolds no journal, envelope fields removed, scaffold heading renamed `## Watchpoints` with legacy `## Journal Watchpoints` accepted via `WAVE_WATCHPOINT_HEADINGS`; lint's active-wave-journal-reference and persona `## Associated journal` requirements removed; journals removed from required-doc manifests.; Retire Wave Journals in Favor of the Memory System: Local migration executed: 99 pristine scaffolds deleted, 16 content-bearing wave journals relocated into their wave directories, 6 role journals folded verbatim into their role/persona docs under an Operating Memory section, README deleted, `docs/agents/journals/` removed; all live references updated (docs/README, workflow-config journal_root, dashboard-adapter table, qa-reviewer, wave-council, prompt-surface manifest); zero live references remain. Durable role-journal lessons promoted as active memory records `1t7yx-mem lifecycle-epoch-is-fixed` and `1t78a-mem patch-the-impl-module-not-the-runner`; remaining distillation bullets were either historical status noise or already canonical in AGENTS.md. `wf_validate_docs` clean.

**Changes delivered:**

- **Retire Wave Journals in Favor of the Memory System** (`1t9w9-ref retire-wave-journals-for-memory`) — 6 ACs completed. Key decisions: Retire the per-wave journal class; keep watchpoints in wave.md.; Move content-bearing wave journals into their wave folders instead of deleting.
## Journal Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| stale-journal-teaching-project-overview | maybe_later | no | completed | wave-council-delivery |
| stale-journal-watchpoints-envelope-key | do_now | no | completed | wave-council-delivery |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 26 records; 9 runs; 2 findings; current: do_now 1, maybe_later 1, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Prepare Review Evidence

Readiness council pass, 2026-07-22 (single change; claims verified against the tree and the live census):

- reality-checker: the census is real and current — 121 files in docs/agents/journals/, 100 at exactly the 52-line scaffold with every section still "Pending", ~a dozen content-bearing wave journals all pre-dating the memory system, six role journals with genuine content; the scaffold is auto-created by `wf_create_wave` (this very wave's creation just minted `1t9wa-retire-wave-journals.md`, reproducing the problem inside the wave that retires it). The claimed better-homes mapping holds: Progress Log real-time updates, Decision Logs, session handoff, wave.md watchpoints, and memory candidates with forced close-time triage are all live, exercised surfaces in this repository.
- red-team: strongest challenge — something may silently require the journal to exist (dashboard rendering, lint, close gate); answered by AC-1 exercising the full lifecycle without one and the implementation-time census of `journal` references across seeds, scripts, and the dashboard. Second challenge — deleting 100 files and moving a dozen breaks links; answered by the fail-loud live-reference residue check with closed archives exempt as historical record, plus the reindex requirement. Third — field repos: upgrades never touch journals (never-destructive principle); the migration prompt is opt-in.
- qa-reviewer: ACs are falsifiable end to end (lifecycle-without-journal, dual-heading lint acceptance, no-teaching-surface grep, empty-directory postcondition with link integrity, full suite). Destructive local steps are operator-approved in the recorded design discussion and scoped to this repository only.
- docs-contract-reviewer: the four operator rulings (retire wave journals; role journals fold into role docs + memories; wave artifacts self-contained in wave folders; scaffold deletion approved) are recorded in the Decision Log with rejected alternatives; the `-jrn` naming question is recorded as moot under retirement.

Synthesis verdict: READY.

Delta readiness pass (2026-07-22, operator-directed upgrade-path addition): reality-checker confirmed the mechanical/judgment split is decidable — a pristine scaffold is structure-matched against the rendered template family with zero non-template content lines (zero information loss provable), wave-journal relocation requires only that the wave directory exists, and everything else defers to the operator-invoked prompt with an upgrade-report listing; red-team's strongest challenge — template drift across versions could misclassify an old scaffold as content-bearing — fails SAFE (unclassified journals are left in place and reported, never deleted); qa-reviewer confirmed AC-4's fixture proof pins the one-non-template-line survival case, relocation, reporting, and re-run no-op; docs-contract-reviewer confirmed the operator revision of the opt-in-only ruling is recorded with the never-destructive principle honored in substance. Synthesis: READY.

## Review Checkpoints

- **Delivery-phase Wave Council [delivery-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: verbatim role-journal folds carrying stale pre-rename tool names into live docs — confirmed real, live-caught by the shipped reconcile_scan guard and repaired with the canonical rename map; strongest-alternative: exempting migrated Operating Memory sections from the retired-surface scan — rejected, live docs must not teach retired surfaces regardless of provenance.)

- **Prepare-phase Wave Council [prepare-council] — 2026-07-22 (delta, upgrade path): PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: template drift misclassifying scaffolds — resolved fail-safe, unclassified journals are reported and never deleted; strongest-alternative: auto-folding role journals in the upgrade — rejected, content merges need judgment and stay with the prompt.)

- **Prepare-phase Wave Council [prepare-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a hidden consumer requiring the journal's existence — resolved by the full-lifecycle-without-journal AC plus an implementation-time reference census; strongest-alternative: lazy/opt-in journal creation keeping the class alive — rejected, the census refutes the niche and the memory candidate flow covers it with forced triage.)

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

Delivery council pass, 2026-07-22 (single change; claims verified against the tree, the suite, and the live index):

- reality-checker: the postcondition is real — `docs/agents/journals/` no longer exists; 99 pristine scaffolds deleted, 16 wave journals relocated (each verified sitting at `docs/waves/<wave-id>/<wave-id-dashes>.md`), 6 role journals folded verbatim into their role/persona docs under an Operating Memory section, and durable lessons promoted as active memory records (`1t7yx-mem lifecycle-epoch-is-fixed`, `1t78a-mem patch-the-impl-module-not-the-runner`). Zero live references remain (repository-wide census excluding wave/report archives); the rebuilt docs index (epoch generation 22, clean finish) serves relocated journals from their wave folders flagged historical and nothing from the retired path.
- red-team: strongest challenge — a verbatim fold can carry stale instructions into live docs, and it DID: the folded sections named pre-1.14.0 tool names, live-caught by the shipped `reconcile_scan` guard in the full-suite run (10 findings) and repaired with the canonical rename map. Second challenge — the mechanical upgrade migration misclassifying journals; two real bugs were live-caught by running the hook on this repository before tests existed (relocation demanded all template fields; role journals with wave-id references mis-relocated) and both are pinned as regressions in `JournalMigrationTests`. Third — field repos with hand-drifted scaffolds: the matcher fails safe (left + reported, never deleted), proven by the one-content-line survival test.
- qa-reviewer: AC-1..AC-6 all evidenced — lifecycle-without-journal and watchpoints-heading tests in `test_server_tools.py`, the 8-test `JournalMigrationTests` fixture proof (pristine deletion, survival, relocation, both live-caught regressions, idempotence, README exemption, version gate), the seeds census for AC-3 (39 remaining mentions all retirement-aware), and a clean single-run full suite: 6,138 tests across 59 files OK.
- docs-contract-reviewer: change doc tracking is real-time and honest — Progress Log records both live-caught hook bugs and the fold's stale-tool-name repair; every AC and task is `[x]` with evidence; docs gate clean; the operator-approved destructive steps (scaffold deletion) are recorded in the Decision Log with the scope ruling.

Synthesis verdict: PASS — deliverable matches the admitted contract; the three live-caught defects were all repaired in-wave with regressions pinned.

Operator review + repair cycle, 2026-07-22 (post-council): the operator's independent review found two stale public-surface issues the delivery council missed. P1 `stale-journal-watchpoints-envelope-key`: `wf_implement_wave` still returned the retired `journal_watchpoints` envelope key with two "Journal Watchpoints" docstrings while this record claimed envelope fields were removed; repaired as a clean rename to `watchpoints` (no alias, per the 1.14.0 no-aliases precedent) with the test now asserting the old key absent. P2 `stale-journal-teaching-project-overview`: the orientation doc still taught journals as current lifecycle state; rewritten to memory-record language, with `docs/waves/README.md` also corrected to lead with `## Watchpoints`. Both chains are terminal (implementer repair_start, qa-reviewer reverification with executed evidence); post-repair full suite 6,138 OK; `wave-council-delivery` re-approved with fresh independent context after both repairs. Council miss classes recorded in the change doc: the envelope census stopped at the creation path, and teaching-language staleness has no mechanical guard.
- operator-signoff: approved 2026-07-22 (operator reviewed the delivery, filed two findings, verified the repairs, and instructed close in session)

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 13 | 17,033 |
| implement | 26 | 736,148 |
| review | 45 | 2,965,746 |
| **Total** | **84** | **3,718,927** |

<!-- wave:context-efficiency-state {"generation":84,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":26,"content_source_credit":749317,"derived_artifact_credit":26,"direct_net":736148,"estimated_tokens_saved":736148,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1011,"response_debit":12184,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":13,"content_source_credit":17476,"derived_artifact_credit":412,"direct_net":17033,"estimated_tokens_saved":17033,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2180,"response_debit":8094,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9419},"review":{"calls":45,"content_source_credit":3048062,"derived_artifact_credit":1030,"direct_net":2965746,"estimated_tokens_saved":2965746,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10708,"response_debit":73733,"source_credit_count":329,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1095}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":84,"content_source_credit":3814855,"derived_artifact_credit":1468,"direct_net":3718927,"estimated_tokens_saved":3718927,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13899,"response_debit":94011,"source_credit_count":355,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10514},"wave_id":"1t9wa retire-wave-journals"} -->
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
